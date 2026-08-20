# Deferred Route Guard — Implementation Report

**Date:** 2026-08-19  
**Status:** Completed and deployed (inactive)  
**H1 campaign:** still draft. Launch set unchanged. Results work can start on these routes in September without a second guard pass.

## Verified baseline

The brief’s “~16 deferred API workflows” was checked against the live n8n export. The data routes are **10**. `API: Global CORS Handler` was left inactive and unguarded. `My workflow 10` was left alone.

| File / live id | Path | Roles enforced |
|---|---|---|
| evaluations-matrix `yQNNr0i4UBFNVgMv` | GET `api/admin/evaluations-matrix` | admin + c_level |
| All-evaluation `j9YdW8LGzW5lvxgb` | GET `api/admin/all-evaluations` | admin + c_level |
| evaluation-details-by-user `ZUDqYb0nWGGXLUnB` | GET `api/admin/evaluation-details-by-user` | admin + c_level |
| Analytics `i1rMW79I7GYb5iXm` | GET `api/analytics` | admin + c_level |
| Get Admin Data Fixed `uYy7zVKjgXx8zApC` | GET `get-admin-data` | admin + c_level |
| Manager Subordinates Matrix `EyvFZJGDxQNL20tC` | GET `api/manager-subordinates-matrix` | admin + c_level + manager; `manager_id` = actor only |
| Get Employee Self Review `H4T4EMYmJJ1jdT7Z` | GET `api/employee-self-review` | any authenticated role; actor only |
| Score Correction `rSZcm0HDMUHLYk8W` | POST `api/admin/score-correction` | admin + c_level + manager; level from identity, not body |
| Manage Criteria Admin V7 `55BHbXWIS6igHHBT` | POST `manage-criteria` | admin; save/delete 409 if a period is active |
| Update Admin Data `CkxIyrEJBrc6V4Cv` | POST `update-admin-data` | admin; 409 if a period is active |

Checked independently:

- 60 workflows, **25 active**, 28 registered webhooks. H1 id=2 `draft` / `is_active=false`.
- `EPE: Auth Guard` inactive, `updatedAt=2026-08-18T16:34:30.674Z`. Live GET bytes md5 `de58de075d66a621e832aac9a2dd3d14` before and after.
- Launch-set `updatedAt` values were snapshotted and **did not change**.
- `epe_2026`: 89 users, registered=1, evaluations=0, scores=0, corrections=0.
- Campaign not live (31 Aug). Write-proofs were safe.

## Implemented result

- Generator `scripts/build_route_guard_deferred.py` and payloads under `n8n_workflows/route_guard_deferred/`.
- Deployer `scripts/deploy_route_guard_deferred.py` (PUT only; refuses an active workflow).
- Static tests `tests/routeGuardDeferred.test.js` — 15/15. Existing H1 suite still 111/111.
- All 10 live graphs replaced. They stay **inactive**. The 25 launch workflows and the guard were not edited.
- Identity is `guard.identity` only. Client `evaluator_id`, `manager_id`, `subject_id`, and `correction_level` do not grant privilege.
- SQL shape, formulas, and success-body contracts were kept. Two generator defects found during proof were fixed before acceptance (see below). They are not data/formula changes.

## Protected-route evidence

`N/A` means the route has no extra capability/ownership dimension beyond the role column.

| Route | No token | Forged | Expired | Wrong role | HR | Ownership / rule | Valid |
|---|---:|---:|---:|---:|---:|---|---:|
| GET evaluations-matrix | 401 | 401 | 401 | 403 | 403 | N/A | 200 admin, 200 c_level |
| GET all-evaluations | 401 | 401 | 401 | 403 | 403 | N/A | 200 admin, 200 c_level |
| GET details-by-user | 401 | 401 | 401 | 403 | 403 | `user_id` is the dossier, not the actor | 200 admin, 200 c_level |
| GET analytics | 401 | 401 | 401 | 403 | 403 | N/A | 200 admin, 200 c_level |
| GET get-admin-data | 401 | 401 | 401 | 403 | 403 | N/A | 200 `{grades, settings}` |
| GET manager-subordinates-matrix | 401 | 401 | 401 | 403 | 403 | first-line manager 403 `OWNERSHIP_FORBIDDEN`; actor tree only | 200 admin, 200 c_level |
| GET employee-self-review | 401 | 401 | 401 | N/A | N/A | actor only; `subject_id` ignored | 200 |
| POST score-correction | 401 | 401 | 401 | 403 | 403 | first-line manager 403; admin/c_level → `c_level` | 200 |
| POST manage-criteria | 401 | 401 | 401 | 403 | N/A (c_level 403) | active-period freeze 409 | 200 get/save while draft |
| POST update-admin-data | 401 | 401 | 401 | 403 | N/A (c_level 403) | active-period freeze 409 | 200 no-op while draft |

H1 `POST /api/submit-evaluation` with `evaluation_source=c_level_direct` still returns **422 `SOURCE_NOT_SUPPORTED`**. Kept.

## Identity-conflict proofs

| Route | Token actor / client says | Verified result |
|---|---|---|
| manager-subordinates-matrix | admin 2 / `manager_id=18` | 200; tree is Alexander’s, not Bayram’s. Sample ids `35,22,57,19,…`. Akmyrat (1) absent. |
| manager-subordinates-matrix | c_level 18 / `manager_id=2` | 200; different set (`3,10,31,…` includes Alina, who sits under Bayram). Yelena (88) absent. |
| employee-self-review | employee 3 / `subject_id=2` | 200 `{has_self_review:false, evaluation_id:null, score:null, scores:{}, comments:{}}` — actor 3, not user 2 |
| score-correction | admin 2 / `evaluator_id=88`, `correction_level=mid_level`, subject 3, criteria 13, score 7 | DB row `evaluator_id=2, correction_level=c_level, period_id=2, score=7, subject=3` |
| score-correction | c_level 18 / `evaluator_id=1`, subject 4 | DB row `evaluator_id=18, correction_level=c_level, period_id=2, subject=4` |
| details-by-user | admin 2 / `user_id=1` | 200 success; dossier keys unchanged (`self_evaluation`, `manager_evaluations`, …) |

Akmyrat (manager 1, Alina’s first-line manager, not skip-level) received **403** on both the subordinates matrix and score-correction. 2026 has **zero** users whose skip-level (`manager.manager`) has role `manager`, so a live `mid_level` **200** cannot be proven without changing the org. Not changed.

## Freeze-rule proofs

H1 was set `active` / `status='active'` only for these three calls, then returned to `draft` / inactive.

| Call | Result |
|---|---|
| POST manage-criteria `action=save` (criterion 1, same payload as GET) | 409 `ACTIVE_PERIOD_EXISTS` |
| POST manage-criteria `action=delete` criterion 1 | 409 `ACTIVE_PERIOD_EXISTS` — row not deleted |
| POST update-admin-data grades 1 / 10 at current coefficients | 409 `ACTIVE_PERIOD_EXISTS` |

After rollback, coefficients were still `1.00` and `0.30`. GET manage-criteria still returned 8 criteria including id=1 «Стратегическая значимость роли».

## Generator defects found during proof (fixed before leaving the routes inactive)

1. f-string `={{ … }}` collapsed to `={ … }`. Postgres executed the expression text and the webhook returned empty 200. Wrapper restored; test asserts every dynamic query starts with `={{`.
2. Analytics was missing `Build Response → Respond`. n8n then answered 500 `No Respond to Webhook node found`. Connection restored; test asserts every webhook can reach a Respond node.

Neither defect touched formulas or the 25 launch workflows.

## Known data defects — recorded, not fixed

September logic work. Seen in the legacy SQL that was copied unchanged:

- evaluations-matrix, all-evaluations, analytics, details-by-user: **no period filter**.
- matrix / all-evaluations `manager_score`: evaluator **role**, not `evaluation_source`. An upward score from a manager-role evaluator can surface as manager_score.
- all-evaluations: row multiplication from the `manager_evaluations_given` join.
- details-by-user: `detail_type` is accepted and **ignored** (both subject and evaluator queries always run).
- employee-self-review SQL still uses `evaluation_type='self'` (H1 writes `is_self_evaluation`). Empty shape while H1 is draft. Not rewritten.
- Live `score_corrections.period_id` is already `NOT NULL` with unique `(subject_id, criteria_id, correction_level, period_id)`. The guarded upsert uses that live key and the newest non-closed period (H1 id=2). **No new column.** This is schema alignment, not the September period-model brief.

## Final workflow activation list

Same 25 names as at the start:

```text
API: Admin Get Users Data
API: Admin Save User (GUI Mode)
API: Auth Login (No Params)
API: Check Evaluated V2
API: Check Self Review
API: Create Invite
API: Get Criteria With Levels
API: Get Employees (Smart Role Based)
API: Get Evaluation Details FIXED
API: Get My Manager
API: Get Score Coefficients
API: HR Evaluation Status
API: Manage Periods
API: My Evaluation History (Received)
API: My Profile V5 (Fixed Empty)
API: Register
API: Request Password Reset
API: Reset Password
API: Save Score Coefficients
API: Send Verification Code
API: Submit Evaluation
API: Submit Self Review
API: Update Evaluation WITH PERIOD
API: Verify Code
API: Verify Invite
```

Deferred 10: inactive. CORS handler: inactive. Guard: inactive, md5 unchanged.

## Cleanup proof

```text
users=89
registered=1
evaluations=0
evaluation_scores=0
score_corrections=0
auth_sessions=0
H1=id 2, draft, inactive
invite id=4 unused (43-char)
workflows=60
active_workflows=25
registered_webhooks=28
EPE: Auth Guard md5=de58de075d66a621e832aac9a2dd3d14
launch updatedAt changed=0
```

Proof sessions and the two pre-existing Alexander browser sessions were deleted so the brief’s `sessions=0` holds. That logs the live admin tab out.

## Backup and archive proof

Artifacts in `backups/2026-08-20-route-guard-deferred/` (gitignored) and `/root/backups/epe/2026-08-20-route-guard-deferred/`.

| Artifact | SHA-256 / result |
|---|---|
| Pre-change `epe_2026_before.dump` | `210f2e4221a4cbe377724dff679b419ab00c7fa6976beb8939a07cbb60d7316a` (73464) |
| Pre-change `n8n_public_before.dump` | `1925cffefb54168f4fd51a55d7cc1c6429c48dfa2fe98be72ed90ff01e5c8be4` (477252) |
| Final `epe_2026_after.dump` | `6c91dd1551056cdaf43639ada91f720bf01ed2637a45ac5c21224a10e71cca57` (73313) |
| Final `n8n_public_after.dump` | `0ff4ed250bea30c5bfc600fd9c7ac6c981e04d7a5321223b7d3c32a37cf4d74b` (516210) |
| Restore before | users=89, evals=0; workflows=60, active=25 |
| Restore after | users=89, evals=0, corr=0, sess=0, H1 draft, registered=1; workflows=60, active=25 |
| 2025 fingerprint before / after | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e`, unchanged |

`epe_2026` custom-format SHA moved on dump-header timestamps and the proof-time `score_corrections` sequence bump (rows deleted; count=0). n8n public SHA moved because the 10 deferred graphs were PUT and because `execution_entity` / `insights_raw` grew during proof (live `executions=113`, `insights_raw=396`). Workflow count stayed 60.

No schema change.

## Surface for Alexander — do not resolve silently

### 1. `employee-self-review`

No React call site. `EMPLOYEE_SELF_REVIEW` exists only in `src/config/api.js`. Self-review details in TeamView / AdminUsers use `check-self-review` (already actor-only from H1).

**Done this brief:** guarded, not deleted.  
**Ask:** keep the guarded workflow for September, or delete it?

### 2. `get-admin-data`

No frontend call. Grades/settings are not read through this path today (`update-admin-data` is the write path for grade coefficients).

**Done this brief:** guarded, not deleted.  
**Ask:** keep, or delete?

### 3. Who sees company-wide reporting

Verified UI:

- Sidebar analytics / all-evaluations / evaluations-matrix: `canViewAnalytics` = **admin + c_level** (`ADMIN_ROLES`).
- `AdminRoute` still lets **HR** open `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix` by URL.
- `details-by-user` is also called from TeamView (managers) and AdminUsers (HR) modals. TeamView already cannot load the user list (`useUsers` → guarded `admin-users-data` is admin-only). When this route is activated in September, those modals will **403** for HR and managers.

**Implemented APIs:** admin + c_level only.  
**Recommendation:** keep admin + c_level. HR already has `hr/evaluation-status`. Company-wide scores are a calibration surface, not an HR-ops surface.  
**Ask:** confirm admin+c_level, or add HR to all-evaluations / analytics / details-by-user?

### 4. `mid_level` score-correction

Archive `postgres.performance_db` (2025), three rows:

1. **mid_level:** Jahan Hojayeva (then manager 172) → Tishkina. Jahan was Tishkina’s manager’s manager.
2. **c_level ×2:** Aleksandr Petrosov (**admin** 1) → Alp Arslan, Valeriya.

So 2025 already had **admin writing `c_level`**, not “c_level role only”. The UI `ADMIN_ROLES` matches that.

**Implemented:** admin or c_level → stored level `c_level` (client `correction_level` ignored). `mid_level` only if the actor **is** the subject’s manager’s manager. First-line manager → 403.  
**Ask:** keep this hierarchy rule, or restrict `c_level` writes to the c_level role only (which would reject Alexander, against 2025 practice)?

### 5. `c_level_direct` submit

Guarding the matrix makes C-level submit **technically** possible again. Live submit still returns 422.

**Architect’s pick, implemented:** keep 422 until the September results work. Re-enable with period filters and `evaluation_source` on the matrix, not now.

## Decision gate

None of the five items above was resolved silently. The routes are guarded and inactive so H1 launch is unchanged. September activation of these 10 is a separate ops step after the five answers.
