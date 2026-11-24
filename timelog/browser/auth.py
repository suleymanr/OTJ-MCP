#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import threading
import time
from typing import Any, Callable

import webview

from timelog import paths
from timelog.config import (
    API_ORIGIN,
    OMBIEL_HOME,
    QMPLUS_LOGIN,
    TIMELOG_START_URL,
    UA,
    WINDOW_SIZE,
)
from timelog.server.modules import calendar as ombiel_calendar
from timelog.server.modules import qmplus as qmplus_client

SERVICES: dict[str, tuple[str, str]] = {
    "session": ("Sign in — OneAdvanced", TIMELOG_START_URL),
    "ombiel": ("Sign in — CampusM", OMBIEL_HOME),
    "qmplus": ("Sign in — QMplus", QMPLUS_LOGIN),
}

_REFRESHAUTH_JS = (
    "(() => {"
    "  try {"
    "    const x = new XMLHttpRequest();"
    "    x.open('GET', '/refreshauth', false);"
    "    x.withCredentials = true;"
    "    x.send();"
    "    return x.status;"
    "  } catch (e) { return 0; }"
    "})()"
)

_CLICK_PROFILE_JS = (
    "(() => {"
    "  const el = Array.from(document.querySelectorAll('a,button,div,span'))"
    "    .find(e => e.textContent && e.textContent.trim() === 'Student/Staff user');"
    "  if (el) { el.click(); return true; }"
    "  return false;"
    "})()"
)

_CLICK_SAML_JS = (
    "(() => {"
    "  const el = Array.from(document.querySelectorAll('a,button'))"
    "    .find(e => e.textContent && e.textContent.includes('Login via SAML2'));"
    "  if (el) { el.click(); return true; }"
    "  return false;"
    "})()"
)

_QMPLUS_LOGGED_IN_JS = (
    "(() => {"
    "  const body = (document.body && document.body.innerText) || '';"
    "  return location.href.includes('qmplus.qmul.ac.uk')"
    "    && !body.includes('Log in to the site')"
    "    && !body.includes('guest access')"
    "    && (body.includes('Log out') || body.includes('My Modules') || document.title.includes('Dashboard'));"
    "})()"
)

_QMPLUS_SESSKEY_JS = (
    "(() => {"
    "  if (window.M && window.M.cfg && window.M.cfg.sesskey) return window.M.cfg.sesskey;"
    "  const m = document.documentElement.innerHTML.match(/\"sesskey\"\\s*:\\s*\"([^\"]+)\"/);"
    "  return m ? m[1] : '';"
    "})()"
)


def read_cookies(window: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for cookie in window.get_cookies() or []:
        for name, morsel in cookie.items():
            if morsel.value:
                out.append({"name": name, "value": morsel.value})
    return out


def _save_timelog_cookies(cookies: list[dict[str, str]]) -> bool:
    by_name = {c["name"]: c["value"] for c in cookies if c.get("name") and c.get("value")}
    access = by_name.get("ACCESS_TOKEN")
    refresh = by_name.get("REFRESH_TOKEN")
    if not access:
        return False

    data = paths.read_json(paths.TOKENS_FILE, {}) or {}
    data["access_token"] = access
    if refresh:
        data["refresh_token"] = refresh
    elif data.get("refresh_token") and paths.jwt_exp(data["refresh_token"]) <= time.time():
        data["refresh_token"] = None

    data["obtained_at"] = int(time.time())
    data["source"] = "webview"
    paths.write_json(paths.TOKENS_FILE, data)
    return True


def _poll_session(window: Any, stop: threading.Event, timeout_s: int) -> bool:
    deadline = time.time() + timeout_s
    while not stop.is_set() and time.time() < deadline:
        try:
            url = window.get_current_url() or ""
            if url.startswith(API_ORIGIN) and window.evaluate_js(_REFRESHAUTH_JS) == 200:
                if _save_timelog_cookies(read_cookies(window)):
                    return True
        except Exception:
            pass
        stop.wait(1.5)

    return False


def _poll_ombiel(window: Any, stop: threading.Event, timeout_s: int) -> bool:
    deadline = time.time() + timeout_s
    clicked_profile = False

    while not stop.is_set() and time.time() < deadline:
        try:
            url = window.get_current_url() or ""
            if not clicked_profile and "select-profile" in url:
                clicked_profile = bool(window.evaluate_js(_CLICK_PROFILE_JS))

            cookies = read_cookies(window)
            token = next((c["value"] for c in cookies if c["name"] == "cmAuthToken"), "")
            if len(token) > 200:
                ombiel_calendar.save_cookies(cookies, source="webview")
                if ombiel_calendar.CalendarClient().calendars():
                    return True
        except Exception:
            pass
        stop.wait(1.5)

    return False


def _poll_qmplus(window: Any, stop: threading.Event, timeout_s: int) -> bool:
    deadline = time.time() + timeout_s
    clicked_saml = False

    while not stop.is_set() and time.time() < deadline:
        try:
            url = window.get_current_url() or ""
            if not clicked_saml and "/login/" in url:
                clicked_saml = bool(window.evaluate_js(_CLICK_SAML_JS))

            if window.evaluate_js(_QMPLUS_LOGGED_IN_JS):
                sesskey = window.evaluate_js(_QMPLUS_SESSKEY_JS) or None
                qmplus_client.save_cookies(read_cookies(window), sesskey=sesskey, source="webview")
                return True
        except Exception:
            pass
        stop.wait(1.5)

    return False


_POLLERS: dict[str, Callable[[Any, threading.Event, int], bool]] = {
    "session": _poll_session,
    "ombiel": _poll_ombiel,
    "qmplus": _poll_qmplus,
}


def open_login_window(
    service: str,
    *,
    timeout_s: int = 1800,
    on_done: Callable[[bool], None] | None = None,
) -> Any:
    title, url = SERVICES[service]
    poller = _POLLERS[service]
    stop = threading.Event()
    finished = threading.Event()

    window = webview.create_window(
        title,
        url=url,
        width=WINDOW_SIZE,
        height=WINDOW_SIZE,
        min_size=(460, 460),
    )

    def _on_closed() -> None:
        stop.set()
        if not finished.is_set() and on_done:
            finished.set()
            on_done(False)

    window.events.closed += _on_closed

    def _watch() -> None:
        ok = poller(window, stop, timeout_s)
        if not finished.is_set():
            finished.set()
            if on_done:
                on_done(ok)
        if ok:
            try:
                window.destroy()
            except Exception:
                pass

    threading.Thread(target=_watch, daemon=True).start()
    return window


def refresh_once(timeout_s: int = 20) -> bool:
    paths.ensure_data_dir()
    ok_box = [False]
    stop = threading.Event()

    window = webview.create_window(
        "Timelog Refresh",
        url=TIMELOG_START_URL,
        width=400,
        height=400,
        hidden=True,
    )

    def _run() -> None:
        ok_box[0] = _poll_session(window, stop, timeout_s)
        try:
            window.destroy()
        except Exception:
            pass

    webview.start(
        _run,
        debug=False,
        private_mode=False,
        storage_path=str(paths.PROFILE_DIR),
        user_agent=UA,
    )
    return ok_box[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Native WebView auth helper")
    ap.add_argument("service", choices=["session", "ombiel", "qmplus", "refresh"])
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args(argv)

    if args.service == "refresh":
        return 0 if refresh_once(timeout_s=min(args.timeout, 30)) else 2

    ok_box = [False]
    open_login_window(
        args.service,
        timeout_s=args.timeout,
        on_done=lambda ok: ok_box.__setitem__(0, ok),
    )
    webview.start(
        debug=False,
        private_mode=False,
        storage_path=str(paths.PROFILE_DIR),
        user_agent=UA,
    )
    return 0 if ok_box[0] else 1


if __name__ == "__main__":
    sys.exit(main())
