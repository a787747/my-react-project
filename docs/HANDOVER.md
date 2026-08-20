# EPE — Handover

**As of:** 2026-08-20 (after docs hygiene; six accepted briefs after the previous HANDOVER) · **H1 campaign start:** 2026-08-31 · **7 working days left**
**Aug 31 is the campaign START date, not the results date.** Results land mid-to-late September. This was explicitly confirmed by Alexander.

---

## 1. What the system is

Employees Performance Evaluation for SEDA Medical Turkmenistan. 89 people. React SPA + n8n as the entire backend + PostgreSQL.

It ran exactly one cycle: a single annual period, "Annual Review 2025", 234 evaluations all dated December 2025. It has never run a half-year cycle. The season goal — H1 → H2 → annual aggregation — is new capability, not a repeat.

Evaluation is multi-source: self-review, manager→subordinate, subordinate→manager (upward), and c_level_direct. Criteria are role-differentiated via `criteria.target_audience`. Two-level correction (`mid_level`, `c_level`) exists as a calibration layer.

---

## 2. Current state — infrastructure

| Thing | State |
|---|---|
| Host | `92.51.45.147`, Timeweb VPS, root via SSH key (password auth disabled, fail2ban on) |
| Public origin | `https://epe.sedamedical.com` — Caddy serves portal + `/webhook/*` → n8n |
| Certificate | Let's Encrypt (`YE1`), valid 2026-08-19 → 2026-11-17, auto-renewal previously verified |
| n8n | 1.121.3, **pinned by digest** `sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, `restart=unless-stopped`, port 5678 closed to internet |
| Live DB | `epe_2026`, schema `performance_db`, own credential `EPE 2026 Postgres` |
| Archived DB | `postgres.performance_db` — 2025 data, **read-only forever**. This session: 73 users, 234 evaluations, 644 scores, 3 corrections. Full fingerprint last computed in `docs/DRAFTS_UX_2026-08-2x.md` (`21d323b0…`); not re-hashed today |
| Frontend | This host. Current release **`20260820T065435Z`**. Previous on disk: `20260820T063333Z`. Deploy: `./scripts/deploy_epe_frontend.sh` |
| Azure VM | `135.232.120.40`, untouched fallback, still serves old build on :8080 |
| Firewall | `DOCKER-USER` chain (ufw does not filter Docker ports). 80/443 open; 5432/5431/8000/9000/2377/7946 restricted; 5678 DROP from `eth0` |
| Portainer | Reachable only via SSH tunnel `127.0.0.1:29000` |
| Backups | Daily on-host, 14 days, restore-verified. **Off-host copy still missing** |

Workflows: **58 total** = **33 active** + 3 inactive unarchived (`EPE: Auth Guard`, `API: Global CORS Handler`, `My workflow 10`) + **22 archived**. **37** registered webhooks.

Active set (live names, 2026-08-20):

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

That is the launch set plus matrix, score-correction, and the five remaining reporting routes (all-evaluations, analytics, details-by-user, manager-subordinates-matrix, manage-criteria) plus update-admin-data. CORS stays inactive. `Get Employee Self Review` and `Get Admin Data Fixed` are deleted (GET 404). H1 period is still draft/inactive — nothing campaign-shaped can be written until it is activated.

---

## 3. Current state — what is built

- **Real authentication.** JWT (HS256, 4h, claims `sub/iss/aud/iat/exp/jti` only). Role and capabilities read live from DB per request; the guard ignores any role claim in the token. Proven: no token / forged / expired / wrong role / forbidden capability all rejected; valid token used `sub` and ignored a conflicting `user_id` in the request.
- **`EPE: Auth Guard`** — one reusable execute-workflow sub-workflow. **Canonical check: `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` (execute-workflow).** GET-body md5 is not canonical: earlier reports quoted `de58de075d66a621e832aac9a2dd3d14`, `docs/REPORTING_SURFACE_2026-08-2x.md` quoted `6ea30fc47b8f51180a4b963fdae79732` from a different serialization of the same GET; `updatedAt` did not move. Applied to the launch routes and the reporting/calibration routes. Identity from token only. Migration 012: `period_id` mandatory, uniqueness `(subject, evaluator, source, period)` and `(subject, period)`, at most one active period. Subjects never see `private_comment`; upward evaluator identity hidden from the subject. Admin + all C-level exempt from self-review. `work_category` canonical, `is_project_participant` derived atomically; classification and coefficient writes return 409 after the first submission in the active period.
- **`c_level_direct` is enabled** for H1. Writers: role `admin` or `c_level`; evaluator = token actor; same plain AVG as manager. C-level / admin writers with `can_evaluate=true`: Alexander (admin id=2), Bayram Urayev (c_level id=18), **Jemal Gulberdiyeva (c_level id=47)**. Read-only C-level: Cem 21, Hemra 40, Mekan 61. Report: `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md`.
- **Shared invite id=4** is reusable (`is_used` stays false). Register validator is `[A-Za-z0-9_-]{16,128}` (live token is 43-char base64url). Report: `docs/SHARED_INVITE_2026-08-20.md`. `GET /api/verify-invite` is 600 / 5 min / IP. Report: `docs/THROTTLE_RAISE_2026-08-20.md`.
- **Drafts** on all three launch forms via `epe:evaluation-draft:{evaluator}:{subject}`, 7-day expiry: self-review, upward, manager→subordinate. Logout / 401 do **not** sweep draft keys. Report: `docs/DRAFTS_UX_2026-08-2x.md`.
- **Matrix and all reporting are period-bound.** Default = the single `is_active AND status='active'` period. No active period → 200 empty-state, not mixed Annual 2025 + H1. Optional `?period_id=` inspect on matrix / all-evaluations / analytics / details-by-user / manager-subordinates-matrix. Empty-state copy is on those screens and on Итоговые баллы / Калькуляция бонусов / Калькуляция баллов. Reports: `docs/MATRIX_CALIBRATION_FIX_2026-08-2x.md`, `docs/REPORTING_SURFACE_2026-08-2x.md`.
- **Score-correction is active.** Writes bind only to the ACTIVE period (`is_active AND status='active'`). Draft POST → 409 `NO_ACTIVE_PERIOD`. `mid_level` = the subject’s manager’s manager (`skip_level_id`). Admin / c_level store `c_level`.
- **`detail_type` is a real filter** (`all` / `self` / `received_from_manager` / `from_subordinates` / `gave_to_manager` / `gave_to_subordinates`; unknown → 422).
- **Company-wide reporting audience = admin + c_level.** `ReportingRoute` on `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix`. HR keeps `/hr/dashboard` (`hr/evaluation-status`) and the employee table; company-wide dossier buttons hidden. Typed `/admin` (criteria) is still `AdminRoute`; API is admin-only (403).
- **Analytics** is period-bound. Company avg is still `AVG(calculated_score)` over **all sources mixed** (self + manager + upward + …). `period_trends` is 0–1 row for the shown period.
- **scrypt** (N=16384, r=8, p=1) in registration and login. No plaintext passwords anywhere. 88 of 89 users have `password_hash = NULL`; Alexander (id=2) is the only registered user. Everyone else registers via the shared invite.
- **One-time password reset** with `token_version` invalidating prior JWTs. Fails closed unless `EPE_FRONTEND_URL` is HTTPS — now configured.
- **Login throttling**: 5 failures / 15 min → 15 min lock, generic 401, dummy scrypt for unknown emails.
- **Periods**: id=1 Annual 2025 (closed), id=2 H1-2026 (`half_year`, draft, **inactive**). `evaluation_period_participants`: 87 in scope, 2 excluded (Esenova, Balova — hired after 30 June). **H1 stays draft until 31 Aug.** After launch it stays `active` through September calibration (D-0820-14).
- **Org imported**: 89 users, real hire dates, hierarchy by `Manager's ID`, 0 cycles, 0 people without an evaluator. `can_evaluate` / `can_be_evaluated` as separate columns — the org tree and the evaluation graph are not the same graph.
- Read-only (evaluate nobody, evaluated by nobody): Cem Durukan, Mekan Yusupov, Hemra Ashyrov. C-level evaluates downward but is never a subject; upward evaluation does not reach C-level.
- **`docs/CALCULATION_MAP.md`** — done 2026-08-19, read-only. Every number traced; all 234 archive evaluations recomputed (229 exact, 5 explained). See §4. Later briefs closed most of the period-filter holes named in §4 item 5; that item is preserved as written and is historical.

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
- Pin n8n by digest, not tag. The `1.121.3` tag was re-pushed and resolves to a different image; recreating would have pulled an unknown build. Security updates are frozen — revisit at rewrite.
- Everyone gets a new password. The 68 plaintext passwords are treated as compromised.
- Role read live per request, not baked into the token.
- Token lifetime 4h (executor proposed 12; shortened because the endpoint was plain HTTP at the time). Drafts persisted client-side + expiry warning to protect half-filled forms.
- **D-0819-1 Annual aggregation** (2026-08-19, Alexander): rating = mean of periods in scope; bonus index = sum of period indices (pro-rata); self-review never aggregated.
- Alexander sets the project/general classification himself in the portal's employees table before launch — `admin-users-data` and `admin/save-user` join the H1 guarded batch for that reason.
- Invitation language: English; Alexander writes and sends the invitation himself, one email to the company-wide address (26 Aug). Supersedes the wave plan.
- Launch routes left active after acceptance (Alexander, 19 Aug); period state is the only campaign switch.
- Shared invite token is reusable; register does not burn `is_used` (D-0820-6).
- `c_level_direct` enabled for H1; writers admin + c_level (D-0820-7).
- Corrections bind to the ACTIVE period only (D-0820-9).
- `mid_level` = the subject’s manager’s manager (D-0820-10).
- Company-wide reporting audience = admin + c_level; HR keeps evaluation-status (D-0820-11).
- Final cell = mean(manager, mid?, c_level?) — mid_level counts (D-0820-12).
- `detail_type` is a real filter (D-0820-13).
- H1 stays active through September calibration (D-0820-14).
- Drafts persist in localStorage; no logout sweep for H1 (D-0820-15).
- No outbound mail except `alexander@sedamedical.com` unless he confirms the recipient (D-0820-8).

---

## 6. Open — Alexander

**Blocking before 26 Aug (invitation email):**

1. ~~Raise the verify-invite throttle~~ **Done** (600 / 5 min / IP). Shared token id=4 is reusable; register accepts the live base64url token.
2. Alexander writes and sends the invitation himself, in English, to the company-wide `@sedamedical.com` address. Architect's English draft is in the chat log of 19 Aug (subject "EPE — register for the H1 2026 performance review by 28 August"). Send in the morning of a working day. Separate two-line note to Cem Durukan, Mekan Yusupov, Hemra Ashyrov: they submit nothing in H1; their results/calibration views open in September. Esenova and Balova get the general email; they are out of H1 scope by hire date and will see no tasks.

**Before 28–29 Aug:** 3. Project classification of the 89 by name in Admin → Сотрудники (43 project today). Freezes after the first real submission (409). Alexander said he will do it himself; remind on 26 Aug. 4. Second admin for launch day? Today only Alexander is admin. Architect's recommendation: do not create one — admin = access to HR data and money inputs; the real fallback is the executor activating H1 by SQL, which needs Alexander's Mac anyway. If Alexander may be unavailable on the morning of 31 Aug: temporarily give admin to one HR specialist for the day (role is live, no re-login) and revert. Undecided.

**Not blocking:** 5. Off-host backup target (Timeweb S3, write-only key) — outstanding since 13 Aug; "later". 6. Change the admin password (Keychain `EPE auth test password reset 2026-08-18` still 401 on live login) — "later". 7. Publish Google Workspace DKIM (`google._domainkey.sedamedical.com`). Test mail already passes SPF/DKIM/DMARC (Google signs with its `gappssmtp.com` domain) and lands in Inbox — so optional, do when convenient. 8. Which number was used for the December 2025 bonus — AdminFinalScores/BonusCalculation index on screen, or the ratings? The DB cannot answer (index never stored). Decides whether formula #3 is the definition of "index" in D-0819-1. Needed before H1 results (mid-Sept), not before launch. 9. Confirm Amangozel = Enesha Bayramgeldiyeva (grade A) and Merdan Rasulov's carried S1. 10. Whether employees see their 2025 score in the new portal (recommended: September, copied closed period). 11. ~~Whether `mid_level` corrections count in the final cell~~ **Decided yes** (D-0820-12). 12. Proposed by the architect, not decided — freeze rule: during an active period and until its results are exported and stored, no edits to `grades.coefficient`, criteria, `score_coefficients`, `users.is_project_participant`. For H1 this is de facto enforced (409 on coefficient/classification/criteria writes while a period is active). 13. Proposed, not decided — persist period results (rating per source + bonus index per person) at period close. Without it D-0819-1 cannot be applied: nothing to sum, as December showed. Do this **after launch**, with the remaining employee-route period filters (`my-profile`, `evaluation-history`).

---

## 7. Next work, in order

Done 19–20 Aug, all accepted with reports: `CALCULATION_MAP.md` · `ROUTE_GUARD_H1` · `LAUNCH_PREP` · `MAIL_AND_RUNBOOK` · `THROTTLE_RAISE_2026-08-20.md` · `SHARED_INVITE_2026-08-20.md` · `DRESS_REHEARSAL_2026-08-2x.md` · `COSMETIC_PRELAUNCH_2026-08-2x.md` · `ROUTE_GUARD_DEFERRED_2026-08-2x.md` · `CLEVEL_DIRECT_ENABLE_2026-08-2x.md` · `MATRIX_CALIBRATION_FIX_2026-08-2x.md` · `REPORTING_SURFACE_2026-08-2x.md` · `DRAFTS_UX_2026-08-2x.md`. Dress rehearsal verdict: ready for 31 Aug — **yes**.

1. **26 Aug** — Alexander sends the invitation (§6.2). Registration badge in Admin → Сотрудники shows progress; expected before: registered = 1.
2. **28–29 Aug** — project classification of the 89 (§6.3).
3. **31 Aug morning** — Alexander activates H1 (Admin → Периоды → Активировать, see `LAUNCH_RUNBOOK_H1.md`); checks «В охвате 87 / 89», one manager sees tasks, one employee sees self-review. Emergency stop = executor sets H1 back to draft by SQL (no button; needs Alexander's Mac). Annual 2025 Activate is hidden (`status === 'closed'`).
4. During the campaign: no brief needed unless something breaks. Watch registration count and first submissions. Leave H1 **active** through September calibration.

After launch / September, none on day one: **persist-period-results** at period close (§6.13); **employee-route period filters** on `my-profile` and `evaluation-history` (check-self-review / check-evaluated / get-my-manager already bind to the active period); **login-time foreign-draft sweep** (logout/401 leave `epe:evaluation-draft:*` keys); **`/team` admin-only API defect** (`TeamView` → `admin-users-data`, managers get an empty/error list); **typed `/admin` for HR** (still `AdminRoute`; API 403, sidebar already hides Критерии); **off-host backup**; **stale Keychain admin password**; **15 npm advisories (11 high)**; BUG-008 invite audit (only matters with a second admin); 2025 scores visible to employees as a copied closed period (§6.10); Phase 3 rewrite off n8n in the H2 window.

---

## 8. How this project is run

**Alexander** — business owner, not a developer. Decides. Reads explanations, not code. Wants a recommendation with its cost, not a menu. Enforces phase order and holds it: sysadmin → diagnostics → anchoring → questions → milestones → detail.

**The architect (this chat)** has no code, server, or database access. It produces hypotheses, decisions, methodology, and copy-pasteable briefs. It must never state a fact about the codebase as if verified.

Alexander's standing rules for the architect (19 Aug): no step-by-step instructions to the executors — they see the code, the architect does not; set context, outcome, boundaries, acceptance criteria, what to surface; then check the report, correct, approve. Update this HANDOVER only at session handover, not after every step. Do not re-litigate the three formulas (§4).

The executors in Cursor have full code and server access. Available: GPT-5.6 Sol (xhigh), Fable 5, Opus 5, Grok 4.6. Brief them with outcome, boundaries, and acceptance criteria — not steps. They choose their own route and are better at code than the architect. State explicitly what they must surface for a decision rather than resolve silently. Model choice per brief: long agentic build-and-prove work → Sol; read-only comprehension with numeric proof → Fable/Opus; mechanical follow-ups → Grok.

**Mail (Alexander, 20 Aug):** executors must not send any message except to `alexander@sedamedical.com` unless he has confirmed the recipient in that conversation. This includes n8n verification codes and SMTP tests. D-0820-8.

**Evidence standard, established and working:** deterministic fingerprint of the 2025 database before and after every operation; dumps verified by actual restore into a throwaway DB, not by parsing; idempotency proven by a second run changing zero rows; rehearsal on a restored copy before touching the target.

### Traps that already cost time

- `ufw` does not filter Docker-published ports. Rules go in `DOCKER-USER`.
- iptables rules do not survive reboot unless persisted.
- Disabling SSH password auth before confirming key login = losing the host (no console access).
- "Preserve every env var byte-for-byte" was read as including image-inherited ones (`NODE_VERSION`); triggered an unnecessary rollback and cost a day. Separate operator-set from image-inherited.
- A failed cosmetic check is not data damage. Stop and ask **before** restoring a healthy database.
- Alexander's home IP changes. Anything allowlisted by IP will silently break. SSH tunnel instead.
- The architect's formula hypotheses were wrong three times. Verify against code before acting on any of them.
- An “end-to-end registration proof” is not permission to email employees. Only `alexander@sedamedical.com` unless he names another mailbox.
- Auth Guard “unchanged” is `updatedAt`, not a GET-body md5. The same GET serializes to more than one md5.

---

## 9. When to start a new Cursor session

**The repo is the memory, not the session.** Every brief ends with a report in `docs/`; that report is what survives. This is why reports are mandatory.

Start a new session:

- **After each completed brief with its report written.** One brief, one session. This is the default rhythm.
- **When the work changes kind** — infrastructure → data → auth → routes. Old context stops helping and starts biasing.
- **After a rollback, a failed path, or a long debugging detour.** That context is noise now and the model will keep referring to it.
- **When you see the model re-reading files it already read**, contradicting its own earlier findings, or hedging on things it proved two hours ago. That is context saturation.

Do **not** start a new session:

- **Mid-brief.** Live SSH multiplexing, verified state, and in-flight facts are lost.
- **Between a change and its verification.** Finish the proof first.

When you do start fresh, point it at `AGENTS.md`, this file, and the specific report from the previous step. Nothing else — a fresh session reading eight reports is as saturated as the one you just closed.

---

## 10. Where things are (repo `docs/`)

Reports, in order: `AUTHENTICATION_CORE_2026-08-18.md` · `TLS_CUTOVER_2026-08-19.md` · `CALCULATION_MAP.md` (read §4 of this file first) · `ROUTE_GUARD_H1_2026-08-19.md` · `LAUNCH_PREP_2026-08-19.md` · `MAIL_AND_RUNBOOK_2026-08-19.md` · `THROTTLE_RAISE_2026-08-20.md` · `SHARED_INVITE_2026-08-20.md` · `DRESS_REHEARSAL_2026-08-2x.md` · `COSMETIC_PRELAUNCH_2026-08-2x.md` · `ROUTE_GUARD_DEFERRED_2026-08-2x.md` · `CLEVEL_DIRECT_ENABLE_2026-08-2x.md` · `MATRIX_CALIBRATION_FIX_2026-08-2x.md` · `REPORTING_SURFACE_2026-08-2x.md` · `DRAFTS_UX_2026-08-2x.md` · `DOCS_HYGIENE_2026-08-2x.md`. Operational: `LAUNCH_RUNBOOK_H1.md` (Alexander's one page), `INVITATION_WAVES.md` (now "single send"; §2 one-pager, §4 registration query, §5 deliverability). Briefs: `docs/briefs/`. Decisions: `DECISIONS.md` (single register; `PROJECT_DECISIONS.md` is a pointer). Bugs: `bugs.md` (open: BUG-008 plus leftovers listed in §7). Progress: `PROGRESS.md`. Ports/names: `PROJECT_RULES.md` (created 2026-08-20 from compose + tunnel facts).

A new Cursor session gets: `AGENTS.md`, this file, and the one report relevant to its brief. Nothing else.
