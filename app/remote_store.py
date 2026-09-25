from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from types import SimpleNamespace

DEFAULT_STORE_URL = "https://br-silent-mud-b305z16x-workerstore.compute.c-4.ap-southeast-1.aws.neon.tech"
STORE_URL = os.getenv("REMOTE_STORE_URL", DEFAULT_STORE_URL).rstrip("/")


class RemoteStoreError(RuntimeError):
    pass


class RemoteNotFound(RemoteStoreError):
    pass


def enabled() -> bool:
    return bool(STORE_URL)


def _request(path: str, method: str = "GET", payload=None, manager_key: str = ""):
    url = STORE_URL + path
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    if manager_key:
        req.add_header("x-manager-key", manager_key)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise RemoteNotFound(body) from exc
        raise RemoteStoreError(f"Remote store HTTP {exc.code}: {body[:300]}") from exc
    except OSError as exc:
        raise RemoteStoreError(f"Remote store unavailable: {exc}") from exc


def _profile_obj(item: dict):
    data = dict(item)
    created = data.get("created_at")
    if isinstance(created, str):
        try:
            data["created_at"] = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            pass
    return SimpleNamespace(**data)


def validate_manager(manager_key: str) -> bool:
    try:
        result = _request("/manager/validate", manager_key=manager_key)
        return bool(result and result.get("ok"))
    except RemoteNotFound:
        return False


def health() -> bool:
    result = _request("/health")
    return bool(result and result.get("ok"))


def create_profile(payload: dict) -> int:
    result = _request("/profiles", method="POST", payload=payload)
    return int(result["id"])


def list_profiles(q: str, manager_key: str):
    path = "/profiles"
    if q.strip():
        path += "?" + urllib.parse.urlencode({"q": q.strip()})
    return [_profile_obj(x) for x in _request(path, manager_key=manager_key)]


def get_profile(profile_id: int, manager_key: str):
    return _profile_obj(_request(f"/profiles/{profile_id}", manager_key=manager_key))


def delete_profile(profile_id: int, manager_key: str):
    _request(f"/profiles/{profile_id}", method="DELETE", manager_key=manager_key)


def list_translations():
    return [SimpleNamespace(**x) for x in _request("/translations")]


def upsert_translation(category: str, vi: str, zh: str, manager_key: str):
    _request(
        "/translations",
        method="POST",
        payload={"category": category, "vi": vi, "zh": zh},
        manager_key=manager_key,
    )
