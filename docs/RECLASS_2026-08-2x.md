# Live reclassification (D-0822-3), BUG-041 runtime-proven, BUG-043, decision riders

**Date:** 2026-08-24, 05:30–06:30 UTC · Brief: Build 2 (D-0822-3 + BUG-041 + BUG-043 + riders) ·
Fact base: `docs/RECON_RECLASS_COEFF_2026-08-2x.md` §3/§4/§7 and decision items 4–9,
`docs/LIFECYCLE_COEFF_2026-08-2x.md`, `docs/GATE_LIFECYCLE_COEFF_2026-08-2x.md` — every fact this
build depends on was re-verified against live before it was changed (live drift check: all 12 target
workflows byte-identical to the HEAD generators before the deploy).

**Outcome in one line.** Classification (project/general) is now editable during a running campaign
and can never destroy evaluation data: exclusion is soft (score rows for no-longer-applicable
criteria stay in the database and stop counting — matrix, close dataset and their corrections all
filter on the subject's *current* classification), addition reopens the manager's task per-criterion
and lands through a new additive path on submit (no more 409 dead end on the manager path), every
write path validates applicability in the classification dimension, BUG-041 got the runtime repro
the code-level close lacked, BUG-043's container-as-current-period answer became an explicit "none",
and the weight floor is 0.1 on the server, deployed.

**Live state after this build.** Campaign-wise **unchanged and inert**: periods
`1 Annual 2025 closed · 2 H1-2026 draft · 5 Annual 2026 draft`, `evaluations` /
`evaluation_scores` / `score_corrections` / `period_results` all **0**, every
`evaluation_started_at` NULL, launch paused. 12 workflows PUT (activation preserved, graphs
re-compared node-for-node after every PUT), frontend release `20260824T061101Z`. No migration —
this build changes no schema. Auth Guard `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` —
checked before, after every PUT, and at the end: **unchanged**. The live post-deploy probe left the
data byte-identical (state fingerprint equal before/after, probe sessions 8 → 8, zero residue).

---

## 1. What changed

### 1.1 One applicability predicate, classification dimension only

A criterion with `target_audience='project_participants'` applies to a subject **iff the subject is
currently a project participant** (`users.is_project_participant`, kept atomic with `work_category`
since BUG-005). Other audiences keep today's semantics everywhere. The predicate now lives in four
places:

| Place | Form |
|---|---|
| `Build Matrix Query` (`API: evaluations-matrix`) | `AND (c.target_audience <> 'project_participants' OR u.is_project_participant = true)` in the row-source WHERE, next to `c.is_active` — the cell for an excluded criterion is **not emitted**, and the `mid_level_correction` / `c_level_correction` sub-selects live inside the cell, so corrections go with it |
| `Build Close Dataset Query` (`API: Manage Periods`) | the same clause on the per-participant `criteria_data` aggregation (`criteria_data` now carries `target_audience`), so the frozen `period_results` inherit exactly what the matrix shows |
| Write validation | `submit-evaluation`, the additive path, `update-evaluation` and `self-review-submit` all answer **422 `CRITERIA_NOT_APPLICABLE`**, naming the offending ids, before any SQL is built — the server no longer accepts any criterion id for any subject (RECON §3.3) |
| The manager-path completion flag and `missing_criteria_ids` (§1.2) | same clause inside `/api/employees` |

Correction→criterion binding, which the RECON did not cover, was verified first:
`score_corrections` rows bind `(subject_id, criteria_id, correction_level, period_id)` (unique index
from migration 006, period column present on live — checked by `information_schema`), and both money
queries read corrections **only** through per-cell correlated sub-selects. Excluding the cell
therefore excludes its corrections; nothing else reads them.

The three §4 formulas are untouched: this changes **which cells exist**, never how they are combined.

### 1.2 Reclassification flow

- **`CLASSIFICATION_FROZEN` is gone.** `API: Admin Save User (GUI Mode)` lost the freeze decision,
  the global first-submission probe and the `Check Classification` node itself (8 nodes now, graph
  rewired Validate → Build). `work_category` validation (`general`/`project` only) and the atomic
  `is_project_participant` derivation are unchanged.
- **project→general is soft.** Rows for 8/13 stop counting in the matrix, the index and the close
  results; nothing is deleted; switching back restores the index **to the digit** (§2.2).
- **general→project reopens the manager's task, per-criterion.** `evaluated_by_actor` on
  `/api/employees` now means "an evaluation exists AND covers every currently-applicable
  manager-path criterion". The applicable set mirrors the manager form exactly: `is_active`, not
  `c_level_only`, `project_participants` only for a current project participant, `managers_only`
  only for a subject with `has_subordinates` (the form's group condition — without this clause no
  manager of a non-manager subject could ever be "done"). The row also carries
  **`missing_criteria_ids`** so the client can name what reopened. `has_self_review` and
  `has_evaluated_manager` stay row-existence — their sets do not depend on classification.
- **The additive path lives on `POST api/submit-evaluation`** (route design was left to the
  executor; extending submit needed no new webhook and no client protocol change). The scope check
  now surfaces `existing_evaluation_id` + `existing_criteria_ids` instead of a boolean duplicate
  flag. With an existing evaluation: submitted ⊆ not-yet-scored → score rows are **added** to the
  existing evaluation and `calculated_score` is recomputed **in SQL** over the full surviving row
  set that counts under the current classification (pre-existing applicable rows `UNION ALL` the new
  values) — a client-sent total is never read. Any overlap with already-scored criteria → **409
  `CRITERIA_ALREADY_SCORED`** naming the ids (edit is the way to change a score); the
  concurrent-create race keeps its 409 `DUPLICATE_EVALUATION` in Format Response. All three additive
  branches share one gate (`target_eval`, `FOR UPDATE`, overlap re-asserted inline — the BUG-041
  rule), so a lost race adds nothing and recomputes nothing, answering 409 `ADDITIVE_CONFLICT`.
  This retires the BUG-036 409-dead-end class on the manager path (row 7 itself is the self-review
  path and stays open, out of scope).
- **Ordinary edit deletes only what the evaluator actively removed.** `update-evaluation`'s
  `removed_scores` CTE keeps the BUG-041 gate and additionally skips rows whose criterion is
  `project_participants` while the subject is currently general — those rows were never in the
  presented set the evaluator edited, so their absence from the payload is not a removal.
  `calculated_score` stays the average of the submitted (applicable) set, computed in SQL as before.
  Active-and-started, non-closed period required, as before.
- **Frontend.** The dashboard card has a third state — «Дооценить (N)» with the missing criteria
  named in the badge tooltip — driven by `evaluated_by_actor` + `missing_criteria_ids`;
  `EvaluationModal` gained an additive mode that presents **only** the missing criteria (drafts
  disabled there — a stale draft could resend scored criteria); every mode now submits **only the
  visible criteria**, which matters in edit mode after a switch (the modal preloads all existing
  rows, including soft-excluded ones, and sending them would now 422); `TaskStatusContext` computes
  «все подчинённые оценены» from the per-criterion flag instead of a second check-evaluated call;
  Dashboard refetches the employee rows after a write so the flag and the missing list stay fresh.

### 1.3 BUG-041 — runtime repro added to the code-level close

The 2026-08-22 close was static (SQL text + tests). The acceptance demanded a runtime proof, and the
race the RECON described — *"the period was closed in the window between Execute Ownership Check and
Execute Update"* — was executed deterministically on the stand at statement level against the closed
period (that is byte-for-byte the state the racing statement runs in): the **pre-fix** statement
(RECON §7.2 text) returned a zero-row header — the 403 path — **and deleted rows 4 and 12 anyway**;
the **post-fix** statement (extracted from the deployed artifact's `Build Update SQL` template, same
values, same state) returned a zero-row header and deleted **nothing**. Row counts in §2.5. The HTTP
route was exercised on both sides of close: 200 with a working (gated) delete during the campaign,
403 `PERIOD_CLOSED` with zero row change after it.

### 1.4 BUG-043 — the current period is an active leaf, or explicitly none

The fix went one step further than the bug row proposed: instead of excluding containers from the
draft fallback, **the draft fallback is removed**. `current_period` in `/api/employees` is the
single `is_active AND status='active'` period that is also a **leaf** (`period_type <> 'annual'`,
no children) — or nothing: `current_period_id` null, `actor_is_in_scope` null, no preparation flag.
Scope exists from **activation** (including the preparation window, where the out-of-scope notice
must keep working), never from a draft and never from the container. The same leaf predicate went
into every campaign-surface period resolution — submit-evaluation, self-review-submit,
check-self-review, check-evaluated, get-my-manager, score-correction — so nothing campaign-shaped
can ever bind to an annual period or a container, even one force-activated by SQL. Admin/reporting
reads stay keyed on active alone (boundary kept). The client already treats only
`actor_is_in_scope === false` as out-of-scope, so the null answer changes no pixels before
activation; Esenova and Balova now get their notice the moment H1 is activated — the window that
matters — instead of being silently in-scope-of-a-container.

### 1.5 Decision riders

- **Weight floor 0.1 (D-0822-2 as amended, approved 2026-08-22).** `MIN_WEIGHT = 0.1` in
  `API: Save Score Coefficients`, mirroring the client `min="0.1"`; the 422 message still names
  `is_active` as the correct way to remove a criterion from the bonus. The negative test that
  guarded "no undecided numeric floor" was rewritten to assert the decided one. Level and grade
  coefficients stay on the plain `> 0` rule.
- `DECISIONS.md`: D-0822-3 appended; D-0822-1 amended (emergency stop also halts the campaign —
  confirmed intended; the start mark survives deactivation and re-activation returns directly to
  «Идёт оценка» — confirmed intended); D-0822-2 amended (the 0.1 floor); note recorded that grades
  S4-M1 (6) and M1 (11) are intentionally one logical grade whose coefficients move together.
- `PROJECT_RULES.md`: the one-session rule (one working directory, one session; side sessions
  declared to the architect first; every session ends commit+push or an explicit stash) — the
  2026-08-22 parallel-session incident, made a rule.
- `docs/HANDOVER.md`: §10 report list now carries `RECON_RECLASS_COEFF` · `LIFECYCLE_COEFF` ·
  `GATE_LIFECYCLE_COEFF` · `RECLASS` **and** `BACKUP_FIX_2026-08-2x.md`, which turned out to be
  missing from the list too (same BUG-044 class); bug counters reconciled to 19 / 25. Two sentences
  that D-0822-3 made false were corrected in place (§3's `CLASSIFICATION_FROZEN` claim, §6.3's
  "409 once a period is active") — leaving them would have recreated the §6.11 wrong-premise class.
- `bugs.md`: BUG-041 verification upgraded with the runtime repro; BUG-043 closed with live + stand
  proofs; BUG-044 closed with the §10 fix as evidence. **BUG-042 and the read-side residue of
  BUG-029 untouched — out of scope, still open.** Statistics: 19 open / 25 closed (44 rows).

---

## 2. Acceptance — compared values

Every figure below is read from `backups/2026-08-24-reclass/reclass_proof.json` (stand,
**148 checks, 0 failures**) and `…/live_reclass_probe.json` (live, post-deploy). Both proof scripts
record the compared values and fail on a vacuous run. Stand: `epe-reclass-n8n` on VPS loopback
`:25679`, throwaway DB `epe_reclass_20260824_0602` restored from a dated dump of live taken this
morning, fixtures 1301–1309 (grade coefficients deliberately different: 0.60 / 2.20 / 1.10), same
pinned image as live, guard imported under its live id and left inactive. Torn down at the end —
`epe_2026` is the only `epe_*` database left.

### 2.1 P (project, coefficient 2.20): soft exclusion, to the digit

P was evaluated by the manager on the full applicable set `{3:8, 4:6, 8:9, 12:7, 13:10}`
(stored `calculated_score` = **8.0**, the plain 5-row average), then given a c_level correction on
criterion 13 (6) and c_level_direct scores on criteria 1 (7) and 10 (8) — so the close's correction
and c_level branches, which BUG-039 records as never end-to-end exercised, both ran with real data.
Index values are the independent client-pipeline replica (formula #3 over emitted cells):

| state | matrix cells for P | final (cell mean) | bonus index |
|---|---|---|---|
| **I1** — project, with corrections | 1, 2, 3, 4, **8**, 10, 12, **13** | 7.571429 | **458.172** |
| **I2** — after P→general | 1, 2, 3, 4, 10, 12 — **8 and 13 gone, correction on 13 gone with its cell** | 7.2 | **300.168** |
| **I3** — after switching back | 1, 2, 3, 4, **8**, 10, 12, **13** | 7.571429 | **458.172 — equals I1 exactly** |

Throughout, `evaluation_scores` held all five manager rows `{3, 4, 8, 12, 13}` — measured by SQL in
the general state, unchanged. `admin/save-user` accepted both switches mid-campaign with 200 (no
freeze), and `is_project_participant` followed atomically.

While P was general, the **ordinary edit** was exercised both ways: an update payload including the
excluded criterion 8 → **422 `CRITERIA_NOT_APPLICABLE`**, rows untouched; a clean edit of the
applicable set `{3:8, 4:6, 12:7}` → **200**, `final_score` **7.0** (average of the applicable set
only), and rows 8/13 **survived the edit** — the DB still held `{3, 4, 8, 12, 13}`.

### 2.2 G (general, coefficient 0.60): reopen, additive, independent average

| step | compared values |
|---|---|
| G evaluated on `{3:8, 4:6, 12:9}` | 200; `evaluated_by_actor = true`, `missing_criteria_ids = []` |
| G → project | `evaluated_by_actor = **false**`, `missing_criteria_ids = **[8, 13]**` — the flag reopens naming the missing criteria |
| additive submit `{8:9, 13:7}` (with hostile `final_score: 999.99`) | 200, `scores_added = 2`, exactly 2 score rows added; DB rows now `{3, 4, 8, 12, 13}` |
| stored `calculated_score` | **7.8** = independent Python average (8+6+9+9+7)/5 = **7.8** = independent SQL `AVG` = **7.8**; the client's 999.99 is nowhere |
| flag after additive | `evaluated_by_actor = true`, `missing_criteria_ids = []` |
| second additive for the already-scored 8 | **409 `CRITERIA_ALREADY_SCORED`**, nothing changed |
| full re-submit of all five | **409 `CRITERIA_ALREADY_SCORED`**, `calculated_score` still 7.8 |

`has_self_review` and `has_evaluated_manager` stayed row-existence (both true after G's self-review
and upward evaluation, no per-criterion demand).

### 2.3 Write validation: 422, with row counts

| probe | response | rows before → after |
|---|---|---|
| manager submits `{8:5}` for N (general, never evaluated) | 422 `CRITERIA_NOT_APPLICABLE` | evaluations for N 0 → **0**, total score rows 7 → **7** |
| N's additive attempt `{8:5}` after a clean 3-criteria evaluation (N still general) | 422 `CRITERIA_NOT_APPLICABLE` — applicability precedes the additive branch | unchanged |
| N's self-review with `{3:5, 8:5}` | 422 `CRITERIA_NOT_APPLICABLE` | unchanged |
| update of P's evaluation including 8 while P general | 422 `CRITERIA_NOT_APPLICABLE` | rows `{3,4,8,12,13}` unchanged |
| **live**, weight floor: criterion 12 `weight: 0` / `weight: 0.09` | both **422 `INVALID_WEIGHT`** | stored weight 1.00 → **1.00** both times |
| stand, weight floor: 0 / 0.05 / 0.09 → 422; **0.1 → 200, stored 0.1**; original restored | | generator, tracked JSON and the live definition all carry `MIN_WEIGHT = 0.1` (the live graph was compared node-for-node to the generated artifact after the PUT) |

### 2.4 Close regression under the new filter

H1 was closed **while P was general** (and G project), after capturing the pre-close matrix. Every
fixture user's persisted `period_results` equal the independent client-pipeline replica to 4 dp:

| user | persisted final | replica final | persisted index | replica index |
|---|---|---|---|---|
| 1303 G (project at close, 5 rows incl. additive) | 7.8 | 7.8 | **71.208** | 71.208 |
| 1304 P (general at close — **8/13 and the correction excluded from the frozen numbers**) | 7.2 | 7.2 | **300.168** | 300.168 |
| 1308 N | 6.0 | 6.0 | 39.93 | 39.93 |
| 1309 R | 5.0 | 5.0 | 28.6 | 28.6 |
| 1301/1302/1305/1306/1307 (no countable cells) | NULL | None | NULL | None |

P's frozen index is the **excluded** one (300.168 < I1's 458.172). After close, P was switched back
to project: `period_results` stayed **byte-identical** (md5 `892f15f4…` before and after), while the
read-only `?period_id=2` matrix inspect — live-joined by design — showed **458.172 = I1 to the
digit** again. The status machine, atomicity and rollup were not touched (boundary); this re-run
proves the emission filter only.

### 2.5 BUG-041 runtime repro (row counts)

Carrier: R's evaluation, rows `{3, 4, 12}`, period closed (the exact state the RECON's race window
produces). Route level first: `POST api/update-evaluation` → **403 `PERIOD_CLOSED`**, rows
unchanged. Then the statement the route would have executed inside the race:

| run | statement | header rows | score rows before | score rows after |
|---|---|---|---|---|
| pre-fix | RECON §7.2 verbatim (old `!= 'closed'` reassertion, ungated DELETE) | **0** (the 403 path) | `{3, 4, 12}` | **`{3}` — two rows destroyed on a refused write** |
| post-fix | extracted from the deployed `Build Update SQL` template, same values, same state | **0** (the 403 path) | `{3, 4, 12}` (restored) | **`{3, 4, 12}` — zero rows deleted** |

The gate does not deaden the branch: during the campaign the same statement shape (valid header,
narrower applicable set) deleted actively-removed rows normally (§2.1's edit path upserted 3 and
preserved only the classification-excluded 8/13).

### 2.6 BUG-043: none, never id 5

| state | `current_period_id` | `actor_is_in_scope` | `period_in_preparation` |
|---|---|---|---|
| stand, draft (all four probed roles) | **null** | **null** | false |
| stand, after activate (preparation) | **2 — the H1 leaf** | true | **true** |
| stand, after close | **null** | null | false |
| **live**, post-deploy, all six roles | **null** (was **5** in the 2026-08-22 probe) | null | false |

### 2.7 Role × route regression on the touched routes

Stand: 6 roles × 12 probes (`reclass_proof.json` → `role_route_matrix`), 32 expectations green —
matrix admin/c_level/c_level-readonly 200 and hr/manager/employee 403; submit/update
`CAPABILITY_FORBIDDEN` for the read-only c_level and (stand) hr; self-review `ROLE_FORBIDDEN` for
admin/c_level; save-user/save-coefficients admin-only; score-correction refusing the read-only
c_level with `CAPABILITY_FORBIDDEN` and hr with `ROLE_FORBIDDEN`; close admin-only. Live: the same
sweep with non-mutating bodies (`live_reclass_probe.json`), all green, with one **live-vs-stand
difference that is a fact, not a defect**: live hr (id 52) carries `can_evaluate=true`, so its empty
submit probe answers 422 `INVALID_SUBJECT` past the guard rather than the stand fixture's 403. The
live probe's state fingerprint (criteria + coefficients + users classification + all four data-table
counts) was byte-identical before and after, probe sessions 8 → 8 → 0 residue.

### 2.8 Static

`npm test` — **272 passed, 0 failed** (was 263; the delta is the reclassification/leaf-period/floor
assertions plus four rewritten tests whose old expectations this brief deliberately changed: the two
save-user freeze tests, the `MIN_WEIGHT` negative assertion, and the employees draft-fallback
regression test — each rewrite states the new decided behaviour). `npm run build` clean.
`npx eslint` on every changed file: the same single pre-existing warning as at HEAD, no new findings.

**Not checked, stated plainly:** the new dashboard UI flow (the «Дооценить» card state → additive
modal showing only the missing criteria) was verified as source, build and API contract, not driven
in a browser — the stand was API-level and live has nothing campaign-shaped to render, the same
limit `LIFECYCLE_COEFF` §"NOT CHECKED" recorded for its frontend. First browser pass happens on the
next stand with a vite front, or on launch day's walk-through.

---

## 3. Deployment

Order: dumps → workflows → frontend → live probe. No migration (no schema change).

| step | evidence |
|---|---|
| dated dump of live `epe_2026` | `backups/2026-08-24-reclass/epe_2026_reclass_20260824_0602.dump` (79 343 bytes; the stand restored from it and verified 89 users + migration-014 column) |
| pre-PUT dump of the n8n app schema | `backups/2026-08-24-reclass/n8n_public_pre_reclass_20260824T060926Z.dump` (531 292 bytes, `postgres -n public`) |
| pre-deploy drift check | all 12 target workflows on live **byte-identical** (nodes + connections) to the HEAD generators — the PUT carried exactly this build's delta |
| 12 workflows | PUT via `scripts/deploy_reclass.py --apply` (`backups/2026-08-24-reclass/deploy_apply.json`); activation preserved on every one (`True → True`); live graph re-read and compared node-for-node after each PUT; tracked top-level exports refreshed from live behind `assert_not_a_generator_input` — including `API_ evaluations-matrix.json`, which had been the stale BUG-028 export and is now current |
| **Auth Guard** | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — checked before, after every single PUT, and at the end. **Unchanged.** |
| frontend | release `20260824T061101Z`, serving (`readlink` = `releases/20260824T061101Z`, site 200, fresh bundle `index-AsO3JRL3.js`); both deploy gates run by hand first (legacy `:5678` absent, `/webhook` present), then the script under the documented `grep -rqE` shim (ripgrep still absent on the laptop — BUG-040) |
| stand teardown | container removed, both `epe_reclass_*` databases dropped, VPS `/tmp` stand files removed, `epe_2026` the only `epe_*` database remaining, no unrelated container touched |

---

## 4. Surfaced for decision

1. **Score-correction writes still accept any criterion for any subject.** The brief's write
   validation names submit/additive/update (and self-review got the same predicate); the correction
   route was not named and was left as-is. Read-side this is safe — a correction on an excluded
   criterion disappears with its cell, proven in §2.1 — but an admin can still *store* a correction
   for a criterion the subject's classification excludes, and it would spring back into the money if
   the person is later switched to project. Same one-clause fix shape if wanted.
2. **The per-criterion flag encodes the manager form's presented set, including
   `managers_only → has_subordinates`.** That clause is presented-set fidelity, not classification
   (without it, no manager of a non-manager subject could ever be "done"). If the form's group
   conditions ever change, the flag's SQL must change with them — they are now two copies of one
   business rule, one in `EvaluationModal.jsx`, one in `Build Identity-Bound Query`.
3. **Additive concurrency has one theoretical residue.** Two *concurrent* additive submits for the
   same evaluation serialize on the row lock and cannot double-insert (unique index + inline overlap
   re-check → 409 `ADDITIVE_CONFLICT`), but if they carry *disjoint* criteria sets the second
   statement's recompute reads its own snapshot and can miss the first's rows in `calculated_score`
   (READ COMMITTED). Same evaluator, same subject, sub-second window, and the rating self-heals on
   the next write; the row data itself can never be wrong. Recorded, not fixed.
4. **`calculated_score` / `rating_*` are at-write snapshots, by design.** A classification switch
   with no subsequent write does not touch `calculated_score` (formula #1 is feedback, written at
   write time), so the archival per-source `rating_manager` can differ from the matrix `final_rating`
   after a switch — e.g. P closed with `rating_manager = 7.0` (the edit's applicable-set average)
   and `final_rating = 7.2` (cell mean incl. c_level rows). This is the documented
   `CALCULATION_MAP.md` §A.1 split, stated here so nobody "fixes" it.
5. **Live hr (id 52) has `can_evaluate=true`.** Surfaced by the live probe (§2.7). Consistent with
   the guard design (capability, not role, gates evaluation) and pre-existing — but it means an HR
   account with subordinates could submit manager-path evaluations. Worth a conscious yes/no from
   Alexander before launch.
6. **`BACKUP_FIX_2026-08-2x.md` was also missing from HANDOVER §10's report list** — the same class
   as BUG-044, found while fixing it. Added; nothing else in the list was missing against `ls docs/`.
7. **The self-review `work_category` staleness (RECON §3.2.1) is unchanged**, per the brief's
   boundary: a person switched mid-campaign still self-reviews against their login-time snapshot
   until re-login. Irrelevant today (no self criterion is project-scoped) but it will matter the day
   one becomes so.

---

## Appendix — files

**Generators:** `scripts/build_route_guard_workflows.py` (submit additive + applicability,
update soft-delete + applicability, self-review applicability, save-user freeze removal, weight
floor, close-dataset filter, leaf clauses on check-self-review/check-evaluated/get-my-manager),
`scripts/build_route_guard_deferred.py` (matrix emission filter, score-correction leaf clause),
`scripts/build_auth_workflows.py` (employees: leaf-only current period, per-criterion flag,
`missing_criteria_ids`).

**Deploy / proof:** `scripts/deploy_reclass.py`, `scripts/setup_reclass_throwaway.sh`,
`scripts/seed_reclass_throwaway.sql`, `scripts/prove_reclass.py`, `scripts/probe_live_reclass.py`.

**Tests:** `tests/routeGuardWorkflows.test.js`, `tests/routeGuardDeferred.test.js`,
`tests/authWorkflows.test.js`, `tests/evaluationStartGate.test.js`,
`tests/regressionWorkflowFixes.test.js` (272 total).

**Frontend:** `src/pages/Dashboard.jsx`, `src/components/EmployeeCard.jsx`,
`src/components/EvaluationModal.jsx`, `src/context/TaskStatusContext.jsx`,
`src/hooks/useDashboardData.js`.

**Docs:** `DECISIONS.md` (D-0822-3, amendments), `PROJECT_RULES.md` (session rule),
`docs/HANDOVER.md` (§3, §6.3, §10), `bugs.md` (BUG-041 runtime, BUG-043/044 closed, 19/25).

**Artefacts (gitignored):** `backups/2026-08-24-reclass/reclass_proof.json`,
`…/live_reclass_probe.json`, `…/deploy_apply.json`, `…/epe_2026_reclass_20260824_0602.dump`,
`…/n8n_public_pre_reclass_20260824T060926Z.dump`.
