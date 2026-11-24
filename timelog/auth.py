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
    AUTH_SERVICES,
    AUTH_TIMEOUT_S,
    AUTH_WINDOW,
    POLL_INTERVAL_S,
    REFRESH_TIMEOUT_S,
    TIMELOG_START_URL,
    UA,
)
from timelog.services import calendar as calendar_svc
from timelog.services import qmplus as qmplus_svc
from timelog.services import timelog as timelog_svc

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


def _poll(
    window: Any,
    stop: threading.Event,
    timeout_s: int,
    check_fn: Callable[[Any], bool],
) -> bool:
    deadline = time.time() + timeout_s
    while not stop.is_set() and time.time() < deadline:
        try:
            if check_fn(window):
                return True
        except Exception:
            pass
        stop.wait(POLL_INTERVAL_S)
    return False


def _timelog_checker() -> Callable[[Any], bool]:
    def _check(window: Any) -> bool:
        url = window.get_current_url() or ""
        if url.startswith(API_ORIGIN) and window.evaluate_js(_REFRESHAUTH_JS) == 200:
            return timelog_svc.save_cookies(read_cookies(window))
        return False

    return _check


def _calendar_checker() -> Callable[[Any], bool]:
    clicked_profile = False

    def _check(window: Any) -> bool:
        nonlocal clicked_profile
        url = window.get_current_url() or ""
        if not clicked_profile and "select-profile" in url:
            clicked_profile = bool(window.evaluate_js(_CLICK_PROFILE_JS))

        cookies = read_cookies(window)
        token = next((c["value"] for c in cookies if c["name"] == "cmAuthToken"), "")
        if len(token) > 200:
            calendar_svc.save_cookies(cookies, source="webview")
            return bool(calendar_svc.CalendarClient().calendars())
        return False

    return _check


def _qmplus_checker() -> Callable[[Any], bool]:
    clicked_saml = False

    def _check(window: Any) -> bool:
        nonlocal clicked_saml
        url = window.get_current_url() or ""
        if not clicked_saml and "/login/" in url:
            clicked_saml = bool(window.evaluate_js(_CLICK_SAML_JS))

        if window.evaluate_js(_QMPLUS_LOGGED_IN_JS):
            sesskey = window.evaluate_js(_QMPLUS_SESSKEY_JS) or None
            qmplus_svc.save_cookies(read_cookies(window), sesskey=sesskey, source="webview")
            return True
        return False

    return _check


_CHECKERS: dict[str, Callable[[], Callable[[Any], bool]]] = {
    "timelog": _timelog_checker,
    "calendar": _calendar_checker,
    "qmplus": _qmplus_checker,
}


def open_login_window(
    service: str,
    *,
    timeout_s: int = AUTH_TIMEOUT_S,
    on_done: Callable[[bool], None] | None = None,
) -> Any:
    title, url = AUTH_SERVICES[service]
    check_fn = _CHECKERS[service]()
    stop = threading.Event()
    finished = threading.Event()

    window = webview.create_window(
        title,
        url=url,
        width=AUTH_WINDOW["width"],
        height=AUTH_WINDOW["height"],
        min_size=AUTH_WINDOW["min_size"],
    )

    def _on_closed() -> None:
        stop.set()
        if not finished.is_set() and on_done:
            finished.set()
            on_done(False)

    window.events.closed += _on_closed

    def _watch() -> None:
        ok = _poll(window, stop, timeout_s, check_fn)
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


def refresh_once(timeout_s: int = REFRESH_TIMEOUT_S) -> bool:
    paths.ensure_data_dir()
    ok_box = [False]
    stop = threading.Event()
    check_fn = _timelog_checker()

    window = webview.create_window(
        "Timelog Refresh",
        url=TIMELOG_START_URL,
        width=400,
        height=400,
        hidden=True,
    )

    def _run() -> None:
        ok_box[0] = _poll(window, stop, timeout_s, check_fn)
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
    ap.add_argument("service", choices=["timelog", "calendar", "qmplus", "refresh"])
    ap.add_argument("--timeout", type=int, default=AUTH_TIMEOUT_S)
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
