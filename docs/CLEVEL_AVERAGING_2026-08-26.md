# C-level direct evaluations are averaged (D-0826-1) — 2026-08-26

**Outcome in one line:** when two C-level people score the same person, the money now reads the
mean of their scores and carries how many there were — screen, payload and frozen `period_results`
alike; with one evaluator every frozen number is byte-identical to before; nothing was ever lost in
the database, and the coefficient tables are photographed as version H1-2026 before anything else.

Live after this session: **H1 active, `evaluation_started_at` NULL on all three periods**, four
data tables **0 / 0 / 0 / 0**, **89** users, **3** terminated, **80** in H1 scope, catalogue,
level coefficients and grades md5-identical to the snapshot taken at the start. Frontend release
**`20260826T051630Z`**. Two live workflows updated, node-for-node, webhook paths unchanged.

---

## 1. Item 1 — is it data loss, or an aggregation rule? Plainly: an aggregation rule.

**Both rows persist. Nothing is overwritten at write time. A reader picked one.**

### 1.1 The constraint

Live `epe_2026.performance_db.evaluations`, read 2026-08-26:

```text
Indexes:
    "evaluations_pkey" PRIMARY KEY, btree (id)
    "idx_evaluations_unique_non_self_period" UNIQUE, btree
        (subject_id, evaluator_id, evaluation_source, period_id) WHERE is_self_evaluation = false
    "idx_evaluations_unique_self_period" UNIQUE, btree
        (subject_id, period_id) WHERE is_self_evaluation = true
```

`evaluator_id` is **in** the non-self key. `(subject X, evaluator 18, c_level_direct, period 2)` and
`(subject X, evaluator 47, c_level_direct, period 2)` are two different keys and two different rows.
`evaluation_scores` is unique on `(evaluation_id, criteria_id)`, so each row carries its own score
per criterion, side by side.

### 1.2 The write path

`API: Submit Evaluation` → `Build Insert SQL`, live definition:

```sql
  ON CONFLICT (subject_id, evaluator_id, evaluation_source, period_id)
  WHERE is_self_evaluation = false
  DO NOTHING
```

and the probe that decides whether this is a first submit or a top-up, in `Validate Evaluation`, is
scoped to the actor:

```sql
        (SELECT dup.id FROM performance_db.evaluations dup
          WHERE dup.subject_id = ${rawSubjectId}
            AND dup.evaluator_id = ${actorId}
            AND dup.evaluation_source = '${safeSource}'
            AND dup.period_id = p.id
            AND dup.is_self_evaluation = false
          LIMIT 1) AS existing_evaluation_id
```

A second C-level person therefore sees no evaluation of their own, takes the insert branch, does not
conflict, and gets a row. The edit route (`API: Update Evaluation WITH PERIOD`) is likewise bound to
`e.evaluator_id = ${actorId}`, so nobody can edit anybody else's row either.

**Measured, not argued.** On the stand, with both evaluations filed:

| evaluator | criterion | score | updated_at |
|---|---|---|---|
| 1606 | 1 | 8 | 2026-08-26 05:02:21.861946 |
| 1606 | 10 | 7 | 2026-08-26 05:02:21.861946 |
| 1616 | 1 | 4 | 2026-08-26 05:07:40.555399 |
| 1616 | 10 | 9 | 2026-08-26 05:07:40.555399 |

Two evaluation rows, four score rows, none overwritten.

### 1.3 The reader that picked one

Both money readers — `API: evaluations-matrix` → `Build Matrix Query` and `API: Manage Periods` →
`Build Close Dataset Query` — carried the same sub-select:

```sql
      'c_level_score', (
        SELECT es.score_value
        FROM performance_db.evaluations e
        JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
        WHERE e.subject_id = u.id
          AND e.evaluation_source = 'c_level_direct'
          AND c.c_level_only = true
          AND es.criteria_id = c.id
          AND e.period_id = ${periodId}
        ORDER BY e.updated_at DESC
        LIMIT 1
      ),
```

`ORDER BY e.updated_at DESC LIMIT 1` — the most recently touched row wins. Not last **writer**
strictly: `updated_at` moves on an *edit* too, so a C-level person who reopens an old evaluation and
changes an unrelated criterion moves their whole row to the front of this queue for every criterion.
And `updated_at` is `timestamp without time zone` with no tiebreaker in the ORDER BY, so two rows
written in the same microsecond resolve arbitrarily.

**So: not data loss. An aggregation rule that had never been chosen** — and the one it defaulted to
was "whoever touched their row last decides", on the two heaviest criteria in the catalogue.

### 1.4 The same question for the other two channels, so the picture is complete

| channel | more than one row possible? | what happens |
|---|---|---|
| **`c_level_direct`** | **yes, by design** — three people hold the right | was latest-by-`updated_at`; **now the mean, with the count** (D-0826-1) |
| **`manager`** | **yes, but only after a reorganisation** | latest-by-`updated_at`, unchanged |
| **`subordinate` (upward)** | yes, by design | already `AVG` + `COUNT` in SQL, and always was |
| **self** | **no** — the database refuses it | one row, enforced |

**Manager.** The relation filter is `AND subj.manager_id = ${actorId}`, so only the person's current
manager can file — one at a time. But the unique key contains `evaluator_id`, so if a person's
`manager_id` is changed mid-period the old manager's row stays and the new manager can file their
own. Two `manager` rows then exist and the same `ORDER BY e.updated_at DESC LIMIT 1` picks the newer
one. That is *probably* the right answer for a manager change and *certainly* the wrong one if the
old row is edited afterwards. **Untouched by this brief and unresolved** — nobody has changed a
`manager_id` mid-period yet, and the owner has not been asked what should happen when they do.

**Self-review.** `API: Submit Self Review`:

```sql
  ON CONFLICT (subject_id, period_id) WHERE is_self_evaluation = true DO NOTHING
```

and `Format Response` turns the zero-row result into **409 `DUPLICATE_SELF_REVIEW`**. There is
exactly one self-review per person per period and the *database* is what guarantees it; the
`ORDER BY … LIMIT 1` in the readers is belt-and-braces over a set that can only hold one row.

---

## 2. Item 2 — the change

### 2.1 One grouped scan, in both workflows, character-for-character

A new CTE, added to `API: evaluations-matrix` beside the upward channel's CTE and to
`API: Manage Periods`' close dataset beside `criteria_data`:

```sql
c_level_direct_scores AS (
  SELECT
    e.subject_id,
    es.criteria_id,
    AVG(es.score_value) as avg_c_level_score,
    COUNT(*) as c_level_count
  FROM performance_db.evaluations e
  JOIN performance_db.evaluation_scores es ON e.id = es.evaluation_id
  JOIN performance_db.criteria c ON es.criteria_id = c.id
  WHERE e.evaluation_source = 'c_level_direct'
    AND c.c_level_only = true
    AND c.is_active = true
    AND e.period_id = ${periodId}
  GROUP BY e.subject_id, es.criteria_id
)
```

and the cell:

```sql
      'c_level_score', (
        SELECT ROUND(cds.avg_c_level_score::numeric, 2)
        FROM c_level_direct_scores cds
        WHERE cds.subject_id = u.id AND cds.criteria_id = c.id
      ),
      'c_level_count', (
        SELECT cds.c_level_count::integer
        FROM c_level_direct_scores cds
        WHERE cds.subject_id = u.id AND cds.criteria_id = c.id
      ),
```

Three deliberate choices:

- **AVG and COUNT come from one grouped scan**, not two correlated sub-selects with duplicated
  WHERE clauses. The mean and the count can never end up describing different sets of rows.
- **Two decimals** — the scale `rating_c_level_direct` already uses for exactly this channel. One
  decimal, which the upward channel's *display* uses, would cost money: 5.33 × coef × weight is not
  5.3 × coef × weight. The level coefficient is chosen by `round()`, which agrees either way.
- **`numeric`, no float cast.** The value sits inside `json_build_object`, so Postgres serialises it
  as a JSON *number* — `6.00` parses to `6`. A single evaluator's integer comes back unchanged.
  `tests/clevelAveraging.test.js` also pins that a string-typed value still computes as a number, so
  a cached payload or a different driver cannot turn a money cell into a string concatenation.

The two CTE bodies are asserted **byte-equal** by a test, because the existing comment in that file
already says what happens when the pair drifts: "the screen and the frozen result stop agreeing
about money".

### 2.2 An unscored cell reads null / null, not zero

Measured on live after the deploy: with no evaluations at all, all **176** `c_level_only` cells
(88 people × 2 criteria) come back `c_level_score: null, c_level_count: null` — the CTE is grouped,
so there is simply no row and the correlated sub-select yields NULL. That is exactly the shape
`subordinate_count` has always had on the upward channel. It is never a score of zero. The client
helper resolves a missing or null count to 1 when there is a score and 0 when there is not, which
is precisely the pre-D-0826-1 behaviour for an old payload.

### 2.3 Every consumer, in lockstep

The server computes the mean, so **every consumer of `c_level_score` receives the mean without a
logic change** — that is the whole reason the aggregation was put in SQL rather than in three copies
of a JavaScript helper. What the client changes are for is making the count visible, so a 6 that is
the mean of 4 and 8 never looks like a plain 6 (the defect D-10 of the previous session, fixed there
for corrections and left open for this channel).

| consumer | what changed |
|---|---|
| `API: evaluations-matrix` (payload) | mean + `c_level_count` |
| `API: Manage Periods` close dataset → `period_results` | the identical CTE; frozen result follows the screen |
| `src/utils/matrixUtils.js` | new `getCLevelChannel` / `formatCLevelChannel` / `formatScoreCompact`; `getCriterionFinalScore` reads the channel through the shared helper and coerces to a number |
| `src/hooks/useFinalScoresMatrix.js` (`/admin/final-scores`) | its private `getCriterionFinalScore` copy now calls the shared helper |
| `src/hooks/useScoreCalculation.js` (`/admin/score-calculator`) | the same |
| `src/components/admin/EvaluationsMatrixTable.jsx` | the cell shows the **channel value**, with a «×N» badge and a tooltip naming the mean, the count and the actor's own score |
| `src/components/admin/EmployeeScoresModal.jsx` | «среднее по N» under each C-level score |
| `src/components/admin/ScoreDetailModal.jsx` | «— среднее по N оценкам» beside the heading |
| `src/components/admin/FinalScoresMatrixTable.jsx` | inherits the extended tooltip |
| `src/utils/excelExport.js` | detail sheet gains a **«C-LEVEL ОЦЕНЩИКОВ»** column |
| `Compute Close Results` (`finalOf`) | comment only — it already read `c_level_score`, which is now the mean |

**One behavioural change worth naming.** The matrix cell used to render
`actor_c_level_score ?? c_level_score` — *your own* score if you had filed one. After averaging that
would have shown an evaluator their own 4 in the cell whose money is 6. It now shows the channel
value, with the actor's own score moved into the tooltip
(«Среднее по 2 оценкам C-level: 6 · ваша оценка: 4 · нажмите, чтобы изменить свою»). Editing still
edits only your own row; `CLevelEvaluationModal` still pre-fills from `actor_c_level_score`.

**Not changed, deliberately:** the tooltip line for a *correction* on a `c_level_only` criterion now
reads «Коррекция C-level: 3 (не входит в расчёт C-level критерия)» instead of the bare
«C-level: 3». Two different things called "C-level" can now appear in one tooltip and the reader has
to be able to tell them apart. The manager-path tooltip is unchanged and pinned by a test:
«Менеджер: 9, Mid-level: 5, C-level: 4, Итого: 6.0».

**No schema change.** `c_level_count` is a payload field. `period_results` stores one row per person
and an evaluator count is a property of a single cell — criterion 1 can have two evaluators while
criterion 10 has one — so a person-level column would misdescribe it. The source rows stay in
`evaluations` forever, so September can reconstruct any count it needs. **Surfaced, not resolved:**
if the owner wants the count frozen too, the honest shape is a per-cell table, not a column.

---

## 3. Item 3 — a correction against an averaged score. Surfaced, not resolved.

### 3.1 What the code does **today** — measured, not read

`API: Score Correction` → `Decide Level` validates the score range and the project-participation
dimension. It contains **no `c_level_only` check at all**. On the stand, 2026-08-26:

```text
POST /webhook/api/admin/score-correction  {subject_id: 1605, criteria_id: 1, correction_score: 3}
  → 200 {"success": true, "data": {"id": 10, "criteria_id": 1,
         "correction_score": 3, "correction_level": "c_level"}}
```

The row is stored. It reaches the matrix payload: that cell came back
`c_level_score: 6, c_level_count: 2, c_level_correction: 3`. And then the close, run through the
real route with that correction in place, froze `bonus_index` **132.8520** — **byte-identical** to
the same close without it. Because the final-cell rule, in the client and in the close alike, is:

```js
const finalOf = (crit) => {
  if (crit.c_level_only) {
    return crit.c_level_score != null ? Number(crit.c_level_score) : null;
  }
  if (crit.manager_score == null) return null;
  const scores = [Number(crit.manager_score)];
  if (crit.mid_level_correction != null) scores.push(Number(crit.mid_level_correction));
  if (crit.c_level_correction != null) scores.push(Number(crit.c_level_correction));
  return scores.reduce((acc, s) => acc + s, 0) / scores.length;
};
```

The `c_level_only` branch returns before corrections are ever consulted. **A correction on criterion
1 or 10 is accepted with a 200, stored, transported to the screen, and discarded.** Filed as
**BUG-073**. Nothing is wrong on live today: `score_corrections` is empty.

There is a second fact in the same area. `score_corrections` is unique on
`(subject_id, criteria_id, correction_level, period_id)` — **no evaluator in the key**. So
corrections are last-writer-wins across C-level people even on the criteria where they *do* count,
and the route's `ON CONFLICT … DO UPDATE` overwrites the previous one and rewrites `evaluator_id`.
That is the same collision D-0826-1 has just removed from the evaluation channel, still present one
table over. It is not in this brief's scope and is recorded in BUG-073.

### 3.2 What it **would** do after this change, under each of the two rules

Neither is implemented. Both are costed so the choice is one sentence, not a study. Take criterion 1
(weight 5.00), two C-level evaluators at 8 and 4, mean 6, and a `c_level` correction of 3:

| rule | final cell | index contribution | what it says |
|---|---|---|---|
| **today (nothing)** | 6.00 | 6 × 1.20 × 5.00 = **36.00** | the correction is ignored |
| **(a) the correction replaces the mean** | 3.00 | 3 × 0.60 × 5.00 = **9.00** | calibration overrules the evaluators |
| **(b) the correction joins the mean as one more opinion** | (8+4+3)/3 = 5.00 | 5 × 1.00 × 5.00 = **25.00** | calibration is a third voice |

Rule (a) matches how a correction behaves on the manager channel *in spirit* — but not in fact: on
the manager path a correction is already **averaged in**, not substituted (`mean(manager, mid?,
c_level?)`, D-0820-12). Rule (b) is the one that is consistent with what corrections already do
everywhere else in the system.

The cost of each, in engineering terms, is the same one-line change to `finalOf` in four places
(`matrixUtils`, two hooks, `Compute Close Results`) plus its test. The cost of **deciding wrongly**
is not symmetric: rule (a) lets one admin override two C-level opinions with no record on screen
that they did; rule (b) dilutes a calibration decision by however many people happened to file.

**A third option exists and is worth naming:** refuse the correction. `API: Score Correction`
returns 422 `CRITERIA_NOT_APPLICABLE` for a project criterion on a non-project person; the same
refusal for a `c_level_only` criterion would make the API honest today with no money rule at all,
and could be shipped before the decision is taken. This is the recommendation if the owner wants
one thing done now.

**This brief does not pick.** The answer is the owner's.

---

## 4. Item 4 — the coefficient snapshot

`docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`, produced by
`scripts/snapshot_coefficients.py --label H1-2026`. **A read.** Three SELECTs, no transaction that
writes, no extension, nothing touched.

| | |
|---|---|
| **Read at** | **`2026-08-26T04:48:44.986621Z` UTC** — `now() AT TIME ZONE 'UTC'` on the live server's own clock, taken in the same statement as the hashes |
| Period state at that moment | `1:Annual 2025:closed`, `2:H1-2026:active:not_started`, `5:Annual 2026:draft` |
| `evaluations` at that moment | 0 |
| md5 of the artefact file | **`916921399c8d4653dfc5b7b9a0ea17db`** |
| md5 `criteria` (9 rows, the weights) | **`fc618757f6aa2c27db5bce7613fc28c7`** |
| md5 `score_coefficients` (90 rows) | **`317e09e8326edde500bfcde2bad81e78`** |
| md5 `grades` (11 rows) | **`946b30a5ea8b8594321ebb5fc645bd32`** |
| md5 combined | **`079177fbb9d52ea4c5b942fcecaed1c2`** |

The three table hashes are computed **by Postgres** over a canonical projection, and the exact SQL
is printed inside the artefact, so September can recompute them against whatever live holds then and
see in one line whether a value moved. All three were **re-read at 05:19:53Z, after the deploy, and
are identical** — this session moved no money input.

This is a photograph, not an approval. The owner sets these values and may change any of them before
the gate; if he does, the file is not edited — the snapshot is retaken and a new dated file is
written beside it. Its purpose is that the September calculation can be reconstructed from the
numbers it was actually computed from. The December 2025 index cannot be, because its inputs were
edited afterwards and the index itself was never stored (HANDOVER §4 item 2). That is what this
prevents.

Criterion 14's live curve `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00` is in the snapshot as
the approved H1-2026 curve, per D-0826-2.

---

## 5. The money proof — two copies of one dump, closed through the real route, twice

`scripts/setup_clevel_throwaway.sh` → `scripts/prove_clevel_close.py` →
`backups/2026-08-26-clevel-averaging/clevel_close_proof.json`, **29 / 29 checks**.

Two databases restored from **one** dump of live (`epe_2026_clevel_20260826_0502.dump`, 95 180
bytes), seeded identically, and two isolated n8n containers on the VPS loopback — one carrying the
workflow surface **as committed at HEAD**, one the **working tree**. Both closed through their own
real `POST /api/periods/close`. The script refused to start unless live read `89/0/notstarted`, and
refused to compare unless the two databases' evaluation fingerprints matched.

Two rounds were needed, because the claim has two halves a single comparison cannot separate.

### 5.1 Round 1 — one C-level evaluator: nothing may move

Both stands: fingerprint `db71b35d55581831e544e8218d87b19e`. One `c_level_direct` evaluation on the
subject (criterion 1 = 8, criterion 10 = 7).

| | |
|---|---|
| Frozen rows | **104** on each side; neither produced a row the other did not |
| Money cells compared | **832** (104 × 8) |
| **Cells that moved** | **0** |
| Pool | **548.494** on both, to the last digit |
| Subject's index | **174.7080** on both — the hand figure `291.18 × 0.60` |
| The new payload | `c_level_count: 1` on both C-level cells; the old payload has no such field |

548.494 is also the pool the *previous* session's close produced on its own stand from its own
fixtures — independent corroboration across two sessions.

### 5.2 Round 2 — a second C-level evaluator: exactly one row must move

Both stands reset identically (results deleted, period 2 back to `active`) and given the **same one
extra evaluation** — 1616 → the subject, criterion 1 = 4, criterion 10 = 9, with a strictly later
`updated_at` so the old reader's choice is deterministic. Both stands: fingerprint
`a41578665acee231e40ae12cc42f97a3`.

**The payload:**

| | criterion 1 | criterion 10 |
|---|---|---|
| scores filed | 8 and 4 | 7 and 9 |
| **OLD code** (last touched wins) | **4** | **9** |
| **NEW code** (mean) | **6** | **8** |
| **`c_level_count`** | **2** | **2** |

The brief's case exactly: 8 and 4 → **6**, count **2**, and **both source rows are in the database**
(§1.2). Under the old code the same fixture yields **4** — the later row's score, named rather than
left as "4 or 8".

**The frozen result:**

| | control (HEAD) | treatment (working tree) |
|---|---|---|
| Frozen rows | 104 | 104 |
| Money cells compared | 832 | |
| **Rows that differ** | **exactly one — the subject** | |
| Columns that differ | `final_rating`, `bonus_index` — **and nothing else** | |
| `final_rating` | 7.3750 | **7.5000** |
| `bonus_index` | **124.8360** | **132.8520** |
| `rating_c_level_direct` | 7.00 | 7.00 — **identical** |
| Every other person | **byte-identical, all 103** | |
| Pool | 498.622 | 506.638 — the difference is exactly 8.016 = 132.852 − 124.836 |

`rating_c_level_direct` agreeing on both sides is the corroboration that matters: that archival
column has always been `AVG(e.calculated_score)` over the source rows. The database has averaged
this channel in one place since it was written; the money path did not. Now they agree.

### 5.3 The hand arithmetic

The subject is grade S1 (**0.60**), a project participant with no direct reports, so eight criteria
apply: 1, 3, 4, 8, 10, 12, 13, 14. Six of them are the manager path and do not move:

| crit | weight | final cell | level coef | contribution |
|---|---|---|---|---|
| 3 | 3.00 | (9+5+4)/3 = 6.0 | 1.10 | 19.80 |
| 4 | 1.50 | 8 | 1.50 | 18.00 |
| 8 | 1.40 | 8 | 1.60 | 17.92 |
| 12 | 1.00 | 7 | 1.30 | 9.10 |
| 13 | 1.80 | 9 | 3.80 | 61.56 |
| 14 | 1.50 | 8 | 3.00 | 36.00 |
| | | | **fixed** | **162.38** |

The two C-level criteria are the whole of the difference:

| | crit 1 (w 5.00) | crit 10 (w 1.60) | Σ | × 0.60 = index |
|---|---|---|---|---|
| round 1, both sides | 8 × 2.80 × 5.00 = 112.00 | 7 × 1.50 × 1.60 = 16.80 | **291.18** | **174.708** |
| round 2, OLD code | 4 × 0.70 × 5.00 = 14.00 | 9 × 2.20 × 1.60 = 31.68 | **208.06** | **124.836** |
| round 2, NEW code | 6 × 1.20 × 5.00 = 36.00 | 8 × 1.80 × 1.60 = 23.04 | **221.42** | **132.852** |

Every figure was written into the proof script as a constant **with its working** before the stand
existed, and matched the frozen numbers to four decimals.

Note what the middle row means: submission order alone moved this person's share by **6.4 %**, and
on a different pair of scores it would move it much further — the level curve of criterion 1 runs
0.30 to 6.00, so the same two evaluators disagreeing 3 against 9 would have produced 4.50 against
270.00 on that cell depending on who saved last.

### 5.4 The screen, in a real browser

Vite against the treatment stand, logged in as the fixture admin. `/admin/evaluations-matrix`:

- C-level cells render **6** and **8** with a **×2** badge;
- tooltips «Среднее по 2 оценкам C-level: 6 · нажмите, чтобы оценить» and «… 8 · …»;
- the employee modal shows both scores with «среднее по 2» under each;
- the manager-path tooltip is unchanged: «Менеджер: 9, Mid-level: 5, C-level: 4, Итого: 6.0».

`/admin/final-scores`, the money screen, same person:

```text
19.80* | 18.00 | 9.10 | 36.00 | 17.92 | 61.56 | н/п | 36.00 | 23.04 || Σ 221.42 | Итог 132.85
```

with «C-level: 6 (среднее по 2 оценкам) · 6.00 × коэф. × вес 5.00 = 36.00» on the criterion-1 cell
and «… 8.00 × коэф. × вес 1.60 = 23.04» on criterion 10. **Σ 221.42 and Итог 132.85 are the frozen
`period_results` figures.** The screen, the payload and the frozen result are the same numbers.

The other seeded people read 170.83 / 108.32 / 80.89 / 13.74 — the previous session's hand figures,
unmoved.

---

## 6. What changed, file by file

**Backend — two live workflows, PUT at 05:16:11Z and 05:16:13Z, both active before and after,
webhook paths identical, no node added or removed:**

| workflow | id | nodes changed |
|---|---|---|
| `API: Manage Periods` | `M9ljMDdO1mIl8m1h` | `Build Close Dataset Query` (the CTE + the two cell sub-selects), `Compute Close Results` (comment only) |
| `API: evaluations-matrix` | `yQNNr0i4UBFNVgMv` | `Build Matrix Query` |

70 and 9 nodes before and after. Every other generator output was byte-identical to live before the
deploy (`check_live_drift.py`: 32 identical, 0 changed) and is again after.

**Frontend:** `src/utils/matrixUtils.js`, `src/utils/excelExport.js`,
`src/hooks/useFinalScoresMatrix.js`, `src/hooks/useScoreCalculation.js`,
`src/components/admin/EvaluationsMatrixTable.jsx`,
`src/components/admin/EmployeeScoresModal.jsx`, `src/components/admin/ScoreDetailModal.jsx`.
Release **`20260826T051630Z`**; the previous release `20260825T194735Z` is the rollback target; 36
releases on disk. The deployed `xlsx.min-DacWxMfi.js` chunk — which is where Rollup put
`EvaluationsMatrixTable` — is md5-identical to the local build
(`8ad9e816e79e51714433455308f339b9`).

**Tests:** `tests/clevelAveraging.test.js`, **21 assertions**, including the byte-equality of the two
CTEs and the "one evaluator is a no-op" pin. `npm test` **401 / 401**. `npx eslint src tests` is at
**16 errors / 14 warnings** — the repository baseline, unchanged by this session (verified by
running the same command against a stashed tree).

**Executors:** `snapshot_coefficients.py`, `setup_clevel_throwaway.sh`, `seed_clevel_second.sql`,
`prove_clevel_close.py`, `teardown_clevel_throwaway.sh`, `deploy_clevel_averaging.py`,
`verify_clevel_live.py`.

The deploy script **refuses** unless: the Auth Guard still carries its frozen `updatedAt`; no period
is started; and `evaluations / evaluation_scores / period_results` read `0/0/0` — the last one
because this change was proven money-neutral on an empty database, and against existing rows it must
be re-proven before it is deployed.

---

## 7. Live, after

### 7.1 The anchor

| | |
|---|---|
| File | `epe_2026_preclevel_20260826T051507Z.dump` |
| Taken | 2026-08-26 **05:15:07Z**, `pg_dump -Fc --no-owner --no-acl`, **before the first live write** |
| Size | **95 180 bytes** |
| md5 | **`d4afe8b446161e884b2c0d83adb4df09`** — equal on both copies |
| On the Mac | `~/EPE_ROLLBACK/2026-08-26-clevel-averaging/`, mode 600, **outside the repository** |

**It supersedes `epe_2026_prenight_20260825T184211Z.dump` (2026-08-25 18:42:11Z, md5
`3ecd8fa9cb8f1b6d8f956aded1c13882`)** and every earlier anchor.

Restoring it would undo **nothing this session did**: no `epe_2026` row was written at any point.
The only live writes were the two workflow definitions, which live in the n8n `postgres` schema, and
that schema was dumped too — `n8n_app_preclevel_20260826T051507Z.dump`, 586 375 bytes, md5
`bd915c4eee14f2eae6f5bcbb520f5fa2`, beside the other. Rolling the two workflows back is simpler than
a restore: regenerate from commit `57b78e1` and PUT.

### 7.2 Invariants — `clevel_live_verify.json`, 22 / 22, read 2026-08-26 05:19:53Z

| check | value |
|---|---|
| Users | **89** |
| Terminated | **3** |
| In scope of H1 | **80** |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| `evaluation_started_at` | **NULL on all three periods** — the gate is unpressed |
| H1-2026 | `status=active`, `is_active=true` |
| Extensions | `plpgsql` only |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — before and after every PUT |
| Workflows | **60 total · 35 active · 22 archived · 48 webhooks** |
| `criteria` / `score_coefficients` / `grades` md5 | **identical to the 04:48:44Z snapshot** |
| Frontend release | **`20260826T051630Z`** |
| Probe session | minted, deleted in a `finally`, count back to 0 |

Read through Caddy with a real admin token: `GET /api/admin/evaluations-matrix` → 200, 88 people,
period `H1-2026`, all **176** `c_level_only` cells carrying `c_level_count`, every one null with no
evaluations. `GET /api/periods` → 200, three rows, `evaluation_started=false` on all three.
Unauthenticated matrix read → **401**.

---

## 8. Surfaced, not resolved

- **BUG-073 — a C-level correction on a C-level criterion is accepted, stored and ignored** (§3).
  The owner's decision: replace the mean, join the mean, or refuse the correction. The third can
  ship before the other two are decided.
- **`score_corrections` has no evaluator in its unique key**, so corrections are last-writer-wins
  across C-level people on the criteria where they *do* count — the same collision this brief just
  removed from the evaluation channel, one table over. Recorded in BUG-073.
- **The manager channel can hold two rows after a reorganisation**, and reads the latest by
  `updated_at` (§1.4). Nobody has changed a `manager_id` mid-period; the rule has never been chosen.
- **`updated_at` has no tiebreaker** in the manager and self readers' `ORDER BY`. Harmless for self
  (one row is enforced); latent for manager.
- **The count is not frozen.** `period_results` is per person and a count is per cell; freezing it
  honestly needs a per-cell table. The source rows persist, so it is reconstructable.
- **Per-evaluator C-level scores are not in the matrix payload** — only the mean and the count. The
  individual rows are visible on `/admin/all-evaluations` and через `evaluation-details-by-user`,
  which lists `c_level_evaluations` as an array and always has. Adding min/max to the cell would
  make disagreement visible on the money screen for the cost of two more aggregates in the same
  scan; not done, because the brief asked for the count.
- **BUG-071** (`c_level_only` cells emitted to people who cannot receive them) is untouched and
  still the owner's call.
- **Eight dumps of live `epe_2026` from previous briefs remain in VPS `/root/epe_stand_tmp`**, root-
  only and mode 600, so not BUG-053's world-readable problem — but `PROJECT_RULES.md` says a brief's
  teardown empties that directory, and three teardowns did not. This session removed only its own.
  Not deleted for them: they are other sessions' artefacts and deleting them is not this session's
  call.
- **No catalogue, coefficient, criteria, grade, department, period, scope or user write of any kind
  was made. The second gate was not pressed and no route that could press it was called.**

---

## 9. Session hygiene

- One dated dump of `epe_2026` and one of the n8n schema before the first live write, copied to the
  Mac outside the repository, md5-verified on both sides; the anchor superseded is named in §7.1.
- Two throwaway databases and two throwaway n8n containers, all removed. The drop loop refuses any
  name without the `epe_mid_night_clv_` prefix, so `epe_2026` can never be a candidate. Afterwards
  `SELECT datname` reads `epe_2026, postgres` and `docker ps` shows the same six containers as
  before. **No container this project does not own was touched, and nothing outside the stand was
  restarted.**
- The stand's own VPS-side dump was deleted at teardown; stand artefacts lived in
  `/root/epe_stand_tmp`, mode 600, never `/tmp`.
- No extension created on live: `pg_extension` reads `plpgsql`.
- One probe session on live, minted and deleted in a `finally`.
- **No mail of any kind was sent.** The browser walkthrough used a password set on the STAND
  database only, and no address was contacted.
- The working tree carried **no other session's edits** at any point; `git status` at the start was
  clean and every modified file is this session's.
- `backups/` is gitignored — the proof artefacts and the dumps under
  `backups/2026-08-26-clevel-averaging/` are deliberately not tracked.

---

**This report, the two D-0826 rows, the two bug rows, the coefficient snapshot, the executor scripts, the refreshed workflow exports and every frontend change landed on `main` as commit `cddccb8`.** The proof artefacts under `backups/2026-08-26-clevel-averaging/` — `clevel_close_proof.json` (29/29), `clevel_correction_probe.json`, `clevel_live_verify.json` (22/22), `throwaway_env.json` and the stand dump — are deliberately **not** tracked: `backups/` is gitignored because those files carry personal data. The rollback anchors live in `~/EPE_ROLLBACK/2026-08-26-clevel-averaging/`, outside the repository.
