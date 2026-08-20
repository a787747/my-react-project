# H1 Route Guard — Implementation Report

**Date:** 2026-08-19  
**Status:** Completed and deployed  
**H1 route verdict:** The guarded route surface can run H1. One newly found launch blocker remains outside the write-path brief: out-of-scope employees are still shown and counted in manager task lists (BUG-007).

## Verified baseline

The repository exports and the live n8n/PostgreSQL instance were checked independently.

- Live n8n contains 61 workflows; all 61 are inactive.
- `EPE: Auth Guard` is unchanged and inactive.
- The listed campaign workflows exist and are inactive. `API: Admin Clear Test Evaluations` still exists and is inactive.
- Three workflows named `API: Check Self Review` exist: one unarchived and two archived; all are inactive.
- `epe_2026` contains 0 evaluations and 0 active sessions.
- H1 is period `id=2`, `status=draft`, `is_active=false`; 89 participation rows exist, 87 are in scope.
- The three read-only users are all C-level: Cem Durukan, Mekan Yusupov, and Hemra Ashyrov. Each has `can_evaluate=false` and `can_be_evaluated=false`.
- Project classification is currently internally consistent: 43 users have `work_category='project'`, the same 43 have `is_project_participant=true`, and there are 0 mismatches.
- No dump, fingerprint, workflow update, activation, test row, test session, or temporary workflow was created because the brief requires Alexander's decisions before those operations.

## Verified disagreements and blockers

1. The live evaluation schema is ahead of the repository. Live `evaluations.period_id` is `NOT NULL`, and live unique indexes are:
   - non-self: `(subject_id, evaluator_id, evaluation_source, period_id)`
   - self: `(subject_id, period_id)`

   Neither the live index names nor `period_id NOT NULL` exist in the repository migrations or `schema.sql`.

2. The live and exported `API: Submit Evaluation` still use:

   `ON CONFLICT (subject_id, evaluator_id, evaluation_source) WHERE is_self_evaluation = false`

   This conflict target does not match the live period-aware unique index. A submission would fail before route-guard concerns are reached.

3. `API: Admin Save User (GUI Mode)` writes `work_category` but never writes `is_project_participant`. The manager evaluation UI decides whether project criteria apply from `is_project_participant`. An edit made in the employees table therefore appears saved but does not change the project criteria or bonus-index inputs.

4. `API: Get Evaluation Details FIXED` currently returns `evaluator_id`, `evaluator_name`, `private_comment`, and every criterion comment for any supplied evaluation ID. It has no ownership check.

5. `API: My Profile V5 (Fixed Empty)` exposes evaluator names for received manager and upward evaluations. The regular-user UI hides the details modal for non-self evaluations, but the API itself does not enforce that UI restriction.

6. The three write paths store client-computed numbers unchanged:
   - submit-evaluation stores `final_score` as `calculated_score`;
   - update-evaluation replaces `calculated_score` from `final_score`;
   - self-review-submit stores `final_score` and `weighted_score || final_score`.

   This is recorded for `CALCULATION_MAP`; no scoring change is proposed in this brief.

## Implemented result

- Added deterministic generator `scripts/build_route_guard_workflows.py` and exported 17 guarded workflow payloads under `n8n_workflows/route_guard_h1/`.
- Added and applied `migrations/012_reconcile_evaluation_period_constraints.sql`: period/source are mandatory; non-self uniqueness is `(subject, evaluator, source, period)`; self uniqueness is `(subject, period)`; at most one period can be active and `is_active` must agree with `status='active'`.
- Replaced 17 live workflow graphs through the n8n public API. `EPE: Auth Guard` remained byte-identical (`md5=4677a2e1da390f6299ef283e5abeaad5`).
- Deleted live workflow `API: Admin Clear Test Evaluations` and its repository export.
- Activated the approved launch set: 25 workflows and 28 registered method-path webhooks. No deferred workflow is active.
- Fixed the frontend double-prefix defect found during browser acceptance and deployed release `20260819T094626Z` (`assets/index-CAUq0inK.js`).
- Local verification: Python compilation, no changed-file lints, and 109/109 tests passed.

## Backup and archive proof

| Artifact | SHA-256 / result |
|---|---|
| Pre-change `epe_2026_before_route_guard.dump` | `fd4b24ee2bc2f1d2e0912147e48ba932115207e7747475cb88b85f6ee4bc4190` |
| Pre-change `n8n_public_before_route_guard.dump` | `feff9428316295956170ecbdb5607d0194d0537f22f9149a4382cad38ce3d33b` |
| Final `epe_2026_after_route_guard.dump` | `9cd916091ee5ea8a2a878ea9b666446585bfc4e80e34aca48f316dd6340b58e6` |
| Final `n8n_public_after_route_guard.dump` | `a01f95ec216cd5aeea62dd5e8631bda3f478aaaf5d58b77f9171946538c85360` |
| Final dump restore proof | 89 users, 0 evaluations; 60 workflows, 25 active |
| 2025 archive before / after | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e`, unchanged |

Migration 012 was first applied twice to a restored database. The schema SHA-256 after run one and run two was identical. It was then applied twice to production with the same idempotency proof.

## Protected-route evidence

`N/A` means the route intentionally allows every authenticated role or has no capability/ownership dimension.

| Route | No token | Forged | Expired | Wrong role | Capability | Ownership / rule | Valid |
|---|---:|---:|---:|---:|---:|---:|---:|
| GET criteria | 401 | 401 | 401 | N/A | N/A | N/A | 200 |
| GET get-my-manager | 401 | 401 | 401 | N/A | N/A | actor self | 200 |
| GET my-profile | 401 | 401 | 401 | N/A | N/A | actor self | 200 |
| GET check-evaluated | 401 | 401 | 401 | N/A | N/A | actor evaluator | 200 |
| GET check-self-review | 401 | 401 | 401 | N/A | N/A | actor self; missing ID accepted | 200 |
| POST submit-evaluation | 401 | 401 | 401 | N/A | 403 | graph/scope violation 403 | 200 |
| POST update-evaluation | 401 | 401 | 401 | N/A | 403 | other evaluator 404 | 200 |
| POST self-review-submit | 401 | 401 | 401 | 403 | N/A | actor in scope | 200 |
| GET evaluation-details | 401 | 401 | 401 | N/A | N/A | outsider 404 | 200 |
| GET evaluation-history | 401 | 401 | 401 | N/A | N/A | actor evaluator | 200 |
| GET hr/evaluation-status | 401 | 401 | 401 | 403 | N/A | N/A | 200 |
| GET score-coefficients | 401 | 401 | 401 | N/A | N/A | N/A | 200 |
| POST score-coefficients | 401 | 401 | 401 | 403 | N/A | active-period freeze 409 | 200 before activation |
| POST admin/create-invite | 401 | 401 | 401 | 403 | N/A | actor admin | 200 |
| GET admin-users-data | 401 | 401 | 401 | 403 | N/A | actor admin | 200 |
| POST admin/save-user | 401 | 401 | 401 | 403 | N/A | classification freeze 409 | 200 |

The D7 expansion was tested separately: periods GET permits admin/HR/C-level; periods create and activate are admin-only; missing/forged/expired tokens return 401; wrong role returns 403; valid calls return 200. n8n itself intercepts `OPTIONS /api/update-evaluation` with 204 before workflow execution. OPTIONS carries no identity and cannot mutate data; this is a platform limitation, not an Auth Guard path.

## Identity-conflict and write proofs

| Route | Token actor A / client says B | Verified result |
|---|---|---|
| get-my-manager | employee 3 / `user_id=88` | manager of actor 3 returned (id 1) |
| my-profile | manager 1 / `user_id=88` | actor 1 profile; upward author redacted |
| check-evaluated | manager 1 / `evaluator_id=88` | actor 1 rows; subject 3 present |
| check-self-review | employee 3 / `user_id=88` | actor 3 self row |
| evaluation-history | employee 3 / `evaluator_id=88` | actor 3 outgoing upward row |
| submit manager | manager 1 / `evaluator_id=88` | DB evaluator 1, subject 3, period 2 |
| submit upward | employee 3 / `evaluator_id=88` | DB evaluator 3, subject 1, period 2 |
| self-review-submit | employee 3 / `user_id=88` | DB evaluator=subject=3, period 2 |
| update-evaluation | manager 1 / evaluator/subject 88 | original evaluator 1, subject 3, period 2 retained |
| create-invite | admin 2 / `admin_id=1`, evil frontend URL | DB `created_by=2`; link origin `https://epe.sedamedical.com` |

Additional write proofs:

- Manager submit outside the actor's graph: 403, evaluation count unchanged.
- Manager submit for excluded Aysoltan Esenova: 403, evaluation count unchanged.
- Upward submit to C-level: 403, evaluation count unchanged.
- `c_level_direct` through the day-one submit route: 422, deferred.
- Duplicate submit: 409; update is the only modification path.
- Update by another evaluator: 404; header and timestamp unchanged.
- Valid manager, upward, and self submissions stored client-computed numbers unchanged and belonged to period 2.
- Subject view of upward details hid evaluator ID/name and `private_comment`; evaluator/admin views retained authorized fields.
- Coefficient writes and every project/general classification change returned 409 after the first active-period submission.

## Browser acceptance

Fresh production bundle and real user rows were used with temporary sessions:

- Employee Alina: `/welcome` loaded with correct `/webhook/api/*` requests and no 401 loop; self-review submitted at 7.00; upward evaluation of Akmyrat submitted at 7.00.
- Manager Akmyrat: dashboard loaded direct reports; manager evaluation of Alina submitted at 7.00.
- Deferred routes remained inactive.
- Evidence screenshots:
  - `/var/folders/n8/smrynkb96r9g4mn8b5s3sgf80000gn/T/cursor/screenshots/epe-employee-self-review-complete.png`
  - `/var/folders/n8/smrynkb96r9g4mn8b5s3sgf80000gn/T/cursor/screenshots/epe-employee-upward-complete.png`
  - `/var/folders/n8/smrynkb96r9g4mn8b5s3sgf80000gn/T/cursor/screenshots/epe-manager-alina-complete.png`

The browser pass also exposed BUG-007: excluded Esenova is still displayed and counted in the manager dashboard even though submit correctly rejects her. This can prevent the manager task indicator from ever becoming complete and must be fixed before invitations.

## Final state

```text
workflows=60
active_workflows=25
registered_webhooks=28
clear_test_workflow=0
evaluations=0
evaluation_scores=0
active_sessions=0
active_periods=0
H1=id 2, draft, inactive
H1_participants=89 (87 in scope)
project classifications=43
classification mismatches=0
temporary periods/invites/sessions/databases/workflows=0
running n8n executions=0
```

## Resolved findings from review and acceptance

- **Critical:** generated admin-users workflow read relay Code-node items instead of Postgres result nodes and would return empty user/options arrays. Corrected before deployment and covered by node-reference/mode tests.
- **High:** update workflow interpolated `actorId` without declaring it in that isolated n8n Code-node scope. Runtime valid update returned an empty 200 and changed no row; the variable scope was fixed, the workflow redeployed, and a real owner update then returned the contract body and changed only the intended row.
- **High:** the shared Axios client prepended `/webhook` to endpoint constants that already contained `/webhook`. Fixed, regression-tested, deployed, and verified in a fresh browser context.
- **Medium:** malformed score-coefficient rows threw from the Code node and bypassed structured response handling. They now return 422; runtime invalid-input proof passed.
- **Medium:** manager, self, and update paths initially accepted finite scores outside 1–10. They now reject out-of-range final and criterion scores without recomputing valid client values.

## Remaining findings

- **High — BUG-007:** campaign employee lists and completion denominators do not filter `evaluation_period_participants`. Excluded Esenova is visible to her manager and can keep “all subordinates evaluated” false even though submit correctly rejects her. Fix before invitations.
- **Medium:** pre-auth `send-verification-code` has no resend cooldown; possession of the shared invite permits repeated registration emails. The brief required pre-auth routes unchanged.
- **Low — BUG-008:** reusable invite lookup is global, not `created_by`-scoped. This can misattribute the creator after a second admin is added; Alexander is currently the only admin.
- **Low:** verify-invite has no request throttle. It exposes only validity/expiry of a high-entropy token.
- **Known deferred risk:** `npm ci` still reports 15 advisories (11 high), unchanged under the prior H1 deadline decision.

## Pre-auth route review (unchanged)

- `POST auth/login`: no actor ID is accepted; the email identifies the login account. PostgreSQL limits five failed attempts per 15-minute window and applies a 15-minute lock.
- `GET api/verify-invite`: no actor identity is accepted. The route checks token existence and expiry, but has no request throttle.
- `POST api/send-verification-code`: no actor ID is accepted; invite token plus company email selects the registration target. The code lasts 10 minutes, but the route has no resend cooldown and can send repeatedly while the invite is valid.
- `POST api/verify-code`: no actor ID is accepted; email plus the latest unexpired code selects the registration target. Each code permits five attempts.
- `POST api/register`: no actor ID/role is accepted; user identity comes from the company email joined to an unused invite and a verified, unexpired code. Registration is one-time and passwords are stored with scrypt.
- `POST api/request-password-reset`: no actor ID is accepted; email selects the possible account, while the response stays generic. A known account can receive at most one reset creation per five minutes.
- `POST api/reset-password`: no actor ID is accepted; the random one-time token selects the account. The token lasts 30 minutes, is stored only as SHA-256, and successful use revokes prior sessions.

## Alexander's decisions

Alexander accepted the recommendation for D1–D6 and D8. For D7 he selected the alternative: guard and activate the three `periods*` routes. This explicitly expands the launch surface beyond the original 23-route boundary. The implementation applies least privilege: GET periods permits HR/admin/C-level, while create and activate are admin-only. He subsequently chose to leave the full pre-auth, campaign, and period-management launch set active immediately after acceptance; the H1 period's draft/active state remains a separate control.

## Decision gate

### D1 — Access to `hr/evaluation-status`

**Verified current behaviour:** The workflow returns company-wide completion status for every non-admin/non-HR user. It has no authorization. The manager/team dashboard calls it, but catches a failure and substitutes an empty employee-status list; therefore a 403 does not cause a 401 loop or prevent the main employee/criteria calls from loading. The ordinary employee `Welcome` flow does not call this route. HR, admin, and C-level pages also call it.

**Options:**
1. Restrict the route to `hr`, `admin`, and `c_level`; accept loss of company-wide status decorations on the general dashboard.
2. Add an authenticated self-scoped response for ordinary users.

**Recommendation:** Option 1. The general dashboard already degrades safely, while option 2 expands scope and exposes no day-one business capability that the actor-scoped check routes cannot provide.

**Decision / final behaviour:** Option 1 implemented. Employee/manager requests receive 403; HR/admin/C-level receive the active-period company status.

### D2 — `score-coefficients` POST during an active period

**Verified current behaviour:** The POST workflow has no authorization and no period-state check. It updates criterion weights and all 1–10 score coefficients directly. The frontend scoring page can be reached through `AdminRoute` by admin, HR, or C-level via a direct URL, although only admin receives the sidebar link. The UI has no active-period freeze.

**Options:**
1. Permit admin-only writes before/after a campaign and reject every POST while any period is active.
2. Permit admin-only writes throughout the active campaign.

**Recommendation:** Option 1. These values affect the bonus index; changing them after submissions begin makes employees in the same campaign incomparable.

**Decision / final behaviour:** Option 1 implemented. POST is admin-only and returns 409 when either period activation marker is present; GET is available to every authenticated role.

### D3 — What a subject sees about received evaluations

**Verified current behaviour:** `my-profile` returns the evaluator's name for every received evaluation, including `evaluation_source='subordinate'`. The profile UI displays that name. The evaluation-details API returns evaluator ID/name, `private_comment`, and criterion comments without ownership or field-level redaction. The regular-user UI hides the non-self details modal, but this is not an API security boundary. Actual December 2025 viewing practice was not verified.

**Options:**
1. For a subject, hide `private_comment` for every source and hide evaluator ID/name for upward (`subordinate`) evaluations; retain score and approved criterion comments. Evaluator and privileged roles receive the full record.
2. Preserve the current named, full-field subject response after adding ownership checks.

**Recommendation:** Option 1. `private_comment` is explicitly private, and named upward feedback discourages honest reporting. This is response redaction, not a scoring change.

**Decision / final behaviour:** Option 1 implemented and runtime-proven. Subjects never receive `private_comment`; upward subjects also receive no evaluator ID/name. Evaluators and privileged roles retain authorized detail.

### D4 — Self-review for the three read-only users and C-level

**Verified current behaviour:** The three named read-only users are themselves C-level, and all five C-level users currently have H1 participation rows marked in scope even though `can_be_evaluated=false`. The frontend exempts admin and all C-level users from self-review; task-status and HR-status calculations also treat C-level as exempt. The backend currently has no equivalent eligibility check and would accept any client-supplied user ID if an active period existed.

**Options:**
1. Keep all C-level users, including the three read-only users, exempt.
2. Require self-review from all C-level users who are period participants.

**Recommendation:** Option 1. It matches every existing frontend/status rule and avoids collecting a self-review that has no manager comparison or bonus effect.

**Decision / final behaviour:** Option 1 implemented in the guard: only employee, manager, and HR roles can submit self-review. Admin/C-level receive `ROLE_FORBIDDEN`.

### D5 — Evaluation uniqueness and resubmission semantics

**Verified current behaviour:** The live database already enforces one non-self row per `(subject, evaluator, source, period)` and one self-review per `(subject, period)`. The repository does not reproduce those constraints. Submit Evaluation still targets the obsolete non-period conflict key and would fail against the live schema. Update Evaluation is currently unrestricted and is not transactionally coupled to replacement of score rows.

**Options:**
1. Keep the live period-aware uniqueness; make a duplicate submit fail and require the guarded update route for changes.
2. Keep the uniqueness but make submit an upsert on the full period-aware key, silently replacing an existing submission.

**Recommendation:** Option 1. A separate update path already exists, and an explicit update is auditable while a repeated submit can otherwise overwrite completed feedback accidentally.

**Decision / final behaviour:** Option 1 implemented. The full source/period unique key is enforced by PostgreSQL; duplicate submit returns 409; guarded update preserves evaluator, subject, and period.

### D6 — Schema reconciliation, period assignment, and `c_level_direct`

**Verified current behaviour:** Live `period_id` is mandatory. Submit Evaluation and Submit Self Review select the first `is_active=true` period; neither checks `status`, participant scope, or that exactly one period is active. Update Evaluation leaves the original period unchanged but checks neither ownership nor closed status. `c_level_direct` is produced only from the deferred evaluations-matrix frontend path. H1 is currently inactive, so all three campaign write paths are unusable as intended.

**Options:**
1. Add an idempotent reconciliation migration that validates/reproduces the already-live `NOT NULL` and period-aware uniqueness without changing conforming live data; make writes require exactly one active, non-closed period; keep `c_level_direct` unavailable until its deferred matrix path is activated.
2. Make no repository migration and accept that a restored environment will not reproduce production; additionally expose a new day-one C-level submission path.

**Recommendation:** Option 1. It is a no-op on the conforming live schema, closes the reproducibility gap, and does not expand the 31 August route surface.

**Decision / final behaviour:** Option 1 implemented with the approved D7 expansion. Migration 012 reconciles and enforces the invariants; writes require the single active/status-active period; `c_level_direct` is rejected by the day-one route.

### D7 — Dependency on deferred `periods*` routes

**Verified current behaviour:** No employee, manager, self-review, or evaluation write flow calls the periods API. `AdminPeriods` calls GET periods on page load, but catches failure and still renders the invite-link control after loading finishes. Create/activate are only UI administration functions. The H1 period and participation rows already exist.

**Options:**
1. Keep all `periods*` workflows inactive and activate H1 through the separately dumped, fingerprinted, rehearsed migration/runbook.
2. Guard and activate period-management routes for launch.

**Recommendation:** Option 1. Period-management activation adds privileged mutation surface and is not required for day-one campaign use or invitations.

**Decision / final behaviour:** Alexander selected Option 2. All three guarded paths are active: GET for HR/admin/C-level, create/activate for admin. New periods start draft/inactive with participant rows; switching away from a period that has evaluations is rejected.

### D8 — Canonical project/general classification

**Verified current behaviour:** The employees table edits `work_category` (`general` or `project`) and sends only that field. The save-user workflow also writes only `work_category`. The manager evaluation, project-criteria matrix, and bonus-related UI gates use `is_project_participant`. The two fields happen to match for all 89 users now, but the first portal edit will desynchronise them.

**Options:**
1. Treat `work_category` as the admin-facing canonical field for H1; make save-user atomically derive `is_project_participant = (work_category = 'project')`, return both fields, and reject classification changes after the first evaluation in the active period.
2. Add a second editable checkbox for `is_project_participant` and keep two independent business fields.

**Recommendation:** Option 1. It makes the existing employees table honest with the smallest H1 change and preserves current evaluation code; removal of the duplicate boolean can wait for the Phase 3 backend rewrite.

**Decision / final behaviour:** Option 1 implemented. Save-user accepts only `general/project`, synchronizes the boolean atomically, and globally freezes classification after the first active-period submission. Final live mismatch count is zero.
