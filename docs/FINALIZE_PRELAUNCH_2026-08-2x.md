# Finalization batch — corrections applicability, BUG-046/047, new-criterion path (2026-08-24)

**Brief:** finalization batch after the accepted Build 2 gate (`874a36b`). Three outcomes: (1) the
approved decision that correction writes enforce the same applicability rule as every other write
path; (2) BUG-046 (middle-manager matrix emission filter) and BUG-047 (D-0822-3 register wording)
closed; (3) the new-criterion path Alexander will use right after this batch, verified end-to-end
on a throwaway stand — **this batch created nothing on live; the ninth criterion is his to create
via the admin UI**. Launch stays paused; nothing was activated.

Everything behavioural ran on throwaway stand `epe_final_20260824_0828` (n8n `epe-final-n8n`, VPS
loopback :25679, restored from a dated dump of live taken at setup). Compared values:
`backups/2026-08-24-finalize/finalize_proof.json` — **90 checks, 0 failures** — and
`backups/2026-08-24-finalize/live_finalize_probe.json`. The stand is torn down: container removed,
`epe_final_*` dropped, VPS `/tmp` stand files removed, `epe_2026` the only `epe_*` database left.

---

## 1. Corrections applicability (approved decision, D-0822-3 extended)

**Change.** `POST api/admin/score-correction` (`API: Score Correction`) now enforces the same
shared predicate as submit / additive / update / self-review: a `project_participants` criterion
applies iff the subject is **currently** a project participant; a correction for an inapplicable
criterion answers the same 422 `CRITERIA_NOT_APPLICABLE` before any write. Implementation mirrors
the submit path: the subject lookup carries `subject_is_project` and `project_criteria_ids`
(`CORR_VALIDATE`), and `Decide Level` refuses on the same rule (`build_route_guard_deferred.py`).
Write-side only, as briefed — the read-side exclusion (corrections live inside the cell) was proven
in the reclass build and gate.

**Ordering decision, surfaced.** The new check sits **after the subject 404 and before the period
409 / ownership 403** — not last. Reasons: the refusal is non-mutating wherever it sits, and it
keeps the deployed rule provable on live while the launch is paused (otherwise every live probe
would stop at `NO_ACTIVE_PERIOD` and the deploy would be verifiable only by byte-identity).
*Correction (2026-08-24, BUG-048):* this paragraph originally gave a third reason — "the deployed
submit path already answers applicability before its relation checks, so this leaks nothing submit
does not" — and that reason is wrong. Submit answers `SCOPE_MISMATCH` / `PERIOD_NOT_STARTED` /
`CANNOT_EVALUATE` **before** its applicability 422, so it never reveals applicability on paused
live; the corrections ordering does give a role-gated writer a marginal pre-period classification
probe that submit does not offer. That cost was accepted by decision (D-0824-1: the pre-period
applicability answer is intentional). The relative order of all pre-existing checks is unchanged.

**Stand evidence** (`finalize_proof.json` → `corrections_applicability`, campaign running):

| write | writer | criterion | subject | result | corrections count |
|---|---|---|---|---|---|
| c_level level | admin 1301 | 8 (project) | 1308 general | **422 `CRITERIA_NOT_APPLICABLE`** | 0 → 0 |
| mid_level level | skip-level 1310 | 13 (project) | 1308 general | **422 `CRITERIA_NOT_APPLICABLE`** | 0 → 0 |
| c_level level | admin 1301 | 8 (project) | 1304 project | **200**, level `c_level` | +1 |
| mid_level level | skip-level 1310 | 13 (project) | 1304 project | **200**, level `mid_level` | +1 |
| c_level level | admin 1301 | 3 (all) | 1309 general | **200** | +1 |

Both directions of the predicate are exercised for both writer levels; exactly the three applicable
writes were stored.

**Live probe pair, post-deploy** (`live_finalize_probe.json`; launch paused, so every answer is a
refusal and nothing needed cleanup): admin probe session (marked jti, deleted in `finally`) against
live subject id 3 (general): criterion 8 → **422 `CRITERIA_NOT_APPLICABLE`** («Критерий 8 —
проектный, а сотрудник сейчас не участник проекта»); criterion 3 → **409 `NO_ACTIVE_PERIOD`** (the
applicable write falls through to the period gate — non-mutating while paused). `score_corrections`
0 → 0.

## 2. BUG-046 closed — the middle-manager matrix gets the same one clause

Exactly the clause the bug named, in the row-source `WHERE` of `MANAGER_MATRIX_INNER_SQL`'s
`CROSS JOIN` — same text and position as the admin matrix and the close dataset:
`AND (c.target_audience <> 'project_participants' OR u.is_project_participant = true)`.

**Stand evidence** (`finalize_proof.json` → `bug046`): middle manager 1310 (manager-of-managers
above 1302) reads `GET api/manager-subordinates-matrix` over span {1303, 1304, 1308, 1309}.
Project subject 1304 carries manager scores on the full set, a `c_level` correction on criterion 8
and a `mid_level` correction on criterion 13 (both = 6):

| state | emitted cells for 1304 | corrections emitted | DB score rows | DB correction rows |
|---|---|---|---|---|
| project | [2, 3, 4, 8, 12, 13, 14] | cell 8: c_level 6; cell 13: mid_level 6 | [3, 4, 8, 12, 13, 14] | 2 |
| → general | **[2, 3, 4, 12, 14]** | **none** (excluded cells take theirs with them) | [3, 4, 8, 12, 13, 14] | 2 |
| → project | [2, 3, 4, 8, 12, 13, 14] | both back, values unchanged (6/6) | [3, 4, 8, 12, 13, 14] | 2 |

The admin matrix emitted the same criteria set for 1304 in the general state (modulo its
`c_level_only` cells 1/10, which the middle-manager matrix never emits) — the two surfaces no
longer contradict each other after a switch. BUG-047's fix is §4.

## 3. New-criterion path, verified end-to-end — the answers

The stand created a criterion **exactly as Alexander will**: the same `POST manage-criteria
{action: 'save'}` the UI sends (`useCriteria.saveCriterion`), shape *all / self off / manager on /
c_level off*, 10 level texts, while H1 was **draft** — the only order production allows, since the
catalogue freezes at «Запустить оценку» (409 `EVALUATION_STARTED`). It got id 14 on the stand.

**Does Manage Criteria seed `score_coefficients` rows?** **No — 0 rows** (expected). More: the
criteria editor **cannot set a weight at all** — the UI has no weight field and the INSERT names no
weight column, so the criterion lands with the DB default `weight = 1.00`. The weight the brief
mentions is set on `/admin/scoring`, nowhere else.

**Does `/admin/scoring` render the unseeded criterion?** **Yes.** `GET /api/score-coefficients`
returns it with the server-side fill — weight 1.0, levels 1..10 all 1.0 — and the page renders
whatever that list contains (`useScoreCoefficients` → `AdminScoring`). Saving through the existing
upsert then **created exactly 10 rows** (weight 1.8, all level coefficients 1.05 on the stand) and
the GET returned the explicit values. `GET /api/criteria` also served the criterion to a manager
with `weight` stripped and `selfassesment=false` intact, so every form filter sees the right flags.

**Do matrix, additive flow and close pick it up for every subject?** **Yes, all three.**
- Admin matrix: a cell for criterion 14 for every fixture subject — project 1304, general 1308,
  and unevaluated 1303 alike (project criteria remain the only audience-filtered cells). The
  middle-manager matrix likewise.
- The per-criterion completion flag counts it: after the manager submitted the **old** 3-criteria
  set for general 1308, `/api/employees` answered `evaluated_by_actor=false,
  missing_criteria_ids=[14]` — the task stays open for exactly the new criterion; the additive
  submit of `{14: 7}` added exactly one row (DB rows `[3, 4, 12, 14]`) and closed the flag. An
  evaluation that predates the criterion therefore reopens correctly.
- Close persisted results for both evaluated subjects including the criterion (below).

**What do the money paths compute while coefficient rows are absent?** **A silent 1.0 fallback —
which is why the `/admin/scoring` save step is mandatory.** The same scores were closed twice on
the stand (stand-only SQL surgery reopened the throwaway's period between the closes; live close
stays irreversible): subject 1308, grade S2 (coefficient 1.10), scores {3: 6, 4: 6, 12: 6, 14: 7}:

| state of criterion 14 | its term in formula #3 | persisted `bonus_index` | independent replica |
|---|---|---|---|
| no coefficient rows, default weight | 7 × **1.0 × 1.0** = 7.00 | **47.63** | 47.63 |
| after the save (weight 1.8, coef 1.05) | 7 × **1.05 × 1.8** = 13.23 | **54.483** | 54.483 |

Delta 6.853 = (13.23 − 7.00) × 1.10 — exactly the new criterion's term, to the digit. The
`final_rating` (6.25) did not move: ratings ignore coefficients by design (§4 formulas untouched).
Subject 1304 (corrections + the new criterion, grade 2.20): 267.344 → 281.05, both equal to the
replica. Nothing errors while the rows are absent — the fallback is silent on every surface (GET
fill, client matrix, close compute), so **create → save coefficients on /admin/scoring → verify the
numbers** is the required sequence, and it must all happen before «Запустить оценку» only as far as
the criterion itself; the coefficient save stays legal until close (D-0822-2).

## 4. BUG-047 closed, and the register extended

`DECISIONS.md` D-0822-3 third bullet now states the deployed truth: a full re-submit answers the
same 409 `CRITERIA_ALREADY_SCORED`; `DUPLICATE_EVALUATION` remains only on the concurrent-create
race in `Format Response` — matching the deployed `Build Insert SQL`, `docs/RECLASS_2026-08-2x.md`
§1.2 and the gate's runtime record. The write-validation bullet of the same decision now also
records the approved corrections extension (§1 of this report), so the register no longer
understates the deployed rule set.

## 5. Deploy and discipline

- **Zero-drift check before the PUTs** (`scripts/check_live_drift.py`, added this batch — full
  generator corpus vs live `workflow_entity` by SQL): 28 identical, changed = exactly
  {`API: Score Correction`, `API: Manager Subordinates Matrix`}, absent = the two deliberately
  deleted workflows. **After** the deploy: 30 identical, 0 changed.
- **Dumps before the PUTs:** dated `epe_2026` dump (taken by the stand setup, local copy in
  `backups/2026-08-24-finalize/`) and an n8n application-schema dump
  (`n8n_public_prefinalize_20260824.dump`, 537 KB, local copy).
- **PUTs** via `scripts/deploy_finalize_prelaunch.py` (deploy_reclass contract): Score Correction
  `rSZcm0HDMUHLYk8W` → `updatedAt=2026-08-24T08:33:49.866Z`, Manager Subordinates Matrix
  `EyvFZJGDxQNL20tC` → `updatedAt=2026-08-24T08:33:51.330Z`; activation preserved, each live graph
  re-read and node-identical to the generator, **Auth Guard untouched at
  `2026-08-18T16:34:30.674Z` / `active=false`** before, between and after.
- **Live money inputs unchanged:** weights + level coefficients + grades fingerprint
  `b0bd0f55ca92c69c65912bd9f151bf89` identical before and after the deploy+probes; all data tables
  still 0; no period state touched.
- **Role×route regression on the two touched workflows** (stand, 7 actors): score-correction —
  422 `INVALID_BODY` for admin/c_level/manager/mid-manager (past the guard, refused on content),
  403 `CAPABILITY_FORBIDDEN` for read-only c_level, 403 `ROLE_FORBIDDEN` for hr and employee;
  manager-subordinates-matrix — 200 for admin/c_level/read-only c_level/mid-manager,
  **403 `OWNERSHIP_FORBIDDEN` for a manager whose reports have no reports** (pre-existing rule,
  re-confirmed), 403 `ROLE_FORBIDDEN` for hr and employee.
- `npm test` **274 passed / 0 failed** (was 272; two new static tests in
  `tests/routeGuardDeferred.test.js`: the correction applicability inputs+error, and the
  matrix row-source clause).

**Deploy defect found and fixed on the way** (the `assert_not_a_generator_input` guard worked as
designed): the export refresh refused `API_ Manager Subordinates Matrix.json` because
`build_route_guard_deferred.py` still read the old matrix SQL from it (`MANAGER_MATRIX_SQL =
legacy_query(...)`) — **dead code** since the inner SQL was rewritten inline, but a build-time
input nonetheless, and refreshing the export would have replaced the read value with a `dummy_if`
expression on the next regeneration. The dead read was removed (generator output byte-unchanged,
suite green) and the export then refreshed from verified live. Both PUTs had already landed and
verified before the refusal; nothing on live was affected. This also progresses BUG-045: the
Manager Subordinates Matrix export was one of its four pre-guard shapes — nine stale exports
remain, and `check_live_drift.py` now gives the full-corpus comparison on demand.

## 6. Riders

- **HANDOVER §10** reconciled: counters 19/25 (three rows stale) → true 22/25 → **20 open / 27
  closed** after this batch's closures; report index gains `GATE_RECLASS_2026-08-2x.md` (it had
  been omitted — the same §10 gap class as BUG-044) and this report.
- **HR `can_evaluate` (for Alexander to confirm): live has TWO carriers, not one.**
  Liya Dmitriyeva (id 52) **and Sona Rahmanova (id 80)**, both `role=hr`,
  both `can_evaluate=true` and `can_be_evaluated=true`, both managed by **Jemal Gulberdiyeva
  (c_level, id 47)**. The reclass report had surfaced only id 52. `can_evaluate=true` is what lets
  an HR account submit upward/self evaluations as an ordinary participant; it does **not** open the
  correction route (role gate: admin/c_level/manager only) or any admin read. If only the HR lead
  should carry it, one of the two flags is for him to clear in Admin → Сотрудники.
- bugs.md: BUG-046 and BUG-047 closed with the evidence above; BUG-045 progress note.
- `PROGRESS.md` appended; committed and pushed.

## 7. Boundaries kept

Auth Guard canonical untouched (frozen `updatedAt` asserted at every step). §4 formulas untouched —
this batch changed which cells exist and which writes are refused, never how numbers combine.
Close/status machinery untouched (the two stand closes used the deployed route as-is; the reopen
between them was SQL on the throwaway only). 2025 archive untouched. No mail. Nothing activated on
live — H1 is still draft, `evaluation_started_at` NULL, all data tables 0. BUG-042 and the BUG-029
read-side residue remain open and out of scope.
