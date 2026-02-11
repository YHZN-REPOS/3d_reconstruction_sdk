const state = {
  config: null,
  yaml: "",
  defaults: {},
  templateYaml: "",
  sdkImage: "",
  activeRunId: null,
  activeStatus: "idle",
  logOffset: 0,
};

const el = (id) => document.getElementById(id);
const valueOrDefault = (value, fallback) => {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") return fallback;
    return trimmed;
  }
  if (value === undefined || value === null) return fallback;
  return value;
};
const numOrDefault = (value, fallback) => {
  const parsed = parseInt(value, 10);
  if (Number.isFinite(parsed)) return parsed;
  return fallback;
};

function setStatus(text) {
  el("global-status").textContent = text;
  el("active-status").textContent = text;
}

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function fillForm(data) {
  const defaults = state.defaults || {};
  el("run_sparse").checked = data.run_sparse ?? defaults.run_sparse ?? false;
  el("run_mesh").checked = data.run_mesh ?? defaults.run_mesh ?? false;
  el("run_gaussian").checked = data.run_gaussian ?? defaults.run_gaussian ?? true;
  el("run_gs_to_pc").checked = data.run_gs_to_pc ?? defaults.run_gs_to_pc ?? false;
  el("use_gps").checked = data.use_gps ?? defaults.use_gps ?? true;
  el("quality_preset").value = data.quality_preset || defaults.quality_preset || "medium";
  el("feature_type").value = data.feature_type || defaults.feature_type || "sift";
  el("sh_degree").value = data.sh_degree ?? defaults.sh_degree ?? 3;

  const alg = data.algorithms || {};
  const defaultAlg = defaults.algorithms || {};
  el("alg_sfm").value = alg.sfm || defaultAlg.sfm || "opensfm";
  el("alg_reconstruction").value = alg.reconstruction || defaultAlg.reconstruction || "opensplat";
  el("alg_sfm_image").value = alg.sfm_docker_image || defaultAlg.sfm_docker_image || "";
  el("alg_reconstruction_image").value = alg.reconstruction_docker_image || defaultAlg.reconstruction_docker_image || "";
  el("alg_gs_to_pc_image").value = alg.gs_to_pc_docker_image || defaultAlg.gs_to_pc_docker_image || "";

  const opensplat = (data.params && data.params.opensplat) || {};
  const defaultOpenSplat = (defaults.params && defaults.params.opensplat) || {};
  el("opensplat_iterations").value = opensplat.iterations ?? defaultOpenSplat.iterations ?? 2000;
  if (opensplat["save-every"] !== undefined) {
    el("opensplat_save_every").value = opensplat["save-every"];
  } else if (defaultOpenSplat["save-every"] !== undefined) {
    el("opensplat_save_every").value = defaultOpenSplat["save-every"];
  } else {
    const preset = data.quality_preset || defaults.quality_preset || "medium";
    const saveEveryDefaults = { high: 5000, medium: 2000, low: 1000 };
    el("opensplat_save_every").value = saveEveryDefaults[preset] ?? 2000;
  }
  if (opensplat["auto-stop-on-same-size"] !== undefined) {
    el("opensplat_auto_stop").checked = !!opensplat["auto-stop-on-same-size"];
  } else if (defaultOpenSplat["auto-stop-on-same-size"] !== undefined) {
    el("opensplat_auto_stop").checked = !!defaultOpenSplat["auto-stop-on-same-size"];
  } else {
    el("opensplat_auto_stop").checked = true;
  }
}

function buildConfigFromForm() {
  const cfg = structuredClone(state.config || {});
  const defaults = state.defaults || {};
  const defaultAlg = defaults.algorithms || {};
  const defaultOpenSplat = (defaults.params && defaults.params.opensplat) || {};
  cfg.run_sparse = el("run_sparse").checked;
  cfg.run_mesh = el("run_mesh").checked;
  cfg.run_gaussian = el("run_gaussian").checked;
  cfg.run_gs_to_pc = el("run_gs_to_pc").checked;
  cfg.use_gps = el("use_gps").checked;
  cfg.quality_preset = el("quality_preset").value;
  cfg.feature_type = el("feature_type").value;
  cfg.sh_degree = parseInt(el("sh_degree").value || "3", 10);

  cfg.algorithms = cfg.algorithms || {};
  cfg.algorithms.sfm = valueOrDefault(
    el("alg_sfm").value,
    cfg.algorithms.sfm ?? defaultAlg.sfm ?? "opensfm"
  );
  cfg.algorithms.reconstruction = valueOrDefault(
    el("alg_reconstruction").value,
    cfg.algorithms.reconstruction ?? defaultAlg.reconstruction ?? "opensplat"
  );
  cfg.algorithms.sfm_docker_image = valueOrDefault(
    el("alg_sfm_image").value,
    cfg.algorithms.sfm_docker_image ?? defaultAlg.sfm_docker_image ?? ""
  );
  cfg.algorithms.reconstruction_docker_image = valueOrDefault(
    el("alg_reconstruction_image").value,
    cfg.algorithms.reconstruction_docker_image ?? defaultAlg.reconstruction_docker_image ?? ""
  );
  cfg.algorithms.gs_to_pc_docker_image = valueOrDefault(
    el("alg_gs_to_pc_image").value,
    cfg.algorithms.gs_to_pc_docker_image ?? defaultAlg.gs_to_pc_docker_image ?? ""
  );

  cfg.params = cfg.params || {};
  cfg.params.opensplat = cfg.params.opensplat || {};
  cfg.params.opensplat.iterations = numOrDefault(
    el("opensplat_iterations").value,
    cfg.params.opensplat.iterations ?? defaultOpenSplat.iterations ?? 2000
  );
  cfg.params.opensplat["save-every"] = numOrDefault(
    el("opensplat_save_every").value,
    cfg.params.opensplat["save-every"] ?? defaultOpenSplat["save-every"] ?? 2000
  );
  cfg.params.opensplat["auto-stop-on-same-size"] = el("opensplat_auto_stop").checked;

  return cfg;
}

let tooltipTarget = null;

function showTooltip(target) {
  const tooltip = el("tooltip");
  if (!tooltip) return;
  const text = target.getAttribute("data-tooltip");
  if (!text) return;

  tooltip.textContent = text;
  tooltip.setAttribute("aria-hidden", "false");
  tooltip.style.opacity = "1";
  tooltip.style.transform = "translateY(0)";

  const rect = target.getBoundingClientRect();
  const padding = 8;
  const width = tooltip.offsetWidth;
  const height = tooltip.offsetHeight;
  let top = rect.top - height - 10;
  let left = rect.left + rect.width / 2 - width / 2;

  if (top < padding) {
    top = rect.bottom + 10;
  }
  if (left < padding) {
    left = padding;
  }
  const maxLeft = window.innerWidth - width - padding;
  if (left > maxLeft) {
    left = Math.max(padding, maxLeft);
  }

  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${left}px`;
}

function hideTooltip() {
  const tooltip = el("tooltip");
  if (!tooltip) return;
  tooltip.setAttribute("aria-hidden", "true");
  tooltip.style.opacity = "0";
  tooltip.style.transform = "translateY(4px)";
  tooltipTarget = null;
}

function setupTooltipHandlers() {
  document.addEventListener("click", (event) => {
    const element =
      event.target instanceof Element ? event.target : event.target.parentElement;
    if (!element) {
      hideTooltip();
      return;
    }
    const target = element.closest("[data-tooltip]");
    if (!target) {
      hideTooltip();
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (tooltipTarget === target) {
      hideTooltip();
      return;
    }
    tooltipTarget = target;
    showTooltip(target);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hideTooltip();
  });

  window.addEventListener("scroll", hideTooltip, true);
  window.addEventListener("resize", hideTooltip);
}

async function loadConfig() {
  const res = await fetch("/api/config");
  if (!res.ok) {
    console.error("Failed to load config");
    return;
  }
  const data = await res.json();
  el("config-path").textContent = data.path;
  state.config = data.data || {};
  state.defaults = data.defaults || {};
  state.yaml = data.yaml || "";
  state.templateYaml = data.template_yaml || "";
  state.sdkImage = data.sdk_image || "";
  el("yaml-editor").value = state.yaml;
  fillForm(state.config);
  const sdkInput = el("sdk_image_input");
  if (sdkInput) {
    sdkInput.value = state.sdkImage || "";
  }
  const sdkImageEl = el("sdk-image");
  if (sdkImageEl) {
    sdkImageEl.textContent = `SDK_IMAGE: ${state.sdkImage || "-"}`;
  }
  await loadImages();
}

function populateDatalist(listId, currentValue, images) {
  const list = el(listId);
  if (!list) return;
  list.innerHTML = "";

  const seen = new Set();
  if (currentValue) {
    seen.add(currentValue);
    const option = document.createElement("option");
    option.value = currentValue;
    list.appendChild(option);
  }

  images.forEach((image) => {
    if (seen.has(image)) return;
    const option = document.createElement("option");
    option.value = image;
    list.appendChild(option);
    seen.add(image);
  });
}

async function loadImages() {
  const targets = [
    { keyword: "odm", inputId: "alg_sfm_image", listId: "images-odm" },
    { keyword: "opensplat", inputId: "alg_reconstruction_image", listId: "images-opensplat" },
    { keyword: "gs2pc", inputId: "alg_gs_to_pc_image", listId: "images-gs2pc" },
    { keyword: "recon3d-sdk", inputId: "sdk_image_input", listId: "images-sdk" },
  ];

  await Promise.all(
    targets.map(async (target) => {
      try {
        const res = await fetch(`/api/images?keyword=${encodeURIComponent(target.keyword)}`);
        if (!res.ok) return;
        const data = await res.json();
        const images = data.images || [];
        const currentValue = el(target.inputId)?.value || "";
        populateDatalist(target.listId, currentValue, images);
      } catch (err) {
        console.warn("Failed to load images", err);
      }
    })
  );
}

async function saveConfig(validateMode) {
  const payload = {
    data: buildConfigFromForm(),
    validate: validateMode || "basic",
  };
  const res = await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "保存失败");
    return;
  }
  await loadConfig();
}

async function saveYaml() {
  const payload = {
    yaml: el("yaml-editor").value,
    validate: "basic",
  };
  const res = await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "保存失败");
    return;
  }
  await loadConfig();
}

async function startRun() {
  const sdkImage = el("sdk_image_input")?.value || state.sdkImage || "";
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sdk_image: sdkImage || null }),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "启动失败");
    return;
  }
  const data = await res.json();
  state.activeRunId = data.run_id;
  state.logOffset = 0;
  el("log-output").textContent = "";
  el("active-run").textContent = state.activeRunId;
  setStatus("running");
  await refreshRuns();
}

async function stopRun() {
  if (!state.activeRunId) return;
  const res = await fetch(`/api/runs/${state.activeRunId}/stop`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "停止失败");
    return;
  }
}

async function refreshRuns() {
  const res = await fetch("/api/runs");
  if (!res.ok) return;
  const data = await res.json();
  const runs = data.runs || [];

  const running = runs.find((r) => r.status === "running");
  if (running) {
    state.activeRunId = running.run_id;
    setStatus("running");
  } else if (!state.activeRunId) {
    setStatus("idle");
  }

  renderRunList(runs);
}

function renderRunList(runs) {
  const container = el("run-list");
  container.innerHTML = "";
  runs.forEach((run) => {
    const card = document.createElement("div");
    card.className = "run-card";
    const status = run.status || "unknown";
    card.innerHTML = `
      <div class="run-id">${run.run_id}</div>
      <div class="run-meta">Status: <strong>${status}</strong></div>
      <div class="run-meta">Started: ${formatTime(run.started_at)}</div>
      <div class="run-meta">Ended: ${formatTime(run.ended_at)}</div>
      <div class="run-actions">
        <div class="button-with-help">
          <button data-action="view">View Logs</button>
          <button type="button" class="help" data-tooltip="Load this run's logs into the viewer.">?</button>
        </div>
        <div class="button-with-help">
          <button data-action="download">Download Result</button>
          <button type="button" class="help" data-tooltip="Download run artifacts as a zip.">?</button>
        </div>
      </div>
    `;
    card.querySelector("[data-action='view']").addEventListener("click", () => {
      state.activeRunId = run.run_id;
      state.logOffset = 0;
      el("log-output").textContent = "";
      el("active-run").textContent = run.run_id;
      setStatus(status);
    });
    card.querySelector("[data-action='download']").addEventListener("click", () => {
      window.location.href = `/api/runs/${run.run_id}/download`;
    });
    container.appendChild(card);
  });

  if (state.activeRunId) {
    el("active-run").textContent = state.activeRunId;
  }
}

async function pollLogs() {
  if (!state.activeRunId) return;
  const res = await fetch(`/api/runs/${state.activeRunId}/logs?offset=${state.logOffset}`);
  if (!res.ok) return;
  const text = await res.text();
  const nextOffset = parseInt(res.headers.get("X-Next-Offset") || state.logOffset, 10);
  if (text) {
    el("log-output").textContent += text;
    el("log-output").scrollTop = el("log-output").scrollHeight;
  }
  state.logOffset = nextOffset;
}

function wireEvents() {
  el("save-basic").addEventListener("click", () => saveConfig("basic"));
  el("save-validate").addEventListener("click", () => saveConfig("full"));
  el("save-yaml").addEventListener("click", saveYaml);
  el("reload-yaml").addEventListener("click", loadConfig);
  el("load-template").addEventListener("click", () => {
    if (!state.templateYaml) return;
    el("yaml-editor").value = state.templateYaml;
  });
  el("start-run").addEventListener("click", startRun);
  el("stop-run").addEventListener("click", stopRun);
  el("sdk_image_input").addEventListener("input", (event) => {
    const sdkImageEl = el("sdk-image");
    if (sdkImageEl) {
      sdkImageEl.textContent = `SDK_IMAGE: ${event.target.value || "-"}`;
    }
  });

}

async function init() {
  setupTooltipHandlers();
  wireEvents();
  await loadConfig();
  await refreshRuns();
  setInterval(refreshRuns, 5000);
  setInterval(pollLogs, 1500);
}

init();
