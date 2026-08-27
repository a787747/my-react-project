# Architecture Decisions

This is the single architecture decision register for EPE. [`PROJECT_DECISIONS.md`](./PROJECT_DECISIONS.md) is a pointer only.

## Overview
Evaluation Portal is an employee performance review application with role-based workflows for employees, managers, HR, C-level users, and administrators.

## Tech Stack
- Frontend: React 19, Vite 7, Tailwind CSS 3
- Backend: n8n webhooks
- Database: PostgreSQL, schema `performance_db`
- Legacy frontend deployment: `http://135.232.120.40:8080`
- Production origin: `https://epe.sedamedical.com` on host `92.51.45.147`

## Conventions
- Keep API endpoint definitions centralized and environment-driven.
- Use fully qualified PostgreSQL table names under `performance_db`.
- Separate page presentation, reusable components, and data hooks.
- Record architectural decisions and operational discoveries here.

---

## Decisions

### 2026-08-12 — Recovery before feature development

**Context:**
The project was previously in production, but the configured backend is unavailable and the current state of the legacy server and database is unknown.

**Decision:**
Recover and document the existing system before changing features or scoring priorities. Infrastructure inspection must begin read-only, followed by verified backups before service changes or database migrations.

**Rationale:**
- Existing production data may still be present.
- Starting or upgrading n8n without inventory and backups can trigger incompatible migrations.
- Product work cannot be validated while the backend is unavailable.

**Pattern:**
1. Inventory services, versions, volumes, environment configuration, and logs.
2. Back up PostgreSQL, n8n workflows, credentials, and deployment configuration.
3. Reproduce the system in a controlled environment.
4. Restore health checks and then validate business workflows.

**Files:**
- `PLAN.md` — phased revival plan.
- `PROGRESS.md` — initial health-check evidence.

---

### 2026-08-12 — Local-only change policy

**Context:**
The revival starts with a large uncommitted working tree, and the user requested repository-local documentation.

**Decision:**
Keep all work local unless the user explicitly asks to commit, push, deploy, or modify the remote server.

**Rationale:**
This preserves the current project state and avoids accidental production changes while the baseline is still being reconstructed.

**Pattern:**
- Document work in the repository.
- Verify changes locally.
- Request explicit authorization before external or Git mutations.

**Files:**
- `PLAN.md`
- `PROGRESS.md`
- `DECISIONS.md`

---

### 2026-08-12 — Credentials are environment-only

**Context:**
The n8n workflow export utility contained an API key directly in source code.

**Decision:**
All service credentials must be supplied through ignored environment variables or a managed secret store. Source files and example environment files may contain variable names and placeholders only.

**Rationale:**
Credentials in source can leak through Git history, archives, logs, or copied project folders even when the current repository is private or the credential has expired.

**Pattern:**
- Read credentials from environment variables.
- Fail before network access when required credentials are absent.
- Never print credentials in logs or error messages.
- Rotate any credential that may have been exposed.

**Files:**
- `dump_n8n.py` — reads n8n connection settings from environment variables.
- `.env.example` — documents placeholders only.
- `bugs.md` — records the resolved defect.

---

### 2026-08-18 — Organisation import identity and evaluation scope

**Context:**
The HR export contains 88 unique emails but omits Employee ID for 29 people.
The organisational tree also cannot express read-only executives and
period-specific H1 exclusions using only `users.role` and `manager_id`.

**Decision:**
- Match and idempotently upsert users by normalized company email.
- Use names only to resolve and validate `Reports to`.
- Keep the three Lab department strings as separate units.
- Keep `work_category=project` and `is_project_participant=true` aligned under
  the approved department/title rules.
- Store permanent evaluation direction with `can_evaluate` and
  `can_be_evaluated`.
- Store campaign-specific eligibility in a period-participation table when the
  period is created.

**Rationale:**
- Email is the only complete stable key in the export.
- Project criteria are selected by `is_project_participant` in the current
  application.
- The reporting hierarchy and evaluation graph are different business
  relationships.
- A permanent user flag would incorrectly exclude post-H1 hires from H2.

**Pattern:**
1. Validate all identity, grade, department, and manager references before SQL.
2. Insert missing rows and update only distinct values.
3. Keep password hashes outside organisation import updates.
4. Prove reruns with zero changes to rows, links, and sequence states.
5. Fingerprint the read-only source before and after every import.

**Files:**
- `scripts/import_epe_2026.py`
- `docs/IMPORT_2026-08-18.md`

---

### 2026-08-18 — Live-authority JWT and reusable n8n guard

**Context:**
The React client already sends bearer tokens, but n8n trusted client-supplied
IDs and stored plaintext passwords. Role and evaluation capabilities can
change during a campaign.

**Decision:**
- JWTs contain only `sub`, `iss`, `aud`, `iat`, `exp`, and `jti`.
- Token lifetime is four hours with no refresh token.
- Every protected request resolves role, capabilities, token version, and
  session state from `epe_2026`.
- Authentication uses one execute-workflow guard.
- Passwords use scrypt; reset tokens are one-time and stored only as hashes.
- Password reset increments `token_version` and revokes all sessions.
- EPE uses a dedicated Postgres credential; the shared credential remains
  unchanged for archived foreign workflows.

**Rationale:**
- Live authorization makes promotions, demotions, and capability changes
  immediate.
- Four hours limits the theft window while frontend draft persistence and an
  expiry warning protect form work.
- Session rows let password reset invalidate JWTs without adding an
  authorization claim.
- A single guard prevents route-by-route authorization drift.

**Pattern:**
1. Verify JWT signature and exact claims.
2. Join `auth_sessions` to the live user and compare token versions.
3. Check required roles and capabilities in the guard.
4. Ignore client identity fields and use `guard.identity.id`.
5. Keep authentication workflows inactive until HTTPS exists.

**Files:**
- `scripts/build_auth_workflows.py`
- `n8n_workflows/auth_core/`
- `migrations/011_add_authentication_core.sql`
- `docs/AUTHENTICATION_CORE_2026-08-18.md`

---

### 2026-08-18 — Pin the current n8n image by registry digest

The running n8n 1.121.3 image is pinned as
`n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`
instead of using `latest` or the mutable `1.121.3` tag. The current
`1.121.3` tag resolves to a different local image ID than the running
container, so recreating from that tag would not reproduce the reviewed
runtime.

This intentionally freezes n8n security and base-image updates. Revisit the
pin when the n8n backend is rewritten in Phase 3; until then, any image change
requires backups, migration review, and full workflow/credential verification.

---

### 2026-08-19 — One HTTPS origin through Caddy

**Context:**
The portal was served from an Azure Windows VM over HTTP while n8n was public
on another HTTP origin. This required CORS, exposed bearer tokens and
passwords, and made frontend deploys depend on RDP.

**Decision:**
- Serve the React SPA and n8n `/webhook/*` from
  `https://epe.sedamedical.com`.
- Run pinned Caddy in the `epe-proxy` Compose project.
- Build the frontend with the relative API base `/webhook`.
- Block direct public access to n8n port 5678.
- Keep the n8n editor available only through the local SSH tunnel.
- Leave the Azure portal untouched as a fallback.

**Rationale:**
- One origin removes CORS and needs one certificate.
- Relative API URLs remain correct across frontend releases.
- Caddy provides automatic certificate issuance and renewal.
- Atomic static releases remove RDP from the normal deploy path.

**Pattern:**
1. Verify DNS before ACME.
2. Validate Caddy configuration before starting it.
3. Store certificates in named persistent volumes.
4. Deploy timestamped frontend releases and switch a relative symlink.
5. Keep direct backend ports filtered and verify from an external host.

**Files:**
- `infra/Caddyfile`
- `infra/caddy-compose.yml`
- `infra/epe-firewall.sh`
- `scripts/deploy_epe_frontend.sh`
- `docs/TLS_CUTOVER_2026-08-19.md`

---

### D-0819-1 — Annual aggregation of H1 and H2

Rating (feedback, 1–10, per source): annual = arithmetic mean of the periods in which the person was in scope; one period → that period's value.
Bonus allocation index: annual = SUM of the period indices (pro-rata for people in scope in one half only).
Self-review is never aggregated and never feeds the index.
Open dependency: which number was used in December 2025 (manager card vs admin matrix) — CALCULATION_MAP question 2.

---

### D-0819-2 — H1 guarded route policy

- `hr/evaluation-status` is restricted to HR, admin, and C-level; the general dashboard degrades without the company-wide status response.
- Score-coefficient writes are admin-only before/after a campaign and unavailable while any period is active.
- Subjects never receive `private_comment`; upward evaluations also hide evaluator identity.
- Admin and all C-level users, including the three read-only C-level users, are exempt from self-review.
- `(subject, evaluator, source, period)` uniqueness is enforced; duplicate submit is rejected and changes use `update-evaluation`.
- The production period constraints are reconciled through an idempotent migration; `c_level_direct` remains deferred with the matrix.
- The three `periods*` routes join the guarded launch surface. Period reads allow HR/admin/C-level; create and activate are admin-only. After acceptance on 2026-08-19, the full launch-route set is left active immediately; evaluation-period state is controlled separately.
- `work_category` is the H1 canonical project/general field; save-user synchronizes `is_project_participant` and classification freezes after the first active-period evaluation.

---

### 2026-08-19 — H1 guarded route and period policy

**Context:**
The legacy n8n routes trusted client IDs, had no ownership checks, and could
not safely assign repeated half-year evaluations to a period. Project/general
classification also had two fields that the admin UI could desynchronise.

**Decision:**
- Every launch route resolves actor identity through the unchanged live-identity guard.
- Route SQL enforces ownership, active-period participation, and source-specific
  evaluation graph rules.
- Non-self uniqueness is `(subject, evaluator, source, period)`; duplicate
  submit is rejected and changes use guarded update.
- Score coefficients and project/general classification freeze after campaign
  submissions begin.
- `work_category` is canonical for H1 and atomically determines
  `is_project_participant`.
- Subjects do not receive private comments or upward evaluator identity.
- Guarded period read/create/activate routes join the active launch surface.

**Rationale:**
- Client IDs are presentation inputs, not authority.
- Period-aware uniqueness prevents H1 from overwriting H2 or annual rows.
- Freezing money inputs preserves one scoring basis for the campaign.
- Keeping n8n for H1 meets the deadline without accepting the legacy trust model.

**Pattern:**
1. Run the reusable guard before route logic and use `guard.identity.id`.
2. Reassert ownership in the mutation statement, not only in a prior read.
3. Require both `is_active=true` and `status='active'`.
4. Disable n8n execution-data persistence on authentication and guarded routes.
5. Restore evaluations/sessions to zero after acceptance.

**Files:**
- `scripts/build_route_guard_workflows.py`
- `migrations/012_reconcile_evaluation_period_constraints.sql`
- `n8n_workflows/route_guard_h1/`
- `tests/routeGuardWorkflows.test.js`
- `docs/ROUTE_GUARD_H1_2026-08-19.md`

---

### D-0820-1 — Campaign views use period scope, not the org tree

Campaign employee lists (`GET /api/employees`), manager task completion, and
HR status denominators include only `evaluation_period_participants.is_in_scope`
for the single period that is both `is_active` and `status='active'`.

When no such period exists, those campaign views return an empty list and
`campaign_active=false`. They do not fall back to the organisation tree.
Admin user management and other non-campaign screens stay unfiltered.

---

### D-0820-2 — Manager/subordinate writes store the mean of score rows

On submit and update for manager/subordinate (and upward) paths, the stored
`calculated_score` is the plain average of that evaluation's stored score rows.
The client `final_score` is ignored. Grade values outside 1–10 are rejected
with 4xx and no row is written. Self-review `weighted_score` is unchanged.
No schema change.

---

### D-0820-3 — Pre-auth resend cooldown and invite throttle

`POST /api/send-verification-code`: 60-second cooldown per email. A second
request inside the window returns `error_code=resend_cooldown` and
`retry_after_seconds`. This does not block a legitimate employee; they wait
one minute.

`GET /api/verify-invite`: originally 30 requests / 5 minutes / client IP
(see D-0820-5 for the H1 raise). Counted in `auth_login_attempts` under
`epe-throttle:verify-invite:<ip>`. No other pre-auth behaviour changes
in the launch-prep pass.

---

### D-0820-4 — Shared registration link for H1 waves

H1 invitations use one reusable invite token (the unused token already in
`invite_tokens`, plus the Admin → Periods control). Per-wave tokens are not
worth it now. BUG-008 stays open as a known audit-trail issue if a second
admin is added later.

---

### D-0820-5 — verify-invite NAT burst limit for 26 Aug

`GET /api/verify-invite` is 600 requests / 5 minutes / client IP. The 601st
returns `error_code=RATE_LIMITED`. Chosen so ~89 people on one office NAT
can open the shared link in the same five minutes without the 30-cap from
D-0820-3. The 60-second per-email resend cooldown is unchanged.

Live `API: Register` still marks the invite `is_used=true` on first success;
that is not a rate limit and was not changed here. See
`docs/THROTTLE_RAISE_2026-08-20.md`.

---

### D-0820-6 — Shared invite token is reusable for H1

`POST /api/register` must not set `invite_tokens.is_used` and must not
require `is_used=false`. Expiry (`expires_at`) stays. The live shared
token (id=4) is base64url; register accepts `[A-Za-z0-9_-]{16,128}` so
that token and UUID tokens both validate. Gates remain: email in
`users`, verified unexpired code, `password_hash IS NULL`. See
`docs/SHARED_INVITE_2026-08-20.md`.

---

### D-0820-7 — `c_level_direct` enabled for H1

Alexander: C-level management may write `evaluation_source=c_level_direct`
on the launch submit route for H1; the evaluations-matrix GET is active.
Stored number is the same plain `AVG` as manager/subordinate (HANDOVER §4).
Actor role `admin` or `c_level`; evaluator is the token actor. 2025 stored
no `c_level_direct` rows — admin acted at C-level via `score_corrections`.
Admin-as-writer is implemented to match that practice; confirm if it should
narrow to role `c_level` only. See `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md`.

---

### 2026-08-20 — Client drafts reuse one localStorage helper

**Context:**
Dress rehearsal: only the manager→subordinate modal survived refresh.
Self-review is one-shot.

**Decision:**
Reuse `getEvaluationDraftKey(evaluatorId, subjectId)` / 7-day expiry.
Self-review key is `(userId, userId)`. Upward is `(userId, managerId)`.
Logout/401 still do not sweep draft keys.

**Rationale:**
Same helper, same expiry, same 401 survival the manager modal already had.

**Files:**
- `src/utils/evaluationDrafts.js`
- `src/hooks/useSelfReview.js`
- `src/pages/ManagerEvaluation.jsx`
- `docs/DRAFTS_UX_2026-08-2x.md`

---

### D-0820-8 — No outbound mail except Alexander, unless he confirms

Executors must not send mail to anyone except `alexander@sedamedical.com`
without Alexander naming that recipient in the same conversation. Covers
n8n `send-verification-code`, password-reset mail, and SMTP tests. A brief
that asks for an emailed proof is not confirmation. If the proof needs a
code and no mailbox is named, stop and ask.

Triggered after verification codes went to Alina Naubatova and Alp-Arslan
Mametnazar during the shared-invite proof (`docs/SHARED_INVITE_2026-08-20.md`)
without a named-mailbox go-ahead.

---

## 2026-08-20 week decisions (one line each)

### D-0820-6 — Shared token reusable
`POST /api/register` does not set `invite_tokens.is_used`; token id=4 stays reusable until expiry.

### D-0820-7 — `c_level_direct` enabled for H1
Writers are role `admin` or `c_level`; evaluator is the token actor; stored number is the same plain AVG as manager.

### D-0820-9 — Corrections bind to ACTIVE period only
Score-correction writes require `is_active=true AND status='active'`; otherwise 409 `NO_ACTIVE_PERIOD`.

### D-0820-10 — `mid_level` = subject's manager's manager
A mid-level correction is accepted only when the actor is `users.manager_id` of the subject's manager (`skip_level_id`).

### D-0820-11 — Company-wide reporting audience
Company-wide results are admin + c_level; HR keeps `hr/evaluation-status` and the employee table, not analytics / all-evaluations / matrix.

### D-0820-12 — Final cell averages manager + mid? + c_level?
`mean(manager_score, mid_level_correction?, c_level_correction?)` — mid_level counts; no manager_score → empty cell.

### D-0820-13 — `detail_type` is a real filter
Allowed: `all` / `self` / `received_from_manager` / `from_subordinates` / `gave_to_manager` / `gave_to_subordinates`; unknown → 422 `INVALID_QUERY`.

### D-0820-14 — H1 stays active through September calibration
Do not close H1 on 31 Aug evening; leave it `active` until calibration week is done, then close it.

### D-0820-15 — Drafts persist in localStorage, no logout sweep for H1
All three forms use `epe:evaluation-draft:{evaluator}:{subject}`; logout/401 remove only `user` and `token`.

## 2026-08-20 evening — visibility and copy (Alexander, one line each)

Taken after the user-facing copy & visibility audit (`docs/USER_FACING_COPY_2026-08-2x.md`) and implemented
the same night in `docs/PRELAUNCH_FIXES_2026-08-2x.md`; re-verified against live definitions in
`docs/PREFLIGHT_H1_2026-08-2x.md`.

### D-0820-16 — The manager sees the subordinate's real self-review; nothing is hidden from them
`API: Check Self Review` honours `user_id` when it is the actor, a direct report of the actor, or any subject for `admin`/`c_level`; anything else falls back to the actor's own row (no 403, no leak). Per-criterion comments are the subordinate's own, not `general_comment` repeated. Reverses the pre-20-Aug behaviour that showed the manager their own self-review labelled as the subordinate's (BUG-024).

### D-0820-17 — Subject-visible results are sealed on the server until a separate release decision
Not in the browser. `API: My Profile V5` attaches score fields only to self rows and computes profile stats from self-evaluations only; `API: Get Evaluation Details FIXED` answers 404 unless the caller is the evaluator, `admin`/`c_level`, or the subject of their own self-evaluation. HR is not privileged (D-0820-11). **When and how subjects see their own results is a later, separate decision** — no result-release mechanism was built (BUG-025). Scoped by D-0824-3: that later decision concerns manager → subordinate results only; upward content is never released to the evaluated manager.

### D-0820-18 — Manager dashboard status flags are real
Completion flags (`has_self_review`, `has_evaluated_manager`, `evaluated_by_actor`) ride on the enriched `/api/employees` payload; the dashboard no longer calls the HR-only `hr/evaluation-status`, which 403'd for managers and made every subordinate look idle.

### D-0820-19 — `c_level_only` level texts are admin/c_level-only; the criteria wording stays unchanged
`level_1_desc`…`level_10_desc` of `c_level_only` rows are stripped below `admin`/`c_level`; titles and descriptions stay visible to everyone, matching what `CriteriaOverview` renders. The catalogue text itself — including criterion 1's level ladder — was deliberately **not** rewritten (BUG-026).

### D-0820-20 — Out-of-scope people are told, not left with dead links
`/api/employees` returns `actor_is_in_scope`; `TaskStatusContext` drives `OutOfScopeNotice` on Welcome / SelfReview / ManagerEvaluation and hides «Самооценка», «Оценить руководителя» and the task panel. `NOT_IN_SCOPE` on the submit routes stays as server-side defence.

### D-0820-21 — Defects found on the way are fixed immediately, not filed
Reaffirmed for the pre-launch window: a defect surfaced while proving something else is fixed in the same brief and named in its report, rather than deferred to a queue. `docs/POSTVERIFY_BATCH_2026-08-2x.md` §8–9 (BUG-031 and the stale-stand import) are the pattern.

---

## 2026-08-21 decisions (one line each)

### D-0821-1 — Containers are non-activatable reporting constructs
A period with children is a container: no Activate control, API refuses activation (422 `CONTAINER_NOT_ACTIVATABLE`) and close (422 `CONTAINER_NOT_CLOSABLE`); a period with evaluations can never become one; child dates lie within the parent's; reparenting a leaf is always safe.

### D-0821-2 — Close-time result persistence (upgrades HANDOVER §6.13 from proposed to decided)
Closing a leaf period atomically stores per participant into `period_results`: rating per source, the final cell (mean over matrix criterion finals, D-0820-12), the bonus index (formula #3), and the in-scope flag; in-scope-never-evaluated is an explicit no-data marker (CHECK-enforced never-zero). Results are immutable through the product; a second close changes zero rows; closed numbers never require a live join.

### D-0821-3 — Annual display: out-of-scope excluded from the mean, index is a sum (confirms D-0819-1 interpretation)
Annual rating = AVG of persisted finals over in-scope periods with data only — no zero-fill, «вне охвата» marked; «нет данных» visible but excluded from the mean; annual index = SUM of persisted period indices; audience admin + c_level (D-0820-11).

### D-0821-4 — The read-only trio stays in H1 scope; no grades are invented for them
Cem Durukan (21), Hemra Ashyrov (40) and Mekan Yusupov (61) remain `is_in_scope=true` for H1 with `grade_id IS NULL` and `manager_id IS NULL`. They are September readers, not H1 writers: `can_evaluate=false` blocks the evaluation and correction paths, and `can_be_evaluated=false` in all three relation filters of `API: Submit Evaluation` means they can never acquire a `manager_score` — so `final_rating` and `bonus_index` persist as NULL rather than as a coefficient-1.00 money row. Nobody assigns them a grade to make a number appear. Resolves M2 of `docs/PERIODS_VERIFY_2026-08-2x.md`, which that report and `docs/POSTVERIFY_BATCH_2026-08-2x.md` both left open as Alexander's call; the decision post-dates both. Scope freezes at close, so this holds for the whole of H1.

---

## 2026-08-22 decisions (one line each)

### D-0822-1 — Two gates: activation opens preparation, a separate start opens the evaluation
A leaf period now has three states before close. **Activate** makes it the current period and nothing more: employees see no tasks, every submit route answers 409 `PERIOD_NOT_STARTED`, and the admin can still finish the criteria catalogue and the money inputs. **Start evaluation** (`POST /api/periods/start-evaluation`, admin-only, migration 014's `evaluation_started_at`) opens the campaign: tasks appear, submits are accepted, and the criteria catalogue freezes. The mark is irreversible at product level exactly like activation and close — no route clears it, recovery is SQL on the host. Preconditions mirror activate and close: leaf only (containers 422 `CONTAINER_NOT_STARTABLE`), never annual (422 `ANNUAL_PERIOD_NOT_STARTABLE`), never closed (422 `PERIOD_CLOSED`), active only (422 `PERIOD_NOT_ACTIVE`); a second start answers 200 `already_started` and changes nothing. "Campaign period" means **active AND started** on the submit routes, the score-correction route and the whole task/status read surface; admin and reporting reads stay keyed on **active** alone, so the matrix, analytics and all-evaluations behave in the preparation window exactly as they did before. Registration and authentication are untouched.

**Amended 2026-08-24 (Alexander, confirming the two states `docs/LIFECYCLE_COEFF_2026-08-2x.md` §5 surfaced):** (1) the emergency stop — setting an active period back to `draft` by SQL — **also halts the campaign**, because the campaign predicate requires `status='active'` as well as the start mark; every submit route answers `PERIOD_NOT_STARTED` and every task disappears. Confirmed intended: that is what an emergency stop should do. (2) The start mark **survives deactivation**: re-activating a previously started period returns it directly to «Идёт оценка» with no second confirmation. Confirmed intended: the mark is irreversible history, and a period whose evaluation once started is never silently back in preparation.

### D-0822-2 — Coefficients are live until close and admin-eyes-only
Weights, level coefficients and grade coefficients stay editable **until the period is closed**: the `ACTIVE_PERIOD_EXISTS` 409 is removed from `POST /api/score-coefficients` and `POST /update-admin-data` entirely. Closed periods are immune because their numbers live in `period_results` and no reporting surface re-joins these tables. In its place the write paths validate: every weight and coefficient finite and **> 0** (zero is rejected rather than silently read back as 1.0 — BUG-029), levels exactly 1..10, grade coefficients likewise. Reading them is now admin-only: `GET /api/score-coefficients` requires role `admin`, and `GET /api/criteria` strips `weight` for every non-admin role (the `c_level_only` level-text stripping is unchanged). The self-review consequence ships with it — the client no longer fetches coefficients and no longer sends `weighted_score`; the server computes it at submit using formula #2 of `HANDOVER` §4 and the subject's **real** grade coefficient from the database. The client-side `|| 1.0` fallback is retired: a subject with no grade coefficient is refused with 422 `NO_GRADE_COEFFICIENT`, never silently valued at 1.0. `/admin/scoring`, `/admin/score-calculator`, `/admin/final-scores` and `/admin/bonus-calculation` become admin-only at the route level.

**Amended 2026-08-24 — the weight floor is 0.1 (approved by Alexander 2026-08-22).** The rule "finite and > 0" becomes "finite and ≥ 0.1": `MIN_WEIGHT = 0.1` in `API: Save Score Coefficients`, mirroring the client input `min="0.1"`, so the form and the server refuse the same values. This retro-legitimises the 0.1 floor the parallel session introduced during the D-0822-2 build (reverted then because it was an undecided business constraint — `docs/LIFECYCLE_COEFF_2026-08-2x.md` §5.1; decided now). The 422 message still names `is_active` as the correct way to remove a criterion from the bonus. Level coefficients and grade coefficients stay on the plain "> 0" rule.

**Note on grades (recorded 2026-08-24):** grade rows **S4-M1 (id 6)** and **M1 (id 11)** — both «Senior Specialist / Junior Manager», both coefficient 2.20 — are **intentionally one logical grade** split across two rows. Their coefficients must always move together; editing one without the other is an error. (The matrix looks grades up by `code`, so the two rows never collide, but they price the same people.)

---

## 2026-08-24 decisions

### D-0824-1 — The pre-period applicability answer is intentional
The corrections route answers 422 `CRITERIA_NOT_APPLICABLE` before its period gate by design: the refusal is non-mutating and keeps the deployed applicability rule provable on live while the launch is paused; the cost — a role-gated writer can distinguish a subject's current project/general classification pre-period by probing a project criterion, which submit does not offer — is accepted and recorded (closes BUG-048; `docs/FINALIZE_PRELAUNCH_2026-08-2x.md` §1 corrected in place).

### D-0822-3 — Classification stays editable during a running campaign; a switch never destroys evaluation data
Approved by Alexander 2026-08-22, implemented 2026-08-24 (`docs/RECLASS_2026-08-2x.md`). The project/general classification is editable at any time, including mid-campaign: the `CLASSIFICATION_FROZEN` 409 and its global first-submission probe are removed from `POST /admin/save-user`. What replaces the freeze is server-side **applicability, classification dimension only**: a criterion with `target_audience='project_participants'` applies to a subject iff the subject is **currently** a project participant; all other audiences keep their existing semantics everywhere.

- **Exclusion is soft.** Switching project→general keeps every score row in the database; the matrix (`Build Matrix Query`) and the close dataset (`Build Close Dataset Query`) simply stop emitting cells for the no-longer-applicable criteria, and corrections attached to an excluded criterion are excluded with it (they live inside the cell). Switching back re-emits the same rows unchanged — the index returns to the digit.
- **Addition reopens the task.** Switching general→project makes `evaluated_by_actor` false again: the flag is now per-criterion — "an evaluation exists AND covers every currently-applicable manager-path criterion" (active, not `c_level_only`, project criteria for current participants, `managers_only` for subjects with subordinates — the exact set the manager form presents). `/api/employees` names the `missing_criteria_ids`. The other two flags stay row-existence: their sets do not depend on classification.
- **The additive path lives on `POST /api/submit-evaluation`.** An existing evaluation no longer makes every further submit a dead-end 409 (retires the BUG-036 class on the manager path): scores for missing applicable criteria are added to the existing evaluation; criteria it already covers answer 409 `CRITERIA_ALREADY_SCORED` (a full re-submit answers the same 409 `CRITERIA_ALREADY_SCORED`; `DUPLICATE_EVALUATION` remains only on the concurrent-create race in `Format Response` — wording corrected 2026-08-24 to the deployed truth, BUG-047); after any write the server recomputes `calculated_score` from the full surviving row set it counts — a client-sent total is never trusted.
- **Ordinary edit deletes only what the evaluator actively removed.** `POST /api/update-evaluation` never deletes rows for criteria merely excluded by the current classification; the destructive CTE stays gated on `updated_header` (BUG-041) and additionally skips classification-excluded rows.
- **Write validation.** Submit, additive, update and self-review all answer 422 `CRITERIA_NOT_APPLICABLE` for a `project_participants` criterion aimed at a currently-general subject, instead of accepting any criterion id for any subject (RECON §3.3). **Extended 2026-08-24 (approved):** `POST api/admin/score-correction` enforces the same shared predicate with the same 422 — a correction lives inside the cell, so a correction for an inapplicable criterion is refused like any other write (`docs/FINALIZE_PRELAUNCH_2026-08-2x.md`).
- The three scoring formulas are untouched: this decision changes **which cells exist**, never how they are combined. The self-review staleness of `work_category` (login-time snapshot, RECON §3.2.1) is a known limitation, out of scope — today's self set does not depend on classification.

### D-0824-2 — Criterion 14 weight is 1.50 (owner, 2026-08-24)
**Context:** PRELAUNCH_FIX_BATCH found criterion 14 («Ответственность сверх роли») at weight
2.00 on live on 2026-08-24 (between 12:36Z and 14:32Z); the approved value was 1.50; the
coefficients route has no server-side audit trail.
**Decision (Alexander):** the 2.00 was his own front-end editability test through
/admin/scoring — not an incident: no forensics, no password change. He reverted the weight to
1.50 himself. The approved weight of criterion 14 is 1.50; the level curve
0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00 is unchanged.
**Consequence:** the methodology table (§4, pending approval) stays at 1.50. Architect's note:
the coefficients route records no who/when/old→new for edits; an audit log for coefficient
writes is listed in the September queue as a candidate, next to coefficient-table versioning.

**Amendment (owner, 2026-08-24, later the same day):** the level curve of criterion 14 read
on live at 17:15Z (0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00) was also the owner's
/admin/scoring editability test, not a decision. The approved curve remains
0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00; the owner restores it himself. A
read-only comparison of live weights, level coefficients and grade coefficients against
the approved tables is a runbook step before «Запустить оценку» and before close.

> **SUPERSEDED on the level curve by [D-0826-2](#d-0826-2--the-live-criterion-14-curve-is-the-approved-one-upward-and-self-stay-display-only-owner-2026-08-26) (owner, 2026-08-26).**
> The curve on live — `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00` — **is** the approved
> curve for H1-2026. The `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00` figures above and in
> `docs/CRITERION9_2026-08-2x.md` no longer describe the system, and the repository stops calling
> the live values drift. The **weight** of 1.50 in this row is unchanged and still current.
> The approved tables the runbook compares against are now the dated snapshot in
> `docs/coefficients/` (`H1-2026_coefficients_20260826T044844Z.md`), not these figures.

### D-0824-3 — Upward evaluation content is never shown to the evaluated manager (owner, 2026-08-24)
**Decision (Alexander):** scores and comments a subordinate gives their manager (source
subordinate → manager, criterion 2) are never visible to that manager — not now and not under
any later results-release decision. Readers of upward content: the author, admin, c_level.
HR sees completion status only. The Welcome wording is the owner's and is fixed verbatim:
«Оценка вашего менеджера остается анонимной - он не видит конкретные баллы и комментарии,
чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только
C-level менеджеры.» and, on the manager track, «Оценки от подчиненных видят только C-level
менеджеры для обеспечения конфиденциальности и объективности.»
**Consequence:** BUG-036 row 2 is closed by decision once the server is verified to enforce it
(no manager-role surface carries upward scores, comments or aggregates for any subject;
subject-facing reads strip score and comment fields and evaluator identity on upward rows).
Any future results-release decision (HANDOVER §6) concerns manager → subordinate results only.

---

## 2026-08-25 decisions

### D-0825-1 — Catalogue wording revised before the H1 start: 20 fields (owner, 2026-08-25; supersedes D-0820-19 for wording)
**Context:** CRITERIA_HR_REVIEW and CRITERIA_HR_OPINION (2026-08-24) proposed 33 wording changes; the owner selected the five groups with money or fairness consequences — 20 fields — for H1 and deferred the remaining 13 (language only) to H2.
**Decision (Alexander):** (1) criterion 13 re-anchored from time-on-site to project-load share (description, levels 4–10); (2) beyond-role facts are paid only under criterion 14 — removed from 3 (description, level 7), 4 (description, level 6), 8 (description, level 10) and 13 (level 9); (3) criterion 14 level 2 no longer conditions the normal state on «качественно»; (4) top anchors of 2, 4 and 10 no longer reward loyalty, indispensability or «свой человек»; (5) criterion 3 level 10 and criterion 12 level 8 refer to the half-year. Titles, audiences, flags, weights, coefficients and the criteria count are unchanged.
**Consequence:** verbatim before/after snapshots are the H1-2026 catalogue version (docs/catalogue/); ratings on the re-anchored levels are not directly comparable with 2025 (methodology §11 series-break note, carried by the architect); the 13 deferred fields go to the H2 wording pass.

### D-0825-2 — Norm labels removed from level texts (owner, 2026-08-25)
**Decision (Alexander):** the parenthetical norm labels on level 6 of criteria 3, 4, 8, 10 and 12 («Нижняя граница нормы», «Базовая норма», «Норма») are removed; level texts describe behaviour only. The norm convention lives in the rating guide (norm = 6; criterion 14 norm = 2) and in the score zones; the sentence in criterion 14's description stays.
**Consequence:** catalogue version H1-2026 is the "after" snapshot of this brief; supersedes the H2 item «унификация ярлыка (Норма)» from CRITERIA_HR_REVIEW.

### D-0825-3 — Lab Solutions Division attached to its actual head (owner, 2026-08-25)
**Context:** live had the whole Lab Solutions branch flat under Bayram Urayev (COO, id 18): Jahan Hojayeva was `role=employee` with zero direct reports despite the job title «Head of the Lab Solutions Division», and both Clinical Lab Solutions sub-department heads plus the two Special Lab Solution employees reported to the COO directly. The `departments` table has no parent column (`id, name, description` only), so department nesting is not expressible there — the evaluation hierarchy lives solely in `users.manager_id`.
**Decision (Alexander):** the Lab Solutions Division is headed by Jahan Hojayeva (45) and structurally contains Special Lab Solution (no leader) and two Clinical Lab Solutions sub-departments, led by Nurmammet Hekimov (68) and Akmyrat Jumahanov (1). Applied as six `manager_id`/`role` edits: Hekimov and Jumahanov report to Hojayeva; Special Lab Solution's two people (Kostina 6, Muhammedov 55) report to Hojayeva because their sub-department has no leader; Muhammetberdi Garayev (53) joins Hekimov's sub-department; Hojayeva becomes `role=manager`. Hojayeva continues to report to Urayev. Nothing else about the 89 changed.
**Consequence:** Hojayeva is now evaluated on criterion 2 «Качество управления и развитие команды» (applicability is gated on `has_subordinates`, not on role) — 7 criteria instead of 6, and the live distribution moves from 37/11/36/5 to **38 × 4, 11 × 5, 34 × 6, 6 × 7**. Hekimov, Jumahanov, Kostina and Muhammedov gain an upward channel they did not have (their previous manager was `c_level`, which the upward filter excludes) and Hojayeva gains four manager→subordinate tasks; Urayev drops from nine direct reports to four. The org-wide invariant `role=manager ⇔ has direct reports` is preserved (13 managers, zero exceptions).

### D-0825-5 — Logistics reports to Jafarova; Egamberdyev returns to project (owner, 2026-08-25)
**Decision (Alexander):** the logistics department reports to Rovshen Jafarova, titled Logistics
Team Lead (Acting Head of Department), role manager, reporting to Alexander Petrosov (id 2).
Kurbangeldyev (33) is a deliberate exception and keeps the manager set by the owner on
2026-08-25. Ruslan Egamberdyev (74), moved to general on 2026-08-24 for a test, returns to
project participant.
**Consequence:** money. Jafarova gains criterion 2 «Качество управления» (weight 3.00) and the
logistics staff gain an upward channel pointing at her instead of at no one; Egamberdyev's
criteria count returns to its project value, roughly +47% on the bonus index at equal scores.
Both changes are made before the second gate, so no evaluation rows are affected.

### D-0825-6 — Six people are out of evaluation by design; C-level is not evaluated from below
**Decision (Alexander):** three C-level (the read-only trio), the General Manager and two
shareholders are in scope but are evaluated by no one. This is intended, not a coverage defect.
The upward channel excludes subjects whose role is c_level or admin, so the ~24 people who report
directly to C-level have no upward task. This too is intended for H1.
**Consequence:** the evaluated population is 81, not 87 — campaign completion is measured against
81. The six receive no evaluation rows and therefore no bonus index; the pool is distributed over
the remaining people. Both facts belong in EVALUATION_METHODOLOGY §1 and §6.

### D-0825-7 — Terminated employees are forgotten by the product and kept by the database (owner, 2026-08-25)
**Decision (Alexander):** a terminated employee disappears from every list, task and calculation.
They are not evaluated, they do not evaluate, and they take no share of the bonus pool for the
period — including when they already have evaluation rows from earlier in that period. The state
is set from /admin/users, is reversible, and is refused while the person still has direct reports.
Evaluations the person GAVE remain in force, because they belong to the people still employed;
evaluations ABOUT them are excluded.
**Consequence:** money. Excluding a person mid-period redistributes the pool among the rest, so
the termination event carries a date and an author and must remain readable after the period
closes. No evaluation row is ever deleted and nothing is recomputed — the database keeps the full
record so the pool size at calculation time stays reconstructible. Closed periods and the 2025
archive are untouched.

### D-0825-8 — A filter offers only what exists, with the count it will produce (engineering, 2026-08-25)
**Decision:** on /admin/users the option list of every control is derived from the population on
screen, never hardcoded in the markup, and each option carries the number of people it will yield
given the other active filters. A value nobody carries is not offered; a value somebody carries is
always offered, including `hr`, a terminated manager, «Без отдела» and «Без руководителя». Every
number in the header names its own population: «Найдено» is the filtered set, «Всего в базе:
N · работают · уволены» is the whole visible one, and the employment control states how many people
it alone is hiding.
**Consequence:** the filter row can no longer return an unexplained zero. Before this, selecting a
manager whose reports are all `employee` made the role control look broken — «Employee» changed
nothing and every other role emptied the list — and a search for a terminated person answered
«Сотрудники не найдены» with no hint that the default «Работают» was hiding them. The predicate
itself was already correct and is unchanged: role AND department AND manager AND employment AND
search, in any order. Employment keeps `active` as its default and reset returns to it (D-0825-7).
The rule is a frontend one; `API: Admin Get Users Data` still returns every row with no WHERE
clause and was not touched. Report: `docs/ADMIN_USERS_FILTERS_2026-08-25.md`.

### D-0825-9 — «Моя команда» is whatever the server says it is, and a deploy that started from a stale reading refuses (engineering, 2026-08-25)
**Decision:** the manager-facing team list has one source, `GET /api/employees`, and the scope is the
server's to decide — direct reports of the actor, in scope of the active period, only while the
campaign is running. The client never assembles a team by walking the org tree, because a tree walked
client-side has no way to know who is out of scope, who was terminated, or whether the campaign is
open. Consequently `/team` and `/dashboard` answer to the same definition and cannot disagree, a
terminated subordinate cannot appear on either, and both are empty until «Запустить оценку» is
pressed — with a notice that says so rather than «У вас нет подчинённых в системе».
**Consequence:** `/team` shows direct reports only, not the recursive subtree; the whole roster stays
at `/admin/users`, where the guard for it already lives (BUG-065 records the change). The page no
longer calls the admin-only `/api/admin-users-data` (BUG-012) nor the HR-only status route, and the
undeclared `setLoadingSelfReviews` went with the fetch that carried it (BUG-063 — which, measured in a
browser, never fired for a manager at all: the 403 stopped the effect three lines earlier).

**Second half, the same principle applied to deploys:** a deploy may only replace the release it
started from. `scripts/deploy_epe_frontend.sh` holds an exclusive lock locally and on the host, and
flips the symlink with a compare-and-swap — `current` is read before the build and re-read inside the
same remote command that flips it. A mismatch refuses and leaves the symlink alone, because the
alternative is silently reverting whoever is live (BUG-062, after two sessions deployed eleven minutes
apart on 2026-08-25). Neither lock is ever broken automatically. The safety gates moved from `rg` to
`grep -r` and now prove the tool works on the bundle before trusting a clean result, so they cannot
pass in one terminal and fail in another, and cannot pass vacuously against an empty `dist` (BUG-040).
Report: `docs/TEAM_PAGE_AND_DEPLOY_LOCK_2026-08-25.md`.

### D-0825-10 — Scope of a period is editable by hand, employment is not the mechanism (engineering, 2026-08-25)
**Decision:** an admin can take an **employed** person out of the scope of an existing period, and
put them back, through two dedicated admin-only routes. The reason written on the participants row
is `excluded_by_admin` — distinct by construction from `terminated` (a leaver) and from
`hired_after_period_end` (computed once, at period creation). The action touches exactly one
`(period, person)` row: no `users` column of any kind is written, no session is revoked, no reset
token is burned, and the person's `can_evaluate` / `can_be_evaluated` policy flags (D-0821-4) stay
the owner's. They keep their login, can still register through the shared invite, and enter H2
normally when H2 is created — `API: Manage Periods` is deliberately unchanged, unlike D-0825-7,
which scopes a leaver out of every future period as well. Each reverse action flips back only rows
carrying its own reason, so termination and hand-exclusion can never undo each other.
**Consequence:** money, and therefore a record. `performance_db.period_scope_events` (migration 016)
is append-only and names the actor, the period, the event, the machine reason and the owner's words;
`period_id` is NOT NULL there, because a scope change without a period means nothing. Excluding a
person who already has evaluation rows in that period is **refused** until the caller confirms
explicitly, and the refusal states the consequence rather than deciding it: nothing is deleted
either way, evaluations they RECEIVED stop counting for them (they freeze at close as
`is_in_scope=false, has_data=false` with every money column NULL), evaluations they GAVE keep
counting in full for the people who received them, and the pool shrinks by exactly their share.
Direct reports are reported, not refused — a manager who genuinely started in the second half of
the year must be excludable, and who evaluates their reports afterwards is the owner's call.
Closed periods are untouched in both directions.
Report: `docs/MID_YEAR_HIRES_SCOPE_2026-08-25.md`; owner's marking sheet:
`docs/MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md`.

### D-0825-11 — H1 scope boundary: hired after 31 March is out (owner, 2026-08-25)
**Decision (Alexander):** a person hired after 2026-03-31 is out of scope of H1-2026. Less than
three months in the period is too little to judge reliability, development or volume, and a noisy
score feeds straight into money because every participant takes a share of the pool. They keep
their login, enter H2 in full and stay in the annual container. Applied to exactly four people:
Asatryan (25), Atayeva (64), Chariyev (22), Jumayeva (63). Esenova (31) and Balova (35) remain out
by the existing hire-date rule.
**Consequence:** the pool is divided among 80 rather than 84, and each of the four stops being an
upward evaluator of their manager. The annual result is unaffected: the annual rating is the mean
over in-scope periods only with no zero-fill, and the annual index is the sum of half-year indices
(D-0821-3), so these four are measured on H2 alone. Both the excluded people and their managers
are told why, in the owner's words, on the surfaces they actually use.

### D-0825-12 — A missing hire date means out of scope until confirmed (owner, 2026-08-25)
**Decision (Alexander):** when a period is created, a person with no join_date is placed out of
scope with a reason stating that the date is missing and must be confirmed, instead of silently
entering scope as the rule did until now (BUG-066). Forward-looking only: Cem Durukan's H1 row is
not changed, because D-0821-4 keeps the read-only trio in H1 scope.
**Consequence:** people entered into the portal before they start work — signed offer, September
start — no longer join a running period by accident and no longer dilute its pool.

### D-0825-13 — A half-year pays nothing; H1 is an intermediate measurement (owner, 2026-08-25)
**Decision (Alexander):** no bonus is paid for a half-year period. H1 is an intermediate
evaluation whose result feeds the annual evaluation together with H2. Every employee is told this
before they start evaluating, on the Welcome page and in the rating guide, in the owner's words.
**Consequence:** the admin bonus-calculation surface stays — it models the pool from the index —
but nothing is paid on a half-year result. This belongs in EVALUATION_METHODOLOGY §1 and in the
aggregation section alongside D-0821-3.

### D-0825-14 — A share of the pool goes to people who can have a result, and the rule is a predicate (engineering, 2026-08-26)
**Decision:** `/admin/bonus-calculation` lists a person if and only if they are in scope of the
period **and** `can_be_evaluated` is true. No identifier appears anywhere in the rule, so the list
maintains itself: both inputs are edited by the owner in «Сотрудники» and by the period routes.
The rule's output decomposes cleanly and the two halves never overlap — `can_be_evaluated=false`
is exactly the six people evaluated by nobody (2, 18, 21, 40, 47, 61 — D-0825-6, of whom id 2 the
matrix route never returns at all because it filters `role <> 'admin'`), and `is_in_scope=false`
is the nine already excluded for their own decided reasons (three terminated under D-0825-7, two
hired after the period end, four under D-0825-11). Everyone who takes no share is **named on the
screen with the reason**, never silently removed.
**Consequence:** money. On live the pool is 74 of 88 matrix rows. `/admin/final-scores` keeps
showing every row — it is a diagnostic screen, not a payout sheet — but its Σ and its average now
count the pool rather than the page; before this they counted 88 people while the period's own
scope table said 84. The brief's claim that the rule yields «exactly six» is true of the
`can_be_evaluated` half only; the difference is stated rather than hidden.

### D-0825-15 — HR are evaluated employees and the portal must let them act like it (engineering, 2026-08-26)
**Decision:** the personal navigation group and the task panel are shown to role `hr`, as to every
other evaluated employee.
**Consequence:** found by the day-one walkthrough (item 9). Both HR people (Liya Dmitriyeva 52,
Sona Rahmanova 80) are in H1 scope and `can_be_evaluated`; `API: Submit Self Review` accepts role
`hr`; Welcome listed «Самооценка» among their tasks — and the sidebar offered no route to the
form, which worked perfectly when reached by URL. Two of eighty in-scope people would have been
told on day one that they had tasks they could not open. No route, guard or payload changed.

### D-0826-1 — C-level direct evaluations are averaged, like the upward channel (owner, 2026-08-26)
**Decision (Alexander):** when more than one C-level person files a direct evaluation on the same
subject in the same period, the scores are averaged and the number of evaluators is carried, the
same way the upward channel already behaves. Last-writer-wins is replaced.
**Consequence:** money. The two closed criteria are «Стратегическая значимость роли» (weight 5.00)
and «Оценка C-Level и соответствие культуре» (1.60) — the heaviest pair in the catalogue — and
three people hold the right to file them, so collisions were likely from day one. Under the old
behaviour whoever submitted last decided a person's share of the pool. Made before the gate, with
zero evaluation rows in the database, so nothing is migrated and nothing is recomputed.

### D-0826-2 — The live criterion-14 curve is the approved one; upward and self stay display-only (owner, 2026-08-26)
**Decision (Alexander):** the level coefficients of criterion 14 «Ответственность сверх роли» as
they stand on live are the approved values for H1-2026. The earlier D-0824-2 / CRITERION9 figures
no longer describe the system and are superseded on this point. Separately: the bonus allocation
index is built from the manager channel and the C-level direct channel only — the upward channel
and self-assessment are feedback surfaces and do not feed money. Both are intentional.
**Consequence:** criterion 2 «Качество управления» (weight 3.00) is scored in the money by the
manager's own boss alone; subordinates' views inform the rating, not the pool. The coefficient
tables as read on this date are snapshotted as version H1-2026 so the September calculation can be
reconstructed — the December 2025 index cannot be, and that is what this prevents.

### D-0826-3 — A score correction on a c_level_only criterion is refused, not interpreted (owner, 2026-08-26)
**Decision (Alexander):** corrections calibrate the **manager** channel. The C-level channel is
calibrated by being averaged across C-level evaluators (D-0826-1), so a `c_level` correction on a
`c_level_only` criterion (today ids 1 and 10) is **refused** by `API: Score Correction` with
422 `CRITERIA_NOT_APPLICABLE` — the third of the three options costed in
`docs/CLEVEL_AVERAGING_2026-08-26.md` §3 — rather than replacing or joining the mean. Closes
BUG-073's route half; the evaluator-less unique key on `score_corrections` stays recorded there.
**Consequence:** the API is honest today: no calibration action can be accepted, stored, shown and
silently discarded. The refusal sits before the period gate, like the project-dimension refusal,
so it is provable on live while no campaign runs. If the owner later wants a correction to mean
something on the C-level channel, that is a new decision and a one-line change in four places —
nothing stored has to be migrated, because nothing can be stored.
**Implemented:** PRELAUNCH_GATE 2026-08-26, `docs/PRELAUNCH_GATE_2026-08-26.md` — proven
money-neutral by two closes of two copies of one dump (100/100 frozen rows identical).

### D-0826-4 — The hire date is editable and drives scope; a manual mark overrides it (owner, 2026-08-26)
**Decision (Alexander):** the hire date is corrected from the employee card by the admin, empty
included, and correcting it recomputes scope for open periods. A manual exclusion or a termination
is never overridden by that recompute; closed periods are never touched; a recompute that would
remove a person who already has evaluations in the period is refused rather than performed. A
manual per-period participation toggle sits in the same card and replaces the command-line path.
Every such change is recorded with actor and time.
**Consequence:** money, in both directions. Scope decides who is evaluated, who evaluates, and who
takes a share of the pool, and until now a wrong hire date could not be corrected at all while
scope could only be changed outside the product. The hire date leaves the frozen-column set: a
change to it is now an ordinary owner action, not an incident.

### D-0826-5 — Scope rule: less than three months in the period means out (owner, 2026-08-26)
**Decision (Alexander):** a person hired later than three months before a period ends is out of
scope of that period. This replaces the previous rule, which excluded only people hired after the
period had already ended. It is the rule already applied by hand to H1-2026 — Asatryan (25),
Atayeva (64), Chariyev (22), Jumayeva (63) — now expressed in the system.
**Consequence:** H2-2026 and every period after it apply the boundary automatically instead of
requiring the same manual pass, and a hire-date correction moves a person to where the rule says
they belong rather than to where the old rule said. A shorter stretch of work produces a score too
noisy to justify a share of the pool.

### D-0826-6 — C-level reads the admin surfaces, HR reads the roster; neither writes (owner, 2026-08-26, via the ROLE_ACCESS_HR_CLEVEL brief)
**Decision (Alexander, as briefed):** role `c_level` gains READ access to `/admin/users`, `/admin`
(criteria), `/admin/all-evaluations`, `/analytics`, `/admin/evaluations-matrix`,
`/admin/final-scores` and `/admin/score-calculator`; role `hr` gains read access to the employees
roster (`/admin/users`). Neither role gains any write capability: every write route — user save,
termination, scope, period management, criteria, coefficients, corrections, invites — refuses
both roles by role, server-side. Compensation columns never reach these roles (the roster route
carries no salary column for anyone; grade coefficients are stripped for HR). An empty or
forbidden surface names its reason instead of rendering a blank list.
**Consequence:** C-level reads the money surfaces — this partially supersedes D-0822-2's
"coefficients are admin-eyes-only" (read-only, for c_level, on the GET route; both save routes
stay admin-only). ~~The corrections item supersedes the **writer half of D-0820-7**~~ — **corrected
by D-0826-7 below before deployment: D-0820-7 stands, c_level keeps its score corrections.** The
conflict was flagged to the owner in `docs/ROLE_ACCESS_HR_CLEVEL_2026-08-26.md` §4.1 with the
one-line revert named, and the owner took the revert. "Password reset
refuses both roles" is unimplementable — the routes are unauthenticated self-service recovery with
no role dimension; surfaced, unchanged.
**Implementation:** branch `claude/hr-clevel-access-control-dudin7` (generators + frontend +
tests + deploy/prove scripts). **Not yet on live** — the executing session had no access to the
Mac, the VPS or live; the stand proof, deploy and live verification follow the runbook in the
report §5.


### D-0826-7 — Correction to D-0826-6: c_level keeps its score corrections; D-0820-7 stands (owner, 2026-08-26, via the ROLE_ACCESS_DEPLOY brief)
**Decision (Alexander):** the ROLE_ACCESS_HR_CLEVEL brief's instruction to refuse role `c_level`
on `api/admin/score-correction` was wrong and is reverted before it ever reached live. D-0820-7
stands as written: `c_level` (with `can_evaluate`) is the intended author of `c_level`-level
corrections. Every other refusal of D-0826-6 remains in force — corrections stay the ONE write
route that admits `c_level`; no write route accepts `hr`.
**Consequence:** Bayram (18) and Jemal (47) keep their September calibration instrument. What
still bounds them is unchanged by this brief: `can_evaluate` (the read-only trio get 403
`CAPABILITY_FORBIDDEN`, D-0820-7), and D-0826-3 (a correction on a `c_level_only` criterion is
422 `CRITERIA_NOT_APPLICABLE` for everyone — the C-level channel is calibrated by averaging).
The live workflow `API: Score Correction` is therefore byte-identical before and after this
batch; the deploy script keeps it as a drift check with an expected `"changed": false`.
**Implementation:** the revert commit on `claude/hr-clevel-access-control-dudin7` before the
merge to main; report `docs/ROLE_ACCESS_HR_CLEVEL_2026-08-26.md` §8.

### D-0827-1 — Criteria catalogue readers see the ten level texts without opening the edit form (2026-08-27)

**Decision:** a `c_level` (or any non-admin) reader of `/admin` must be able to
open each criterion and read its description and `level_1_desc`…`level_10_desc`
from the payload they already receive. No edit affordance on that path. Admin
editing stays the existing `CriteriaForm`. Completes the C-level read of the
criteria page granted by D-0826-6; does not change who may write, and does not
add fields to `manage-criteria` GET.

**Consequence:** C-level can read the same scale texts an evaluator already sees
on the scoring form, without being able to change a frozen catalogue. Weights
remain on the money screens, not newly promoted onto this page.

**Implementation:** `docs/CRITERIA_READONLY_DETAILS_2026-08-27.md`; frontend
`20260827T060913Z`.

### D-0827-2 — An untouched criterion is not a score of 1 (2026-08-27)

**Decision:** on the evaluator forms (self-review, manager→subject, upward)
the slider thumb may rest at the left end of the track, but until the
evaluator touches it the criterion shows no number and no zone label — a dash
in the corner, nothing under the scale. Both appear on first interaction.
Submission stays blocked until every applicable criterion has been touched.
The submit payload omits untouched keys; it never invents a 1.

**Consequence:** the owner's screenshot («1/10», «Зона риска» on an untouched
card) is a visual lie, not a stored 1. A crafted API call can still store a
partial set; the server writes only the keys sent and treats the rest as
missing (additive path included). That write-route behaviour is unchanged.
The C-level modal still prefills 5 (BUG-078) — out of this decision.

**Implementation:** `docs/EVALUATION_FORM_READABILITY_2026-08-27.md`; frontend
`20260827T065624Z`. The C-level exception (BUG-078) is closed by D-0827-3.

### D-0827-3 — C-level modal follows the untouched-criterion rule; /admin/users names every campaign population (2026-08-27)

**Decision:** the C-level evaluation modal obeys the same rule as D-0827-2:
the slider may rest, an untouched criterion shows a dash and no zone, and
submit is blocked until every applicable C-level criterion has been touched.
The payload never invents a 5. An existing actor score remains shown and
editable.

On `/admin/users`, the campaign summary names each population and never mixes
them: everyone; employed; in-scope of the current period; evaluated-by-someone
(in-scope and `can_be_evaluated` — the six the owner declared evaluated by
nobody are in scope and excluded here). Registration is counted against
employed people (the invitation list). Campaign progress is two directions:
tasks assigned TO a person (Welcome: self / upward / evaluate in-scope
evaluable subordinates) and whether that person has been fully evaluated BY
everyone who owes them a 1:1 evaluation (complete manager-path, plus owed
upward). `c_level_direct` is a shared channel and is in neither counter.

**Consequence:** opening the C-level modal and confirming without a touch can
no longer store a mid-scale 5 on criteria 1 and 10. The owner steers H1 from
labelled numerators and denominators, not from an unlabelled mix. BUG-070
(HR card) is a different screen and is unchanged.

**Implementation:** `docs/ADMIN_USERS_SUMMARY_AND_CLEVEL_MODAL_2026-08-27.md`;
frontend `20260827T075704Z`; `API: Admin Get Users Data` read-payload
extension.

### D-0827-4 — Peer recognition is a separate surface, and it never becomes a count (2026-08-27)

**Decision:** any employed, registered person may name **one** colleague per
period whose help mattered, in three free-text fields (situation → action →
outcome), on a **separate page** with its own menu entry «Отметить коллегу» —
not a field inside the evaluation form, which is not touched while the campaign
runs. The nomination is replaceable until the period closes and is physically
one row: `UNIQUE (period_id, author_id)`.

Refused, server-side and re-asserted inside the writing statement: oneself,
one's own manager, one's own direct report, and anyone terminated. Readers are
`admin` and `c_level` only — HR is refused 403, the nominated person is refused
403, their manager is refused 403.

**No count of nominations is displayed anywhere, for anybody, ever** — not a
number, not a badge, not a sort order, not a leaderboard, not a column in an
export. The reader's list is ordered by time alone, and the table carries no
index on `nominee_id`, because the only query such an index makes cheap is the
one that must never run.

Scope binding is the **active leaf period**, deliberately NOT gated on
`evaluation_started_at`: people out of scope of H1 have no evaluation tasks at
all and are exactly the population the surface is for. Close ends it — with no
active leaf the save route answers 409 `NO_ACTIVE_PERIOD`.

**Consequence:** it is not a vote, not a rating and not money. Migration 018's
table has no numeric column and no foreign key into `evaluations`,
`evaluation_scores`, `score_corrections` or `period_results`. Proven, not
asserted: two copies of one database — identical in every money input, differing
only by the two nomination rows — were closed side by side by the real route and
froze **89 `period_results` rows md5-identical** (`565faa99…`), including the
rows of both nominated people.

**Implementation:** `docs/PEER_RECOGNITION_2026-08-27.md`; migration 018;
workflow `API: Peer Recognition` (`KLDk6WmWZKsZ8GVX`, 3 routes); frontend
`20260827T114910Z`. Two of the three refusal sentences are the executor's
wording, not the owner's, and are flagged in §9 of the report.
