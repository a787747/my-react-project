# Gate: Finalization-batch verification (corrections applicability, BUG-046/047, new-criterion path)

**Date:** 2026-08-24, 09:07–09:35 UTC · **Brief:** verification gate for
`docs/FINALIZE_PRELAUNCH_2026-08-2x.md` (commit `bfca5e1`) · **Mode: read-only toward the system** —
SELECT over SSH, local `pg_restore` of the recorded dump, local generator runs, local `npm test`.
No workflow PUT, no DB write, no deploy, no mail, no live HTTP probe (a valid probe session cannot
be minted without an `auth_sessions` INSERT — same constraint as the previous gate).

**Verdict in one line.** Every claim of the batch that this gate could reach is **confirmed** — all
four money figures re-derive to the digit with fresh arithmetic, the deployed definitions carry
exactly the SQL the report describes, full-corpus drift is zero by this gate's own comparison, live
is campaign-inert with no stand or probe residue, and the docs counters count out exactly — with
**two new findings filed** (BUG-048, BUG-049), one of which refutes a *justification sentence* in
the report's §1 (not the deployed behaviour, which is as claimed).

Method note: live definitions were fetched from `workflow_entity` by SQL (36 rows, saved to this
session's scratchpad) and compared against freshly generated output from all three builders — this
gate's own code, not `check_live_drift.py` (which was read but not trusted). Every "deployed SQL"
statement below therefore reads the live definition and the generator output at once.

---

## 1. Money, independently — CONFIRMED (all four figures, to the digit)

**Artifacts:** all five exist at `backups/2026-08-24-finalize/` — `finalize_proof.json` (90 checks,
failures `[]`), `live_finalize_probe.json` (failures `[]`), `epe_2026_final_20260824_0828.dump`
(79 KB), `n8n_public_prefinalize_20260824.dump` (537 KB), `throwaway_env.json`. **They are NOT
committed**: `.gitignore:21` excludes `backups/` (PII/password-hash rationale). Laptop-only evidence,
same grading as the reclass gate: genuine recorded-value files, unreadable to a future session.

**Re-derivation.** Inputs taken only from recorded sources: weights, per-level coefficients and
grade coefficients extracted from the recorded dump by local `pg_restore` (criteria 3/4/12: weights
3.00/1.50/1.00, level-6 coefficients all 1.10, level-7 1.30/1.20/1.30, level-8 for 8/13: 1.60/2.80;
grades S2=1.10, S4-M1=2.20); fixture scores from `scripts/prove_finalize.py` (N `{3:6,4:6,12:6,14:7}`;
P manager `{3:8,4:6,8:9,12:7,13:10,14:7}` + corrections 8→6 c_level, 13→6 mid_level); criterion 14's
two states from the proof JSON (absent rows / weight 1.8 + coefficient 1.05). Formula #3 semantics
from HANDOVER §4, implemented as a fresh script — not the build's `client_pipeline` replica.

| figure | claimed | re-derived | arithmetic |
|---|---|---|---|
| 1308 close #1 | 6.25 / **47.63** | 6.25 / **47.63** | (19.8 + 9.9 + 6.6 + 7×1.0×1.0) × 1.10 = 43.30 × 1.10 |
| 1308 close #2 | 6.25 / **54.483** | 6.25 / **54.483** | (36.30 + 7×1.05×1.8) × 1.10 = 49.53 × 1.10 |
| 1304 close #1 | 7.25 / **267.344** | 7.25 / **267.344** | cells 3:8, 4:6, 8:(9+6)/2, 12:7, 13:(10+6)/2, 14:7 → 121.52 × 2.20 |
| 1304 close #2 | 7.25 / **281.05** | 7.25 / **281.05** | 127.75 × 2.20 |
| delta 1308 | 6.853 | 6.853 | (13.23 − 7.00) × 1.10 — exactly the new criterion's term |
| delta 1304 | (13.706) | 13.706 | (13.23 − 7.00) × 2.20 — same term at the other grade |

`final_rating` did not move between closes for either subject (6.25 / 7.25) — ratings ignore
coefficients, as claimed. The corrections enter as cell means (8: (9+6)/2, 13: (10+6)/2), which is
formula #1 per D-0820-12, then feed formula #3 — both re-derived, not assumed.

**BUG-046 cell transitions re-derived** from the catalogue alone: active criteria after the stand's
criterion 14 = {1,2,3,4,8,10,12,13,14}; the middle-manager matrix never emits `c_level_only` (1,10)
→ project state **[2,3,4,8,12,13,14]**; general state excludes project criteria (8,13) →
**[2,3,4,12,14]**; switch-back restores the first set. Matches the recorded transitions exactly,
with the two corrections present only while their cells are (values 6/6 on return, recorded), and DB
rows constant through all three states (scores `[3,4,8,12,13,14]`, corrections 2). The recorded
admin-matrix agreement check (modulo cells 1/10) is consistent with the same catalogue arithmetic.

## 2. Deployed SQL — CONFIRMED; ordering assessed, one justification sentence refuted

**Corpus first** (this gate's own comparison, nodes + connections, canonical JSON): 33 generator
outputs; **31 byte-identical to live** — including the frozen `EPE: Auth Guard`, which
`check_live_drift.py` skips — **0 changed**, and exactly the 2 deliberately deleted workflows absent
(`API: Get Admin Data Fixed`, `API: Get Employee Self Review`). The 5 live-only workflows are the
known non-generated set (CORS handler, mail trio, `My workflow 10`). So every statement below about
"the deployed SQL" is simultaneously a statement about the repo generators.

**Applicability predicate in score-correction** (`rSZcm0HDMUHLYk8W`, live): `Validate Input` builds
the subject lookup with `s.is_project_participant AS subject_is_project` and the `project_criteria_ids`
sub-select (`target_audience = 'project_participants'`, no `is_active` filter — **the same shape as
the deployed submit path's list, verified side by side**); `Decide Level` refuses
422 `CRITERIA_NOT_APPLICABLE` when the subject is not currently a participant. The check precedes
the level decision, so **one shared check covers both writer levels** — the stand exercised both
(c_level and mid_level, recorded 422s with counts 0→0) and the refusal path provably reaches no
write: `Upsert Correction` runs `$json.ok ? $json.sql : 'SELECT NULL … WHERE false'`.

**Emission filter in the middle-manager matrix** (`EyvFZJGDxQNL20tC`, live): exactly
`AND (c.target_audience <> 'project_participants' OR u.is_project_participant = true)` in the
row-source `CROSS JOIN` WHERE, next to `c.is_active = true AND c.c_level_only = false` — same clause
text as the admin matrix's row source, same predicate shape as the close dataset's
(`cd.target_audience <> …` inside `criteria_data`). All three read from the live definitions this
gate fetched. The new static tests (`tests/routeGuardDeferred.test.js`) pin both, including the
row-source-not-sub-select regex; suite re-run by this gate: **274 passed / 0 failed**.

**Ordering (check before the period gate).** Deployed order in `Decide Level`: passthrough errors →
subject 404 → **applicability 422** → period 409 → ownership 403. Both properties the brief asks for
hold: (a) **it refuses nothing legitimate** — only writes that are inapplicable by the D-0822-3 rule
reach the 422, and the refusal writes nothing; (b) **applicable writes see no behaviour change** —
they skip the new block, and the relative order of every pre-existing check is unchanged (verified
against the `bfca5e1` diff: the block was inserted between the 404 and the period check; nothing
else moved). **However**, the report's third justification — "the deployed submit path already
answers applicability before its relation checks, so this leaks nothing submit does not" — is
**refuted at source**: deployed `Submit Evaluation` → `Build Insert SQL` answers `SCOPE_MISMATCH`
403 (which bundles the actor–subject relation and period scope in one lookup), `PERIOD_NOT_STARTED`
409 and `CANNOT_EVALUATE` 403 all **before** its applicability 422. Consequence: on paused live, the
corrections route discloses a subject's current classification (422 vs 409) to any role-gated writer
for any subject id — a distinction submit never reveals while paused. The other two reasons for the
ordering stand (non-mutating refusal; live provability), the decision itself was approved, and the
sensitivity is minimal — filed as **BUG-048** (docs accuracy + the marginal disclosure, Low), not as
a refutation of the deployed behaviour, which does exactly what the report says it does.

## 3. New-criterion path claims, source-level — CONFIRMED

All read from the live `API: Manage Criteria Admin V7` / `API: Get Score Coefficients` /
`API: Save Score Coefficients` definitions (= generator output, §2):

- **No weight, no seeding.** The Manage Criteria INSERT names columns `title, description, category,
  target_audience, is_active, selfassesment, for_manager, c_level_only, level_*_desc` — no `weight`
  (schema default `1.0`, `schema.sql:96`); the whole workflow contains **zero** references to
  `weight` or `score_coefficients`. The UI editor (`AdminSettings.jsx` via `useCriteria.saveCriterion`)
  sends `{action:'save', criteria}` — the same shape the stand used — and has no weight field.
- **Unseeded render.** `GET api/score-coefficients` selects `is_active` criteria and
  `Format Response` fills weight `parseFloat(weight) || 1.0` and levels 1..10 with 1.0 where rows are
  missing — the recorded `scoring_get_unseeded` (weight 1, ten 1.0 levels) is exactly this code path.
- **Save = exactly 10 rows.** The save builds one weight UPDATE plus **exactly ten** per-level
  `INSERT … ON CONFLICT (criteria_id, score_level) DO UPDATE`; every level 1..10 is mandatory
  (missing/non-positive → 422), so an unseeded criterion cannot end up with fewer than 10 rows.
  Weight floor 0.1 (D-0822-2) enforced in the same node.
- **Byte-identity of the dead-read removal, verified empirically** — not from the story: in the
  parent commit `MANAGER_MATRIX_SQL` is assigned once and referenced nowhere (`legacy_query` is a
  pure file read); this gate then rebuilt the pre-removal generator (HEAD file + the dead lines
  re-added, against the pre-refresh export from `874a36b`) and diffed outputs — **byte-identical**,
  all ten files. The refresh-refusal mechanism is real: `assert_not_a_generator_input` scans the
  three builders for `legacy_node(`/`legacy_query(` naming the export and raises before writing, and
  it runs *after* the PUT in the deploy loop — consistent with "both PUTs had landed before the
  refusal".
- **Freeze respected.** The stand created the criterion while H1 was draft; the deployed write path
  409s `EVALUATION_STARTED` once `evaluation_started_at` is set (freeze on start, not activation),
  and the freeze check precedes both the save and delete branches. The coefficient save has no
  period gate at all (D-0822-2: editable until close) — the "create before «Запустить оценку», save
  coefficients any time until close" sequence in the report matches the deployed gates.

## 4. Corpus and inertness — CONFIRMED (no residue of any kind found)

Live state read 2026-08-24 ~09:08 UTC, all by SQL:

- **Zero drift**: §2 — 31 identical / 0 changed / 2 deliberately absent, this gate's own comparison.
- **Auth Guard canonical**: `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — exactly the
  frozen value; the deploy script asserts it before, between and after each PUT (source-verified).
- **Only the intended deploy timestamps**: `rSZcm0HDMUHLYk8W` at `2026-08-24T08:33:49.866Z`,
  `EyvFZJGDxQNL20tC` at `08:33:51.330Z` — the exact values in the report; every other workflow's
  `updatedAt` predates the batch.
- **Periods**: 1 closed / 2 (H1-2026) draft / 5 draft; H1 `evaluation_started_at` NULL,
  `is_active=false`. **Data tables**: evaluations, evaluation_scores, score_corrections,
  period_results all **0**.
- **No residue**: 0 users in 1301–1310, 0 fixture jtis (`44444444…`), 0 probe jti
  (`fa9ade00-2026-4824-…`), `epe_2026` the only `epe*` database, no `epe-final-n8n` container, every
  `epe*` file in VPS `/tmp` dated ≤ 2026-08-22. `auth_sessions` = 9 rows, newest 07:19:57Z user 2
  (Alexander live, pre-deploy) — legitimate, per the Build-2 gate's own rule.
- **Fingerprint replay**: this gate re-ran the probe's `FINGERPRINT_SQL` verbatim on live →
  `b0bd0f55ca92c69c65912bd9f151bf89`, equal to the recorded before **and** after values. Money
  inputs untouched, still.
- **Stand fidelity**: the live n8n container runs `n8nio/n8n@sha256:0a65e6e5…` — the same digest
  `setup_finalize_throwaway.sh` pins for the stand.
- **Which backend answered the probe** (the recorded `base_url` is a loopback tunnel
  `127.0.0.1:25678`, not the public origin): the probe minted its JWT with the **live container's**
  `JWT_SIGNING_SECRET` and its jti existed only in **live** `epe_2026`; the stand's n8n had a
  different secret and database, and any non-live listener would have answered 401, not the recorded
  422/409/200. The answering instance was therefore the live n8n. What the tunnel did *not* exercise
  is the public TLS path (Caddy → n8n) — listed under NOT-CHECKED.

## 5. Docs — CONFIRMED (counters counted, not trusted)

- **HANDOVER §10 = bugs.md**: this gate counted the rows — 47 `### BUG-` blocks, **20 OPEN / 27
  CLOSED / 0 in-progress** — matching both the bugs.md statistics table and §10's "20 open / 27
  closed". (This gate's two new rows make bugs.md 22/27; §10 is now two rows stale by the same
  convention as after the previous gate — reconcile at the next handover pass, brief limits this
  push to report + bugs.md.)
- **DECISIONS.md** records the corrections extension: the D-0822-3 write-validation bullet carries
  "**Extended 2026-08-24 (approved)**: `POST api/admin/score-correction` enforces the same shared
  predicate…" and the third bullet now states the `CRITERIA_ALREADY_SCORED` truth (BUG-047's fix) —
  both verified in the `bfca5e1` diff and the file.
- **BUG-045 narrowed to nine — reproduced independently**: this gate compared all 37 top-level
  exports against the live definitions: **exactly 9 stale** (`Admin Get Users Data`,
  `All-evaluation`, `Analytics Dashboard`, `Get Evaluation Details FIXED`, `HR Evaluation Status`,
  `My Profile V5`, `Register`, `Reset Password`, `evaluation-details-by-user`), 26 identical —
  including both exports the deploy refreshed (`API_ Manager Subordinates Matrix.json`,
  `API_ Score Correction.json`, now live-identical) — and the 2 deleted-workflow exports. The
  progress note's "nine stale exports remain" is exact.
- **BUG-046/047 closures evidence-backed**: both rows carry fix + verification blocks whose claims
  this gate re-verified upstream (§1 transitions, §2 clause, DECISIONS wording); the artifact files
  they cite exist and contain the cited values.

## 6. Adversarial pass — two new findings, rest holds

- **Fixture-shaped expectations**: the three subject grades differ (0.60/2.20/1.10 — a 1.0 fallback
  cannot pass silently), and the two money examples use different criteria mixes and correction
  shapes. The level-6 coefficients of criteria 3/4/12 are all 1.10, but their weights differ, so a
  weight/criterion mixup could not cancel. No fixture symmetry that could mask the checked claims
  was found.
- **Subject with no classification row**: impossible as a row — `users.is_project_participant` is
  `NOT NULL DEFAULT false` — and the code fails closed anyway (`=== true || === 't'`), so anything
  unexpected reads as general, which *refuses* project-criterion writes rather than accepting them.
- **`is_active=false` vs deleted criterion**: the applicability list has no `is_active` filter —
  deliberately identical to submit's list. An inactive project criterion therefore still 422s for
  general subjects (fail-closed); for a project subject a correction against an existing-but-inactive
  criterion is accepted and stored invisibly (every reader filters `is_active=true`) — a
  **pre-existing class shared with submit**, unchanged by this batch and out of its declared scope
  ("classification dimension only"). A correction for a **nonexistent** criteria_id dies on the live
  FK `score_corrections_criteria_fkey` (raw 500, nothing stored) — also pre-existing. A hard
  `delete` via Manage Criteria is freeze-gated during a campaign and FK-blocked (`NO ACTION` from
  both `evaluation_scores` and `score_corrections`) once any data references the criterion; a clean
  criterion deletes with its coefficient rows (`ON DELETE CASCADE` — the one intended cascade).
  History cannot be destroyed by the delete path.
- **What the FK check surfaced** (new): migration `006_add_hierarchical_corrections.sql` does not
  reproduce live — it declares the criteria FK **against `users(id)`** (a typo) and `ON DELETE
  CASCADE` on all three FKs, where live has `… REFERENCES criteria(id)` and `NO ACTION`; `schema.sql`
  predates the table entirely. Stands restore from live dumps so nothing is currently wrong, but a
  from-migrations rebuild would get materially different (and data-destroying) constraints —
  **BUG-049** (Low).
- **`managers_only` cells for non-managers** (observation, pre-existing): both matrices emit
  criterion 2 for employee subjects (visible in the recorded `admin_matrix_cells` — every fixture
  subject carries cell 2). Project criteria are the only audience-filtered cells, exactly as the
  report itself states; money-inert while unscored, but an API submit of criterion 2 for a
  non-manager would be accepted and would count. Same class as the inactive-criterion residue:
  today's non-classification audience semantics, explicitly out of D-0822-3's scope. Recorded here
  so the next audience-semantics brief starts from a written observation.
- **The two-close stand sequence**: the reopen between closes was SQL on the throwaway only; the
  deployed close route was used as-is both times, and live close stays irreversible — the recorded
  `stand_reset` string states exactly this. No deployed-behaviour claim rests on the surgery.

## NOT-CHECKED (mandatory)

- **The public TLS path** for the two touched routes: the recorded probe ran through a loopback
  tunnel to the live n8n (§4). The workflows behind the public origin are byte-verified; the
  Caddy → n8n hop itself was not re-exercised by this gate.
- **Live HTTP probes of any kind** — read-only mode; a valid session needs an `auth_sessions`
  INSERT. Runtime behaviour rests on the stand record (90/90), the byte-identity of definitions, and
  the batch's own recorded probe pair.
- **Workflow `settings` blocks**: both `check_live_drift.py` and this gate's comparison cover
  `nodes` + `connections` only. A drift confined to a workflow's settings (timeouts, error workflow)
  would be invisible to both. Low risk, unbounded by this gate.
- **The browser render of `/admin/scoring`** with an unseeded criterion: verified at API + source
  level (`useScoreCoefficients` → `AdminScoring` renders the GET list; the GET fill is proven); no
  browser was driven at the stand and none can be driven read-only now.
- **Role×route regression beyond the two touched workflows** — deliberately scoped by the batch; the
  other 28 workflows are byte-identical to generators already verified by earlier gates.
- **`weight` stripping for non-admin readers of `GET /api/criteria`**: recorded on the stand
  (`criteria_get_manager.weight: null`) and pinned by the existing suite; the stripping code itself
  was not re-read by this gate.
- **The n8n schema dump's restorability** (`n8n_public_prefinalize_20260824.dump`, 537 KB): present
  and sized, headers not test-restored (the previous gate's local `pg_restore -l` technique applies
  if ever needed).
- **BUG-042 and the BUG-029 read-side residue** — open and out of scope, as the batch states.

## New rows filed

- **BUG-048** (Low): the FINALIZE report §1's ordering justification mis-describes the deployed
  submit path (submit answers scope/period/capability before applicability), so the pre-period 422
  on the corrections route is a paused-state classification disclosure submit does not make. The
  deployed ordering itself is as claimed, approved, and its other two justifications stand.
- **BUG-049** (Low): migration 006 declares `score_corrections` constraints that live does not have
  (criteria FK → `users(id)` typo, CASCADE vs live `NO ACTION`); `schema.sql` lacks the table.

## Session facts

- Read-only techniques reused from the Build-2 gate: `workflow_entity` reads by SQL (no API key),
  local `pg_restore` of recorded dumps, fingerprint replay instead of live probes.
- Everything in §1–§5 was verified against **live** or **recorded** state fetched this session;
  nothing was taken from the batch report without an independent read.
- Suite re-run at `bfca5e1`: 274/274. Generators re-run three times (corpus ×2 shapes, dead-read
  reconstruction ×1); no generator touched the network (verified before running).
