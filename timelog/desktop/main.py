from __future__ import annotations

import os
import sys
import time

import webview

from timelog import paths
from timelog.config import UA
from timelog.desktop.bridge import Api, ICON_FILE, MCP_SERVER, UI_FILE


def main() -> int:
    if "--check" in sys.argv:
        ok = os.path.exists(UI_FILE) and (paths.FROZEN or os.path.exists(MCP_SERVER))
        import timelog.browser.auth  # noqa: F401
        import timelog.integrations  # noqa: F401
        import timelog.server.modules.client  # noqa: F401
        import timelog.updater  # noqa: F401

        print("ui:", "ok" if os.path.exists(UI_FILE) else "MISSING")
        print("check:", "ok" if ok else "failed")
        return 0 if ok else 1

    api = Api()
    window = webview.create_window(
        "Timelog",
        url=UI_FILE,
        js_api=api,
        width=700,
        height=640,
        min_size=(500, 440),
        frameless=True,
        easy_drag=False,
        background_color="#141416",
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
        "icon": ICON_FILE if os.path.exists(ICON_FILE) else None,
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
