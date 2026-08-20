# C-level direct enable — Implementation Report

**Date of work:** 2026-08-19 (UTC) / 2026-08-20 (Ashgabat)  
**Status:** Completed and deployed  
**H1 campaign:** still draft. `c_level_direct` writes are accepted on the live submit route when a period is active. The evaluations-matrix read route is active.

Alexander decided C-level management may directly influence an employee’s evaluation via the admin matrix for H1. That required editing the **active** launch route `API: Submit Evaluation` (it returned 422 `SOURCE_NOT_SUPPORTED` for `source=c_level_direct`) and activating the matrix read route the UI already calls. Two unused inactive workflows were deleted. Score-correction and the other deferred routes stayed inactive.

---

## Verdict

H1 can run with `c_level_direct` from **admin and c_level**. Manager / upward submit proofs still pass. Formula and response contract of submit-evaluation are unchanged: stored `calculated_score` is `AVG(score_val::numeric)` of the posted rows; client `final_score` is ignored.

Two items are surfaced below, not resolved silently: whether admin should remain a writer, and what the current matrix UI can still get wrong about period / evaluator **display**.

---

## Verified baseline (live, before change)

Checked against the live n8n API and `epe_2026.performance_db`, not against a prior report.

| Check | Live |
|---|---|
| Workflows | 60 total, **25 active**, 28 webhooks |
| H1 id=2 | `draft` / `is_active=false` |
| Users | 89; registered=1 (Alexander id=2); evaluations=0; sessions=1 (pre-existing Alexander JWT) |
| Invite id=4 | unused, 43-char |
| `EPE: Auth Guard` `L0Zr7nVa8O5YWXd3` | inactive; `updatedAt=2026-08-18T16:34:30.674Z`; GET md5 `de58de075d66a621e832aac9a2dd3d14` |
| Submit Evaluation `tUxHoRn38rJVDxWv` | active; `c_level_direct` → 422 `SOURCE_NOT_SUPPORTED`; insert already used `AVG(score_val::numeric)` |
| evaluations-matrix `yQNNr0i4UBFNVgMv` | **inactive**; guard already admin + c_level |
| Get Employee Self Review `H4T4EMYmJJ1jdT7Z` | inactive |
| Get Admin Data Fixed `uYy7zVKjgXx8zApC` | inactive |
| 2025 archive | fingerprint `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e` |

2025 `postgres.performance_db` evaluations: 120 manager + 64 self (`source=manager`, `is_self_evaluation=true`) + 50 subordinate. **Zero** `c_level_direct` rows.

2025 `score_corrections` (three rows):

| evaluator | level | subject |
|---|---|---|
| Jahan Hojayeva (manager 172) | `mid_level` | Shasenem Tishkina |
| Aleksandr Petrosov (**admin** 1) | `c_level` | Alp Arslan Mametnazar |
| Aleksandr Petrosov (**admin** 1) | `c_level` | Valeriya Ruhlyadko |

So 2025 C-level *influence* was **score_corrections at `correction_level='c_level'` written by admin**, not `evaluations.evaluation_source='c_level_direct'`. The 2025 frontend already POSTed `evaluation_source: 'c_level_direct'` from the matrix; those writes never landed as evaluation rows.

Read-only emails (import source of truth): `cem@`, `hemra@`, `mekan@sedamedical.com`. They are in H1 scope and `can_be_evaluated=false`. The three C-level users with `can_evaluate=true` in 2026 are Alexander (admin 2) and Bayram Urayev (c_level 18). Cem / Hemra / Mekan have `can_evaluate=false`.

---

## What changed

### 1. `API: Submit Evaluation` — mechanism (not a diff recap)

Only this **active** launch workflow was edited (`tUxHoRn38rJVDxWv`). Generator: `scripts/build_route_guard_workflows.py` (`SUBMIT_EVAL_VALIDATE`). Repo export: `n8n_workflows/route_guard_h1/submit-evaluation.json` and `n8n_workflows/API_ Submit Evaluation.json`. Live `updatedAt` `2026-08-19T11:52:23.934Z` → `2026-08-19T19:43:38.525Z`.

**Build Insert SQL was not touched.** `calculated_score` is still:

```sql
(SELECT AVG(score_val::numeric) FROM score_rows)
```

Evaluator in the INSERT is still `guard.identity.id` (the token actor). Client `evaluator_id` and `final_score` are still ignored. Period binding is still: both actor and subject must be `is_in_scope` on the single period with `is_active=true AND status='active'`. Duplicate key is still `(subject, evaluator, source, period)`.

What *did* change in `Validate Evaluation`:

1. Removed the 422 `SOURCE_NOT_SUPPORTED` branch. Allowed sources are `manager`, `subordinate`, `c_level_direct`. Anything else is still 422 `INVALID_SOURCE`.
2. After source parse: if `source === 'c_level_direct'` and `guard.identity.role` is not `c_level` or `admin` → **403 `ROLE_FORBIDDEN`**. Employee, manager, and HR all hit this before the SQL relation check.
3. Comment `// Ignore body.evaluator_id` — evaluator remains the token actor (already true for manager/subordinate).
4. `relationFilter` is now three-way:
   - `manager`: `subj.manager_id = actor AND subj.can_be_evaluated`
   - `subordinate`: `actor.manager_id = subject AND can_be_evaluated AND subject role not c_level/admin`
   - `c_level_direct`: `actor.role IN ('c_level','admin') AND subj.can_be_evaluated AND lower(subj.email) NOT IN (cem, hemra, mekan)`

A failed relation or scope join still returns 403 `SCOPE_MISMATCH`. Guard input is still `required_capability: can_evaluate` (not emptied). Alexander is in H1 scope and `can_evaluate=true`, so an admin submit does not need a weaker actor-scope join.

No other active workflow was PUT. The H1 generator can rewrite sibling JSON under `n8n_workflows/route_guard_h1/`; only submit-evaluation was deployed.

Static test added: `submit-evaluation accepts c_level_direct for admin or c_level only`. H1 suite **99/99**. Combined with deferred static tests: **114/114**.

### 2. Deletions

n8n public dump taken **before** delete. Precedent: clear-test-evaluations.

| id | name | Before | After |
|---|---|---|---|
| `H4T4EMYmJJ1jdT7Z` | API: Get Employee Self Review | inactive | GET **404** |
| `uYy7zVKjgXx8zApC` | API: Get Admin Data Fixed | inactive | GET **404** |

Workflow snapshot before→after: those two ids gone; no other id disappeared. They were not in the launch set of 25.

### 3. Activation

| id | name | Before | After |
|---|---|---|---|
| `yQNNr0i4UBFNVgMv` | API: evaluations-matrix | inactive | **active** (`updatedAt=2026-08-19T19:43:39.242Z`) |

Guard on the matrix was already admin + c_level. SQL, formulas, and response shape were not edited. Known display defects (no `period_id` in the SQL, `manager_score` by evaluator role) were not touched.

Deferred that **stayed inactive** (live GET after deploy):

- All-evaluation `j9YdW8LGzW5lvxgb`
- evaluation-details-by-user `ZUDqYb0nWGGXLUnB`
- Analytics `i1rMW79I7GYb5iXm`
- Manager Subordinates Matrix `EyvFZJGDxQNL20tC`
- **Score Correction** `rSZcm0HDMUHLYk8W`
- Manage Criteria Admin V7 `55BHbXWIS6igHHBT`
- Update Admin Data `CkxIyrEJBrc6V4Cv`

`EPE: Auth Guard` GET md5 after = `de58de075d66a621e832aac9a2dd3d14` (same as before). `updatedAt` still `2026-08-18T16:34:30.674Z`.

---

## Active set

Previous launch set **25**, minus nothing from that 25, plus `API: evaluations-matrix`. The two deletions were inactive, so they do not change the active count.

**26 active** (live GET, restore of `n8n_public_after.dump` agrees):

```text
API: Admin Get Users Data
API: Admin Save User (GUI Mode)
API: Auth Login (No Params)
API: Check Evaluated V2
API: Check Self Review
API: Create Invite
API: evaluations-matrix
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

Workflows total **58**. Registered webhooks **29** (was 28; matrix path registered on activate).

---

## Proofs

Public origin `https://epe.sedamedical.com`. H1 was set `active` / `is_active=true` only for write proofs and the browser pass, then returned to `draft` / inactive. Tokens minted for admin=2, c_level=18, manager=1, employee=3, hr=52. Evidence: `backups/2026-08-20-clevel-direct/submit_proofs.json`.

### Auth (all sources share the same webhook)

| Case | Result |
|---|---:|
| submit no token | 401 |
| submit forged JWT | 401 |
| submit expired JWT | 401 |
| `c_level_direct` no token | 401 |
| `c_level_direct` forged | 401 |
| `c_level_direct` expired | 401 |
| `c_level_direct` employee (Alina 3) | 403 `ROLE_FORBIDDEN` |
| `c_level_direct` manager (Akmyrat 1) | 403 `ROLE_FORBIDDEN` |
| `c_level_direct` hr (Liya 52) | 403 `ROLE_FORBIDDEN` (extra to the brief; same role gate) |

### Relation / scope rejects (evaluation count stayed 0 through this block)

| Case | Result |
|---|---|
| `c_level_direct` subject Aysoltan Esenova 31 (out of H1 scope) | 403 `SCOPE_MISMATCH` |
| `c_level_direct` subject Cem Durukan 21 (read-only) | 403 `SCOPE_MISMATCH` |
| manager 1 → subject 22 (outside graph) | 403 `SCOPE_MISMATCH` |
| manager 1 → Esenova 31 | 403 `SCOPE_MISMATCH` |
| upward 1 → Bayram 18 (C-level) | 403 `SCOPE_MISMATCH` |

### Identity conflict and valid writes

| Case | Token actor / body `evaluator_id` | HTTP | Stored row `eval,subj,source,period,score` |
|---|---|---:|---|
| manager → Alina | 1 / 88 | 200 | `1,3,manager,2,7.00` |
| upward → Akmyrat | 3 / 88 | 200 | `3,1,subordinate,2,8.00` |
| `c_level_direct` admin → Asadbek | 2 / 18 | 200 | `2,10,c_level_direct,2,7.00` |
| `c_level_direct` Bayram → Halykberdi | 18 / 2 | 200 | `18,39,c_level_direct,2,6.00` |
| duplicate manager 1→3 | — | 409 `DUPLICATE_EVALUATION` | unchanged |

Formula check on those rows (client `final_score` was 1 on the manager call):

- manager grades 6 / 8 / 7 → stored **7.00** (`AVG`)
- `c_level_direct` admin grades 6 / 8 → stored **7.00**
- `c_level_direct` Bayram grades 5 / 7 → stored **6.00**

Same `AVG` node as manager. Period on every successful row was **2** (the then-active H1). Evaluator on every row was the token actor, not the body `evaluator_id`.

### Matrix read + score-correction left dark

| Call | Result |
|---|---|
| GET `api/admin/evaluations-matrix` admin | 200, 88 rows |
| GET same, c_level | 200 |
| GET same, employee | 403 |
| POST `api/admin/score-correction` | **404** webhook not registered |

88 rows = `WHERE u.role != 'admin'` (Alexander excluded as a subject). Not a period filter.

---

## Browser check as Alexander

Origin `https://epe.sedamedical.com/admin/evaluations-matrix`.

The Keychain item `EPE auth test password reset 2026-08-18` returned 401 on live login (`Неверный email или пароль`). Failed attempts were deleted so Alexander was not locked. The tab was then given a minted JWT for `sub=2` (jti `c9750982-a263-4d8e-8894-1b823480d11a`) plus the live user object. This is Alexander’s identity, not a password-form walk.

Observed:

- Heading «Матрица оценок». Counter **«Показано: 88 из 88»**. No period filter in `MatrixFilters.jsx`.
- Orange C-level star on every remaining row (including out-of-scope, read-only, and other C-level subjects).
- Click Shasenem Tishkina star → modal «👑 C-level оценка» / Shasenem. Default sliders 5 / 5 (criteria 1 and 10).
- Save → `POST /webhook/api/submit-evaluation` (~279 ms) → DB row `evaluator=2, subject=79, source=c_level_direct, period=2, score=5.00`. Browser alert «C-level оценка сохранена!».
- Screenshot: `backups/2026-08-20-clevel-direct/browser-matrix-after-submit.png`.

That browser row was deleted with the other proof writes.

---

## Surface for Alexander — do not resolve silently

### 1. May admin submit `c_level_direct`, or only role `c_level`?

**What 2025 stored:** no `c_level_direct` evaluation rows. Admin Aleksandr Petrosov (then user id=1, role=`admin`) wrote two `score_corrections` at `correction_level='c_level'` (Alp Arslan, Valeriya). Jahan (manager) wrote the one `mid_level` row.

**What 2025 UI already sent:** `useEvaluationsMatrix.js` POSTed `evaluation_source: 'c_level_direct'` and `evaluator_id: user.id`. Those inserts were not persisted as evaluation rows in the archive.

**What this brief implemented:** both `admin` and `c_level` may submit `c_level_direct`. Evaluator is always the token actor. That matches 2025 *who acted at C-level*, via a different write path (evaluation row instead of correction row).

If Alexander wants only role `c_level` (Bayram today; Cem/Hemra/Mekan cannot evaluate), say so — one role check to drop `admin`. Cost of leaving it: Alexander can write C-level ratings from the matrix, as he did in December via corrections.

### 2. Can the current matrix UI land a submit on the wrong period or evaluator?

**Wrong evaluator — no, on the write path.** The page sends `evaluator_id: user.id` from React / localStorage. The server ignores it and stores `guard.identity.id`. Identity-conflict proofs above: body said 88 / 18 / 2; rows stored 1 / 3 / 2 / 18.

**Wrong period — no, on the write path.** The page does **not** send `period_id`. The server binds to the single `is_active AND status='active'` period. Today that can only be H1 (Annual 2025 is `closed`; activate refuses closed). A submit cannot write a client-chosen period.

**Display / operator risk — yes, not fixed:**

1. Matrix SQL has **zero** `period_id` predicates (`n8n_workflows/route_guard_deferred/evaluations-matrix.json`). Today `epe_2026` has no 2025 evaluation rows, so the 88 cells are empty-or-H1 only. If 2025 scores were ever copied into `epe_2026`, sliders would initialise from mixed-period `c_level_score` (`CLevelEvaluationModal` uses `c.c_level_score || 5`) while submit still wrote the active period.
2. Tooltip says «Изменить C-level оценку». The modal always **submit**, never `update-evaluation`. A second save for the same actor+subject+source+period is **409**. The UI title does not say that.
3. Stars are clickable for Esenova, Cem, other C-level, etc. Server 403s. Not filtered in the table.
4. Score-correction UI is still on the page (click a score cell). Route inactive → 404. Not activated.
5. No period selector. Operator cannot pick H1 vs anything else because the control does not exist.

None of (1)–(5) was changed. September work.

---

## Cleanup

```text
DELETE evaluations          → 5 (4 API writes + 1 browser)
DELETE score_corrections    → 0
DELETE auth_sessions        → 7 (pre-existing Alexander + proof actors + minted browser)
DELETE auth_login_attempts  → 0
DELETE email_verification_codes → 0
H1 id=2                     → draft, is_active=false
```

End state, live and restore-verified from `epe_2026_after.dump`:

```text
users=89
registered=1
evaluations=0
evaluation_scores=0
score_corrections=0
auth_sessions=0
H1=id 2, draft, inactive
invite id=4 unused (43-char)
workflows=58
active_workflows=26
registered_webhooks=29
EPE: Auth Guard md5=de58de075d66a621e832aac9a2dd3d14
score-correction active=false
```

Cleanup deleted Alexander’s sessions so `sessions=0` holds. That logs a live admin tab out.

---

## Backup and archive proof

Artifacts in `backups/2026-08-20-clevel-direct/` (gitignored) and `/root/backups/epe/2026-08-20-clevel-direct/`. Dumps restore-tested into throwaway databases, then dropped.

| Artifact | SHA-256 / result |
|---|---|
| Pre-change `epe_2026_before.dump` | `b0185b9e4381a7f85b67437d97ca639b720bbc3384331ff8e01cb64ba5c6204e` (73389) — restore: users=89, evals=0, sessions=1, H1 draft |
| Pre-change `n8n_public_before.dump` | `49a94951947eb0412d6507948456ee2cac714de4120b86dfbcbf561976099109` (504014) — restore: workflows=60 active=25, webhooks=28, executions=113, insights_raw=0 |
| Final `epe_2026_after.dump` | `9dfdde736308c1c45992b235ee6877c63dbc68c4fbe1f8d2bbb9c5e526be41e8` (73313) — restore: users=89, evals=0, sessions=0, registered=1, H1 draft |
| Final `n8n_public_after.dump` | `dbcc37008d5fd251814b0597a8294760dcaed568b351111d473ca98bbbe2a8ff` (501667) — restore: workflows=58 active=26 |
| 2025 fingerprint before / after | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e`, **unchanged=true** |

`epe_2026` custom-format SHA moved because the before dump still had Alexander’s session (sessions=1), proof inserts advanced sequences even after row delete, and dump-header timestamps differ. Row counts after cleanup match the required end state.

n8n public SHA moved because:

1. Two workflow **DELETEs** (`H4T4EMYmJJ1jdT7Z`, `uYy7zVKjgXx8zApC`) — dump shrank 504014 → 501667.
2. Submit-evaluation **PUT** (graph + `updatedAt`).
3. evaluations-matrix **activated** (flag + webhook row; webhooks 28 → 29).
4. `insights_raw` 0 → 72 during proofs. `execution_entity` count stayed 113 on the before-dump restore and on live after cleanup.

No schema change. 2025 archive not written.

---

## Boundaries held

- Auth Guard bytes unchanged (same GET md5).
- No other active workflow edited.
- No formula, SQL-shape, or success-body change on submit insert or on the matrix.
- Matrix period-filter and `manager_score`-by-role defects not fixed.
- score-correction and the other deferred routes still inactive.
- Proof writes rolled back in full.
