# Bug Tracker

## Statistics
| Status | Count |
|--------|-------|
| 🔴 Open | 11 |
| 🟡 In Progress | 0 |
| 🟢 Closed | 20 |

---

## 🚨 Critical

### BUG-002: Admin write webhooks have no JWT/secret check
- Status: 🟢 CLOSED
- Severity: 🚨 Critical
- Location: live `postgres_n8n.public.workflow_entity` (verified 2026-08-12). Routes: `api/admin/clear-test-evaluations`, `admin/save-user`, `manage-criteria`, `update-admin-data`, `api/periods/create`, `api/periods/activate`. Same pattern on admin GET: `api/admin/all-evaluations`, `api/admin/evaluations-matrix`, `api/admin-users-data`.
- Description: Webhook `authentication` is null. First node after POST on the destructive route is a Postgres `DELETE` of all `performance_db.evaluations` and `score_corrections`. Other admin writes go webhook → Code/SQL with no token, header, or secret IF.
- Why it matters: Anyone who can reach `:5678` can wipe last year's evaluations, create users, change criteria, or activate periods. Frontend JWT, if any, is not checked in these workflows.
- How to fix: Do not call the endpoints to test. Add a server-side check (n8n webhook header auth or a JWT verify node) before any SQL, then deactivate or gate the destructive route. Decision required before changing live workflows — they share the n8n process with foreign tenants.
- Mitigation (2026-08-12 21:32 UTC): all 35 active `API:*` workflows deactivated via n8n API; `webhook_entity` empty. Bug remains OPEN because the workflow graphs still have no auth — restoring them re-opens the hole. See `docs/n8n_deactivation_2026-08-13.md`.
- Progress (2026-08-18): reusable live-identity guard is proven on `GET api/employees`; all other protected routes remain for the next pass. All 37 unarchived `API:*` workflows remain inactive.
- Progress (2026-08-19): D1–D8 authorization policy is approved; guarded route replacement and destructive-workflow deletion are in progress under `docs/briefs/ROUTE_GUARD_H1_2026-08-19.md`.
- Fix (2026-08-19): all approved campaign/admin/period workflows call `EPE: Auth Guard`; actor identity comes from the live session; ownership and role/capability failures were runtime-proven. `API: Admin Clear Test Evaluations` was deleted.
- Verification: 19 protected method routes rejected missing, forged, and expired tokens; role/capability/ownership matrices passed; the final guard graph hash remained unchanged. See `docs/ROUTE_GUARD_H1_2026-08-19.md`.

### BUG-003: Public authentication transport has no TLS
- Status: 🟢 CLOSED
- Severity: 🚨 Critical
- Location: frontend API base and n8n webhook endpoint at `http://92.51.45.147:5678`.
- Description: Passwords, bearer tokens, invite tokens, and reset tokens would cross the network in plaintext if auth workflows were activated on the current public endpoint.
- Why it matters: A network observer can take over accounts even though passwords are hashed and JWT signatures are correct.
- Fix (2026-08-19): Caddy serves the portal and `/webhook/*` at `https://epe.sedamedical.com`; `EPE_FRONTEND_URL` uses the same origin and direct public port 5678 is blocked.
- Verification: valid Let's Encrypt certificate, HTTP-to-HTTPS redirect, HTTPS login/guard acceptance, HTTPS reset email delivery, and external 5678 filtering. See `docs/TLS_CUTOVER_2026-08-19.md`.

---

## ⚠️ High

### BUG-004: Submit Evaluation conflict target does not match production
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `n8n_workflows/API_ Submit Evaluation.json`, node `Insert Evaluation`; live `epe_2026` index `idx_evaluations_unique_non_self_period`.
- Description: the workflow uses `ON CONFLICT (subject_id, evaluator_id, evaluation_source)`, while production uniquely indexes `(subject_id, evaluator_id, evaluation_source, period_id)`.
- Why it matters: every otherwise valid H1 submission reaches a PostgreSQL error instead of creating an evaluation.
- Fix: keep period-aware uniqueness, reject duplicate submit explicitly, and use the guarded update route for changes.
- Verification (2026-08-19): migration 012 was rehearsed and applied twice idempotently; valid manager/upward submissions stored actor identity and period 2, duplicate submit returned 409, and all rows were removed after acceptance.

### BUG-005: Employee classification editor writes the wrong source of truth
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `n8n_workflows/API_ Admin Save User (GUI Mode).json`; `src/components/admin/UserModal.jsx`; manager evaluation paths use `users.is_project_participant`.
- Description: the employees table writes only `work_category`, while project criteria and bonus-index inputs are selected by `is_project_participant`.
- Why it matters: Alexander can see a saved Project/General edit that does not change the criteria or bonus allocation.
- Fix: make `work_category` canonical, synchronize `is_project_participant` atomically, and freeze classification after the first active-period evaluation.
- Verification (2026-08-19): save-user returns both synchronized fields; a classification change after the first active-period submission returned 409 and left the row unchanged. Final live mismatch count: 0.

### BUG-006: Axios prepends `/webhook` twice
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `src/api/client.js`.
- Description: endpoint constants already include `API_BASE_URL`, while the shared Axios instance also configured `baseURL`, producing `/webhook/webhook/api/*`.
- Why it matters: authenticated pages loaded their shell but failed every protected API request with 404.
- Fix (2026-08-19): endpoint constants remain authoritative; the duplicate Axios `baseURL` was removed and frontend release `20260819T094626Z` deployed.
- Verification: fresh bundle `index-CAUq0inK.js` issued only `/webhook/api/*`; real employee self/upward and manager/downward UI submissions completed without a 401 loop.

### BUG-010: Live-joined screens rewrite history for every period that is not closed
- Status: 🔴 OPEN (re-scoped 2026-08-21 — the persistence half shipped)
- Severity: ⚠️ High
- Location: `API: evaluations-matrix`, `API: Get Score Coefficients`, `src/hooks/useFinalScoresMatrix.js`, `src/pages/BonusCalculation.jsx`; HANDOVER §4 item 2 / §6.13; D-0819-1.
- Description (original): the bonus index and per-source ratings existed only on screen; closing a period stored nothing to sum later. December showed this — the index was unrecoverable once weights and coefficients changed.
- Shipped (2026-08-21): `POST api/periods/close` computes and stores `performance_db.period_results` (migration 013) in one atomic statement, and the annual roll-up reads that table only — no live join. Proven immutable: editing `criteria.weight` and `grades.coefficient` after close left both the stored rows and the roll-up byte-identical. H1 + H2 → annual aggregation is therefore possible. See `docs/PERIODS_HIERARCHY_2026-08-2x.md`.
- Still open — the other half: **every period that is not yet closed is still live-joined.** Итоговые баллы, Калькуляция бонусов and the evaluations matrix recompute from `criteria.weight`, `grades.coefficient` and the user's classification on each render, so editing any of those mid-campaign silently rewrites the numbers people already saw. Freezing only happens at close, which is a one-way door: before it, nothing is stable; after it, nothing is recomputable.
- Why it matters: between 31 August and the September close, H1's numbers are only as stable as the catalogue nobody promised not to edit.
- Fix: version the scoring inputs (weights, coefficients, grade coefficients) per period, or freeze the catalogue for the duration of an active campaign and refuse edits with a 409.
- H1 impact: none on 31 Aug. Operational discipline during the campaign; the code fix is post-H1.
- Related: [BUG-029] (a zero weight is read as 1.0), [BUG-030] (a failed coefficients fetch used to un-weight the screen silently).

---

## 📌 Medium

### BUG-009: Employee profile and history still have no period filter
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `n8n_workflows/route_guard_h1/my-profile.json`, `evaluation-history.json`.
- Description: Both JOIN `evaluation_periods` for the name only. They do not restrict rows to the active period. `check-self-review`, `check-evaluated`, and `get-my-manager` already bind to `is_active AND status='active'` — `docs/REPORTING_SURFACE_2026-08-2x.md` listed those three as still unbound; that is false in the live generator JSON.
- Why it matters: harmless while `epe_2026` has one campaign period. After H2 exists, profile/history will mix cycles.
- Fix: bind both queries the same way check-* already do. Schedule with persist-period-results after launch.

### BUG-012: `/team` calls an admin-only API
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `src/pages/TeamView.jsx` → `useUsers` → `GET /api/admin-users-data`; route is `ManagerRoute`.
- Description: The page is shown to managers. The API guard is admin-only. Managers get an empty/error list. Pre-existing; reporting-surface brief hid dossier buttons but did not change the list endpoint.
- Why it matters: the “Список команды” item in the sidebar does not work for a manager.
- Fix: either point the list at a manager-scoped employees read, or hide `/team` from managers until that exists.
- H1 impact: managers use `/dashboard` for campaign tasks. `/team` is the leftover.

### BUG-016: npm production/dev advisories
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `npm audit` 2026-08-20.
- Description: 15 advisories (11 high, 3 moderate, 1 low). Production-only (`--omit=dev`): 5 (4 high, 1 moderate).
- Why it matters: known high-severity frontend dependencies. Not a campaign blocker.
- Fix: after H1 launch, upgrade in a dedicated pass and rebuild.

---

## 📝 Low

### BUG-008: Invite reuse is global rather than creator-scoped
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: guarded `API: Create Invite`, existing-token lookup.
- Description: an unused valid invite is reused without filtering `created_by`. With multiple admins, Admin B can receive a token whose audit row names Admin A.
- Why it matters: registration remains authorized, but the creator audit trail becomes misleading.
- Fix: either define invites as an intentional shared pool and rename the audit field, or filter reusable tokens by `created_by = guard.identity.id`.
- H1 impact: none while Alexander is the only admin. Launch-prep recommendation: keep the shared single invite for the waves; per-wave tokens are not worth it now.

### BUG-011: Logout and 401 do not sweep evaluation drafts
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/utils/evaluationDrafts.js`; `src/context/UserContext.jsx` `logout`; `src/pages/Login.jsx`.
- Description: Draft keys `epe:evaluation-draft:{evaluator}:{subject}` survive logout and 401. They expire after 7 days or on submit. A second account on the same browser does not see the previous sliders (keys include user id). DevTools on a shared computer can still read unpublished scores.
- Why it matters: shared-computer leftover. Decided: no logout sweep for H1 (D-0820-15).
- Fix: if wanted later, sweep `epe:evaluation-draft:*` at login for keys that are not the current user, or on logout for all three forms.

### BUG-013: Typed `/admin` is still `AdminRoute` for HR
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/App.jsx` path `/admin` → `AdminRoute` → `AdminSettings`; `canAccessAdminPanel` includes `hr`.
- Description: Sidebar hides «Критерии» from HR. A typed URL opens the criteria catalogue shell. The API is admin-only (403). Company-wide numbers are not returned.
- Why it matters: HR sees a frozen/error catalogue, not results. Reporting-surface brief left this on purpose.
- Fix: wrap `/admin` in an admin-only route, or keep as-is.

### BUG-014: No off-host backup copy
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: host `/root/backups/epe`; daily on-host dump, 14-day retention.
- Description: Weekly off-host copy (Timeweb S3, write-only key) was not implemented. Outstanding since 13 Aug.
- Why it matters: a host disk failure loses the only copies. Restore-verified on-host dumps exist.
- Fix: pick a target and a write-only key. Alexander said “later”.

### BUG-015: Stale Keychain admin password
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: macOS Keychain item `EPE auth test password reset 2026-08-18`.
- Description: That password returns 401 on live login (`Неверный email или пароль`). Browser proofs used a minted admin JWT. Alexander’s real session was kept.
- Why it matters: the stored item is wrong; failed attempts can lock the only admin if retried. Not a campaign-code defect.
- Fix: Alexander changes the admin password and updates or deletes the Keychain item.

---

## ✅ Closed

### BUG-007: Out-of-scope employees remain in manager task lists
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: Get Employees (Smart Role Based)`, `API: HR Evaluation Status`, `TaskStatusContext`, and manager task-status calculations.
- Description: subordinate lists and completion counts used the organisation tree without joining active-period participation. Aysoltan Esenova was shown to her manager even though H1 marks her out of scope.
- Fix: campaign lists and HR/task denominators join `evaluation_period_participants.is_in_scope` for the period that is both `is_active` and `status='active'`. No active period → empty campaign list, `campaign_active=false`. Organisation tree outside campaign views is unchanged.
- Verification (2026-08-19): with H1 active, Akmyrat's list was 5 names and Esenova absent; Alyona's list was 1 name and Balova absent; periods GET showed `in_scope_count=87` / `participant_count=89`; HR status omitted both excluded people and counted Akmyrat's in-scope subordinates as 5. See `docs/LAUNCH_PREP_2026-08-19.md`.

### BUG-001: Hard-coded n8n API credential
- Status: 🟢 CLOSED
- Severity: 🚨 Critical
- File: `dump_n8n.py`
- Description: The workflow export utility contained an n8n API key in source code.
- Fix: Removed the key and required `N8N_URL` and `N8N_API_KEY` through environment variables.
- Verification: Confirmed the script exits before network access when credentials are absent.

### BUG-017: verify-invite 30 / 5 min / IP would block the all-hands email
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: Verify Invite` Format Response.
- Description: Live limit was still 30 / 5 min / IP. One office NAT opening the shared link would hit RATE_LIMITED.
- Fix: raised to 600 / 5 min / IP. Per-email 60 s resend cooldown unchanged.
- Verification (2026-08-19): 40 GETs from one IP, none RATE_LIMITED. Live `updatedAt=2026-08-19T13:46:13.004Z`, `throttleCount > 600`. See `docs/THROTTLE_RAISE_2026-08-20.md`.

### BUG-018: Shared invite burned on first register; UUID-only token validator
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: Register` load JOIN and persist SQL; Validate Registration regex.
- Description: First successful register set `invite_tokens.is_used=true`. Token id=4 is 43-char base64url and failed `[a-f0-9-]{16,128}`.
- Fix: register no longer writes `is_used`; validator `[A-Za-z0-9_-]{16,128}`.
- Verification: two sequential registers on id=4; invite stayed unused; hashes rolled back. Live `updatedAt=2026-08-19T13:56:52.642Z`. See `docs/SHARED_INVITE_2026-08-20.md`.

### BUG-019: Self-review and upward forms had no draft
- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `SelfReviewModal` / `ManagerEvaluation.jsx` vs `EvaluationModal`.
- Description: Dress rehearsal: refresh mid-form lost sliders on self-review and upward. Only the manager modal wrote `epe:evaluation-draft:*`.
- Fix: same helper on all three forms. Frontend `20260820T065435Z`.
- Verification: Alina self `3:3` and upward `3:1` survived refresh and 401-relogin; cleared on submit. See `docs/DRAFTS_UX_2026-08-2x.md`.

### BUG-020: Matrix mixed periods; `manager_score` by evaluator role
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: evaluations-matrix`; `src/utils/matrixUtils.js`.
- Description: No `period_id` predicate; `manager_score` could pick an upward row from a manager-role evaluator. Stars on invalid subjects; second C-level save was 409 behind an edit label.
- Fix: one named period; `manager_score` by `evaluation_source='manager'`; stars only on in-scope evaluable non-C-level subjects; «Изменить» uses update-evaluation.
- Verification: H1 draft → empty-state; H1 active → 88 rows; upward did not fill manager_score. See `docs/MATRIX_CALIBRATION_FIX_2026-08-2x.md`.

### BUG-021: Score-correction inactive and would write a draft period
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: Score Correction`.
- Description: Route inactive (POST 404). Period subquery was `status <> 'closed' ORDER BY id DESC` — a draft would have been writable.
- Fix: activated; period = `is_active AND status='active'` only; else 409 `NO_ACTIVE_PERIOD`.
- Verification: draft POST 409; active POST 200 `period_id=2`. Live `updatedAt=2026-08-19T20:34:42.909Z`, active. See `docs/MATRIX_CALIBRATION_FIX_2026-08-2x.md`.

### BUG-022: Reporting unbound; `detail_type` ignored; HR saw company-wide APIs
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: all-evaluations, analytics, details-by-user, manager-subordinates-matrix; `App.jsx` routing.
- Description: No period bind (mixed cycles); all-evaluations duplicated Alina via the upward join; `detail_type` accepted and ignored; HR 200 on company-wide reads.
- Fix: period bind + empty-state; `DISTINCT ON` upward join; `detail_type` enforced; HR 403 on those five APIs; `ReportingRoute` on the three URLs.
- Verification: H1 draft empty-state; H1 active Alina ×1; unknown `detail_type` 422; HR 403. See `docs/REPORTING_SURFACE_2026-08-2x.md`.

### BUG-024: Manager form showed the manager's own self-review as the subordinate's
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: Check Self Review` (`QRkUvs24DkcC3WBW`); `EvaluationModal` / `getSelfComment`.
- Description: The 2026-08-19 route-guard rewrite replaced the `user_id` subject selector with `WHERE e.subject_id = ${actorId}`, so the manager evaluation form displayed the manager's own self-review labelled as the subordinate's; `getSelfComment` returned `general_comment` for every criterion.
- Fix (2026-08-20): gated `selected_subject` CTE — `user_id` honored for self, admin/c_level, or a direct report (`target.manager_id = actorId`); anything else silently falls back to the actor's own row. Frontend loads `?user_id={employee.id}` and shows «Самооценка ещё не отправлена» when absent.
- Verification: throwaway-stand suite (`api_proof.json`) + preflight re-read of the live CTE 2026-08-20 evening (`updatedAt=2026-08-20T15:46:51.305Z`). See `docs/PRELAUNCH_FIXES_2026-08-2x.md`, `docs/PREFLIGHT_H1_2026-08-2x.md`.

### BUG-025: Subject could read received scores and comments via my-profile / evaluation-details
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: My Profile V5 (Fixed Empty)`; `API: Get Evaluation Details FIXED`.
- Description: Confidentiality of manager/upward scores was enforced only in the browser; both APIs returned numbers, comments, and (details) `private_comment` to the subject.
- Fix (2026-08-20): my-profile attaches score fields only to self rows and computes stats from self-evaluations; details allows evaluator / admin / c_level / subject-of-own-self-review only (HR not privileged), otherwise 404 «Оценка не найдена или недоступна вам».
- Verification: stand suite rows (subject sealed, evaluator 200, foreign 404) + preflight live-definition re-read (`updatedAt` 15:46:56/15:46:53). See `docs/PREFLIGHT_H1_2026-08-2x.md`.

### BUG-026: C-level-only criteria level texts visible to every employee
- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `API: Get Criteria With Levels`.
- Description: `/api/criteria` had `required_roles: []` and no `c_level_only` filter; all level texts of C-level criteria were readable by any registered user.
- Fix (2026-08-20): `level_1_desc`…`level_10_desc` deleted from `c_level_only` rows unless the actor is admin/c_level; titles and descriptions stay for everyone (`level_0_desc` is empty on both `c_level_only` rows — checked live).
- Verification: stand suite + preflight live re-read (`updatedAt=2026-08-20T15:46:52.342Z`). See `docs/PREFLIGHT_H1_2026-08-2x.md`.

### BUG-027: Score Correction did not require the can_evaluate capability
- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `API: Score Correction` guard input.
- Description: Read-only C-level (Cem 21, Hemra 40, Mekan 61, `can_evaluate=false`) could write `c_level` corrections — the guard checked role only.
- Fix (2026-08-20): `required_capability='can_evaluate'` per D-0820-7; guard returns 403 `CAPABILITY_FORBIDDEN`.
- Verification: stand 403 row + preflight live re-read (`updatedAt=2026-08-20T15:46:49.134Z`; guard's capability branch confirmed). See `docs/PREFLIGHT_H1_2026-08-2x.md`.

### BUG-023: `c_level_direct` submit returned 422
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `API: Submit Evaluation` Validate Evaluation.
- Description: `SOURCE_NOT_SUPPORTED` for `c_level_direct`. 2025 stored C-level influence as `score_corrections`, not evaluation rows.
- Fix: allowed for admin or c_level; evaluator = token actor; same `AVG(score_val)`.
- Verification: employee/manager/HR 403; admin and Bayram 200; formula AVG. Live `updatedAt=2026-08-19T19:43:38.525Z`. See `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md`.

### BUG-028: Stale top-level workflow export (evaluations-matrix)
- Status: 🔴 OPEN
- Severity: 🟢 Low
- Location: `n8n_workflows/API_ evaluations-matrix.json`
- Description: The top-level export is the pre-guard, pre-period-binding 4-node workflow. Live runs the generated version (`scripts/build_route_guard_deferred.py` → `route_guard_deferred/evaluations-matrix.json`). Anything importing or trusting the top-level file gets an unguarded, all-periods-mixed matrix — it cost the 2026-08-21 throwaway stand one debug cycle.
- Why it matters: A future session or stand that seeds from the stale export silently reintroduces an unauthenticated period-mixing matrix.
- How to fix: Refresh top-level exports from live after each PUT (deploy_periods_hierarchy.py already does this for Manage Periods), or drop top-level duplicates of generator-owned workflows keeping only the id-bearing metadata.

### BUG-029: Criterion weight of 0 silently behaves as 1.0 in the bonus index
- Status: 🔴 OPEN
- Severity: 🟢 Low–Medium (latent hardening gap — no currently-wrong number; no zero weight or zero grade coefficient exists on live today)
- Location: LIVE `API: Manage Periods` → `Compute Close Results` (`const weight = Number(crit.weight) || 1.0;`); LIVE `API: Get Score Coefficients` → `Format Response` (`weight: parseFloat(row.weight) || 1.0`); `src/hooks/useFinalScoresMatrix.js:84`.
- Description: `|| 1.0` treats 0 as absent. Setting a criterion's weight to 0 — the natural way an admin would express "this criterion should not count toward the bonus" — makes it count with weight 1.0 instead. The same applies to a grade coefficient of 0. A score *coefficient* of 0 is handled correctly (it zeroes the term); only weight and grade coefficient are trapped.
- Why it matters: the bonus index is the money-allocation number. An admin who zeroes a weight to remove a criterion from the pool gets the opposite of what they asked for, silently, with no validation error. Because the index has no denominator (HANDOVER §4), the mistake inflates that person's share of the pool rather than merely mis-scaling it. Since 2026-08-21 the wrong number is also *frozen* into `period_results` at close and cannot be recomputed.
- Repro: set `criteria.weight = 0` for any active criterion, open Итоговые баллы / Калькуляция бонусов — the criterion contributes `score × coefficient × 1.0`. Close the period — the same value is persisted.
- How to fix: use `Number.isFinite(w) && w >= 0 ? w : 1.0` on both sides (the close compute node and the coefficients API), so an explicit 0 means 0 and only NULL/garbage defaults to 1.0. Add a `CHECK (weight > 0)` or an explicit UI affordance for "exclude this criterion" if 0 must stay illegal. The two sides must change together or the server/client parity breaks.
- H1 impact: none today (no zero weights on live; re-measured 2026-08-21: zero criteria with `weight IS NULL OR weight <= 0`, zero `score_coefficients` rows with `coefficient IS NULL OR coefficient <= 0`). Fix before anyone edits the criteria catalogue.

### BUG-030: A failed coefficients call silently un-weighted the whole bonus screen
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `src/hooks/useFinalScoresMatrix.js:150` (pre-fix), consumed by `src/pages/AdminFinalScores.jsx` and `src/pages/BonusCalculation.jsx`.
- Description: the hook fetched the matrix, the criterion coefficients and the grades in one `Promise.all`, with `.catch(() => ({ data: { data: [] } }))` on the last two. On any solo failure — an expired token giving 401, a 500, a network blip — `coefficients` became `[]`, `coefficientsMap` became `{}`, and every criterion then hit the client-only early return `if (!criteriaCoefs) { return score; }`, which returns the **raw, unweighted** cell score. A grades failure defaulted every grade coefficient to 1.00 the same way. The screen rendered a full, plausible bonus table computed without weights or level coefficients, with no error and no empty state.
- Why it matters: the exposure was an admin distributing a real bonus pool from a silently degraded screen. The server has no equivalent branch — `Compute Close Results` reads weight and coefficients from the same SQL result as the scores — so what gets persisted at close was never affected.
- Fix (2026-08-21): the three requests run through `Promise.allSettled`; any rejection is classified and becomes an explicit error state («Коэффициенты не загружены — расчёт невозможен», «Коэффициенты грейдов не загружены — расчёт невозможен», «Матрица оценок не загружена — расчёт невозможен»). The failure branch clears employees, criteria and period, and both money screens return an error card with a retry button before any table renders. No request in the hook substitutes a fabricated empty response any more.
- Verification: `tests/moneyScreenGuards.test.js` (4 assertions over the hook and both screens); frontend release `20260821T072859Z` carries the strings (`useFinalScoresMatrix-D4w0eZxr.js`).
- Residual: the client-only early return still exists for the case where the coefficients API and the matrix disagree on the active-criteria set — unreachable today (both enumerate `criteria WHERE is_active = true`) and tracked under [BUG-029]'s hardening.

### BUG-031: Creating a child period ending on the container's last day was refused
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: LIVE `API: Manage Periods` → `Validate Period Create` / `Build Create SQL` (and the same pattern in `Validate Period Reparent` / `Build Reparent SQL`).
- Description: the child-inside-parent check compared a client-supplied `YYYY-MM-DD` string against the parent's dates as read back from Postgres. The n8n Postgres node returns `date` columns as JS `Date` objects serialised in UTC, so in Europe/Moscow a stored `2026-12-31` came back as `2026-12-30T21:00:00.000Z` and `String(v).slice(0, 10)` yielded the *previous calendar day*. The end-date test was therefore one day too strict: creating a child that ends on the container's own last day returned 422 `CHILD_DATES_OUTSIDE_PARENT`. The start-date test was one day too lenient for the same reason. The reparent path happened to work because both sides came from Postgres and the shifts cancelled.
- Why it matters: this is exactly the H2 attach Alexander performs in September — «H2-2026» 01.07–31.12 under «Annual 2026» 01.01–31.12 — and it would have been refused with a message saying the dates are outside the container when they are not. Found by the post-verification proof, not in production.
- Fix (2026-08-21): containment is decided by Postgres (`'start'::date >= p.start_date AND 'end'::date <= p.end_date` as `child_inside_parent`), and the Code node accepts only an explicit `true`; NULL or false refuses. The same change was applied to reparent so it no longer depends on the two shifts cancelling. The SQL re-assertions inside the INSERT/UPDATE were already date-typed and were correct throughout.
- Verification: stand proof `create_h1_canonical` 200 + `create_h2_canonical` 200 on the canonical 01.01–30.06 / 01.07–31.12 split, `dates_outside_parent_422` still 422; `tests/periodsHierarchy.test.js` — the SQL verdict is read, JS date slicing is gone, and false/null/undefined all refuse. Live `updatedAt=2026-08-21T07:28:10.039Z`.
