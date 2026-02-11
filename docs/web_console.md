# Web 控制台使用说明

本说明适用于当前 SDK 的 Web 可视化控制台（配置编辑、任务启停、日志查看、历史记录、结果下载）。

---

## 1. Docker 方式（推荐）

### 启动
```bash
# 先构建 SDK 镜像（首次或 SDK 代码更新时）
docker compose build sdk

# DATA_DIR 指向你的宿主机项目目录（包含 images/ 及可选的 config.yaml）
DATA_DIR=/abs/path/to/project docker compose up --build web
```

### 访问
浏览器打开：
```
http://localhost:8000
```

### 说明
- 只需挂载 `DATA_DIR`，Web 会在首次访问时自动生成 `/project/config.yaml`（宿主机路径为 `$DATA_DIR/config.yaml`）。  
- 保存配置会写回宿主机项目目录。  
- 启动任务后，结果会输出到 `$DATA_DIR/runs/<run_id>/`。  
- “下载结果”会打包该 `run_id` 目录为 zip。  
- Web 端会通过 `docker run` 拉起 **SDK 容器** 执行任务，因此宿主机需要有 `recon3d-sdk:latest` 镜像（或通过 `SDK_IMAGE` 指定）。  

---

## 2. 本地方式（不使用 Docker）

### 安装依赖
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r /Users/gmet/mnt/code/3d_reconstruction_sdk/web/requirements.txt
```

### 启动服务
```bash
DATA_DIR=/abs/path/to/project \
uvicorn web.server:app --host 0.0.0.0 --port 8000
```

### 说明
- 若不设置 `DATA_DIR`，默认使用仓库根目录的 `config.yaml`。  
- 启动任务时，SDK 仍会在 `DATA_DIR/runs/` 下生成输出。  
- 本地运行 Web 时，也会通过 `docker run` 启动 SDK，因此同样需要先构建 SDK 镜像。  

---

## 3. 可选环境变量

- `DATA_DIR`：宿主机项目目录（包含 `images/`），用于运行输出与默认 config 保存位置。  
- `CONFIG_FILE`：显式指定配置文件路径（默认：`$DATA_DIR/config.yaml`）。  
- `WEB_PORT`：Docker 启动时的端口映射（默认 8000）。  
- `SDK_IMAGE`：SDK 镜像名称（默认 `recon3d-sdk:latest`）。  
- `HOST_DATA_DIR`：宿主机的 `DATA_DIR`，Web 用于启动 SDK 容器时挂载（Docker 模式会自动设置）。  

---

## 4. 常见问题

1. **Web 能打开但无法启动任务？**  
   请确认 `DATA_DIR` 指向的目录包含 `images/`，且 Docker 能运行。  

2. **保存配置后不生效？**  
   请确认 `DATA_DIR` 是宿主机真实路径，且写权限正常。  
