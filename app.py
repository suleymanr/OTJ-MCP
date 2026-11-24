from __future__ import annotations

import os
import sys


def _dispatch() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--mcp":
        from timelog.mcp.server import main as mcp_main

        return mcp_main(args[1:])

    if args and args[0] == "--auth":
        from timelog.auth import main as auth_main

        return auth_main(args[1:])

    # built as a console exe so --mcp stdio works; hide the console for gui mode
    if os.name == "nt" and getattr(sys, "frozen", False) and "--check" not in args:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)

    from timelog.desktop.app import main as desktop_main

    return desktop_main()


if __name__ == "__main__":
    raise SystemExit(_dispatch())
