# GATE — verification of Build 1 (two-gate lifecycle; coefficient freedom/privacy)

**The pre-migration dump of `epe_2026` exists and is valid** — item 2 is not a breach.
`backups/2026-08-22-lifecycle-coeff/epe_2026_pre_mig014_20260822T063731Z.dump`, 77 705 bytes,
timestamp 06:37:31 UTC, taken before migration 014 ran on live (~06:37:56 UTC).

**Date:** 2026-08-22 · Build under gate: `a6ef553` (report `docs/LIFECYCLE_COEFF_2026-08-2x.md`),
recon `f9758d3` (`docs/RECON_RECLASS_COEFF_2026-08-2x.md`), backup `9a78e6e`. **Read-only toward the
system.** No workflow PUT/activate/deactivate, no DB write, no deploy, no mail. Every live touch was a
`SELECT` on `epe_2026` / `postgres_n8n.public.workflow_entity` over the SSH tunnel, plus `git`,
`pg_restore -l`-equivalent extraction of local dumps, and reads of the committed proof artifacts.

**Verdict in one line.** Seven of the eight items **confirmed**; one sub-point of item 7 **refuted**
— HANDOVER §10's report index omits both new reports (filed BUG-044). The incident is fully closed:
the weight threshold is `> 0` (`weight <= 0`) identically in the generator, the tracked JSON and the
live definition; the parallel session's 0.1 floor survives nowhere (not committed, not live, not
tracked). Live state is byte-for-byte the pre-launch state: periods `closed/draft/draft`, all data
tables 0, every `evaluation_started_at` NULL, coefficient fingerprint unchanged, Auth Guard
`updatedAt=2026-08-18T16:34:30.674Z`.

Method note on independence: I re-derived the two self-review tuples from first principles (item 5),
counted the dump's COPY blocks with a stateful parser rather than a regex (item 2 — a regex first gave
a false "fixture data" alarm, corrected below), diffed live `workflow_entity` node-for-node against
the tracked artifacts, and read the guard-role literals straight from the live graphs. I did **not**
re-run the live role×route probe: minting a probe session inserts `auth_sessions` rows, which this
read-only gate forbids. Item 4's HTTP outcomes are therefore taken from the committed probe artifact
and corroborated by the live guard literals I read directly.

---

## Verdict per item

### 1. Incident closure — **CONFIRMED**

**Weight-validation threshold, three places side by side (all `weight <= 0`, i.e. the brief's `> 0`):**

| Place | Value | Evidence |
|---|---|---|
| Generator source | `if (!Number.isFinite(weight) \|\| weight <= 0)` | `scripts/build_route_guard_workflows.py:2284`, error `INVALID_WEIGHT` |
| Tracked workflow JSON | `weight <= 0` | `n8n_workflows/route_guard_h1/save-score-coefficients.json` **and** the top-level `n8n_workflows/API_ Save Score Coefficients.json`, node `Build Coefficients Update` |
| LIVE `workflow_entity` | `weight <= 0`, `MIN_WEIGHT` ×0 | `API: Save Score Coefficients` (`jAqkljoRb24jrcZx`, `updatedAt=2026-08-22T06:49:44.483Z`) — node-for-node identical to the tracked artifact |

No `MIN_WEIGHT`, no `weight < 0.1`, no `weight < MIN_WEIGHT` in the generator, the tracked JSON, or
the live definition. `git log -S MIN_WEIGHT --all` returns exactly one commit — `a6ef553` — which
*adds* a **negative** assertion (`tests/routeGuardWorkflows.test.js:861`:
`assert.equal(js.includes("MIN_WEIGHT"), false, "the rule is > 0, not an undecided numeric floor")`).
The 0.1 floor is dangling-gone: reverted on live at 06:49:44, never committed, and now guarded against
by a test.

**Fate of the parallel session's three edits:**

| Edit | Fate | Evidence |
|---|---|---|
| Formula caption in `ScoringCoefficientsTable.jsx` | **Swept into `a6ef553`** — caption changed from formula #2 to formula #3 (`Σ(…) × коэффициент_грейда`, no `/ Σ(весов)`), plus an explanatory paragraph that it is a bonus-share index, not a rating | `git show a6ef553 -- src/components/admin/ScoringCoefficientsTable.jsx` |
| Removal of `calculateWeightedScore` | **Swept into `a6ef553`** — function deleted from `src/utils/evaluationUtils.js` (no callers left after the self-review moved server-side) | `git show a6ef553 -- src/utils/evaluationUtils.js` |
| `MIN_WEIGHT` change (0.1 floor) | **Dangling-gone** — not committed, not on live, not in any tracked JSON | as above |

**`git status`:** clean. **Graph `375b8c1..HEAD`** (all author Aleksandr Petrosov, linear, no merges):

```
a6ef553  Split the campaign switch in two and make coefficients admin-only   (build: D-0822-1/2; closes BUG-029, BUG-041; files BUG-042, BUG-043)
f9758d3  Recon the freeze semantics from live: BUG-041 filed                  (recon; two brief expectations refuted)
9a78e6e  Back up the live database daily: BUG-032 closed                      (backup brief; n8n app schema included)
```

`origin/main == main == a6ef553` (`origin/HEAD -> origin/main`). Linear through f9758d3 and a6ef553.

### 2. Pre-migration dump — **CONFIRMED (present)**

`backups/2026-08-22-lifecycle-coeff/epe_2026_pre_mig014_20260822T063731Z.dump` — 77 705 bytes,
timestamp `063731Z` = 06:37:31 UTC, PostgreSQL custom dump v1.16. Restored locally to SQL and counted:
**89 users, 3 periods, 0 evaluations, 0 evaluation_scores, 0 period_results, 0 score_corrections,
178 participants, 8 auth_sessions, 8 criteria, 80 score_coefficients, 11 grades** — identical to the
current live empty state, and the `evaluation_periods` DDL has **no `evaluation_started_at` column**,
i.e. it predates migration 014. Migration 014 first appears on live at 06:37:56 UTC (the
`updatedAt` of the first workflow re-deployed after it), so the 06:37:31 dump precedes it. The four
sibling `epe_2026_pre014_20260822_06{17,23,28,32}.dump` files are the stand-setup dumps and carry the
same empty-live content (different md5 only because custom dumps embed a timestamp).

*Correction to my own first pass:* a fragile non-greedy regex initially reported "8 evaluations /
88 period_results" in this dump and I flagged it as fixture data. A stateful COPY-block parser shows
those tables are empty; the regex had spanned into an adjacent block. The dump is a genuine snapshot
of live's empty state, not the stand's fixtures.

### 3. Two-gate mechanics on live — **CONFIRMED**

- **Migration 014 present.** Live `evaluation_periods` carries `evaluation_started_at` /
  `evaluation_started_by`, `chk_evaluation_periods_started_by_needs_started_at`
  (`(evaluation_started_by IS NULL) OR (evaluation_started_at IS NOT NULL)`), and the FK to
  `users`. File `migrations/014_add_evaluation_start_gate.sql` present.
- **Periods** `1 Annual 2025 closed`, `2 H1-2026 draft` (parent 5), `5 Annual 2026 draft`;
  `is_active=false` on all three; **`evaluation_started_at` NULL on all three**.
- **Data tables 0** — `evaluations`/`evaluation_scores`/`score_corrections`/`period_results` all 0.
- **Status CHECK machinery intact** (live): `evaluation_periods_status_check`
  (`draft/active/closed`), `chk_evaluation_periods_active_status_consistent`
  (`(is_active=true) = (status='active')`); `period_results` anti-zero pair
  `period_results_no_data_is_empty` and `period_results_out_of_scope_no_data` present — matches
  HANDOVER §3 / the 2026-08-21 shape.
- **Close semantics untouched.** All 11 `*Close*` nodes in `API: Manage Periods` are byte-identical
  to `70d218f` (the 2026-08-21 POSTVERIFY_BATCH verified state); this build added 9 `*START*` nodes
  and changed only `Build Periods Query`. (The `Validate Period Close` / `Build Close Dataset Query` /
  `Compute Close Results` deltas versus the earlier `e5e313e` were the 2026-08-21 postverify batch,
  not this build.)
- **Auth Guard** `L0Zr7nVa8O5YWXd3`, live `updatedAt=2026-08-18T16:34:30.674+00`, `active=false` —
  and `n8n_workflows/auth_core/auth-guard.json` is unchanged at HEAD. Every campaign/coefficient
  route on live still executes `L0Zr7nVa8O5YWXd3`.

### 4. Role matrix, independently — **CONFIRMED**

Guard-role literals read directly from the live `Prepare Guard Input` nodes (`workflow_entity`):

| Route | `required_roles` (live) | Outcome |
|---|---|---|
| GET `/api/score-coefficients` | `["admin"]` | admin 200, everyone else 403 `ROLE_FORBIDDEN` |
| POST `/api/score-coefficients` | `["admin"]` | admin-only |
| GET `/api/criteria` | `[]` (auth-only) | `Format Response`: `canSeeWeight = role === 'admin'` → `delete criterion.weight` for all non-admins; `c_level_only` level texts deleted below admin/c_level |
| POST `/update-admin-data` | `["admin"]` | admin-only |
| POST `/manage-criteria` | `["admin"]` | admin-only |
| POST `/api/periods/start-evaluation` | `["admin"]` | admin-only |

The committed live probe (`live_role_route_probe.json`, run at deploy time) corroborates the HTTP
outcomes for all five roles **plus the read-only c_level (21)**: GET score-coefficients admin **200 /
c_level, c_level-readonly, hr, manager, employee 403**; GET criteria weight **present only for admin**;
`c_level_only` level texts present for admin+c_level, absent for hr/manager/employee; POST
score-coefficients / update-admin-data / manage-criteria / start-evaluation **403** for every
non-admin. **manage-criteria freeze in the current state:** the freeze predicate is now
`EVALUATION_STARTED` (×1 in the live graph; `ACTIVE_PERIOD_EXISTS` ×0), so with no started period,
writes are allowed — matching the brief. **Validation rejects weight 0 without writing:** the live
`Build Coefficients Update` returns 422 `INVALID_WEIGHT` before any SQL is built (and the admin
empty-body probes returned 422 `INVALID_BODY`, proving the request reaches the handler past the guard
without mutating). I did not re-execute the probe (it writes `auth_sessions`); the artifact stands and
the guard literals are read live.

### 5. Server-side W5, independently — **CONFIRMED; the 285-case claim RECONCILED (narrow but true)**

**Independent re-derivation** of both stand tuples, using HANDOVER §4 formula #2
`(Σ score·coef·weight / Σ weight) × grade_coefficient` with the **real** grade coefficient and the
live catalogue weights/level-coefficients (RECON appendix A.1–A.3):

| user | grade coef | grades | Σ score·coef·weight | Σ weight | ÷ | × coef | = | stored |
|---|---|---|---|---|---|---|---|---|
| 1203 | 0.60 | {3:8, 4:6, 12:9} | 8·1.60·3 + 6·1.10·1.5 + 9·1.80·1 = 64.5 | 5.5 | 11.7273 | ×0.60 | **7.036 → 7.04** | **7.04** ✓ |
| 1204 | 2.20 | {3:5, 4:10, 12:4} | 5·0.90·3 + 10·2.50·1.5 + 4·0.90·1 = 54.6 | 5.5 | 9.9273 | ×2.20 | **21.84** | **21.84** ✓ |

Both match to the penny. The plain ratings also check: AVG(8,6,9)=7.67 and AVG(5,10,4)=6.33 equal the
stored `calculated_score`.

**What the "285 comparisons, 0 discrepancies against the old client formula" actually compared.** The
"old client formula" is the pure function `evaluationUtils.calculateWeightedScore(scores, criteria,
gradeCoef)` — which *takes* `gradeCoef` as a parameter and multiplies by whatever it is given. Per the
build report §2.4, the harness ran the generated server node and this retired function over **7 grade
coefficients × 40 pseudo-random score sets + 5 edges = 285 cases**, feeding **both sides the same
grade coefficient**. So it is a **source-level equivalence test of two implementations of the same pure
function**, guards included — nothing more. It is silent, by construction, on parity with what
production self-reviews historically *stored*.

That is fully consistent with "the old client used grade coefficient 1.0", and does **not** refute it:

- In production the client always *called* `calculateWeightedScore` with `gradeCoef =
  user.grade_coefficient || 1.0`, and `grade_coefficient` is stripped from `/api/employees` for
  non-admins (RECON §1.4), so employees computed at **1.0**. The only self-reviewers with an
  un-stripped coefficient are admin/c_level, whose grades all carry coefficient **1.00** anyway
  (RECON A.3). Effective production gradeCoef was 1.0 for everyone.
- The server now uses the subject's **real** coefficient (0.30–3.00 range), refusing rather than
  defaulting (`NO_GRADE_COEFFICIENT`, the one guard deliberately *not* reproduced — build §1.4).
- The harness holds the grade coefficient **identical on both sides**, so it cannot and does not
  detect this one intended divergence. The divergence is proven elsewhere — the 0.60-vs-2.20 stand
  test yields two *different* stored values (7.04 ≠ 21.84), which only happens if the real coefficient
  is used, and neither equals the hostile client-sent 999.99.

**Reconciled:** the "0 discrepancies" claim is true and means "the server reproduces the retired
function's arithmetic and fallback guards exactly." It is not a claim of parity with historical stored
numbers, and read that way it does not conflict with the old client's effective 1.0. The server node
implementation was inspected directly (`build_route_guard_workflows.py`, "computed HERE, never taken
from the client") and matches formula #2, including `parseFloat(weight)||1.0`, the 0..10 level clamp,
`?? 1.0` for a missing level, and weight/coef 1.0 for an unknown criterion id.

### 6. Campaign-surface gating regression — **CONFIRMED**

Predicate extracted from the live definitions:

| Surface | Keyed on | Live evidence |
|---|---|---|
| `submit-evaluation`, `self-review-submit`, `update-evaluation` | active **AND** started | each carries `evaluation_started_at IS NOT NULL` + `status='active'`/`is_active=true`; 409 `PERIOD_NOT_STARTED` |
| `admin/score-correction` | active **AND** started | `evaluation_started_at IS NOT NULL` + active; 409 `NO_ACTIVE_PERIOD` |
| `/api/employees` flags, `check-self-review`, `check-evaluated`, `get-my-manager` | active **AND** started | each references `evaluation_started_at IS NOT NULL` |
| matrix, analytics, all-evaluations, details-by-user, manager-subordinates-matrix, HR status, admin-users-data, my-profile, evaluation-history | **active** only | **zero** `evaluation_started` references in all nine |

**`can_be_evaluated` rejection for the trio unchanged.** `API: Submit Evaluation` retains all three
relation filters with `AND subj.can_be_evaluated = true` and the `c_level_direct` email denylist —
byte-identical to the pre-build `f9758d3` (3 filters + denylist on both). The trio (21/40/61) can never
acquire a `manager_score`. (Self-review and update-evaluation carry no `can_be_evaluated` clause, as
before — those are self / own-row paths, not downward-subject paths; that is unchanged and correct.)

### 7. Docs and process — **CONFIRMED except the §10 report list (REFUTED)**

- **DECISIONS.md D-0822-1/2** — present (both). Expected gap holds: the build report body does not
  itself point at DECISIONS, but the decisions are recorded. **Confirmed.**
- **HANDOVER §6.11 corrected** — yes; now reads "decided 2026-08-22 (D-0822-1 / D-0822-2), and the
  earlier premise here was wrong", with the split-switch semantics. **Confirmed.**
- **HANDOVER §10 report list includes both new reports** — **REFUTED.** The §10 "Reports, in order"
  list (line 339) still ends at `DOCS_HYGIENE_2026-08-21.md`; neither `LIFECYCLE_COEFF_2026-08-2x.md`
  nor `RECON_RECLASS_COEFF_2026-08-2x.md` is in it, though both files exist and are cited in §3/§6.11.
  The §10 *footer* was updated (`bugs.md` 20/23, `migrations/001…014`) but the report list was not.
  **Filed BUG-044.**
- **PROGRESS.md entries for recon and build** — both present (the recon entry and the
  "Two-gate period lifecycle…" build entry). **Confirmed.**
- **bugs.md rows:** BUG-029 **closed with evidence** (422 table + static assertions + live
  `updatedAt`s); BUG-041 present and **closed** (removed_scores now gated on `updated_header`);
  BUG-042 and BUG-043 present (open). **Statistics consistent** *before this gate*: 20 open / 23
  closed, 43 `### BUG-` headings, status lines 20 `🔴 OPEN` (19 + 1 re-scoped) / 23 `🟢 CLOSED`.
  **Confirmed.** (This gate adds BUG-044 → 21 open / 23 closed; the bugs.md statistics cell is updated
  to match. See "Consequence" below.)
- **Working tree clean; origin/main linear through f9758d3 and a6ef553** — **Confirmed** (see item 1).

### 8. Deploy-script guard — **CONFIRMED**

`scripts/deploy_lifecycle_coeff.py` defines `assert_not_a_generator_input(export_name)` (line 91),
**called before refreshing each export** (line 191). It scans `build_route_guard_deferred.py`,
`build_route_guard_workflows.py` and `build_auth_workflows.py` for `legacy_node(` / `legacy_query(`
markers within 400 chars of the export name and raises `SystemExit("Refusing to refresh … reads it as
a generator input. Inline the node into the builder first.")`. The guard exists as committed.

---

## Consequence of this gate on the counts

Adding **BUG-044** makes the true tally **21 open / 23 closed**. The `bugs.md` statistics cell is
updated to `🔴 Open | 21` accordingly. HANDOVER §10's parenthetical "**20 open / 23 closed**" is
therefore now stale by one — **left unchanged on purpose**, because the brief scopes commits to "the
report and any bugs.md additions — nothing else". It should be reconciled at the next HANDOVER touch
(alongside the BUG-044 report-list fix).

## NOT CHECKED (out of read-only scope, or not required by the brief)

- **Live role×route probe not re-executed.** Minting a probe session writes `auth_sessions`; forbidden
  here. Item 4 rests on the live guard literals (read) + the committed probe artifact. The
  200-status *write* paths (an actual coefficient save) were never in scope — proving them means
  writing to live.
- **The 285-case comparison harness was not re-run.** It is not committed (a build-time artifact); I
  reconstructed *what it compared* from the report and the committed server node + the 2-case
  behavioral test (`tests/evaluationStartGate.test.js`), and re-derived the two live tuples by hand.
- **`npm test` / `npm run build` / `eslint` not re-run.** The build reports 263 passing; not
  re-executed here (no behaviour was changed by this gate, and the brief is verification, not CI).
- **BUG-041 race not reproduced.** It is a static SQL property and reproducing it needs a concurrent
  sub-second write — impossible read-only and pointless with `evaluation_scores` empty.
- **Stand E2E not reproduced.** The stand `epe-lifecycle-n8n` was torn down at build time; rebuilding
  it is a write-heavy operation outside this gate. The stand results were checked for internal
  consistency against the committed `lifecycle_proof.json` values (re-derived tuples match).
- **Off-host backup / `N8N_ENCRYPTION_KEY` (BUG-014)** — unchanged and out of scope.
- **Frontend render behaviour** (`CampaignNotStartedNotice`, three period-state rows, sidebar gating)
  — verified only as source/diff, not rendered; the app is paused and there is nothing to drive.

## New bugs filed

- **BUG-044** (Low) — HANDOVER §10 report index omits `LIFECYCLE_COEFF_2026-08-2x.md` and
  `RECON_RECLASS_COEFF_2026-08-2x.md`, though both files exist and are cited elsewhere in HANDOVER.
  Documentation-integrity only; one-line fix deferred because this gate edits nothing but its own
  report and `bugs.md`.

No other new findings. Every other brief expectation held.
