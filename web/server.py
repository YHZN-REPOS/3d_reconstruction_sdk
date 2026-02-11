import json
import os
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parent
DEFAULT_CONFIG = REPO_DIR / "config.yaml"
SAMPLE_CONFIG = REPO_DIR / "sample_config.yaml"

_ENV_CONFIG = os.environ.get("CONFIG_FILE")
_ENV_DATA_DIR = os.environ.get("DATA_DIR")

if _ENV_CONFIG:
    CONFIG_PATH = Path(_ENV_CONFIG).resolve()
elif _ENV_DATA_DIR:
    CONFIG_PATH = Path(_ENV_DATA_DIR).resolve() / "config.yaml"
else:
    CONFIG_PATH = DEFAULT_CONFIG.resolve()

WORKING_DIR = Path(os.environ.get("DATA_DIR", str(CONFIG_PATH.parent))).resolve()
RUNS_DIR = WORKING_DIR / "runs"
SDK_IMAGE = os.environ.get("SDK_IMAGE", "recon3d-sdk:latest")
HOST_DATA_DIR = os.environ.get("HOST_DATA_DIR")

RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_host_data_dir() -> Optional[Path]:
    if HOST_DATA_DIR and HOST_DATA_DIR.strip():
        return Path(HOST_DATA_DIR).resolve()
    # Local (non-docker) run: DATA_DIR is already a host path
    env_data_dir = os.environ.get("DATA_DIR")
    if env_data_dir and env_data_dir.strip() and env_data_dir != "/project":
        return Path(env_data_dir).resolve()
    return None


def _resolve_host_config_path() -> Optional[Path]:
    host_data_dir = _resolve_host_data_dir()
    if not host_data_dir:
        return None
    try:
        rel = CONFIG_PATH.resolve().relative_to(WORKING_DIR.resolve())
        return (host_data_dir / rel).resolve()
    except Exception:
        return (host_data_dir / "config.yaml").resolve()

class ConfigUpdate(BaseModel):
    data: Optional[dict] = None
    yaml: Optional[str] = None
    validate: Optional[str] = "basic"  # basic | full

class RunInfo(BaseModel):
    run_id: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    exit_code: Optional[int] = None
    log_path: Optional[str] = None
    config_path: Optional[str] = None


class RunStartRequest(BaseModel):
    sdk_image: Optional[str] = None

class RunProcess:
    def __init__(self, run_id: str, process: 'subprocess.Popen', log_path: Path, run_dir: Path, meta_path: Path):
        self.run_id = run_id
        self.process = process
        self.log_path = log_path
        self.run_dir = run_dir
        self.meta_path = meta_path
        self.started_at = datetime.now()
        self.ended_at: Optional[datetime] = None
        self.exit_code: Optional[int] = None
        self.status = "running"

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "exit_code": self.exit_code,
            "log_path": str(self.log_path),
            "config_path": str(CONFIG_PATH),
        }

RUNNING: Dict[str, RunProcess] = {}
RUNNING_LOCK = threading.Lock()

app = FastAPI()

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

@app.get("/")
def index():
    html_path = APP_DIR / "templates" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


def _load_yaml_config() -> str:
    if not CONFIG_PATH.exists():
        return ""
    return CONFIG_PATH.read_text(encoding="utf-8")


def _parse_yaml(text: str) -> dict:
    try:
        if text.strip() == "":
            return {}
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("Root of YAML must be a mapping")
        return data
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}")


def _resolve_working_dir(data: dict) -> Path:
    env_data_dir = os.environ.get("DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir).resolve()
    if data.get("working_dir"):
        return Path(data["working_dir"]).resolve()
    return CONFIG_PATH.parent.resolve()


def _validate_config(data: dict, validate_mode: str) -> None:
    if validate_mode == "basic":
        return
    working_dir = _resolve_working_dir(data)
    images_path = working_dir / "images"
    if not images_path.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Input images directory not found: {images_path}. "
                f"Please place your images in {working_dir}/images/"
            ),
        )


def _save_yaml_config(text: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(text, encoding="utf-8")


def _load_default_data() -> dict:
    for path in (DEFAULT_CONFIG, SAMPLE_CONFIG):
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8")
                data = yaml.safe_load(text) or {}
                if isinstance(data, dict):
                    return data
            except Exception:
                return {}
    return {}


def _load_template_yaml() -> str:
    if SAMPLE_CONFIG.exists():
        try:
            return SAMPLE_CONFIG.read_text(encoding="utf-8")
        except Exception:
            return ""
    if DEFAULT_CONFIG.exists():
        try:
            return DEFAULT_CONFIG.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def _ensure_config_exists() -> None:
    if CONFIG_PATH.exists():
        return
    if SAMPLE_CONFIG.exists():
        _save_yaml_config(SAMPLE_CONFIG.read_text(encoding="utf-8"))
    else:
        _save_yaml_config("run_sparse: true\nrun_mesh: false\nrun_gaussian: true\nrun_gs_to_pc: false\n")


@app.get("/api/config")
def get_config():
    _ensure_config_exists()
    text = _load_yaml_config()
    data = _parse_yaml(text)
    host_config_path = _resolve_host_config_path()
    return {
        "path": str(host_config_path) if host_config_path else str(CONFIG_PATH),
        "data": data,
        "yaml": text,
        "defaults": _load_default_data(),
        "template_yaml": _load_template_yaml(),
        "sdk_image": SDK_IMAGE,
    }


@app.put("/api/config")
def update_config(payload: ConfigUpdate):
    if payload.yaml is None and payload.data is None:
        raise HTTPException(status_code=400, detail="Provide either 'yaml' or 'data'.")

    if payload.yaml is not None:
        data = _parse_yaml(payload.yaml)
        _validate_config(data, payload.validate or "basic")
        _save_yaml_config(payload.yaml)
        return {"ok": True}

    # payload.data path
    data = payload.data or {}
    _validate_config(data, payload.validate or "basic")
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    _save_yaml_config(text)
    return {"ok": True}


def _write_run_meta(meta_path: Path, meta: dict) -> None:
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _read_run_meta(meta_path: Path) -> Optional[dict]:
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _list_docker_images() -> list:
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except Exception:
        return []

    images = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "<none>:<none>" or line.startswith("<none>:") or line.endswith(":<none>"):
            continue
        images.append(line)
    return sorted(set(images))


@app.get("/api/images")
def list_images(keyword: str = ""):
    images = _list_docker_images()
    if keyword:
        kw = keyword.lower()
        images = [img for img in images if kw in img.lower()]
    return {"images": images}


def _stream_process_output(run_proc: RunProcess):
    process = run_proc.process
    exit_code = None
    try:
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if line == "" and process.poll() is not None:
                    break
                # Drain stdout to avoid blocking, unified log is written by SDK
                continue
        exit_code = process.wait()
    except Exception:
        exit_code = process.poll()
        if exit_code is None:
            try:
                exit_code = process.wait(timeout=5)
            except Exception:
                exit_code = -1

    with RUNNING_LOCK:
        run_proc.exit_code = exit_code
        run_proc.ended_at = datetime.now()
        run_proc.status = "success" if exit_code == 0 else "failed"
        meta = run_proc.to_dict()
        _write_run_meta(run_proc.meta_path, meta)
        RUNNING.pop(run_proc.run_id, None)


def _create_run_dir(run_id: str) -> Path:
    run_dir = RUNS_DIR / run_id
    if run_dir.exists():
        raise HTTPException(status_code=409, detail="Run ID already exists")
    run_dir.mkdir(parents=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    return run_dir


def _build_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@app.post("/api/runs")
def start_run(payload: Optional[RunStartRequest] = None):
    # Block multiple runs by default
    with RUNNING_LOCK:
        if RUNNING:
            raise HTTPException(status_code=409, detail="Another run is in progress")

    _ensure_config_exists()

    run_id = _build_run_id()
    run_dir = _create_run_dir(run_id)
    log_path = run_dir / "logs" / "sdk.log"
    meta_path = run_dir / "run.json"

    host_data_dir = HOST_DATA_DIR
    if not host_data_dir or host_data_dir.strip() == "":
        if WORKING_DIR.is_absolute() and str(WORKING_DIR) != "/project":
            host_data_dir = str(WORKING_DIR)
        else:
            raise HTTPException(
                status_code=400,
                detail="HOST_DATA_DIR is not set. Please set it to the host DATA_DIR.",
            )

    host_data_dir = str(Path(host_data_dir).resolve())
    try:
        rel_config_path = CONFIG_PATH.resolve().relative_to(WORKING_DIR.resolve())
        host_config_path = str(Path(host_data_dir) / rel_config_path)
    except Exception:
        host_config_path = str(Path(host_data_dir) / "config.yaml")

    sdk_image = SDK_IMAGE
    if payload and payload.sdk_image:
        sdk_image = payload.sdk_image.strip() or SDK_IMAGE

    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock",
        "-v",
        "/etc/localtime:/etc/localtime:ro",
        "-v",
        f"{host_data_dir}:/project",
        "-v",
        f"{host_config_path}:/tmp/config.yaml",
        "-e",
        "DATA_DIR=/project",
        "-e",
        f"HOST_DATA_DIR={host_data_dir}",
        "-e",
        "CONFIG_FILE=/tmp/config.yaml",
        "-e",
        f"RESUME_ID={run_id}",
        "-e",
        "PYTHONUNBUFFERED=1",
        sdk_image,
        "--config",
        "/tmp/config.yaml",
    ]

    import subprocess
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    run_proc = RunProcess(run_id, process, log_path, run_dir, meta_path)
    meta = run_proc.to_dict()
    _write_run_meta(meta_path, meta)

    with RUNNING_LOCK:
        RUNNING[run_id] = run_proc

    t = threading.Thread(target=_stream_process_output, args=(run_proc,), daemon=True)
    t.start()

    return {"ok": True, "run_id": run_id}


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    with RUNNING_LOCK:
        run_proc = RUNNING.get(run_id)

    if not run_proc:
        raise HTTPException(status_code=404, detail="Run not found or already finished")

    process = run_proc.process
    process.send_signal(signal.SIGTERM)

    try:
        process.wait(timeout=10)
    except Exception:
        process.kill()

    return {"ok": True}


@app.get("/api/runs")
def list_runs():
    runs = []
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        meta_path = run_dir / "run.json"
        meta = _read_run_meta(meta_path) or {
            "run_id": run_dir.name,
            "status": "unknown",
            "started_at": None,
            "ended_at": None,
            "exit_code": None,
            "log_path": str(run_dir / "logs" / "sdk.log"),
            "config_path": str(CONFIG_PATH),
        }
        with RUNNING_LOCK:
            if run_dir.name in RUNNING:
                meta["status"] = "running"
        runs.append(meta)
    return {"runs": runs}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    meta_path = run_dir / "run.json"
    meta = _read_run_meta(meta_path)
    if meta is None:
        meta = {
            "run_id": run_id,
            "status": "unknown",
            "started_at": None,
            "ended_at": None,
            "exit_code": None,
            "log_path": str(run_dir / "logs" / "sdk.log"),
            "config_path": str(CONFIG_PATH),
        }
    with RUNNING_LOCK:
        if run_id in RUNNING:
            meta["status"] = "running"
    return meta


@app.get("/api/runs/{run_id}/logs")
def get_run_logs(run_id: str, offset: int = 0):
    log_path = RUNS_DIR / run_id / "logs" / "sdk.log"
    if not log_path.exists():
        return PlainTextResponse("", headers={"X-Next-Offset": "0"})

    data = log_path.read_bytes()
    if offset < 0:
        offset = 0
    if offset > len(data):
        offset = len(data)

    chunk = data[offset:]
    next_offset = offset + len(chunk)
    return PlainTextResponse(chunk.decode("utf-8", errors="ignore"), headers={"X-Next-Offset": str(next_offset)})


@app.get("/api/runs/{run_id}/download")
def download_run(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    import tempfile
    import shutil

    tmp_dir = Path(tempfile.gettempdir())
    archive_path = tmp_dir / f"run_{run_id}"
    zip_path = shutil.make_archive(str(archive_path), "zip", root_dir=str(run_dir))
    return FileResponse(zip_path, filename=f"run_{run_id}.zip", media_type="application/zip")
