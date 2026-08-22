# Two-gate period lifecycle; coefficients live-until-close and admin-only

**Date:** 2026-08-22, 06:15–06:55 UTC · Brief: D-0822-1 + D-0822-2 · Fact base:
`docs/RECON_RECLASS_COEFF_2026-08-2x.md` (re-verified, not trusted). Reclassification semantics
(D-0822-3) are out of scope and unchanged.

**Outcome in one line.** A period now has two gates instead of one — activation opens a preparation
window in which employees see nothing and the admin can still finish the catalogue and the money
inputs, and a separate irreversible «Запустить оценку» opens the campaign. Weights, level
coefficients and grade coefficients stopped being frozen by activation and started being validated
instead; reading them became admin-only, which meant moving the weighted self-review computation
onto the server. Migration 014, fourteen live workflows, the frontend, one migration-safety fix and
two bugs closed.

**Live state after this brief.** All three periods are unchanged — `1 Annual 2025 closed`,
`2 H1-2026 draft`, `5 Annual 2026 draft`, every one `evaluation_started_at = NULL`. **Nothing was
started, activated or closed on live.** `evaluations` / `evaluation_scores` / `period_results` are
still 0 rows, and the criteria/coefficient/grade fingerprint is byte-identical before and after
(`59cc552a… / d2dcb678… / b121ee2d…`). The behaviour changes are deployed and inert until Alexander
lifts the pause.

---

## 1. What changed

### 1.1 The second gate (D-0822-1)

Migration `014_add_evaluation_start_gate.sql` adds `evaluation_periods.evaluation_started_at`
(timestamptz, NULL = not started) and `evaluation_started_by` (FK to `users`), plus
`chk_evaluation_periods_started_by_needs_started_at`. It is idempotent, writes no data rows, and
leaves every existing period NULL — no period is retroactively started.

The column is deliberately **not** tied to `status` by a CHECK. Close leaves the mark set (a closed
period was started; that is history), and the documented emergency stop sets an active period back
to `draft` by SQL. A status-linked CHECK would break both.

`API: Manage Periods` gains a seventh route, `POST /api/periods/start-evaluation`, admin-only,
built exactly like `activate` and `close`:

| Case | Answer |
|---|---|
| bad `period_id` | 422 `INVALID_PERIOD_ID` |
| unknown id | 404 `PERIOD_NOT_FOUND` |
| container (`child_count > 0`) | 422 `CONTAINER_NOT_STARTABLE` |
| `period_type='annual'` (even childless) | 422 `ANNUAL_PERIOD_NOT_STARTABLE` |
| closed | 422 `PERIOD_CLOSED` |
| not `active`/`is_active` | 422 `PERIOD_NOT_ACTIVE` |
| already started | **200 `already_started: true`**, zero state change |
| lost race on the gated UPDATE | 409 `START_CONFLICT` |

The write re-asserts every precondition inside the statement (`FOR UPDATE` target CTE), so a lost
race changes zero rows rather than starting a period that no longer qualifies. **No route clears
the mark** — a static test asserts the only assignment anywhere in the workflow is
`evaluation_started_at = now(),`. Recovery is SQL on the host, exactly like activation rollback.

`GET /api/periods` now returns `evaluation_started_at`, `evaluation_started_by` and
`evaluation_started`, and `/admin/periods` renders three distinguishable states:

| State | Row shows | Controls (admin only) |
|---|---|---|
| draft | «Неактивен» | Активировать |
| active, not started | «Активен · подготовка» + «Оценка не запущена — сотрудники не видят задач» | **Запустить оценку**, Закрыть период |
| active, started | «Идёт оценка» + the start timestamp | Закрыть период |
| closed | «Закрыт · результаты сохранены» | — |

### 1.2 The campaign surface keys on started, the reporting surface does not

| Route / surface | Keyed on |
|---|---|
| `POST api/submit-evaluation` | active **AND started** → else 409 `PERIOD_NOT_STARTED` |
| `POST api/self-review-submit` | active **AND started** → else 409 `PERIOD_NOT_STARTED` |
| `POST api/update-evaluation` | active **AND started** → else 409 `PERIOD_NOT_STARTED` (was: "not closed") |
| `POST api/admin/score-correction` | active **AND started** → else 409 `NO_ACTIVE_PERIOD` |
| `GET api/employees` (`campaign_active`, the three flags) | active **AND started** |
| `GET api/check-self-review` | active **AND started** |
| `GET api/check-evaluated` | active **AND started** |
| `GET api/get-my-manager` (`has_evaluated_manager`, `last_evaluation_score`) | active **AND started** |
| matrix, analytics, all-evaluations, details-by-user, manager-subordinates-matrix, HR status, admin-users-data, my-profile, evaluation-history/details | **active** — untouched |
| `POST admin/save-user` (`CLASSIFICATION_FROZEN`) | first submission in the active period — untouched |
| login, register, verify-invite, password reset, `EPE: Auth Guard` | not period-bound — untouched |

The submit routes answer with a **named** error rather than falling through to a scope error: the
period row is still selected in the preparation window, with `period_started` alongside it, so
"you are out of scope" and "the campaign has not started" stay distinguishable.

`GET api/employees` also gained `period_in_preparation`, so the client can tell "no period at all"
from "period open, evaluation not started". `actor_is_in_scope` is deliberately **not** gated: scope
is a fact about the period, not about the campaign, and the out-of-scope notice must keep working
during preparation.

Frontend consequence: `TaskStatusContext` exposes `campaignActive` / `periodInPreparation` and
returns all task flags false when the campaign is not running; the sidebar task panel and the
Welcome task cards disappear; `/self-review` and `/manager-evaluation` render a new
`CampaignNotStartedNotice` that says which of the two states applies instead of an empty form.

### 1.3 Freeze retuning (D-0822-2)

| Write | Before | After |
|---|---|---|
| `manage-criteria` save/delete | 409 `ACTIVE_PERIOD_EXISTS` on **activation** | 409 `EVALUATION_STARTED` only once the evaluation has **started**; editable in draft and in the preparation window |
| `POST api/score-coefficients` (weights + level coefficients) | 409 `ACTIVE_PERIOD_EXISTS` | **no period check at all**; validated instead |
| `POST update-admin-data` (grade coefficients) | 409 `ACTIVE_PERIOD_EXISTS` | **no period check at all**; validated instead |
| `admin/save-user` classification | 409 on first submission | unchanged |

Both freeze nodes and their dead period SELECTs were removed from the graphs, not merely bypassed
(`Validate No Active Period` / `Check Active Period` / `Check Freeze` / `Load Active Period` are
gone; static tests assert their absence).

Validation now rejects, with named 422s and before any SQL is built: weights and level coefficients
that are not finite and `> 0`; levels outside 1..10; missing coefficient maps; grade coefficients on
the same rule; and — new — `setting_key` / `setting_value` on the `update-admin-data` settings
branch, which until today interpolated `setting_value` straight into SQL with no validation of any
kind. That closes BUG-029 by making the misread value unwritable rather than by repairing the
readers.

**Why closed periods are immune — verified, not assumed.** Three checks:

1. `docs/RECON_RECLASS_COEFF_2026-08-2x.md` §2.4 enumerated every producer that writes
   `criteria.weight`, `grades.coefficient` or `score_coefficients` across all 33 active workflows:
   exactly three, all of them now unfrozen-but-validated. There is no fourth path.
2. The annual roll-up reads `period_results` **only** — no `evaluations`, `evaluation_scores`,
   `score_corrections`, `criteria` or `score_coefficients` (`HANDOVER` §3, re-read today in the
   generated `manage-periods.json`).
3. Proven behaviourally on the stand: after H1 was closed, `period_results.final_rating` /
   `bonus_index` for both fixture subjects were re-read and matched the pre-close matrix pipeline
   to 3 decimal places, and a second close changed nothing (identical fingerprint).

What is **not** immune, and was already known: an **open** period is live-joined, so editing a
weight mid-campaign does move that campaign's on-screen index. That is the point of D-0822-2 — it
is now allowed on purpose, until close freezes the numbers into `period_results`. The residue of
BUG-010 is exactly this live-joining, not editability (see §5).

### 1.4 Coefficient privacy

- `GET /api/score-coefficients` → `required_roles: ["admin"]`. It was authenticated-only, and
  **every employee fetched the full weight + level-coefficient table while filling in a
  self-review**.
- `GET /api/criteria` strips `weight` for every non-admin role. Closing one route without the other
  would have left the weights readable. The existing `c_level_only` level-text stripping (admin +
  c_level) is untouched and was re-verified live.
- Self-review: the client stopped fetching coefficients and stopped sending `weighted_score`. The
  server computes it at submit — formula #2 of `HANDOVER` §4, reproduced from the retired client
  implementation **including its guards** (`parseFloat(weight) || 1.0`, level clamp 0..10,
  `?? 1.0` for a missing level, weight 1.0 / coefficient 1.0 for an unknown criterion id) so the
  stored number is identical to what the browser used to compute. The one guard **not** reproduced
  is `grade_coefficient || 1.0`: the subject's real coefficient is read from the database, and its
  absence is 422 `NO_GRADE_COEFFICIENT`, never a silent 1.0. Unreachable today — the only live users
  without a grade are the read-only c_level trio, and the guard already refuses c_level on that
  route.
- Frontend: `/admin/scoring`, `/admin/score-calculator`, `/admin/final-scores` and
  `/admin/bonus-calculation` are behind a new admin-only `CoefficientRoute`, and the money-screen
  links are hidden from c_level in the sidebar. This removes dead ends rather than capability:
  recon §1.3 recorded that c_level and HR already got an error card on the money screens (grades are
  admin-only) and a silently empty grades table on `/admin/scoring`. That silent empty is also
  fixed — `useScoreCoefficients` moved to `Promise.allSettled` and `/admin/scoring` now returns an
  error card with retry instead of rendering a table it cannot save safely (the BUG-030 pattern).
- `src/utils/evaluationUtils.js` lost `calculateWeightedScore`: it had no callers left.

---

## 2. Acceptance — compared values

Every figure below is read from
`backups/2026-08-22-lifecycle-coeff/lifecycle_proof.json` (stand) and
`…/live_role_route_probe.json` (live). Both files record the compared values, and both proof scripts
fail on a vacuous run.

### 2.1 Live role × route probe

Live, `https://epe.sedamedical.com/webhook`, after deployment. Every POST in the matrix is
non-mutating by construction (empty body → 422 before any SQL; `manage-criteria action=get` is the
read branch), and the coefficient fingerprint is identical before and after the run. Six temporary
`auth_sessions` rows were created for the probe, marked with a `0822c0ef-` jti prefix and a
30-minute expiry, and deleted in a `finally` block — verified 0 remaining, `auth_sessions` 8 → 8, no
`token_version` touched, no real session read or removed.

| role (live id) | GET score-coefficients | POST score-coefficients | GET criteria | POST update-admin-data | POST manage-criteria (get) | POST start-evaluation |
|---|---|---|---|---|---|---|
| admin (2) | **200**, 8 criteria | 422 `INVALID_BODY` | 200, `weight` **present**, c_level texts present | 422 `INVALID_BODY` | 200, `evaluation_started=false` | 422 `PERIOD_NOT_ACTIVE` |
| c_level (18) | **403** `ROLE_FORBIDDEN` | 403 | 200, `weight` **absent**, c_level texts present | 403 | 403 | 403 `ROLE_FORBIDDEN` |
| c_level read-only (21) | **403** | 403 | 200, `weight` **absent**, c_level texts present | 403 | 403 | 403 |
| hr (52) | **403** | 403 | 200, `weight` **absent**, c_level texts absent | 403 | 403 | 403 |
| manager (1) | **403** | 403 | 200, `weight` **absent**, c_level texts absent | 403 | 403 | 403 |
| employee (3) | **403** | 403 | 200, `weight` **absent**, c_level texts absent | 403 | 403 | 403 |

The read-only c_level trio behaves exactly like any other c_level on every one of these routes, as
recon §1.2 predicted. The admin 422s are the new empty-body validation: they prove the request
reached the handler past the guard without writing anything. The 200 write path was proven on the
stand instead (§2.2), because proving it on live would mean writing to live.

`GET /api/employees` for every role returned `campaign_active=false`,
`period_in_preparation=false`, `actor_is_in_scope=true` — correct with no active period, and the
source of BUG-043 (§5).

### 2.2 Stand E2E, in order

Stand `epe-lifecycle-n8n` on VPS loopback `:25679`, throwaway DB `epe_lifecycle_20260822_0632`
restored from a dated dump of live, migration 014 + fixtures applied to the throwaway only, same
pinned image as live, guard imported under its live id and left inactive. Torn down at the end:
container removed, database dropped, `epe_2026` the only `epe_*` database left.

| step | check | result |
|---|---|---|
| **draft** | start H1 | 422 `PERIOD_NOT_ACTIVE` |
| | criteria save / weight save | 200 / 200 |
| **activate** | H1 state after activate | `status=active`, `is_active=true`, `evaluation_started=false`, `evaluation_started_at=null` |
| | criteria save / weight save / grade save | **200 / 200 / 200** |
| | employee `GET /api/employees` | `campaign_active=false`, `period_in_preparation=true`, `actor_is_in_scope=true`, **0 rows** |
| | manager `GET /api/employees` | `campaign_active=false`, **0 subordinate rows** |
| | `check-evaluated` / `has_evaluated_manager` | 0 rows / false |
| | self-review submit | **409 `PERIOD_NOT_STARTED`** |
| | manager submit | **409 `PERIOD_NOT_STARTED`** |
| | score-correction | **409 `NO_ACTIVE_PERIOD`** |
| **start** | start as employee | **403 `ROLE_FORBIDDEN`** |
| | start as admin | 200, `already_started=false`, `evaluation_started_at=2026-08-22 06:35:11.576642+00`, `evaluation_started_by=1201` |
| | criteria save / criteria delete | **409 `EVALUATION_STARTED`** / **409 `EVALUATION_STARTED`** |
| | weight save / grade save | **200 / 200** |
| | employee `GET /api/employees` | `campaign_active=true`, `period_in_preparation=false` |
| | manager `GET /api/employees` | subordinates `[1203, 1204]` |
| | self-review ×2, manager submit ×2, upward submit, update-evaluation, score-correction | 200 each |
| | `check-evaluated` / `check-self-review` | `[1203, 1204]` / `has_self_review=true` |
| **start again** | response | 200, `already_started=true`, «Оценка в этом периоде уже запущена» |
| | period row fingerprint before / after | `f680dde6c2e4a23578ae7b8bc8f5e53d` / `f680dde6c2e4a23578ae7b8bc8f5e53d` — **identical** |
| **refusals** | container (Annual 2026, 1 child) | 422 `CONTAINER_NOT_STARTABLE` |
| | childless annual (created id 6) | 422 `ANNUAL_PERIOD_NOT_STARTABLE` |
| | draft leaf (created id 7) | 422 `PERIOD_NOT_ACTIVE` |
| | unknown id 999999 | 404 `PERIOD_NOT_FOUND` |
| | `period_id: "not-a-number"` | 422 `INVALID_PERIOD_ID` |
| | closed H1 (after close) | 422 `PERIOD_CLOSED` |
| **close** | close of a **started** period | 200, `results_stored=96`, `in_scope=94`, `no_data=91` |
| | second close | 200 `already_closed=true`, results fingerprint `4ebed633…` → `4ebed633…` unchanged |
| | start mark after close | `2026-08-22 06:35:11.576642+00` — survives close unchanged |

**Close proof re-run** (persisted `period_results` vs an independent replay of the client matrix
pipeline over the pre-close matrix API):

| user | matrix pipeline final | persisted `final_rating` | matrix pipeline index | persisted `bonus_index` |
|---|---|---|---|---|
| 1203 | 8.0 | **8.0** | 40.32 | **40.32** |
| 1204 | 7.0 | **7.0** | 254.936 | **254.936** |

### 2.3 The read surface really keys on started — and reporting really does not

The cleanest available comparison: with the identical rows in place, clear `evaluation_started_at`
by SQL on the throwaway, re-read both surfaces, restore it.

| reading | mark set | mark cleared | restored |
|---|---|---|---|
| `employees.campaign_active` | true | **false** | true |
| `employees.period_in_preparation` | false | **true** | false |
| `employees.subordinate_rows` | 2 | **0** | 2 |
| `employees.evaluated_by_actor` (1203) | true | **null** | true |
| `check_self_review.has_self_review` | true | **false** | true |
| `check_evaluated.rows` | 2 | **0** | 2 |
| `get_my_manager.has_evaluated_manager` | true | **false** | true |
| `employees.actor_is_in_scope` | true | **true** | true |
| `matrix.campaign_active` | true | **true** | true |
| `matrix.period_id` | 2 | **2** | 2 |
| `matrix.employee_rows` | 94 | **94** | 94 |

The last four rows are the point: scope and the whole admin matrix are untouched by the gate.

### 2.4 Self-review: no coefficients out, real grade coefficient in

Network-level evidence that the employee never receives coefficients is the live probe (§2.1):
`GET /api/score-coefficients` → **403** for every non-admin role, and `GET /api/criteria` returns
no `weight` key at all. The client no longer requests either.

Stored `weighted_score` vs an independent recomputation, for two subjects with **different** grade
coefficients (0.60 vs 2.20), both submitted with a hostile `weighted_score: 999.99` in the payload:

| user | grade coef | grades | client sent | **stored** | independent recomputation | stored `calculated_score` |
|---|---|---|---|---|---|---|
| 1203 | **0.60** | `{3: 8, 4: 6, 12: 9}` | 999.99 | **7.04** | **7.04** | 7.67 |
| 1204 | **2.20** | `{3: 5, 4: 10, 12: 4}` | 999.99 | **21.84** | **21.84** | 6.33 |

The two differ, which is what proves the real coefficient was used rather than a 1.0 fallback; and
neither is 999.99, which is what proves the client value is ignored.

Separately, before any of this touched live, the generated server node was executed against the
**live** catalogue and compared to the retired client function over **285 cases** — 7 grade
coefficients × 40 pseudo-random score sets, plus unknown-criterion, single-criterion, all-ones,
all-tens and empty-catalogue edges. **0 mismatches.** The server reproduces formula #2 exactly,
including the fallback branches.

### 2.5 BUG-029

| write | request | response | stored before | stored after |
|---|---|---|---|---|
| `POST /api/score-coefficients` | criterion 12, `weight: 0` | 422 `INVALID_WEIGHT` | `1.00` | `1.00` |
| `POST /api/score-coefficients` | criterion 12, all ten level coefficients `0` | 422 `INVALID_COEFFICIENT` | level 5 `1.00` | level 5 `1.00` |
| `POST /update-admin-data` | grade `S1`, `coefficient: 0` | 422 `INVALID_GRADE_COEFFICIENT` | `0.60` | `0.60` |
| `POST /api/score-coefficients` | `weight: -1` | 422 `INVALID_WEIGHT` | — | — |
| `POST /api/score-coefficients` | level `11` supplied | 422 `INVALID_COEFFICIENT_LEVEL` | — | — |

### 2.6 Static

`npm test` — **263 passed, 0 failed** (was 236 before this brief; 27 new assertions, of which 21 are
the new `tests/evaluationStartGate.test.js` covering the start route, its preconditions, the
irreversibility of the mark, the campaign/reporting split, and the weighted-score computation
executed with fixture rows). Six pre-existing tests that asserted the **old** freeze semantics were
rewritten to assert the new ones; each rewrite is a behaviour change the brief asked for, and the
new assertion states it explicitly. `npm run build` clean. `npx eslint` on every changed file
reports the same pre-existing findings as before the brief and no new ones.

---

## 3. Deployment

Order: dump → migration → workflows → frontend.

| step | evidence |
|---|---|
| live dump before migration | `backups/2026-08-22-lifecycle-coeff/epe_2026_pre_mig014_20260822T063731Z.dump` (77 705 bytes), plus four dated stand dumps |
| migration 014 on live | applied 06:37 UTC; both columns present, both NULL on all three periods; `chk_evaluation_periods_started_by_needs_started_at` and the FK verified by `\d` |
| 14 workflows | PUT via `scripts/deploy_lifecycle_coeff.py --apply`; activation preserved on every one (`True → True`); live graph re-read and compared node-for-node after each PUT; `POST api/periods/start-evaluation` registered on `API: Manage Periods` |
| **Auth Guard** | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — checked before, after every single PUT, and at the end. **Unchanged.** The generated `auth_core/auth-guard.json` is byte-identical to HEAD |
| auth workflows | login `2026-08-19T08:40:17.190Z`, register `2026-08-20T15:46:43.694Z`, verify-invite `2026-08-20T15:47:40.923Z`, request/reset password `08-19`/`08-20` — all pre-date this deploy, none touched. Live `GET /api/verify-invite` → **200** |
| frontend | release `20260822T065024Z`; both deploy gates run by hand first (legacy `:5678` absent, `/webhook` present) because ripgrep is still missing on the laptop (BUG-040), then the script re-run under a `grep -rqE` shim that preserves gate semantics |
| stand teardown | container removed, `epe_lifecycle_*` dropped, `epe_2026` the only `epe_*` database remaining, no unrelated container touched |

---

## 4. One deployment defect found and fixed on the way

`scripts/deploy_lifecycle_coeff.py` refreshes the tracked top-level exports from live after a PUT
(BUG-028 hygiene). One of them — `n8n_workflows/API_ Manage Criteria Admin V7.json` — is also a
**generator input**: `build_route_guard_deferred.py` lifted the legacy `Prep SQL` node's JavaScript
out of it at build time. Refreshing it from live replaced the legacy graph with the generated one,
which has no `Prep SQL` node, and the generator could no longer run at all:

```
KeyError: "API_ Manage Criteria Admin V7.json: node 'Prep SQL' not found"
```

Caught immediately after the deploy, on the next regeneration. Fixed in two places: the legacy node
is now **inlined** in the builder (byte-identical output — verified by regenerating and diffing
against the deployed artefacts), and the deploy script gained
`assert_not_a_generator_input()`, which refuses to refresh any export that a builder reads through
`legacy_node` / `legacy_query`. Four other exports are still generator inputs
(`All-evaluation`, `evaluation-details-by-user`, `Analytics Dashboard`,
`Manager Subordinates Matrix`); none is in this brief's deploy set, and the guard now protects them.

No live behaviour was affected — the deployed graphs were already correct; only the ability to
regenerate them was lost, for about ten minutes.

---

## 5. Surfaced for decision

1. **A concurrent session edited this working tree during the run, and one of its edits reached
   live.** Between 11:37:20 and 11:38:17 local (06:37–06:38 UTC) another session modified
   `scripts/build_route_guard_workflows.py`, `tests/routeGuardWorkflows.test.js`, `bugs.md`,
   `src/utils/evaluationUtils.js` and `src/components/admin/ScoringCoefficientsTable.jsx` — inside
   the window in which this brief's deploy regenerates from the builders. The functional delta was
   one line: the weight rule became `weight < MIN_WEIGHT` with `MIN_WEIGHT = 0.1` instead of the
   brief's `weight <= 0`, and it went to live at 06:37:59 UTC. **Detected, and live was corrected
   at 06:49:44 UTC back to the brief's rule** (finite and `> 0`), keeping the other session's better
   error message, which names the right remedy. The other session's remaining changes were kept
   because they are consequences of this brief and not contrary to it: the now-dead
   `calculateWeightedScore` was deleted from `src/utils/evaluationUtils.js`, and the `/admin/scoring`
   formula caption was corrected from formula #2 to formula #3 (which is the number those
   coefficients actually feed). **If the 0.1 floor was deliberate, it is a one-line change plus a
   decision record — but it is a business constraint nobody has decided, and it forbids legitimate
   small weights.** Two agents on one working tree is the underlying hazard; nothing in the repo
   detects it.
2. **The start mark survives deactivation.** Activating another period sets the previous one to
   `is_active=false, status='draft'` but does not clear `evaluation_started_at`. Re-activating it
   therefore returns it to "started" immediately, with no second confirmation. Deliberate (the mark
   is irreversible by design) and unreachable in practice (activation refuses to deactivate a period
   that has evaluations), but it is a state nobody has been asked about.
3. **The emergency stop now stops the campaign too, and that is new.** Setting an active period back
   to `draft` by SQL already deactivated it; now it also makes every submit route answer
   `PERIOD_NOT_STARTED` and hides every task, because the campaign predicate requires `status='active'`
   as well as the mark. That is almost certainly what "emergency stop" should mean — worth confirming.
4. **`period_results` is now what makes closed periods immune, and it is the only thing.** With the
   coefficient freeze gone, a closed period's numbers are safe solely because the roll-up reads
   `period_results` and nothing else. Every money screen that is **not** the roll-up
   (Итоговые баллы, Калькуляция бонусов, the matrix) still live-joins and still renders nothing after
   close — BUG-033, and it is now load-bearing rather than merely inconvenient.
5. **BUG-041 was closed inside this brief rather than filed.** The brief rewrote the same `WHERE`
   clause the bug lives in; extending the inline re-assertion without gating the DELETE would have
   widened a destructive race. It is a code-level close: the race was not reproduced, and it is not
   reproducible without a concurrent write in a sub-second window.
6. **Two new bugs filed**: BUG-042 (`useScoreCalculation` still substitutes an empty coefficient set
   on failure — the last member of the BUG-030 family) and BUG-043 (with no active period,
   `/api/employees` names the annual **container** as the current period, because H1 and Annual 2026
   share a start date and `id DESC` decides; found by the live probe, pre-existing).
7. **Formula #3's denominator remains absent by design** (`HANDOVER` §4). Nothing in this brief
   touched any of the three formulas; the self-review server computation is formula #2 reproduced
   character-for-character from the client, guards included, and verified over 285 cases.

---

## Appendix — files

**Migration:** `migrations/014_add_evaluation_start_gate.sql`

**Generators:** `scripts/build_route_guard_workflows.py` (manage-periods start route, criteria weight
stripping, score-coefficients guard, save-score-coefficients validation, submit/self-review/update
gates, self-review weighted_score), `scripts/build_route_guard_deferred.py` (manage-criteria freeze,
update-admin-data rewrite, score-correction gate, `CRITERIA_PREP_JS` inlined),
`scripts/build_auth_workflows.py` (employees route)

**Deploy / proof:** `scripts/deploy_lifecycle_coeff.py`, `scripts/setup_lifecycle_throwaway.sh`,
`scripts/seed_lifecycle_throwaway.sql`, `scripts/prove_lifecycle_coeff.py`,
`scripts/probe_live_coeff_roles.py`

**Tests:** `tests/evaluationStartGate.test.js` (new, 21 assertions), `tests/routeGuardWorkflows.test.js`,
`tests/routeGuardDeferred.test.js`

**Frontend:** `src/App.jsx`, `src/components/Sidebar.jsx`,
`src/components/common/CampaignNotStartedNotice.jsx` (new), `src/components/common/index.js`,
`src/config/api.js`, `src/context/TaskStatusContext.jsx`, `src/hooks/useCriteria.js`,
`src/hooks/useScoreCoefficients.js`, `src/hooks/useSelfReview.js`, `src/pages/AdminPeriods.jsx`,
`src/pages/AdminScoring.jsx`, `src/pages/AdminSettings.jsx`, `src/pages/ManagerEvaluation.jsx`,
`src/pages/SelfReview.jsx`, `src/pages/Welcome.jsx`, `src/utils/evaluationUtils.js`,
`src/components/admin/ScoringCoefficientsTable.jsx`

**Artefacts (gitignored):** `backups/2026-08-22-lifecycle-coeff/lifecycle_proof.json`,
`…/live_role_route_probe.json`, `…/epe_2026_pre_mig014_20260822T063731Z.dump`
