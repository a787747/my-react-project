# Criterion 9 «Ответственность сверх роли» — created and proven on live (id 14); riders shipped (2026-08-24)

Brief: create the ninth criterion on live through Alexander's own path (manage-criteria save →
score-coefficients save), audience all / self off / manager on / c_level off, weight 1.50, level
coefficients 0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00, texts VERBATIM from the attached
document; plus riders (BUG-048, BUG-049, HANDOVER reconcile).

**Outcome in one line: criterion id 14 is live with the approved texts (char-for-char), weight
1.50 and all ten coefficients to the digit, created through the same two admin routes the UI
calls, launch still paused; the other 8 criteria / 80 coefficient rows / grades are byte-identical
before and after; the riders (BUG-048 closed by D-0824-1, BUG-049 closed, BUG-050 filed, HANDOVER
reconciled) shipped in the same batch. Execution record: §6.**

The batch ran in two pushes: the riders first, while the texts document was missing (§1 records
that blocker and the search — it was real for half the session); then the document's texts arrived
verbatim in chat, were saved as `docs/briefs/criterion9_texts.json`, and the staged executor ran
green on live.

---

## 1. The blocker (resolved the same day): the attached document was not on this machine

The brief says title, description and the ten level texts come from the attached document,
VERBATIM. That document is nowhere the executor can reach:

- **Repo**: no tracked or untracked file contains «Ответственность сверх роли» (case-insensitive
  sweep; the only «сверх роли» hit is inside existing criterion 8's level-10 text in
  `docs/USER_FACING_COPY_2026-08-2x.md`, which catalogues the live 8 criteria from a DB read).
- **`~/Downloads`** (where every previous brief's files landed — `BRIEF_CALCULATION_MAP.md`,
  `BRIEF_ROUTE_GUARD_H1.md` are still there): no matching file; nothing criterion-shaped among
  the recent files.
- **`~/Desktop`, `~/Documents`**, the session scratchpad: nothing.
- The stand proof (`docs/FINALIZE_PRELAUNCH_2026-08-2x.md` §3, `scripts/prove_finalize.py`) used
  **placeholder** texts by design (`Уровень {i}: описание критерия 9 ({i}/10)`), so it holds no
  approved wording either.

Inventing or paraphrasing user-facing evaluation copy for live was not an option, so the creation
did not run. **No live write of any kind happened this session** — live was touched only by two
read-only catalog reads (`pg_constraint` / `pg_indexes` on `score_corrections`, for BUG-049's
evidence). Because nothing was written, no pre-change dump was taken; the dump is the executor
script's first gate and will be taken by the run that actually creates the criterion.

### What is staged, so the creation is mechanical when the document arrives

`scripts/create_criterion9_live.py` — written this batch, compiled, refusal path tested. It:

- **refuses to run** without `--texts <file>.json` holding exactly
  `{"title", "description", "level_1_desc" … "level_10_desc"}`, all non-empty; the strings go into
  the API body **as-is** and are re-read from the DB afterwards and compared char-for-char;
- carries the approved constants: flags all/self-off/manager-on/c_level-off, weight **1.50**,
  levels **0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00**;
- executes exactly the stand-proven sequence: dump `epe_2026` first → `POST manage-criteria
  {action:'save'}` (the UI's own call; catalogue is writable while the launch is paused, freezes
  only at «Запустить оценку») → verify weight lands at the 1.00 default with **zero** seeded
  coefficient rows → `GET api/score-coefficients` renders the unseeded criterion (all-1.0 fill) →
  `POST api/score-coefficients` with the approved weight + ten values — **the mandatory second
  step**, because until it happens every money surface silently values the criterion at
  1.0 × 1.0 (FINALIZE §3);
- proves brief items 2–4 with compared values: exactly 10 rows / weight 1.50 / GET returns the
  approved values / catalogue flags with weight admin-only (a second marked **read-only** manager
  session checks the stripping) / the level-5 editability round-trip 0.50 → 0.55 → 0.50 with all
  four reads recorded / the other 8 criteria's weights, their 80 coefficient rows and all grades
  **byte-identical** before/after (raw aggregates, not just md5) / totals 9 active criteria and
  90 coefficient rows / periods state byte-identical (launch stays paused);
- rerun guard: refuses if the title already exists (`--resume` continues only from an unseeded
  default-weight leftover); probe sessions are marked jtis deleted in `finally`;
- writes `backups/2026-08-24-criterion9/criterion9_live_proof.json`.

Resolution: Alexander re-sent the texts verbatim in chat; they were saved untouched as
`docs/briefs/criterion9_texts.json` (12 keys, validated) and the executor ran green — see §6.
Two pre-run fixes on the way, neither touching the sequence: the dump plausibility floor was
lowered from 100 KB to 50 KB (this DB legitimately dumps at ~79 KB in `-Fc` with 0 evaluations —
verified against the reclass/finalize batches' known-good dumps and a local `pg_restore --list`:
161 TOC entries, 17 table-data sections), and the repo's standard `_tls_context()` helper (certifi
→ `/etc/ssl/cert.pem`, from `probe_live_reclass.py`) was adopted because this machine's Python
does not see the system CA store. The first two attempts stopped **before any live write** (dump
gate; TLS handshake) and left no residue — probe-session count and criteria count re-verified
clean between attempts.

---

## 2. Rider: BUG-049 closed — migration 006 brought to the live FK set

Live evidence (read-only, `epe_2026`, 2026-08-24):

    pg_constraint on performance_db.score_corrections:
      score_corrections_criteria_fkey  | FOREIGN KEY (criteria_id)  REFERENCES performance_db.criteria(id)
      score_corrections_evaluator_fkey | FOREIGN KEY (evaluator_id) REFERENCES performance_db.users(id)
      score_corrections_period_id_fkey | FOREIGN KEY (period_id)    REFERENCES performance_db.evaluation_periods(id)
      score_corrections_pkey           | PRIMARY KEY (id)
      score_corrections_subject_fkey   | FOREIGN KEY (subject_id)   REFERENCES performance_db.users(id)
    (all FKs plain NO ACTION; no CHECK constraint)

`migrations/006_add_hierarchical_corrections.sql` now declares: criteria FK →
`performance_db.criteria(id)` (was the `users(id)` typo), all three FKs plain `NO ACTION` (were
`ON DELETE CASCADE` — the data-destroying part), names aligned to live
(`_subject_fkey` / `_criteria_fkey` / `_evaluator_fkey`), with a dated corrective comment.
**Migration file only; live was already correct and was not touched** — exactly the brief's scope.

**BUG-050 filed** for what the same read surfaced beyond the FK scope: `period_id` (column, FK,
and live's 4-column unique index `idx_score_corrections_unique_period`) appears in **no** migration
at all; 006's CHECK constraint does not exist on live; `schema.sql` still predates the table. A
from-migrations rebuild would get a table `API: Score Correction` cannot write to. Closing BUG-049
without re-filing that remainder would have hidden it.

## 3. Rider: BUG-048 closed as accepted behavior — D-0824-1

- `DECISIONS.md` **D-0824-1** (one line, as briefed): the pre-period applicability answer is
  intentional — non-mutating, keeps the deployed rule provable on paused live; the marginal
  pre-period classification probe (which submit does not offer) is an accepted, recorded cost.
- The wrong justification sentence in `docs/FINALIZE_PRELAUNCH_2026-08-2x.md` §1 ("this leaks
  nothing submit does not") is corrected **in place as a marked correction** — the report now
  states the two standing reasons and the accepted cost, so the §6.11 wrong-premise class is
  extinguished rather than merely outvoted by bugs.md.
- No code change; the deployed ordering stays as approved.

## 4. Rider: HANDOVER reconciled — and the two updates that must wait

- §10 counters: **21 open / 29 closed** (was 20/27, stale since the finalize gate filed
  BUG-048/049; this batch closed both and filed BUG-050). Matches `bugs.md` statistics and a
  status-marker recount.
- §10 report list completed: `GATE_FINALIZE_2026-08-2x.md` was missing entirely; it and this
  report are appended.
- ~~Deferred until the criterion actually exists~~ — **done after the green run (§6)**:
  - HANDOVER §5 "Criteria catalogue" → **9 active rows / 90 `score_coefficients` rows**, and the
    catalogue table gained `| 14 | Ответственность сверх роли | all | 1.50 | for_manager |`;
  - both per-person criteria-count distributions **recomputed from live** (not hand-shifted):
    classification unchanged at 48 general / 41 project, counts now
    **37 people × 4, 11 × 5, 36 × 6, 5 × 7** — exactly the +1-for-everyone an 'all'-audience
    `for_manager` criterion predicts over the previous 37×3 / 11×4 / 36×5 / 5×6.

## 5. Suite

`npm test` **274/274** (target 272+), unchanged before and after the batch — no code paths under
test were touched (a migration file, docs, one standalone script, one texts JSON).

---

## 6. Execution record — criterion 14 on live (2026-08-24, proof `backups/2026-08-24-criterion9/criterion9_live_proof.json`)

Run: `python3 scripts/create_criterion9_live.py --texts docs/briefs/criterion9_texts.json` —
**all checks passed, `failures: []`**. Compared values, per the brief's items:

- **Dump first**: `epe_2026_20260824_164442.dump` taken before any write (79,427 bytes,
  the known-good size for this DB; local `pg_restore --list` validated the format on the
  identical previous attempt's dump).
- **Creation (brief item 1)**: `POST manage-criteria {action:'save'}` → **id 14** (same id the
  stand got). Every stored text — title, description, all ten level texts — **char-for-char equal
  to `criterion9_texts.json`**; flags exactly all / self off / manager on / c_level off / active;
  weight landed at the **1.00 DB default** with **0** seeded coefficient rows (the editor cannot
  set a weight — FINALIZE §3 confirmed on live). `GET api/score-coefficients` rendered the
  unseeded criterion with the all-1.0 server-side fill. Then `POST api/score-coefficients` with
  weight 1.50 + the ten approved values.
- **Stored values (brief item 2)**: exactly **10** coefficient rows for id 14; stored weight
  **1.50** (not the default); levels 1..10 = **0.20 / 0.25 / 0.30 / 0.35 / 0.50 / 0.70 / 1.00 /
  2.00 / 3.60 / 6.00** to the digit, both in SQL and in the admin GET. `GET api/criteria` as
  admin: criterion present with weight 1.50; as a live manager (marked read-only session,
  user id 1): criterion visible with the correct flags and audience, **`weight` absent** —
  admin-only stripping confirmed on live.
- **Front-editability round-trip (brief item 3)**, level 5 via the same save route, four recorded
  values: approved **0.50** → saved **0.55** → re-read **0.55** → restored → re-read **0.50**.
- **Everything else unchanged (brief item 4)**: the raw aggregates over the other 8 criteria's
  weights, their 80 coefficient rows and all grades are **byte-identical** before/after (compared
  raw, not only hashed); md5 `b0bd0f55ca92c69c65912bd9f151bf89` — the same fingerprint the
  finalize batch recorded, unchanged through this batch. Totals after: **9 active criteria /
  90 coefficient rows**. Periods state byte-identical (closed/draft/draft — launch stays paused,
  no activation, no start, no mail, no workflow PUT, Auth Guard untouched). Both marked probe
  sessions deleted in `finally` (`DELETE 2`), session count back to its pre-run value.

---

## Surfaced for decision

*(empty — the one blocker this report originally surfaced, the missing texts document, was
resolved by Alexander re-sending the texts in chat; nothing else requires a decision)*
