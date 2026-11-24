#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from timelog import paths

HTTP_URL = "http://127.0.0.1:8765/mcp"
NAME = "timelog"

HOME = Path.home()
if os.name == "nt":
    APPDATA = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
    ZED_SETTINGS = APPDATA / "Zed" / "settings.json"
elif sys.platform == "darwin":
    APPDATA = HOME / "Library" / "Application Support"
    ZED_SETTINGS = HOME / ".config" / "zed" / "settings.json"
else:
    APPDATA = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
    ZED_SETTINGS = HOME / ".config" / "zed" / "settings.json"


def _which(*names: str) -> bool:
    return any(shutil.which(n) for n in names)


TARGETS: dict[str, dict[str, Any]] = {
    "claude-code": {
        "name": "Claude Code",
        "kind": "json",
        "key": "mcpServers",
        "path": HOME / ".claude.json",
        "detect": lambda: _which("claude")
        or (HOME / ".claude.json").exists()
        or (HOME / ".claude").is_dir(),
        "supports_http": True,
        "note": "User-scope MCP servers in ~/.claude.json",
    },
    "claude-desktop": {
        "name": "Claude Desktop",
        "kind": "json",
        "key": "mcpServers",
        "path": APPDATA / "Claude" / "claude_desktop_config.json",
        "detect": lambda: (APPDATA / "Claude").is_dir(),
        "supports_http": False,
        "note": "Requires restarting Claude Desktop",
    },
    "antigravity": {
        "name": "Antigravity",
        "kind": "json",
        "key": "mcpServers",
        "path": HOME / ".gemini" / "config" / "mcp_config.json",
        "detect": lambda: _which("agy", "antigravity")
        or (HOME / ".gemini" / "antigravity-cli").is_dir()
        or (HOME / ".gemini" / "antigravity").is_dir()
        or (HOME / ".gemini" / "config" / "mcp_config.json").exists(),
        "supports_http": True,
        "note": "~/.gemini/config/mcp_config.json",
    },
    "gemini": {
        "name": "Gemini CLI",
        "kind": "json",
        "key": "mcpServers",
        "path": HOME / ".gemini" / "settings.json",
        "detect": lambda: _which("gemini") or (HOME / ".gemini").is_dir(),
        "supports_http": True,
        "note": "~/.gemini/settings.json",
    },
    "codex": {
        "name": "Codex CLI",
        "kind": "toml",
        "key": "mcp_servers",
        "path": HOME / ".codex" / "config.toml",
        "detect": lambda: _which("codex") or (HOME / ".codex").is_dir(),
        "supports_http": True,
        "note": "~/.codex/config.toml",
    },
    "cursor": {
        "name": "Cursor",
        "kind": "json",
        "key": "mcpServers",
        "path": HOME / ".cursor" / "mcp.json",
        "detect": lambda: _which("cursor") or (HOME / ".cursor").is_dir(),
        "supports_http": True,
        "note": "Global MCP config for Cursor",
    },
    "windsurf": {
        "name": "Windsurf",
        "kind": "json",
        "key": "mcpServers",
        "path": HOME / ".codeium" / "windsurf" / "mcp_config.json",
        "detect": lambda: _which("windsurf") or (HOME / ".codeium").is_dir(),
        "supports_http": True,
        "note": "mcp_config.json for Windsurf",
    },
    "vscode": {
        "name": "VS Code (Copilot MCP)",
        "kind": "json",
        "key": "servers",
        "path": APPDATA / "Code" / "User" / "mcp.json",
        "detect": lambda: _which("code") or (APPDATA / "Code").is_dir(),
        "supports_http": True,
        "note": "User-level mcp.json",
    },
    "zed": {
        "name": "Zed",
        "kind": "json",
        "key": "context_servers",
        "path": ZED_SETTINGS,
        "detect": lambda: _which("zed") or ZED_SETTINGS.parent.is_dir(),
        "supports_http": False,
        "note": "context_servers in Zed settings",
    },
}


def _entry_present(meta: dict[str, Any]) -> bool:
    path: Path = meta["path"]
    try:
        if not path.exists() or path.stat().st_size == 0:
            return False

        if meta["kind"] == "json":
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return False
            section = data.get(meta["key"]) or {}
            return isinstance(section, dict) and NAME in section

        import tomllib

        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        return NAME in (data.get("mcp_servers") or {})
    except Exception:
        return False


def targets() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tid, meta in TARGETS.items():
        path: Path = meta["path"]
        try:
            detected = bool(meta["detect"]())
        except Exception:
            detected = False

        out.append(
            {
                "id": tid,
                "name": meta["name"],
                "path": str(path),
                "detected": detected,
                "exists": path.exists(),
                "configured": _entry_present(meta),
                "supports_http": meta["supports_http"],
                "note": meta["note"],
            }
        )

    return out


def spec(tid: str, transport: str = "stdio") -> dict[str, Any]:
    if transport == "http" and TARGETS[tid]["supports_http"]:
        if tid == "gemini":
            return {"httpUrl": HTTP_URL}
        if tid == "antigravity":
            return {"url": HTTP_URL}
        return {"type": "http", "url": HTTP_URL}

    cmd = paths.mcp_command()
    base: dict[str, Any] = {"command": cmd[0], "args": cmd[1:]}
    if tid == "vscode":
        return {"type": "stdio", **base}
    if tid == "zed":
        return {"command": {"path": cmd[0], "args": cmd[1:], "env": {}}}
    return base


def _toml_section(spec_: dict[str, Any]) -> str:
    lines = [f"[mcp_servers.{NAME}]"]
    if "url" in spec_:
        lines.append(f'url = "{spec_["url"]}"')
    else:
        lines.append(f'command = {json.dumps(spec_["command"])}')
        args = ", ".join(json.dumps(a) for a in spec_["args"])
        lines.append(f"args = [{args}]")
    return "\n".join(lines) + "\n"


def _write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def install(target_ids: list[str], transport: str = "stdio") -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for tid in target_ids:
        meta = TARGETS.get(tid)
        if not meta:
            results.append({"id": tid, "ok": False, "message": "unknown target"})
            continue

        path: Path = meta["path"]
        payload = spec(tid, transport)

        try:
            bak = None
            if path.exists():
                bak = str(
                    path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
                )
                shutil.copy2(path, bak)

            if meta["kind"] == "toml":
                import tomllib

                if path.exists() and path.stat().st_size:
                    with open(path, "rb") as fh:
                        tomllib.load(fh)
                    text = path.read_text(encoding="utf-8")
                    if f"[mcp_servers.{NAME}]" in text:
                        note = "already present - left unchanged"
                    else:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with open(path, "a", encoding="utf-8") as fh:
                            if not text.endswith("\n"):
                                fh.write("\n")
                            fh.write("\n" + _toml_section(payload))
                        note = "appended"
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(_toml_section(payload), encoding="utf-8")
                    note = "created"
            else:
                data: dict[str, Any] = {}
                if path.exists() and path.stat().st_size:
                    with open(path, "r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    if not isinstance(loaded, dict):
                        raise ValueError("top-level JSON is not an object")
                    data = loaded

                key = meta["key"]
                data.setdefault(key, {})
                if not isinstance(data[key], dict):
                    raise ValueError(f'"{key}" is not an object')

                data[key][NAME] = payload
                _write_json_file(path, data)
                note = "written"

            results.append(
                {
                    "id": tid,
                    "name": meta["name"],
                    "ok": True,
                    "path": str(path),
                    "backup": bak,
                    "message": note,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "id": tid,
                    "name": meta["name"],
                    "ok": False,
                    "path": str(path),
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )

    return results


def remove(target_ids: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for tid in target_ids:
        meta = TARGETS.get(tid)
        if not meta:
            continue

        path: Path = meta["path"]
        try:
            if meta["kind"] == "json":
                changed = False
                if path.exists():
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    key = meta["key"]
                    if (
                        isinstance(data, dict)
                        and isinstance(data.get(key), dict)
                        and NAME in data[key]
                    ):
                        del data[key][NAME]
                        _write_json_file(path, data)
                        changed = True

                results.append(
                    {
                        "id": tid,
                        "name": meta["name"],
                        "ok": True,
                        "message": "removed" if changed else "not configured",
                    }
                )
            else:
                results.append(
                    {
                        "id": tid,
                        "name": meta["name"],
                        "ok": False,
                        "message": "remove the [mcp_servers.timelog] block manually",
                    }
                )
        except Exception as exc:
            results.append(
                {"id": tid, "name": meta["name"], "ok": False, "message": str(exc)}
            )

    return results
