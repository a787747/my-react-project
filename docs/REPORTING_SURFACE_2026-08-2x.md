# Reporting surface — Implementation Report

**Date of work:** 2026-08-20 (UTC) / Ashgabat  
**Status:** Completed, deployed, proof writes rolled back  
**H1 campaign:** back to draft / inactive. Launch 31 Aug.

Alexander’s rule: known reporting defects are fixed now, not in September. The matrix / correction surface was already done. This brief finishes the remaining reporting routes, their period hygiene, and the frontend routing around them.

Company-wide results = **admin + c_level only**. HR keeps `hr/evaluation-status`. The three scoring formulas in `docs/HANDOVER.md` §4 were not changed.

---

## Verdict

The five reporting routes are period-honest and **active**.

- Default period = the single `is_active=true AND status='active'` row. The response names it. No active period → **200 empty-state**, not mixed Annual 2025 + H1 rows.
- Optional `?period_id=` is a read-only inspect on all-evaluations, analytics, details-by-user, and manager-subordinates-matrix.
- Row multiplication on all-evaluations is closed (`DISTINCT ON` the upward join).
- `detail_type` is a real filter (not accepted-and-ignored). Unknown values → **422 `INVALID_QUERY`**.
- Manager subordinates matrix: `manager_score` by `evaluation_source='manager'` + period bind + actor-tree-only. First-line manager → **403**.
- manage-criteria GET still returns the catalogue and now names the period. save/delete stay **409 `ACTIVE_PERIOD_EXISTS`** while a period is active. update-admin-data stays write-frozen the same way.

H1 can be run against this surface. No functional blocker on these five screens.

---

## What was deployed

Generator: `scripts/build_route_guard_deferred.py` (regenerates all 10 deferred JSON files).  
Deployer: `scripts/deploy_reporting_surface.py` — **only** these six live PUTs. Evaluations-matrix, score-correction, Auth Guard, and every launch/campaign route were refused.

| Workflow | id | Change | `updatedAt` |
|---|---|---|---|
| `API: All-evaluation` | `j9YdW8LGzW5lvxgb` | activated; period bind; `DISTINCT ON` upward join; `manager_score` by source | `2026-08-20T06:29:08.971Z` |
| `API: evaluation-details-by-user` | `ZUDqYb0nWGGXLUnB` | activated; period bind; `detail_type` enforced | `2026-08-20T06:29:10.451Z` |
| `API: Analytics Dashboard - Optimized` | `i1rMW79I7GYb5iXm` | activated; period bind; chain-dedup of list nodes | `2026-08-20T06:33:26.304Z` (second PUT: list unique) |
| `API: Manager Subordinates Matrix` | `EyvFZJGDxQNL20tC` | activated; period bind; `manager_score` by source | `2026-08-20T06:29:13.367Z` |
| `API: Manage Criteria Admin V7` | `55BHbXWIS6igHHBT` | activated; GET names period, catalogue kept; save/delete 409 freeze | `2026-08-20T06:29:14.973Z` |
| `API: Update Admin Data` | `CkxIyrEJBrc6V4Cv` | activated; graph unchanged; 409 freeze while a period is active | `2026-08-20T06:29:16.555Z` |

Not touched (live `updatedAt` unchanged):

| Workflow | `updatedAt` |
|---|---|
| `EPE: Auth Guard` `L0Zr7nVa8O5YWXd3` | `2026-08-18T16:34:30.674Z`, inactive, GET md5 **`6ea30fc47b8f51180a4b963fdae79732`** before and after |
| `API: evaluations-matrix` | `2026-08-19T20:34:41.748Z` |
| `API: Score Correction` | `2026-08-19T20:34:42.909Z` |
| `API: Submit Evaluation` | `2026-08-19T19:43:38.525Z` |
| `API: Submit Self Review` | `2026-08-19T08:40:23.767Z` |
| `API: Update Evaluation WITH PERIOD` | `2026-08-19T11:52:24.730Z` |
| `API: Auth Login (No Params)` | `2026-08-19T08:40:17.190Z` |

Earlier reports quoted Auth Guard md5 `de58de075d66a621e832aac9a2dd3d14`. That was a different serialization of the same GET. This session uses the raw GET body both times; `updatedAt` did not move.

Static tests: `tests/routeGuardDeferred.test.js` + `tests/matrixUtils.test.js` — **29/29**.

Frontend release **`20260820T063333Z`** → `/var/www/epe/current`. Previous **`20260819T203659Z`** kept on disk.

---

## Per-route evidence (auth + period + defect)

Proof actors (minted JWT, then deleted): admin 2, c_level 18, manager 1 (Akmyrat), employee 3 (Alina), HR 52 (Liya). H1 was draft for empty-state, then temporarily `active` for data proofs and the browser pass.

| Route | No token | Forged | Expired | Employee | HR | Admin | C-level | Period empty (H1 draft) | Period bound (H1 active) | Defect closed |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| GET `api/admin/all-evaluations` | 401 | 401 | 401 | 403 | **403** | 200 | 200 | `data=[]`, `period=null`, `campaign_active=false` | `period.name=H1-2026`, 83 rows, Alina ×1 | row multiplication; source-based `manager_score` |
| GET `api/analytics` | 401 | 401 | 401 | 403 | **403** | 200 | 200 | zeros + empty arrays, `period=null` | `company_avg_score=5.00`, 3 evals, named H1 | all aggregates `period_id`; inspect `?period_id=1` → 9.00 |
| GET `api/admin/evaluation-details-by-user` | 401 | 401 | 401 | 403 | **403** | 200 | 200 | empty groups, `period=null` | Alina self 6 / manager 4 / to-manager 5 | `detail_type` real; see Surface |
| GET `api/manager-subordinates-matrix` | 401 | 401 | 401 | 403 | **403** | 200 | 200 | `data=[]`, `period=null` | admin 24 rows (Alexander’s tree); c_level 18 different tree (`3,10,31,…`) | actor-tree; `manager_score` by source; first-line **403** |
| POST `manage-criteria` action=get | 401 | 401 | 401 | 403 | 403 | 200 | 403 | catalogue 8, `period=null` | catalogue 8, `period.name=H1-2026` | GET not emptied; save **409** |
| POST `update-admin-data` | 401 | — | — | — | 403 | 200 (draft no-op) | 403 | 200 while draft | **409 `ACTIVE_PERIOD_EXISTS`** | write-frozen while active |

Manager first-line (Akmyrat 1) on manager-subordinates-matrix: **403** even with `manager_id=18` in the query. Client `manager_id` is ignored.

---

## Row multiplication — same dataset, before / after

Proof rows (SQL insert, not submit): period 1 and period 2 each have Alina self, Akmyrat→Alina manager, Alina→Akmyrat upward.

Old all-evaluations SQL (no period filter, `manager_evaluations_given` not deduplicated):

| Count | Value |
|---|---:|
| Total rows | **84** |
| Alina rows | **2** |

New API with H1 active:

| Count | Value |
|---|---:|
| HTTP | 200 |
| Total rows | **83** (= 84 − the extra Alina copy) |
| Alina rows | **1** |
| Alina scores | self **6.00**, manager **4.00**, gave-to-manager **5.00** (period 2, not 8 / 10 / 9) |

`?period_id=1` (inspect): Alina self **8.00**, manager **10.00**, gave-to-manager **9.00**. The two periods do not mix.

Browser: «Найдено: 83 из 83», Alina one row, banner «Период: H1-2026 — активен». Screenshot `all-evaluations-h1-active.png`.

---

## Analytics — the number that moved

Formula unchanged: `ROUND(AVG(calculated_score), 2)` over evaluations with a non-null score, **all sources mixed** (self + manager + upward). That was already R19 in `docs/CALCULATION_MAP.md`. It is still not a HANDOVER §4 formula.

What changed is **which rows enter the AVG**.

On the six-row proof set:

| View | Rows in the AVG | `company_avg_score` |
|---|---|---:|
| Unbound (old SQL, both periods) | 8, 10, 9, 6, 4, 5 | **7.00** |
| Bound default (H1 id=2) | 6, 4, 5 | **5.00** |
| Inspect `?period_id=1` | 8, 10, 9 | **9.00** |

`period_trends` is no longer a multi-period history. It is **0 or 1 row** for the shown period (proof: one H1-2026 row, avg 5.00). Departments / top / low use the same bind.

Chain bug found in proof (not in CALCULATION_MAP): n8n runs the analytics queries in series, so `Get Period Trends` executed once per upstream row and returned **4 identical H1 rows**; `low_performers` was 4 for 2 people. Format now unique-by key. After the second PUT: trends 1, low 2, top 2. Overall **5.00 did not move**.

Browser: banner «Период: H1-2026 — активен», company average **5.00**, 3 evaluations, 2 employees, Clinical Lab Solutions 5.00. Screenshot `analytics-h1-active.png`. Copy on the page: «Числа — одного периода.»

When H1 has real data, this dashboard will **not** include Annual 2025. That is the intended honesty.

---

## `detail_type` — what it now really does

Smallest honest choice: **make the parameter real**, do not drop it. The frontend already sent it from the all-evaluations cells.

Allowed: `all` (default), `self`, `received_from_manager`, `from_subordinates`, `gave_to_manager`, `gave_to_subordinates`. Anything else → **422 `INVALID_QUERY`**.

| `detail_type` | Subject half | Evaluator half | Proof on Alina, H1 |
|---|---|---|---|
| `all` | self + received manager/`c_level_direct` + from subordinates | gave to manager + gave to subordinates | self yes, manager_n=1, to_manager yes |
| `self` | self only | empty | self yes, manager_n=0, to_manager no |
| `received_from_manager` | as_subject, source ∈ (`manager`, `c_level_direct`) | empty | self no, manager_n=1 |
| `from_subordinates` | as_subject, source=`subordinate` | empty | (no rows on Alina) |
| `gave_to_manager` | empty | as_evaluator, source=`subordinate` | to_manager yes, self no |
| `gave_to_subordinates` | empty | as_evaluator, source ∈ (`manager`, `c_level_direct`) | (Alina has none) |

Also honest on this route: a `c_level_direct` row **as evaluator** is now grouped into `evaluations_to_subordinates`. The legacy format dropped it. Not a stored-formula change.

Browser modal on Alina: self 6, Akmyrat manager 4, Alina→Akmyrat 5. Screenshot `alina-details-modal.png`. Period-1 scores 8/10/9 did not appear.

---

## Frontend routing vs the audience decision

`ReportingRoute` = `canViewAnalytics` = admin + c_level. Applied to `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix`. HR → `/hr/dashboard`. Anyone else → `/welcome`. Sidebar «Аналитика» is the same gate.

**HR is not left with a half-empty reporting screen.** What HR still has:

- `/hr/dashboard` (`hr/evaluation-status`) — unchanged.
- `/admin/users` — table, filters, self-review column via `check-self-review`. Company-wide dossier buttons («Детали» for manager / subordinates, which call details-by-user) are **hidden** (`canOpenDossier` is false).

What HR no longer reaches by URL: analytics, all-evaluations, evaluations-matrix (redirect, not a 403 page).

Leftover, not widened in this brief:

- `AdminRoute` still lets HR open `/admin` (criteria catalogue) and `/admin/periods`. Sidebar hides «Критерии» from HR. The API is admin-only, so a typed URL gets **403**, not company-wide numbers. I did not wrap `/admin` in `ReportingRoute` because the brief named three URLs.
- `/team` (TeamView) is a manager list. Dossier controls that would call details-by-user are **hidden** (`onManagerEvaluationClick` / `onSubordinateEvaluationClick` = `undefined`). Self-review modal stays (`check-self-review`). The list itself still loads `admin-users-data`, which is admin-only — managers already saw an empty/error list before this brief. Not expanded.

Modals still degrade if somehow called: 403 → «Детали оценки доступны только администратору и C-level».

---

## Browser pass (Alexander, H1 temporarily active)

Login Keychain password still **401**. Pass used a minted admin JWT in localStorage. Alexander’s **real** session `f443cfa5-…` was not deleted.

| Screen | What was on it |
|---|---|
| `/admin/all-evaluations` | Banner «Период: H1-2026 — активен»; 83 rows; Alina 6.00 / 4.00 / 5.00 once |
| Details modal (Alina, eye) | Self 6, manager 4, to-manager 5; period-1 numbers absent |
| `/analytics` | Same banner; company avg **5.00**; 3 evaluations |
| `/team-scores` | Same banner; 24 people in Alexander’s skip-level tree (Alyona, Dovran, Muhammet, …). Not Bayram’s tree |
| `/admin` (criteria) | Same banner; 8 criteria still listed; amber «Сохранение и удаление критериев заморожены, пока период активен (409).» |

HR of the five APIs: **403** at API level (table above). Not walked in the browser.

---

## Cleanup

Proof writes deleted: 6 evaluations, 6 score rows, 0 corrections. H1 returned to `draft` / `is_active=false`. Annual 2025 stayed `closed`.

Proof sessions deleted: 7 (5 prove JTIs + 2 extra admin mints). Kept: Alexander `f443cfa5-f8b8-42fd-9a41-0e527d6f24c6`.

End state (live `epe_2026`):

```text
users=89  registered=1  evaluations=0  scores=0  corrections=0
sessions=1  (Alexander)
H1=id 2, draft, inactive
invite id=4 unused
```

Sequences on `epe_2026` advanced (rows were inserted then deleted). Row counts match the start. 2025 archive was not written.

---

## Dumps and fingerprint

Files: `backups/2026-08-20-reporting-surface/` (gitignored) and `/root/backups/epe/2026-08-20-reporting-surface/`.

| Artifact | SHA-256 | Restore |
|---|---|---|
| `epe_2026_before.dump` | `a4773eb8a264aa9282954e3977007317604d4c21cccda85ce902e93f814cd39f` | users=89 evals=0 corr=0 h1=draft,false reg=1 |
| `epe_2026_after.dump` | `2cbb38d6f9ec292beb9d7e9c4409c5fb700cfb25e6659c185afc9730b8efc619` | users=89 evals=0 h1=draft,false reg=1 |
| `n8n_public_before.dump` (plain) | `8872184722411e8e85ba3db97dd5e45c26fbf8f21f3cf021ad9f8f2a44fbddc8` | workflows=58 active=27 |
| `n8n_public_after.dump` (plain) | `90d5ee3650146b3fd47b6ec932bb57462aab2457366e3f46ea653446925d7603` | workflows=58 active=33 |

epe SHA moved: ~1 byte. Sequences, not evaluation rows.

n8n SHA moved (~69 KB): six workflow PUTs + activation bits + `public` executions/insights growth. Not identical, and should not be. Restore-tested both sides.

2025 archive fingerprint (schema dump + per-row md5 of 12 tables + sequence `last_value\|is_called` from the sequence relation — same method as `docs/IMPORT_2026-08-18.md`):

```text
before=21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
after =21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
unchanged=true
```

---

## Final workflow activation list

**33 active**, 37 registered webhooks, 58 workflows total. Previous 27 plus the six in this brief.

```text
API: Admin Get Users Data
API: Admin Save User (GUI Mode)
API: All-evaluation
API: Analytics Dashboard - Optimized
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
API: Manage Criteria Admin V7
API: Manage Periods
API: Manager Subordinates Matrix
API: My Evaluation History (Received)
API: My Profile V5 (Fixed Empty)
API: Register
API: Request Password Reset
API: Reset Password
API: Save Score Coefficients
API: Score Correction
API: Send Verification Code
API: Submit Evaluation
API: Submit Self Review
API: Update Admin Data
API: Update Evaluation WITH PERIOD
API: Verify Code
API: Verify Invite
API: evaluation-details-by-user
API: evaluations-matrix
```

---

## Surface for decision (do not resolve silently)

1. **`detail_type` now filters.** Values: `all` / `self` / `received_from_manager` / `from_subordinates` / `gave_to_manager` / `gave_to_subordinates`. Unknown → 422. The UI already used those names. `c_level_direct` given by the actor is listed under evaluations-to-subordinates (legacy dropped it).

2. **HR reporting screens are not half-empty.** HR keeps statuses + the employee table (self-review via `check-self-review`). Company-wide dossier buttons are hidden. `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix` redirect. Leftover: typed `/admin` (criteria) is still an `AdminRoute`; API 403, sidebar already hidden.

3. **Analytics numbers move because of the period bind, not because of a new formula.** Same `AVG(calculated_score)` as before, still mixing sources. On the proof set the unbound mix was **7.00**; H1 showed **5.00**. `period_trends` is one named period, not a history of both cycles. After H1 has real scores, this dashboard will not include 2025.

Employee-facing reads (`my-profile`, `evaluation-history`, `get-my-manager`, `check-*`) still have the period defects listed in CALCULATION_MAP. Out of scope here — one period in `epe_2026` cannot mix during H1. Scheduled with persist-period-results.
