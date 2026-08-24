# Gate: Build 2 verification (live reclassification, BUG-041/043, riders)

**Date:** 2026-08-24, 07:20–07:50 UTC · **Brief:** verification gate for `docs/RECLASS_2026-08-2x.md`
(commit 39e34fd) · **Mode: read-only toward the system** — SELECT / GET / `readlink` / local
`pg_restore` of the recorded dump only. No workflow PUT, no DB write, no deploy, no mail, and no live
HTTP probe (see NOT-CHECKED — a valid probe session cannot be minted without writing to
`auth_sessions`).

**Verdict in one line.** Every claim of the build that this gate could reach is **confirmed** — the
money figures re-derive to the digit from recorded inputs with independent arithmetic, the deployed
definitions carry exactly the SQL the report describes, live is campaign-inert and drift-free — with
**three new findings filed** (BUG-045, BUG-046, BUG-047), none of which refutes a build claim: a
wider stale-export class than BUG-028 records, a third corrections-reading matrix surface without the
applicability clause, and one wrong sentence in the D-0822-3 decision text.

Method note: all 12 target workflows on live were proven **node-for-node identical to the HEAD
generators by this gate's own comparison** (nodes, connections, name, settings subset — fetched from
`workflow_entity` via SQL, compared against freshly generated output). Every "deployed SQL" statement
below therefore reads the live definition and the generator output at once.

---

## 1. Money math, independently — CONFIRMED

**Artifacts:** both exist, on this laptop only —
`backups/2026-08-24-reclass/reclass_proof.json` (148 checks, failures `[]`) and
`…/live_reclass_probe.json` (failures `[]`), with `deploy_apply.json`, `throwaway_env.json`, two
`epe_2026` dumps and the n8n pre-PUT dump beside them. All are **gitignored** (`.gitignore:21
backups/`), so they are not in version control: the evidence base survives exactly as long as this
machine does. Graded accordingly: the artifacts are genuine recorded-value files (they carry compared
tuples, not slogans), but a future session cannot re-read them from the repo.

**Re-derivation.** Inputs taken only from recorded sources: submitted scores from
`scripts/prove_reclass.py` (P manager `{3:8, 4:6, 8:9, 12:7, 13:10}` + c_level correction 13→6 +
c_level_direct `{1:7, 10:8}`; G `{3:8, 4:6, 12:9}` + additive `{8:9, 13:7}`; N `{3,4,12}=6`; R
`{3,4,12}=5`), grade coefficients from `scripts/seed_reclass_throwaway.sql` fixture grades (S4-M1
2.20 / S1 0.60 / S2 1.10), weights and per-level coefficients extracted from the recorded dump
`epe_2026_reclass_20260824_0602.dump` by local `pg_restore` (the stand was restored from this same
dump). Formula semantics from `CALCULATION_MAP.md` R13–R16 / HANDOVER §4 #3, implemented as a fresh
script — **not** the build's `client_pipeline` replica.

| figure | claimed | re-derived | arithmetic |
|---|---|---|---|
| I1 final / index | 7.571429 / **458.172** | 7.571429 / **458.172** | cells 1:7, 3:8, 4:6, 8:9, 10:8, 12:7, 13:mean(10,6)=8 → 53/7; Σ(score·coef·weight)=208.26 × 2.20 |
| I2 final / index | 7.2 / **300.168** | 7.2 / **300.168** | 8/13 cells and the 13-correction gone → 36/5; 136.44 × 2.20 |
| I3 | = I1 exactly | = I1 exactly | same cells re-emitted |
| close 1303 G | 7.8 / **71.208** | 7.8 / **71.208** | 5 cells incl. additive; 118.68 × 0.60 |
| close 1304 P | 7.2 / **300.168** | 7.2 / **300.168** | frozen as the excluded I2 shape |
| close 1308 N | 6.0 / **39.93** | 6.0 / **39.93** | 36.3 × 1.10 |
| close 1309 R | 5.0 / **28.6** | 5.0 / **28.6** | 26.0 × 1.10 |
| additive average | **7.8** | **7.8** | (8+6+9+9+7)/5 |

Every figure reproduces exactly; nothing was unreproducible. The dump itself also confirms the stand
started from campaign-zero live state (evaluations / scores / corrections / period_results all 0
rows, 89 users, periods closed/draft/draft).

## 2. Emission filter in the deployed definitions — CONFIRMED

Read from live `workflow_entity` (= generator output, see method note):

- `API: evaluations-matrix` → `Build Matrix Query`: the row source is `CROSS JOIN criteria c` with
  `WHERE u.role != 'admin' AND c.is_active = true AND (c.target_audience <> 'project_participants'
  OR u.is_project_participant = true)` — the applicability clause sits in the row-source WHERE next
  to `is_active`, so the excluded cell is not emitted. `mid_level_correction` / `c_level_correction`
  are correlated sub-selects **inside** `json_build_object` (and period-bound), so corrections ride
  their cell. `c_level_only` emission unchanged (cell-internal `c.c_level_only` conditions only);
  `managers_only` cells still emitted for everyone (empty for non-managers), unchanged.
- `API: Manage Periods` → `Build Close Dataset Query`: `criteria_data` now carries
  `target_audience`; the per-participant aggregation filters `WHERE cd.target_audience <>
  'project_participants' OR u.is_project_participant = true`, corrections again inside the cell.
- **Formulas untouched, no denominator anywhere:** close-side `Compute Close Results` computes
  `finalOf` = D-0820-12 mean and `weightedSum × grade_coefficient` with no ÷Σweights; client
  `useFinalScoresMatrix.js` at HEAD identical shape (`weightedSum * gradeCoefficient`);
  `calculated_score` stays a plain average in every write-path SQL. My §1 re-derivation matching all
  seven persisted values is the arithmetic proof that this pipeline is what actually ran.

## 3. Write-path applicability and the additive branch — CONFIRMED

All from the deployed text (`API: Submit Evaluation` → `Validate Evaluation` / `Build Insert SQL` /
`Format Response`; `API: Update Evaluation WITH PERIOD` → `Build Update SQL`; `API: Submit Self
Review` → `Build Self Review Insert`):

- **422 precedes the additive branch.** In `Build Insert SQL` the `CRITERIA_NOT_APPLICABLE` return
  is emitted before the `existingEvaluationId` branch is entered — an inapplicable criterion never
  reaches additive logic. Same predicate in update and self-review.
- **Additive inserts only missing applicable criteria.** Overlap with `existing_criteria_ids` → 409
  `CRITERIA_ALREADY_SCORED` before SQL; in SQL, `target_eval` re-asserts the overlap inline
  (`NOT EXISTS … JOIN score_rows`), plus active+started period, `FOR UPDATE OF e` — all three
  additive CTEs hang off that one gate (the BUG-041 rule). A zero-row outcome answers **409
  `ADDITIVE_CONFLICT`** in `Format Response`; the concurrent-create race keeps 409
  `DUPLICATE_EVALUATION` on the insert path.
- **No client total is read on submit/additive/update.** Insert: `calculated_score =
  (SELECT AVG(score_val) FROM score_rows)`. Additive: SQL recompute over surviving rows filtered by
  the subject's *current* classification `UNION ALL` the new values. Update: `AVG` over the submitted
  set. `final_score` from the body is never referenced. (Self-review `calculated_score` remains the
  client's number, range-checked 1–10 — pre-existing W4 design, outside this build's claim;
  `weighted_score` is server-computed with formula #2 and the real grade coefficient, 422
  `NO_GRADE_COEFFICIENT` without one.)
- **Update deletes only actively-removed applicable criteria.** `removed_scores` carries both
  `AND EXISTS (SELECT 1 FROM updated_header)` — **the BUG-041 gate, present in the deployed
  text** — and the `NOT EXISTS (… target_audience = 'project_participants' AND
  subj.is_project_participant = false)` skip, so classification-excluded rows survive any edit.
- **The claimed indexes exist on live** (`pg_indexes`, epe_2026): `idx_evaluation_scores_unique
  (evaluation_id, criteria_id)` — the arbiter behind the additive safety and the update upsert —
  plus `idx_evaluations_unique_non_self_period`, `idx_evaluations_unique_self_period`,
  `idx_score_corrections_unique_period`.

*Concurrency nuance (observation, unverifiable read-only):* for two concurrent additive submits
carrying the **same** criterion, whether the loser's overlap re-check sees the winner's committed row
depends on EvalPlanQual/snapshot details; the guaranteed backstop is the unique index, which may
surface as an n8n DB error rather than the clean 409. Data-safe in every interleaving (no double
insert, no lost row); the disjoint-set snapshot residue is already recorded as report §4.3.

## 4. The intentional gap (score-correction writes) — CONFIRMED, not fixed

Deployed `API: Score Correction` → `Validate Input` / `Decide Level`: the body is validated only for
finite integers and 1–10 range; `criteria_id` is checked for **nothing else** — not existence, not
`is_active`, not applicability. The upsert keys `(subject_id, criteria_id, correction_level,
period_id)`. So an admin can still store a correction for a criterion the subject's classification
excludes, exactly as report §4.1 states, and it springs back into the money if the person later
switches to project. Read-side exclusion holds in **both money readers** (§2: matrix and close read
corrections only through per-cell sub-selects, and the cell is not emitted). Left as-is per the
brief. One adjacent surface the build did not name reads corrections without the clause —
**BUG-046** (§8).

## 5. Live inertness and integrity — CONFIRMED (one benign delta, two findings on exports)

All measured live 2026-08-24 07:21–07:45 UTC:

| check | result |
|---|---|
| periods | 1 closed / 2 draft / 5 draft; `evaluation_started_at` NULL on all three |
| data tables | evaluations 0 · evaluation_scores 0 · score_corrections 0 · period_results 0 |
| probe residue | users 1301–1310: **0 rows**; no fixture sessions |
| auth_sessions | **9** (probe recorded 8 → 8). The 9th: user 2 (Alexander), `issued_at 2026-08-24 07:19:57Z` — a real login two minutes before this gate's query, after the build. Not residue. |
| Auth Guard | `updatedAt = 2026-08-18 16:34:30.674Z`, `active = false`, and its live graph is node-identical to `build_auth_workflows.py` output |
| 12 target workflows | all `active=true`, `updatedAt 2026-08-24 06:10:02–06:10:17Z`, **byte-identical to HEAD generators now** (this gate's own node-for-node comparison) |
| all other generated workflows | the remaining 19 generator outputs that exist on live are **also identical** — zero drift anywhere; the 2 with no live counterpart are the deliberately deleted `Get Employee Self Review` / `Get Admin Data Fixed` (HANDOVER §2) |
| deploy order | pre-PUT n8n dump stamped 06:09:26Z, PUTs 06:10:02–17Z — ordering holds; `deploy_apply.json`: 12/12 changed, activation `True → True` on every one |
| state fingerprint | recomputed now with the probe's own SQL: `ebd15644…/8fcb8817…/66516149…/0/0/0/0` — **equal to the probe's before and after** values; live money inputs have not moved since the build |
| frontend | `readlink` = `releases/20260824T061101Z`, site 200, bundle `index-AsO3JRL3.js` |
| trio guards | `can_be_evaluated = true` required in **all three** relation filters of the deployed Submit Evaluation + the e-mail denylist on the c_level_direct branch; live 21/40/61: `can_evaluate=false, can_be_evaluated=false, grade NULL` |
| classification | 48 general / 41 project, `is_project_participant` agrees on all 89, zero tender, zero NULL `work_category` |
| stand teardown | `epe_2026` is the only `epe_*` database; no reclass container (`docker ps -a`); no reclass files in VPS `/tmp` |

**Top-level exports vs live — they do NOT all match, so BUG-028 is narrowed, not closed.** All 12
build targets match live (including `API_ evaluations-matrix.json`, BUG-028's named instance — now
current). But **10 of the 37 top-level exports differ materially from live** (stale `jsCode`, and
four of them — `All-evaluation`, `Analytics Dashboard`, `Manager Subordinates Matrix`,
`evaluation-details-by-user` — are **pre-Auth-Guard** shapes, the exact stand-seeding hazard BUG-028
records), and 2 name deleted workflows. Filed as **BUG-045** with the file list; BUG-028's row stays
open as written until the class is resolved.

## 6. Completion-flag semantics — CONFIRMED (one recorded nuance)

- Deployed `Build Identity-Bound Query`: `evaluated_by_actor` = evaluation exists **and** no active,
  non-`c_level_only` criterion that is applicable (`project_participants` → current
  `is_project_participant`; `managers_only` → `has_subordinates`) lacks a score row by this actor;
  `missing_criteria_ids` uses the identical set. `has_self_review` / `has_evaluated_manager` remain
  plain EXISTS — row-existence, as claimed.
- Presented-set comparison (source): `filterCriteriaByEmployee` + the modal's group conditions
  produce, for a **regular manager**, exactly the flag's set. **Nuance:** for a `c_level` evaluator
  the form also presents the two `c_level_only` criteria (`groupConfigData` keys on the evaluator
  role), which the flag never demands. Benign today — the modal blocks submit until every *visible*
  criterion is scored, so a c_level-authored evaluation can't be created partial through the UI —
  but the "two copies of one business rule" (report §4.2) already differ for c_level-as-manager
  evaluators, and live has 18 subjects reporting to c_level 18/47. Recorded here for the §4.2
  decision; no bug row (no reachable wrong state).
- Consumers agree at source level: `Dashboard.jsx:135` keys on `evaluated_by_actor === true`,
  `TaskStatusContext.jsx:121` computes «все подчинённые оценены» as
  `every(evaluated_by_actor === true)` (no check-evaluated dependence for doneness — that route now
  feeds score display only via `useDashboardData`), the additive modal presents only
  `missing ∩ applicable`, and every mode submits only the visible criteria
  (`EvaluationModal.jsx:352`). «Дооценить (N)» card present (`EmployeeCard.jsx:211–220`).

## 7. Docs and process — CONFIRMED (one discrepancy → BUG-047)

- `DECISIONS.md`: D-0822-3 present; D-0822-1 amended (emergency stop halts the campaign; start mark
  survives deactivation — both "confirmed intended"); D-0822-2 amended (floor 0.1, message still
  names `is_active`; deployed `MIN_WEIGHT = 0.1` verified in the live text); S4-M1/M1 one-logical-
  grade note present. **Discrepancy:** the D-0822-3 bullet says a full re-submit "stays 409
  `DUPLICATE_EVALUATION`" — the deployed code and the build's own proof (§2.2) answer **409
  `CRITERIA_ALREADY_SCORED`**; `DUPLICATE_EVALUATION` survives only on the concurrent-create race.
  The RECLASS report states it correctly; the decision register does not → **BUG-047**.
- `PROJECT_RULES.md`: the one-directory-one-session rule present (§ "Sessions", added 2026-08-24).
- `HANDOVER.md`: §3 now states classification editable mid-campaign (D-0822-3); §6.3 no longer a
  hard gate — both freeze statements corrected in place. §10 report list carries RECON_RECLASS_COEFF
  · LIFECYCLE_COEFF · GATE_LIFECYCLE_COEFF · RECLASS **and** BACKUP_FIX; diffed against `ls docs/`,
  the only unlisted .md files predate the list's era (IMPORT/STEP1/SYSADMIN/INCIDENT/
  n8n_deactivation/REVIEW_H1 — same boundary the previous gate accepted). Counters 19/25 consistent
  with `bugs.md` (44 rows; status-line count 19 OPEN / 25 CLOSED). *This gate's three new rows make
  those counters 22/25 — bugs.md statistics updated here; HANDOVER §10's copy goes stale by three
  and reconciles at the next handover pass, per the brief's "nothing else" boundary.*
- `bugs.md`: BUG-041 closed **with** the runtime repro table (row counts, pre/post-fix); BUG-043
  closed with live + stand evidence; BUG-044 closed with the §10 fix; **BUG-042 open and untouched;
  BUG-029 closed with its read-side residue explicitly recorded** — and this gate re-verified the
  `|| 1.0` defaults are still present (untouched) in the deployed `Compute Close Results`.
- Git: working tree clean; `origin/main` = 39e34fd (ls-remote), no merge commits — linear. Re-ran
  `npm test`: **272 passed, 0 failed**. `npm run build` clean (standard chunk-size warning only).
  `npx eslint` on the build's five frontend files: the same single pre-existing
  `react-refresh/only-export-components` warning, nothing new.

## 8. Adversarial pass — three new findings, rest holds

Hunted specifically for what the build's proof design could not catch:

1. **Fixture-shaped expectations (9 stand users vs 89 live).** Confirmed live-vs-stand deltas are
   facts, not defects: hr id 52 `can_evaluate=true` re-measured (report §4.5 stands, Alexander's
   call pending). **Coverage hole found (not a defect):** every stand *subject* had
   `has_subordinates=false`, so the flag's `managers_only → has_subordinates` arm and the 6-criteria
   project+manager shape were never runtime-driven — SQL-verified only (§6). Similarly the
   `mid_level` branch of close-side `finalOf` still has no end-to-end run (the build exercised the
   c_level correction and c_level_direct branches; BUG-039 remains open, correctly).
2. **Predicate edge cases.** `users.is_project_participant` is `NOT NULL DEFAULT false` on live, so
   the applicability predicate can never see NULL; `work_category` is nullable in schema but
   save-user validates `general`/`project` and writes both atomically (deployed upsert text), live
   has zero NULLs. NULL-grade subjects: only the trio, who are `can_be_evaluated=false` and can
   never acquire data; close guards with the recorded BUG-029 residual. **Inactive criteria:** the
   write-validation's `project_criteria_ids` is deliberately not filtered by `is_active` — an
   inactive project criterion still 422s for a general subject (fails safe). Latent oddity: a stored
   score row for a criterion later made inactive would count in the additive recompute's average but
   not in the matrix — unreachable through the API within one period (catalogue freezes at start,
   D-0822-1), noted for the multi-period future, no row. **Upward path:** not caught by the new
   422 — the upward form submits only criterion 2 (`managers_only`), and the predicate constrains
   only `project_participants` criteria; an upward payload smuggling 8/13 for a general manager is
   correctly refused.
3. **"Current period" resolvers beyond BUG-043's six.** Full sweep of every generated workflow: the
   six campaign routes (submit, self-review, check-self-review, check-evaluated, get-my-manager,
   score-correction) plus `/api/employees` all carry the leaf predicate. Resolving on `is_active`
   alone: the admin/reporting reads (documented boundary — matrix, analytics, all-evaluations,
   details-by-user, manager-subordinates-matrix) **plus** `admin-users-data`'s two status
   subqueries, `hr-evaluation-status`, and the dead `employee-self-review` route. All pre-existing,
   read-only surfaces; a misbinding requires a hand-forged SQL state that the deployed activate/
   start/close SQL refuses to create. No new row.
4. **New findings filed:**
   - **BUG-045 (Low):** the BUG-028 class is 10 files wide — 10 top-level exports materially stale
     vs live (4 of them pre-Auth-Guard), 2 more name deleted workflows. The named BUG-028 instance
     itself is now current.
   - **BUG-046 (Medium):** `API: Manager Subordinates Matrix` (`EyvFZJGDxQNL20tC`) emits
     `project_participants` cells — scores **and corrections** — for subjects who are currently
     general: its row source has no applicability clause (`WHERE c.is_active = true AND
     c.c_level_only = false` only). A middle manager's matrix disagrees with the admin matrix, the
     close numbers and the reopened-task flag after any switch. Read-only surface, not a money
     producer (the bonus index is computed from `evaluations-matrix` and at close), which is why the
     build's proofs could not see it.
   - **BUG-047 (Low, docs):** the D-0822-3 full-re-submit sentence in `DECISIONS.md` (§7 above).

## NOT-CHECKED (mandatory)

- **No live HTTP probes were run by this gate.** Minting an accepted session requires inserting an
  `auth_sessions` row — a DB write, out of read-only bounds. Live behavioural claims rest on three
  legs: definitions byte-identical to generators (this gate's comparison), the build's recorded
  probe artifact, and the state fingerprint this gate recomputed matching that artifact exactly.
- **The stand run was not re-executed** (torn down by design). All of its money outputs were
  independently re-derived instead (§1); its 148-check pass is taken as recorded.
- **BUG-041's statement-level repro was not re-run** (needs a writable stand); re-verified as
  deployed SQL text plus the recorded row counts.
- **The additive/«Дооценить» UI flow is still not browser-driven** — same standing gap the build
  recorded; nothing campaign-shaped exists on live to render. First browser pass remains owed on the
  next stand or launch-day walk-through.
- **Frontend bundle equivalence to HEAD was not proven bit-for-bit** (release stamp, symlink and
  bundle filename verified; Vite builds are not byte-reproducible here).
- **Concurrent-write interleavings** (same-criteria additive race, §3 nuance; the recorded §4.3
  disjoint-set residue) — unverifiable without concurrent live writes.
- **Runtime coverage holes inherited from the fixture shape** (managers_only flag arm, 6-criteria
  subject, `finalOf` mid_level branch) — source-verified only, listed in §8.1.

## Session facts

Read-only throughout: SSH SELECTs against `epe_2026` and the n8n `public` schema, `readlink`, one
HTTPS GET of the site root, local `pg_restore` of the recorded dump into a text file (no database
created), local `npm test` / `npm run build` / `npx eslint`. No workflow touched, no row written, no
mail sent. Deliverable: this report + three `bugs.md` rows (and its statistics table) — nothing else.
