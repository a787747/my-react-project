# RECON — live reclassification, coefficient visibility and scoring freeze

**Date:** 2026-08-22, 04:58–05:06 UTC · **Read-only.** No workflow PUT/activate/deactivate, no DB write,
no deploy, no mail. Every SQL below is `SELECT`. **This brief changed no behaviour.**

**Method.** Facts come from three sources only:

1. Live workflow definitions read out of `postgres_n8n.public.workflow_entity` over the SSH tunnel
   (`ssh root@92.51.45.147 "docker exec postgres_n8n psql -U admin -d postgres -At -c \"SELECT nodes::text FROM public.workflow_entity WHERE id='<id>'\""`).
   33 active workflows were dumped in one pass and parsed. Top-level `n8n_workflows/*.json` exports were
   **not** consulted (BUG-028: at least one is stale against live).
2. Live `epe_2026` / `performance_db` by SELECT.
3. Frontend source in this repo at `9a78e6e`.

Where an answer differs from what the brief expected, or from `docs/HANDOVER.md`, that is stated explicitly.

**Live state at the time of reading** (`SELECT` on `epe_2026`):

| Thing | Value |
|---|---|
| Periods | id 1 `Annual 2025` annual/closed · id 2 `H1-2026` half_year/**draft**, parent 5 · id 5 `Annual 2026` annual/draft |
| `evaluations` / `evaluation_scores` / `period_results` / `score_corrections` | **0 / 0 / 0 / 0** |
| `users.work_category` | 48 `general` / 41 `project` |
| Roles | 1 admin · 5 c_level · 12 manager · 69 employee · 2 hr |

**No period is active.** Every "frozen" statement below is therefore a statement about the code path, not
an observed 409 — nothing on live can 409 today because there is nothing active to freeze against.

---

## 1. Coefficient visibility

### 1.1 The guard, and what an empty role list means

`EPE: Auth Guard` (`L0Zr7nVa8O5YWXd3`, `updatedAt=2026-08-18T16:34:30.674Z`, inactive sub-workflow) node
**`Authorize`**:

```js
if (
  parsed.required_roles.length
  && !parsed.required_roles.includes(String(identity.role))
) { … 403 ROLE_FORBIDDEN … }
```

`required_roles: []` therefore **skips the role check entirely** — the route is *authenticated-only*, open
to every role. Same node: `required_capability` is checked only when non-empty, and only `can_evaluate` /
`can_be_evaluated` are accepted.

### 1.2 Full role → access table

Server outcome for an authenticated, in-session user of each role. Sourced from each workflow's
`Prepare Guard Input` node (`required_roles` / `required_capability` literal) in the live definition.

| Route | admin | c_level | hr | manager | employee | Evidence |
|---|---|---|---|---|---|---|
| **GET `/api/score-coefficients`** | ✅ 200 | ✅ 200 | ✅ **200** | ✅ **200** | ✅ **200** | `API: Get Score Coefficients` `zq3dufVhcnjkS7RV` → `Prepare Guard Input`: `required_roles: []`, `required_capability: ""` |
| **POST `/api/score-coefficients`** | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | `API: Save Score Coefficients` `jAqkljoRb24jrcZx` → `Prepare Guard Input`: `required_roles: ["admin"]` |
| **GET `/api/admin-users-data`** | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | `API: Admin Get Users Data` `AwID96McjHKyk8WI` → `Prepare Guard Input`: `required_roles: ["admin"]` |
| **POST `/manage-criteria`** (all three actions incl. `get`) | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | `API: Manage Criteria Admin V7` `55BHbXWIS6igHHBT` → `Prepare Guard Input`: `required_roles: ["admin"]` |
| **POST `/admin/save-user`** | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | `API: Admin Save User (GUI Mode)` `JCjzhRJtIDW0z8mI` → `Prepare Guard Input`: `required_roles: ["admin"]` |
| **POST `/update-admin-data`** (grade coefficients) | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | ❌ 403 | `API: Update Admin Data` `CkxIyrEJBrc6V4Cv` → `Prepare Guard Input`: `required_roles: ["admin"]` |
| **GET `/api/admin/evaluations-matrix`** | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 | `API: evaluations-matrix` `yQNNr0i4UBFNVgMv` → `required_roles: ["admin","c_level"]` |
| **GET `/api/criteria`** | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 | `API: Get Criteria With Levels` `KKlGLEYMlXlbYUjb` → `required_roles: []` |

**The read-only c_level trio** — Cem Durukan (21), Hemra Ashyrov (40), Mekan Yusupov (61), all
`can_evaluate=false` (measured live) — has **exactly the same outcome as any other c_level** on every row
of this table. None of these routes sets `required_capability`, so `can_evaluate` is never consulted. The
trio differs only on `POST /api/admin/score-correction` (`required_capability: "can_evaluate"` →
403 `CAPABILITY_FORBIDDEN`) and on the submit routes.

### 1.3 Frontend routes

`src/App.jsx:271–291` and `src/App.jsx:311` put **AdminScoring (`/admin/scoring`), AdminFinalScores
(`/admin/final-scores`), BonusCalculation (`/admin/bonus-calculation`)** and AdminScoreCalculator behind
`AdminRoute`, which is `canAccessAdminPanel` = `['admin','c_level','hr']` (`src/utils/permissions.js:15-16`).
So **HR and c_level can open all three money screens.** What they then see is decided by the APIs:

| Screen | admin | c_level | hr |
|---|---|---|---|
| `/admin/scoring` (`AdminScoring` → `useScoreCoefficients`) | full: weights + level coefficients + grades | **weights + level coefficients render; grades silently empty** | **weights + level coefficients render; grades silently empty** |
| `/admin/final-scores`, `/admin/bonus-calculation` (`useFinalScoresMatrix`) | full | error card (grades 403) | error card (matrix + grades 403) |

The `/admin/scoring` asymmetry is in `src/hooks/useScoreCoefficients.js:42-48`: the grades call is
`.catch(...)`-swallowed to `{ options: { grades: [] } }`, while the coefficients call is not wrapped. A
non-admin therefore gets a rendered coefficients table with an empty grades table and **no error**. The
money screens do not have this hole — `useFinalScoresMatrix.js:164-193` uses `Promise.allSettled` and
fails loudly (the BUG-030 fix).

### 1.4 Every client consumer of GET `/api/score-coefficients`

Four, from `grep -rn "SCORE_COEFFICIENTS" src/` (endpoint defined at `src/config/api.js:98`):

| # | Call site | Page(s) | Audience | Purpose |
|---|---|---|---|---|
| 1 | `src/hooks/useFinalScoresMatrix.js:166` | AdminFinalScores, BonusCalculation | admin/c_level/hr (route), admin in practice | bonus index |
| 2 | `src/hooks/useScoreCoefficients.js:43` | AdminScoring | admin/c_level/hr | edit weights + coefficients |
| 3 | `src/hooks/useScoreCalculation.js:79` | AdminScoreCalculator | admin/c_level/hr | what-if calculator |
| 4 | **`src/hooks/useSelfReview.js:93-94`** | **SelfReview** | **every employee** | **client-side weighted self-review value** |

**W5 confirmed, not refuted.** `useSelfReview.js:93-94` fetches the full weights + level-coefficient
table for every person filling in a self-review. It is used at `src/hooks/useSelfReview.js:174-175`:

```js
const gradeCoef = user?.grade_coefficient || 1.0;
const weightedScore = calculateWeightedScore(grades, criteriaWithCoefficients, gradeCoef);
```

and POSTed as `weighted_score` (`useSelfReview.js:180`). The server accepts it as given —
`API: Submit Self Review` → `Validate Self Review` only checks it is finite and `>= 0`, then stores it
verbatim into `evaluations.weighted_score`. **The weighted self-review value is computed on the client
today, from a coefficient table every employee can read.**

Two details worth separating:

- `user.grade_coefficient` is **not** in the self-review payload path in practice: `/api/employees` and
  `/api/get-my-manager` both strip `grade_coefficient` unless the role is admin or c_level
  (`API: Get Employees (Smart Role Based)` → `Format Response`: `if (!canSeeGradeCoefficient) delete safeEmployee.grade_coefficient;`
  and the equivalent spread in `API: Get My Manager` → `Format Response`). So for an employee the
  fallback `|| 1.0` applies. **Grade coefficients are already admin+c_level-only. Criterion weights and
  level coefficients are not.**
- `GET /api/criteria` (§3.1) also returns `weight` to every role, independently of
  `/api/score-coefficients`. Closing one and not the other leaves weights readable.

---

## 2. Current freeze semantics, exactly

Two different triggers are in use. They are not the same event.

| Write route | Returns | Trigger | Enforced where |
|---|---|---|---|
| `POST /admin/save-user` (**classification**) | **409 `CLASSIFICATION_FROZEN`** | **first submitted evaluation in the active period** | `API: Admin Save User (GUI Mode)` — SQL in `Validate User Data`, decision in `Build User Upsert` |
| `POST /api/score-coefficients` (**weights + level coefficients**) | **409 `ACTIVE_PERIOD_EXISTS`** | **period activation** | `API: Save Score Coefficients` — SQL in `Validate No Active Period`, decision in `Build Coefficients Update` |
| `POST /update-admin-data` (**grade coefficients**) | **409 `ACTIVE_PERIOD_EXISTS`** | **period activation** | `API: Update Admin Data` — SQL in `Check Freeze`, decision in `Build SQL` |
| `POST /manage-criteria` `action=save`/`delete` (**criteria catalogue**) | **409 `ACTIVE_PERIOD_EXISTS`** | **period activation** | `API: Manage Criteria Admin V7` — SQL in `Route Action` (write branch), decision in `Prepare Write` |
| `POST /manage-criteria` `action=get` | never frozen | — | `Route Action` returns the `get` branch before the freeze SQL is built |

All four are **node logic in a Code node reading the result of a preceding SELECT** — none is a database
constraint and none is in the guard.

### 2.1 Classification — freeze on first submission

`API: Admin Save User (GUI Mode)` → `Validate User Data` builds, only when updating an existing user:

```sql
SELECT u.work_category AS old_category,
   EXISTS(
     SELECT 1 FROM performance_db.evaluations e
     JOIN performance_db.evaluation_periods p
       ON p.id = e.period_id AND p.is_active = true AND p.status = 'active'
   ) AS period_has_any_evaluation
 FROM performance_db.users u WHERE u.id = ${userId} LIMIT 1
```

→ `Build User Upsert`:

```js
if (!prev.is_new && check && check.old_category && check.old_category !== prev.work_category) {
  if (check.period_has_any_evaluation) { … 409 CLASSIFICATION_FROZEN … }
}
```

Three properties that matter for the redesign:

- The `EXISTS` is **global**, not per-subject: *any* evaluation by *anyone* for *anyone* in the active
  period freezes *every* person's classification.
- The freeze fires **only when the category actually changes**. Saving a user with an unchanged
  `work_category` passes, so every other field on the user form stays editable after the freeze.
- A **new** user (`is_new`) is never checked.

### 2.2 Coefficients, grades and criteria — freeze on activation

All three run the identical SELECT:

```sql
SELECT id, name, status
FROM performance_db.evaluation_periods
WHERE is_active = true OR status = 'active'
LIMIT 1
```

and 409 if it returns a row. The `OR` is not tied to the period being written about — it is "does any
active period exist anywhere".

### 2.3 The criteria catalogue **is** frozen — brief expectation refuted

The brief expected "criteria catalogue writes: never frozen — confirm". **That is not the live
behaviour.** `API: Manage Criteria Admin V7` → `Prepare Write` contains:

```js
const activePeriod = $input.all().map(item => item.json).find(item => item.id !== undefined);
if (activePeriod) {
  return { json: { http_status: 409, body: { success: false, error: 'ACTIVE_PERIOD_EXISTS',
    message: `Нельзя менять критерии во время активного периода «${activePeriod.name}»` } } };
}
```

The client already expects this: `src/hooks/useCriteria.js:63-66` maps a 409 to
«Критерии заморожены, пока период активен».

### 2.4 Weights **are** frozen — `HANDOVER.md` §6.11 is wrong on this point

`docs/HANDOVER.md` §6 item 11 says the freeze is "de facto enforced for classification and coefficients
(409 while a period is active) but **not** for weights". Measured against live, weights are frozen through
**both** paths that can write them. Exhaustive search of all 33 active workflows for writes to
`criteria.weight`, `grades.coefficient` and `score_coefficients` returns exactly three producers:

| Workflow | Node | Statement | Behind a 409? |
|---|---|---|---|
| `API: Save Score Coefficients` | `Build Coefficients Update` | `UPDATE performance_db.criteria SET weight = ${weight} WHERE id = ${criteriaId};` | **yes** — `ACTIVE_PERIOD_EXISTS` |
| `API: Save Score Coefficients` | `Build Coefficients Update` | `INSERT INTO performance_db.score_coefficients … ON CONFLICT (criteria_id, score_level) DO UPDATE …` | **yes** — same node |
| `API: Manage Criteria Admin V7` | `Prepare Write` | `UPDATE performance_db.criteria …` (full criterion save) | **yes** — `ACTIVE_PERIOD_EXISTS` |
| `API: Update Admin Data` | `Build SQL` | `UPDATE performance_db.grades SET coefficient = …` | **yes** — `ACTIVE_PERIOD_EXISTS` |

There is no unfrozen write path to a weight on live. BUG-010's remaining half should be re-read against
this: the live gap is not "weights are editable during a period", it is "everything is *live-joined* until
close, so an edit made **before** activation or **after** close re-renders history" (§4.4).

---

## 3. Criteria presentation per path

### 3.1 The server never filters

`API: Get Criteria With Levels` (`KKlGLEYMlXlbYUjb`) → `Build Criteria Query`:

```sql
SELECT id, title, description, target_audience, weight, is_active,
  selfassesment, for_manager, c_level_only,
  level_0_desc, … level_10_desc
FROM performance_db.criteria
ORDER BY id ASC
```

**No `WHERE` clause at all** — not `is_active`, not `target_audience`, not classification. Every
authenticated role receives every row of the catalogue. The only server-side redaction is in
`Format Response`: for `c_level_only` rows, `level_1_desc … level_10_desc` are deleted unless the role is
admin or c_level (`level_0_desc` is not in that list — both live `c_level_only` rows have it empty, so
nothing leaks through it today).

### 3.2 Per-path table

| Path | Criteria source | Set served | Filter applied | Where |
|---|---|---|---|---|
| **Manager form** | `GET /api/criteria` | whole catalogue | **client** | `filterCriteriaByEmployee` — `src/utils/evaluationUtils.js:108-135`, called from `src/components/EvaluationModal.jsx:70`. Drops `!is_active`; drops `project_participants` when `!employee.is_project_participant`; drops `c_level_only` unless the evaluator's role is `c_level`. **Does not filter `managers_only`** — that grouping happens in `src/pages/Dashboard.jsx:105-111` for the count badge only |
| **Upward** (subordinate → manager) | `GET /api/criteria` | whole catalogue | **client** | `src/hooks/useManagerEvaluation.js:101-106` — `c.is_active && c.target_audience === 'managers_only' && !c_level_only` |
| **`c_level_direct`** | `GET /api/admin/evaluations-matrix` (`employee.criteria`) | every active criterion, per person (§4.1) | **client** | `src/components/admin/CLevelEvaluationModal.jsx:25,38` → `groupCriteria(...).c_level` = `src/utils/matrixUtils.js:24` — `criteria.filter(c => c.c_level_only)` |
| **Self-review** | `GET /api/criteria` | whole catalogue | **client** | `src/hooks/useSelfReview.js:105-114` — `is_active && selfassesment && !c_level_only && (audience === 'all' \|\| audience === user.work_category)` |

**Every path filters on the client. No path filters server-side.**

### 3.2.1 Where the classification the client filters on comes from — and how stale it can be

Two different sources, with different freshness:

- **Manager form and `c_level_direct`** read `is_project_participant` off the *subject* row in the API
  response — `/api/employees` (`API: Get Employees (Smart Role Based)` → `scoped` CTE selects
  `users.is_project_participant`) and the matrix payload respectively. Both are fetched per page load, so
  they reflect the current database value.
- **Self-review** reads the *actor's own* `user.work_category` from React context
  (`src/hooks/useSelfReview.js:111`, dependency `user?.work_category` at `:157`). That object is populated
  at **login** — `API: Auth Login (No Params)` → `Load User and Attempts` selects `u.work_category` — and
  `src/context/UserContext.jsx:50-53` writes it to `localStorage`, from which `:27-32` restores it on
  mount. There is **no refresh path**: nothing re-reads the profile into the context, so
  `user.work_category` is a **login-time snapshot**.

Consequence for a mid-campaign switch: the person's own self-review form keeps filtering on their **old**
category until they log in again. The 4-hour token bounds this in practice, but only because expiry forces
a re-login — nothing in the app invalidates the stale value on its own.

### 3.3 No write path validates applicability

Exhaustive check of `API: Submit Evaluation`, `API: Submit Self Review` and
`API: Update Evaluation WITH PERIOD` for any reference to `target_audience`, `is_project_participant`,
`work_category`, or a join to `performance_db.criteria`:

```
API: Submit Evaluation:            NO criteria-applicability reference found
API: Update Evaluation WITH PERIOD: NO criteria-applicability reference found
API: Submit Self Review:           NO criteria-applicability reference found
```

The only per-criterion validation on all three is in the `Build … SQL` nodes: `criteriaId` must be a finite
integer `>= 1` and `scoreValue` a finite integer in `1..10`. **A caller may submit any criterion id for any
subject** — including a `project_participants` criterion for a `general` person, or a `c_level_only`
criterion from a manager. The presented set is a client convention, not a server contract.

---

## 4. Row selection in the money math

**Answer: the money math sums whatever score rows exist. The subject's classification is never consulted
— not in SQL, not on the client, not at close time.**

### 4.1 The matrix API returns a cartesian product

`API: evaluations-matrix` (`yQNNr0i4UBFNVgMv`) → `Build Matrix Query`, closing clause:

```sql
FROM performance_db.users u
LEFT JOIN performance_db.departments d ON u.department_id = d.id
LEFT JOIN performance_db.grades g ON u.grade_id = g.id
LEFT JOIN performance_db.evaluation_period_participants epp
  ON epp.user_id = u.id AND epp.period_id = ${periodId}
CROSS JOIN performance_db.criteria c
WHERE u.role != 'admin'
  AND c.is_active = true
GROUP BY …
ORDER BY u.full_name
```

`CROSS JOIN criteria c … WHERE c.is_active = true` — **every active criterion is emitted for every
non-admin person**, regardless of `target_audience`, `work_category` or `is_project_participant`. The
per-criterion `self_score` / `manager_score` / `c_level_score` / correction values are correlated
sub-selects that return `NULL` when no score row exists.

### 4.2 The client sums the non-null cells

`src/hooks/useFinalScoresMatrix.js:236-247`:

```js
emp.criteria.forEach(crit => {
  const rawScore = getCriterionFinalScore(crit);
  if (rawScore !== null) {
    const weightedScore = calculateCriterionScore(rawScore, crit.criteria_id, coefficientsMap);
    criteriaScores[crit.criteria_id] = weightedScore;
    weightedSum += weightedScore || 0;
  }
});
```

`getCriterionFinalScore` (`useFinalScoresMatrix.js:56-82`) returns `null` when `manager_score` is
null (or `c_level_score` for `c_level_only`). So **existence of a score row is the entire selection
predicate**; then `final_weighted_score = weightedSum × gradeCoefficient`
(`useFinalScoresMatrix.js:252-253`).

### 4.3 Close time uses the same predicate

`API: Manage Periods` (`M9ljMDdO1mIl8m1h`) → `Build Close Dataset Query` builds
`criteria_data AS (SELECT c.id, c.weight, c.c_level_only, … FROM performance_db.criteria c WHERE c.is_active = true)`
and aggregates `FROM criteria_data cd` for **every participant** — again no classification filter — with
the same null-returning sub-selects. `Compute Close Results` then mirrors the client exactly:

```js
for (const crit of (row.criteria || [])) {
  const raw = finalOf(crit);
  if (raw !== null) { finals.push(raw); weightedSum += weightedOf(raw, crit); }
}
```

So the frozen `period_results.bonus_index` inherits the same semantics.

### 4.4 Consequences for the reclassification decision

- Switching **general → project** mid-campaign adds nothing by itself. The extra criteria only enter the
  index once someone actually submits scores for them.
- Switching **project → general** mid-campaign removes nothing. Score rows already written for the
  project criteria **remain and keep being summed** — the index does not shrink. The only thing that
  removes them is `update-evaluation` re-submitting a narrower set (§7.2), which deletes them permanently.
- Because the index has no denominator (HANDOVER §4), this is a money asymmetry, not a rounding one.

---

## 5. Completion semantics

**All three flags are evaluation-row existence. None is per-criterion completeness.**

`API: Get Employees (Smart Role Based)` (`bKB4Sb46yWoq1tSV`) → `Build Identity-Bound Query`, inside the
`scoped` CTE:

```sql
EXISTS (SELECT 1 FROM performance_db.evaluations self_eval
        WHERE self_eval.subject_id = users.id
          AND self_eval.is_self_evaluation = true
          AND self_eval.period_id = ap.id)                     AS has_self_review,
EXISTS (SELECT 1 FROM performance_db.evaluations upward_eval
        WHERE upward_eval.evaluator_id = users.id
          AND upward_eval.subject_id = ${actorId}
          AND upward_eval.evaluation_source = 'subordinate'
          AND upward_eval.period_id = ap.id)                   AS has_evaluated_manager,
EXISTS (SELECT 1 FROM performance_db.evaluations actor_eval
        WHERE actor_eval.evaluator_id = ${actorId}
          AND actor_eval.subject_id = users.id
          AND actor_eval.is_self_evaluation = false
          AND actor_eval.period_id = ap.id)                    AS evaluated_by_actor
```

None of the three joins `evaluation_scores` or counts criteria. Corroborating routes:

- `API: Check Self Review` (`QRkUvs24DkcC3WBW`) → `Format Response`: `has_self_review: true` iff the
  single-row query returned an `evaluations` row. It does return `evaluated_criteria_ids` (an
  `ARRAY_AGG(es.criteria_id)` over the joined score rows) — **that array is the only per-criterion signal
  anywhere in the system**, and it is used only by the self-review page to compute `newCriteria`
  (`src/hooks/useSelfReview.js:122-127`).
- `API: Check Evaluated V2` (`msl2T1flMo1Hn7uj`) → `Build Evaluated Query`: selects `evaluations` rows by
  `evaluator_id` in the active period. Row existence again.

An evaluation submitted with one criterion out of five is therefore "done" on every dashboard.

---

## 6. The «Оценить новые критерии» path (BUG-036 row 7)

**What it calls.** The button is `src/components/self-review/SelfReviewStatusCard.jsx:76-82`, rendered on
`/self-review` in the branch that fires when `newCriteriaCount > 0`. Its `onClick` is the prop
`onStartReview`, bound at `src/pages/SelfReview.jsx:175` to `() => setIsModalOpen(true)` — it opens the
self-review modal on the same page, it does not navigate. The modal is fed
`criteriaToShow = hasReview ? newCriteria : criteria` (`src/pages/SelfReview.jsx:126`), so it presents
**only the criteria not already scored**. Submitting runs `submitReview`
(`src/hooks/useSelfReview.js:160-186`) → `apiClient.post(API_ENDPOINTS.SELF_REVIEW_SUBMIT, payload)`
(`:186`) = **`POST /api/self-review-submit`**, with `is_update: hasReview` in the body (`:183`).

**What produces the unconditional 409 — two independent places, both in `API: Submit Self Review`
(`CuHkTYvGDyhqEarg`):**

1. `Validate Self Review` builds the scope query with a duplicate probe:

   ```sql
   EXISTS(
     SELECT 1 FROM performance_db.evaluations dup
     WHERE dup.subject_id = ${actorId}
       AND dup.evaluator_id = ${actorId}
       AND dup.period_id = p.id
       AND dup.is_self_evaluation = true
   ) AS is_duplicate
   ```

   `Build Self Review Insert` then returns, before building any SQL:

   ```js
   if (check.is_duplicate) {
     return { json: { http_status: 409, body: { success: false,
       error: 'DUPLICATE_SELF_REVIEW', message: 'Самооценка за этот период уже отправлена' } } };
   }
   ```

2. Even if that were bypassed, the insert is
   `ON CONFLICT (subject_id, period_id) WHERE is_self_evaluation = true DO NOTHING`, and `Format Response`
   turns the zero-row result into the same 409 (`'Самооценка за этот период уже была отправлena'` — race path).

**`is_update` is read nowhere on the server.** Measured: `grep -c is_update` over the live
`API: Submit Self Review` definition = **0**, and over all 33 active workflow definitions = **0**. It
exists only at `src/hooks/useSelfReview.js:183`.

So the button is reachable exactly when `has_self_review` is true, and that is exactly the condition that
makes `is_duplicate` true. It can only ever 409. BUG-036 row 7 is confirmed against live, with the
mechanism located.

---

## 7. Partial-write behaviour

### 7.1 Submit — the first write wins, permanently

`API: Submit Evaluation` (`tUxHoRn38rJVDxWv`) → `Build Insert SQL`:

```sql
WITH score_rows(crit_id, score_val, cmt) AS ( VALUES … ),
new_eval AS (
  INSERT INTO performance_db.evaluations
    (subject_id, evaluator_id, period_id, calculated_score, evaluation_source,
     is_self_evaluation, status, general_comment, updated_at)
  SELECT ${subjectId}, ${actorId}, ${periodId},
         (SELECT AVG(score_val::numeric) FROM score_rows), '${source}', false, 'completed', …, now()
  WHERE EXISTS (SELECT 1 FROM score_rows)
  ON CONFLICT (subject_id, evaluator_id, evaluation_source, period_id)
  WHERE is_self_evaluation = false
  DO NOTHING
  RETURNING id
)
INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
SELECT ne.id, sr.crit_id, sr.score_val, sr.cmt
FROM new_eval ne CROSS JOIN score_rows sr
RETURNING evaluation_id
```

Given a **subset** of the applicable criteria:

- **Upsert key:** `(subject_id, evaluator_id, evaluation_source, period_id)` partial-unique on
  `is_self_evaluation = false`. `DO NOTHING`, never `DO UPDATE`.
- Exactly the supplied rows are written to `evaluation_scores`. The missing criteria have **no row** —
  indistinguishable from "not applicable".
- `calculated_score` is `AVG` over **only the supplied rows** — the rating is the average of the subset,
  not of the applicable set.
- Any **second** submit for the same tuple hits the conflict, inserts zero score rows, and
  `Format Response` returns **409 `DUPLICATE_EVALUATION`**. There is no additive path.

Self-review is the same shape with key `(subject_id, period_id) WHERE is_self_evaluation = true` (§6).

### 7.2 Update — the submitted set is authoritative and destructive

`API: Update Evaluation WITH PERIOD` (`LWuZNTehzMDJkE8u`) → `Build Update SQL`:

```sql
WITH score_rows(crit_id, score_val, cmt) AS ( VALUES … ),
updated_header AS (
  UPDATE performance_db.evaluations
  SET calculated_score = (SELECT AVG(score_val::numeric) FROM score_rows),
      general_comment = …, updated_at = now()
  WHERE id = ${evalId}
    AND evaluator_id = ${actorId}
    AND (SELECT status FROM performance_db.evaluation_periods WHERE id = period_id) != 'closed'
  RETURNING id, calculated_score
),
upserted_scores AS (
  INSERT INTO performance_db.evaluation_scores (evaluation_id, criteria_id, score_value, comment)
  SELECT uh.id, sr.crit_id, sr.score_val, sr.cmt
  FROM updated_header uh CROSS JOIN score_rows sr
  ON CONFLICT (evaluation_id, criteria_id) DO UPDATE
    SET score_value = EXCLUDED.score_value, comment = EXCLUDED.comment
  RETURNING criteria_id
),
removed_scores AS (
  DELETE FROM performance_db.evaluation_scores
  WHERE evaluation_id = ${evalId}
    AND criteria_id NOT IN (SELECT crit_id FROM score_rows)
  RETURNING criteria_id
)
SELECT uh.id AS evaluation_id, uh.calculated_score AS final_score,
       (SELECT count(*)::integer FROM upserted_scores) AS scores_saved
FROM updated_header uh
```

- **Upsert key:** `(evaluation_id, criteria_id)`, `DO UPDATE` — supplied criteria are overwritten in place.
- **Score rows no longer in the presented set are `DELETE`d, permanently.** This is the direct answer to
  the brief's last clause: a narrower presented set does not "exclude from computation", it **destroys the
  data**. There is no soft-delete, no history table, no audit row.
- `calculated_score` is recomputed as the `AVG` of the submitted subset only.
- Ownership and non-closed-period are re-asserted inline in `updated_header`'s `WHERE` (the deliberate
  race-closing described in the node's own comment), and `Format POST Response` maps a zero-row result to
  403.

This is the mechanism a "continue evaluation" redesign would have to build on, and today it is
subtractive by construction: whatever the client shows is what survives.

**It also carries a live defect — see §8.**

---

## 8. New defect found: BUG-041

Filed in `bugs.md`. Summary here because it bears directly on the redesign.

In §7.2, `removed_scores` is gated **only** on `evaluation_id = ${evalId}`. It does not reference
`updated_header`, and nothing in the outer `SELECT` reads it. PostgreSQL executes data-modifying `WITH`
clauses *"exactly once, and always to completion, independently of whether the primary query reads all (or
indeed any) of their output"*. So when the inline re-assertion in `updated_header` selects zero rows —
the period was closed, or the evaluation's `evaluator_id` changed, in the window between
`Execute Ownership Check` and `Execute Update` — the header `UPDATE` and the `INSERT` write nothing, the
caller correctly receives **403**, and **the `DELETE` still runs.**

The node comment states the intent: *"Reassert evaluator ownership and non-closed period inline in the
UPDATE WHERE clause to close the validation/mutation race."* The race is closed on the two constructive
branches and left open on the destructive one.

Not reachable through ordinary use: `Validate Update` → `Execute Ownership Check` returns 404/403 first,
so an unauthorized caller never reaches the SQL. It needs the race window. **No runtime proof was run** —
this brief is read-only and executing it would require a write. The finding rests on the live SQL text and
documented PostgreSQL `WITH` semantics.

Live impact today: **none** — `evaluation_scores` has 0 rows and no period is active.

---

## Surfaced for decision

Facts that make one of the three decisions expensive or contradictory. Not resolved here.

1. **Decision 2 is the inverse of live behaviour, for all three quantities.** Alexander wants weights,
   level coefficients and grade coefficients editable *until period close*. Today all three 409 the moment
   the period is **activated** (§2.2, §2.4) — the widest possible freeze, applied at the earliest possible
   moment. This is not a small edit: it is three workflows whose freeze is the only thing standing between
   an admin and silently rewriting a live campaign's money inputs.

2. **Decision 1's "Activate" gate collides with the same three 409s.** A preparation window in which
   "admin can still edit everything" is, in current code, precisely the state that forbids editing
   criteria, weights and grade coefficients. Whatever the new `activate` state is called, it cannot reuse
   `is_active = true OR status = 'active'` as its freeze predicate without contradicting its own purpose.

3. **`HANDOVER.md` §6.11 mis-states the current position** ("not enforced for weights"). Live has no
   unfrozen write path to any weight (§2.4). A decision taken from that sentence would be taken from a
   wrong premise. The real residue of BUG-010 is live-joining, not editability.

4. **Nothing enforces criteria applicability on any write path** (§3.3). Reclassification "adds the newly
   applicable criteria" is therefore not a server concept today — the server accepts any criterion for any
   subject. Either the redesign introduces the first server-side applicability check, or "applicable" stays
   a client convention and the freeze cannot be enforced.

5. **"Exclude the extra criteria from all computations" has no place to live.** Both money paths select by
   score-row existence (§4). There is no per-(subject, criterion) applicability record — the only
   candidate, `criteria.target_audience` joined to `users.work_category`, is exactly the thing being made
   mutable. Excluding a criterion after a switch requires either deleting its score rows (destructive,
   §7.2) or introducing a new record of what applied when.

6. **Reclassification is asymmetric on money** (§4.4). general→project is inert until someone evaluates;
   project→general does not reduce an index that already counted the project criteria. If the two
   directions are meant to behave alike, that is new behaviour, not a filter change.

7. **"Continue evaluation" cannot be built on the submit routes as they stand** (§7.1). Both submits are
   `DO NOTHING` on conflict and 409 on the second call. The only additive-capable route is
   `update-evaluation`, which is subtractive by construction (§7.2) and carries BUG-041 (§8).

8. **A reclassified person does not see their own new criteria until they log in again** (§3.2.1). The
   self-review form filters on a login-time `work_category` snapshot held in `localStorage` with no
   refresh path, while the manager form filters on a freshly-fetched subject row. So the same switch takes
   effect immediately for the manager and only after re-login for the person themselves — and "continue
   evaluation" is precisely the flow that depends on the person seeing the addition.

9. **Completion flags cannot express "partially evaluated"** (§5). Every dashboard flag is row existence.
   The moment classification can change mid-campaign, "evaluated" and "evaluated against the criteria that
   now apply" become different questions, and no surface can currently distinguish them. The single
   per-criterion signal that exists — `evaluated_criteria_ids` in `check-self-review` — is on the
   self-review path only.

10. **Decision 2's "admin ONLY" is one route away, but not one line away.** `GET /api/score-coefficients`
   is authenticated-only (§1.1) and every employee reads it during self-review (§1.4). Restricting it
   breaks the self-review weighted value unless that computation moves server-side first — which is the
   other half of decision 2, so the two must ship together. `GET /api/criteria` **also** returns `weight`
   to every role (§3.1); closing one route without the other leaves weights readable. Grade coefficients
   are already correctly gated.

---

## Appendix — verbatim live dump (for `EVALUATION_METHODOLOGY.md`)

Read 2026-08-22 05:0x UTC by SELECT on `epe_2026`, schema `performance_db`.

### A.1 `criteria` — all 8 rows

```
 id |                    title                    |       audience       | weight | is_active | self | mgr | clvl
----+---------------------------------------------+----------------------+--------+-----------+------+-----+------
  1 | Стратегическая значимость роли              | all                  |   5.00 | t         | f    | f   | t
  2 | Качество управления и развитие команды      | managers_only        |   3.00 | t         | f    | t   | f
  3 | Личная результативность и эффективность     | all                  |   3.00 | t         | t    | t   | f
  4 | Надежность и взаимодействие с руководителем | all                  |   1.50 | t         | t    | t   | f
  8 | Взаимодействие и надежность в проекте       | project_participants |   1.40 | t         | f    | t   | f
 10 | Оценка C-Level и соответствие культуре      | all                  |   1.60 | t         | f    | f   | t
 12 | Профессиональное развитие и обмен знаниями  | all                  |   1.00 | t         | t    | t   | f
 13 | Объем проектной работы и загрузка           | project_participants |   1.80 | t         | f    | t   | f
(8 rows)
```

`self` = `selfassesment`, `mgr` = `for_manager`, `clvl` = `c_level_only`. The table has **no inactive
rows** — all 8 are `is_active = true`. Ids 5, 6, 7, 9, 11 are absent.

### A.2 `score_coefficients` — all 80 rows

Ten levels per criterion, for each of the 8 criteria. Transposed for readability; the source is
`SELECT criteria_id, score_level, coefficient FROM performance_db.score_coefficients ORDER BY criteria_id, score_level`.

| criteria_id | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.30 | 0.40 | 0.60 | 0.70 | 1.00 | 1.20 | 1.60 | 2.80 | 4.00 | 6.00 |
| 2 | 0.40 | 0.60 | 0.80 | 0.90 | 1.00 | 1.20 | 1.40 | 1.60 | 2.00 | 2.40 |
| 3 | 0.40 | 0.50 | 0.60 | 0.70 | 0.90 | 1.10 | 1.30 | 1.60 | 2.00 | 2.30 |
| 4 | 0.40 | 0.60 | 0.80 | 0.90 | 1.00 | 1.10 | 1.20 | 1.50 | 2.00 | 2.50 |
| 8 | 0.50 | 0.70 | 0.80 | 0.90 | 1.00 | 1.10 | 1.20 | 1.60 | 2.50 | 3.00 |
| 10 | 0.50 | 0.70 | 0.80 | 0.90 | 1.00 | 1.20 | 1.50 | 1.80 | 2.20 | 2.50 |
| 12 | 0.50 | 0.70 | 0.80 | 0.90 | 1.00 | 1.10 | 1.30 | 1.50 | 1.80 | 2.00 |
| 13 | 0.50 | 0.70 | 0.80 | 0.90 | 1.00 | 1.30 | 1.80 | 2.80 | 3.80 | 4.20 |

There is **no `score_level = 0` row** for any criterion. `GET /api/score-coefficients` →
`Format Response` fills levels 1–10 only; `useFinalScoresMatrix.calculateCriterionScore` clamps to
`0..10` and falls back to `1.0` for a missing level, so a rounded final score of 0 would silently use
coefficient 1.0. Not reachable today — score values are validated `1..10` on every write path.

### A.3 `grades` — all 11 rows with coefficients

```
 id | code  |               description                | coefficient
----+-------+------------------------------------------+-------------
  1 | C3    | C-Level 3 - Топ-менеджмент               |        1.00
  2 | C2    | C-Level 2 - Операционное руководство     |        1.00
  3 | C1    | C-Level 1 - Административное руководство |        1.00
  4 | M3    | Manager 3 - Старший руководитель         |        3.00
  5 | M2    | Manager 2 - Руководитель отдела          |        3.00
  6 | S4-M1 | Senior Specialist / Junior Manager       |        2.20
  7 | S3    | Specialist 3 - Старший специалист        |        1.40
  8 | S2    | Specialist 2 - Специалист                |        1.10
  9 | S1    | Specialist 1 - Младший специалист        |        0.60
 10 | A     | Assistant - Ассистент                    |        0.30
 11 | M1    | Senior Specialist / Junior Manager       |        2.20
```

Two observations, recorded not resolved: ids 6 (`S4-M1`) and 11 (`M1`) share the description
*"Senior Specialist / Junior Manager"* and the coefficient 2.20 — a probable duplicate grade. And the
matrix looks grades up **by `code`**, not by id (`useFinalScoresMatrix.js:213-214`,
`gradesMap[g.code] = parseFloat(g.coefficient) || 1.0`; `:251-252`,
`gradesMap[emp.grade_code] || 1.0`), so two grades sharing a code would silently collapse. The 11 codes
are distinct today.

---

## Riders

- **`9a78e6e` push state.** It was **not** on origin at session start — `git branch -vv` reported
  `main 9a78e6e [origin/main: ahead 1]`, and `git rev-parse origin/main` was `375b8c1`. Pushed:

  ```
  To https://github.com/a787747/my-react-project.git
     375b8c1..9a78e6e  main -> main
  ```

  Verified after: `git branch -vv` → `* main 9a78e6e [origin/main]`, and `git branch -r --contains 9a78e6e`
  → `origin/HEAD -> origin/main`, `origin/main`.
- **`docs/HANDOVER.md` §10 counts.** Measured from `bugs.md` before this brief wrote anything:
  `grep -c '^- Status: 🔴 OPEN'` = 18 plus one `🔴 OPEN (re-scoped 2026-08-21 …)` = **19 open**;
  `grep -c '^- Status: 🟢 CLOSED'` = **21 closed** (40 `### BUG-` headings). That confirms the brief's
  expected 19 / 21 and refutes the line's `20 open / 20 closed`.

  **The line was then set to `20 open / 21 closed`, not `19 / 21`** — filing BUG-041 (§8) in the same
  session makes 20 the true count, and writing 19 would have left the line stale again on commit. The
  pre-existing figure is recorded here so the two numbers are not confused. One line changed in
  `HANDOVER.md`, nothing else touched.
- **`bugs.md`** gained BUG-041 only (§8), plus the `🔴 Open` statistics cell 19 → 20 that the new row
  requires. No existing row was re-triaged. Post-write measurement: 20 open / 21 closed, matching the
  statistics table and `HANDOVER.md` §10.
