from __future__ import annotations

import sys
import time

import webview

from timelog import paths
from timelog.config import APP_TITLE, MAIN_WINDOW, UA
from timelog.desktop.bridge import Api


def main() -> int:
    if "--check" in sys.argv:
        ok = paths.UI_FILE.exists() and (paths.FROZEN or paths.APP_SCRIPT.exists())
        import timelog.auth  # noqa: F401
        import timelog.mcp.clients  # noqa: F401
        import timelog.mcp.server  # noqa: F401
        import timelog.services.timelog  # noqa: F401

        print("ui:", "ok" if paths.UI_FILE.exists() else "MISSING")
        print("check:", "ok" if ok else "failed")
        return 0 if ok else 1

    paths.ensure_data_dir()

    api = Api()
    window = webview.create_window(
        APP_TITLE,
        url=str(paths.UI_FILE),
        js_api=api,
        width=MAIN_WINDOW["width"],
        height=MAIN_WINDOW["height"],
        min_size=MAIN_WINDOW["min_size"],
        frameless=True,
        easy_drag=False,
        background_color=MAIN_WINDOW["bg"],
    )
    api._window = window

    def on_closed() -> None:
        api.stop_keepalive()
        api.stop_mcp()

    window.events.closed += on_closed

    start_kwargs = {
        "debug": False,
        "private_mode": False,
        "storage_path": str(paths.PROFILE_DIR),
        "user_agent": UA,
        "icon": str(paths.ICON_FILE) if paths.ICON_FILE.exists() else None,
    }

    if "--smoke" in sys.argv:
        def smoke() -> None:
            deadline = time.time() + 15
            while time.time() < deadline and not api._ui_ready:
                time.sleep(0.1)

            print("smoke ui:", "ready" if api._ui_ready else "timeout", flush=True)
            time.sleep(0.6)
            try:
                window.destroy()
            except Exception:
                pass

        webview.start(smoke, **start_kwargs)
        return 0 if api._ui_ready else 2

    webview.start(**start_kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
