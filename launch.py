#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

from timelog.config import CREATE_NO_WINDOW, MIN_PYTHON, MIN_SPLASH_SECONDS
from timelog.paths import APP_SCRIPT, ROOT
from timelog.updater import (
    ensure_shortcut_icon,
    ensure_venv,
    update_via_git,
    venv_python,
    venv_pythonw,
)


def _run_with_splash(skip_update: bool) -> Exception | None:
    try:
        import tkinter as tk
    except Exception:
        start = time.monotonic()
        if not skip_update:
            update_via_git(lambda msg: print(msg, flush=True))
        ensure_venv(lambda msg: print(msg, flush=True))
        remaining = MIN_SPLASH_SECONDS - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(remaining)
        return None

    root = tk.Tk()
    root.title("Timelog")
    root.overrideredirect(True)
    root.configure(bg="#2b2b30")

    width, height = 380, 176
    sx = (root.winfo_screenwidth() - width) // 2
    sy = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{sx}+{sy}")

    shell = tk.Frame(root, bg="#141416")
    shell.pack(fill="both", expand=True, padx=1, pady=1)

    font_family = "Segoe UI" if os.name == "nt" else "Helvetica"
    cancelled = threading.Event()

    titlebar = tk.Frame(shell, bg="#141416", height=36)
    titlebar.pack(fill="x", side="top")
    titlebar.pack_propagate(False)

    brand = tk.Frame(titlebar, bg="#141416")
    brand.pack(side="left", padx=(12, 0), fill="y")

    mark = tk.Canvas(brand, width=18, height=18, bg="#141416", highlightthickness=0)
    mark.pack(side="left", pady=9)
    mark.create_oval(2, 2, 16, 16, outline="#e5e5e5", width=1.6)
    mark.create_arc(2, 2, 16, 16, start=0, extent=90, fill="#e5e5e5", outline="")

    brand_lbl = tk.Label(
        brand,
        text="Timelog",
        fg="#f5f5f5",
        bg="#141416",
        font=(font_family, 10, "bold"),
    )
    brand_lbl.pack(side="left", padx=(7, 0))

    def start_move(event: tk.Event) -> None:  # type: ignore[type-arg]
        root._drag_x = event.x  # type: ignore[attr-defined]
        root._drag_y = event.y  # type: ignore[attr-defined]

    def do_move(event: tk.Event) -> None:  # type: ignore[type-arg]
        dx = event.x - getattr(root, "_drag_x", 0)
        dy = event.y - getattr(root, "_drag_y", 0)
        root.geometry(f"+{root.winfo_x() + dx}+{root.winfo_y() + dy}")

    for w in (titlebar, brand, mark, brand_lbl):
        w.bind("<ButtonPress-1>", start_move)  # type: ignore[attr-defined]
        w.bind("<B1-Motion>", do_move)  # type: ignore[attr-defined]

    def on_close() -> None:
        cancelled.set()
        try:
            root.destroy()
        except Exception:
            pass

    def on_minimize() -> None:
        root.overrideredirect(False)
        root.iconify()

    def on_map(event: tk.Event) -> None:  # type: ignore[type-arg]
        if root.state() == "normal":
            root.overrideredirect(True)

    root.bind("<Map>", on_map)

    close_btn = tk.Label(
        titlebar,
        text="×",
        fg="#a1a1aa",
        bg="#141416",
        width=4,
        font=(font_family, 12),
        cursor="hand2",
    )
    close_btn.pack(side="right", fill="y")
    close_btn.bind("<Enter>", lambda _e: close_btn.configure(bg="#c42b1c", fg="#ffffff"))
    close_btn.bind("<Leave>", lambda _e: close_btn.configure(bg="#141416", fg="#a1a1aa"))
    close_btn.bind("<Button-1>", lambda _e: on_close())

    min_btn = tk.Label(
        titlebar,
        text="—",
        fg="#a1a1aa",
        bg="#141416",
        width=4,
        font=(font_family, 10),
        cursor="hand2",
    )
    min_btn.pack(side="right", fill="y")
    min_btn.bind("<Enter>", lambda _e: min_btn.configure(bg="#222225", fg="#ffffff"))
    min_btn.bind("<Leave>", lambda _e: min_btn.configure(bg="#141416", fg="#a1a1aa"))
    min_btn.bind("<Button-1>", lambda _e: on_minimize())

    tk.Frame(shell, bg="#26262a", height=1).pack(fill="x")

    body = tk.Frame(shell, bg="#141416")
    body.pack(fill="both", expand=True, padx=24, pady=(18, 20))

    tk.Label(
        body,
        text="TimelogMCP",
        fg="#f5f5f5",
        bg="#141416",
        font=(font_family, 13, "bold"),
    ).pack(anchor="w")

    status_var = tk.StringVar(value="Checking for updates...")
    tk.Label(
        body,
        textvariable=status_var,
        fg="#9e9ea7",
        bg="#141416",
        font=(font_family, 9),
    ).pack(anchor="w", pady=(8, 14))

    bar = tk.Canvas(body, height=3, bg="#222225", highlightthickness=0)
    bar.pack(fill="x")
    thumb = bar.create_rectangle(0, 0, 90, 3, fill="#e5e5e5", outline="")
    pos = [0]

    def animate_bar() -> None:
        if cancelled.is_set() or done.is_set():
            return
        w = bar.winfo_width() or 330
        pos[0] = (pos[0] + 10) % (w + 90)
        x0 = pos[0] - 90
        bar.coords(thumb, x0, 0, x0 + 90, 3)
        root.after(25, animate_bar)

    err_box: list[Exception | None] = [None]
    done = threading.Event()

    def set_status(msg: str) -> None:
        if cancelled.is_set():
            return
        try:
            root.after(0, status_var.set, msg)
        except Exception:
            pass

    def worker() -> None:
        start = time.monotonic()
        try:
            ensure_shortcut_icon()
            if not skip_update:
                update_via_git(set_status)
            ensure_venv(set_status)
        except Exception as exc:
            err_box[0] = exc
        finally:
            remaining = MIN_SPLASH_SECONDS - (time.monotonic() - start)
            if remaining > 0 and not cancelled.is_set():
                time.sleep(remaining)
            done.set()
            try:
                root.after(0, root.destroy)
            except Exception:
                pass

    root.after(25, animate_bar)
    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    if cancelled.is_set():
        raise SystemExit(0)
    done.wait(timeout=1)
    return err_box[0]


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required "
            f"(found {sys.version_info.major}.{sys.version_info.minor}).",
            file=sys.stderr,
        )
        return 1

    args = sys.argv[1:]
    skip_update = "--no-update" in args
    check_only = "--check" in args

    if check_only:
        ensure_venv(lambda msg: print(msg, flush=True))
        return subprocess.run([str(venv_python()), str(APP_SCRIPT), "--check"], cwd=str(ROOT)).returncode

    err = _run_with_splash(skip_update=skip_update)
    if err is not None:
        print(f"error: {err}", file=sys.stderr)
        try:
            import tkinter as tk
            from tkinter import messagebox

            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("TimelogMCP Launch Error", str(err))
            r.destroy()
        except Exception:
            pass
        return 1

    if os.name == "nt":
        subprocess.Popen(
            [str(venv_pythonw()), str(APP_SCRIPT)],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
        return 0

    os.execv(str(venv_python()), [str(venv_python()), str(APP_SCRIPT)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
