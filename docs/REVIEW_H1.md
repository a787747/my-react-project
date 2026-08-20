# H1-2026 Critical-Path Review and Authentication Feasibility

**Review date:** 2026-08-18  
**Deadline assessed:** campaign start by 2026-08-31; results in September  
**Scope:** only A1-A5 and B1-B5 from the review request. Performance, code style, frontend quality, dependency review, and the full domain checklist were deliberately excluded.

## Executive conclusion

**The API cannot be reactivated in its current state.** Authentication is absent, but the immediate data-preservation blocker is even more severe: the live non-self-evaluation uniqueness rule omits `period_id`, and `Submit Evaluation` upserts on that rule. Starting H1 would update the existing 2025 evaluation rows and their detail scores instead of creating an independent H1 record.

The full safe remediation is estimated at **11.5-15 engineer-days**, before contingency, against roughly **9 working days** through 2026-08-31. The verdict for a safe start on the current API by that date is **NO-GO**. A reduced H1-only route set could shorten the route-authorization work, but it does not remove the period-isolation, password, scoring-authority, TLS, or test blockers.

## Evidence boundary

- Live facts were read from `postgres_n8n`, `n8n-n8n-1`, and `public.workflow_entity` over read-only SSH commands in this session.
- No webhook was called, no workflow was activated, and no schema, row, workflow, credential, or container environment value was changed.
- The live n8n version is `1.121.3`; Node is `v22.21.0`.
- The repository does not contain `PROJECT_RULES.md`, `docs/REVIEW_CHECKLIST.md`, `docs/EVALUATION_METHODOLOGY.md`, or the live Portainer compose definition. The missing evaluation methodology means the annual and authoritative scoring business rules are not documented in the expected contract file.

# Part A — Five plan-deciding facts

## A1. Password storage

### Finding

The live login performs **plaintext equality**, not hash verification.

Live workflow `API: Auth Login (No Params)`, Code node `Verify Password`:

```javascript
const inputPassword = $('Prepare SQL').first().json.target_password;
// ...
if (String(user.password_hash) === String(inputPassword)) {
  // ...
  token: 'fake-jwt-' + user.id
}
```

The live `Prepare SQL` node selects the complete user row by email, including `password_hash`; no hash function appears in the login path.

The premise “all 73 rows are plaintext” needs one correction:

- `73` user rows total;
- `68` non-null `password_hash` values;
- `5` null values;
- among the 68 stored values: `0` bcrypt-like, `0` Argon2-like, `0` scrypt-like, `0` PBKDF2-like, and `0` hex-digest-like;
- stored lengths are 5-17 characters.

Therefore, **all 68 stored passwords look like plaintext; five users have no password**. No password values were read or printed.

The repository registration workflow confirms the write behavior: node `Update Password` executes:

```sql
UPDATE performance_db.users
SET password_hash = '{{ $json.password }}'
WHERE id = {{ $json.user_id }}
```

### Consequence

A database disclosure exposes reusable employee passwords. Login and registration must switch together to a real password KDF; the 68 existing values require an authorized migration preceded by a dated dump.

## A2. Period model and route isolation

### Live DDL

The live database does have a nullable foreign key from evaluations to periods:

```sql
CREATE TABLE performance_db.evaluation_periods (
  id integer PRIMARY KEY,
  name varchar NOT NULL,
  start_date date NULL,
  end_date date NULL,
  is_active boolean DEFAULT true
);

CREATE TABLE performance_db.evaluations (
  id integer PRIMARY KEY,
  period_id integer NULL,
  subject_id integer NULL,
  evaluator_id integer NULL,
  status varchar DEFAULT 'draft',
  calculated_score numeric NULL,
  updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
  evaluation_type varchar DEFAULT 'manager',
  is_self_evaluation boolean NOT NULL DEFAULT false,
  evaluation_source varchar DEFAULT 'manager',
  weighted_score numeric NULL,
  FOREIGN KEY (period_id)
    REFERENCES performance_db.evaluation_periods(id)
);
```

Relevant live uniqueness:

```sql
CREATE UNIQUE INDEX idx_evaluations_self_unique
ON performance_db.evaluations (subject_id, period_id)
WHERE is_self_evaluation = true;

CREATE UNIQUE INDEX idx_evaluations_unique_pair_source
ON performance_db.evaluations (subject_id, evaluator_id, evaluation_source)
WHERE is_self_evaluation = false;
```

There are two equivalent non-self unique indexes under different names. Neither contains `period_id`.

Live data currently has one period:

- `Annual Review 2025`, 2025-01-01 through 2025-12-31, `is_active=true`;
- 234 evaluations, all linked to that period;
- 120 manager evaluations, 50 subordinate-to-manager evaluations, and 64 self-evaluations.

### Route classification

Routes whose evaluation reads are scoped to the active/current period:

- `API: Admin Get Users Data`
- `API: Check Evaluated V2`
- canonical `API: Check Self Review` (`QRkUvs24DkcC3WBW`)
- `API: Get Employee Self Review`
- `API: HR Evaluation Status`
- `API: Submit Self Review` when checking for an existing self-review

Routes with mixed behavior:

- `API: Analytics Dashboard - Optimized`: period trends are grouped by period, but overall, department, top-performer, and low-performer queries use every evaluation.
- `API: Get My Manager`: `has_evaluated_manager` and detailed previous scores use the active period, but `last_evaluation_score` ignores period.

Routes that read evaluations and ignore period entirely:

- `API: All-evaluation`
- `API: evaluation-details-by-user`
- `API: evaluations-matrix`
- `API: Manager Subordinates Matrix`

Routes that intentionally return a named record or history rather than the active-period view:

- `API: Get Evaluation Details FIXED` — one client-supplied `evaluation_id`; ownership is not checked.
- `API: My Evaluation History (Received)` — all periods, with period name.
- `API: My Profile V5 (Fixed Empty)` — all periods, with period name.

Write/destructive routes:

- `API: Submit Evaluation` gets the active period, but its upsert conflict key omits period.
- `API: Update Evaluation WITH PERIOD` updates any supplied `evaluation_id`; it does not require that the evaluation belongs to the active period.
- `API: Admin Clear Test Evaluations` deliberately reads/deletes across all periods.
- `API: Score Correction` has no period column or period predicate. Live `score_corrections` uniqueness is `(subject_id, criteria_id, correction_level)`, so corrections also cannot coexist by period.

The other 17 workflow files do not read `performance_db.evaluations`.

### Data-loss blocker

Live `Submit Evaluation`, node `Insert Evaluation`, does:

```sql
ON CONFLICT (subject_id, evaluator_id, evaluation_source)
WHERE is_self_evaluation = false
DO UPDATE SET
  calculated_score = EXCLUDED.calculated_score,
  period_id = COALESCE(EXCLUDED.period_id, performance_db.evaluations.period_id),
  updated_at = NOW()
```

For the same subject/evaluator/source in H1, this reuses the 2025 evaluation ID, replaces its score, changes its period, and upserts the associated `evaluation_scores`. It can overwrite at least the 170 current non-self evaluation rows. This must be fixed before any H1 write is accepted.

## A3. Scoring authority

### Finding

There is no authoritative server-side score computation. All three write paths trust client numbers:

- `Submit Evaluation`: `parseFloat(body.final_score)` is inserted as `evaluations.calculated_score`.
- `Update Evaluation WITH PERIOD`: `body.final_score` directly updates `calculated_score`.
- `Submit Self Review`: `body.final_score` and `body.weighted_score` are directly inserted.

The n8n backend stores criterion-level `grades`, but it does not recompute the submitted total from them. `score_coefficients` and `criteria.weight` are only read/written by coefficient endpoints and consumed by the frontend.

There are several client implementations, not one:

1. Manager, subordinate-to-manager, and direct C-level submission use a simple arithmetic average.
2. Self-review stores a simple average plus `calculateWeightedScore`, which computes  
   `(sum(score × scoreCoefficient × weight) / sum(weight)) × gradeCoefficient`.
3. Admin final-score and score-calculator hooks compute  
   `sum(score × scoreCoefficient × weight) × gradeCoefficient` **without dividing by the sum of weights**.

The live `criteria`, `score_coefficients`, `grades`, and `score_corrections` tables have no period/version key. A later coefficient change therefore cannot be tied unambiguously to the formula in force when an evaluation was submitted.

### Consequence

Any authenticated client can alter `final_score` independently of detailed grades. Different screens can show different “final” results for the same underlying scores. Before H1 results are accepted, one business formula must be fixed and the server must recompute it from validated criterion scores and period-versioned inputs; client totals must be ignored or treated as display-only.

## A4. Annual aggregation capability

### What the current model can express

- Separate named date ranges in `evaluation_periods`.
- One `period_id` reference on each evaluation.
- A workflow-managed “active” flag and queries grouped by period.
- Raw criterion scores per evaluation.

### What it cannot express

- Period type (`H1`, `H2`, `annual`, or another campaign type).
- Parent/child relation between an annual period and its H1/H2 components.
- An annual aggregation record, formula, weights, missing-half policy, approval/calibration state, or frozen result.
- Period-versioned criteria, weights, score coefficients, grade coefficients, or corrections.
- Multiple non-self evaluations for the same subject/evaluator/source across periods under the current unique index.
- More than one correction for the same subject/criterion/level across periods.

Naming rows “H1” and “H2” would be a convention only. The database cannot prove their relationship or preserve the rule that produced an annual score.

## A5. Repository versus live workflow drift

Semantic comparison result: **1 identical, 34 drifted, 0 missing**. All 35 canonical live rows are inactive. Of the 34 drifted files, 32 differ only because the repository export says `active=true` while live says `false`; two also have node-level drift.

| Repository file | Status | Actual difference |
|---|---|---|
| `API_ Admin Clear Test Evaluations.json` | drifted | active-only |
| `API_ Admin Get Users Data.json` | drifted | active-only |
| `API_ Admin Save User (GUI Mode).json` | drifted | active-only |
| `API_ All-evaluation.json` | drifted | active-only |
| `API_ Analytics Dashboard - Optimized.json` | drifted | active-only |
| `API_ Auth Login (No Params).json` | drifted | active-only |
| `API_ Check Evaluated V2.json` | drifted | active-only |
| `API_ Check Self Review.json` | drifted | active-only |
| `API_ Create Invite.json` | drifted | active-only |
| `API_ Get Admin Data Fixed.json` | drifted | active-only |
| `API_ Get Criteria With Levels.json` | drifted | active-only |
| `API_ Get Employee Self Review.json` | drifted | active-only |
| `API_ Get Employees (Smart Role Based).json` | drifted | active-only |
| `API_ Get Evaluation Details FIXED.json` | drifted | active-only |
| `API_ Get My Manager.json` | drifted | active-only |
| `API_ Get Score Coefficients.json` | drifted | active-only |
| `API_ Global CORS Handler.json` | drifted | active-only |
| `API_ HR Evaluation Status.json` | drifted | active-only |
| `API_ Manage Criteria Admin V7.json` | drifted | active-only |
| `API_ Manage Periods.json` | drifted | active-only |
| `API_ Manager Subordinates Matrix.json` | drifted | active-only |
| `API_ My Evaluation History (Received).json` | drifted | active-only |
| `API_ My Profile V5 (Fixed Empty).json` | drifted | active-only |
| `API_ Register.json` | drifted | active-only |
| `API_ Save Score Coefficients.json` | drifted | active-only |
| `API_ Score Correction.json` | drifted | active plus node code: repository accepts correction score 0-10; live accepts 1-10 |
| `API_ Send Verification Code.json` | drifted | active plus SMTP credential binding; credential identifiers/names were not exposed |
| `API_ Submit Evaluation.json` | drifted | active-only |
| `API_ Submit Self Review.json` | drifted | active-only |
| `API_ Update Admin Data.json` | identical | repository omits `active`; no differing compared definition field |
| `API_ Update Evaluation WITH PERIOD.json` | drifted | active-only |
| `API_ Verify Code.json` | drifted | active-only |
| `API_ Verify Invite.json` | drifted | active-only |
| `API_ evaluation-details-by-user.json` | drifted | active-only |
| `API_ evaluations-matrix.json` | drifted | active-only |

No differences were found in `name`, `connections`, `settings`, `staticData`, `pinData`, or `isArchived`.

Live contains three additional inactive, archived rows with duplicate names:

- `UlM7eAX082nfNgrF` — `API: Check Self Review`;
- `sR7mRVLGrmIvpue2` — `API: Check Self Review`;
- `wwiy79j2YjcsSoFR` — `API: evaluation-details-by-user`.

Comparison matched 21 files by workflow ID and 14 by unique name. JSON object order and node array order were normalized; autogenerated/editor metadata was excluded; credential values and credential tables were not read.

# Part B — Authentication design feasibility

## B1. Shared guard sub-workflow

### Mechanism confirmed in this instance

The live database contains:

- workflow `Workflow B` with `n8n-nodes-base.executeWorkflowTrigger`, type version 1;
- workflow `Workflow A` with `n8n-nodes-base.executeWorkflow`, type version 1.

The mechanism therefore exists in this exact n8n instance. The 35 API definitions do not currently use it.

Live workflows also contain 27 `Respond to Webhook` nodes across 24 workflows. The login `Respond` node already uses a dynamic status:

```javascript
responseCode: {{ $json.success ? 200 : 401 }}
```

Static graph compatibility is confirmed. End-to-end execution of a new guard shape is **unverified**, because calling or activating workflows was prohibited.

### Recommended shape

Shared guard input:

- original webhook item, including headers;
- `requiredRole`: one role, an allowed-role array, or `any`.

Shared guard output:

```text
authorized
statusCode
reason
auth.userId
auth.role
```

The guard must:

1. Parse `Authorization: Bearer <token>`.
2. Verify HS256 signature and fixed `alg`, `iss`, `aud`, `exp`, `iat`, and numeric `sub`.
3. Resolve `sub` to a current database user and obtain the current role.
4. Evaluate the allowed-role policy.
5. Return a result item; do not throw for ordinary auth failures.

Roles are not a safe total order: HR and C-level are different capabilities. `requiredRole` must therefore resolve to explicit allowed-role sets, not a numeric “higher than” comparison.

Each protected parent workflow must be:

```text
Webhook -> Execute Guard -> IF authorized
                            | true  -> existing logic
                            | false -> Respond 401/403
```

An Execute Workflow node cannot terminate its parent, so the IF branch is mandatory. Use `401` for a missing/invalid token and `403` for a valid identity lacking the required role. Existing `responseNode` workflows need both branches to reach a response node. `lastNode` workflows must also be normalized/tested so the unauthorized branch reliably returns the chosen status.

The guard authenticates the actor; route logic must still enforce object and relationship authorization. For example, a valid employee token must not be able to submit as another `evaluator_id` or read an arbitrary `evaluation_id`.

## B2. Crypto availability

Live container facts:

```text
NODE_FUNCTION_ALLOW_EXTERNAL=<UNSET>
NODE_FUNCTION_ALLOW_BUILTIN=<UNSET>
N8N_RUNNERS_ENABLED=<UNSET>
jsonwebtoken=AVAILABLE, version 9.0.2
bcrypt=UNAVAILABLE
crypto=AVAILABLE in the container Node runtime
```

Only the main `node /usr/local/bin/n8n` process is running; no separate task-runner process was visible.

`crypto` and `jsonwebtoken` resolve from the installed n8n directory, but neither is currently allowlisted for Code nodes. `NODE_FUNCTION_ALLOW_BUILTIN=crypto` and `NODE_FUNCTION_ALLOW_EXTERNAL=jsonwebtoken` are required. Actual imports inside the Code-node sandbox were not executed and are therefore **unverified**.

### Recommendation

Use `jsonwebtoken` 9.0.2 for JWT signing/verification and Node built-in `crypto` for password storage:

- HS256 signing/verification and claim validation through `jsonwebtoken`;
- password storage with salted `crypto.scrypt`;
- `crypto.timingSafeEqual` for password-hash comparison;
- `crypto.randomBytes` for salts and tokens.

This avoids hand-written JWT parsing and its common algorithm/claim-validation mistakes while avoiding unavailable bcrypt. Because `jsonwebtoken` is currently supplied by the n8n installation rather than this project, pin the n8n image/version and verify module availability before every upgrade. Cover altered payload/signature, expiry, wrong role, wrong issuer/audience, and malformed-token cases.

## B3. Secret storage

Live facts:

```text
N8N_BLOCK_ENV_ACCESS_IN_NODE=<UNSET>
N8N_ENCRYPTION_KEY=SET
Portainer working directory=/data/compose/5
```

The current n8n behavior should not be assumed to expose `$env` when the block flag is unset. The deployment must set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` explicitly if the Code guard reads `$env.JWT_SIGNING_SECRET`. Effective `$env` access was not tested by workflow execution and is therefore **unverified**.

### Recommendation

For this deadline, store the signing secret as a container environment variable and read it through `$env`; do not place it in workflow JSON, repository files, n8n variables, or Code-node literals.

An n8n credential is encrypted in the database and is preferable in principle, but a generic Code node cannot directly consume an arbitrary credential value without a custom node or an additional service/node design. That extra mechanism is not justified for the H1 stabilization.

Set only the narrow module allowlist:

```text
NODE_FUNCTION_ALLOW_BUILTIN=crypto
NODE_FUNCTION_ALLOW_EXTERNAL=jsonwebtoken
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
JWT_SIGNING_SECRET=<random secret, not in git/workflow JSON>
```

Changing Portainer container environment means recreating the n8n container. The currently set `N8N_ENCRYPTION_KEY` must be preserved byte-for-byte; losing it makes stored n8n credentials unreadable. A dated backup of both `performance_db` and n8n `public`, plus the live Portainer stack definition, is required before recreation.

## B4. Route classification

The list below covers all 35 repository workflow files. “Identity field” means a client field currently used as actor identity; target object IDs still require ownership/scope checks even when not listed.

### Group 1 — pre-auth/infrastructure

| Workflow | Route | Policy | Client identity/input note |
|---|---|---|---|
| Auth Login | `POST /auth/login` | pre-auth | `body.email`; password verification establishes identity |
| Verify Invite | `GET /api/verify-invite` | pre-auth | invite `query.token` |
| Send Verification Code | `POST /api/send-verification-code` | pre-auth | `body.email`, invite token |
| Verify Code | `POST /api/verify-code` | pre-auth | `body.email`, code |
| Register | `POST /api/register` | pre-auth | `body.email`, invite token, verification code |
| Global CORS Handler | `OPTIONS /admin/*` | public OPTIONS only | no identity; must allow `Authorization` for protected browser calls |

### Group 2 — authenticated self/service routes

| Workflow | Route | Minimum policy | Field that must stop being trusted / required scope |
|---|---|---|---|
| Check Evaluated V2 | `GET /api/check-evaluated` | `manager` | `query.evaluator_id` -> token `sub` |
| Check Self Review | `GET /api/check-self-review` | `any` | `query.user_id`/fallback body field -> token `sub` |
| Get Criteria With Levels | `GET /api/criteria` | `any` | no actor field |
| Get Employee Self Review | `GET /api/employee-self-review` | `manager` | `query.subject_id` is a target; require actual reporting-line or privileged scope |
| Get Employees | `GET /api/employees` | `manager` | `query.user_id` and `query.role` -> token `sub` and server role; scope to actual reporting line |
| Get Evaluation Details | `GET /api/evaluation-details` | `any` | `evaluation_id` needs subject/evaluator or privileged-object authorization |
| Get My Manager | `GET /api/get-my-manager` | `any` | `query.user_id` -> token `sub` |
| Get Score Coefficients | `GET /api/score-coefficients` | `any` | no actor field |
| My Evaluation History | `GET /api/evaluation-history` | `any` | `query.evaluator_id`/`query.user_id` -> token `sub` |
| My Profile | `GET /api/my-profile` | `any` | `query.user_id` -> token `sub` |
| Submit Evaluation | `POST /api/submit-evaluation` | `any` plus action policy | `body.evaluator_id` -> token `sub`; validate subject relationship and source; direct C-level source requires C-level |
| Submit Self Review | `POST /api/self-review-submit` | `any` | `body.user_id` -> token `sub` |
| Update Evaluation | `POST /api/update-evaluation` | `any` plus ownership | supplied `evaluation_id` must belong to the actor and active period; client also sends `evaluator_id`, which live SQL ignores |

### Group 3 — privileged routes

| Workflow | Route | Minimum policy | Field/scope note |
|---|---|---|---|
| Admin Clear Test Evaluations | `POST /api/admin/clear-test-evaluations` | `admin` | no actor field; destructive all-period action |
| Admin Get Users Data | `GET /api/admin-users-data` | `hr`/`c_level`/`admin` allowlist | no actor field; response scope may differ by role |
| Admin Save User | `POST /admin/save-user` | `admin` | body role/email/manager are target attributes, not actor identity |
| All-evaluation | `GET /api/admin/all-evaluations` | `c_level`/`admin` | no actor field; currently mixes periods |
| Analytics Dashboard | `GET /api/analytics` | `c_level`/`admin` | no actor field; current aggregate queries mix periods |
| Create Invite | `POST /api/admin/create-invite` | `admin` | `body.admin_id` -> token `sub` |
| Evaluation Details by User | `GET /api/admin/evaluation-details-by-user` | `c_level`/`admin` | `query.user_id` is target; route must not accept non-privileged access |
| Evaluations Matrix | `GET /api/admin/evaluations-matrix` | `c_level`/`admin` | no actor field; currently mixes periods |
| Get Admin Data Fixed | `GET /get-admin-data` | `admin` | legacy route; no actor field |
| HR Evaluation Status | `GET /api/hr/evaluation-status` | `hr`/`admin` | no actor field |
| Manage Criteria Admin V7 | `POST /manage-criteria` | `admin` | no actor field |
| Manage Periods | `GET/POST /api/periods*` | `admin` | `body.period_id` is target, not actor |
| Manager Subordinates Matrix | `GET /api/manager-subordinates-matrix` | `manager` plus hierarchy scope | `query.manager_id` -> token `sub` |
| Save Score Coefficients | `POST /api/score-coefficients` | `admin` | no actor field |
| Score Correction | `POST /api/admin/score-correction` | `manager` or `c_level`, action-dependent | `body.evaluator_id` -> token `sub`; validate hierarchy; `subject_id` is target |
| Update Admin Data | `POST /update-admin-data` | `admin` | no actor field |

## B5. Effort

Estimates are engineer-days for one engineer familiar with n8n and PostgreSQL; they include focused tests for each group but not a rewrite.

| Group | Estimate | Reason |
|---|---:|---|
| Shared guard, HS256, secret wiring, login token issuance | 2.0 days | reusable guard, claims, DB identity lookup, 401/403 branches, negative tests, container recreation |
| Pre-auth password/register migration path | 1.5-2.0 days | scrypt login/register, dated dump, migration of 68 values, rollback verification |
| 13 authenticated self/service workflows | 2.5-3.0 days | mechanical guard insertion plus non-mechanical ownership/reporting-line/source checks |
| 16 privileged workflows | 2.5-3.0 days | role allowlists, manager hierarchy checks, destructive route handling |
| Period isolation for evaluations and corrections | 1.5-2.0 days | safe migration, conflict target changes, active-period filters, preservation checks for 234 historical evaluations |
| One authoritative server-side scoring path | 1.5-2.5 days | business formula decision, recomputation, coefficient/version handling, tamper tests |
| HTTPS/CORS, staging regression, activation runbook | 1.0-1.5 days | bearer header preflights, TLS, response-code tests, route-by-route staged activation |
| **Total** | **11.5-15.0 days** | before contingency; some testing can overlap but the data and auth foundations are sequential |

# Preconditions for API reactivation

1. Create and verify dated backups of `performance_db`, n8n `public`, credentials/encryption context, workflow exports, and the live Portainer stack definition.
2. Preserve last year's 234 evaluations exactly; change evaluation and correction uniqueness/storage so H1 writes create period-isolated records instead of updating 2025 rows.
3. Decide and document the H1 + H2 -> annual aggregation rule before H1 starts, including the period relationship and frozen/versioned scoring inputs.
4. Establish HTTPS before transmitting passwords or bearer tokens; make CORS preflight explicitly allow `Authorization` on every protected route.
5. Configure and verify the signing secret and `crypto` access without embedding secrets in workflow JSON; preserve `N8N_ENCRYPTION_KEY` during container recreation.
6. Replace fake tokens with signed, expiring tokens; migrate plaintext password storage to scrypt after the required dump; update login and registration together.
7. Put every reactivated protected workflow behind guard -> IF -> existing logic / Respond 401 or 403, and replace client actor IDs with token identity.
8. Add route-specific ownership, reporting-line, and action authorization; a valid token alone is insufficient.
9. Fix every active-period read that currently mixes 2025 and H1, and prevent updates to historical evaluations through arbitrary IDs.
10. Make the server recompute authoritative scores from validated detailed grades and the approved period-versioned scoring contract; do not trust client `final_score` or `weighted_score`.
11. Reconcile repository exports with the canonical live definitions, remove/resolve duplicate live routes, and retain a versioned export of exactly what will be activated.
12. Pass negative auth, cross-user access, period-isolation, score-tampering, CORS, and preservation regression tests in staging; activate only the tested H1 route subset.

## Verdict on the 2026-08-31 start date

**NO-GO for a safe launch on the current API by 2026-08-31.** The available window is about nine working days, while the verified critical path is 11.5-15 engineer-days and contains sequential data-preservation and authentication work. Reactivating first and fixing later would expose write routes and can overwrite the 2025 results. The deadline can only be retained by reducing the activated surface to the minimum H1 route set, assigning parallel engineering/testing capacity immediately, and still satisfying every data-preservation, period, auth, password, scoring, TLS, and regression blocker above.
