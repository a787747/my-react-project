You are the executor for EPE. Read `AGENTS.md` first and work under it. Then read `HANDOVER.md`, `docs/AUTHENTICATION_CORE_2026-08-18.md`, and `API_CONTRACT.md` §3–§4. Nothing else — a fresh session reading eight reports is as saturated as a stale one.

Save this brief verbatim as `docs/briefs/ROUTE_GUARD_H1_2026-08-19.md` before starting. Your report goes to `docs/ROUTE_GUARD_H1_<date>.md`.

Everything below that describes the code is a hypothesis from an architect with no code access. Verify against the repository and the n8n instance before acting. Where the code disagrees with the brief, the code wins and the disagreement goes into the report.

# Outcome

On day one of H1 (31 Aug) the campaign runs on 23 active API routes:
- 7 pre-auth routes, unchanged: auth/login, verify-invite, send-verification-code, verify-code, register, Request Password Reset, Reset Password.
- GET /api/employees — already guarded and proven.
- 15 routes behind `EPE: Auth Guard`, where the acting identity comes ONLY from `guard.identity`, and every client-supplied identity field (user_id, evaluator_id, admin_id, role, frontend_url) is ignored:
  criteria, get-my-manager, my-profile, check-evaluated, check-self-review, submit-evaluation, update-evaluation (+ its OPTIONS twin), self-review-submit, evaluation-details, evaluation-history, hr/evaluation-status, score-coefficients (GET; POST — see D2), admin/create-invite, admin-users-data, admin/save-user.

The last two are in because Alexander will set the project/general classification of employees himself, in the portal's employees table, before 31 Aug. That classification decides which criteria a subject gets and therefore the bonus index (HANDOVER §4). Editable before launch, frozen after the first submission.

The guard checks role and capability. Each route additionally enforces its ownership rule — that is route logic and part of this brief. Business rules the code must satisfy (how is yours):
- Read routes about "me" (get-my-manager, my-profile, check-self-review, check-evaluated, evaluation-history) return the actor's own data. check-self-review without user_id returns the actor's row, never 500, never another user.
- submit-evaluation: evaluator = actor. source=manager: subject is in the actor's evaluation graph (can_evaluate / can_be_evaluated, subject reports to actor). source=subordinate: subject is the actor's manager and can_be_evaluated; upward never reaches C-level. Subject must be in scope in evaluation_period_participants for the active period; row belongs to the active period (H1, id=2).
- update-evaluation: evaluation_id belongs to the actor as evaluator and to a non-closed period; otherwise rejected, row untouched.
- self-review-submit: user = actor, actor in scope.
- evaluation-details: actor is evaluator or subject of the record, or admin/hr/c_level.
- hr/evaluation-status: hr/admin/c_level only (see D1).
- admin/create-invite, admin-users-data, admin/save-user: admin only. The invite link is built from EPE_FRONTEND_URL, never from a client-supplied frontend_url.
- criteria, score-coefficients GET: any authenticated user.

No scoring change. submit-evaluation, self-review-submit and update-evaluation may change only in WHO writes and WHICH period the row belongs to — never in WHAT number is computed or stored. If a route today stores a client-computed final_score as-is, it keeps doing so; record it as a finding for CALCULATION_MAP.

All other API workflows stay inactive. Delete `api/admin/clear-test-evaluations` (after the n8n public dump). Activation state at the end = as at the start (all inactive) unless Alexander says otherwise mid-brief.

Also: append the block below to `DECISIONS.md` (Alexander's decision, 2026-08-19):

## D-0819-1 — Annual aggregation of H1 and H2
Rating (feedback, 1–10, per source): annual = arithmetic mean of the periods in which the person was in scope; one period → that period's value.
Bonus allocation index: annual = SUM of the period indices (pro-rata for people in scope in one half only).
Self-review is never aggregated and never feeds the index.
Open dependency: which number was used in December 2025 (manager card vs admin matrix) — CALCULATION_MAP question 2.

# Boundaries

- No schema change unless required for period assignment or uniqueness — surface first, rehearse on a restored copy, idempotent migration, dump before.
- 2025 archive untouched: fingerprint before and after, must be `21d323b0…` both times.
- Guard workflow itself is not modified; if a route needs something it cannot express, surface it.
- Deferred routes stay inactive and unguarded. No IP allowlists. n8n image/container untouched. Every temporary session, harness, test row and test workflow deleted; evaluations=0 at the end.

# Acceptance criteria

1. Per-route evidence table in the AUTHENTICATION_CORE format: no_token 401, forged 401, expired 401, wrong_role 403, capability_forbidden 403 where applicable, ownership_violation 403/404, valid 200 — for all 15.
2. Identity-conflict proof per route that accepts an identity field: token actor A, client says B, response and DB reflect A.
3. Write-path proofs: submit for a subject outside the actor's graph → rejected, no row; upward submit whose manager is C-level → rejected; submit for an excluded participant (Esenova, Balova) → rejected; update of another evaluator's evaluation → rejected, row unchanged; valid submit → row with evaluator_id = actor, period_id = 2.
4. One line per pre-auth route: no identity choice possible; what abuse limit exists.
5. End state: evaluations=0, active sessions=0, temporary artefacts=0, activation state by workflow name, clear-test-evaluations deleted, verified dumps (epe_2026, n8n public) with SHA-256 before/after, 2025 fingerprint unchanged.
6. One browser pass on the deployed frontend with real accounts: employee (self-review + upward), manager (one subordinate); no 401 loop; employee dashboard survives deferred routes being inactive. If time is short, reduce this criterion explicitly — do not skip silently.
7. Report written; HANDOVER.md §3/§7 updated in one paragraph each.

# Surface for decision — do not resolve silently

D1 hr/evaluation-status is called by the general dashboard: restrict to hr/admin/c_level and let the employee dashboard degrade, or a self-scoped variant? (Architect's pick: restrict.)
D2 score-coefficients POST during an active period: unavailable (freeze) vs admin-only. (Pick: unavailable.)
D3 What a subject sees about evaluations received — especially upward ones (evaluator name, private_comment). Report current behaviour; Alexander decides whether H1 keeps 2025 behaviour.
D4 Do the three read-only users and C-level submit a self-review?
D5 Uniqueness of (evaluator, subject, source, period): enforce, or is update-evaluation the only path?
D6 Any schema change; how the write paths assign period_id today; how c_level_direct is handled while the matrix is deferred.
D7 Anything that needs the deferred periods* routes before launch (H1 activation is expected via migration + fingerprint proof, not UI).
D8 Which field is the project/general classification (work_category? is_project_participant? — the contract's save-user body has no is_project_participant) and whether the employees table lets Alexander change it. If not — the smallest honest way to give him that.

The report ends with D1–D8, each with verified current behaviour, options, and your recommendation. Do not start on any of them until Alexander answers.

---

# Addendum from the architect — 2026-08-19, after CALCULATION_MAP.md landed (read its §B.3, §B.5, §C — nothing else from it)

1. H1 must be activated (migration + fingerprint proof) BEFORE any rehearsal submission: submit-evaluation stamps period_id=NULL when no period is active; self-review refuses to write. Activation order is now part of your acceptance criteria — report it.
2. On the manager/subordinate write paths, the stored rating must equal the plain average of its own stored score rows after any submit or update, and score values must be validated 1–10 server-side. Same formula, no scoring change; how you achieve it is yours. weighted_score on self-review is untouched.
3. Fact for your ownership rules: submit-evaluation never sets evaluation_type (defaults 'manager'), so check-evaluated matches upward and c_level_direct rows too.
4. D5 (uniqueness) now has evidence — the December upsert defect. Recommend accordingly.

## Executor note — 2026-08-19 (verified read-only, see CALCULATION_MAP.md §E)

`epe_2026` already enforces per-period uniqueness (`idx_evaluations_unique_non_self_period`, `idx_evaluations_unique_self_period`, `idx_score_corrections_unique_period`; `score_corrections.period_id` is NOT NULL). The current `ON CONFLICT` targets in `API: Submit Evaluation` and `API: Score Correction` do not match these indexes: **every call to either route fails on epe_2026 with error 42P10 at planning time** (proven via `EXPLAIN`, no data written). Fixing the two upserts is a launch blocker inside this brief's scope regardless of guard work.
