const SOURCES = [
  {
    id: "timelog",
    icon: "icons/education.png",
    name: "education.oneadvanced.com",
    noun: "Coursework",
    loginToast: "Sign in to education.oneadvanced.com in the browser window."
  },
  {
    id: "calendar",
    icon: "icons/timetable.png",
    name: "qmul.ombiel.co.uk",
    noun: "Timetable",
    loginToast: "Sign in to qmul.ombiel.co.uk in the browser window."
  },
  {
    id: "qmplus",
    icon: "icons/materials.png",
    name: "qmplus.qmul.ac.uk",
    noun: "Course materials",
    loginToast: "Sign in to qmplus.qmul.ac.uk in the browser window."
  }
];

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const S = {
  boot: null,
  targets: [],
  mcp: null,
  qmplusValid: undefined,
  qmplusTried: false,
  error: "",
  aiMenu: null,
  confirmRemove: null,
  loginSeen: {},
  pendingSource: null,
  pendingTarget: null,
  refreshing: false,
  serverBusy: false,
  keepalive: false,
  polling: false,
  lastKey: "",
  lastFocus: null,
  promptTab: "prompt",
  promptData: { prompt: "", snippet: "" }
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function icon(name, extraClass = "") {
  const cls = `icon${extraClass ? ` ${extraClass}` : ""}`;
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON_PATHS[name] || ""}</svg>`;
}

function paintIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((element) => {
    element.innerHTML = icon(element.dataset.icon);
  });
}

function esc(value) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(value ?? "").replace(/[&<>"']/g, (ch) => map[ch]);
}

function call(name, ...args) {
  try {
    if (!window.pywebview || !window.pywebview.api) {
      return Promise.resolve({ ok: false, error: "The desktop bridge isn't ready." });
    }
    return Promise.resolve(window.pywebview.api[name](...args)).catch((error) => ({
      ok: false,
      error: String(error)
    }));
  } catch (error) {
    return Promise.resolve({ ok: false, error: String(error) });
  }
}

function toast(kind, title, body = "") {
  const element = document.createElement("div");
  element.className = "toast";
  element.dataset.s = kind || "ok";

  const iconWrap = document.createElement("span");
  iconWrap.className = "toast-icon";
  iconWrap.innerHTML = `<span data-icon="${kind === "bad" ? "alert" : "check"}"></span>`;

  const content = document.createElement("div");
  content.className = "toast-body-wrap";

  const heading = document.createElement("div");
  heading.className = "toast-title";
  heading.textContent = title;
  content.appendChild(heading);

  if (body) {
    const detail = document.createElement("div");
    detail.className = "toast-body";
    detail.textContent = body;
    content.appendChild(detail);
  }

  const close = document.createElement("button");
  close.type = "button";
  close.className = "icon-btn toast-close";
  close.setAttribute("aria-label", "Dismiss notification");
  close.innerHTML = '<span data-icon="x"></span>';

  const dismiss = () => {
    if (element.classList.contains("is-leaving")) return;
    element.classList.add("is-leaving");
    setTimeout(() => element.remove(), 160);
  };
  close.addEventListener("click", dismiss);

  element.append(iconWrap, content, close);
  paintIcons(element);
  $("#toasts").appendChild(element);
  setTimeout(dismiss, 5000);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (fallbackError) {
      copied = false;
    }
    area.remove();
    return copied;
  }
}

function parseWhen(value) {
  if (!value) return null;
  const date = new Date(String(value).replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayMonth(date) {
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

function fullDate(date) {
  const hm = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${dayMonth(date)} ${date.getFullYear()}, ${hm}`;
}

function inDays(days) {
  const count = Math.ceil(days);
  if (count <= 0) return "today";
  return count === 1 ? "in 1 day" : `in ${count} days`;
}

function isConnected(row) {
  return row.kind === "ok" || row.kind === "expiring";
}

function loginRunning(id) {
  if (S.pendingSource === id) return true;
  if (!S.boot || !S.boot[id]) return false;
  return !!S.boot[id].login_running;
}

function sourceStatus(source) {
  if (S.error) {
    return { kind: "error", label: "Unavailable", detail: "The saved session could not be checked." };
  }
  if (!S.boot) {
    return { kind: "loading", label: "Checking", detail: "Reading saved session…" };
  }

  if (source.id === "timelog") {
    const token = S.boot.timelog || {};
    if (token.access_expires_in > 0 || token.refresh_expires_in > 0) {
      return {
        kind: "ok",
        label: "Connected",
        detail: token.email ? `Signed in as ${token.email}` : "Your saved session is ready to use."
      };
    }
    if (token.has_access || token.has_refresh) {
      return {
        kind: "expired",
        label: "Sign-in expired",
        detail: "Sign in again to restore coursework and logged hours."
      };
    }
    return {
      kind: "never",
      label: "Not connected",
      detail: "Coursework, results and off-the-job hours."
    };
  }

  if (source.id === "calendar") {
    const calendar = S.boot.calendar || {};
    if (calendar.connected) {
      const expires = parseWhen(calendar.expires_at);
      if (expires) {
        const days = (expires.getTime() - Date.now()) / 86400000;
        if (days <= 7) {
          return {
            kind: "expiring",
            label: "Expires soon",
            detail: `Session expires ${inDays(days)}. Sign in again to keep it active.`,
            title: fullDate(expires)
          };
        }
        return {
          kind: "ok",
          label: "Connected",
          detail: `Session active until ${dayMonth(expires)}.`,
          title: fullDate(expires)
        };
      }
      return { kind: "ok", label: "Connected", detail: "Your saved session is ready to use." };
    }
    if (calendar.error) {
      return {
        kind: "error",
        label: "Couldn't check",
        detail: "The saved session couldn't be read. Refresh to try again."
      };
    }
    if (calendar.has_token) {
      return {
        kind: "expired",
        label: "Sign-in expired",
        detail: "Sign in again to restore your timetable."
      };
    }
    return { kind: "never", label: "Not connected", detail: "Classes and upcoming university events." };
  }

  const qmplus = S.boot.qmplus || {};
  if (qmplus.connected && S.qmplusValid !== false) {
    const saved = qmplus.saved_at ? new Date(qmplus.saved_at * 1000) : null;
    return {
      kind: "ok",
      label: "Connected",
      detail: saved ? `Session saved on ${dayMonth(saved)}.` : "Your saved session is ready to use."
    };
  }
  if (qmplus.connected || qmplus.has_session) {
    return {
      kind: "expired",
      label: "Session expired",
      detail: "Sign in again to restore course materials."
    };
  }
  if (qmplus.error) {
    return {
      kind: "error",
      label: "Couldn't check",
      detail: "The saved session couldn't be read. Refresh to try again."
    };
  }
  return { kind: "never", label: "Not connected", detail: "Lecture slides, module resources and files." };
}

function sourceRows() {
  return SOURCES.map((source) => {
    const status = sourceStatus(source);
    return {
      ...source,
      ...status,
      running: loginRunning(source.id),
      attention: status.kind === "expired" || status.kind === "error"
    };
  });
}

function setBadge(element, label, kind = "off", pulsing = false) {
  element.dataset.s = kind;
  element.classList.toggle("is-pulsing", !!pulsing);
  element.innerHTML = `<span class="badge-dot" aria-hidden="true"></span>${esc(label)}`;
}

function badge(label, kind = "off", pulsing = false) {
  const cls = `badge${pulsing ? " is-pulsing" : ""}`;
  return `<span class="${cls}" data-s="${kind}"><span class="badge-dot" aria-hidden="true"></span>${esc(label)}</span>`;
}

function summaryState(rows) {
  const connected = rows.filter(isConnected).length;
  const attention = rows.filter((row) => row.attention).length;
  const warning = rows.some((row) => row.kind === "expiring");
  let kind = "off";
  if (S.error || attention) kind = "bad";
  else if (warning) kind = "warn";
  else if (S.boot && connected === rows.length) kind = "ok";
  return { connected, attention, kind };
}

function renderChrome(rows) {
  const { connected, attention, kind } = summaryState(rows);
  $("#globalDot").dataset.s = kind === "off" ? "" : kind;
  $("#globalStatus").textContent = S.error
    ? "Check unavailable"
    : !S.boot
      ? "Checking accounts"
      : `${connected} of ${rows.length} connected`;

  $(".status-pill").title = attention
    ? `${attention} account${attention === 1 ? "" : "s"} need attention`
    : `${connected} of ${rows.length} university accounts connected`;
}

function sourceAction(row, primaryId) {
  if (row.running) {
    return (
      '<button class="btn btn-secondary btn-sm is-loading" type="button" disabled>' +
      '<span data-icon="loader" class="spinning"></span>Waiting…</button>'
    );
  }
  if (row.kind === "loading") return "";
  if (row.kind === "error") {
    return '<button class="btn btn-secondary btn-sm" type="button" data-retry>Try again</button>';
  }
  if (isConnected(row)) {
    return `<button class="btn btn-ghost btn-sm" type="button" data-src="${row.id}">Sign in again</button>`;
  }
  const primary = row.id === primaryId || row.kind === "expired";
  const label = row.kind === "expired" ? "Sign in again" : "Connect";
  return `<button class="btn ${primary ? "btn-primary" : "btn-secondary"} btn-sm" type="button" data-src="${row.id}">${label}</button>`;
}

function renderSources(rows) {
  const { connected, kind } = summaryState(rows);
  const statusKind = !S.boot ? "off" : kind;
  setBadge(
    $("#sourcesStatus"),
    S.boot ? `${connected} of ${rows.length} connected` : "Checking…",
    statusKind
  );

  $("#refreshBtn").disabled = S.refreshing;
  $("#refreshBtn [data-icon]").classList.toggle("spinning", S.refreshing);

  if (S.error) {
    $("#sourceList").innerHTML = `
      <div class="error-row">
        <div>
          <strong>Couldn't check your accounts</strong>
          <p>Your saved sessions have not been changed.</p>
        </div>
        <button class="btn btn-secondary btn-sm" type="button" data-retry>Try again</button>
      </div>`;
    return;
  }

  const primary = rows.find((row) => row.attention) || rows.find((row) => row.kind === "never");
  $("#sourceList").innerHTML = rows.map((row) => {
    let badgeState = "off";
    if (row.kind === "ok") badgeState = "ok";
    else if (row.kind === "expiring") badgeState = "warn";
    else if (row.kind === "expired" || row.kind === "error") badgeState = "bad";

    const badgeEl = badge(
      row.running ? "Signing in" : row.label,
      row.running ? "warn" : badgeState,
      row.running
    );

    return `
      <div class="account-row${row.attention ? " is-attention" : ""}">
        <span class="row-symbol source-icon">
          <img src="${esc(row.icon)}" alt="" width="26" height="26" />
        </span>
        <div class="row-main">
          <div class="row-heading">
            <span class="row-title">${esc(row.noun)}</span>
            <span class="row-host">${esc(row.name)}</span>
          </div>
          <p class="row-detail"${row.title ? ` title="${esc(row.title)}"` : ""}>${esc(row.detail)}</p>
        </div>
        <div class="row-actions">
          ${badgeEl}${sourceAction(row, primary && primary.id)}
        </div>
      </div>`;
  }).join("");
}

function targetRow(target) {
  if (S.confirmRemove === target.id) {
    const removing = S.pendingTarget === target.id;
    const disabled = S.pendingTarget ? " disabled" : "";
    const removeLabel = removing
      ? '<span data-icon="loader" class="spinning"></span>Removing…'
      : "Remove";

    return `
      <div class="integration-row is-confirm">
        <div class="confirm-main">
          <strong>Remove Timelog from ${esc(target.name)}?</strong>
          <p>Only the Timelog entry is removed. Your other settings stay unchanged.</p>
        </div>
        <div class="confirm-actions">
          <button class="btn btn-secondary btn-sm" type="button" data-ai-cancel="${esc(target.id)}"${disabled}>Cancel</button>
          <button class="btn btn-danger btn-sm${removing ? " is-loading" : ""}" type="button" data-ai-confirm="${esc(target.id)}"${disabled}>${removeLabel}</button>
        </div>
      </div>`;
  }

  const configured = !!target.configured;
  const pending = S.pendingTarget === target.id;
  let action;

  if (configured) {
    const open = S.aiMenu === target.id;
    action = `
      <div class="menu-wrap">
        <button class="icon-btn" type="button" data-ai-menu="${esc(target.id)}" aria-haspopup="menu" aria-expanded="${open}" aria-label="Options for ${esc(target.name)}">${icon("more")}</button>
        <div class="menu" role="menu"${open ? "" : " hidden"}>
          <button class="menu-item" type="button" role="menuitem" data-ai-remove="${esc(target.id)}">
            <span>${icon("trash")}</span>Remove Timelog
          </button>
        </div>
      </div>`;
  } else {
    const disabled = S.pendingTarget ? " disabled" : "";
    const addLabel = pending
      ? '<span data-icon="loader" class="spinning"></span>Adding…'
      : "Add";
    action = `<button class="btn btn-secondary btn-sm${pending ? " is-loading" : ""}" type="button" data-ai-set="${esc(target.id)}"${disabled}>${addLabel}</button>`;
  }

  const symbol = BRAND_PATHS[target.id]
    ? `<svg class="brand-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">${BRAND_PATHS[target.id]}</svg>`
    : esc((target.name || "?").charAt(0));

  return `
    <div class="integration-row${S.aiMenu === target.id ? " has-menu" : ""}">
      <span class="tool-symbol" aria-hidden="true">${symbol}</span>
      <div class="row-main">
        <div class="row-title">${esc(target.name)}</div>
        <p class="row-detail">${configured ? "Timelog is added to this app's local configuration." : "Detected on this device."}</p>
      </div>
      <div class="row-actions">${badge(configured ? "Added" : "Available", configured ? "ok" : "off")}${action}</div>
    </div>`;
}

function renderAi() {
  const found = S.targets.filter((target) => target.detected);
  const configured = S.targets.filter((target) => target.configured);

  let aiLabel = "Manual setup";
  if (!S.boot) aiLabel = "Finding apps…";
  else if (configured.length) aiLabel = `${configured.length} added`;
  else if (found.length) aiLabel = `${found.length} detected`;

  setBadge($("#aiStatus"), aiLabel, configured.length ? "ok" : "off");

  if (!S.boot) {
    $("#targetList").innerHTML = '<div class="empty-row">Looking for supported AI apps…</div>';
  } else if (!found.length) {
    $("#targetList").innerHTML = '<div class="empty-row">No supported AI apps found. Use Manual setup above.</div>';
  } else {
    $("#targetList").innerHTML = found.map(targetRow).join("");
  }

  const running = !!(S.mcp && S.mcp.running);
  const toggle = $("#serverToggle");
  toggle.setAttribute("aria-checked", running ? "true" : "false");
  toggle.disabled = !!S.error || S.serverBusy;

  setBadge(
    $("#serverSummary"),
    S.serverBusy ? "Updating…" : running ? "Running" : "Optional",
    S.serverBusy ? "warn" : running ? "ok" : "off",
    S.serverBusy
  );
  $("#serverNote").textContent = running
    ? "Available to clients that connect over HTTP. Keep Timelog open while the server is in use."
    : "Most AI apps start Timelog automatically. Only run this for clients that connect over HTTP.";
  $("#endpointBar").hidden = !running;
  $("#serverAddress").textContent = running
    ? (S.mcp.url || `http://127.0.0.1:${S.mcp.port}/mcp`)
    : "Server stopped";
}

function renderAll() {
  const rows = sourceRows();
  renderChrome(rows);
  renderSources(rows);
  renderAi();
  paintIcons(document);
}

async function startSource(id) {
  const source = SOURCES.find((item) => item.id === id);
  if (!source || S.pendingSource) return;

  S.pendingSource = id;
  renderAll();

  const result = await call("start_login", id);
  if (result && result.ok) {
    S.loginSeen[id] = true;
    toast("ok", "Sign-in window opened", source.loginToast);
  } else {
    toast("bad", "Couldn't open the sign-in window", (result && result.error) || "Try again.");
  }

  S.pendingSource = null;
  await poll(true);
}

async function refresh() {
  if (S.refreshing) return;
  S.refreshing = true;
  renderAll();
  await loadBootstrap();
  S.refreshing = false;
  renderAll();
}

async function setTarget(id, remove) {
  const target = S.targets.find((item) => item.id === id);
  if (!target || S.pendingTarget) return;

  S.pendingTarget = id;
  renderAll();

  const result = remove ? await call("remove_servers", [id]) : await call("install", [id], "stdio");
  const detail = (result && result.results && result.results[0]) || null;
  const ok = result && result.ok && (!detail || detail.ok);

  if (ok) {
    toast(
      "ok",
      remove ? `Removed from ${target.name}` : `Added to ${target.name}`,
      remove
        ? "Timelog is no longer included in its configuration."
        : "Restart the app if Timelog doesn't appear straight away."
    );
  } else {
    toast(
      "bad",
      remove ? "Couldn't remove Timelog" : `Couldn't add Timelog to ${target.name}`,
      (detail && detail.message) || (result && result.error) || "Try again."
    );
  }

  S.confirmRemove = null;
  S.aiMenu = null;
  const targets = await call("targets");
  if (targets && targets.targets) S.targets = targets.targets;
  S.pendingTarget = null;
  renderAll();
}

async function toggleServer() {
  if (S.serverBusy) return;
  const running = !!(S.mcp && S.mcp.running);
  const defaultPort = (S.boot && S.boot.config && S.boot.config.port) || 8765;

  S.serverBusy = true;
  renderAll();

  const result = running ? await call("stop_mcp") : await call("start_mcp", defaultPort);
  if (!result || !result.ok) {
    toast(
      "bad",
      running ? "Couldn't stop the server" : "Couldn't start the server",
      (result && result.error) || "Try again."
    );
  }

  const state = await call("mcp_state");
  if (state && typeof state.running === "boolean") S.mcp = state;
  S.serverBusy = false;
  renderAll();
}

function renderPromptModal() {
  const tabs = $(".modal-tabs");
  tabs.dataset.active = S.promptTab;
  $$("[data-prompt-tab]").forEach((button) => {
    button.setAttribute("aria-selected", button.dataset.promptTab === S.promptTab ? "true" : "false");
  });

  $("#promptDescription").textContent = S.promptTab === "snippet"
    ? "Merge this server entry into your AI client's MCP configuration file."
    : "Paste this prompt into an AI app that can edit files or run commands.";

  const text = S.promptTab === "snippet"
    ? (S.promptData.snippet || "Building your JSON config…")
    : (S.promptData.prompt || "Building your setup prompt…");
  $("#promptText").textContent = text;

  const copy = $("#copyPromptBtn");
  copy.innerHTML = `<span data-icon="copy">${icon("copy")}</span>${S.promptTab === "snippet" ? "Copy JSON" : "Copy prompt"}`;
}

async function openPrompt() {
  S.lastFocus = document.activeElement;
  S.promptTab = "prompt";
  S.promptData = { prompt: "", snippet: "" };
  $("#promptModal").hidden = false;
  renderPromptModal();

  const copy = $("#copyPromptBtn");
  copy.disabled = true;
  const result = await call("mcp_prompt");
  if (result && result.ok) {
    S.promptData = { prompt: result.prompt || "", snippet: result.snippet || "" };
  } else {
    const err = (result && result.error) || "Couldn't build the setup prompt.";
    S.promptData = { prompt: err, snippet: err };
  }

  renderPromptModal();
  copy.disabled = false;
  if (!$("#promptModal").hidden) copy.focus();
}

function closePrompt() {
  $("#promptModal").hidden = true;
  if (S.lastFocus && S.lastFocus.isConnected) S.lastFocus.focus();
}

async function copyPrompt() {
  const button = $("#copyPromptBtn");
  const copied = await copyText($("#promptText").textContent || "");
  if (!copied) {
    toast("bad", "Couldn't copy", "Select the text and copy it manually.");
    return;
  }

  const label = S.promptTab === "snippet" ? "Copy JSON" : "Copy prompt";
  button.innerHTML = `<span data-icon="check">${icon("check")}</span>Copied`;
  setTimeout(() => {
    if (!button.disabled) button.innerHTML = `<span data-icon="copy">${icon("copy")}</span>${label}`;
  }, 1800);
}

function trapFocus(event) {
  if (event.key !== "Tab") return;
  const focusable = $$("#promptModal button:not(:disabled), #promptModal [tabindex='0']");
  if (!focusable.length) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function bootKey(boot) {
  return JSON.stringify([
    boot.timelog,
    boot.calendar,
    boot.qmplus,
    boot.mcp,
    boot.targets,
    S.qmplusValid !== false
  ]);
}

async function syncKeepalive(active) {
  if (active === S.keepalive) return;
  S.keepalive = active;
  if (active) await call("start_keepalive");
  else await call("stop_keepalive");
}

async function checkQmplus() {
  if (!S.boot || !S.boot.qmplus || !S.boot.qmplus.connected || S.qmplusTried) return;
  S.qmplusTried = true;
  const result = await call("qmplus_check");
  if (result && result.valid === true) S.qmplusValid = true;
  else if (result && result.valid === false) S.qmplusValid = false;
  renderAll();
  S.lastKey = bootKey(S.boot);
}

function applyBoot(boot) {
  S.boot = boot;
  S.targets = boot.targets || [];
  S.mcp = boot.mcp || {};
  S.error = "";
  renderAll();
  if (boot.qmplus && boot.qmplus.connected) checkQmplus();
}

async function loadBootstrap() {
  const boot = await call("bootstrap");
  if (!boot || !boot.timelog) {
    S.error = (boot && boot.error) || "The desktop bridge didn't respond.";
    S.boot = null;
    renderAll();
    return;
  }

  applyBoot(boot);
  S.lastKey = bootKey(boot);
  await syncKeepalive(boot.timelog.access_expires_in > 0 || boot.timelog.refresh_expires_in > 0);
}

async function poll(force = false) {
  if (S.polling) return;
  S.polling = true;

  try {
    const boot = await call("bootstrap");
    if (!boot || !boot.timelog) {
      if (!S.error) {
        S.error = (boot && boot.error) || "The desktop bridge didn't respond.";
        S.boot = null;
        renderAll();
      }
      return;
    }

    const tokenValid = boot.timelog.access_expires_in > 0 || boot.timelog.refresh_expires_in > 0;
    if (S.loginSeen.timelog && !boot.timelog.login_running) {
      S.loginSeen.timelog = false;
      if (tokenValid) {
        toast("ok", "Coursework connected", boot.timelog.email || "The account is ready to use.");
      }
    }
    if (S.loginSeen.calendar && boot.calendar && !boot.calendar.login_running) {
      S.loginSeen.calendar = false;
      if (boot.calendar.connected) {
        toast("ok", "Timetable connected", boot.calendar.mail || "The account is ready to use.");
      }
    }
    if (S.loginSeen.qmplus && boot.qmplus && !boot.qmplus.login_running) {
      S.loginSeen.qmplus = false;
      if (boot.qmplus.connected) {
        S.qmplusValid = undefined;
        S.qmplusTried = false;
        toast("ok", "Course materials connected", "The account is ready to use.");
      }
    }

    const key = bootKey(boot);
    if (force || S.error || key !== S.lastKey) {
      S.lastKey = key;
      applyBoot(boot);
    }
    await syncKeepalive(tokenValid);
  } finally {
    S.polling = false;
  }
}

function bind() {
  $("#minBtn").addEventListener("click", () => call("minimize"));
  $("#closeBtn").addEventListener("click", () => call("close"));
  $("#refreshBtn").addEventListener("click", refresh);
  $("#serverToggle").addEventListener("click", toggleServer);
  $("#copyPromptBtn").addEventListener("click", copyPrompt);

  $("#copyServerBtn").addEventListener("click", async () => {
    if (!S.mcp || !S.mcp.running) return;
    const button = $("#copyServerBtn");
    const url = S.mcp.url || `http://127.0.0.1:${S.mcp.port}/mcp`;
    const copied = await copyText(url);
    if (!copied) {
      toast("bad", "Couldn't copy the address");
      return;
    }
    button.innerHTML = `<span data-icon="check">${icon("check")}</span>Copied`;
    setTimeout(() => {
      button.innerHTML = `<span data-icon="copy">${icon("copy")}</span>Copy`;
    }, 1800);
  });

  $("#dataFolderBtn").addEventListener("click", async () => {
    const info = await call("app_info");
    if (info && info.data) call("reveal", info.data);
  });

  document.addEventListener("click", async (event) => {
    if (event.target.closest("[data-open-prompt]")) {
      await openPrompt();
      return;
    }

    const promptTab = event.target.closest("[data-prompt-tab]");
    if (promptTab) {
      S.promptTab = promptTab.dataset.promptTab;
      renderPromptModal();
      return;
    }

    if (event.target.closest("[data-close-modal]")) {
      closePrompt();
      return;
    }

    const sourceButton = event.target.closest("[data-src]");
    if (sourceButton) {
      await startSource(sourceButton.dataset.src);
      return;
    }
    if (event.target.closest("[data-retry]")) {
      await refresh();
      return;
    }

    const menuButton = event.target.closest("[data-ai-menu]");
    if (menuButton) {
      S.aiMenu = S.aiMenu === menuButton.dataset.aiMenu ? null : menuButton.dataset.aiMenu;
      renderAi();
      paintIcons($("#targetList"));
      const current = $(`[data-ai-menu="${menuButton.dataset.aiMenu}"]`);
      if (current) current.focus();
      return;
    }

    const removeButton = event.target.closest("[data-ai-remove]");
    if (removeButton) {
      S.confirmRemove = removeButton.dataset.aiRemove;
      S.aiMenu = null;
      renderAi();
      paintIcons($("#targetList"));
      const confirm = $("[data-ai-confirm]");
      if (confirm) confirm.focus();
      return;
    }

    const confirmButton = event.target.closest("[data-ai-confirm]");
    if (confirmButton) {
      await setTarget(confirmButton.dataset.aiConfirm, true);
      return;
    }

    const cancelButton = event.target.closest("[data-ai-cancel]");
    if (cancelButton) {
      S.confirmRemove = null;
      renderAi();
      paintIcons($("#targetList"));
      const menu = $(`[data-ai-menu="${cancelButton.dataset.aiCancel}"]`);
      if (menu) menu.focus();
      return;
    }

    const setupButton = event.target.closest("[data-ai-set]");
    if (setupButton) {
      await setTarget(setupButton.dataset.aiSet, false);
      return;
    }

    if (S.aiMenu && !event.target.closest(".menu-wrap")) {
      S.aiMenu = null;
      renderAi();
      paintIcons($("#targetList"));
    }
  });

  document.addEventListener("keydown", (event) => {
    if (!$("#promptModal").hidden) {
      if (event.key === "Escape") closePrompt();
      else trapFocus(event);
      return;
    }
    if (event.key === "Escape" && (S.aiMenu || S.confirmRemove)) {
      S.aiMenu = null;
      S.confirmRemove = null;
      renderAi();
      paintIcons($("#targetList"));
    }
  });
}

async function init() {
  paintIcons();
  bind();
  await new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api) return resolve();
    window.addEventListener("pywebviewready", resolve, { once: true });
  });
  await loadBootstrap();
  call("ui_ready");
  setInterval(() => poll(), 5000);
}

document.addEventListener("DOMContentLoaded", init);
