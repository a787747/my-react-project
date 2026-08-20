#!/usr/bin/env python3
"""PUT and activate the six reporting-surface workflows. Does not touch the 27 live graphs."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN_DIR = REPO / "n8n_workflows" / "route_guard_deferred"

TARGETS = {
    "all-evaluations.json": {
        "id": "j9YdW8LGzW5lvxgb",
        "allow_active": True,
        "activate": True,
    },
    "evaluation-details-by-user.json": {
        "id": "ZUDqYb0nWGGXLUnB",
        "allow_active": True,
        "activate": True,
    },
    "analytics.json": {
        "id": "i1rMW79I7GYb5iXm",
        "allow_active": True,
        "activate": True,
    },
    "manager-subordinates-matrix.json": {
        "id": "EyvFZJGDxQNL20tC",
        "allow_active": True,
        "activate": True,
    },
    "manage-criteria.json": {
        "id": "55BHbXWIS6igHHBT",
        "allow_active": True,
        "activate": True,
    },
    "update-admin-data.json": {
        "id": "CkxIyrEJBrc6V4Cv",
        "allow_active": True,
        "activate": True,
    },
}

FORBIDDEN_IDS = {
    "yQNNr0i4UBFNVgMv",  # evaluations-matrix
    "rSZcm0HDMUHLYk8W",  # score-correction
    "L0Zr7nVa8O5YWXd3",  # Auth Guard
}


def request(method: str, url: str, api_key: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"X-N8N-API-KEY": api_key, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {url} failed: {exc.code} {body[:800]}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n8n-url", default=os.environ.get("N8N_URL", "http://127.0.0.1:25678"))
    parser.add_argument("--api-key", default=os.environ.get("N8N_API_KEY", ""))
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("N8N_API_KEY is required")
    base = args.n8n_url.rstrip("/")
    for spec in TARGETS.values():
        if spec["id"] in FORBIDDEN_IDS:
            raise SystemExit(f"refusing to touch forbidden id {spec['id']}")
    results = []
    for filename, spec in TARGETS.items():
        wf_id = spec["id"]
        generated = json.loads((GEN_DIR / filename).read_text())
        live = request("GET", f"{base}/api/v1/workflows/{wf_id}", args.api_key)
        if live.get("name") != generated["name"]:
            raise SystemExit(f"{filename}: live name {live.get('name')!r} != {generated['name']!r}")
        if live.get("active") and not spec["allow_active"]:
            raise SystemExit(f"{filename}: refusing to replace an active workflow")
        payload = {
            "name": generated["name"],
            "nodes": generated["nodes"],
            "connections": generated["connections"],
            "settings": generated["settings"],
            "staticData": live.get("staticData"),
        }
        updated = request("PUT", f"{base}/api/v1/workflows/{wf_id}", args.api_key, payload)
        activated = updated.get("active")
        if spec["activate"] and not activated:
            request("POST", f"{base}/api/v1/workflows/{wf_id}/activate", args.api_key)
            updated = request("GET", f"{base}/api/v1/workflows/{wf_id}", args.api_key)
            activated = updated.get("active")
        results.append(
            {
                "id": wf_id,
                "name": updated.get("name"),
                "active": activated,
                "nodes": len(updated.get("nodes") or []),
                "updatedAt": updated.get("updatedAt"),
            }
        )
    print(json.dumps({"put": results}, indent=2))


if __name__ == "__main__":
    main()
