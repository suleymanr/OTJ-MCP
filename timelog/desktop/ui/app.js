const ICON_PATHS = {
  minus: '<path d="M5 12h14"/>',
  x: '<path d="m6 6 12 12M18 6 6 18"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 8a7 7 0 0 1 11.8-1L20 12M4 12l2.1 5a7 7 0 0 0 11.8-1"/>',
  "arrow-up-right": '<path d="M7 17 17 7M8 7h9v9"/>',
  lock: '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2"/>',
  server: '<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  more: '<circle cx="5" cy="12" r="1.65" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.65" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1.65" fill="currentColor" stroke="none"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v4m0 4h.01"/>',
  loader: '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>'
};

// Brand marks from Simple Icons (CC0). Monochrome so they sit cleanly in the dark UI.
const BRAND_PATHS = {
  "claude-code": "<path d=\"M21 10.5h3v3h-3v3h-1.5v3H18v-3h-1.5v3H15v-3H9v3H7.5v-3H6v3H4.5v-3H3v-3H0v-3h3v-6h18Zm-15 0h1.5v-3H6Zm10.5 0H18v-3h-1.5z\"/>",
  "claude-desktop": "<path d=\"m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3.0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.3279h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9064-1.3114Z\"/>",
  "antigravity": "<path d=\"M12 2 3.5 21h3.2l2.1-5h6.4l2.1 5h3.2L12 2Zm-1.9 10.8L12 7.6l1.9 5.2h-3.8Z\"/>",
  "codex": "<path d=\"M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z\"/>",
  "gemini": "<path d=\"M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24 12q-2.49 0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 12 0q0 2.49-.96 4.68-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49 0 4.68.96 2.19.93 3.81 2.55t2.55 3.81\"/>",
  "cursor": "<path d=\"M11.503.131 1.891 5.678a.84.84 0 0 0-.42.726v11.188c0 .3.162.575.42.724l9.609 5.55a1 1 0 0 0 .998 0l9.61-5.55a.84.84 0 0 0 .42-.724V6.404a.84.84 0 0 0-.42-.726L12.497.131a1.01 1.01 0 0 0-.996 0M2.657 6.338h18.55c.263 0 .43.287.297.515L12.23 22.918c-.062.107-.229.064-.229-.06V12.335a.59.59 0 0 0-.295-.51l-9.11-5.257c-.109-.063-.064-.23.061-.23\"/>",
  "windsurf": "<path d=\"M23.55 5.067c-1.2038-.002-2.1806.973-2.1806 2.1765v4.8676c0 .972-.8035 1.7594-1.7597 1.7594-.568 0-1.1352-.286-1.4718-.7659l-4.9713-7.1003c-.4125-.5896-1.0837-.941-1.8103-.941-1.1334 0-2.1533.9635-2.1533 2.153v4.8957c0 .972-.7969 1.7594-1.7596 1.7594-.57 0-1.1363-.286-1.4728-.7658L.4076 5.1598C.2822 4.9798 0 5.0688 0 5.2882v4.2452c0 .2147.0656.4228.1884.599l5.4748 7.8183c.3234.462.8006.8052 1.3509.9298 1.3771.313 2.6446-.747 2.6446-2.0977v-4.893c0-.972.7875-1.7593 1.7596-1.7593h.003a1.798 1.798 0 0 1 1.4718.7658l4.9723 7.0994c.4135.5905 1.05.941 1.8093.941 1.1587 0 2.1515-.9645 2.1515-2.153v-4.8948c0-.972.7875-1.7594 1.7596-1.7594h.194a.22.22 0 0 0 .2204-.2202v-4.622a.22.22 0 0 0-.2203-.2203Z\"/>",
  "vscode": "<path d=\"M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.327 7.261A1 1 0 0 0 .326 8.74L3.899 12 .326 15.26a1 1 0 0 0 .001 1.479L1.65 17.94a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.492 1.492 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.939a1.5 1.5 0 0 0-.85-1.352zm-5.146 14.861L10.826 12l7.178-5.448v10.896z\"/>",
  "zed": "<path d=\"M2.25 1.5a.75.75 0 0 0-.75.75v16.5H0V2.25A2.25 2.25 0 0 1 2.25 0h20.095c1.002 0 1.504 1.212.795 1.92L10.764 14.298h3.486V12.75h1.5v1.922a1.125 1.125 0 0 1-1.125 1.125H9.264l-2.578 2.578h11.689V9h1.5v9.375a1.5 1.5 0 0 1-1.5 1.5H5.185L2.562 22.5H21.75a.75.75 0 0 0 .75-.75V5.25H24v16.5A2.25 2.25 0 0 1 21.75 24H1.655C.653 24 .151 22.788.86 22.08L13.19 9.75H9.75v1.5h-1.5V9.375A1.125 1.125 0 0 1 9.375 8.25h5.314l2.625-2.625H5.625V15h-1.5V5.625a1.5 1.5 0 0 1 1.5-1.5h13.19L21.438 1.5z\"/>"
};

const SOURCES = [
  {
    id: "coursework",
    icon: "icons/education.png",
    name: "education.oneadvanced.com",
    noun: "Coursework",
    start: "start_login",
    loginToast: "Sign in to education.oneadvanced.com in the browser window."
  },
  {
    id: "timetable",
    icon: "icons/timetable.png",
    name: "qmul.ombiel.co.uk",
    noun: "Timetable",
    start: "start_calendar_login",
    loginToast: "Sign in to qmul.ombiel.co.uk in the browser window."
  },
  {
    id: "materials",
    icon: "icons/materials.png",
    name: "qmplus.qmul.ac.uk",
    noun: "Course materials",
    start: "start_qmplus_login",
    loginToast: "Sign in to qmplus.qmul.ac.uk in the browser window."
  }
];

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
  return `<svg class="icon${extraClass ? ` ${extraClass}` : ""}" viewBox="0 0 24 24" aria-hidden="true">${ICON_PATHS[name] || ""}</svg>`;
}

function paintIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((element) => {
    element.innerHTML = icon(element.dataset.icon);
  });
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
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

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function parseWhen(value) {
  if (!value) return null;
  const date = new Date(String(value).replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayMonth(date) {
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

function fullDate(date) {
  return `${dayMonth(date)} ${date.getFullYear()}, ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
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
  if (!S.boot) return false;
  if (id === "coursework") return !!S.boot.timelog_login_running;
  if (id === "timetable") return !!(S.boot.calendar && S.boot.calendar.login_running);
  return !!(S.boot.qmplus && S.boot.qmplus.login_running);
}

function sourceStatus(source) {
  if (S.error) return { kind: "error", label: "Unavailable", detail: "The saved session could not be checked." };
  if (!S.boot) return { kind: "loading", label: "Checking", detail: "Reading saved session…" };

  if (source.id === "coursework") {
    const token = S.boot.token || {};
    if (token.access_expires_in > 0 || token.refresh_expires_in > 0) {
      return {
        kind: "ok",
        label: "Connected",
        detail: token.email ? `Signed in as ${token.email}` : "Your saved session is ready to use."
      };
    }
    if (token.has_access || token.has_refresh) {
      return { kind: "expired", label: "Sign-in expired", detail: "Sign in again to restore coursework and logged hours." };
    }
    return { kind: "never", label: "Not connected", detail: "Coursework, results and off-the-job hours." };
  }

  if (source.id === "timetable") {
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
        return { kind: "ok", label: "Connected", detail: `Session active until ${dayMonth(expires)}.`, title: fullDate(expires) };
      }
      return { kind: "ok", label: "Connected", detail: "Your saved session is ready to use." };
    }
    if (calendar.error) return { kind: "error", label: "Couldn't check", detail: "The saved session couldn't be read. Refresh to try again." };
    if (calendar.has_token) return { kind: "expired", label: "Sign-in expired", detail: "Sign in again to restore your timetable." };
    return { kind: "never", label: "Not connected", detail: "Classes and upcoming university events." };
  }

  const qmplus = S.boot.qmplus || {};
  if (qmplus.connected && S.qmplusValid !== false) {
    const saved = qmplus.saved_at ? new Date(qmplus.saved_at * 1000) : null;
    return { kind: "ok", label: "Connected", detail: saved ? `Session saved on ${dayMonth(saved)}.` : "Your saved session is ready to use." };
  }
  if (qmplus.connected || qmplus.has_session) {
    return { kind: "expired", label: "Session expired", detail: "Sign in again to restore course materials." };
  }
  if (qmplus.error) return { kind: "error", label: "Couldn't check", detail: "The saved session couldn't be read. Refresh to try again." };
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
  return `<span class="badge${pulsing ? " is-pulsing" : ""}" data-s="${kind}"><span class="badge-dot" aria-hidden="true"></span>${esc(label)}</span>`;
}

function renderChrome(rows) {
  const connected = rows.filter(isConnected).length;
  const attention = rows.filter((row) => row.attention).length;
  const warning = rows.some((row) => row.kind === "expiring");
  const state = S.error || attention ? "bad" : warning ? "warn" : S.boot && connected === rows.length ? "ok" : "";
  $("#globalDot").dataset.s = state;
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
    return `<button class="btn btn-secondary btn-sm is-loading" type="button" disabled><span data-icon="loader" class="spinning"></span>Waiting…</button>`;
  }
  if (row.kind === "loading") return "";
  if (row.kind === "error") return `<button class="btn btn-secondary btn-sm" type="button" data-retry>Try again</button>`;
  if (isConnected(row)) {
    return `<button class="btn btn-ghost btn-sm" type="button" data-src="${row.id}">Sign in again</button>`;
  }
  const primary = row.id === primaryId || row.kind === "expired";
  return `<button class="btn ${primary ? "btn-primary" : "btn-secondary"} btn-sm" type="button" data-src="${row.id}">${row.kind === "expired" ? "Sign in again" : "Connect"}</button>`;
}

function renderSources(rows) {
  const connected = rows.filter(isConnected).length;
  const attention = rows.filter((row) => row.attention).length;
  const warning = rows.some((row) => row.kind === "expiring");
  const statusKind = !S.boot ? "off" : S.error || attention ? "bad" : warning ? "warn" : connected === rows.length ? "ok" : "off";
  setBadge($("#sourcesStatus"), S.boot ? `${connected} of ${rows.length} connected` : "Checking…", statusKind);

  $("#refreshBtn").disabled = S.refreshing;
  $("#refreshBtn [data-icon]").classList.toggle("spinning", S.refreshing);

  if (S.error) {
    $("#sourceList").innerHTML = `
      <div class="error-row">
        <div><strong>Couldn't check your accounts</strong><p>Your saved sessions have not been changed.</p></div>
        <button class="btn btn-secondary btn-sm" type="button" data-retry>Try again</button>
      </div>`;
    return;
  }

  const primary = rows.find((row) => row.attention) || rows.find((row) => row.kind === "never");
  $("#sourceList").innerHTML = rows.map((row) => {
    const badgeState = row.kind === "ok" ? "ok" : row.kind === "expiring" ? "warn" : (row.kind === "expired" || row.kind === "error") ? "bad" : "off";
    return `
    <div class="account-row${row.attention ? " is-attention" : ""}">
      <span class="row-symbol source-icon"><img src="${esc(row.icon)}" alt="" width="26" height="26" /></span>
      <div class="row-main">
        <div class="row-heading">
          <span class="row-title">${esc(row.noun)}</span>
          <span class="row-host">${esc(row.name)}</span>
        </div>
        <p class="row-detail"${row.title ? ` title="${esc(row.title)}"` : ""}>${esc(row.detail)}</p>
      </div>
      <div class="row-actions">${badge(row.running ? "Signing in" : row.label, row.running ? "warn" : badgeState, row.running)}${sourceAction(row, primary && primary.id)}</div>
    </div>`;
  }).join("");
}

function targetRow(target) {
  if (S.confirmRemove === target.id) {
    const removing = S.pendingTarget === target.id;
    return `
      <div class="integration-row is-confirm">
        <div class="confirm-main">
          <strong>Remove Timelog from ${esc(target.name)}?</strong>
          <p>Only the Timelog entry is removed. Your other settings stay unchanged.</p>
        </div>
        <div class="confirm-actions">
          <button class="btn btn-secondary btn-sm" type="button" data-ai-cancel="${esc(target.id)}"${S.pendingTarget ? " disabled" : ""}>Cancel</button>
          <button class="btn btn-danger btn-sm${removing ? " is-loading" : ""}" type="button" data-ai-confirm="${esc(target.id)}"${S.pendingTarget ? " disabled" : ""}>${removing ? '<span data-icon="loader" class="spinning"></span>Removing…' : "Remove"}</button>
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
          <button class="menu-item" type="button" role="menuitem" data-ai-remove="${esc(target.id)}"><span>${icon("trash")}</span>Remove Timelog</button>
        </div>
      </div>`;
  } else {
    action = `<button class="btn btn-secondary btn-sm${pending ? " is-loading" : ""}" type="button" data-ai-set="${esc(target.id)}"${S.pendingTarget ? " disabled" : ""}>${pending ? '<span data-icon="loader" class="spinning"></span>Adding…' : "Add"}</button>`;
  }

  return `
    <div class="integration-row${S.aiMenu === target.id ? " has-menu" : ""}">
      <span class="tool-symbol" aria-hidden="true">${BRAND_PATHS[target.id] ? `<svg class="brand-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">${BRAND_PATHS[target.id]}</svg>` : esc((target.name || "?").charAt(0))}</span>
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
  setBadge(
    $("#aiStatus"),
    !S.boot
      ? "Finding apps…"
      : configured.length
        ? `${configured.length} added`
        : found.length
          ? `${found.length} detected`
          : "Manual setup",
    configured.length ? "ok" : "off"
  );

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
  $("#serverAddress").textContent = running ? `http://127.0.0.1:${S.mcp.port}/mcp` : "Server stopped";
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
  const result = await call(source.start);
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
    toast("ok", remove ? `Removed from ${target.name}` : `Added to ${target.name}`,
      remove ? "Timelog is no longer included in its configuration." : "Restart the app if Timelog doesn't appear straight away.");
  } else {
    toast("bad", remove ? "Couldn't remove Timelog" : `Couldn't add Timelog to ${target.name}`,
      (detail && detail.message) || (result && result.error) || "Try again.");
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
  S.serverBusy = true;
  renderAll();
  const result = running ? await call("stop_mcp") : await call("start_mcp", 8765);
  if (!result || !result.ok) {
    toast("bad", running ? "Couldn't stop the server" : "Couldn't start the server", (result && result.error) || "Try again.");
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
    S.promptData = {
      prompt: result.prompt || "",
      snippet: result.snippet || ""
    };
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
    boot.token,
    boot.calendar,
    boot.qmplus,
    boot.mcp,
    boot.targets,
    boot.timelog_login_running,
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
  if (!boot || !boot.token) {
    S.error = (boot && boot.error) || "The desktop bridge didn't respond.";
    S.boot = null;
    renderAll();
    return;
  }
  applyBoot(boot);
  S.lastKey = bootKey(boot);
  await syncKeepalive(boot.token.access_expires_in > 0 || boot.token.refresh_expires_in > 0);
}

async function poll(force = false) {
  if (S.polling) return;
  S.polling = true;
  try {
    const boot = await call("bootstrap");
    if (!boot || !boot.token) {
      if (!S.error) {
        S.error = (boot && boot.error) || "The desktop bridge didn't respond.";
        S.boot = null;
        renderAll();
      }
      return;
    }

    const tokenValid = boot.token.access_expires_in > 0 || boot.token.refresh_expires_in > 0;
    if (S.loginSeen.coursework && !boot.timelog_login_running) {
      S.loginSeen.coursework = false;
      if (tokenValid) toast("ok", "Coursework connected", boot.token.email || "The account is ready to use.");
    }
    if (S.loginSeen.timetable && boot.calendar && !boot.calendar.login_running) {
      S.loginSeen.timetable = false;
      if (boot.calendar.connected) toast("ok", "Timetable connected", boot.calendar.mail || "The account is ready to use.");
    }
    if (S.loginSeen.materials && boot.qmplus && !boot.qmplus.login_running) {
      S.loginSeen.materials = false;
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
    const copied = await copyText(`http://127.0.0.1:${S.mcp.port}/mcp`);
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
