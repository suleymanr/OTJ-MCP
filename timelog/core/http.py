from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from timelog.config import HTTP_TIMEOUT_S, UA


class ServiceError(RuntimeError):
    pass


class AuthRequired(ServiceError):
    pass


def err_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def subprocess_flags() -> int:
    return 0x08000000 if os.name == "nt" else 0


def request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = HTTP_TIMEOUT_S,
    auth_message: str = "Session rejected. Reconnect in the app.",
) -> tuple[int, str, Any, bytes]:
    req_headers = {"User-Agent": UA}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.geturl(), resp.headers, resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        if exc.code in (401, 403):
            raise AuthRequired(f"{auth_message} ({body[:160]})" if body else auth_message) from None
        raise ServiceError(f"HTTP {exc.code} on {method} {url}: {body[:200]}") from None
    except Exception as exc:
        raise ServiceError(err_text(exc)) from None


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: Any = None,
    data: bytes | None = None,
    timeout: int = HTTP_TIMEOUT_S,
    auth_message: str = "Session rejected. Reconnect in the app.",
) -> Any:
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    _, _, _, raw = request(
        url,
        method=method,
        headers=req_headers,
        data=data,
        timeout=timeout,
        auth_message=auth_message,
    )
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise ServiceError(f"Unexpected non-JSON response from {url}") from None
