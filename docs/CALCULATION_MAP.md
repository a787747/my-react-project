# EPE — Calculation Map

**Date:** 2026-08-19 · **Brief:** `docs/briefs/CALCULATION_MAP_2026-08-19.md` · **Mode: read-only**

Every number the system computes, stores or displays; where it is computed; what it depends on. Sources: current repo `src/` (verified against the live-bundle path map per `docs/FRONTEND_MAP.md` §4), repo `n8n_workflows/*.json` (verified against the server's n8n `public` schema — all distinctive formula fragments matched the live dump), the 2025 archive database `postgres.performance_db` (queried read-only), and `epe_2026`.

## Integrity proof

2025 archive canonical fingerprint (schema dump + per-row md5 of all 12 tables + all sequences — same method as `docs/IMPORT_2026-08-18.md`):

```text
before=21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
after =21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
unchanged=true
```

n8n public schema dump (plain-format pg_dump, deterministic):

```text
before=3d4d7cfae5ed8e06637b49faae3fdd0abe38613f195b54c5816c88e2ceaac523
after =3d4d7cfae5ed8e06637b49faae3fdd0abe38613f195b54c5816c88e2ceaac523
identical=true
```

Files: `backups/2026-08-19-calcmap/` (gitignored). No workflow, migration, or data change was made.

**Naming note.** The DB column is `evaluations.calculated_score`; the API field is `final_score`. They are the same number. `evaluations.weighted_score` is a separate column, populated only by self-review.

---

## A. Inventory

Scale is 1–10 integers per criterion everywhere in the UI (`CriterionSlider.jsx:23`, `UI_CONFIG.MAX_SCORE=10`). "Active period" means `evaluation_periods.is_active = true LIMIT 1` (no ORDER BY — assumes at most one active row; the activate flow deactivates all first).

### A.1 Write paths (numbers that get stored)

| # | Number | Producer (role) | Route | Where computed | Exact formula | Inputs | Stored | Live/snapshot | Period filter | Rounding/scale |
|---|--------|-----------------|-------|----------------|---------------|--------|--------|---------------|---------------|----------------|
| W1 | Manager rating | `EvaluationModal.jsx` (manager/admin/c_level) | POST `/api/submit-evaluation` | **Client**: `EvaluationModal.jsx:334` → `calculateFinalScore` (`evaluationUtils.js:15`) | `mean(grades) × 1.0` | per-criterion integers 1–10 of the visible criteria set | `evaluations.calculated_score`, source `manager` | snapshot of the number; **server does not recompute or validate** | write: active period id; **`NULL` if no period is active** (`Prepare Data` node) | `toFixed(2)` client; `numeric(10,2)` |
| W2 | Upward rating | `useManagerEvaluation.js:126-138` (any employee with a manager) | POST `/api/submit-evaluation` | **Client** | `mean(grades)`, `managers_only` criteria only | criterion 2 (currently the only one) | same, source `subordinate` | snapshot, unvalidated | same as W1 | `toFixed(2)` |
| W3 | C-level direct rating | `useEvaluationsMatrix.js:159-181` (admin/c_level from matrix) | POST `/api/submit-evaluation` | **Client** | `mean(grades)` | cell criteria | same, source `c_level_direct` | snapshot, unvalidated | same as W1 | `toFixed(2)` |
| W4 | Self-review rating (`final_score`) | `useSelfReview.js:143` (everyone) | POST `/api/self-review-submit` | **Client** | `mean(grades)` | self criteria (currently 3, 4, 12) | `evaluations.calculated_score`, `is_self_evaluation=true`, `evaluation_type='self'`, source `manager` (column default) | snapshot, unvalidated | write requires an active period (`Get Active Period` → insert references its id); one self-review per period — resubmit throws, `is_update` is sent by the client and **ignored** by n8n | `toFixed(2)` |
| W5 | Self-review weighted value (`weighted_score`) | `useSelfReview.js:146-147` | POST `/api/self-review-submit` | **Client**: `calculateWeightedScore` (`evaluationUtils.js:33-80`) | `(Σ sᵢ·coef(round sᵢ)·wᵢ / Σ wᵢ) × grade_coefficient` | grades; live `/api/score-coefficients` (weights + per-level coefficients); `user.grade_coefficient` from the **login object in localStorage** | `evaluations.weighted_score` | snapshot of live inputs at submit time; inputs themselves are unversioned | same as W4 | `toFixed(2)`; level clamped to 0–10, missing coefficient → 1.0 |
| W6 | Updated rating | `EvaluationModal` edit mode | POST `/api/update-evaluation` | **Client** (same as W1) | `mean(grades)` | new grades | overwrites `calculated_score`; **deletes all score rows and reinserts** | server writes the client number as-is | period_id kept | 2 dp |
| W7 | Per-criterion score | `CriterionSlider` | both submit routes | user input | integer | — | `evaluation_scores.score_value` (`ON CONFLICT (evaluation_id, criteria_id) DO UPDATE`) | snapshot | via parent evaluation | integer; **no range CHECK in DB, no server-side range validation** |
| W8 | Correction score | matrix cells (admin/c_level → `c_level`; manager-of-manager → `mid_level`) | POST `/api/admin/score-correction` | user input; level derived server-side from hierarchy, or taken from body | integer 1–10 (server validates this one) | — | `score_corrections`, upsert key `(subject_id, criteria_id, correction_level)` | snapshot | **no period dimension at all** — an H2 correction overwrites the H1 correction for the same subject+criterion | integer 1–10 |

**Grade coefficient in W5 today:** the 2026 login (`API: Auth Login (No Params)`, `Load User and Attempts` node) returns `grade_id` but **not** `grade_coefficient`, and nothing else populates it on the user object. `useSelfReview.js:146` falls back to `1.0`. So every 2026 self-review would store `weighted_score` with grade coefficient 1.0. The 2025 data shows the same (§B.6, §C).

### A.2 Read paths (numbers computed at read/render time)

| # | Number | Consumer (role) | Route | Where computed | Exact formula | Period filter | Rounding |
|---|--------|-----------------|-------|----------------|---------------|---------------|----------|
| R1 | `check-self-review.score` — badge "Самооценка" in `EvaluationModal.jsx:465`, SelfReview page status | manager evaluating; employee | GET `/api/check-self-review` | n8n SQL `Check Database` | latest active-period self-review `calculated_score` (plain 1–10 average) + grades/comments maps | **active period** | stored 2 dp |
| R2 | `my-profile.stats.average_score` | Profile (`ProfileStats.jsx:42`) | GET `/api/my-profile` | n8n Code `Format Response` | `mean(calculated_score)` over **all** evaluations of the subject — **all periods and all sources mixed (self + manager + upward)** | **none** | JS `toFixed(2)` |
| R3 | `my-profile.stats.latest_score` / `latest_period` / `total_evaluations` | Profile | same | same | latest row by `updated_at` regardless of source | **none** | 2 dp |
| R4 | `my-profile.evaluations[].score`, `.weighted_score` | Profile table (`ProfileEvaluationsTable.jsx:94-96`; weighted shown only to admin/c_level via `Profile.jsx:345`) | same | SQL passthrough | stored values | **none** | 2 dp |
| R5 | `get-my-manager.last_evaluation_score` | ManagerEvaluation page | GET `/api/get-my-manager` | n8n SQL | latest `calculated_score` of this evaluator's `subordinate`-source evaluation of the manager, **any period** | **none** | stored |
| R6 | `get-my-manager.previous_scores[]`, `has_evaluated_manager` | same | same | same | per-criterion rows / EXISTS, active period | **active period** | integer |
| R7 | `get-my-manager.manager.grade_coefficient` | same | same | SQL live join `grades` | current value | n/a | numeric(5,2) |
| R8 | `check-evaluated.details[].last_score` | Dashboard, TaskStatusContext | GET `/api/check-evaluated` | n8n SQL | latest `calculated_score` per subject by this evaluator, `evaluation_type='manager'` — **matches every submit-evaluation row incl. upward and c_level_direct**, because submit-evaluation never sets `evaluation_type` (column default `'manager'`) | **active period** | stored |
| R9 | `evaluation-history[].final_score` | EvaluationHistory page | GET `/api/evaluation-history` | SQL passthrough (`calculated_score AS final_score`) | given evaluations, non-self, **all periods** | **none** | stored |
| R10 | Matrix per-criterion `self_score`, `manager_score`, `c_level_score`, `mid_level_correction`, `c_level_correction`, `subordinate_avg_score`, `subordinate_count`, `boss_score` | AdminEvaluationsMatrix, AdminFinalScores, AdminScoreCalculator, BonusCalculation (admin/c_level) | GET `/api/admin/evaluations-matrix` | n8n SQL (`API: evaluations-matrix`, `Execute Query`) | per (user × active criterion): latest `score_value` by `updated_at`; `manager_score` = latest non-self score whose **evaluator role** ∈ (manager, admin, c_level); `c_level_score` = same for `c_level_only` criteria, role ∈ (admin, c_level); corrections `LIMIT 1` **without ORDER BY**; `subordinate_avg_score = ROUND(AVG,1)` over `subordinate`-source scores | **none — latest across all periods** | `ROUND(…,1)` for subordinate avg; others raw integers |
| R11 | Same for a middle manager's span | ManagerSubordinatesMatrix (manager of managers) | GET `/api/manager-subordinates-matrix` | n8n SQL, same subqueries minus `c_level_score`/`boss` | same | **none** | same |
| R12 | Matrix cell final — **admin matrix screen** | `EvaluationsMatrixTable.jsx:40-48`; also `EmployeeScoresModal.jsx:37-45` | client render | `c_level_correction` present → `(manager_score + c_level_correction)/2` else `manager_score`. **Ignores `mid_level_correction`** | n/a | `toFixed(1)` |
| R13 | Matrix cell final — **manager matrix, final scores, calculator, Excel export** | `matrixUtils.getCriterionFinalScore:68-94`, `ManagerSubordinatesMatrix.jsx:26-45`, `useFinalScoresMatrix.js:43-69`, `useScoreCalculation.js:28-54`, `excelExport.js` | client render | `mean(manager_score, mid_level_correction?, c_level_correction?)`; `c_level_only` criteria → `c_level_score` as-is | n/a | unrounded float, display-rounded |
| R14 | Weighted criterion score | AdminFinalScores, AdminScoreCalculator | client: `useFinalScoresMatrix.calculateCriterionScore:75-90`, `useScoreCalculation.js:170-187` | `R13 × coef(clamp(round(R13),0,10)) × weight` | n/a | float |
| R15 | `weighted_sum` | same | client | `Σ R14` over the subject's scored criteria — **no ÷ Σweights** | n/a | float |
| R16 | **Bonus allocation index** (`final_weighted_score`) | AdminFinalScores, BonusCalculation | client: `useFinalScoresMatrix.js:204`, `useScoreCalculation.js:227` | `weighted_sum × grade_coefficient` (grade coefficient **live** from `/api/admin-users-data` grades) | n/a | float, displayed 2 dp |
| R17 | Bonus money | BonusCalculation | client: `BonusCalculation.jsx:98-136` | `totalPoints = Σ R16` (grade A optionally excluded); `pointValue = round(budget/totalPoints)` to integer; `bonus = R16 × pointValue` | n/a | integer point value |
| R18 | Totals row | AdminFinalScores (`useFinalScoresMatrix.totals:240-273`) | client | per-criterion sums, Σ weighted_sum, Σ R16, mean R16 per employee | n/a | 2 dp |
| R19 | `analytics.overall.company_avg_score` | Analytics page | GET `/api/analytics` | n8n SQL | `ROUND(AVG(calculated_score),2)` over **all evaluations — self, manager, upward mixed, all periods** | **none** | 2 dp |
| R20 | `analytics.departments[].avg_score` | same | same | same per department; client adds zone distribution and deviation from company avg (`Analytics.jsx:231-244, 458`) | **none** | 2 dp |
| R21 | `analytics.top_performers / low_performers` | same | same | latest row per subject by `updated_at` **regardless of source** (can be a self-review), all periods | **none** | stored |
| R22 | `analytics.period_trends` | same | same | AVG per period (grouped by `period_id`) — the only period-aware analytics number | grouped by period | 2 dp |
| R23 | HR flags (`has_self_review`, `evaluated_manager`, `all_subordinates_evaluated`, counts) | HRDashboard, TeamView, Dashboard, AdminUsers | GET `/api/hr/evaluation-status` | n8n SQL; score values stripped in Code node | boolean/int flags, `status='completed'` | **active period** | n/a |
| R24 | `admin-users-data.self_review_done`, `manager_review_status` | AdminUsers | GET `/api/admin-users-data` | n8n SQL | subqueries `LIMIT 1` without ORDER BY; `manager_review_status` filters only `is_self_evaluation=false` — **an upward evaluation of a manager satisfies it** | **active period** | n/a |
| R25 | All-evaluations columns (`self_score`, `manager_score`, `gave_to_manager_score`, `from_subordinates_score = ROUND(AVG,2)`, counts) | AdminAllEvaluations (admin/c_level; the screen where self and manager ratings sit side by side) | GET `/api/admin/all-evaluations` | n8n SQL built in Code node | latest per (subject × source); upward average over all upward rows | **none** — and the `manager_evaluations_given` join is not deduplicated: a second period adds a second row per employee (row multiplication in H2) | 2 dp |
| R26 | Evaluation details (header `final_score` + score rows) | profile/history/modal views | GET `/api/evaluation-details` | SQL passthrough | stored values; criteria titles live-joined | by evaluation id | stored |
| R27 | Details-by-user groups | AllEvaluationsDetailsModal, SubordinateEvaluationsModal, ManagerEvaluationDetailsModal | GET `/api/admin/evaluation-details-by-user` | n8n Code groups rows | `self_evaluation` is a **single slot** (latest processed wins across periods); as-evaluator grouping recognises only `subordinate`/`manager` sources — **`c_level_direct` evaluations are dropped** from the evaluator view | **none** | stored |
| R28 | `employee-self-review.total_score` | no React call site (compiled into live bundle) | GET `/api/employee-self-review` | n8n SQL | active-period self `calculated_score` | **active period** | stored |
| R29 | Per-criterion self vs manager delta | `CriterionSlider.jsx:169-176` (dot + ±n badge), `ScoreDetailModal.jsx:269-277` | client | `current − self`, integers | n/a | integer |

### A.3 Reference data (inputs the formulas join live)

| Input | Table | Written by | Versioned? |
|-------|-------|-----------|------------|
| Criterion weight | `criteria.weight` | POST `/api/score-coefficients` (`API: Save Score Coefficients` — plain UPDATE) | **No** |
| Per-level score coefficient | `score_coefficients` (criteria_id × levels 1–10) | same route, upsert | **No** |
| Grade coefficient | `grades.coefficient` | POST `/update-admin-data` | **No** |
| Criteria set / target_audience / flags | `criteria` | POST `/manage-criteria` | **No** |
| Hierarchy (`manager_id`), `has_subordinates`, `is_project_participant`, `work_category`, `grade_id` | `users` | `/admin/save-user` | **No** |

Nothing snapshots these onto an evaluation except W5's arithmetic result. Every consumer joins the current values.

---

## B. Findings

### B.1 Self vs manager comparison: raw or normalized?

**Like-for-like (1–10 vs 1–10), not grade-driven.** The hypothesis in HANDOVER §4 consequence 1 is **not confirmed** — the code contradicts it. Every place a self value sits next to a manager value uses the plain 1–10 numbers:

- `EvaluationModal.jsx:465` badge: `check-self-review.score` = self `calculated_score` (plain average) — the manager's own result on the same screen is the plain average of their slider values.
- `CriterionSlider.jsx:117-176`: per-criterion self integer vs the manager's slider integer, with a ± badge.
- `ScoreDetailModal.jsx:269-277` (admin matrix): per-criterion `self_score` vs `manager_score` integers ("Самооценка выше на N баллов").
- `AllEvaluationsTable.jsx` (admin): `self_score` and `manager_score` columns — both `calculated_score` plain averages.
- Matrix cells (`EvaluationsMatrixTable renderSelfCell`, `EmployeeScoresModal`): raw integers.

The weighted × grade value (`weighted_score`) appears in exactly one place — the subject's own Profile, labeled "Взвешенный", visible only to admin/c_level (`Profile.jsx:345`) — and is never juxtaposed against a manager rating. The gap C-level reads today measures disagreement, not grade.

### B.2 Which number was used in December 2025

Archive facts (all queries read-only, fingerprint unchanged):

- 234 evaluations, all `period_id=1`, all December 2025: **120 manager** (plain-average `calculated_score` 3.50–9.50, `weighted_score` NULL), **64 self** (`calculated_score` 5.67–9.33 plain average; `weighted_score` 6.57–21.29), **50 upward** (`subordinate` source, single criterion, 6.00–10.00, weighted NULL). **Zero `c_level_direct` rows** — that source did not exist or was not used in December.
- **The admin-matrix/bonus index is stored nowhere.** The archive has 12 tables; none holds a matrix or bonus value. R14–R17 are computed in the browser on each render. If a bonus index was used in December, it was read off the screen or an Excel export and cannot be reconstructed today, because its inputs (weights, score coefficients, grade coefficients) are live tables that have been edited since (see §C: 0 of 64 stored `weighted_score` values reproduce from today's stored inputs).
- **Corrections exist**: 3 rows, all December, all on criterion 13 ("Объем проектной работы") — 1 `mid_level` (evaluator 172 → Shasenem Tishkina), 2 `c_level` (evaluator 1 → Alp Arslan Mametnazar, Valeriya Ruhlyadko). So the matrix screen was actively used for calibration.
- **Grade coefficient was NOT applied to December self-reviews.** Identical score vectors always produced identical `weighted_score` across subjects whose grade coefficients range 0.30–3.00 (11 distinct vectors with n>1, all with `distinct_weighted=1` — e.g. vector `7,7,7` → 10.50 for ten people with grades 0.30, 0.60, 1.10 and 2.20). December's stored self value = weighted formula × 1.0.

**What this settles:** the numbers that existed in the database in December are the plain-average ratings per (subject, evaluator, source). The bonus index existed only transiently on screen. Whether the December *decision* used the on-screen index or the stored rating is a fact about the meeting, not the database — that remains HANDOVER open item 8 for Alexander, but the DB evidence above is the complete set of what he could have taken from the system.

### B.3 Where final_score is computed per write path; does the server validate?

| Route | Computed | Server behaviour |
|-------|----------|------------------|
| `/api/submit-evaluation` | client (`EvaluationModal.jsx:334`; `useManagerEvaluation.js:127-134`; `useEvaluationsMatrix.js:161-163`) | `parseFloat` and INSERT into `calculated_score`. **No recomputation, no range check, no check that grades match the criteria set.** Upsert key `(subject_id, evaluator_id, evaluation_source) WHERE is_self_evaluation=false`. |
| `/api/self-review-submit` | client (`useSelfReview.js:143-152`) — two numbers | inserts both `final_score→calculated_score` and `weighted_score` as sent. **No validation.** n8n uses `weighted_score \|\| final_score`. |
| `/api/update-evaluation` | client | UPDATE `calculated_score` as sent; deletes and reinserts score rows (only criteria-id existence is checked). **No validation.** |
| `/api/admin/score-correction` | user input | the only route with a server-side range check (1–10). |

Nothing server-side ever recomputes a stored score from its rows. A tampered or buggy client can store any number (see §C mismatches for a real-data consequence of the upsert design).

### B.4 How corrections enter final numbers; 2025 corrections

Corrections never touch stored evaluations. They live in `score_corrections` and are merged at read time only:

1. Matrix SQL returns them as `mid_level_correction` / `c_level_correction` per (subject, criterion) — `LIMIT 1`, no ORDER BY, **no period filter** (the table has no period column).
2. The UI computes the cell value. **Two different formulas coexist:** the final-scores/calculator/manager-matrix/Excel path averages `(manager, mid?, c?)` (`matrixUtils.js:68-94` and 3 local copies); the admin matrix screen and `EmployeeScoresModal` compute `(manager + c_level)/2` and **ignore `mid_level` entirely** (`EvaluationsMatrixTable.jsx:40-48`, `EmployeeScoresModal.jsx:37-45`). With 2025 data: Tishkina's criterion-13 mid_level correction (8) changes her bonus-index input on AdminFinalScores but is invisible in the admin matrix cell.
3. The corrected value then feeds R14→R16 (bonus index). Corrections therefore affect bonuses but never ratings shown to employees (`my-profile`, history and details read `evaluations`/`evaluation_scores` only).

2025: 3 corrections exist (detail in §B.2).

### B.5 Period filter per query

Filtered to the **active period**: `check-evaluated`, `check-self-review`, `employee-self-review`, `hr/evaluation-status`, `admin-users-data` (both status subqueries), `get-my-manager` (`has_evaluated_manager`, `previous_scores` only). Writes: `submit-evaluation` stamps the active period (**NULL if none active — with both 2026 periods currently inactive, a submission today would store `period_id=NULL` and become invisible to every active-period query**); `self-review-submit` requires an active period and blocks a second self-review per period.

**No period filter — every one of these is an H2 problem once epe_2026 holds two periods:**

1. `/api/my-profile` — stats and list mix periods **and sources** (self + manager + upward averaged together in `stats.average_score`).
2. `/api/get-my-manager` → `last_evaluation_score` (latest across periods; inconsistent with its own period-filtered `previous_scores`).
3. `/api/evaluation-history` — all periods (arguably by design for "history"; UI has a period column).
4. `/api/admin/evaluations-matrix` — every subquery (self/manager/c_level scores by latest `updated_at`, corrections, subordinate averages, boss score). H1 scores silently become "current" H2 matrix values until overwritten.
5. `/api/manager-subordinates-matrix` — same.
6. `/api/admin/all-evaluations` — all CTEs; additionally `manager_evaluations_given` is joined un-deduplicated → **row multiplication** for any employee with upward evaluations in ≥2 periods.
7. `/api/analytics` — `overall`, `departments`, `top_performers`, `low_performers` (only `period_trends` is period-aware).
8. `/api/admin/evaluation-details-by-user` — both halves; the single `self_evaluation` slot will show an arbitrary period's self-review.
9. `score_corrections` as a data model — no period column; H2 calibration on the same subject+criterion **overwrites** H1's correction via the upsert.

### B.6 Live-joined vs stored on the evaluation

| Value | On the evaluation? | Effect of changing it mid/after period |
|-------|--------------------|------------------------------------------|
| Grade coefficient | **Not stored.** Live-joined at every render (`admin-users-data` options → R16; `get-my-manager`) | Every historical bonus index recomputes with the new coefficient. December's own self-review evidence: current grades can't reproduce stored `weighted_score` (§C) |
| Criterion weight | **Not stored.** Live (`/api/score-coefficients` → W5 at submit, R14 at render) | Same — history rewrites on next render |
| score_coefficients | **Not stored.** Live | Same |
| `manager_id` / hierarchy | evaluations keep `evaluator_id` (true snapshot of who evaluated), but matrix `manager_score` is **role-based, not relationship-based**, and team views join current `manager_id` | Re-assigning a manager moves people between matrices; old evaluations keep their evaluator but may stop being surfaced |
| Criteria set / `is_active` | score rows snapshot what was scored; matrix CROSS JOINs **current active criteria** | Deactivating a criterion hides its historical scores from every matrix and from R15/R16 sums; adding one changes counts (= bonus share) immediately |
| The submitted numbers themselves (`calculated_score`, `weighted_score`, `score_value`) | Stored | Only true snapshots in the system |

### B.7 Criteria per subject (epe_2026, the 89)

`target_audience` maps to a person three different ways depending on the path:

- **Manager evaluation** (`filterCriteriaByEmployee` + `groupCriteria` + group visibility in `EvaluationModal.jsx:80-99`): active criteria; `project_participants`-audience only if `users.is_project_participant`; `managers_only` group only if subject `has_subordinates`; `c_level_only` criteria only when the **evaluator** is admin/c_level.
- **Self-review** (`useSelfReview.js:93-101`): active + `selfassesment` + (`audience='all'` or `audience = work_category`). Today all three self criteria are `'all'`, so everyone gets 3. Note the mismatch: audiences compared against `work_category` values (`general/project/tender`), which can never equal `'project_participants'` — a criterion with audience `project`/`tender`/`back_office` (offered by the admin form) would enter self-review for that category but fall into the "general" group for every subject in the manager path.
- **Upward** (`useManagerEvaluation.js:101-103`): active + `managers_only` → 1 criterion (id 2).

Current catalogue (8 active criteria): self 3,4,12 (audience `all`); project 8,13 (`project_participants`); management 2 (`managers_only`); c_level-only 1,10 (`all` + `c_level_only`). **The count is not stored anywhere** — recomputed from the criteria table on every render; the only persisted trace is how many `evaluation_scores` rows a submission wrote.

Distribution across the 89 (criteria a regular manager scores for the subject; +2 if the evaluator is admin/c_level):

| Category | has_subordinates | People | Criteria (manager path) | + c_level evaluator |
|----------|------------------|--------|--------------------------|---------------------|
| general (not project) | no | 35 | **3** (3, 4, 12) | 5 |
| general | yes | 11 | **4** (+2) | 6 |
| project participant | no | 38 | **5** (+8, 13) | 7 |
| project participant | yes | 5 | **6** (+2, 8, 13) | 8 |

Self-review: 3 for all 89. Upward: 1. Because R15 has no ÷Σweights, this table **is** the bonus-share structure: a project participant's index is built from 5–6 criteria against 3–4 for general staff. The 43-name classification check (HANDOVER open item 4) governs the 5-vs-3 split.

### B.8 Scale and rounding

- **UI**: integers 1–10 everywhere (`SCORE_VALUES=[1..10]`, `MAX_SCORE:10`). Zero cannot be entered anywhere; `score-correction` rejects 0 server-side.
- **Zero residue**: `calculateWeightedScore` clamps to 0–10 and criteria carry `level_0_desc`; level 0 has no `score_coefficients` row (levels stored 1–10 only) → falls back to coefficient 1.0. Dead but live-looking support; per API_CONTRACT some old n8n checks said 0–10.
- **DB**: no CHECK constraints on `evaluation_scores.score_value`, `calculated_score`, or `weighted_score`. Archive actuals: score_value 3–10, zero zeros. The only server-side range validation in the system is on corrections.
- **Rounding points**: client `toFixed(2)` at submit (W1–W5) → `numeric(10,2)` column; n8n `ROUND(avg,1)` for matrix `subordinate_avg_score`; `ROUND(avg,2)` in analytics and all-evaluations; profile average `toFixed(2)` in the Code node; UI `toFixed(1)` on matrix cells (R12), `toFixed(2)` on final scores/bonus. R13–R16 propagate unrounded floats internally and round only for display — the stored 2-dp `calculated_score` and the on-screen matrix values can therefore disagree in the last digit by design.
- `getCriterionFinalScore` averaging (R13) produces non-integers (e.g. 6 with correction 8 → 7.0; three values → x.33) which then pick a score coefficient via `Math.round` — a corrected 6.5 rounds to 7 and takes the level-7 coefficient.

---

## C. Reproduction proof (2025 archive, read-only)

Method: for **all 234** evaluations (not a 10-sample), recompute from stored `evaluation_scores` rows and the archive's stored inputs (criteria.weight, score_coefficients, subject's grades.coefficient), and compare with stored values. SQL run against `postgres.performance_db`; fingerprint unchanged before/after.

**Ratings (`calculated_score` = plain average of score rows):**

| Source | Total | Reproduced exactly | Mismatches |
|--------|-------|-------------------|------------|
| manager (is_self=false) | 120 | **115** | 5 (below) |
| self | 64 | **64** | 0 |
| subordinate | 50 | **50** | 0 |

Sample of exact reproductions (id · source · stored · recomputed · score vector): 173 manager 4.80 = mean(6,5,4,6,3); 178 manager 6.20 = mean(7,6,7,6,5); 183 manager 7.20 = mean(7,7,7,7,8); 184 manager 7.00 = mean(7,8,6); 108/112/115 subordinate 8.00 = mean(8); 114 subordinate 10.00 = mean(10); 106 self 9.33 = mean(9,9,10); 107 self 7.00 = mean(7,7,7); 109 self 7.00 = mean(8,7,6); 110 self 5.67 = mean(6,5,6).

**The 5 mismatches — a real defect of the upsert design (§B.3):** ids 268, 269, 270, 278, 285, all by evaluator 1 (admin), December 26. In each, stored `calculated_score` equals the average of **only the two `c_level_only` criteria (1, 10)**, while the row set contains the full criteria set:

| id | subject | stored | avg of all its rows | avg of criteria 1,10 only |
|----|---------|--------|---------------------|---------------------------|
| 268 | 234 | 4.00 | 5.00 (5 rows) | (4+4)/2 = **4.00** |
| 269 | 200 | 7.50 | 7.75 (8 rows) | (8+7)/2 = **7.50** |
| 270 | 197 | 7.50 | 7.33 (6 rows) | (8+7)/2 = **7.50** |
| 278 | 233 | 5.50 | 7.00 (5 rows) | (5+6)/2 = **5.50** |
| 285 | 192 | 4.00 | 4.80 (5 rows) | (4+4)/2 = **4.00** |

Consistent explanation: two submissions by the same evaluator merged into one row by `ON CONFLICT (subject_id, evaluator_id, evaluation_source)` — the later submission scored only the c_level criteria and its client-computed average **overwrote** `calculated_score`, while the score-row upsert kept the earlier rows (it updates matching criteria, never deletes others). The exact December UI flow is unverified (the December frontend has no version history — `FRONTEND_MAP.md` §4), but the arithmetic identity holds for all five. Consequence: these five stored ratings do not equal the average of their own visible details.

**Self-review `weighted_score`: 0 of 64 reproduce from today's stored inputs.** Recomputing `(Σ s·coef·w/Σw) × grade_coef` with the archive's current `criteria.weight`, `score_coefficients` and `grades.coefficient` matches no stored value (examples — id 106: stored 21.29 vs 20.20; id 107: stored 10.50 vs 5.35; id 116: stored 15.60 vs 32.44). Two structural facts are provable from the stored data alone:

1. **Grade coefficient was not applied** (all 11 repeated score vectors give one weighted value each across grades 0.30–3.00 — §B.2).
2. **The weight/coefficient tables were edited after December.** With grade removed, no combination of today's stored weights and coefficients reproduces the values either (all-7s vector: stored 10.50 implies an effective level-7 multiplier of 1.5; today's tables give 1.27 equal-weighted or 1.29 weight-averaged). The December inputs are unrecoverable because the catalogue is live-edited and unversioned (§A.3). This is the freeze-rule argument in one number.

Every mismatch above is reported with its numbers; there are no unexplained mismatches.

---

## D. Surface for decision (no recommendation on the formulas)

1. **Self-vs-manager comparison is NOT grade-driven.** All comparison surfaces are raw 1–10 vs 1–10 (§B.1). The weighted self value is stored but only displayed, never compared. No fix needed for the comparison itself.
2. **December evidence (§B.2):** stored December numbers are plain-average ratings per source; the admin-matrix/bonus index was never persisted and its December inputs are unrecoverable (weights/coefficients edited since; grade coefficient provably not applied to self-reviews). 3 corrections exist. `c_level_direct` did not exist in the data. The "which number was used" question is answerable only by Alexander's recollection; the DB can no longer reproduce the December matrix.
3. **Freeze rule — values whose history rewrites if edited during a period** (§B.6): grade coefficients (`grades.coefficient`), criterion weights (`criteria.weight`), per-level `score_coefficients`, criteria set/`is_active`/`target_audience` (drives both visibility and the criteria-count = bonus share), and hierarchy/`is_project_participant`/`has_subordinates` on `users`. None is versioned; all are edited through live admin routes.
4. **Queries without a period filter** (H2 blockers, full list §B.5): my-profile, get-my-manager.last_evaluation_score, evaluation-history, evaluations-matrix, manager-subordinates-matrix, all-evaluations (plus row-multiplication), analytics (all but trends), details-by-user, and the `score_corrections` table which has no period column at all.
5. **Server stores client-computed numbers unvalidated:** `submit-evaluation.final_score`, `self-review-submit.final_score` and `.weighted_score`, `update-evaluation.final_score`; `evaluation_scores.score_value` has no range validation on any submit path (only corrections are range-checked). Proof of consequence: the 5 December rows where the stored rating ≠ the average of its own rows (§C).
6. **Criteria-count distribution across the 89** (§B.7): 35×3, 11×4, 38×5, 5×6 (manager path; +2 under a c_level evaluator; self=3, upward=1 for everyone). Input for the 43-name project classification check.
7. Secondary formula-consistency facts surfaced (not defects of the three intentional formulas, but places the map's single formula splits per screen): admin matrix and EmployeeScoresModal ignore `mid_level_correction` while final-scores/calculator/Excel average it in (§B.4); `analytics`/`my-profile` averages mix self+manager+upward sources in one number; matrix `manager_score` is role-based — 2 upward evaluations by manager-role evaluators exist in 2025 and would surface as `manager_score`, and 54 subjects have >1 privileged non-self evaluation making "latest wins" order-dependent; if the 2026 grade coefficient is intended to be applied to self-review weighted values, the current login must start returning `grade_coefficient` (today it silently falls back to 1.0, as it demonstrably did in December).

**Session facts:** one session, read-only; fingerprints unchanged (§ Integrity proof); `PROJECT_RULES.md` referenced by `AGENTS.md` does not exist in the repo (noted, not reconstructed — out of scope for a read-only brief).

---

## E. Addendum — 2026-08-19, post-report verification (read-only)

Verified after the architect's addendum to the route-guard brief, in support of its D5 (uniqueness). All checks read-only; the 2025 fingerprint proof in § Integrity proof covers this session.

**epe_2026 already enforces per-period uniqueness — the schema has moved ahead of the workflows:**

```text
idx_evaluations_unique_non_self_period  UNIQUE (subject_id, evaluator_id, evaluation_source, period_id) WHERE is_self_evaluation = false
idx_evaluations_unique_self_period      UNIQUE (subject_id, period_id)                                   WHERE is_self_evaluation = true
idx_score_corrections_unique_period     UNIQUE (subject_id, criteria_id, correction_level, period_id)
score_corrections.period_id             NOT NULL, no default
```

(The 2025 archive has none of these — its upsert keys are period-less, which is what allowed the §C merge defect.)

**Consequence — launch blocker independent of guard work:** the `ON CONFLICT` targets in `API: Submit Evaluation` (`(subject_id, evaluator_id, evaluation_source) WHERE is_self_evaluation = false`) and `API: Score Correction` (`(subject_id, criteria_id, correction_level)`) no longer match any unique index on epe_2026. PostgreSQL rejects the arbiter at planning time, so **every call to either route fails with error 42P10 before touching data** — proven with `EXPLAIN` (no execution, no writes):

```text
EXPLAIN INSERT … ON CONFLICT (subject_id, evaluator_id, evaluation_source) WHERE is_self_evaluation = false …
ERROR:  there is no unique or exclusion constraint matching the ON CONFLICT specification
EXPLAIN INSERT … ON CONFLICT (subject_id, criteria_id, correction_level) …
ERROR:  there is no unique or exclusion constraint matching the ON CONFLICT specification
```

`API: Score Correction` additionally never supplies `period_id`, which is NOT NULL on epe_2026. `API: Submit Self Review` uses a plain INSERT and is unaffected; its SELECT-then-INSERT race is now closed by `idx_evaluations_unique_self_period` (a duplicate becomes a DB error instead of a second row).

**D5 evidence summary:** the December defect (§C — five ratings not equal to the average of their own rows, produced by the period-less upsert merging two submissions) is the failure mode per-period uniqueness plus server-side recomputation eliminates. The epe_2026 indexes are the right shape; the two workflows must be aligned to them (add `period_id` to both conflict targets and supply `period_id` on corrections). Note that in the current frontend the December collision path is also narrowed by source separation (`c_level_direct` lands in a different row than `manager`), but only server-side recomputation makes the header provably equal to its rows.
