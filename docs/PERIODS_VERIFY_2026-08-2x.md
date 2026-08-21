# Periods hierarchy — acceptance verification (read-only gate)

**Date:** 2026-08-21
**Subject:** the 2026-08-21 periods-hierarchy build (`docs/PERIODS_HIERARCHY_2026-08-2x.md`, commits `88ff91d`, `e5e313e`)
**Mode:** read-only. No PUT, no deploy, no DB write, no mail. Every write-capable path was avoided; the only
remote operations were `SELECT` over `ssh root@92.51.45.147 → docker exec postgres_n8n psql` and `ls`/`readlink`
on the host.
**Truth source:** LIVE n8n workflow definitions, read out of `postgres.workflow_entity` rather than from repo
exports (BUG-028). Repo exports were used only as a comparison target and are labelled as such throughout.

---

## Verdict

**Accept, with seven named microfixes.** No blocker.

The two persisted quantities that carry money — the final cell and the bonus index — are formula-identical
to the live matrix and the client pipeline, verified fragment-for-fragment and independently re-derived by
hand to the exact cent (`36.30`, `68.40`, `104.70`). The four per-source ratings have no matrix counterpart
to be identical to; they are new archival columns, built consistently with the write path and feeding
nothing. Authorization on all four new routes is `admin`-only except the read-only
roll-up (`admin` + `c_level`), matching the pre-existing pattern and the client guard. Close is genuinely
atomic, genuinely idempotent, and genuinely irreversible; today it cannot be invoked at all, because H1 is
`draft` and close rejects anything that is not `active`.

Most of the microfixes are not defects in what shipped — they are things the build correctly did **not**
promise, plus stale documentation. They matter because they all land inside the September window. One
(**M6**) is a pre-existing frontend defect on the bonus screen that this audit turned up along the way; it
does not touch the close path, but it does touch the money, so it is named here rather than filed quietly.

**Note on live state:** while this verification was running, the designated UX acceptance was performed on
live — period id 5 «Annual 2026» was created and H1 was attached to it. The baseline in §5 is measured as
of the end of this audit and supersedes the build report's figures. Nothing was activated or closed;
`evaluations`, `evaluation_scores`, `score_corrections` and `period_results` are all still 0.

---

## 1. Formula fidelity

Every fragment below is quoted from the LIVE definition (`API: Manage Periods`, id `M9ljMDdO1mIl8m1h`,
61 nodes, `updatedAt = 2026-08-21T06:00:08.687Z`) or from the repo frontend, which was confirmed to be the
build source of the deployed release `20260821T060049Z`.

### (a) Per-source rating — **no counterpart to be identical to** (new quantities, faithfully built)

Server, `Build Close Dataset Query` (node 48):

```sql
(SELECT ROUND(AVG(e.calculated_score)::numeric, 2)
   FROM performance_db.evaluations e
   WHERE e.subject_id = epp.user_id AND e.period_id = <id>
     AND e.is_self_evaluation = false AND e.evaluation_source = 'manager') AS rating_manager,
...  'subordinate' ... AS rating_upward,
...  'c_level_direct' ... AS rating_c_level_direct,
(SELECT e.calculated_score
   FROM performance_db.evaluations e
   WHERE e.subject_id = epp.user_id AND e.period_id = <id>
     AND e.is_self_evaluation = true
   ORDER BY e.updated_at DESC LIMIT 1) AS rating_self,
```

`rating_self` is literally the self-review's plain `calculated_score`, latest-by-`updated_at` — **not** the
weighted value, and not an average. This matches HANDOVER §4: the self value never feeds bonuses.
The three multi-evaluator sources are `AVG(calculated_score)`, i.e. the 1–10 rating, formula #1.

**There is nothing in the matrix to compare these against.** The live matrix has no per-source aggregate
anywhere — its only aggregate is `subordinate_avg_score`, an average across evaluators *within one
criterion*. The four `rating_*` columns aggregate `evaluations.calculated_score`, a column the matrix never
reads. So the verdict for (a) is not "identical" or "divergent" but *no counterpart*: these are new archival
quantities. They are built correctly and consistently with the write path (`API: Submit Self Review` stores
the 1–10 value in `calculated_score` and the weighted value in a separate `weighted_score` column that close
never touches), and they feed nothing — `final_rating` and `bonus_index` are computed from the criterion
cells, not from these. The practical consequence is only that no existing screen can be used to eyeball-check
them after close; see the reconciliation note in the observations.

Where the close dataset *does* mirror the matrix is the per-criterion cell resolution, and there it does so
subquery-for-subquery: same `ORDER BY e.updated_at DESC LIMIT 1` tie-break, same `is_self_evaluation` /
`evaluation_source` / `c_level_only` predicates, same `score_corrections` lookups. The differences are
cosmetic (`epp.user_id` vs `u.id`, `cd.` vs `c.`). That is the part that determines money, and it is exact.

### (b) Final cell — **IDENTICAL**

Server, `Compute Close Results` (node 50, lines 12–22):

```js
// matrixUtils.getCriterionFinalScore — the matrix final cell (D-0820-12)
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

Client, `src/utils/matrixUtils.js:68-94`:

```js
export const getCriterionFinalScore = (criterion) => {
  const { manager_score, mid_level_correction, c_level_correction, c_level_score, c_level_only } = criterion;
  if (c_level_only) { return c_level_score ?? null; }
  if (manager_score === null || manager_score === undefined) { return null; }
  const scores = [manager_score];
  if (mid_level_correction !== null && mid_level_correction !== undefined) { scores.push(mid_level_correction); }
  if (c_level_correction !== null && c_level_correction !== undefined) { scores.push(c_level_correction); }
  const sum = scores.reduce((acc, s) => acc + s, 0);
  return sum / scores.length;
};
```

Semantically identical, including the null handling: the server's `== null` and the client's
`=== null || === undefined` / `??` cover exactly the same two values.

**Per-person `final_rating` — the build report is wrong here, in the build's favour.**
`docs/PERIODS_HIERARCHY_2026-08-2x.md` states the aggregate is *«this brief's call — the matrix has no
per-person total to copy»*. It does have one. `src/utils/excelExport.js:228-229,248` — the Excel export of
the evaluations matrix, column «ИТОГОВЫЙ БАЛЛ» — already ships exactly this aggregate:

```js
const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
const finalScores = criteria.map(c => getCriterionFinalScore(c)).filter(s => s !== null);
...
styledCell(formatScoreForExcel(avg(finalScores)), highlightStyle),
```

against the server's

```js
if (finals.length > 0) {
  finalRating = finals.reduce((acc, s) => acc + s, 0) / finals.length;
```

Same function per cell, same non-null filter, same population (`emp.criteria`, i.e. every active criterion).
So `final_rating` is **not** a novel definition — it reproduces a surface Alexander has already been
exporting. That is a stronger position than the build report claimed for itself; the provenance sentence in
that document should be corrected (microfix **M5**).

### (c) Bonus index — **IDENTICAL**, and confirmed to have no denominator

Server, node 50, lines 24–33 and 62–66:

```js
// useFinalScoresMatrix.calculateCriterionScore — score × coef(round(clamp)) × weight.
// `|| 1.0` mirrors the client exactly (parseFloat(weight) || 1.0 in the
// score-coefficients API): a zero/absent weight or grade behaves as 1.0.
const weightedOf = (raw, crit) => {
  const weight = Number(crit.weight) || 1.0;
  const coefficients = crit.score_coefficients || {};
  const level = Math.max(0, Math.min(10, Math.round(raw)));
  const coefficient = coefficients[level] != null ? Number(coefficients[level]) : 1.0;
  return raw * coefficient * weight;
};
...
  const gradeCoefficient = Number(row.grade_coefficient) || 1.0;
  bonusIndex = weightedSum * gradeCoefficient;
```

Client, `src/hooks/useFinalScoresMatrix.js:74-89` and `:206-208`:

```js
const calculateCriterionScore = (score, criteriaId, coefficientsMap) => {
  if (score === null || score === undefined) return null;
  const criteriaCoefs = coefficientsMap[criteriaId];
  if (!criteriaCoefs) { return score; }
  const weight = criteriaCoefs.weight || 1.0;
  const scoreLevel = Math.round(score);
  const clampedLevel = Math.max(0, Math.min(10, scoreLevel));
  const scoreCoef = criteriaCoefs.score_coefficients?.[clampedLevel] ?? 1.0;
  return score * scoreCoef * weight;
};
...
const gradeCoefficient = gradesMap[gradeCode] || 1.0;
const finalWeightedScore = weightedSum * gradeCoefficient;
```

**No division by the sum of weights on either side.** Formula #3 as HANDOVER §4 specifies it, deliberately.

`src/pages/BonusCalculation.jsx` — the Калькуляция бонусов screen — does **not** re-implement anything: it
imports `useFinalScoresMatrix` (line 23) and consumes `emp.final_weighted_score` directly (line 101, 136).
So the index has exactly one client implementation, and the server mirrors that one. There is no third
formula to drift.

### Mirrored quirks — the full catalogue

| # | Quirk | Server | Client | Mirrored? |
|---|---|---|---|---|
| 1 | **Zero weight → 1.0** | `Number(crit.weight) \|\| 1.0` (node 50 L28) | `parseFloat(row.weight) \|\| 1.0` (LIVE `API: Get Score Coefficients`, `Format Response` L24) | Yes — faithfully |
| 2 | **Zero grade coefficient → 1.0** | `Number(row.grade_coefficient) \|\| 1.0` (L64) | `parseFloat(g.coefficient) \|\| 1.0` (L169) | Yes |
| 3 | **NULL grade → 1.0** | same expression; `LEFT JOIN grades` yields NULL | `gradesMap[gradeCode] \|\| 1.0` | Yes — see finding **M2** |
| 4 | **Zero score-coefficient stays 0** | `coefficients[level] != null ? Number(...) : 1.0` | `found ? parseFloat(found.coefficient) : 1.0` | Yes — a `0.00` coefficient correctly zeroes the term. Only *weight* is trapped |
| 5 | **Rounding order** | `Math.max(0, Math.min(10, Math.round(raw)))` | `Math.round` then `Math.max(0, Math.min(10, …))` | Yes — round-then-clamp on both |
| 6 | **Level 0** | DB `score_coefficients` starts at level 1 → lookup misses → `1.0` | `coeffMap` built `for (let i = 1; i <= 10; i++)` → key `0` absent → `?? 1.0` | Yes — both yield 1.0 |
| 7 | **Missing level row** | `!= null` check → 1.0 | `found ? … : 1.0` | Yes |
| 8 | **Rounding is lookup-only** | the raw cell (`6`, or `6.5` after corrections) multiplies un-rounded; only the *coefficient lookup level* is rounded | identical | Yes |
| 9 | **Persistence precision** | `numeric(10,4)` for `final_rating`, `numeric(14,4)` for `bonus_index`, `numeric(10,2)` for the four ratings | screen renders `toFixed(2)` | Storage is strictly finer than display — no disagreement is reachable |
| 10 | **Client-only early return** | none | `if (!criteriaCoefs) { return score; }` (L77-81) — returns the *unweighted* score | **Not mirrored.** Unreachable in practice: both sides enumerate `criteria WHERE is_active = true`, so the map is always complete. Latent divergence only if the coefficients API and the matrix ever disagree on the criteria set |

Live hygiene check (`epe_2026`, today): **zero** criteria with `weight IS NULL OR weight <= 0`, **zero**
`score_coefficients` rows with `coefficient IS NULL OR coefficient <= 0`, and all 8 active criteria carry a
complete 1–10 coefficient set. Quirks 1, 2 and 4 are therefore **latent, not active**.

### bugs.md-ready entry — the zero-weight trap

```
### BUG-029: Criterion weight of 0 silently behaves as 1.0 in the bonus index
- Status: 🔴 OPEN
- Severity: 🟢 Low–Medium (latent hardening gap — no currently-wrong number; no zero weight or
  zero grade coefficient exists on live today)
- Location: LIVE `API: Manage Periods` → `Compute Close Results` L28
            (`const weight = Number(crit.weight) || 1.0;`);
            LIVE `API: Get Score Coefficients` → `Format Response` L24
            (`weight: parseFloat(row.weight) || 1.0`);
            `src/hooks/useFinalScoresMatrix.js:84`.
- Description: `|| 1.0` treats 0 as absent. Setting a criterion's weight to 0 — the natural way an admin
  would express "this criterion should not count toward the bonus" — makes it count with weight 1.0
  instead. The same applies to a grade coefficient of 0. A score *coefficient* of 0 is handled correctly
  (it zeroes the term); only weight and grade coefficient are trapped.
- Why it matters: the bonus index is the money-allocation number. An admin who zeroes a weight to remove a
  criterion from the pool gets the opposite of what they asked for, silently, with no validation error.
  Because the index has no denominator (HANDOVER §4), the mistake inflates that person's share of the pool
  rather than merely mis-scaling it. Since 2026-08-21 the wrong number is also *frozen* into
  `period_results` at close and cannot be recomputed.
- Repro: set `criteria.weight = 0` for any active criterion, open Итоговые баллы / Калькуляция бонусов —
  the criterion contributes `score × coefficient × 1.0`. Close the period — the same value is persisted.
- How to fix: use `Number.isFinite(w) && w >= 0 ? w : 1.0` on both sides (server node 50 and the
  coefficients API), so an explicit 0 means 0 and only NULL/garbage defaults to 1.0. Add a
  `CHECK (weight > 0)` or an explicit UI affordance for "exclude this criterion" if 0 must stay illegal.
  The two sides must change together or the server/client parity breaks.
- H1 impact: none today (no zero weights on live). Fix before anyone edits the criteria catalogue.
```

---

## 2. Independent recomputation, and the cross-check provenance

### Recomputation — confirmed exactly, by hand

Inputs read directly from the surviving throwaway DB `epe_hier_20260821_0549` (SELECT only), not from the
build report:

- Employee A = user **1103**, `grade_id = 1` → grade **C3**, coefficient **1.00**.
- Criteria and weights: `3 → 3.00`, `4 → 1.50`, `12 → 1.00` (all `target_audience='all'`, not `c_level_only`).
- `score_coefficients`: criterion 3 → `6:1.10, 8:1.60`; criterion 4 → `6:1.10, 8:1.50`; criterion 12 → `6:1.10, 8:1.50`.
- P1 (period 12): manager evaluation `2101` scored **6** on criteria 3, 4, 12. Self evaluation `2102` scored 5.
- P2 (period 13): manager evaluation `2111` scored **8** on criteria 3, 4, 12.
- `score_corrections` is **empty** — no mid-level or c-level correction anywhere on the stand.

Criteria 1 and 10 are `c_level_only` with no `c_level_direct` evaluation → `finalOf` returns `null` → excluded.
Criteria 8 and 13 are `project_participants` and A is not one → never scored → `null` → excluded. Criterion 2
is `managers_only` → never scored for A → `null` → excluded. Five empty cells, three scored cells.

**P1**

```
final  = mean(6, 6, 6)                                            = 6.0000   ✓ stored 6.0000
index  = 6 × 1.10 × 3.00  +  6 × 1.10 × 1.50  +  6 × 1.10 × 1.00
       = 19.80            +  9.90             +  6.60             = 36.30
       × grade coefficient 1.00                                   = 36.3000  ✓ stored 36.3000
```

**P2**

```
final  = mean(8, 8, 8)                                            = 8.0000   ✓ stored 8.0000
index  = 8 × 1.60 × 3.00  +  8 × 1.50 × 1.50  +  8 × 1.50 × 1.00
       = 38.40            +  18.00            +  12.00            = 68.40
       × grade coefficient 1.00                                   = 68.4000  ✓ stored 68.4000
```

**Annual**

```
rating = AVG(6.0000, 8.0000)     = 7.0000    ✓
index  = SUM(36.3000, 68.4000)   = 104.7000  ✓
```

Every figure reproduces to the last digit from criterion rows, weights and coefficients alone. The
persisted numbers are correct.

**Anti-zero-fill.** Employee B (1104) is `is_in_scope = false` in P1 and in scope with final 8.0 in P2.
The exclusion is in the LIVE roll-up SQL (`Build Rollup Query`, node 57):

```sql
'annual_rating', (
  SELECT ROUND(AVG(pr.final_rating)::numeric, 4)
  FROM performance_db.period_results pr
  WHERE pr.user_id = u.id
    AND pr.period_id IN (SELECT id FROM performance_db.evaluation_periods WHERE parent_period_id = <id>)
    AND pr.is_in_scope = true
    AND pr.final_rating IS NOT NULL
),
'annual_index', (
  SELECT ROUND(SUM(pr.bonus_index)::numeric, 4)
  ... AND pr.is_in_scope = true AND pr.bonus_index IS NOT NULL
),
```

`AVG` over `is_in_scope = true AND final_rating IS NOT NULL` — SQL `AVG` ignores excluded rows rather than
counting them as zero. B's annual is 8.0, not 4.0, and C (1105, in scope, never evaluated, `has_data=false`,
all numbers NULL) is excluded from the mean while remaining a visible row. Confirmed against the stored
rows, which I read directly.

**The roll-up reads nothing live.** Node 57's SQL touches only `period_results`, `evaluation_periods`,
`users`, `departments`, `grades`. No `evaluations`, `evaluation_scores`, `score_corrections`, `criteria`, or
`score_coefficients`. The immutability invariant is real, not merely tested.

### Cross-check provenance — settled

`api_proof.json`'s `cross_check` key is a bare string:

```
"stored final/index match client matrix+money pipeline (<0.005)"
```

That is a label, not evidence. It is settled by diffing the definitions directly:

| Definition | Nodes | Identical to LIVE, node-for-node? |
|---|---|---|
| `n8n_workflows/API_ Manage Periods.json` (tracked top-level export) | 61 | **Yes** — refreshed from live by `deploy_periods_hierarchy.py` |
| `n8n_workflows/route_guard_h1/manage-periods.json` (generator output) | 61 | **Yes** |
| `n8n_workflows/API_ evaluations-matrix.json` (tracked top-level export) | **4** | **No** — this is BUG-028, the pre-guard, pre-period-binding version. LIVE has 9 |
| `build_route_guard_deferred.py` output, regenerated today | 9 | **Yes** |

`scripts/setup_hierarchy_throwaway.sh` step 4 generates the matrix rather than copying the tracked export,
with the stale export called out in a comment. Since the regenerated definition is byte-identical to live,
**the stand's server/client cross-check ran against a live-equivalent matrix.** The BUG-028 export did not
contaminate the proof; per the build report it cost one debug cycle before the generator was wired in.

### What the proof does *not* establish

Two gaps, both honest consequences of the fixture rather than defects:

1. **The grade coefficient is never exercised.** All seven fixture users have `grade_id = 1` → C3 →
   coefficient `1.00`. Every `× gradeCoefficient` in the proof multiplied by one. The stored index is
   consistent with the formula but does not *prove* the multiply happens. (Circumstantially it does:
   the post-close grade edit test changed the coefficient and the stored rows stayed identical, which
   proves immutability, not application.)
2. **Corrections are never exercised on the live close path.** `score_corrections` is empty in the
   throwaway, so `mid_level_correction` / `c_level_correction` were `null` for every cell in every recorded
   close. The averaging branch of `finalOf` is covered by the static fixtures only.

Neither blocks acceptance — the code paths are visibly identical to the client's, which *is* exercised in
production. They are named so the next proof stand seeds a non-1.0 grade and at least one correction.

---

## 3. Authorization of the four new routes

From the LIVE definitions (`Prepare Guard Input *` nodes and the webhook nodes), not from the repo:

| Route | Method | Path | `required_roles` | `required_capability` | Passes |
|---|---|---|---|---|---|
| GET | GET | `api/periods` | `admin`, `hr`, `c_level` | `""` | admin, HR, c_level |
| CREATE | POST | `api/periods/create` | `admin` | `""` | admin |
| ACTIVATE | POST | `api/periods/activate` | `admin` | `""` | admin |
| **RENAME** | POST | `api/periods/rename` | `admin` | `""` | admin |
| **REPARENT** | POST | `api/periods/reparent` | `admin` | `""` | admin |
| **CLOSE** | POST | `api/periods/close` | `admin` | `""` | admin |
| **ROLLUP** | GET | `api/periods/annual-rollup` | `admin`, `c_level` | `""` | admin, c_level |

The four new routes follow the established pattern exactly. The three mutating ones inherit CREATE/ACTIVATE's
`admin`-only guard; the read-only roll-up gets `admin` + `c_level`, matching `ReportingRoute`. **No new route
received a weaker guard than its peers.**

Enforcement, LIVE `EPE: Auth Guard` → `Authorize` (node 03):

```js
if (!identity.id) { … 401 SESSION_INVALID … }
if (parsed.required_roles.length && !parsed.required_roles.includes(String(identity.role))) {
  return { json: { ok: false, status: 403, code: 'ROLE_FORBIDDEN', … } };
}
```

The role is read from the **live DB identity** (`Load Live Identity`, joined on the session `jti` and
`token_version`), not from a JWT claim, so a forged or stale role claim cannot pass. `required_capability` is
`""` on all seven routes, so the capability branch is inert here by design — period management is a role
decision, not a capability one. No route is reachable without a valid, unexpired, unrevoked session.

### What `/admin/periods` renders for c_level and HR

`src/App.jsx:238-245` wraps `/admin/periods` in `AdminRoute`, which admits **admin, c_level, hr**. The page
renders its action controls with **no role branch at all**:

- rename (pencil) — every row, unconditionally (`AdminPeriods.jsx:520-527`)
- reparent (folder-tree) — every non-container row (`:529-543`)
- «Активировать» — non-active, non-closed, non-container rows (`:545-561`)
- «Закрыть период» — the active, non-container row (`:563-580`)

So a c_level or HR viewer sees all four buttons and gets a 403 alert on click. This is documented, not
accidental — the file header says so: *«Доступ: admin, c_level, hr (просмотр); действия — только admin (API
403)»*. It matches the pre-existing Activate button and BUG-013's pattern. Cosmetic, but it now includes an
irreversible action, which changes the calculus — see microfix **M4**.

**The "read-only 21/40/61" in the brief are user IDs, not counts on the screen.** The label comes from
`docs/DOCS_HYGIENE_2026-08-2x.md:65`, whose «C-level writers» table separates the c_level accounts by
`can_evaluate`. Re-measured on live today:

| id | name | role | `can_evaluate` | grade | manager | in scope H1 |
|---|---|---|---|---|---|---|
| 18 | Bayram Urayev | c_level | **true** | C1 | 21 | yes |
| 47 | Jemal Gulberdiyeva | c_level | **true** | C2 | 21 | yes |
| **21** | Cem Durukan (General Manager) | c_level | **false** | **NULL** | **NULL** | yes |
| **40** | Hemra Ashyrov (Managing Partner) | c_level | **false** | **NULL** | **NULL** | yes |
| **61** | Mekan Yusupov (Managing Partner) | c_level | **false** | **NULL** | **NULL** | yes |

So "read-only 21/40/61" = the three c_level accounts that cannot evaluate. On `/admin/periods` they see the
page (via `AdminRoute`) and all four action buttons, and every mutating click returns 403; on
`/admin/annual-rollup` they get full read access, same as 18 and 47. **This build gave them nothing they
could not already reach** — the new fields on `GET api/periods` are `parent_period_id`, `child_count` and
`has_results`, all aggregates.

Note separately that all three also have `grade_id IS NULL` and `manager_id IS NULL` while being in H1
scope. That is a money-relevant data gap, not an authorization one — finding **M2**.

### `/admin/annual-rollup`

Client: `src/App.jsx:294-301` → `ReportingRoute` → admin + c_level.
Server: `required_roles: ["admin", "c_level"]`.
**The two agree.** HR and employees get 403 from the API and are bounced by the client guard.

### Subject-side sealing gained nothing

`GET api/periods` (the only new-data surface a non-admin can reach) returns aggregates only:

```sql
SELECT id, name, start_date, end_date, is_active, status, period_type, parent_period_id,
  (SELECT COUNT(*)…) AS participant_count,
  (SELECT COUNT(*)… AND epp.is_in_scope = true) AS in_scope_count,
  (SELECT COUNT(*) FROM performance_db.evaluation_periods child
    WHERE child.parent_period_id = evaluation_periods.id) AS child_count,
  EXISTS(SELECT 1 FROM performance_db.evaluations e …) AS has_evaluations,
  EXISTS(SELECT 1 FROM performance_db.period_results pr …) AS has_results
```

The three fields this build added — `parent_period_id`, `child_count`, `has_results` — are a foreign key and
two aggregates. No per-person data, no score, no money. `period_results` is referenced by exactly one live
workflow (`API: Manage Periods`), and no employee-facing route joins it. This week's subject-side sealing is
untouched: no subject-facing workflow was modified by this build.

---

## 4. Close semantics

### (a) What close does, and what it refuses

Transition, from the SQL built in `Compute Close Results` (node 50):

```sql
closed AS (
  UPDATE performance_db.evaluation_periods
  SET status = 'closed', is_active = false
  WHERE id = <id> AND EXISTS (SELECT 1 FROM target) AND (SELECT count(*) FROM ins) >= 0
  RETURNING id
)
```

`ACTIVE → status='closed', is_active=false`, in the same statement that inserts the results. The live
CHECK `chk_evaluation_periods_active_status_consistent` — `(is_active = true) = (status = 'active')` —
makes the pair inseparable at the DB level too.

Refusals, `Build Close Dataset Query` (node 48), in order:

| Condition | Response |
|---|---|
| period not found | 404 `PERIOD_NOT_FOUND` |
| `child_count > 0` (container) | 422 `CONTAINER_NOT_CLOSABLE` |
| already `closed` **with** results | **200 `already_closed`, `results_stored: 0`** |
| already `closed` **without** results | 409 `PERIOD_ALREADY_CLOSED` |
| `status !== 'active'` | 422 `PERIOD_NOT_ACTIVE` |
| zero participants | 422 `NO_PARTICIPANTS` |

**A draft period cannot be closed.** `if (check.target_status !== 'active')` → 422. This is the single most
important fact about today's risk posture.

### (b) Idempotence and the race

Both are enforced inside one SQL statement, in the `target` CTE:

```sql
WITH target AS (
  SELECT id FROM performance_db.evaluation_periods
  WHERE id = <id>
    AND status = 'active' AND is_active = true
    AND NOT EXISTS (SELECT 1 FROM performance_db.evaluation_periods c WHERE c.parent_period_id = <id>)
    AND NOT EXISTS (SELECT 1 FROM performance_db.period_results pr WHERE pr.period_id = <id>)
    AND (SELECT COUNT(*) FROM performance_db.evaluations e WHERE e.period_id = <id>) = <evaluation_count>
  FOR UPDATE
),
ins AS ( INSERT … WHERE EXISTS (SELECT 1 FROM target) RETURNING user_id ),
closed AS ( UPDATE … WHERE id = <id> AND EXISTS (SELECT 1 FROM target) … RETURNING id )
```

Four preconditions — still active, still a leaf, no results yet, evaluation count unchanged since the
compute step — re-asserted at execution time under `FOR UPDATE`. Both the INSERT and the status UPDATE are
gated on `EXISTS (SELECT 1 FROM target)`, so a lost race selects zero target rows and changes **zero rows**
in both. It is a single statement, therefore a single implicit transaction: a partial insert is not
reachable. A second close never gets that far — node 48 short-circuits it to `200 already_closed` before any
SQL runs, and even if it did, `NOT EXISTS (… period_results …)` would empty the target.

The `evaluation_count` predicate is the interesting one: if anyone submits an evaluation between the dataset
read and the write, the target is empty, nothing changes, and the caller gets a zero-row result rather than
a snapshot that silently omits the late evaluation. That is the right trade.

### (c) Between a misclick and a frozen H1

One `window.confirm`. `src/pages/AdminPeriods.jsx:143-155`:

```js
const handleClose = async (periodId) => {
  const period = periods.find((item) => item.id === periodId);
  if (!period || !period.is_active || isContainer(period)) { return; }
  if (!window.confirm(
    `Закрыть период «${period.name}»?\n\n` +
    'Результаты всех участников (рейтинги по источникам, итоговая оценка и бонусный индекс) ' +
    'будут рассчитаны и сохранены без возможности изменения. Период станет закрытым. ' +
    'Действие необратимо.'
  )) { return; }
```

The period name is interpolated and the text says «Действие необратимо» plainly. It is not a typed
confirmation, and the button (`bg-gray-800`) is not styled as destructive.

**The irreversibility is real.** I checked all seven live webhooks: there is no reopen route, no route that
writes or deletes `period_results`, and ACTIVATE explicitly refuses a closed period —
`Build Activation SQL` (node 21):

```js
if (check.target_status === 'closed') {
  return { json: { http_status: 422, body: { success: false, error: 'PERIOD_CLOSED',
    message: 'Закрытый период нельзя активировать' } } };
}
```

…re-asserted inside the UPDATE via `AND status != 'closed'` in the `activatable` CTE. Recovery from a
mistaken close is a database restore, nothing less.

Blast radius if H1 were closed mid-campaign: `status='closed', is_active=false` → the campaign period stops
being the active one → `API: evaluations-matrix` with no `period_id` falls back to
`WHERE is_active = true AND status = 'active'`, finds nothing, and returns `no_period` → every evaluation
surface loses its period binding, and `period_results` is frozen from a partial dataset that can never be
recomputed. In-flight evaluations are not deleted; they simply stop counting toward anything.

One thing does work in the build's favour: the `activatable` CTE also re-asserts leaf-ness and
non-closed-ness before the `deactivated` UPDATE runs, gated on `EXISTS (SELECT 1 FROM activatable)`. The
build report's claim that a failed activation can no longer deactivate the current period is correct.

### (d) Who could close H1 today — concretely

**Nobody.** H1 is `status='draft'`, and close returns 422 `PERIOD_NOT_ACTIVE` for anything that is not
`active`.

From 2026-08-31, once H1 is activated, the set is exactly the holders of an `admin` role with a live
session. On live today:

- `role='admin'`: **one row** — id 2, Alexander Petrosov, `alexander@sedamedical.com`.
- Unexpired `auth_sessions`: **one** — user 2.
- The five c_level accounts (18, 21, 40, 47, 61) and both HR accounts (52, 80) see the button and get 403.

So the answer is: **from 31 August, Alexander alone, in two clicks, with no undo.** That is a defensible
posture for a one-admin system, but it deserves the guardrail in microfix **M1**.

---

## 5. Updated baseline for future pre-flights

Every line re-measured against live today, independently of the build report.

> **This table is the new baseline and supersedes the build report's.** One line genuinely drifted during
> the audit — see the periods row.

| Item | Expected | Measured | |
|---|---|---|---|
| Workflows total | 58 | 58 | ✅ |
| — active | 33 | 33 | ✅ |
| — inactive, unarchived | 3 | 3 | ✅ |
| — archived | 22 | 22 | ✅ |
| Registered webhooks | 41 | **41** | ✅ |
| Frontend release | `20260821T060049Z` | `/var/www/epe/current → releases/20260821T060049Z`, carrying `AdminAnnualRollup-EgeMZ3Oo.js` | ✅ |
| H1 (id 2) | `draft` / `is_active=false` | `draft` / `f` | ✅ |
| H1 scope | 87 / 89 | 87 in scope, 89 participants | ✅ |
| Periods on live | 2 rows (`Annual 2025`, `H1-2026`) | **3 rows** — `1 Annual 2025 closed`, `2 H1-2026 draft parent=5`, **`5 Annual 2026 draft annual`** | ⚠️ **drifted** |
| `evaluations` | 0 | 0 | ✅ |
| `evaluation_scores` | 0 | 0 | ✅ |
| `score_corrections` | 0 | 0 | ✅ |
| `period_results` | 0 | 0 | ✅ |
| `EPE: Auth Guard` `updatedAt` | `2026-08-18T16:34:30.674Z` | `2026-08-18 16:34:30.674+00`, `active=false` | ✅ |
| `API: Manage Periods` | 61 nodes, 7 webhooks | 61 nodes, 7 webhooks, `updatedAt=2026-08-21T06:00:08.687Z` | ✅ |
| 2025 archive (`postgres.performance_db`) | 73 / 234 / 644 / 3 | 73 users / 234 evaluations / 644 scores / 3 corrections | ✅ |
| `npm test` | 213 / 213 | **213 pass, 0 fail** | ✅ |
| Working tree | clean | clean at `e5e313e`, but **`main` is 9 commits ahead of `origin/main`** | ⚠️ |

**One line drifted, and it is good news:** Alexander performed the designated UX acceptance while this audit
ran. He created period **id 5 «Annual 2026»** (`draft`, `annual`, 2026-01-01 → 2026-12-31, top-level) and
re-parented **H1-2026 to it** — exactly the walk-through the build report nominated. `Annual 2026` therefore
has `child_count = 1` and is now a container: non-activatable, non-closable. H1 remains a leaf and remains
activatable for 31 August. Nothing was activated or closed; all four data tables are still 0.

Two side-effects of that walk-through, both benign but worth recording:

- **The container carries 89 participant rows, all in scope.** `Build Create SQL` (node 12) seeds
  `evaluation_period_participants` for every new period unconditionally — it has no way to know the period
  will become a container. The rows are inert while `Annual 2026` has a child. See the container-state
  observation below for when they stop being inert.
- **`evaluation_periods_id_seq` is at 5 while ids 3 and 4 do not exist.** A sequence gap is *not* proof that
  two periods were created and deleted: `nextval` fires before the `UNIQUE (name)` and FK checks, so a
  rejected `INSERT` consumes an id. There is no delete route among the seven webhooks, and `Annual 2026`
  landing on id 5 after two failed attempts is the parsimonious reading. **Unverified either way** — the
  artifacts cannot distinguish a failed insert from an insert plus a raw-SQL delete.

### Migration 013 on live

`performance_db.period_results` exists on live with the exact shape the migration declares:

```
period_id             integer    NOT NULL
user_id               integer    NOT NULL
is_in_scope           boolean    NOT NULL
has_data              boolean    NOT NULL  DEFAULT false
rating_manager        numeric    NULL
rating_upward         numeric    NULL
rating_c_level_direct numeric    NULL
rating_self           numeric    NULL
final_rating          numeric    NULL
bonus_index           numeric    NULL
closed_at             timestamptz NOT NULL DEFAULT now()
closed_by             integer    NULL
```

Both anti-zero CHECKs are present **on live**, not merely on the throwaway:

```
period_results_no_data_is_empty     CHECK (has_data OR (rating_manager IS NULL AND rating_upward IS NULL
                                          AND rating_c_level_direct IS NULL AND rating_self IS NULL
                                          AND final_rating IS NULL AND bonus_index IS NULL))
period_results_out_of_scope_no_data CHECK (is_in_scope OR NOT has_data)
```

plus `PRIMARY KEY (period_id, user_id)`, three foreign keys, and `idx_period_results_user (user_id, period_id)`.
A no-data or out-of-scope row cannot carry a number, so a missing rating can never be read back as a zero —
enforced by the database, not only by the code.

`evaluation_periods` carries `parent_period_id` (self-referential FK), `period_type`, and
`chk_evaluation_periods_active_status_consistent`.

---

## Findings

Every finding below survived an adversarial pass whose default was to refute. Four claims were knocked down
or downgraded in that pass and are reported at their corrected severity, not their original one.

### Blockers

**None.** Nothing found requires a change before this build is accepted.

### Microfixes

**M1 — Harden the action surface on `/admin/periods`: role-gate it, and make close a typed confirmation.**
Two things, one screen. First, the page has **no client-side role gating at all** —
`grep -n "role\|isAdmin\|canAccess\|permissions" src/pages/AdminPeriods.jsx` returns nothing; the `user` prop
is used only for `user?.id` when generating an invite link. So a c_level or HR viewer renders the entire
write toolbar, and that now includes the irreversible «Закрыть период». The build report logs this as
rename/reparent only and calls it cosmetic; it is broader than that. The server is correct (403 on all
three), so this is presentation, not access — but showing an irreversible control to someone who must not
use it is a different proposition from showing them a rename pencil.
Second, close itself: the confirmation is real — `window.confirm` naming the period and stating «Действие
необратимо» — and an adversarial reading correctly points out that this is already a two-step action. I am
still recommending a typed confirmation, and the reason is the asymmetry rather than a defect: the guard is
conventional, the consequence is not. There is no reopen route, no `period_results` mutation route, and
ACTIVATE hard-rejects a closed period, so the only recovery is a database restore. The rename and reparent
modals on this same page already provide the pattern.

**M2 — Three in-scope c_level accounts have no grade and no manager. Fix the data before 31 August.**
Ids **21** (Cem Durukan), **40** (Hemra Ashyrov), **61** (Mekan Yusupov) are all `is_in_scope = true` for H1
with `grade_id IS NULL` **and** `manager_id IS NULL`. Two consequences at close:
`Number(row.grade_coefficient) || 1.0` applies coefficient **1.00** instead of a real grade — a money number
produced by a data gap, not a decision; and with no manager there is no `manager_score`, so `finalOf`
returns `null` for every non-`c_level_only` cell and both `final_rating` and `bonus_index` persist as NULL.
They would show «нет данных» in Годовые итоги unless a c_level colleague scores them on criteria 1 and 10.
*Fix:* set the grades, and decide explicitly whether the two Managing Partners and the General Manager are
in H1 scope at all. A data decision, not a code change — and scope is frozen at close, so it must land
before the campaign starts.

**M3 — After H1 closes, no screen can spend the frozen index.**
`useFinalScoresMatrix` requests the matrix with **no `period_id`** (`src/hooks/useFinalScoresMatrix.js:149`),
so the server falls back to `WHERE is_active = true AND status = 'active'`. The moment H1 closes there is no
active period, the API returns `no_period → data: []`, and Итоговые баллы, Калькуляция бонусов **and** the
evaluations matrix all render empty. The frozen `bonus_index` is then visible only on Годовые итоги, which
has no budget field, no point-value field, no payout column, and no grade-A exclusion filter — all of which
live on `BonusCalculation.jsx`. The server already accepts `?period_id=` and `useEvaluationsMatrix(periodId)`
already takes the argument; nobody passes it and there is no period selector in the UI.
*Fix:* add a period selector, or read `period_results` on the money screens. Not needed in August. Needed in
September, which is when the bonus is actually paid.

**M4 — Make the annual roll-up tell the truth about what it summed.** Three related gaps on one money screen:
- **No partial-year marker.** The columns are labelled «Годовой рейтинг / среднее по охвату» and «Годовой
  индекс / сумма индексов» with nothing indicating how much of the container's declared span contributed.
  Live is *already* in the vulnerable shape: «Annual 2026» spans a full year and has exactly one child. When
  H1 closes in September, a half-year figure will sit under an annual heading. (When H2 exists as an
  attached child the state is legible — it gets its own column with a «черновик» badge and «период не
  закрыт» cells. The problem is the one-child case.)
- **Siblings may overlap.** The only date validation on the hierarchy paths is child-inside-parent
  (inclusive on both ends). Two children of one container may overlap in time, and since the annual index is
  a `SUM`, an overlapping pair double-counts. The roll-up does not display child dates, so it would not be
  visible either.
- **Detach silently rebases the annual figures.** The attach branch re-asserts every rule inside the UPDATE;
  the detach branch (`parentId === null`) is unconditional: `UPDATE … SET parent_period_id = NULL WHERE id
  = <id>`. Detaching a **closed** child leaves its `period_results` rows intact but removes them from the
  container's mean and sum, with no warning — and the modal tells the admin the operation is safe without
  qualifying that the annual number will move.
*Fix:* show `n of m children closed` plus child date ranges in the header; reject overlapping siblings at
create/reparent; confirm on detach when the child `has_results`.

**M5 — Three stale documents.**
`bugs.md:67-70` still records **BUG-010 "Period results are not persisted at close"** as `🔴 OPEN`, High,
`Location: no write path`. Live contradicts that: `period_results` exists, the close route writes it, and no
route mutates it. Re-scope rather than simply close — the entry's second half (grades/weights/classification
rewriting history on the next render) remains true for every *unclosed* period and for every live-joined
screen. Second, correct `docs/PERIODS_HIERARCHY_2026-08-2x.md:44`: the per-person aggregate did have a
precedent to copy (§1b). Third, add **BUG-029** (§1); BUG-028 is correctly recorded (Low, open) and its
signature is confirmed — the tracked export has 4 nodes against live's 9.

**M6 — Pre-existing: a failed coefficients call silently un-weights the whole bonus screen.**
Not introduced by this build, and the close path is immune — but it is on the money screen, so it belongs
here. `src/hooks/useFinalScoresMatrix.js:150`:

```js
apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS).catch(() => ({ data: { data: [] } })),
```

On any solo failure — an expired token giving 401, a 500, a network blip — `coefficients` becomes `[]`,
`coefficientsMap` becomes `{}`, and every criterion then hits the client-only early return
`if (!criteriaCoefs) { return score; }` (`:79-81`), which returns the **raw, unweighted** cell score. The
screen renders a full, plausible bonus table, computed without weights or level coefficients, with no error
and no empty state. The server has no equivalent branch — `Compute Close Results` reads weight and
coefficients from the same SQL result as the scores — so **what gets persisted at close stays correct**. The
exposure is an admin distributing a pool from a silently degraded screen. *Fix:* let the failure surface;
same for the grades call on the next line, which defaults every grade coefficient to 1.0 the same way.
File at High in `bugs.md`.

**M7 — Make `period_type = 'annual'` load-bearing.**
"Container" is not a stored type — it is the derived state `child_count > 0`, everywhere: the frontend
(`isContainer = (period) => Number(period?.child_count) > 0`), the activation guard (`target_child_count > 0`
→ 422 `CONTAINER_NOT_ACTIVATABLE`) and the close guard (`child_count > 0` → 422 `CONTAINER_NOT_CLOSABLE`).
`period_type` is stored and displayed but enforces nothing. Consequence, live today: detach H1 from «Annual
2026» and that period — spanning 2026-01-01 → 2026-12-31, already carrying 89 in-scope participant rows —
stops being a container and becomes an ordinary activatable, closable period. Activating it would make a
full-year period the campaign period; closing it would freeze 89 `has_data=false` rows forever. Mid-campaign
the `ACTIVE_PERIOD_HAS_EVALUATIONS` 409 blocks the activation half; before 31 August, with H1 in draft and
zero evaluations, nothing does. *Fix:* gate activate and close on `period_type != 'annual'` as well as on
`child_count`, so an annual period is never a campaign period whatever its children happen to be.

### Observations

- **`api_proof.json`'s `cross_check` is a slogan, and the loop behind it is vacuity-prone.**
  `scripts/prove_periods_hierarchy.py:420` writes the literal string
  `"stored final/index match client matrix+money pipeline (<0.005)"`. The per-user comparison it stands for
  computes `|stored − expected| < 0.005` and then discards both numbers; two silent `continue` paths mean a
  run that compared *nothing* would record the same string. The assertion is almost certainly sound — the
  numbers reproduce by hand (§2) — but the artifact does not carry the evidence. Future proofs should write
  the compared tuples.
- **`rating_*` and `final_rating` are different quantities and will not reconcile — by design.**
  `rating_manager` is `AVG(evaluations.calculated_score)` over every manager-source evaluation, where
  `calculated_score` is the evaluator's own mean over the criteria *that evaluator* graded. `final_rating`
  is the mean of matrix cells, each `mean(manager_score, mid?, c_level?)` with `manager_score` taken
  latest-first. They already diverge with a single evaluator and one correction. The `rating_*` columns are
  archival per-source summaries, not matrix cells. Worth one sentence in `CALCULATION_MAP.md` so nobody
  later reports the gap as a bug.
- **The close staleness guard counts evaluations; it cannot see edits to existing ones.** The `target` CTE
  re-asserts `(SELECT COUNT(*) FROM evaluations WHERE period_id = N) = <count>`, which catches an insert
  during the close window but not an update to a row already counted, and `score_corrections` is not
  re-asserted at all. A close racing an in-flight edit or a fresh calibration correction silently freezes
  the pre-edit number. Narrow window, admin-only, and the right fix is procedural (close after the campaign
  is quiet) rather than a `max(updated_at)` fingerprint.
- **The activation path's re-assertions are snapshot-only.** CLOSE's `target` CTE takes `FOR UPDATE`;
  ACTIVATE's `activatable` CTE does not, and `ACTIVE_PERIOD_HAS_EVALUATIONS` is enforced in JS only, never
  re-asserted inside the UPDATE. Pre-existing, not introduced here, and unreachable in single-admin
  operation — but it is the one place where the build's otherwise consistent belt-and-braces pattern is
  missing a strap. Relatedly, a lost activation race surfaces as **404 "not found or already closed"**,
  where every sibling route returns 409.
- **`FOR UPDATE` locks only `evaluation_periods`.** In the close statement, the `NOT EXISTS` sub-selects
  against `period_results` and `evaluations` are separate query levels and are not locked. Idempotence
  therefore rests on the `status`/`is_active` pair of the locked period row — which is sufficient, because
  only a close can change it and only one close can hold the lock.
- **The throwaway stand holds a second copy of production PII.** `epe_hier_20260821_0549` (~9 MB) sits on
  the live Postgres instance with all 89 restored user rows plus its fixture set. It made this verification
  possible and its retention is deliberate — but it is a duplicate of production personal data outside the
  backup regime. Drop it once this report is accepted.
- **`main` is 9 commits ahead of `origin/main`.** The working tree is clean, but the only copy of the build
  source for what is now running on live is this laptop. Combined with the still-open BUG-014 (no off-host
  backup), that is a single point of failure for the whole H1 delivery.
- **The guard contract fail-opens on an omitted `required_roles`.** `Authorize` guards the role comparison
  behind `parsed.required_roles.length`, and `Verify JWT` normalises a missing or non-array value to `[]`.
  None of the seven periods routes is affected — all declare explicit roles — but a future route that
  forgets the field authenticates without authorizing. Worth a lint or a default-deny.
- **`period_results` stores admins; the roll-up hides them.** The close dataset iterates all participants, so
  `role='admin'` rows are persisted, while the roll-up filters `u.role != 'admin'` (matching the matrix
  precedent). Alexander is stored but not displayed.
- **The `c_level_only` branch and the corrections branch of `finalOf` have no end-to-end coverage.**
  `score_corrections` is empty in both databases, and no `c_level_direct` evaluation exists on the stand, so
  neither branch executed during the proof. Both are covered by static fixtures and both are textually
  identical to the client's, which production does exercise. Criterion 1 carries the largest weight in the
  scheme (5.00) and is `c_level_only`, so the next proof stand should seed a c_level score, a correction,
  and a grade coefficient other than 1.00.
- **`Annual 2025` (period 1) is `closed` with zero `period_results` and can never obtain them.** Feeding it
  to the close route returns 409 `PERIOD_ALREADY_CLOSED`. Correct behaviour — its inputs are the read-only
  archive — but it means an «Annual 2025» container would render «нет сохранённых результатов» for every
  person, which is exactly the state that cell label was written for.
- **The three pre-013 dumps are content-identical.** `_0547`, `_0548`, `_0549` differ only in the embedded
  pg_dump timestamp. Citing `_0549` alone is safe; drop the other two when convenient.
- **`My workflow 10` is an unnamed stray** among the three inactive-unarchived workflows (the other two —
  `API: Global CORS Handler` and `EPE: Auth Guard` — are intentional; the guard must stay inactive because
  it is called via `executeWorkflowTrigger`). Archive it so the baseline count means something.

---

## Method note

Live workflow definitions were read from `postgres.workflow_entity` and decomposed node-by-node before
analysis. Repo exports were compared against them rather than trusted: `API_ Manage Periods.json` and
`route_guard_h1/manage-periods.json` both matched live node-for-node; `API_ evaluations-matrix.json` did not
(4 nodes vs 9), and `build_route_guard_deferred.py` regenerated today did. The throwaway stand database was
read with `SELECT` only, as was live `epe_2026` and the 2025 archive. `npm test` was run locally.
Findings were produced by six independent read-only audits and then put through an adversarial pass
instructed to refute; four claims were downgraded or withdrawn there and are reported at corrected severity.
Nothing was written, deployed, activated, closed, renamed, reparented, or mailed.
