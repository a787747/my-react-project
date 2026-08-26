# EPE — Handover

**As of:** 2026-08-26 (CLEVEL_AVERAGING) · **H1: active, not started**
H1 (id 2) has been **active** since **2026-08-24 19:07:36Z** (`POST /webhook/api/periods/activate`, Caddy 200,
from `/admin/periods`). `evaluation_started_at` is still NULL — preparation window; employees have no tasks;
submits answer 409 `PERIOD_NOT_STARTED`. The invitation date and «Запустить оценку» remain **his**. §7 is
the remaining order of work.

Every number in §§1–3 and §§5–10 was re-measured against the live system on 2026-08-24 17:14–17:16 UTC,
read-only (SELECT / GET / `readlink` / `openssl` / `crontab -l`). **§4 is copied verbatim and was not
edited** (md5 `0b2e854c22dc41f1d96e169b375b6350` before and after). Reports were used to locate claims,
never as the source of a fact — see `docs/DOCS_HYGIENE_2026-08-24.md` for the live-vs-docs and
docs-vs-docs differences this pass found.

---

## 1. What the system is

Employees Performance Evaluation for SEDA Medical Turkmenistan. 89 people. React SPA + n8n as the entire backend + PostgreSQL.

**Live now:** H1-2026 is the current period (`status=active`, `is_active=true`) since **2026-08-24 19:07:36Z**. The campaign has not been started. Four data tables are empty.

It ran exactly one cycle: a single annual period, "Annual Review 2025", 234 evaluations all dated December 2025. It has never run a half-year cycle. The season goal — H1 → H2 → annual aggregation — is new capability, not a repeat.

Evaluation is multi-source: self-review, manager→subordinate, subordinate→manager (upward), and c_level_direct. Criteria are role-differentiated via `criteria.target_audience`. Two-level correction (`mid_level`, `c_level`) exists as a calibration layer.

Since 2026-08-21 periods form a **hierarchy**: a half-year period may hang under an annual **container**, and closing a half-year period **freezes** its per-person results into `period_results` so the annual roll-up never has to recompute them. That is the mechanism the season goal was missing.

---

## 2. Current state — infrastructure

| Thing | State (live, 2026-08-24 17:14–17:16 UTC) |
|---|---|
| Host | `92.51.45.147`, Timeweb VPS, root via SSH key (password auth disabled, fail2ban on). Up **11 days, 19 hours** (`uptime` 2026-08-24 17:14 UTC) |
| Public origin | `https://epe.sedamedical.com` — Caddy (`epe-proxy-caddy-1`) serves portal + `/webhook/*` → n8n |
| Certificate | Let's Encrypt (`YE1`), `notBefore` 2026-08-19, `notAfter` **2026-11-17** |
| n8n | pinned by digest `sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, `restart=unless-stopped`, running, port 5678 DROP from `eth0` |
| Live DB | `epe_2026`, schema `performance_db`, own credential `EPE 2026 Postgres` |
| Archived DB | `postgres.performance_db` — 2025 data, **read-only forever**. This session by SELECT: **73 users, 234 evaluations, 644 scores, 3 corrections**. Fingerprint not re-hashed today (no dump taken); last computed `21d323b0…` in `docs/DRAFTS_UX_2026-08-2x.md` |
| Databases on `postgres_n8n` | **`epe_2026` and `postgres` only** — every throwaway stand DB is gone |
| Frontend | This host. Current release **`20260826T051630Z`** (2026-08-26 05:16:30Z, CLEVEL_AVERAGING). **36** releases on disk; the rollback target is the previous one, `20260825T194735Z`. Deploy: `./scripts/deploy_epe_frontend.sh` — it now holds an exclusive lock locally and on the host and refuses a flip that started from a stale `current` (BUG-062), and its safety gates use `grep -r`, not `rg` (BUG-040). |
| Azure VM | `135.232.120.40`, untouched fallback, still serves the old build on :8080. **Not re-probed this session** (last measured `docs/TLS_CUTOVER_2026-08-19.md`: TCP 3389 RDP open). September queue. |
| Firewall | `DOCKER-USER` → `EPE-DOCKER-USER` (ufw does not filter Docker ports). 80/443 open; 5432/5431/8000/9000/2377/7946/4789 restricted to one allowlisted IP; 5678 DROP on `eth0`. **The allowlisted source is a single home IP (`188.137.254.191`) that changes — use the SSH tunnel, not the allowlist** |
| Portainer | Reachable only via SSH tunnel `127.0.0.1:29000` |
| Backups | **Two daily jobs since 2026-08-21.** 03:00 MSK `backup-performance-db.sh` → the 2025 archive (`postgres -n performance_db`), **13** dumps on disk (`retained=13` in the 2026-08-24 00:00Z log). 03:20 MSK `backup-epe-live.sh` → **`epe_2026` in full** and the **n8n application schema** (`postgres -n public`: 58 workflows, 7 credentials, 8 settings). Today's live job: `backup-epe-live.status` = **`OK 2026-08-24T00:20:01Z`**; `epe_2026` 24 100 B retained=4; `n8n_app` 366 338 B retained=4. 14-day stem-scoped prune on both; failure = non-zero exit + `FAIL` in `backup.log` and in `backup-epe-live.status` (no MTA on the host, so that file is the alarm). Restore-proven 2026-08-21: 17/17 and 52/52 tables row-matched from a cron-produced dump. BUG-032 **closed**, `docs/BACKUP_FIX_2026-08-2x.md`. **Off-host copy still missing (BUG-014)** — one disk now holds live, n8n and every backup of both |

Workflows: **60 total** = **35 active** + 3 inactive unarchived (`EPE: Auth Guard`, `API: Global CORS Handler`, `My workflow 10`) + **22 archived**. **48** registered webhooks (21 GET / 25 POST / 2 OPTIONS). Re-measured 2026-08-26 05:19Z. Two were rewritten on 2026-08-26 at 05:16Z by CLEVEL_AVERAGING — `Manage Periods` and `evaluations-matrix` — with no node added or removed and every webhook path unchanged. The two added since the 58/42 reading are `API: Manage Employment Status` (D-0825-7) and `API: Manage Period Scope` (D-0825-10); five existing workflows were rewritten on 2026-08-25 at 19:47Z by PRELAUNCH_BATCH_NIGHT — `Manage Periods`, `Admin Get Users Data`, `Manage Period Scope`, `evaluations-matrix`, `Get Employees (Smart Role Based)` — with no node added or removed and every webhook path unchanged.

Active set (live names, 2026-08-24 — identical to the 2026-08-20/21 set):

```text
API: Admin Get Users Data
API: Admin Save User (GUI Mode)
API: All-evaluation
API: Analytics Dashboard - Optimized
API: Auth Login (No Params)
API: Check Evaluated V2
API: Check Self Review
API: Create Invite
API: evaluation-details-by-user
API: evaluations-matrix
API: Get Criteria With Levels
API: Get Employees (Smart Role Based)
API: Get Evaluation Details FIXED
API: Get My Manager
API: Get Score Coefficients
API: HR Evaluation Status
API: Manage Criteria Admin V7
API: Manage Periods
API: Manager Subordinates Matrix
API: My Evaluation History (Received)
API: My Profile V5 (Fixed Empty)
API: Register
API: Request Password Reset
API: Reset Password
API: Save Score Coefficients
API: Score Correction
API: Send Verification Code
API: Submit Evaluation
API: Submit Self Review
API: Update Admin Data
API: Update Evaluation WITH PERIOD
API: Verify Code
API: Verify Invite
```

The set has not changed since 20 Aug; the webhook count rose 41 → **42** because `API: Manage Periods` grew from 7 to **8** routes (`POST api/periods/start-evaluation`, D-0822-1). CORS stays inactive. `Get Employee Self Review` and `Get Admin Data Fixed` are confirmed **absent** from `workflow_entity` (deleted; generators still emit them — BROWSER_WALKTHROUGH §9.4). H1 is **active** and **not started** — nothing campaign-shaped can be written until «Запустить оценку». Unauthenticated `GET /webhook/api/periods` and `GET …/annual-rollup` → **401 `TOKEN_MISSING`**; `GET …/start-evaluation` → 404 (POST-only, expected).

`My workflow 10` is an unnamed stray in the inactive-unarchived three. Archiving it would make the "3 inactive" baseline mean something; nobody has.

---

## 3. Current state — what is built

- **Real authentication.** JWT (HS256, 4h, claims `sub/iss/aud/iat/exp/jti` only). Role and capabilities read live from DB per request; the guard ignores any role claim in the token. Proven: no token / forged / expired / wrong role / forbidden capability all rejected.
- **`EPE: Auth Guard`** — one reusable execute-workflow sub-workflow. **Canonical check: `updatedAt=2026-08-18T16:34:30.674Z`, `active=false`** — re-read live today, unchanged since 18 Aug through every PUT since. GET-body md5 is **not** canonical: the same GET serializes to more than one hash. Identity from token only. Migration 012: `period_id` mandatory, uniqueness `(subject, evaluator, source, period)` and `(subject, period)`, at most one active period. `work_category` canonical, `is_project_participant` derived atomically; **classification is editable at any time, including mid-campaign (D-0822-3, 2026-08-24)** — the old `CLASSIFICATION_FROZEN` 409 is gone, replaced by server-side applicability: project criteria (8/13) count only for current project participants, a switch soft-excludes their score rows without deleting them, and switching back restores the index to the digit. **Coefficient writes no longer 409 at all** (D-0822-2): weights (floor 0.1 since 2026-08-24), level coefficients and grade coefficients are editable until close, validated instead of frozen. Criteria-catalogue writes 409 `EVALUATION_STARTED` once the evaluation has been started (D-0822-1), not on activation.
- **Subject-side visibility is enforced on the server, not in the browser.** This was the opposite a week ago and is the single largest change of 20 Aug. `API: My Profile V5` attaches `score`/`calculated_score`/`weighted_score` only to self rows and computes profile stats from self-evaluations alone; `API: Get Evaluation Details FIXED` returns a row only to the evaluator, to `admin`/`c_level`, or to the subject of their **own** self-evaluation — anything else is 404. Upward evaluator identity is nulled to the subject. HR is **not** privileged here (D-0820-11). **D-0824-3 (owner, 2026-08-24):** scores and comments a subordinate gives their manager are never shown to that manager — not now and not under any later results-release. Readers of upward content: the author, admin, c_level; HR sees completion flags only. Report: `docs/PRELAUNCH_FIXES_2026-08-2x.md`, re-verified against live definitions in `docs/PREFLIGHT_H1_2026-08-2x.md` and again in `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md`.
- **The manager form serves the subordinate's real self-review.** `API: Check Self Review` honours `user_id` when it is the actor, a direct report, or any subject for `admin`/`c_level`; anything else silently falls back to the actor's own row (no 403, no leak). Before 20 Aug it showed the manager their own self-review labelled as the subordinate's — BUG-024.
- **Manager dashboard statuses are real.** Completion flags (`has_self_review`, `has_evaluated_manager`, `evaluated_by_actor`) ride on `/api/employees`; the dashboard no longer calls the HR-only status route and no longer reports every subordinate as having done nothing. **Since 2026-08-24 the same payload also carries the current period's `period_name` / `period_start_date` / `period_end_date`** — `to_char(…, 'YYYY-MM-DD')` text produced in SQL (BUG-031 defence), all three `null` when no leaf period is activated; this is the feed for the Welcome period notice title and scope sentence. Guard unchanged (any authenticated session); `GET /api/periods` stays `admin`/`hr`/`c_level`. Live `updatedAt=2026-08-24T18:49:55.486Z`. Report: `docs/EMPLOYEES_PERIOD_META_2026-08-2x.md`.
- **`c_level_only` criteria keep titles and descriptions for everyone; their `level_1_desc`…`level_10_desc` are stripped below `admin`/`c_level`.** `level_0_desc` is outside the stripped list and is empty on both live `c_level_only` rows (ids 1, 10), so nothing leaks through it today. Criteria wording itself was deliberately left unchanged (D-0820-19).
- **Out-of-scope UX.** `/api/employees` returns `actor_is_in_scope`; `TaskStatusContext` drives `OutOfScopeNotice` on Welcome / SelfReview / ManagerEvaluation, and hides «Самооценка», «Оценить руководителя» and the task panel. `NOT_IN_SCOPE` on the submit routes stays as defence.
- **`c_level_direct` is averaged across evaluators (D-0826-1, 2026-08-26).** When more than one
  C-level person scores the same subject on the same criterion in the same period, the value that
  reaches the screen, the payload and the frozen `period_results` is the **mean**, and
  `c_level_count` travels beside it. Nothing was ever lost at write time — the unique index on
  `evaluations` carries `evaluator_id`, so each C-level person has their own row — but both readers
  used to take `ORDER BY e.updated_at DESC LIMIT 1`, so whoever touched their row last decided a
  person's share of the pool on criteria 1 (weight 5.00) and 10 (1.60). One grouped CTE,
  `c_level_direct_scores`, character-for-character identical in `API: evaluations-matrix` and in the
  close dataset of `API: Manage Periods`. An unscored cell reads null score / null count, never a
  zero. Proven on two stands closed side by side: one evaluator moves **zero** of 832 frozen money
  cells; two evaluators move exactly one row, by exactly the hand figure. Report:
  `docs/CLEVEL_AVERAGING_2026-08-26.md`. **A `c_level` score correction on a `c_level_only`
  criterion is still accepted with a 200, stored, and discarded — BUG-073, the owner's call.**
- **`c_level_direct` is enabled** for H1. Writers: role `admin` or `c_level` **with `can_evaluate=true`** — live today that is Alexander (admin id=2), Bayram Urayev (c_level id=18, grade C1), Jemal Gulberdiyeva (c_level id=47, grade C2). Read-only C-level: Cem 21, Hemra 40, Mekan 61 (`can_evaluate=false`). Score-correction now also requires `can_evaluate` (D-0820-7), so the read-only trio get 403 `CAPABILITY_FORBIDDEN` there too. All five c_level accounts and the admin have `can_be_evaluated=false`: C-level evaluates downward and is never a subject.
- **Periods are a hierarchy, and closing one freezes it.** `API: Manage Periods` (`M9ljMDdO1mIl8m1h`, `updatedAt=2026-08-24T06:10:13.683Z`, active, **70 nodes / 8 webhooks**) serves `GET api/periods`, `POST …/create`, `…/activate`, `…/rename`, `…/reparent`, `…/close`, `POST …/start-evaluation`, and `GET …/annual-rollup`. All mutating routes are `admin`-only; the roll-up is `admin` + `c_level`. Reports: `docs/PERIODS_HIERARCHY_2026-08-2x.md`, verified in `docs/PERIODS_VERIFY_2026-08-2x.md`, hardened in `docs/POSTVERIFY_BATCH_2026-08-2x.md`; start-evaluation in `docs/LIFECYCLE_COEFF_2026-08-2x.md`.
- **A period has two gates, not one (2026-08-22, D-0822-1).** «Активировать» makes a leaf period the current one and nothing else — employees see no tasks, every submit route answers 409 `PERIOD_NOT_STARTED`, and the criteria catalogue and all coefficients stay editable. «Запустить оценку» (`POST /api/periods/start-evaluation`, admin-only, migration 014's `evaluation_started_at`) opens the campaign: tasks appear, submits are accepted, and the criteria catalogue freezes with 409 `EVALUATION_STARTED`. Irreversible at product level like activation and close — no route clears the mark, recovery is SQL. Refuses containers (422 `CONTAINER_NOT_STARTABLE`), annual periods (422 `ANNUAL_PERIOD_NOT_STARTABLE`), closed (422 `PERIOD_CLOSED`) and non-active periods (422 `PERIOD_NOT_ACTIVE`); a second call answers 200 `already_started` and writes nothing. `/admin/periods` shows three distinguishable states — «Неактивен» / «Активен · подготовка» / «Идёт оценка» — and the start control is admin-only. **"Campaign period" now means active AND started** on the submit routes, score-correction, and the whole task/status read surface (`/api/employees` flags, check-self-review, check-evaluated, get-my-manager); admin and reporting reads (matrix, analytics, all-evaluations, details-by-user, HR status) stay keyed on **active** alone and are unaffected by the new gate. Registration and authentication are untouched. Report: `docs/LIFECYCLE_COEFF_2026-08-2x.md`.
- **Coefficients are admin-eyes-only and live until close (2026-08-22, D-0822-2).** `GET /api/score-coefficients` is now `admin`-only; `GET /api/criteria` strips `weight` for every non-admin role (the `c_level_only` level-text stripping is unchanged). The self-review no longer fetches coefficients and no longer sends `weighted_score` — the server computes it at submit with formula #2 and the subject's **real** grade coefficient, refusing with 422 `NO_GRADE_COEFFICIENT` rather than falling back to 1.0. The `ACTIVE_PERIOD_EXISTS` 409 is gone from both coefficient write paths; they validate instead (finite, > 0, levels 1..10 — BUG-029 closed). `/admin/scoring`, `/admin/score-calculator`, `/admin/final-scores` and `/admin/bonus-calculation` are admin-only at the route level, and `/admin/scoring` now fails loudly instead of rendering an empty grades table.
- **Migration 014 — `evaluation_periods.evaluation_started_at` / `evaluation_started_by`** on live, both NULL on all three periods (nothing is retroactively started), with `chk_evaluation_periods_started_by_needs_started_at` and an FK on `evaluation_started_by`. Deliberately **not** tied to `status` by a CHECK: close leaves the mark set (a closed period was started — that is history) and the documented emergency stop sets an active period back to draft by SQL; a status-linked CHECK would break both.
- **Close semantics, exactly.** Close is **admin-only**, requires typing the period's name (submit stays disabled until the string matches exactly), and is **irreversible** — there is no reopen route, no route that writes or deletes `period_results`, and activation hard-rejects a closed period. Recovery is a database restore — and since 2026-08-21 there is one to restore from: the previous night's `epe_2026` dump (BUG-032 closed, §2 Backups). Close refuses, in order: not found → 404; container (`child_count > 0`) → 422; already closed **with** results → 200 `already_closed`, zero rows; already closed **without** results → 409; `period_type='annual'` → 422 `ANNUAL_PERIOD_NOT_CLOSABLE`, **independently of child count**; not `active` → 422 `PERIOD_NOT_ACTIVE`; zero participants → 422. The insert and the `status='closed', is_active=false` update are one atomic SQL statement gated on a `FOR UPDATE` target CTE, so a lost race changes zero rows in both. Activation refuses containers and annual periods the same way.
- **Migration 013 — `performance_db.period_results`** exists on live, **empty**, with the exact shape the migration declares: `period_id`, `user_id`, `is_in_scope`, `has_data` (default false) NOT NULL; `rating_manager`, `rating_upward`, `rating_c_level_direct`, `rating_self`, `final_rating`, `bonus_index` nullable numeric; `closed_at` NOT NULL default `now()`; `closed_by` nullable. `PRIMARY KEY (period_id, user_id)`, three foreign keys, index `idx_period_results_user`, and both anti-zero CHECKs on live:
  - `period_results_no_data_is_empty` — `has_data OR (every rating and both money columns IS NULL)`
  - `period_results_out_of_scope_no_data` — `is_in_scope OR NOT has_data`

  A no-data or out-of-scope row therefore **cannot** carry a number: a missing rating can never be read back as a zero, enforced by the database rather than only by the code. `evaluation_periods` carries `parent_period_id` (self-FK), `period_type`, `UNIQUE (name)`, a status CHECK (`draft`/`active`/`closed`), and `chk_evaluation_periods_active_status_consistent` — `(is_active = true) = (status = 'active')`.
- **Annual roll-up.** `/admin/annual-rollup` «Годовые итоги», `ReportingRoute` (admin + c_level), server guard the same. It reads `period_results` **only** — no `evaluations`, `evaluation_scores`, `score_corrections`, `criteria` or `score_coefficients` — so closed numbers survive any later edit of weights or grade coefficients. Annual rating = AVG of persisted finals over in-scope periods with data (no zero-fill; «вне охвата» and «нет данных» shown, excluded from the mean); annual index = SUM of persisted indices. The header states «закрыто N из M дочерних периодов» with each child's date range, so a half-year figure can never sit silently under an annual heading. `role='admin'` subjects are stored but not displayed.
- **Money screens fail loudly.** `useFinalScoresMatrix` runs matrix + coefficients + grades through `Promise.allSettled`, classifies each rejection, clears employees/criteria/period on failure and returns an error card with retry **before** any table renders («Коэффициенты не загружены — расчёт невозможен» / «Коэффициенты грейдов не загружены…» / «Матрица оценок не загружена…»). Until 21 Aug a solo failure rendered a full, plausible, **unweighted** bonus table with no error (BUG-030).
- **`/admin/periods` write controls are admin-only** (`isAdmin(user.role)` / `canManage` gates create, rename, reparent, activate, close). «Создать период» sits behind the same gate as the other four (BUG-037 closed, 2026-08-24).
- **Matrix and all reporting are period-bound.** Default = the single `is_active AND status='active'` period. No active period → 200 empty-state, not mixed Annual 2025 + H1. Optional `?period_id=` inspect on matrix / all-evaluations / analytics / details-by-user / manager-subordinates-matrix.
- **Score-correction is active** and binds only to the ACTIVE period (409 `NO_ACTIVE_PERIOD` otherwise). `mid_level` = the subject's manager's manager (`skip_level_id`); admin / c_level store `c_level`.
- **`detail_type` is a real filter** (`all` / `self` / `received_from_manager` / `from_subordinates` / `gave_to_manager` / `gave_to_subordinates`; unknown → 422).
- **Company-wide reporting audience = admin + c_level.** `ReportingRoute` on `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix`, `/admin/annual-rollup`. HR keeps `/hr/dashboard` and the employee table. Typed `/admin` (criteria) is still `AdminRoute` (BUG-013); its API is admin-only (403).
- **Analytics** is period-bound. Company avg is still `AVG(calculated_score)` over **all sources mixed**.
- **scrypt** (N=16384, r=8, p=1) in registration and login. No plaintext passwords anywhere. **87 of 89 users have `password_hash = NULL`; two are registered:** Alexander (id 2, admin) and Jemal Gulberdiyeva (id 47, c_level). Session rows exist for those two accounts; the count moves with ordinary login and is **not an invariant**. Everyone else registers via the shared invite.
- **One-time password reset** with `token_version` invalidating prior JWTs. Fails closed unless `EPE_FRONTEND_URL` is HTTPS — configured.
- **Login throttling**: 5 failures / 15 min → 15 min lock, generic 401, dummy scrypt for unknown emails. `GET /api/verify-invite` is 600 / 5 min / IP.
- **Shared invite id=4** is reusable (`is_used` stays false), unexpired until **2026-09-18**. Register validator `[A-Za-z0-9_-]{16,128}`; the live token is 43-char base64url.
- **Drafts** on all three launch forms via `epe:evaluation-draft:{evaluator}:{subject}`, 7-day expiry. Logout / 401 do **not** sweep draft keys (D-0820-15, BUG-011).
- **Periods on live — three rows:**

  | id | name | type | status | active | parent | children | participants / in scope |
  |---|---|---|---|---|---|---|---|
  | 1 | Annual 2025 | `annual` | `closed` | false | — | 0 | 0 / 0 |
  | 2 | H1-2026 | `half_year` | `active` | true | **5** | 0 | 89 / **80** |
  | 5 | Annual 2026 | `annual` | `draft` | false | — | **1** | 89 / **86** |

  `evaluation_started_at` / `evaluation_started_by` are **NULL on all three** (re-read 2026-08-25). Nothing is started.

  In scope re-measured **2026-08-25 19:52Z**: H1 **80 of 89**. Nine are out — three terminated by the owner on 2026-08-25 (39, 51, 66 — D-0825-7), two by hire date (31 Esenova, 35 Balova), and four by hand at 18:46Z under D-0825-11 (25 Asatryan, 64 Atayeva, 22 Chariyev, 63 Jumayeva), reason `excluded_by_admin`, reversible by `POST /api/admin/include-participant`. The annual container holds 86: an exclusion from one half-year does not take a person out of the year, so only the three terminated are out of period 5.

  Alexander activated H1 on **2026-08-24 19:07:36Z**. Annual 2026 stays a container — non-activatable, non-closable, both by `child_count` and by `period_type='annual'`. H1 is the active leaf; the remaining gate is «Запустить оценку». Its 89 participant rows are inert until start. Two excluded from H1: Esenova and Balova, hired after 30 June. `evaluation_periods_id_seq` is at 5 with ids 3 and 4 absent — a rejected INSERT still consumes a `nextval`; there is no delete route. Unverified either way, and harmless.
  **Annual 2025 has zero participant rows**, so it can never obtain `period_results`; feeding it to close returns 409. An «Annual 2025» container would render «нет сохранённых результатов» for every person — which is exactly what that cell label was written for.
- **Live data tables are all empty:** `evaluations` 0, `evaluation_scores` 0, `score_corrections` 0, `period_results` 0. Nothing campaign-shaped has been written.
- **Org imported**: 89 users, real hire dates, hierarchy by `Manager's ID`, 0 cycles, 0 people without an evaluator. `can_evaluate` / `can_be_evaluated` as separate columns — the org tree and the evaluation graph are not the same graph. Live roles: 1 admin, 5 c_level, 12 manager, 2 hr, 69 employee.
- Read-only (evaluate nobody, evaluated by nobody): Cem Durukan (21), Mekan Yusupov (61), Hemra Ashyrov (40). All three are **in H1 scope with `grade_id IS NULL` and `manager_id IS NULL`** — decided and left that way, D-0821-4. `API: Submit Evaluation` carries `AND subj.can_be_evaluated = true` in all three relation filters plus an e-mail denylist on the `c_level_direct` branch, so they can never acquire a `manager_score`; `final_rating` and `bonus_index` would persist as NULL, never a coefficient-1.00 money row. That guard has no static test (BUG-039).
- **Classification is Alexander's, and he is editing it.** Live `work_category`: **48 general / 41 project** (`is_project_participant` agrees on every row; zero `tender`). On 2026-08-20 it was 46 / 43 — two people moved to general since. «Тендер» is a leftover UI option and an unused Postgres enum label; `API: Admin Save User` allows only `general` / `project` and answers 422 otherwise. Report: `docs/TENDER_CATEGORY_2026-08-2x.md`.
- **Criteria catalogue: 9 active rows**, all with a positive weight, and 90 `score_coefficients` rows all positive — so the zero-weight trap (BUG-029) is latent, not active. (The ninth, id 14, was created 2026-08-24 through the admin routes with the launch paused; the other eight and all grades stayed byte-identical — `docs/CRITERION9_2026-08-2x.md`.) **20 text fields revised 2026-08-25 (D-0825-1); five level-6 norm labels removed the same day (D-0825-2); latest snapshot `docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md`; catalogue still freezes at «Запустить оценку».**

  | id | title | audience | weight | flags |
  |---|---|---|---|---|
  | 1 | Стратегическая значимость роли | `all` | 5.00 | `c_level_only` |
  | 2 | Качество управления и развитие команды | `managers_only` | 3.00 | `for_manager` |
  | 3 | Личная результативность и эффективность | `all` | 3.00 | self + `for_manager` |
  | 4 | Надежность и взаимодействие с руководителем | `all` | 1.50 | self + `for_manager` |
  | 8 | Взаимодействие и надежность в проекте | `project_participants` | 1.40 | `for_manager` |
  | 10 | Оценка C-Level и соответствие культуре | `all` | 1.60 | `c_level_only` |
  | 12 | Профессиональное развитие и обмен знаниями | `all` | 1.00 | self + `for_manager` |
  | 13 | Объем проектной работы и загрузка | `project_participants` | 1.80 | `for_manager` |
  | 14 | Ответственность сверх роли | `all` | **1.50** (D-0824-2) | `for_manager` |

  Live `score_coefficients`: **90** rows, all positive, minimum **0.30**. Criterion 14's curve is **0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00** and, since **D-0826-2 (owner, 2026-08-26)**, that **is the approved curve** for H1-2026: the earlier `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00` figures in D-0824-2 and `docs/CRITERION9_2026-08-2x.md` are superseded on this point and both carry a banner saying so. **The weight, 1.50, is unchanged.** This is no longer drift and the repository stops calling it that.

  **The money inputs are versioned as of 2026-08-26.** `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md` — nine weights, 90 level coefficients, 11 grade coefficients, read `2026-08-26T04:48:44.986621Z` UTC, with md5 per table (`fc618757…` / `317e09e8…` / `946b30a5…`, combined `079177fb…`) and the SQL to recompute them. It is a photograph, not an approval: if the owner changes a value, the snapshot is retaken (`scripts/snapshot_coefficients.py --label H1-2026`) and a new dated file is written beside it, never edited. **This is the table the pre-gate and pre-close runbooks now compare against.**

- **`docs/CALCULATION_MAP.md`** — done 2026-08-19, read-only, extended 2026-08-21 with §A.1 (`rating_*` are archival per-source summaries of `evaluations.calculated_score`; `final_rating`/`bonus_index` are matrix quantities; the two **will not reconcile, by design**). Every number traced; all 234 archive evaluations recomputed (229 exact, 5 explained). See §4. Later briefs closed most of the period-filter holes named in §4 item 5; that item is preserved as written and is historical.

---
> **Reading §4 below:** it is copied verbatim from the previous HANDOVER and deliberately not edited. Two
> figures inside it are older than this document and are **not** corrected in place: the criteria-count
> distribution ("35 × 3, 11 × 4, 38 × 5, 5 × 6") is the 2026-08-20 measurement — live today is **37 × 4,
> 11 × 5, 36 × 6, 5 × 7** (§6.3, including criterion 14), because Alexander is still editing the classification; and item 5's
> nine unfiltered query families is a 2026-08-19 statement that later briefs largely closed (§3). The
> three formulas themselves are current and are the point of the section.

---

## 4. The most important thing in this document

**The three scoring formulas are intentional. They are not a bug. Do not "fix" them.**

The chat-side architect called this a defect twice and was wrong twice, because it compared three numbers without asking what each measures.

| Formula | What it is | Where |
|---|---|---|
| Plain average of criterion scores | A **rating**, 1–10. Feedback to the person. | Manager / subordinate / c_level_direct |
| Weighted sum ÷ sum of weights, × grade coefficient | Self-review value | Self-review path |
| Weighted sum **without** dividing by sum of weights, × grade coefficient | A **bonus allocation index**, not a rating | Admin matrix / final score |

The missing denominator is deliberate: more criteria means deeper project involvement means a larger share of the bonus pool, because the company earns on projects. Alexander confirmed this directly.

Self-review **never** feeds bonuses. It exists so C-level can spot a large gap between self-rating and manager rating, which signals a problem worth investigating.

What `CALCULATION_MAP.md` (2026-08-19) established — read it before touching any formula:

1. The self-vs-manager comparison is **NOT grade-driven**. The architect's earlier hypothesis (that the gap was driven by grade coefficient) was refuted by the code: every comparison surface shows plain 1–10 vs 1–10. The weighted self value is displayed in one place (own profile, admin/c_level only) and never compared. The gap C-level reads is disagreement. Third architect error on this topic, in the other direction — the verification rule works.
2. The bonus index was **never persisted**. December's index existed only on screen; its inputs (weights, level coefficients, grade coefficients) have been edited since and are unrecoverable. Grade coefficient was provably not applied to December self-reviews (login did not return it; it still doesn't in 2026). Three corrections exist — the matrix was used for calibration.
3. **Nothing is versioned.** Grades, weights, level coefficients, criteria set, hierarchy, `is_project_participant` — all live-joined; editing any of them rewrites history on the next render. This is the argument for a freeze rule (§6.12, proposed).
4. The server validates nothing on the write paths. `final_score` is client-computed and stored as-is; no 1–10 range check on score rows. Five December ratings do not equal the average of their own rows (partial resubmit + upsert).
5. Nine query families have no period filter (profile, matrices, all-evaluations, analytics, details-by-user, …) and `score_corrections` has no period column. Harmless with one period in the DB; every one is an H2 defect.

Because criteria count drives bonus share, the project/general classification is a **money decision**. Distribution today (recomputed from live 2026-08-24, including criterion 14): 37 people × 4 criteria, 11 × 5, 36 × 6, 5 × 7. Editing the classification or the catalogue mid-period silently redistributes the pool.

---

## 5. Decisions taken (do not re-litigate without cause)

- Stay on n8n for H1; rewrite the backend in the H2 window. Deadline beats architecture.
- New database rather than migrating the old one. `epe_2026` with the same schema name means every SQL node works unchanged — one credential change instead of 35 SQL edits. 2025 data becomes physically unreachable for writes.
- Frontend moved off Azure to this host, same origin as the API. Kills CORS, one certificate, deploy is a command not an RDP session.
- Pin n8n by digest, not tag. The `1.121.3` tag was re-pushed and resolves to a different image. Security updates are frozen — revisit at rewrite.
- Everyone gets a new password. The 68 plaintext passwords are treated as compromised.
- Role read live per request, not baked into the token.
- Token lifetime 4h. Drafts persisted client-side + expiry warning to protect half-filled forms.
- **D-0819-1 Annual aggregation** (Alexander): rating = mean of periods in scope; bonus index = sum of period indices (pro-rata); self-review never aggregated. Confirmed and made concrete by D-0821-3.
- Alexander sets the project/general classification himself in the portal's employees table before launch — `admin-users-data` and `admin/save-user` are in the H1 guarded batch for that reason.
- Invitation language: English; Alexander writes and sends it himself, one email to the company-wide address. Supersedes the wave plan.
- Launch routes left active after acceptance; period state is the only campaign switch.
- Shared invite token is reusable; register does not burn `is_used` (D-0820-6).
- `c_level_direct` enabled for H1; writers admin + c_level with `can_evaluate` (D-0820-7).
- No outbound mail except `alexander@sedamedical.com` unless he confirms the recipient (D-0820-8).
- Corrections bind to the ACTIVE period only (D-0820-9).
- `mid_level` = the subject's manager's manager (D-0820-10).
- Company-wide reporting audience = admin + c_level; HR keeps evaluation-status (D-0820-11).
- Final cell = mean(manager, mid?, c_level?) — mid_level counts (D-0820-12).
- `detail_type` is a real filter (D-0820-13).
- H1 stays active through September calibration (D-0820-14).
- Drafts persist in localStorage; no logout sweep for H1 (D-0820-15).
- **Visibility and copy, 2026-08-20 evening (Alexander, D-0820-16 … D-0820-21):** the manager sees the subordinate's **real** self-review, nothing hidden; subject-visible results are **sealed on the server** until a separate release decision; manager dashboard status flags are real, not the HR route's 403 fallback; `c_level_only` **level texts** are admin/c_level-only while the criteria wording stays unchanged; out-of-scope people get an explicit notice instead of dead task links; defects found on the way are fixed immediately rather than filed.
- Containers are non-activatable reporting constructs (D-0821-1).
- Close-time result persistence — `period_results`, atomic, immutable, never-zero (D-0821-2). This upgrades what was §6.13 "proposed" to decided and shipped.
- Annual display: out-of-scope excluded from the mean, index is a sum (D-0821-3).
- **The read-only trio (21 / 40 / 61) stays in H1 scope with no invented grades** (D-0821-4). They are September readers, not H1 writers; `can_be_evaluated=false` keeps them out of every money number.
- **C-level direct evaluations are averaged across evaluators, with the count carried** (D-0826-1, 2026-08-26). Last-writer-wins is gone from that channel. Made before the gate with zero evaluation rows, so nothing was migrated. §3 for the mechanics.
- **The criterion-14 level curve on live is the approved curve for H1-2026, and the coefficient tables are snapshotted** (D-0826-2, 2026-08-26). D-0824-2's amendment and `CRITERION9` are superseded on that point only; the weight 1.50 stands. Also confirmed in the same decision: **the bonus index is built from the manager channel and `c_level_direct` alone** — the upward channel and self-assessment are feedback surfaces and do not feed money, so criterion 2 «Качество управления» (weight 3.00) is scored in the money by the manager's own boss alone. Intentional, and consistent with §4.

---

## 6. Open — Alexander

**Activate is done; these are the things only he can settle.** The campaign itself still waits on «Запустить оценку».

1. **When to start the evaluation.** Nothing in the system holds a date. Since 2026-08-22 this is **two** clicks in Admin → Периоды, not one (D-0822-1): «Активировать» (done 2026-08-24 19:07:36Z) opened the preparation window — H1 is the current period, employees still see nothing, and the catalogue and coefficients stay editable — and «Запустить оценку» opens the campaign itself, irreversibly. The emergency stop is unchanged: the executor sets H1 back to draft by SQL, which needs his Mac (and which also stops the campaign, because every submit route requires `status='active'` as well as the start mark).
2. **The invitation.** He writes and sends it himself, in English, to the company-wide `@sedamedical.com` address. Separate two-line note to Cem Durukan, Mekan Yusupov, Hemra Ashyrov: they submit nothing in H1; their results/calibration views open later. Esenova and Balova get the general email; they are out of H1 scope by hire date and will see no tasks.
3. **Finish the project/general classification** of the 89 in Admin → Сотрудники — ideally before activating, but since 2026-08-24 (D-0822-3) this is no longer a hard gate: classification stays editable during the campaign, a switch never destroys evaluation data (project-criteria rows are soft-excluded and return on switch-back), and a general→project switch reopens the manager's task for exactly the missing criteria. It is still a money decision — criteria count drives bonus share. Live today: 48 general / 41 project. Criteria count per person (incl. criterion 14 «Ответственность сверх роли», audience `all`, since 2026-08-24): 37 people × 4, 11 × 5, 36 × 6, 5 × 7.
4. **Second admin for launch day?** Today only Alexander is admin, and only he can close a period. Recommendation unchanged: do not create a standing second admin — admin = access to HR data and money inputs. If he may be unavailable, temporarily give admin to one HR specialist for the day (role is live, no re-login) and revert.
5. **Off-host backup target** (Timeweb S3, write-only key) — outstanding since 13 Aug (BUG-014), and now the *only* remaining backup gap: BUG-032 is closed, so `epe_2026` and the n8n backend are in the daily on-host job as of 2026-08-21. The stakes rose with the fix — one disk on one VPS now holds the live campaign database, the n8n backend and every backup of both. He needs to name a target; `N8N_ENCRYPTION_KEY` (Portainer env var, in no dump) should go somewhere he can reach if the VPS is gone.
6. **Change the admin password** (Keychain `EPE auth test password reset 2026-08-18` still 401 on live login) — BUG-015, "later".
7. **Publish Google Workspace DKIM** (`google._domainkey.sedamedical.com`). Test mail already passes SPF/DKIM/DMARC and lands in Inbox — optional.
8. **Which number was used for the December 2025 bonus** — the on-screen index, or the ratings? The DB cannot answer (the index was never stored). Decides whether formula #3 is the definition of "index" in D-0819-1. Needed before H1 results, not before launch.
9. Confirm Amangozel = Enesha Bayramgeldiyeva (grade A) and Merdan Rasulov's carried S1.
10. Whether employees see their 2025 score in the new portal (recommended: as a copied closed period, after the first cycle lands).
11. **The catalogue freeze — decided 2026-08-22 (D-0822-1 / D-0822-2), and the earlier premise here was wrong.** This item used to say the freeze was enforced for classification and coefficients "but **not** for weights". Measured against live on 2026-08-22 (`docs/RECON_RECLASS_COEFF_2026-08-2x.md` §2.4), there was no unfrozen write path to any weight: all three producers — `API: Save Score Coefficients`, `API: Manage Criteria Admin V7`, `API: Update Admin Data` — sat behind the same `ACTIVE_PERIOD_EXISTS` 409, which fired on **activation**, the earliest possible moment and the widest possible freeze. What is now decided splits that single switch in two: the **criteria catalogue** freezes when the evaluation **starts** (not when the period is activated), so draft and the preparation window are both editable; **weights, level coefficients and grade coefficients** are editable **until close** with the 409 removed entirely and per-value validation in its place (weights finite and ≥ 0.1 since the 2026-08-24 D-0822-2 amendment; level and grade coefficients finite and > 0; levels 1..10 — this is what closed BUG-029); **classification** stays editable during a running campaign (D-0822-3, 2026-08-24) — the first-submission `CLASSIFICATION_FROZEN` 409 is gone, replaced by server-side applicability. The real residue of BUG-010 was never editability: it is that everything stays **live-joined until close**, so an edit made before activation or after close re-renders history. That half of BUG-010 is still open, and `period_results` is what bounds it — closed periods no longer re-join these tables. Report: `docs/LIFECYCLE_COEFF_2026-08-2x.md`.
12. **How the frozen index gets spent in September.** Once H1 closes there is no active period, so Итоговые баллы, Калькуляция бонусов and the matrix all render empty, and `bonus_index` is visible only on Годовые итоги — which has no budget, point-value or payout field (BUG-033). Either a period selector or reading `period_results` on the money screens. Needed in September, not in August.
13. **What a `c_level` score correction means against an averaged C-level score (BUG-073).** Today the correction route accepts one on criteria 1 and 10 with a 200, stores it, shows it in the payload, and every consumer discards it — measured on a stand 2026-08-26, the frozen index was byte-identical with and without it. Three options, costed in `docs/CLEVEL_AVERAGING_2026-08-26.md` §3: the correction **replaces** the mean, it **joins** the mean as one more opinion (which is what corrections already do on the manager path), or the route **refuses** `c_level_only` criteria by name. The third can ship before the other two are decided and would make the API honest today. `score_corrections` is empty on live, so nothing is wrong yet; it becomes wrong the first time somebody calibrates criterion 1.
14. **Results-visibility release (D-0820-17 / BUG-025), scoped by D-0824-3.** When subjects see results they received from their manager. That later decision is **manager → subordinate only**. Upward scores and comments a subordinate writes about their manager are never shown to that manager, now or after any release.

---

## 7. Next work, in order

Done 19–25 Aug, accepted reports through `WELCOME_PERIOD_NOTICE`, `EMPLOYEES_PERIOD_META`, `CATALOGUE_FIX_H1`, `PRELAUNCH_GUIDE_AND_ZONES`. Pre-flight verdict: H1 can be started — **yes**, no blockers on the remaining gate.

**Activate is done** (2026-08-24 19:07:36Z). The row reads «Активен · подготовка»; «В охвате 87 / 89»; employees still see no tasks, by design.

**Remaining, in order:**

1. Classification finished (§6.3) if anything is left — still editable (D-0822-3). Invitation sent (§6.2). Finish the catalogue and the coefficients if anything remains. **Runbook before «Запустить оценку»:** compare the nine live weights, 90 level coefficients and eleven grade coefficients against **`docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`** — one command, `python3 scripts/snapshot_coefficients.py --label H1-2026`, and the three md5 sums in the new file must equal the three in that one. It supersedes the CRITERION9 and RECON appendices as the reference (D-0826-2). If the owner has deliberately changed a value, the snapshot is retaken and the new file becomes the reference. Then **Запустить оценку** (irreversible, typed confirmation dialog): check one manager sees tasks and one employee sees the self-review. Annual 2025 and Annual 2026 show neither control.
2. During the campaign: no brief needed unless something breaks. Watch the registration count and the first submissions. Leave H1 **active** through September calibration (D-0820-14).
3. Close H1 only after calibration is quiet — typed confirmation, admin-only, irreversible, and **the close staleness guard counts evaluations but cannot see an edit to an existing one or a fresh correction**, so close when nothing is in flight. **Runbook before close:** the same comparison against the dated coefficient snapshot as in step 1.

**September queue** — mirrored from the leftovers of the accepted reports, none of it needed on activation day:

| Item | Source | Row |
|---|---|---|
| Off-host copy of the dumps (the live DB is in the daily job since 21 Aug — BUG-032 closed) | 21 Aug hygiene / BACKUP_FIX | BUG-014 |
| A screen that can spend the frozen `bonus_index` after close (period selector, or read `period_results`) | PERIODS_VERIFY M3 | BUG-033 |
| Catalogue freeze / per-period **versioning** of weights, coefficients, classification (coefficient-table versioning) | PERIODS_VERIFY M5 / D-0824-2 | BUG-010 |
| Audit log for coefficient writes (who / when / old→new) — the coefficients route has none | D-0824-2 | candidate, no row |
| `useScoreCalculation` still substitutes an empty coefficient set on failure | LIFECYCLE_COEFF | BUG-042 |
| Nine stale top-level `n8n_workflows/` exports (named BUG-028 instance is current) | GATE_RECLASS / GATE_FINALIZE | BUG-045 |
| Migration chain cannot rebuild live `score_corrections` (`period_id` in no migration) | CRITERION9 | BUG-050 |
| Guard contract fail-opens on an omitted `required_roles` — default-deny or a lint | PERIODS_VERIFY | BUG-038 |
| Static test for `can_be_evaluated` on Submit Evaluation; end-to-end coverage for the `c_level_only` and corrections branches of `finalOf` | POSTVERIFY_BATCH / PERIODS_VERIFY | BUG-039 |
| `deploy_epe_frontend.sh` needs `rg` on PATH or it fails closed | POSTVERIFY_BATCH | BUG-040 |
| Employee-route period filters on `my-profile` and `evaluation-history` | REPORTING_SURFACE | BUG-009 |
| `/team` calls an admin-only API; typed `/admin` still `AdminRoute` for HR; login-time foreign-draft sweep | earlier briefs | BUG-012, BUG-013, BUG-011 |
| 15 npm advisories (11 high, 3 moderate, 1 low) — re-measured 2026-08-24 | `npm audit` | BUG-016 |
| BUG-008 invite audit (only matters with a second admin) | LAUNCH_PREP | BUG-008 |
| Stale Keychain admin password | DRESS_REHEARSAL | BUG-015 |
| Azure VM `135.232.120.40` RDP :3389 still public | TLS_CUTOVER 2026-08-19; **not re-probed** 24 Aug | triaged, no row |
| Legacy domains `bk.sedamedical.com` (measured 19 Aug) / `assessment.sedamedical.com` (2026-08-24: A `216.250.12.243`, 80/443/8080 connection refused — does not serve EPE) | TLS_CUTOVER; PRELAUNCH_COPY_BATCH | triaged, no row |
| Archive the stray `My workflow 10` so the "3 inactive" baseline means something | PERIODS_VERIFY | triaged, no row |
| Which figure paid the December 2025 bonus (on-screen index vs ratings) | §6.8 | — |
| Results-visibility release — when subjects see **manager → subordinate** results (upward never, D-0824-3) | D-0820-17 / D-0824-3 / BUG-025 | — |
| Whether 2025 scores display in the new portal | §6.10 | — |
| HR / manager methodology consultation before H2 | architect queue 2026-08-24 | — |
| Phase 3 rewrite off n8n in the H2 window | AGENTS.md | — |

---

## 8. How this project is run

**Alexander** — business owner, not a developer. Decides. Reads explanations, not code. Wants a recommendation with its cost, not a menu. Enforces phase order and holds it: sysadmin → diagnostics → anchoring → questions → milestones → detail. **He sets the dates; the system enforces none of them.**

**The architect (this chat)** has no code, server, or database access. It produces hypotheses, decisions, methodology, and copy-pasteable briefs. It must never state a fact about the codebase as if verified.

Alexander's standing rules for the architect (19 Aug): no step-by-step instructions to the executors — they see the code, the architect does not; set context, outcome, boundaries, acceptance criteria, what to surface; then check the report, correct, approve. Update this HANDOVER only at session handover, not after every step. Do not re-litigate the three formulas (§4).

The executors in Cursor have full code and server access. Available: GPT-5.6 Sol (xhigh), Fable 5, Opus 5, Grok 4.6. Brief them with outcome, boundaries, and acceptance criteria — not steps. State explicitly what they must surface for a decision rather than resolve silently. Model choice per brief: long agentic build-and-prove work → Sol; read-only comprehension with numeric proof → Fable/Opus; mechanical follow-ups → Grok.

**Mail (Alexander, 20 Aug):** executors must not send any message except to `alexander@sedamedical.com` unless he has confirmed the recipient in that conversation. This includes n8n verification codes and SMTP tests. D-0820-8.

**Evidence standard, established and working:** deterministic fingerprint of the 2025 database before and after every operation; dumps verified by actual restore into a throwaway DB, not by parsing; idempotency proven by a second run changing zero rows; rehearsal on a restored copy before touching the target. The throwaway-stand pattern and its ports are in `PROJECT_RULES.md`.

**A verification pass is worth its cost.** `PERIODS_VERIFY` accepted the periods build but named seven microfixes, two of which — a silently unweighted bonus screen and a date comparison that would have refused the canonical September H2 attach — were real money-or-schedule defects. Neither was visible from the build report alone.

### Traps that already cost time

- `ufw` does not filter Docker-published ports. Rules go in `DOCKER-USER`.
- iptables rules do not survive reboot unless persisted.
- Disabling SSH password auth before confirming key login = losing the host.
- "Preserve every env var byte-for-byte" was read as including image-inherited ones (`NODE_VERSION`); cost a day.
- A failed cosmetic check is not data damage. Stop and ask **before** restoring a healthy database.
- Alexander's home IP changes. Anything allowlisted by IP will silently break. SSH tunnel instead.
- The architect's formula hypotheses were wrong three times. Verify against code before acting on any of them.
- An "end-to-end registration proof" is not permission to email employees.
- Auth Guard "unchanged" is `updatedAt`, not a GET-body md5. The same GET serializes to more than one md5.
- **The n8n Postgres node returns `date` columns as UTC-serialised JS `Date` objects.** In Europe/Moscow `String(v).slice(0,10)` yields the previous calendar day. Never compare a client `YYYY-MM-DD` against a date that crossed that node — decide containment in SQL (BUG-031).
- **`docker cp <dir> container:/path` nests** when the target exists, so an import re-reads the previous file. Two diagnoses were made against a stand silently running old code.
- **`n8n import:workflow` always assigns a new workflow id** — the file's `id` is ignored, so a stand accumulates duplicates. Verify the active definition node-for-node before trusting a proof.
- **A tracked export is not the truth.** `n8n_workflows/API_ evaluations-matrix.json` has 4 nodes; live has 9. Read live `workflow_entity`, or regenerate.
- **A proof artifact that records a slogan proves nothing.** `api_proof.json`'s `cross_check` was the bare string "stored final/index match…"; a run that compared nothing would have written it just as happily. Record the compared tuples and fail on a vacuous run.

---

## 9. When to start a new Cursor session

**The repo is the memory, not the session.** Every brief ends with a report in `docs/`; that report is what survives. This is why reports are mandatory.

Start a new session:

- **After each completed brief with its report written.** One brief, one session. This is the default rhythm.
- **When the work changes kind** — infrastructure → data → auth → routes. Old context stops helping and starts biasing.
- **After a rollback, a failed path, or a long debugging detour.** That context is noise now.
- **When you see the model re-reading files it already read**, contradicting its own earlier findings, or hedging on things it proved two hours ago. That is context saturation.

Do **not** start a new session:

- **Mid-brief.** Live SSH multiplexing, verified state, and in-flight facts are lost.
- **Between a change and its verification.** Finish the proof first.

When you do start fresh, point it at `AGENTS.md`, this file, and the specific report from the previous step. Nothing else — a fresh session reading eight reports is as saturated as the one you just closed.

---

## 10. Where things are (repo `docs/`)

Reports, in order: `AUTHENTICATION_CORE_2026-08-18.md` · `TLS_CUTOVER_2026-08-19.md` · `CALCULATION_MAP.md` (read §4 of this file first) · `ROUTE_GUARD_H1_2026-08-19.md` · `LAUNCH_PREP_2026-08-19.md` · `MAIL_AND_RUNBOOK_2026-08-19.md` · `THROTTLE_RAISE_2026-08-20.md` · `SHARED_INVITE_2026-08-20.md` · `DRESS_REHEARSAL_2026-08-2x.md` · `COSMETIC_PRELAUNCH_2026-08-2x.md` · `ROUTE_GUARD_DEFERRED_2026-08-2x.md` · `CLEVEL_DIRECT_ENABLE_2026-08-2x.md` · `MATRIX_CALIBRATION_FIX_2026-08-2x.md` · `REPORTING_SURFACE_2026-08-2x.md` · `DRAFTS_UX_2026-08-2x.md` · `DOCS_HYGIENE_2026-08-2x.md` · `USER_FACING_COPY_2026-08-2x.md` · `PRELAUNCH_FIXES_2026-08-2x.md` · `PREFLIGHT_H1_2026-08-2x.md` · `ADMIN_USERS_SORT_2026-08-2x.md` · `TENDER_CATEGORY_2026-08-2x.md` · `PERIODS_HIERARCHY_2026-08-2x.md` · `PERIODS_VERIFY_2026-08-2x.md` · `POSTVERIFY_BATCH_2026-08-2x.md` · `BACKUP_FIX_2026-08-2x.md` · `DOCS_HYGIENE_2026-08-21.md` · `RECON_RECLASS_COEFF_2026-08-2x.md` · `LIFECYCLE_COEFF_2026-08-2x.md` · `GATE_LIFECYCLE_COEFF_2026-08-2x.md` · `RECLASS_2026-08-2x.md` (closes BUG-044) · `GATE_RECLASS_2026-08-2x.md` (files BUG-045/046/047) · `FINALIZE_PRELAUNCH_2026-08-2x.md` (corrections applicability, BUG-046/047 closed, new-criterion path verified) · `GATE_FINALIZE_2026-08-2x.md` (gate on the finalization batch; files BUG-048/049) · `CRITERION9_2026-08-2x.md` (BUG-048 closed by D-0824-1, BUG-049 closed, BUG-050 filed; the ninth criterion — id 14 «Ответственность сверх роли» — created and proven on live the same day, once the texts document arrived). · `BROWSER_WALKTHROUGH_2026-08-2x.md` (the campaign UI walked end-to-end in a real browser on a stand — the last «not browser-driven» debt retired; BUG-052 fixed and deployed, BUG-051/053 filed). · `PRELAUNCH_FIX_BATCH_2026-08-2x.md` (BUG-051 matrix alignment fixed+deployed with browser proof and money reconciled to the digit; BUG-053 `/tmp` dumps cleaned with md5-verified local copies; refresh check answered — no bug; the criterion-14 weight found moved 1.5→2.0 on live by an admin edit, surfaced). · `PRELAUNCH_COPY_BATCH_2026-08-2x.md` (BUG-034/035/036/037 closed on the frontend and deployed; visibility copy mapped to HANDOVER §3; self-review add-criteria control removed). · `WELCOME_PERIOD_NOTICE_2026-08-2x.md` (period-aware Welcome notice; owner visibility wording restored; D-0824-3; upward-channel seal verified). · `EMPLOYEES_PERIOD_META_2026-08-2x.md` (period name + dates on `/api/employees`). · `CATALOGUE_FIX_H1_2026-08-25.md` (20 catalogue fields written on live). · `PRELAUNCH_GUIDE_AND_ZONES_2026-08-25.md` (in-product rating guide; score bands treat 6 as first «хорошо»). · `TERMINATED_EMPLOYEES_2026-08-25.md` (D-0825-7) · `ADMIN_USERS_FILTERS_2026-08-25.md` (D-0825-8) · `MID_YEAR_HIRES_SCOPE_2026-08-25.md` + `MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md` (D-0825-10; the hand-exclusion route) · **`PRELAUNCH_BATCH_NIGHT_2026-08-26.md`** — the four post-31-March hires taken out of H1 (D-0825-11), a NULL hire date out of scope from the next period on (D-0825-12), «a half-year pays nothing» on Welcome and in the rating guide (D-0825-13), the period state on /admin/users, /admin/final-scores verified then fixed, the bonus budget actually distributed and the pool defined by a predicate (D-0825-14), and the day-one walk (D-0825-15, BUG-069/070/071). · **`CLEVEL_AVERAGING_2026-08-26.md`** — `c_level_direct` is averaged across evaluators with the count carried (D-0826-1, BUG-072 closed); the collision question answered for all four channels; a `c_level` correction on a `c_level_only` criterion measured to be accepted and discarded (BUG-073 filed, the owner's call); the criterion-14 curve on live declared approved (D-0826-2) and the coefficient tables photographed as `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`.

Operational: `LAUNCH_RUNBOOK_H1.md` (Alexander's one page), `INVITATION_WAVES.md` (now "single send"). Maps: `SERVER_MAP.md`, `FRONTEND_MAP.md`, `API_CONTRACT.md`, `CALCULATION_MAP.md`. Briefs: `docs/briefs/`. Decisions: `DECISIONS.md` (single register; `PROJECT_DECISIONS.md` is a pointer). Bugs: `bugs.md` (**29 open / 44 closed**, recounted 2026-08-26 after CLEVEL_AVERAGING — which closed BUG-072, the defect it fixed, and filed BUG-073. Before it: **28 open / 43 closed** after PRELAUNCH_BATCH_NIGHT — 28 `🔴 OPEN` / 43 `🟢 CLOSED`. Since the 16/37 reading: BUG-040/051/052/053 and 063 closed, BUG-054…068 filed by the termination, filter, team-page and mid-year briefs, and this session closed BUG-066 (forward-looking) and BUG-069 and filed BUG-070/071). Progress: `PROGRESS.md`. Ports, names, the throwaway-stand pattern and the one-session rule: `PROJECT_RULES.md`. Migrations: `migrations/001…016` (015 employment termination, 016 the append-only period-scope log).

**`docs/EVALUATION_METHODOLOGY.md` does not exist.** `AGENTS.md` calls it the business contract Alexander owns — role groups, criteria, weights, scale, aggregation, calibration — and says code conforms to it, never the reverse. There is no such file anywhere in the repo, and there never has been. A draft v1.0 exists outside the repository (chat-side architect, 2026-08-24) and is pending the owner's approval of four wording points; on approval it is committed verbatim as docs/EVALUATION_METHODOLOGY.md with a DECISIONS.md row. Until then the de facto contract remains HANDOVER §3–§4. Do not create the file.

A new Cursor session gets: `AGENTS.md`, this file, and the one report relevant to its brief. Nothing else.
