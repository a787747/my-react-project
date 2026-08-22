# EPE — Handover

**As of:** 2026-08-21 (after docs hygiene; eight accepted briefs after the previous HANDOVER) · **Launch: PAUSED**
**Alexander paused the H1 launch on 2026-08-21.** The 31 August start date, the 26 August invitation and every
other date in this document are **his** to set or move — nothing in the system enforces them. H1 is still
`draft`/`is_active=false`; no campaign date is coded anywhere. When he lifts the pause, §7 is the order of work.

**Later the same day**, the backup brief (`docs/BACKUP_FIX_2026-08-2x.md`) closed BUG-032 and changed the
facts in §2 Backups, §6 item 5, §7 close semantics and the September queue; those four places are updated and
post-date the 08:40 UTC snapshot below.

Every number in §§1–3 and §§5–10 was re-measured against the live system on 2026-08-21 08:21–08:40 UTC,
read-only (SELECT / GET / `readlink` / `openssl`). **§4 is copied verbatim from the previous HANDOVER and was
not edited.** Reports were used to locate claims, never as the source of a fact — see
`docs/DOCS_HYGIENE_2026-08-21.md` for the live-vs-report differences this pass found.

---

## 1. What the system is

Employees Performance Evaluation for SEDA Medical Turkmenistan. 89 people. React SPA + n8n as the entire backend + PostgreSQL.

It ran exactly one cycle: a single annual period, "Annual Review 2025", 234 evaluations all dated December 2025. It has never run a half-year cycle. The season goal — H1 → H2 → annual aggregation — is new capability, not a repeat.

Evaluation is multi-source: self-review, manager→subordinate, subordinate→manager (upward), and c_level_direct. Criteria are role-differentiated via `criteria.target_audience`. Two-level correction (`mid_level`, `c_level`) exists as a calibration layer.

Since 2026-08-21 periods form a **hierarchy**: a half-year period may hang under an annual **container**, and closing a half-year period **freezes** its per-person results into `period_results` so the annual roll-up never has to recompute them. That is the mechanism the season goal was missing.

---

## 2. Current state — infrastructure

| Thing | State (live, 2026-08-21) |
|---|---|
| Host | `92.51.45.147`, Timeweb VPS, root via SSH key (password auth disabled, fail2ban on). Up 8 days |
| Public origin | `https://epe.sedamedical.com` — Caddy (`epe-proxy-caddy-1`) serves portal + `/webhook/*` → n8n |
| Certificate | Let's Encrypt (`YE1`), `notBefore` 2026-08-19, `notAfter` **2026-11-17** |
| n8n | pinned by digest `sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, `restart=unless-stopped`, running, port 5678 DROP from `eth0` |
| Live DB | `epe_2026`, schema `performance_db`, own credential `EPE 2026 Postgres` |
| Archived DB | `postgres.performance_db` — 2025 data, **read-only forever**. This session by SELECT: **73 users, 234 evaluations, 644 scores, 3 corrections**. Fingerprint not re-hashed today (no dump taken); last computed `21d323b0…` in `docs/DRAFTS_UX_2026-08-2x.md` |
| Databases on `postgres_n8n` | **`epe_2026` and `postgres` only** — every throwaway stand DB is gone |
| Frontend | This host. Current release **`20260821T072859Z`**. 14 releases on disk (previous: `20260821T060049Z`, `20260820T165040Z`, `20260820T154749Z`, …). Deploy: `./scripts/deploy_epe_frontend.sh` |
| Azure VM | `135.232.120.40`, untouched fallback, still serves the old build on :8080 |
| Firewall | `DOCKER-USER` → `EPE-DOCKER-USER` (ufw does not filter Docker ports). 80/443 open; 5432/5431/8000/9000/2377/7946/4789 restricted to one allowlisted IP; 5678 DROP on `eth0`. **The allowlisted source is a single home IP (`188.137.254.191`) that changes — use the SSH tunnel, not the allowlist** |
| Portainer | Reachable only via SSH tunnel `127.0.0.1:29000` |
| Backups | **Two daily jobs since 2026-08-21.** 03:00 MSK `backup-performance-db.sh` → the 2025 archive (`postgres -n performance_db`), unchanged, 10 dumps. 03:20 MSK `backup-epe-live.sh` → **`epe_2026` in full** and the **n8n application schema** (`postgres -n public`: 58 workflows, 7 credentials, 8 settings), neither of which had any backup before that date. 14-day stem-scoped prune on both; failure = non-zero exit + `FAIL` in `backup.log` and in `backup-epe-live.status` (no MTA on the host, so that file is the alarm). Restore-proven the same day: 17/17 and 52/52 tables row-matched from a cron-produced dump. BUG-032 **closed**, `docs/BACKUP_FIX_2026-08-2x.md`. **Off-host copy still missing (BUG-014)** — one disk now holds live, n8n and every backup of both |

Workflows: **58 total** = **33 active** + 3 inactive unarchived (`EPE: Auth Guard`, `API: Global CORS Handler`, `My workflow 10`) + **22 archived**. **41** registered webhooks (19 GET / 20 POST / 2 OPTIONS).

Active set (live names, 2026-08-21 — identical to the 2026-08-20 set):

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

The set has not changed since 20 Aug; the webhook count rose 37 → 41 because `API: Manage Periods` grew from 3 to 7 routes. CORS stays inactive. `Get Employee Self Review` and `Get Admin Data Fixed` are confirmed **absent** from `workflow_entity` (deleted; GET 404). H1 is still draft/inactive — nothing campaign-shaped can be written until it is activated.

`My workflow 10` is an unnamed stray in the inactive-unarchived three. Archiving it would make the "3 inactive" baseline mean something; nobody has.

---

## 3. Current state — what is built

- **Real authentication.** JWT (HS256, 4h, claims `sub/iss/aud/iat/exp/jti` only). Role and capabilities read live from DB per request; the guard ignores any role claim in the token. Proven: no token / forged / expired / wrong role / forbidden capability all rejected.
- **`EPE: Auth Guard`** — one reusable execute-workflow sub-workflow. **Canonical check: `updatedAt=2026-08-18T16:34:30.674Z`, `active=false`** — re-read live today, unchanged since 18 Aug through every PUT since. GET-body md5 is **not** canonical: the same GET serializes to more than one hash. Identity from token only. Migration 012: `period_id` mandatory, uniqueness `(subject, evaluator, source, period)` and `(subject, period)`, at most one active period. `work_category` canonical, `is_project_participant` derived atomically; classification and coefficient writes return 409 after the first submission in the active period.
- **Subject-side visibility is enforced on the server, not in the browser.** This was the opposite a week ago and is the single largest change of 20 Aug. `API: My Profile V5` attaches `score`/`calculated_score`/`weighted_score` only to self rows and computes profile stats from self-evaluations alone; `API: Get Evaluation Details FIXED` returns a row only to the evaluator, to `admin`/`c_level`, or to the subject of their **own** self-evaluation — anything else is 404. Upward evaluator identity is nulled to the subject. HR is **not** privileged here (D-0820-11). Report: `docs/PRELAUNCH_FIXES_2026-08-2x.md`, re-verified against live definitions in `docs/PREFLIGHT_H1_2026-08-2x.md`.
- **The manager form serves the subordinate's real self-review.** `API: Check Self Review` honours `user_id` when it is the actor, a direct report, or any subject for `admin`/`c_level`; anything else silently falls back to the actor's own row (no 403, no leak). Before 20 Aug it showed the manager their own self-review labelled as the subordinate's — BUG-024.
- **Manager dashboard statuses are real.** Completion flags (`has_self_review`, `has_evaluated_manager`, `evaluated_by_actor`) ride on `/api/employees`; the dashboard no longer calls the HR-only status route and no longer reports every subordinate as having done nothing.
- **`c_level_only` criteria keep titles and descriptions for everyone; their `level_1_desc`…`level_10_desc` are stripped below `admin`/`c_level`.** `level_0_desc` is outside the stripped list and is empty on both live `c_level_only` rows (ids 1, 10), so nothing leaks through it today. Criteria wording itself was deliberately left unchanged (D-0820-19).
- **Out-of-scope UX.** `/api/employees` returns `actor_is_in_scope`; `TaskStatusContext` drives `OutOfScopeNotice` on Welcome / SelfReview / ManagerEvaluation, and hides «Самооценка», «Оценить руководителя» and the task panel. `NOT_IN_SCOPE` on the submit routes stays as defence.
- **`c_level_direct` is enabled** for H1. Writers: role `admin` or `c_level` **with `can_evaluate=true`** — live today that is Alexander (admin id=2), Bayram Urayev (c_level id=18, grade C1), Jemal Gulberdiyeva (c_level id=47, grade C2). Read-only C-level: Cem 21, Hemra 40, Mekan 61 (`can_evaluate=false`). Score-correction now also requires `can_evaluate` (D-0820-7), so the read-only trio get 403 `CAPABILITY_FORBIDDEN` there too. All five c_level accounts and the admin have `can_be_evaluated=false`: C-level evaluates downward and is never a subject.
- **Periods are a hierarchy, and closing one freezes it.** `API: Manage Periods` (`M9ljMDdO1mIl8m1h`, `updatedAt=2026-08-21T07:28:10.039Z`, active, **61 nodes / 7 webhooks**) serves `GET api/periods`, `POST …/create`, `…/activate`, `…/rename`, `…/reparent`, `…/close`, and `GET …/annual-rollup`. All mutating routes are `admin`-only; the roll-up is `admin` + `c_level`. Reports: `docs/PERIODS_HIERARCHY_2026-08-2x.md`, verified in `docs/PERIODS_VERIFY_2026-08-2x.md`, hardened in `docs/POSTVERIFY_BATCH_2026-08-2x.md`.
- **Close semantics, exactly.** Close is **admin-only**, requires typing the period's name (submit stays disabled until the string matches exactly), and is **irreversible** — there is no reopen route, no route that writes or deletes `period_results`, and activation hard-rejects a closed period. Recovery is a database restore — and since 2026-08-21 there is one to restore from: the previous night's `epe_2026` dump (BUG-032 closed, §2 Backups). Close refuses, in order: not found → 404; container (`child_count > 0`) → 422; already closed **with** results → 200 `already_closed`, zero rows; already closed **without** results → 409; `period_type='annual'` → 422 `ANNUAL_PERIOD_NOT_CLOSABLE`, **independently of child count**; not `active` → 422 `PERIOD_NOT_ACTIVE`; zero participants → 422. The insert and the `status='closed', is_active=false` update are one atomic SQL statement gated on a `FOR UPDATE` target CTE, so a lost race changes zero rows in both. Activation refuses containers and annual periods the same way.
- **Migration 013 — `performance_db.period_results`** exists on live, **empty**, with the exact shape the migration declares: `period_id`, `user_id`, `is_in_scope`, `has_data` (default false) NOT NULL; `rating_manager`, `rating_upward`, `rating_c_level_direct`, `rating_self`, `final_rating`, `bonus_index` nullable numeric; `closed_at` NOT NULL default `now()`; `closed_by` nullable. `PRIMARY KEY (period_id, user_id)`, three foreign keys, index `idx_period_results_user`, and both anti-zero CHECKs on live:
  - `period_results_no_data_is_empty` — `has_data OR (every rating and both money columns IS NULL)`
  - `period_results_out_of_scope_no_data` — `is_in_scope OR NOT has_data`

  A no-data or out-of-scope row therefore **cannot** carry a number: a missing rating can never be read back as a zero, enforced by the database rather than only by the code. `evaluation_periods` carries `parent_period_id` (self-FK), `period_type`, `UNIQUE (name)`, a status CHECK (`draft`/`active`/`closed`), and `chk_evaluation_periods_active_status_consistent` — `(is_active = true) = (status = 'active')`.
- **Annual roll-up.** `/admin/annual-rollup` «Годовые итоги», `ReportingRoute` (admin + c_level), server guard the same. It reads `period_results` **only** — no `evaluations`, `evaluation_scores`, `score_corrections`, `criteria` or `score_coefficients` — so closed numbers survive any later edit of weights or grade coefficients. Annual rating = AVG of persisted finals over in-scope periods with data (no zero-fill; «вне охвата» and «нет данных» shown, excluded from the mean); annual index = SUM of persisted indices. The header states «закрыто N из M дочерних периодов» with each child's date range, so a half-year figure can never sit silently under an annual heading. `role='admin'` subjects are stored but not displayed.
- **Money screens fail loudly.** `useFinalScoresMatrix` runs matrix + coefficients + grades through `Promise.allSettled`, classifies each rejection, clears employees/criteria/period on failure and returns an error card with retry **before** any table renders («Коэффициенты не загружены — расчёт невозможен» / «Коэффициенты грейдов не загружены…» / «Матрица оценок не загружена…»). Until 21 Aug a solo failure rendered a full, plausible, **unweighted** bonus table with no error (BUG-030).
- **`/admin/periods` write controls are admin-only** (`isAdmin(user.role)` gates rename, reparent, activate, close). «Создать период» in the page header is still rendered for c_level/HR and answers 403 — the one write control left visible to a non-admin there (BUG-037).
- **Matrix and all reporting are period-bound.** Default = the single `is_active AND status='active'` period. No active period → 200 empty-state, not mixed Annual 2025 + H1. Optional `?period_id=` inspect on matrix / all-evaluations / analytics / details-by-user / manager-subordinates-matrix.
- **Score-correction is active** and binds only to the ACTIVE period (409 `NO_ACTIVE_PERIOD` otherwise). `mid_level` = the subject's manager's manager (`skip_level_id`); admin / c_level store `c_level`.
- **`detail_type` is a real filter** (`all` / `self` / `received_from_manager` / `from_subordinates` / `gave_to_manager` / `gave_to_subordinates`; unknown → 422).
- **Company-wide reporting audience = admin + c_level.** `ReportingRoute` on `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix`, `/admin/annual-rollup`. HR keeps `/hr/dashboard` and the employee table. Typed `/admin` (criteria) is still `AdminRoute` (BUG-013); its API is admin-only (403).
- **Analytics** is period-bound. Company avg is still `AVG(calculated_score)` over **all sources mixed**.
- **scrypt** (N=16384, r=8, p=1) in registration and login. No plaintext passwords anywhere. **87 of 89 users have `password_hash = NULL`; two are registered:** Alexander (id 2, admin) and Jemal Gulberdiyeva (id 47, c_level). `auth_sessions`: 6 rows, 2 distinct users, 1 unexpired. Everyone else registers via the shared invite.
- **One-time password reset** with `token_version` invalidating prior JWTs. Fails closed unless `EPE_FRONTEND_URL` is HTTPS — configured.
- **Login throttling**: 5 failures / 15 min → 15 min lock, generic 401, dummy scrypt for unknown emails. `GET /api/verify-invite` is 600 / 5 min / IP.
- **Shared invite id=4** is reusable (`is_used` stays false), unexpired until **2026-09-18**. Register validator `[A-Za-z0-9_-]{16,128}`; the live token is 43-char base64url.
- **Drafts** on all three launch forms via `epe:evaluation-draft:{evaluator}:{subject}`, 7-day expiry. Logout / 401 do **not** sweep draft keys (D-0820-15, BUG-011).
- **Periods on live — three rows:**

  | id | name | type | status | active | parent | children | participants / in scope |
  |---|---|---|---|---|---|---|---|
  | 1 | Annual 2025 | `annual` | `closed` | false | — | 0 | 0 / 0 |
  | 2 | H1-2026 | `half_year` | `draft` | false | **5** | 0 | 89 / **87** |
  | 5 | Annual 2026 | `annual` | `draft` | false | — | **1** | 89 / 89 |

  Alexander performed the designated UX walk-through on 21 Aug: he created **Annual 2026** (2026-01-01 → 2026-12-31) and attached H1 to it. Annual 2026 is therefore a container — non-activatable, non-closable, both by `child_count` and by `period_type='annual'`. H1 remains a leaf and remains activatable. Its 89 participant rows are inert (`Build Create SQL` seeds participants for every new period and cannot know it will become a container). Two excluded from H1: Esenova and Balova, hired after 30 June. `evaluation_periods_id_seq` is at 5 with ids 3 and 4 absent — a rejected INSERT still consumes a `nextval`; there is no delete route. Unverified either way, and harmless.
  **Annual 2025 has zero participant rows**, so it can never obtain `period_results`; feeding it to close returns 409. An «Annual 2025» container would render «нет сохранённых результатов» for every person — which is exactly what that cell label was written for.
- **Live data tables are all empty:** `evaluations` 0, `evaluation_scores` 0, `score_corrections` 0, `period_results` 0. Nothing campaign-shaped has been written.
- **Org imported**: 89 users, real hire dates, hierarchy by `Manager's ID`, 0 cycles, 0 people without an evaluator. `can_evaluate` / `can_be_evaluated` as separate columns — the org tree and the evaluation graph are not the same graph. Live roles: 1 admin, 5 c_level, 12 manager, 2 hr, 69 employee.
- Read-only (evaluate nobody, evaluated by nobody): Cem Durukan (21), Mekan Yusupov (61), Hemra Ashyrov (40). All three are **in H1 scope with `grade_id IS NULL` and `manager_id IS NULL`** — decided and left that way, D-0821-4. `API: Submit Evaluation` carries `AND subj.can_be_evaluated = true` in all three relation filters plus an e-mail denylist on the `c_level_direct` branch, so they can never acquire a `manager_score`; `final_rating` and `bonus_index` would persist as NULL, never a coefficient-1.00 money row. That guard has no static test (BUG-039).
- **Classification is Alexander's, and he is editing it.** Live `work_category`: **48 general / 41 project** (`is_project_participant` agrees on every row; zero `tender`). On 2026-08-20 it was 46 / 43 — two people moved to general since. «Тендер» is a leftover UI option and an unused Postgres enum label; `API: Admin Save User` allows only `general` / `project` and answers 422 otherwise. Report: `docs/TENDER_CATEGORY_2026-08-2x.md`.
- **Criteria catalogue: 8 active rows**, all with a positive weight, and 80 `score_coefficients` rows all positive — so the zero-weight trap (BUG-029) is latent, not active.

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

- **`docs/CALCULATION_MAP.md`** — done 2026-08-19, read-only, extended 2026-08-21 with §A.1 (`rating_*` are archival per-source summaries of `evaluations.calculated_score`; `final_rating`/`bonus_index` are matrix quantities; the two **will not reconcile, by design**). Every number traced; all 234 archive evaluations recomputed (229 exact, 5 explained). See §4. Later briefs closed most of the period-filter holes named in §4 item 5; that item is preserved as written and is historical.

---
> **Reading §4 below:** it is copied verbatim from the previous HANDOVER and deliberately not edited. Two
> figures inside it are older than this document and are **not** corrected in place: the criteria-count
> distribution ("35 × 3, 11 × 4, 38 × 5, 5 × 6") is the 2026-08-20 measurement — live today is **37 × 3,
> 11 × 4, 36 × 5, 5 × 6** (§6.3), because Alexander is still editing the classification; and item 5's
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

Because criteria count drives bonus share, the project/general classification is a **money decision**. Distribution today: 35 people × 3 criteria, 11 × 4, 38 × 5, 5 × 6. Editing the classification or the catalogue mid-period silently redistributes the pool.

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

---

## 6. Open — Alexander

**Launch is paused; these are the things only he can settle.**

1. **When to lift the pause.** Nothing in the system holds a date. Activating H1 is one click in Admin → Периоды (`LAUNCH_RUNBOOK_H1.md`); the emergency stop is the executor setting H1 back to draft by SQL, which needs his Mac.
2. **The invitation.** He writes and sends it himself, in English, to the company-wide `@sedamedical.com` address. Separate two-line note to Cem Durukan, Mekan Yusupov, Hemra Ashyrov: they submit nothing in H1; their results/calibration views open later. Esenova and Balova get the general email; they are out of H1 scope by hire date and will see no tasks.
3. **Finish the project/general classification** of the 89 in Admin → Сотрудники **before** activating — those writes return 409 once a period is active. Live today: 48 general / 41 project, and moving. Criteria count per person, and therefore bonus share: 37 people × 3, 11 × 4, 36 × 5, 5 × 6.
4. **Second admin for launch day?** Today only Alexander is admin, and only he can close a period. Recommendation unchanged: do not create a standing second admin — admin = access to HR data and money inputs. If he may be unavailable, temporarily give admin to one HR specialist for the day (role is live, no re-login) and revert.
5. **Off-host backup target** (Timeweb S3, write-only key) — outstanding since 13 Aug (BUG-014), and now the *only* remaining backup gap: BUG-032 is closed, so `epe_2026` and the n8n backend are in the daily on-host job as of 2026-08-21. The stakes rose with the fix — one disk on one VPS now holds the live campaign database, the n8n backend and every backup of both. He needs to name a target; `N8N_ENCRYPTION_KEY` (Portainer env var, in no dump) should go somewhere he can reach if the VPS is gone.
6. **Change the admin password** (Keychain `EPE auth test password reset 2026-08-18` still 401 on live login) — BUG-015, "later".
7. **Publish Google Workspace DKIM** (`google._domainkey.sedamedical.com`). Test mail already passes SPF/DKIM/DMARC and lands in Inbox — optional.
8. **Which number was used for the December 2025 bonus** — the on-screen index, or the ratings? The DB cannot answer (the index was never stored). Decides whether formula #3 is the definition of "index" in D-0819-1. Needed before H1 results, not before launch.
9. Confirm Amangozel = Enesha Bayramgeldiyeva (grade A) and Merdan Rasulov's carried S1.
10. Whether employees see their 2025 score in the new portal (recommended: as a copied closed period, after the first cycle lands).
11. **The catalogue freeze.** Proposed by the architect, still not decided: during an active period and until its results are stored, no edits to `grades.coefficient`, criteria, `score_coefficients`, `users.is_project_participant`. For H1 this is de facto enforced for classification and coefficients (409 while a period is active) but **not** for weights — and until a period is closed every money screen is live-joined (BUG-010). This is now the only remaining half of that bug.
12. **How the frozen index gets spent in September.** Once H1 closes there is no active period, so Итоговые баллы, Калькуляция бонусов and the matrix all render empty, and `bonus_index` is visible only on Годовые итоги — which has no budget, point-value or payout field (BUG-033). Either a period selector or reading `period_results` on the money screens. Needed in September, not in August.

---

## 7. Next work, in order

Done 19–21 Aug, all accepted with reports: `CALCULATION_MAP.md` · `ROUTE_GUARD_H1` · `LAUNCH_PREP` · `MAIL_AND_RUNBOOK` · `THROTTLE_RAISE` · `SHARED_INVITE` · `DRESS_REHEARSAL` · `COSMETIC_PRELAUNCH` · `ROUTE_GUARD_DEFERRED` · `CLEVEL_DIRECT_ENABLE` · `MATRIX_CALIBRATION_FIX` · `REPORTING_SURFACE` · `DRAFTS_UX` · `DOCS_HYGIENE_2026-08-2x` · `USER_FACING_COPY` · `PRELAUNCH_FIXES` · `PREFLIGHT_H1` · `ADMIN_USERS_SORT` · `TENDER_CATEGORY` · `PERIODS_HIERARCHY` · `PERIODS_VERIFY` · `POSTVERIFY_BATCH`. Pre-flight verdict: H1 can be activated — **yes**, no blockers.

**While paused:** nothing needs a brief. If the pause runs long, the only thing that decays is the certificate (17 Nov) and the invite token (18 Sep).

**On the day he lifts the pause:**

1. Classification finished (§6.3), invitation sent (§6.2), then Admin → Периоды → Активировать. Check «В охвате 87 / 89», one manager sees tasks, one employee sees self-review. Annual 2025 and Annual 2026 show no Activate control.
2. During the campaign: no brief needed unless something breaks. Watch the registration count and the first submissions. Leave H1 **active** through September calibration (D-0820-14).
3. Close H1 only after calibration is quiet — typed confirmation, admin-only, irreversible, and **the close staleness guard counts evaluations but cannot see an edit to an existing one or a fresh correction**, so close when nothing is in flight.

**September queue** — mirrored from the leftovers of the accepted reports, none of it needed on activation day:

| Item | Source | Row |
|---|---|---|
| Off-host copy of the dumps (the live DB is in the daily job since 21 Aug — BUG-032 closed) | this hygiene pass | BUG-014 |
| A screen that can spend the frozen `bonus_index` after close (period selector, or read `period_results`) | PERIODS_VERIFY M3 | BUG-033 |
| Catalogue freeze / per-period versioning of weights, coefficients, classification | PERIODS_VERIFY M5 | BUG-010 |
| `Number.isFinite(w) && w >= 0` on both sides of the weight and grade-coefficient defaults | PERIODS_VERIFY §1 | BUG-029 |
| Refresh the stale top-level `API_ evaluations-matrix.json` export (4 nodes vs live's 9) | PERIODS_HIERARCHY | BUG-028 |
| `AdminUsers` status circles never load (`setLoadingStatuses` has no state) | ADMIN_USERS_SORT §6 | BUG-034 |
| `errorHandler.js` overwrites 401/403/429 server messages, so `CAPABILITY_FORBIDDEN` reads as the generic «Доступ запрещен» | PRELAUNCH_FIXES | BUG-035 |
| §4.8 copy-vs-behaviour rows 2, 3, 7, 8, 9, 10 — including «Оценить новые критерии», which always 409s | USER_FACING_COPY / PRELAUNCH_FIXES | BUG-036 |
| «Создать период» still visible to c_level/HR | POSTVERIFY_BATCH | BUG-037 |
| Guard contract fail-opens on an omitted `required_roles` — default-deny or a lint | PERIODS_VERIFY | BUG-038 |
| Static test for `can_be_evaluated` on Submit Evaluation; end-to-end coverage for the `c_level_only` and corrections branches of `finalOf` | POSTVERIFY_BATCH / PERIODS_VERIFY | BUG-039 |
| `deploy_epe_frontend.sh` needs `rg` on PATH or it fails closed | POSTVERIFY_BATCH | BUG-040 |
| Employee-route period filters on `my-profile` and `evaluation-history` | REPORTING_SURFACE | BUG-009 |
| `/team` calls an admin-only API; typed `/admin` still `AdminRoute` for HR; login-time foreign-draft sweep | earlier briefs | BUG-012, BUG-013, BUG-011 |
| 15 npm advisories (11 high) | `npm audit` | BUG-016 |
| BUG-008 invite audit (only matters with a second admin) | LAUNCH_PREP | BUG-008 |
| Stale Keychain admin password | DRESS_REHEARSAL | BUG-015 |
| Archive the stray `My workflow 10` so the "3 inactive" baseline means something | PERIODS_VERIFY | triaged, no row |
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

Reports, in order: `AUTHENTICATION_CORE_2026-08-18.md` · `TLS_CUTOVER_2026-08-19.md` · `CALCULATION_MAP.md` (read §4 of this file first) · `ROUTE_GUARD_H1_2026-08-19.md` · `LAUNCH_PREP_2026-08-19.md` · `MAIL_AND_RUNBOOK_2026-08-19.md` · `THROTTLE_RAISE_2026-08-20.md` · `SHARED_INVITE_2026-08-20.md` · `DRESS_REHEARSAL_2026-08-2x.md` · `COSMETIC_PRELAUNCH_2026-08-2x.md` · `ROUTE_GUARD_DEFERRED_2026-08-2x.md` · `CLEVEL_DIRECT_ENABLE_2026-08-2x.md` · `MATRIX_CALIBRATION_FIX_2026-08-2x.md` · `REPORTING_SURFACE_2026-08-2x.md` · `DRAFTS_UX_2026-08-2x.md` · `DOCS_HYGIENE_2026-08-2x.md` · `USER_FACING_COPY_2026-08-2x.md` · `PRELAUNCH_FIXES_2026-08-2x.md` · `PREFLIGHT_H1_2026-08-2x.md` · `ADMIN_USERS_SORT_2026-08-2x.md` · `TENDER_CATEGORY_2026-08-2x.md` · `PERIODS_HIERARCHY_2026-08-2x.md` · `PERIODS_VERIFY_2026-08-2x.md` · `POSTVERIFY_BATCH_2026-08-2x.md` · `DOCS_HYGIENE_2026-08-21.md` (this pass).

Operational: `LAUNCH_RUNBOOK_H1.md` (Alexander's one page), `INVITATION_WAVES.md` (now "single send"). Maps: `SERVER_MAP.md`, `FRONTEND_MAP.md`, `API_CONTRACT.md`, `CALCULATION_MAP.md`. Briefs: `docs/briefs/`. Decisions: `DECISIONS.md` (single register; `PROJECT_DECISIONS.md` is a pointer). Bugs: `bugs.md` (**20 open / 21 closed**). Progress: `PROGRESS.md`. Ports, names, and the throwaway-stand pattern: `PROJECT_RULES.md`. Migrations: `migrations/001…013`.

**`docs/EVALUATION_METHODOLOGY.md` does not exist.** `AGENTS.md` calls it the business contract Alexander owns — role groups, criteria, weights, scale, aggregation, calibration — and says code conforms to it, never the reverse. There is no such file anywhere in the repo, and there never has been. The catalogue in §3 and the formulas in §4 are the de facto contract. Writing the real one is Alexander's call, not an executor's; until then a "divergence from the methodology" cannot be checked against anything.

A new Cursor session gets: `AGENTS.md`, this file, and the one report relevant to its brief. Nothing else.
