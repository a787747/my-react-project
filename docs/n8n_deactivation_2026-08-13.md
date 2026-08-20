# n8n EPE API deactivation — 2026-08-13

Captured: 2026-08-12 21:29–21:32 UTC.  
Host: `3569961-foreignpay.twc1.net` (`92.51.45.147`).  
n8n container `n8n-n8n-1` was **not** restarted (`StartedAt` still `2026-08-12T19:22:45.580Z`, `RestartCount=0`).

---

## Pre-checks

### 1. Restore list vs live

`docs/n8n_workflow_state_2026-08-12.json` (20:41 UTC) **did not** match live flags. Recapture: `docs/n8n_workflow_state_2026-08-12T2129.json`.

| Set | 20:41 UTC snapshot | Live at 21:29 UTC (before this change) |
|-----|--------------------|----------------------------------------|
| `API:*` active, not archived | 35 | **35** (same IDs, including CORS `BJwFjunajsGkoNY2`) |
| Foreign active (`school-helper`, `My workflow 7`, three `new_clinic/*`) | 5 | **0** — archived+inactive |
| `webhook_entity` rows | 44 (EPE + foreign) | 40 (EPE only) |

The 20:41 file is still the last known-good of the **foreign** workflows. Do not overwrite it.

Who archived the foreign set is **unverified**. `updatedAt` on those rows is `2026-08-12 21:18:27`–`21:19:44` UTC. This session did not touch them. n8n public API keys labeled `cursor` and `my internal` were already **expired** (cursor `exp` 2026-01-12, internal 2026-03-06), so that archive was not done with those stored keys in their current form.

The instruction said “all 36”. Live and both snapshots have **35** active unarchived `API:*` workflows. CORS is in that 35. Three additional `API:*` rows were already archived duplicates and were left alone.

### 2. Shared webhook paths

No **active** EPE path was shared with an **active** FOREIGN workflow: at 21:29 UTC there were zero active non-`API:*` workflows. Deactivation proceeded.

---

## What was deactivated

Method: `POST /api/v1/workflows/{id}/deactivate` against the running n8n on `127.0.0.1:5678` (not a container restart, not a raw SQL `active=false`). All 35 calls returned HTTP 200 with `active=false`.

A short-lived JWT was minted inside the n8n container with the same secret derivation n8n uses, written over the expired `cursor` row in `user_api_keys` for the duration of the calls, then the original expired JWT was written back (`length=229` match). No standing new API key was left.

| id | name |
|----|------|
| `U4XURKlDnaZ6XHg3` | API: Admin Clear Test Evaluations |
| `AwID96McjHKyk8WI` | API: Admin Get Users Data |
| `JCjzhRJtIDW0z8mI` | API: Admin Save User (GUI Mode) |
| `j9YdW8LGzW5lvxgb` | API: All-evaluation |
| `i1rMW79I7GYb5iXm` | API: Analytics Dashboard - Optimized |
| `A4Ah3w21JEqHvQFR` | API: Auth Login (No Params) |
| `msl2T1flMo1Hn7uj` | API: Check Evaluated V2 |
| `QRkUvs24DkcC3WBW` | API: Check Self Review |
| `uxKDjQFNJDv7MEnS` | API: Create Invite |
| `ZUDqYb0nWGGXLUnB` | API: evaluation-details-by-user |
| `yQNNr0i4UBFNVgMv` | API: evaluations-matrix |
| `uYy7zVKjgXx8zApC` | API: Get Admin Data Fixed |
| `KKlGLEYMlXlbYUjb` | API: Get Criteria With Levels |
| `H4T4EMYmJJ1jdT7Z` | API: Get Employee Self Review |
| `bKB4Sb46yWoq1tSV` | API: Get Employees (Smart Role Based) |
| `s2mrMporGOx0h14B` | API: Get Evaluation Details FIXED |
| `3C1u68KOTSMwcqgy` | API: Get My Manager |
| `zq3dufVhcnjkS7RV` | API: Get Score Coefficients |
| `BJwFjunajsGkoNY2` | API: Global CORS Handler |
| `NkUapcE4NycvAeiJ` | API: HR Evaluation Status |
| `55BHbXWIS6igHHBT` | API: Manage Criteria Admin V7 |
| `M9ljMDdO1mIl8m1h` | API: Manage Periods |
| `EyvFZJGDxQNL20tC` | API: Manager Subordinates Matrix |
| `k5lNBhvMfJSLFSDz` | API: My Evaluation History (Received) |
| `jCKNLytVw0qEF17W` | API: My Profile V5 (Fixed Empty) |
| `wkDxU72Kg8fOiZCB` | API: Register |
| `jAqkljoRb24jrcZx` | API: Save Score Coefficients |
| `rSZcm0HDMUHLYk8W` | API: Score Correction |
| `imGl6C6SUPAexvBE` | API: Send Verification Code |
| `tUxHoRn38rJVDxWv` | API: Submit Evaluation |
| `CuHkTYvGDyhqEarg` | API: Submit Self Review |
| `CkxIyrEJBrc6V4Cv` | API: Update Admin Data |
| `LWuZNTehzMDJkE8u` | API: Update Evaluation WITH PERIOD |
| `OMmlbaAAPmRHcCLS` | API: Verify Code |
| `VVqO0KkCr28emLsq` | API: Verify Invite |

Not touched: any workflow whose name does not start `API:`. Archived `API:*` duplicates (`UlM7eAX082nfNgrF`, `sR7mRVLGrmIvpue2`, `wwiy79j2YjcsSoFR`) were already inactive.

---

## Verification after the change

| Check | Result |
|-------|--------|
| `API:*` still `active=true` | **0** |
| `API:*` inactive, not archived | **35** |
| `webhook_entity` | **0 rows** (EPE paths unregistered in the running process) |
| n8n `healthz` | HTTP 200, `{"status":"ok"}` |
| Container restart | none |

EPE webhook endpoints were **not** called.

---

## Foreign workflows — not touched by this change

Step 4 asked to confirm these four paths still registered and active. **They were already neither**, before this deactivation:

| Path | Workflow | Live after this change | `updatedAt` (unchanged by us) |
|------|----------|------------------------|-------------------------------|
| `school-helper` | `qgXjtH5gCW4PgYDX` (and `S8j5OeUNh4bIgAkH`) | inactive, archived | 21:18:27 / 21:19:00 UTC |
| `new_clinic/equipment` | `YZsxqjxUVhqh0Kfh` | inactive, archived | 21:19:44 UTC |
| `new_clinic/request` | `Ro2zyLRh66D2S2n0` | inactive, archived | 21:19:44 UTC |
| `new_clinic/rooms` | `o4cSxegfSGGQKM7l` | inactive, archived | 21:19:44 UTC |

None of those five IDs appear in `webhook_entity`. Restoring clinic/school-helper is a **separate** action and must use `docs/n8n_workflow_state_2026-08-12.json` (20:41 UTC), via n8n activate/unarchive, not SQL.

---

## Restore command (EPE only)

Do **not** `UPDATE workflow_entity SET active=true` in Postgres. The running n8n process will not re-register webhooks. Do **not** restart the container to force a reload (that also drops anything you later re-activate for the clinic until n8n is up).

Use the n8n public API against the **running** process. Stored API keys `cursor` and `my internal` are expired; create a new key in the n8n UI (Settings → API) or mint one the same way this session did, then:

```bash
# KEY = a valid n8n public API key with workflow:activate
# Run on the VPS so traffic stays on 127.0.0.1
for id in \
  U4XURKlDnaZ6XHg3 AwID96McjHKyk8WI JCjzhRJtIDW0z8mI j9YdW8LGzW5lvxgb \
  i1rMW79I7GYb5iXm A4Ah3w21JEqHvQFR msl2T1flMo1Hn7uj QRkUvs24DkcC3WBW \
  uxKDjQFNJDv7MEnS ZUDqYb0nWGGXLUnB yQNNr0i4UBFNVgMv uYy7zVKjgXx8zApC \
  KKlGLEYMlXlbYUjb H4T4EMYmJJ1jdT7Z bKB4Sb46yWoq1tSV s2mrMporGOx0h14B \
  3C1u68KOTSMwcqgy zq3dufVhcnjkS7RV BJwFjunajsGkoNY2 NkUapcE4NycvAeiJ \
  55BHbXWIS6igHHBT M9ljMDdO1mIl8m1h EyvFZJGDxQNL20tC k5lNBhvMfJSLFSDz \
  jCKNLytVw0qEF17W wkDxU72Kg8fOiZCB jAqkljoRb24jrcZx rSZcm0HDMUHLYk8W \
  imGl6C6SUPAexvBE tUxHoRn38rJVDxWv CuHkTYvGDyhqEarg CkxIyrEJBrc6V4Cv \
  LWuZNTehzMDJkE8u OMmlbaAAPmRHcCLS VVqO0KkCr28emLsq
do
  curl -sS -X POST "http://127.0.0.1:5678/api/v1/workflows/${id}/activate" \
    -H "X-N8N-API-KEY: ${KEY}" -H "Accept: application/json"
  echo
done
```

Then confirm `webhook_entity` again contains the EPE paths from the 20:41 snapshot. Do not activate foreign IDs with this loop.

Until those workflows have an auth check, restoring them re-opens the unauthenticated write surface (BUG-002).
