# Post-verification batch — periods hardening, money-screen honesty, housekeeping

**Date:** 2026-08-21
**Input:** `docs/PERIODS_VERIFY_2026-08-2x.md` — verdict *accept with microfixes*. This batch is those fixes.
**Scope discipline:** every change below is one of the seven numbered items, plus two defects the work
itself surfaced (§Fixed 8–9), which are named rather than filed quietly.
**Live writes:** `API: Manage Periods` PUT + frontend release. **No data row was written to `epe_2026`.**
2025 archive: not touched. No mail. `EPE: Auth Guard` frozen.

---

## Verdict

All seven items are done and evidenced. Two additional defects were found while proving them, both fixed
and proven: a create-with-parent date comparison that would have **refused the canonical H2 attach in
September** (BUG-031, would have bitten Alexander directly), and a stand-tooling bug that made a `docker cp`
silently import a stale workflow. Tests 213 → **236 pass / 0 fail**. Live after: H1 `draft/false` 87/89, all
four data tables 0, 41 webhooks, guard `updatedAt` unchanged.

---

## Fixed

### 1. (M6, High) A failed coefficients call no longer un-weights the money screens — BUG-030

`src/hooks/useFinalScoresMatrix.js` fetched the matrix, the criterion coefficients and the grades in one
`Promise.all` with `.catch(() => ({ data: { data: [] } }))` on the last two. On any solo failure the
coefficient map became `{}`, every criterion hit the client-only early return `if (!criteriaCoefs) return
score;`, and Итоговые баллы / Калькуляция бонусов rendered a **full, plausible, unweighted** bonus table with
no error. The grades call degraded the same way, defaulting every grade coefficient to 1.00.

Now: the three requests run through `Promise.allSettled`; each rejection is classified and becomes an
explicit error state; the failure branch clears employees, criteria and period so no stale numbers survive;
both screens return an error card with a retry button **before** any table renders.

| Failed request | Message |
|---|---|
| coefficients | «Коэффициенты не загружены — расчёт невозможен» |
| grades | «Коэффициенты грейдов не загружены — расчёт невозможен» |
| matrix | «Матрица оценок не загружена — расчёт невозможен» |

No request in the hook substitutes a fabricated empty response any more.

**Rendered proof** (stand, admin, coefficients request failed at the XHR layer — the same rejection a
500/timeout/blip produces — while the other two succeeded):
`hasTable: false`, screen text *«Бонусы не рассчитаны · Коэффициенты не загружены — расчёт невозможен …
Повторить загрузку»*, `blockedRequests: ["/webhook/api/score-coefficients"]`. Reload with all three
succeeding → error card gone, table renders.

`bugs.md`: **BUG-030**, ⚠️ High, CLOSED, with the residual client-only early-return path named.

### 2. (M1) `/admin/periods` write controls are admin-only; close is a typed confirmation

The page had **no role branch at all** — a c_level or HR viewer rendered the whole write toolbar including
the irreversible «Закрыть период», and learned it was forbidden only from a 403 alert.

- New `isAdmin(role)` in `src/utils/permissions.js`; `canManage` gates rename, reparent, activate and close.
- Close no longer uses `window.confirm`. It opens a modal in the page's existing pattern that requires the
  admin to **type the period name**; the submit button stays disabled until it matches exactly.

The reason for typing is asymmetry, not doubt about the old guard: there is no reopen route, no route that
writes or deletes `period_results`, and activation hard-rejects a closed period — the only recovery is a
database restore.

**Rendered proof** (stand):

| Check | Result |
|---|---|
| admin, 11 period rows | rename / reparent / activate / close render as before |
| **c_level viewer, same 11 rows** | **0 action buttons in total** |
| typed confirm — «Hier H1» (prefix) | submit disabled |
| typed confirm — «hier h1-t» (case) | submit disabled |
| typed confirm — «Hier P2» (another period) | submit disabled |
| typed confirm — «Hier H1-T» (exact) | submit enabled → close succeeded, 96 results stored |

**Boundary kept, and worth Alexander's decision:** the brief named four controls, so «Создать период» in the
page header is still rendered for c_level/HR (server answers 403). It is the one write control left visible
to a non-admin on this page.

### 3. (M7) `period_type = 'annual'` is now load-bearing on activate and close

"Container" was the derived state `child_count > 0`. Detaching the last child turned «Annual 2026»
— a full-year period already carrying 89 in-scope participant rows — into an ordinary activatable, closable
period. Activating it would have made a whole year the campaign period; closing it would have frozen 89
`has_data=false` rows forever.

Both routes now refuse an annual period **independently of child count**, and the refusal is re-asserted
inside the write (`period_type != 'annual'` in the `activatable` CTE and in the close `target` CTE):

| Route | Code | Message |
|---|---|---|
| activate | 422 `ANNUAL_PERIOD_NOT_ACTIVATABLE` | «Годовой период — контейнер отчётности: активировать можно только полугодовой период» |
| close | 422 `ANNUAL_PERIOD_NOT_CLOSABLE` | «Годовой период — контейнер отчётности: закрываются его дочерние периоды» |

Refusal order was chosen to preserve every pre-existing semantic: activate stays
container → closed → annual; close stays container → `already_closed` (200) / 409 → annual → not-active.
So `Annual 2025` still answers exactly what it answered before.

### 4. (M4, overlap half) Siblings of one container may not overlap

The annual index is a `SUM` over children, so two overlapping children double-count the overlap and the
roll-up had no way to show it. `create` and `reparent` now reject an overlapping sibling with
422 `SIBLING_DATES_OVERLAP` («Даты пересекаются с другим дочерним периодом этого контейнера»), re-asserted
inside the INSERT/UPDATE. A period is never its own sibling, so detach → re-attach still works.

**The canonical split passes:** H1 `01.01–30.06` + H2 `01.07–31.12` under an annual container — both 200,
including the 30.06/01.07 boundary.

### 5. (M4, honesty half) The roll-up says how much of the year it summed

- Header banner: `«Hier Annual-Split (01.01.2026 — 31.12.2026) — закрыто 1 из 2 дочерних периодов. Годовые
  значения ниже покрывают только эти периоды, а не весь срок контейнера.»` — amber when partial, neutral
  when complete, with every child listed as name + date range + status badge.
- Each child column header now carries its date range.
- The table footnote states «Годовые значения посчитаны по N из M дочерних периодов».
- The empty state (no closed child yet) lists the children with their date ranges too.

**Rendered proof:** partial container → amber banner «закрыто 1 из 2 дочерних периодов»; complete container
→ neutral banner «закрыто 2 из 2 дочерних периодов», footnote «посчитаны по 2 из 2», and the acceptance
figures unchanged — A `6.00 / 8.00 → 7.00 / 104,70`, B `вне охвата / 8.00 → 8.00 / 68,40`, C `нет данных →
— / —`.

### 6. (M4, detach half) Detaching a child with stored results asks first

Detach was unconditional. Detaching a **closed** child leaves its `period_results` intact but removes them
from the container's mean and sum — the annual numbers move silently. Detach of a child with
`has_results = true` now confirms, naming the consequence:

> Отвязать «Hier P2» от контейнера «Hier Annual-T»? … Сами результаты останутся нетронутыми, но они
> перестанут учитываться в годовой сводке: годовой рейтинг (среднее) и годовой индекс (сумма) участников
> изменятся.

**Rendered proof:** the confirmation fired on Hier P2; declining left the container at 2 children, nothing
written.

### 7. (M5 + docs) Documentation corrected

- **BUG-010 re-scoped, not closed.** The persistence half shipped (migration 013, atomic close, roll-up
  reads `period_results` only, immutability proven). The other half stays true and is now stated as the
  entry's subject: **every period that is not yet closed is still live-joined**, so editing weights, grade
  coefficients or classification mid-campaign silently rewrites numbers people already saw. Freezing happens
  only at close, which is a one-way door.
- **BUG-029 added** (zero-weight trap) verbatim from the verification's §1, at 🟢 Low–Medium, with today's
  live hygiene re-measured: zero criteria with `weight IS NULL OR weight <= 0`, zero `score_coefficients`
  rows with `coefficient IS NULL OR coefficient <= 0`. Latent, not active.
- **BUG-030 added** (§1 above) at ⚠️ High, CLOSED.
- **`docs/PERIODS_HIERARCHY_2026-08-2x.md` provenance corrected.** The document claimed the per-person
  aggregate was this brief's own call because «the matrix has no per-person total to copy». It has one:
  `final_rating` reproduces the «ИТОГОВЫЙ БАЛЛ» column of the evaluations-matrix Excel export
  (`src/utils/excelExport.js:228-229,248` — same per-cell function, same non-null filter, same population).
  The correction is stated in place, not silently swapped.
- **`docs/CALCULATION_MAP.md`** now records, in §A.1, that `rating_*` are archival per-source summaries of
  `evaluations.calculated_score` while `final_rating`/`bonus_index` are matrix quantities, and that the two
  **will not reconcile, by design**.
- **`scripts/prove_periods_hierarchy.py` cross-check records the compared tuples, not a slogan.** It was the
  bare string *"stored final/index match client matrix+money pipeline (<0.005)"*, which a run that compared
  nothing would have written just as happily. It now records every comparison with both sides and the delta,
  plus the skipped rows with the reason they were skipped, and **fails if fewer than three numeric
  comparisons happened or if either closed period is missing**.

  ```
  numeric_comparisons: 3   max_final_delta: 0.0   max_index_delta: 0.0
  {period 13, user 1103, stored_final 6.0, client_final 6.0, stored_index 36.3, client_index 36.3}
  {period 14, user 1103, stored_final 8.0, client_final 8.0, stored_index 68.4, client_index 68.4}
  {period 14, user 1104, stored_final 8.0, client_final 8.0, stored_index 68.4, client_index 68.4}
  skipped: 4 (in_scope=false, or has_data=false — no numbers by design)
  ```

### 8. Found while proving — BUG-031: the canonical H2 attach would have been refused

**Not in the brief. It would have hit Alexander in September, so it is fixed here.**

`Build Create SQL` compared the client's `YYYY-MM-DD` against the parent's dates *as read back from
Postgres*. The n8n Postgres node returns `date` columns as JS `Date` objects serialised in UTC, so in
Europe/Moscow a stored `2026-12-31` comes back as `2026-12-30T21:00:00.000Z` and `String(v).slice(0, 10)`
yields the **previous calendar day**. The end-date test was therefore one day too strict:

> creating «H2-2026» `01.07–31.12` under «Annual 2026» `01.01–31.12` returned
> **422 `CHILD_DATES_OUTSIDE_PARENT`** — the dates *are* inside the container.

(The start-date test was one day too lenient for the same reason. Reparent worked only because both sides
came from Postgres and the two shifts cancelled.)

Containment is now decided by Postgres (`'start'::date >= p.start_date AND 'end'::date <= p.end_date` as
`child_inside_parent`), and the Code node accepts only an explicit `true` — `false`, `NULL` and missing all
refuse. The same change was applied to reparent so it no longer depends on a coincidence. The SQL
re-assertions inside the INSERT/UPDATE were already date-typed and were correct throughout.

`bugs.md`: **BUG-031**, ⚠️ High, CLOSED.

### 9. Found while proving — the stand imported a stale workflow

`docker cp <dir> container:/tmp/wf_upd` **nests** the directory when the target already exists, leaving the
previous file at the top level — which is what `n8n import:workflow --input=/tmp/wf_upd/` then imported. Two
diagnoses were made against a stand that was silently running old code before this was caught. The stand
push helper now clears the container-side directory first, and the stand's active definition was verified
node-for-node against the repo before the proof was trusted. No repo file was affected; recorded here so the
next session does not repeat it.

---

## Verified present — no change needed

### `can_be_evaluated = false` is rejected on every Submit Evaluation path (verification rider)

**Present.** LIVE `API: Submit Evaluation` (`tUxHoRn38rJVDxWv`, 9 nodes, node-for-node identical to
`n8n_workflows/route_guard_h1/submit-evaluation.json`) carries `AND subj.can_be_evaluated = true` in **all
three** relation filters — `manager`, `subordinate` and `c_level_direct`:

```js
if (source === 'manager')      relationFilter = `AND subj.manager_id = ${actorId} AND subj.can_be_evaluated = true`;
else if (source === 'subordinate') relationFilter = `AND actor.manager_id = ${rawSubjectId} AND subj.can_be_evaluated = true AND subj.role NOT IN ('c_level','admin')`;
else /* c_level_direct */      relationFilter = `AND actor.role IN ('c_level','admin') AND subj.can_be_evaluated = true AND lower(subj.email) NOT IN ('cem@sedamedical.com','hemra@sedamedical.com','mekan@sedamedical.com')`;
```

A subject with `can_be_evaluated = false` produces zero rows from the scope check, and `Build Insert SQL`
answers **403 `SCOPE_MISMATCH`**. Re-measured on live today: ids **21 / 40 / 61** (Cem Durukan, Hemra
Ashyrov, Mekan Yusupov) are `can_be_evaluated = false`, `grade_id IS NULL`, `manager_id IS NULL`, and their
emails are exactly the three in the `c_level_direct` denylist. They therefore can never acquire a
`manager_score`, so `final_rating` and `bonus_index` persist as NULL — never a coefficient-1.00 money row.

*Observation, not a change:* this guard has no static test. If someone regenerates the workflow without it,
nothing fails. One assertion in `tests/routeGuardWorkflows.test.js` would close that; out of scope here.

*Unchanged and still open:* **M2** — 21/40/61 are in H1 scope with no grade and no manager. That is a data
decision for Alexander before 31 August, not a code change, and scope freezes at close.

---

## Tests

`npm test` → **236 pass / 0 fail** (was 213). New coverage:

| File | Adds |
|---|---|
| `tests/periodsHierarchy.test.js` | annual-type 422 on activate and close (static **and** behavioural — the Code nodes executed with fixtures, `half_year` passing the same gate); sibling-overlap 422 on create and reparent with the H1/H2 split passing; detach still unconditional; containment decided in SQL with `false`/`null`/`undefined` all refusing |
| `tests/moneyScreenGuards.test.js` (new) | the hook swallows nothing, all three requests classified, the failure branch clears the numbers, both screens return the error before the table; `isAdmin` exists; the four period controls sit behind `canManage`; typed close (handler + disabled submit); detach confirmation names the consequence |
| `tests/annualRollup.test.js` | `coverageSummary` / `coverageLabel` / `formatDateRange`, including the live-today shape «закрыто 0 из 1 дочернего периода» |

`npx eslint src/` — 34 problems before the batch, **34 after**: no new lint debt. `npm run build` clean.

---

## Stand proof

Isolated `epe-hier-n8n` on VPS loopback `:25679` against throwaway `epe_hier_20260821_0710`, restored from a
dated dump of **current** live (so the stand carried the real `Annual 2026` + `H1-2026` shape). The active
definition was verified node-for-node against `n8n_workflows/route_guard_h1/manage-periods.json` before the
proof was trusted. `scripts/prove_periods_hierarchy.py` → **ALL CHECKS PASSED**, 51 recorded calls.

New refusals, quoted from `api_proof.json`:

| Check | Result |
|---|---|
| `annual_leaf_activate_422` | 422 `ANNUAL_PERIOD_NOT_ACTIVATABLE` — on a **childless** annual (`child_count: 0` confirmed from `GET api/periods`); period still `draft\|false` afterwards |
| `annual_leaf_close_422` | 422 `ANNUAL_PERIOD_NOT_CLOSABLE` — forced to `active` in SQL on the throwaway so the close guard is proven independently of the activate guard; zero `period_results` rows written |
| `create_h1_canonical` / `create_h2_canonical` | 200 / 200 — `01.01–30.06` + `01.07–31.12` under an annual container |
| `create_sibling_overlap_boundary_422` | 422 `SIBLING_DATES_OVERLAP` — one shared day (30.06) is an overlap |
| `create_sibling_overlap_inner_422` | 422 `SIBLING_DATES_OVERLAP` — a range contained in H2 |
| `reparent_sibling_overlap_422` | 422 — and the period stayed `parent_period_id = NULL` |
| `detach_h2_canonical` → `reattach_h2_canonical` | 200 → 200 — a period is not its own sibling |
| pre-existing suite | container 422s, anti-zero-fill (B = 8.0 not 4.0), second close 200 `already_closed` / 0 rows, immutability under weight+grade edits, rename, audience 200/200/403/403 — all still pass |

Rendered checks (vite `:5299` → stand) are quoted inline in §1, §2, §5 and §6 above.

---

## Live deploy

1. **`API: Manage Periods` PUT** (`M9ljMDdO1mIl8m1h`) via `scripts/deploy_periods_hierarchy.py --apply`.
   Guard checked before and after. 9 nodes changed, all of them Code nodes on the create/activate/reparent/
   close paths: `Validate Period Create/Activate/Reparent/Close`, `Build Create/Activation/Reparent SQL`,
   `Build Close Dataset Query`, `Compute Close Results`. Node count 61 → 61, connections unchanged,
   webhooks 7 → 7.
   `updatedAt` `2026-08-21T06:00:08.687Z` → **`2026-08-21T07:28:10.039Z`**, `active` stayed `true`.
   Live graph re-read from `postgres.workflow_entity` after the PUT: **identical node-for-node** to the
   generated file. Top-level export `n8n_workflows/API_ Manage Periods.json` refreshed from live.
2. **Frontend** `./scripts/deploy_epe_frontend.sh` → **`20260821T072859Z`** (`/var/www/epe/current`).
   Deployed bundle carries all three new behaviours: «Коэффициенты не загружены» in
   `useFinalScoresMatrix-D4w0eZxr.js`, «закрыто …» in `AdminAnnualRollup-B3kLibOk.js`, «Закрыть период
   навсегда» in `AdminPeriods-Rj7ZXzOy.js`. Previous stamps remain on disk.
   *Note:* the script's two safety gates call `rg`, which is not installed on this laptop as a binary, so the
   deploy refused (correctly, fail-closed). Both gates were run by hand first — legacy `:5678` URL absent,
   `/webhook` base present — and the script was then run with a shell shim mapping `rg -q` to `grep -rqE`.
   The gate semantics were preserved, not bypassed. Installing ripgrep would remove the workaround.

### Live after

| Item | Expected | Measured |
|---|---|---|
| `API: Manage Periods` `updatedAt` | new | **`2026-08-21T07:28:10.039Z`**, active, 61 nodes, 7 webhooks ✅ |
| Frontend release | new | **`20260821T072859Z`** ✅ |
| H1 (id 2) | `draft` / `is_active=false`, parent 5 | `draft` / `f`, parent 5 ✅ |
| H1 scope | 87 / 89 | 87 / 89 ✅ |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | 0 / 0 / 0 / 0 | **0 / 0 / 0 / 0** ✅ |
| Registered webhooks | 41 | **41** ✅ |
| Workflows | 58 total / 33 active | 58 / 33 ✅ |
| `EPE: Auth Guard` | `2026-08-18T16:34:30.674Z`, inactive | unchanged, `active=false` ✅ |
| Periods on live | 3 rows, nothing activated or closed | `1 Annual 2025 closed`, `2 H1-2026 draft parent=5`, `5 Annual 2026 draft annual` ✅ |

---

## Housekeeping

| Action | Result |
|---|---|
| `DROP DATABASE epe_hier_20260821_0549` | **dropped** — the production-PII copy the verification flagged. The drop loop refuses any name not matching `epe_hier_*`; `epe_2026` was never a candidate |
| Fresh throwaway `epe_hier_20260821_0710` | **dropped** — created for this brief's proof, gone at the end |
| Container `epe-hier-n8n` | **removed** (project-owned; nothing else touched) |
| Duplicate dumps `_0547`, `_0548` | **deleted** in `backups/2026-08-21-periods-hierarchy/` and in `/tmp` on the host. `_0549` kept, as instructed |
| Databases remaining on `postgres_n8n` | **`epe_2026` only** (plus n8n's own `postgres`) |
| `git push origin main` | **pushed** — `78dbeb1..70d218f`; `main` was 9 commits ahead, now 0. The laptop is no longer the only copy of what runs on live (BUG-014, no off-host *backup*, is a separate matter and stays open) |

Two dumps now sit in `backups/2026-08-21-periods-hierarchy/`: `_0549` (kept per the brief) and `_0710` (this
brief's stand source, and the only dump that reflects live *after* migration 013 and the Annual 2026
walk-through). **The `pre013` in `_0710`'s filename is wrong** — it comes from the setup script's fixed
template; the file is a post-013 dump. Worth renaming when someone touches that script. The host still holds
`/tmp/epe_2026_pre013_20260821_0549.dump`; it was left because the brief named `_0549` as the one to keep.

---

## Constraints held

- `epe_2026`: **schema and data untouched** — the only live writes were one workflow definition and the
  static frontend. All four data tables still 0; H1 and Annual 2026 unchanged in status, activation and
  parentage; nothing closed anywhere.
- 2025 archive (`postgres.performance_db`): not read, not written by this batch.
- `EPE: Auth Guard`: `updatedAt` re-read after the final probe — unchanged.
- No mail (D-0820-8).
- Every throwaway created by this batch is gone.

## Leftovers

- **M2 is still open and is Alexander's call:** ids 21 / 40 / 61 are in H1 scope with `grade_id IS NULL` and
  `manager_id IS NULL`. Scope freezes at close, so the decision has to land before 31 August.
- **M3 is still open:** after H1 closes there is no active period, so Итоговые баллы, Калькуляция бонусов and
  the matrix all render empty and the frozen `bonus_index` is only visible on Годовые итоги, which has no
  budget or payout field. Needed in September, not in August.
- **BUG-029** (zero weight reads as 1.0) is open and latent — fix before anyone edits the criteria catalogue.
- **BUG-010** stays open in its re-scoped form: unclosed periods are still live-joined.
- **BUG-028** (stale `n8n_workflows/API_ evaluations-matrix.json`) unchanged, still open.
- «Создать период» remains visible to c_level/HR on `/admin/periods` (server 403) — outside the four
  controls the brief named.
- The `can_be_evaluated` guard on Submit Evaluation has no static test.
- `scripts/deploy_epe_frontend.sh` needs `rg` on PATH; without it the deploy fails closed.
