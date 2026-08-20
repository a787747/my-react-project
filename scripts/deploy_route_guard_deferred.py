#!/usr/bin/env python3
"""PUT generated deferred workflows onto live n8n. Does not activate them."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN_DIR = REPO / "n8n_workflows" / "route_guard_deferred"

LIVE_IDS = {
    "evaluations-matrix.json": "yQNNr0i4UBFNVgMv",
    "all-evaluations.json": "j9YdW8LGzW5lvxgb",
    "evaluation-details-by-user.json": "ZUDqYb0nWGGXLUnB",
    "analytics.json": "i1rMW79I7GYb5iXm",
    "get-admin-data.json": "uYy7zVKjgXx8zApC",
    "manager-subordinates-matrix.json": "EyvFZJGDxQNL20tC",
    "employee-self-review.json": "H4T4EMYmJJ1jdT7Z",
    "score-correction.json": "rSZcm0HDMUHLYk8W",
    "manage-criteria.json": "55BHbXWIS6igHHBT",
    "update-admin-data.json": "CkxIyrEJBrc6V4Cv",
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
    results = []
    for filename, wf_id in LIVE_IDS.items():
        generated = json.loads((GEN_DIR / filename).read_text())
        live = request("GET", f"{base}/api/v1/workflows/{wf_id}", args.api_key)
        if live.get("name") != generated["name"]:
            raise SystemExit(f"{filename}: live name {live.get('name')!r} != {generated['name']!r}")
        if live.get("active"):
            raise SystemExit(f"{filename}: refusing to replace an active workflow")
        payload = {
            "name": generated["name"],
            "nodes": generated["nodes"],
            "connections": generated["connections"],
            "settings": generated["settings"],
            "staticData": live.get("staticData"),
        }
        updated = request("PUT", f"{base}/api/v1/workflows/{wf_id}", args.api_key, payload)
        results.append(
            {
                "id": wf_id,
                "name": updated.get("name"),
                "active": updated.get("active"),
                "nodes": len(updated.get("nodes") or []),
                "updatedAt": updated.get("updatedAt"),
            }
        )
    print(json.dumps({"put": results}, indent=2))


if __name__ == "__main__":
    main()
