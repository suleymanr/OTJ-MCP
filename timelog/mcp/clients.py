from __future__ import annotations

import json
import shutil
import time
import tomllib
from pathlib import Path
from typing import Any

from timelog import paths
from timelog.config import MCP_CLIENTS, MCP_SERVER_NAME, mcp_http_url


def _client_path(meta: dict[str, Any], overrides: dict[str, Path] | None = None) -> Path:
    if overrides and meta["key_id"] in overrides:
        return overrides[meta["key_id"]]

    return paths.CLIENT_ROOTS[meta["root"]].joinpath(*meta["rel_path"])


def _detected(meta: dict[str, Any], config_path: Path) -> bool:
    if any(shutil.which(name) for name in meta["bins"]):
        return True

    if meta["detect_file"] and config_path.exists():
        return True

    return any(
        paths.CLIENT_ROOTS[root].joinpath(*parts).is_dir()
        for root, parts in meta["detect_dirs"]
    )


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}

    if path.suffix == ".toml":
        with open(path, "rb") as fh:
            return tomllib.load(fh)
            
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("top-level JSON is not an object")

    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _backup(path: Path) -> str | None:
    if not path.exists():
        return None

    bak = str(path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}"))
    shutil.copy2(path, bak)
    return bak


def _entry_present(path: Path, key: str) -> bool:
    try:
        section = _read_config(path).get(key)
        return isinstance(section, dict) and MCP_SERVER_NAME in section
    except Exception:
        return False


def targets(path_overrides: dict[str, Path] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tid, meta in MCP_CLIENTS.items():
        cfg_path = (
            path_overrides[tid]
            if path_overrides and tid in path_overrides
            else paths.CLIENT_ROOTS[meta["root"]].joinpath(*meta["rel_path"])
        )
        try:
            detected = _detected(meta, cfg_path)
        except Exception:
            detected = False

        out.append(
            {
                "id": tid,
                "name": meta["name"],
                "path": str(cfg_path),
                "detected": detected,
                "exists": cfg_path.exists(),
                "configured": _entry_present(cfg_path, meta["key"]),
                "supports_http": meta["supports_http"],
                "note": meta["note"],
            }
        )
    return out


def spec(tid: str, transport: str = "stdio") -> dict[str, Any]:
    if transport == "http" and MCP_CLIENTS[tid]["supports_http"]:
        url = mcp_http_url()

        if tid == "gemini":
            return {"httpUrl": url}
        if tid == "antigravity":
            return {"url": url}
            
        return {"type": "http", "url": url}

    cmd = paths.mcp_command()
    base: dict[str, Any] = {"command": cmd[0], "args": cmd[1:]}
    if tid == "vscode":
        return {"type": "stdio", **base}
        
    if tid == "zed":
        return {"command": {"path": cmd[0], "args": cmd[1:], "env": {}}}
    return base


def _toml_section(spec_: dict[str, Any]) -> str:
    lines = [f"[mcp_servers.{MCP_SERVER_NAME}]"]
    if "url" in spec_:
        lines.append(f'url = "{spec_["url"]}"')
    else:
        lines.append(f'command = {json.dumps(spec_["command"])}')
        args = ", ".join(json.dumps(a) for a in spec_["args"])
        lines.append(f"args = [{args}]")
    return "\n".join(lines) + "\n"


def _install_toml(path: Path, payload: dict[str, Any]) -> tuple[str, str | None]:
    # shortcut: appends TOML section without updating existing entries; add tomlkit if full TOML editing is needed
    if path.exists() and path.stat().st_size:
        if MCP_SERVER_NAME in (_read_config(path).get("mcp_servers") or {}):
            return "already present - left unchanged", None
        bak = _backup(path)
        text = path.read_text(encoding="utf-8")
        with open(path, "a", encoding="utf-8") as fh:
            if not text.endswith("\n"):
                fh.write("\n")
            fh.write("\n" + _toml_section(payload))
        return "appended", bak

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_toml_section(payload), encoding="utf-8")
    return "created", None


def install(
    target_ids: list[str],
    transport: str = "stdio",
    path_overrides: dict[str, Path] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for tid in target_ids:
        meta = MCP_CLIENTS.get(tid)
        if not meta:
            results.append({"id": tid, "ok": False, "message": "unknown target"})
            continue

        cfg_path = (
            path_overrides[tid]
            if path_overrides and tid in path_overrides
            else paths.CLIENT_ROOTS[meta["root"]].joinpath(*meta["rel_path"])
        )
        payload = spec(tid, transport)
        try:
            if cfg_path.suffix == ".toml":
                note, bak = _install_toml(cfg_path, payload)
            else:
                data = _read_config(cfg_path)
                key = meta["key"]
                section = data.setdefault(key, {})
                if not isinstance(section, dict):
                    raise ValueError(f'"{key}" is not an object')
                bak = _backup(cfg_path)
                section[MCP_SERVER_NAME] = payload
                _write_json(cfg_path, data)
                note = "written"

            results.append(
                {
                    "id": tid,
                    "name": meta["name"],
                    "ok": True,
                    "path": str(cfg_path),
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
                    "path": str(cfg_path),
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
    return results


def remove(
    target_ids: list[str],
    path_overrides: dict[str, Path] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for tid in target_ids:
        meta = MCP_CLIENTS.get(tid)
        if not meta:
            continue

        cfg_path = (
            path_overrides[tid]
            if path_overrides and tid in path_overrides
            else paths.CLIENT_ROOTS[meta["root"]].joinpath(*meta["rel_path"])
        )
        if cfg_path.suffix == ".toml":
            # shortcut: manual TOML removal avoids fragile regex edits; add tomlkit if needed
            results.append(
                {
                    "id": tid,
                    "name": meta["name"],
                    "ok": False,
                    "message": f"remove the [mcp_servers.{MCP_SERVER_NAME}] block manually",
                }
            )
            continue

        try:
            data = _read_config(cfg_path)
            section = data.get(meta["key"])
            changed = isinstance(section, dict) and MCP_SERVER_NAME in section
            if changed:
                del section[MCP_SERVER_NAME]
                _write_json(cfg_path, data)
            results.append(
                {
                    "id": tid,
                    "name": meta["name"],
                    "ok": True,
                    "message": "removed" if changed else "not configured",
                }
            )
        except Exception as exc:
            results.append(
                {"id": tid, "name": meta["name"], "ok": False, "message": str(exc)}
            )
    return results
