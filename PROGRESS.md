# Evaluation Portal Progress

## 2026-08-12 — Initial revival health check

**What was done:**
- Reconstructed the high-level architecture from the repository.
- Installed dependencies with `npm ci`.
- Built the frontend successfully with `npm run build`.
- Started the Vite development server and verified `/` and `/login` return HTTP 200 locally.
- Ran ESLint and the production dependency audit.
- Probed the legacy host and the configured n8n webhook endpoint.
- Verified that the GitHub remote is reachable.

**Results:**
- Frontend source: buildable and locally startable.
- Frontend quality gate: failing with 20 errors and 13 warnings.
- Automated tests: no test command is configured.
- Dependency audit: 5 production vulnerabilities (4 high, 1 moderate).
- Legacy host `92.51.45.147`: reachable by ICMP; SSH port 22 is open.
- Ports 80, 443, and 5678: connection refused.
- Configured n8n API: unavailable from the current environment.
- Former public frontend URL: not recorded in repository metadata.
- Working tree: 73 changed or untracked paths before adding revival documentation.

**Important findings:**
- `src/config/api.js` defaults to `http://92.51.45.147:5678/webhook`.
- `src/pages/Login.jsx` duplicates the login endpoint as a hard-coded URL, bypassing centralized configuration.
- The login form posts email and password over plain HTTP; it must not be exposed to users in this state.
- Several lint errors indicate possible runtime defects, including undefined state setters in admin and team pages.
- The production build warning identifies an oversized spreadsheet bundle.

**Notes / Gotchas:**
- A successful Vite build proves the frontend can compile; it does not prove business workflows work without n8n and PostgreSQL.
- The host itself is alive. Current evidence points to stopped or unexposed web/n8n services, not a dead machine.
- No server configuration was changed and no deployment was attempted.

**Next step:**
Perform a read-only SSH infrastructure inventory, then back up the legacy services and data before attempting recovery.

## 2026-08-12 — Removed embedded n8n credential

**What was done:**
- Removed the hard-coded n8n API key from `dump_n8n.py`.
- Made the export script require `N8N_URL` and `N8N_API_KEY` environment variables.
- Added safe placeholders to `.env.example`.
- Recorded the resolved security defect in `bugs.md`.

**Notes / Gotchas:**
- The discovered key was already expired and `dump_n8n.py` was untracked, so there is no evidence from the current Git state that it reached the public remote.
- Any replacement key must remain in an ignored local `.env` or shell environment.

## 2026-08-12 — Located the legacy production frontend

**What was done:**
- Confirmed the production frontend at `http://135.232.120.40:8080`.
- Verified both `/` and `/register` return the Evaluation Portal SPA with HTTP 200.
- Confirmed the deployed bundle still points to `http://92.51.45.147:5678/webhook`.

**Result:**
- The production frontend service is alive and serves the same bundle currently produced locally.
- End-to-end operation remains broken because the referenced n8n backend refuses connections.

**Notes / Gotchas:**
- Production is served over plain HTTP and has no verified domain or TLS endpoint.
- The invite token supplied during discovery was intentionally not used or stored in repository documentation.

## 2026-08-12 — Read-only VPS safety map

**What was done:**
- Connected as `root@92.51.45.147` via the existing multiplexed SSH socket (password not written).
- Inventoried Docker, host listeners, systemd, cron, disk, firewall, both Postgres clusters, and all 58 n8n workflows.
- Wrote `docs/SERVER_MAP.md`. No server object was changed.

**Results:**
- Five containers, all running. EPE owns none of them exclusively. `n8n-n8n-1` and `postgres_n8n` are shared; `postgres_main`, `redis_prod`, and `portainer` are foreign.
- `postgres_n8n` database `postgres` has four application schemas, all owned by superuser `admin`: `performance_db` (EPE), `new_scheme` (108 079 equipment rows), `medical_equipment`, `public` (n8n).
- 39 EPE workflows, 17 foreign, 2 unclear. Live foreign webhooks: `school-helper`, `new_clinic/equipment`, `new_clinic/request`, `new_clinic/rooms`.
- Host firewall does not restrict 5431, 5432, 5678, 8000, 9000. ufw inactive. `DOCKER-USER` is empty.
- Docker json logs have no rotation. `postgres_n8n` log is 1 710 309 517 bytes. Disk 22 G/50 G used, 28 G free.
- `/var/run/reboot-required` is set (`libc6`, `libssl3`). n8n restart policy remains `on-failure`.

**Notes / Gotchas:**
- `/root/n8n/docker-compose.yml` does not describe the running n8n container. The live definition is Portainer stack `compose/5`.
- `PROJECT_RULES.md` is still missing from the repo.
- Hypothesis that `new_scheme` was a small leftover is false: it is a live catalog.

## 2026-08-12 — Auth surface of EPE write webhooks

**What was done:**
- Read live `workflow_entity` JSON for 10 EPE routes. No endpoints were called. No workflows were deactivated.

**Results:**
- `api/admin/clear-test-evaluations`: webhook → `DELETE` all evaluations. No token/JWT/secret check.
- Same absence of webhook auth on save-user, manage-criteria, update-admin-data, periods create/activate, and the three admin GET routes.
- `api/admin/score-correction` has a spoofable role check on `body.evaluator_id`, not a secret.
- `api/register` checks an invite token in `invite_tokens` before the password UPDATE.

**Notes / Gotchas:**
- Recorded as BUG-002. Live workflows were left active.

## 2026-08-12 — Deactivated EPE API:* workflows

**What was done:**
- Recaptured live flags to `docs/n8n_workflow_state_2026-08-12T2129.json` because the 20:41 snapshot had drifted (foreign workflows already archived at 21:18–21:19 UTC).
- Confirmed no active EPE path shared with an active foreign workflow.
- Deactivated all 35 active `API:*` workflows via n8n `POST /api/v1/workflows/{id}/deactivate` on the running process. Container not restarted.
- Wrote `docs/n8n_deactivation_2026-08-13.md`.

**Results:**
- `webhook_entity` is empty. All 35 `API:*` rows are `active=false`, not archived.
- Foreign four paths were already inactive/archived before this change; their `updatedAt` did not move.
- n8n `healthz` HTTP 200. `StartedAt` unchanged.

**Notes / Gotchas:**
- Instruction said 36; live count was 35 (CORS included). Stored n8n API keys were expired; a 2-hour JWT was swapped onto the `cursor` key for the calls and the original JWT restored.

## 2026-08-12 — Frontend host inventory (read-only)

**What was done:**
- Probed `135.232.120.40` over HTTP and TCP. Did not SSH (port 22 times out from this Mac and from `92.51.45.147`). Did not call EPE webhooks. Did not rebuild or restart anything.
- Downloaded the live SPA (`index.html`, `assets/index-C9WM9w28.js`, `assets/index-De9_K8gc.css`, `vite.svg`) and compared the compiled endpoint map with `src/config/api.js` and `n8n_workflows/`.
- Wrote `docs/FRONTEND_MAP.md` and `docs/API_CONTRACT.md`.

**Results:**
- `:8080` is npm `serve -s` on Windows (Azure, `mnt-by: MICROSOFT-MAINT`). HTTP-only, public. Port 80 is unused HTTP.sys 404. Port 3389 RDP is public.
- Host serves a Vite production artifact only. No source, source map, or `.git` at the web root. That artifact is not in git (repo: 32 tracked files, 2 commits).
- Live API base URL is hard-coded `http://92.51.45.147:5678/webhook`. 35 paths in the bundle match `src/config/api.js`.
- Client stores `user` + `token` (`fake-jwt-<id>`) in `localStorage`, sends `Authorization: Bearer …` on `apiClient` calls. n8n does not read it. Admin UI is `user.role` in the browser.

**Notes / Gotchas:**
- Disk path `C:\WebApps\evaluation-portal` and Node version on the VM are from the 2025-12-23 deploy conversation, not from a shell this session.
- `EMPLOYEE_SELF_REVIEW` is in the client map and unused. `/get-admin-data` exists in n8n and is not in the client.

## 2026-08-13 — Sysadmin hardening of 92.51.45.147

**What was done:**
- Authorised host changes, one step then verify. Report: `docs/SYSADMIN_2026-08-13.md`.
- n8n restart policy `unless-stopped` (container not recreated). Proven by Docker restart and by a full host reboot: same id `0a8304de6083`, `healthz` 200.
- `performance_db` dump restored into a throwaway database; all 12 table counts matched; throwaway dropped.
- Daily gzip dump + 14-day retention on the host. Weekly off-host copy **not** implemented — target not chosen.
- `DOCKER-USER` (+ `INPUT` for Swarm) allowlist `212.36.169.90`; internet DROP on 5432/5431/8000/9000/2377/7946; 5678 and 22 left open. Survived reboot. External checker confirmed.
- Docker `daemon.json` log caps, postgres json logs truncated (1.59 GiB → 0), journal vacuum 3.9 G → 176 M, Docker restarted in this window.
- SSH: Alexander’s ed25519 key installed and confirmed in a second session, then password auth disabled, fail2ban sshd on.
- Postgres `log_connections` / `log_disconnections` / `%h` prefix, `pg_reload_conf()` only.
- Security pocket via `unattended-upgrade`; `docker-ce` 27→29 held; reboot cleared `reboot-required`.
- Dumped then dropped schemas `new_scheme` and `medical_equipment`; removed dangling n8n image and Mattermost/Metabase volumes. `performance_db` and `public` untouched.

**Results:**
- Five containers up after reboot. Disk 22 G → 15 G used.
- Paid API keys (OpenAI, OpenRouter) not rotated — need Alexander’s provider accounts.

**Notes / Gotchas:**
- `iptables-persistent` not used; systemd `epe-firewall.service` + Docker `ExecStartPost` is what actually survived Docker’s iptables rewrite.
- Dangling `postgres` image `f0dfc903a663` is the live `postgres_n8n` image; it was not removed.
- Daily dump is `performance_db` only, not n8n `public`.

**Next step:**
Alexander picks the off-host weekly backup target and rotates OpenAI/OpenRouter (and SMTP if still billed).

## 2026-08-18 — H1 critical-path and auth feasibility review

**What was done:**
- Completed the requested read-only review of password storage, period isolation, scoring authority, annual-model capability, workflow drift, and n8n authentication feasibility.
- Compared all 35 repository API workflow exports with the canonical live rows and wrote `docs/REVIEW_H1.md`.

**Results:**
- H1 is NO-GO on the current API: the non-self evaluation conflict key omits `period_id`, so H1 submissions can overwrite the 2025 records.
- Live passwords are plaintext-like, write routes trust client identity and final scores, and the model has no H1/H2-to-annual aggregation concept.
- Workflow comparison: 1 identical, 34 drifted, 0 missing; 32 differences are deactivation-only and two include node-level drift.

**Notes / Gotchas:**
- No workflow, schema, data, credential, webhook, or container environment value was changed.

## 2026-08-18 — Step 1 container foundation and isolated database

**What was done:**
- Confirmed SMTP delivery before changes; captured the Portainer stack and a gitignored container inspect.
- Stored the n8n encryption key and new JWT signing secret in macOS Keychain.
- Created and restore-tested fresh `performance_db` and n8n `public` dumps.
- Pinned n8n to the running image's immutable registry digest and recreated only the n8n service.
- Added the crypto/jsonwebtoken allowlists, Code-node environment access, and a 64-byte JWT signing secret.
- Created the unused `epe_2026.performance_db` schema from the live baseline with period-isolation corrections and reference data only.
- Diagnosed Portainer access without changing it.

**Results:**
- n8n 1.121.3, healthz 200, restart `unless-stopped`; all 11 existing operator-set variables preserved.
- 58 workflows, 35 inactive `API:*`, 6 credentials. Post-recreation SMTP delivery confirmed.
- Manual Code-node proof passed: crypto import, jsonwebtoken sign/verify, and `$env.JWT_SIGNING_SECRET` length 88.
- `epe_2026`: 12 tables; criteria 8, departments 14, grades 10, score coefficients 80; all transactional/user tables empty.
- n8n still points to database `postgres`; `epe_2026` has no active connections.
- Portainer is healthy. Current IP `188.137.254.191` is blocked because the firewall still allowlists `212.36.169.90`.

**Notes / Gotchas:**
- An initial recreation was rolled back because an image-inherited `NODE_VERSION` difference was incorrectly treated as operator configuration drift. The verified retry used the corrected criterion.
- The mutable `1.121.3` tag resolves to a different image; the stack uses the running image's RepoDigest.
- Full evidence and rollback instructions: `docs/STEP1_2026-08-18.md`.

## 2026-08-18 — Admin access follow-up and import preflight

**What was done:**
- Replaced the persisted firewall allowlist address `212.36.169.90` with Alexander's current `188.137.254.191`; kept port 5678 public.
- Added and started local SSH alias `epe-vps-tunnel`.
- Searched the project, Downloads, Desktop, and Documents for the dated HR export before starting the organisation import.

**Results:**
- Firewall service active; 12 rules use the current address and none use the former address.
- Persistent launchd tunnel verified: `25432 -> 5432`, `29000 -> 9000`, `25431 -> 5431`; Portainer returned HTTP 200.
- The required 2026-08-18 HR export was not found. Only `public/шаблон_импорта_сотрудников.xlsx` exists, so no import or mapping proposal was attempted.

**Notes / Gotchas:**
- The agent shell's public address is `216.147.123.47`, not Alexander's browser address, so direct Portainer access from `188.137.254.191` remains user-verifiable.
- No evidence of a purchased portal domain or configured TLS endpoint exists in the repository or current server documentation.

## 2026-08-18 — Organisation import approval gate

**What was done:**
- Parsed the supplied HR export after correcting its invalid Excel dimension metadata (`A1` despite 89 actual rows).
- Compared all 88 export employees with the 73 read-only 2025 users, 14 departments, 10 grades, and 8 criteria.
- Validated reporting lines, manager flags, grade carry-over by email, and project-question eligibility.
- Captured a deterministic source fingerprint in the ignored backup area and created the import approval canvas.

**Results:**
- 88 unique export emails; 29 rows have no Employee ID, so email is the only complete identity key.
- All `Reports to` names resolve after adding Cem Durukan manually; manager cycles: 0.
- The export has 18 department strings, not 20. Proposed target has four new departments.
- Exact grade `M1` is missing (`S4-M1` is not a substitute); six normal employees still need grades.
- One confirmed leaver: Gulsoltan Kulyaliyeva. Merdan Rasulov is an email-change candidate, not a leaver.
- Current project questions depend on `is_project_participant`, not `work_category` alone.

**Notes / Gotchas:**
- Import has not started. Department, questionnaire, grade, identity-alias, and evaluation-capability decisions require Alexander's approval.
- The users schema cannot represent Cem reporting above C-level while being excluded from both evaluation directions; a separate capability/scope model is required.

## 2026-08-18 — Current organisation imported into epe_2026

**What was done:**
- Applied Alexander's department, questionnaire, role, grade, identity, and evaluation-capability decisions.
- Added `can_evaluate` and `can_be_evaluated` to target users.
- Created exact grade M1 by copying coefficient and description from S4-M1.
- Imported 88 HR-export employees plus manual Cem using `scripts/import_epe_2026.py`.
- Ran full reconciliation, a sequence-safe idempotent rerun, and before/after source fingerprints.

**Results:**
- 89 unique users; roles: admin 1, c_level 5, hr 2, manager 12, employee 69.
- Passwords 0; evaluations 0; evaluation scores 0; periods 0.
- 86 manager links; eligible users without an evaluator 0; manager cycles 0; `has_subordinates` mismatches 0.
- Project participants 43; general 46.
- Target rerun changed 0 users and 0 manager links; full target fingerprint unchanged.
- Source schema, all table contents, and all sequence states matched the pre-import fingerprint.

**Notes / Gotchas:**
- n8n remains connected to `postgres`; all 35 `API:*` workflows remain inactive.
- Scrypt registration/login, capability enforcement, H1 participation rows, credential repointing, and TLS remain unimplemented.
- Full report: `docs/IMPORT_2026-08-18.md`.

## 2026-08-18 — Authentication core proven on one route

**What was done:**
- Audited 14 archived non-EPE workflows that shared the old Postgres credential; confirmed their deleted schema dependencies and preserved them unchanged.
- Added stable 2025 annual and H1-2026 periods plus 89 H1 participation rows.
- Added scrypt registration/login, DB-backed throttling, one-time email reset, token-versioned sessions, and a reusable live-identity guard.
- Protected only `GET api/employees` and proved six authorization scenarios.
- Created a dedicated EPE 2026 Postgres credential and rebound only EPE workflows.
- Added local evaluation drafts, a 15-minute session-expiry warning, and reset-password UI.

**Results:**
- Real registration stored a 133-character scrypt hash; real login issued only the six approved JWT claims for 4 hours.
- Reset email delivered; reset token worked once, incremented token version, revoked sessions, and made the old password/token invalid.
- Guard rejected missing, forged, expired, wrong-role, and disabled-capability tokens; valid identity ignored conflicting client IDs.
- Throttle locked after five failures in 15 minutes.
- 37 unarchived API workflows, 0 active, 0 registered webhooks; 36 use the new credential and CORS uses none.
- 14 foreign workflows and the shared credential matched the pre-change backup.
- 2025 source fingerprint unchanged.

**Notes / Gotchas:**
- Reset now fails closed until `EPE_FRONTEND_URL` is configured with an HTTPS origin.
- Frontend changes are built and tested but not deployed.
- Only one route is guarded; remaining routes are the next pass.
- Full report: `docs/AUTHENTICATION_CORE_2026-08-18.md`.

## 2026-08-19 — TLS and same-origin portal cutover

**What was done:**
- Verified DNS through three resolvers and audited non-interactive access to the Azure fallback and old `.243` host.
- Deployed pinned Caddy as the `epe-proxy` Compose project.
- Issued one production Let's Encrypt certificate for `epe.sedamedical.com`.
- Built the frontend with `VITE_API_URL=/webhook` and deployed timestamped static releases from the Mac.
- Set n8n webhook/reset origins to the HTTPS domain and recreated n8n with all unrelated environment values preserved.
- Opened public 80/443 and blocked direct public 5678 in the persistent firewall.
- Sent and confirmed a real HTTPS reset email without n8n attribution.
- Temporarily activated only login and employees for authorized HTTPS acceptance, then deactivated both.

**Results:**
- Portal HTTPS 200; HTTP 308 to HTTPS; SPA reset route 200.
- Valid Let's Encrypt certificate through 2026-11-17.
- HTTPS login 200; guarded valid token accepted; forged token rejected 401.
- External 5678 filtered; local n8n health 200.
- Caddy certificate persisted across restart; background renewal maintenance active.
- All 61 workflows inactive, webhook registry empty, active auth sessions 0.
- Azure fallback remained HTTP 200 on port 8080 and was not changed.
- 2025 source fingerprint unchanged.

**Notes / Gotchas:**
- Workflows remain inactive after acceptance; the portal shell is live but login is deliberately unavailable until the route rollout.
- The dependency audit reports 15 advisories, including 11 high.
- No non-interactive access exists for Azure or `216.250.12.243`.
- Full report: `docs/TLS_CUTOVER_2026-08-19.md`.

## 2026-08-19 — Calculation map (read-only)

**What was done:**
- Saved the brief verbatim to `docs/briefs/CALCULATION_MAP_2026-08-19.md`; deliverable written to `docs/CALCULATION_MAP.md`.
- Traced every computed/stored/displayed number to a named client function or n8n node/SQL; verified repo workflow exports match the server's n8n public schema by formula fragments.
- Queried the 2025 archive read-only; reproduced stored scores for all 234 evaluations, not a 10-sample.
- Took the archive canonical fingerprint and a plain-format n8n public dump before and after.

**Results:**
- Fingerprint `21d323b0…` unchanged; n8n dump SHA-256 identical (`3d4d7cfa…`), artifacts in `backups/2026-08-19-calcmap/`.
- Self-vs-manager comparison is raw 1–10 vs 1–10 everywhere — not grade-driven; the weighted self value is displayed once (own profile, admin/c_level) and never compared.
- Ratings reproduce: 115/120 manager, 64/64 self, 50/50 upward. The 5 mismatches are upsert merges where a later c_level-criteria-only submission overwrote `calculated_score` while older score rows survived.
- Self `weighted_score`: 0/64 reproduce from today's stored inputs; grade coefficient provably not applied in December (identical vectors → identical weighted across grades 0.30–3.00); weights/coefficients were edited after December and are unversioned.
- The admin-matrix/bonus index is stored nowhere; December matrix values are unrecoverable. 3 corrections exist (criterion 13). No `c_level_direct` rows in 2025.
- 9 query families have no period filter (matrix, all-evaluations, analytics, my-profile, history, details-by-user, get-my-manager last score; `score_corrections` has no period column at all).
- Criteria distribution across the 89: 35×3, 11×4, 38×5, 5×6 (manager path; +2 under c_level evaluator; self 3, upward 1).

**Notes / Gotchas:**
- Server stores client-computed `final_score`/`weighted_score` without recomputation or range validation on every write path except score-correction.
- The 2026 login does not return `grade_coefficient`; self-review weighting silently falls back to 1.0 (as it did in December).
- Admin matrix and EmployeeScoresModal ignore `mid_level_correction`; final-scores/calculator/Excel average it in — same cell, two values.
- `PROJECT_RULES.md` referenced by `AGENTS.md` does not exist in the repo (not reconstructed — read-only brief).
- Full report: `docs/CALCULATION_MAP.md`.

**Follow-up (same day):** recorded the architect's addendum verbatim in `docs/briefs/ROUTE_GUARD_H1_2026-08-19.md` and verified its D5 evidence read-only. Found that `epe_2026` already has per-period unique indexes (evaluations non-self/self, score_corrections with NOT NULL `period_id`) and that the current `ON CONFLICT` targets in `API: Submit Evaluation` and `API: Score Correction` no longer match them — every call to either route fails with 42P10 at planning time (proven via `EXPLAIN`, no writes). Documented in `docs/CALCULATION_MAP.md` §E; launch blocker for the route-guard brief.

## 2026-08-19 — H1 route guard decision gate

**What was done:**
- Preserved the route-guard brief verbatim and recorded the approved H1/H2 annual aggregation rule.
- Compared the relevant workflow exports and frontend call sites with the live n8n graphs and `epe_2026` schema.
- Stopped before route, schema, workflow, or data changes as required by the brief's D1–D8 decision gate.

**Results:**
- All 61 workflows remain inactive; evaluations and active sessions remain 0.
- H1 remains period 2, draft and inactive, with 89 participants and 87 in scope.
- Live period-aware evaluation uniqueness and `period_id NOT NULL` are missing from repository migrations; the current submit conflict target does not match production and would fail.
- The portal edits `work_category`, while project criteria use `is_project_participant`; all 43 project classifications match now, but a portal edit would desynchronise them.
- Decision report: `docs/ROUTE_GUARD_H1_2026-08-19.md`.

**Notes / Gotchas:**
- No remote mutation, dump, fingerprint, activation, test row, test session, or temporary workflow was created in this decision-gate pass.
- Route implementation is blocked only on Alexander's answers to D1–D8 in the report.

## 2026-08-19 — H1 guarded launch surface deployed

**What was done:**
- Applied Alexander's D1–D8 decisions, including the expanded guarded `periods*` surface and immediate launch-route activation.
- Reconciled period/source constraints with migration 012 after restore rehearsal and idempotency proof.
- Replaced 17 n8n workflow graphs, deleted the clear-test workflow, fixed the frontend Axios double-prefix defect, and deployed release `20260819T094626Z`.
- Ran API authorization/identity/ownership/write proofs and real employee/manager browser submissions; then deleted every evaluation, session, invite, and period created by acceptance.

**Results:**
- 25 approved workflows active, 28 registered webhooks; 0 unexpected active workflows.
- Missing/forged/expired tokens rejected on 19 protected method routes; role, capability, ownership, identity-conflict, scope, uniqueness, privacy, and freeze cases passed.
- Browser: employee self-review, upward evaluation, and manager evaluation of one subordinate completed at 7.00; no 401 loop.
- Final state: evaluations 0, scores 0, active sessions 0, active periods 0, H1 id=2 draft/inactive, temporary artefacts 0.
- Final dumps restored successfully; 2025 fingerprint remained `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e`.
- Full report: `docs/ROUTE_GUARD_H1_2026-08-19.md`.

**Notes / Gotchas:**
- n8n intercepts OPTIONS preflight with 204 before the workflow guard; the request has no identity and performs no mutation.
- Open BUG-007: out-of-scope employees are still displayed/count toward manager task completion even though submit rejects them. Fix before invitations.
- The frontend dependency audit still reports 15 advisories (11 high); unchanged and deferred under the prior decision.

## 2026-08-19 — Launch prep for invitations and H1

**What was done:**
- Filtered campaign employee lists, manager task status, and HR denominators through active-period `evaluation_period_participants.is_in_scope` (BUG-007).
- Added a 60-second verification-code cooldown and a 30/5-minute verify-invite IP throttle.
- Made manager/subordinate submit and update store the plain average of their own score rows; out-of-range grades remain 422.
- Rehearsed the production bundle with temporary JWTs, proved classification/coefficient freeze lift after cleanup, and returned H1 to draft.
- Wrote `docs/INVITATION_WAVES.md`, merged decision registers, deployed frontend `20260819T120100Z`.

**Results:**
- With H1 active: Akmyrat 5 names (Esenova absent), Alyona 1 name (Balova absent), periods `87 / 89`.
- Tampered `final_score` stored as the row mean (7.00 then 8.00); grade 11 → 422 and no row.
- After rehearsal: evaluations 0, sessions 0, registered 1, H1 draft/inactive, 25 workflows active, 2025 fingerprint unchanged.
- Full report: `docs/LAUNCH_PREP_2026-08-19.md`.

**Notes / Gotchas:**
- DKIM for `noreply@sedamedical.com` is missing; inbox/spam tests wait on mailboxes Alexander names.
- Shared invite token id=4 is unused until 2026-09-18; do not commit the raw token.
- No `acceptance_tokens.json` / `browser_accounts.json` was ever in git.

## 2026-08-19 — Mail deliverability and H1 launch runbook

**What was done:**
- Read n8n `SMTP account` (host/port/auth domain only): `smtp.gmail.com`, default 465, user domain `sedamedical.com`. SPF `include:_spf.google.com` covers it. DKIM still absent.
- Sent two deliverability messages through that credential to `alexander@sedamedical.com` and `a.petrosov@gmail.com` (placeholders were empty; these are the only two mail identities on the workstation).
- Proved `verify-invite` already stores the real client IP behind Caddy (`216.147.123.249` vs `92.51.45.147`); spoofed `X-Forwarded-For` ignored. No workflow change, no dump.
- Wrote `docs/LAUNCH_RUNBOOK_H1.md`. Probe throttle rows deleted.

**Results:**
- SMTP login and both sends succeeded. Received-header inbox/spam verdicts unverified (no IMAP; Gmail login wall).
- End state: users 89, registered 1, evaluations 0, sessions 0, H1 draft/inactive, 25 workflows active.
- Full report: `docs/MAIL_AND_RUNBOOK_2026-08-19.md`.

**Notes / Gotchas:**
- Live verify-code and reset paths both require `@sedamedical.com`; they cannot test an external mailbox.
- Periods UI has no Deactivate button; Annual 2025 is closed, so H1 cannot be turned off from the screen after activation.
- Only one admin exists.

## 2026-08-19 — verify-invite throttle raise for 26 Aug NAT burst

**What was done:**
- Verified live n8n: `verify-invite` was still 30 / 5 min / IP (`throttleCount > 30`). The hypothesized earlier raise to 600 had not been applied.
- Dumped `epe_2026` and n8n `public` (restore-tested); 2025 fingerprint `21d323b0…` before and after.
- Raised only `API: Verify Invite` Format Response to `throttleCount > 600`. Workflow stayed active. 25 active names unchanged.
- Proved 40 GETs from one IP (`216.147.123.249`) all returned invalid-token, none `RATE_LIMITED`; counter=40; then deleted the throttle row.
- Left the 60-second per-email resend cooldown unchanged.

**Results:**
- Live limit is 600 / 5 min / IP. Burst 40/40 passed the throttle layer.
- End state: users 89, registered 1, evaluations 0, sessions 0, throttle rows 0, H1 draft/inactive, 25 workflows active, 28 webhooks.
- Full report: `docs/THROTTLE_RAISE_2026-08-20.md`.

**Notes / Gotchas:**
- `HANDOVER.md` has no §6.1; the 30-cap lived in §3 and the mail report (§2 said no throttle change).
- `API: Register` still sets `invite_tokens.is_used=true` on first success. A company-wide shared link would stop after person 1. Not changed in this brief.

## 2026-08-19 — Shared invite token reusable for 26 Aug

**What was done:**
- Replaced `docs/HANDOVER.md` with the 2026-08-20 text, then verified live `API: Register` still required `is_used=false` and set `is_used=true`.
- Dumped `epe_2026` and n8n `public` (restore-tested); 2025 fingerprint `21d323b0…` before and after.
- Stopped burning the invite on register (expiry still checked). Widened the token regex so the live base64url token id=4 is accepted (UUID hex still is).
- Proved two employees registered through the same link; third already-registered attempt rejected; then rolled `password_hash` back.

**Results:**
- Invite id=4 remains unused after two successful registers. End state: registered=1 (Alexander), evaluations 0, sessions 0, H1 draft/inactive, 25 workflows active.
- Full report: `docs/SHARED_INVITE_2026-08-20.md`.

**Notes / Gotchas:**
- Without the regex change the 26 Aug link could not register anyone (id=4 is 43-char base64url; validator was UUID-only). First proof wave verified email then got 400 with no password write.
- Alina and Alp-Arslan received real verification emails; codes consumed/deleted; hashes NULL again.

## 2026-08-19 — Dress rehearsal in the live browser

**What was done:**
- Dumped `epe_2026` and n8n `public` (restore-tested); 2025 fingerprint `21d323b0…` before activation.
- Activated H1 (id=2) from Admin → Периоды. Coverage on screen **87 / 89**.
- Registered Alina in the browser via invite id=4 (email code, password, login). Registered Akmyrat via the same invite over curl so the manager flow could be walked.
- Walked employee (self-review + upward) and manager (one subordinate) on `https://epe.sedamedical.com`. Proved `period_id=2` and evaluator-from-token. HR status API reflected the three writes. Employee `/admin/*` bounced. Esenova cannot log in (401); exclusion on manager list + HR API.
- Corrected `LAUNCH_RUNBOOK_H1.md` wording `проект / полевые` → `general` / `project`.
- Deleted rehearsal rows, nulled test hashes, H1 back to draft. After-dumps restore-tested.

**Results:**
- Verdict: ready for 31 Aug — **yes**. No functional blocker.
- Draft persistence failed on self-review and upward; only the manager modal restores sliders after refresh.
- End state: evaluations 0, scores 0, sessions 0, registered 1 (Alexander), H1 draft/inactive, invite id=4 unused, 25 workflows active, 2025 fingerprint unchanged.
- n8n public SHA changed (executions 106→111, insights_raw 0→220); workflow count and history row count did not.
- Full report: `docs/DRESS_REHEARSAL_2026-08-2x.md`.

**Notes / Gotchas:**
- Annual 2025 still shows **Активировать**. That is the ops risk on activation day.
- Admin cannot open `/hr/dashboard` (`isHR` is role `hr` only). Status was proven by API.
- Login «Зарегистрироваться» still tells people to write HR; the launch plan is one company-wide mail.

## 2026-08-19 — Cosmetic pre-launch (D2 / D4)

**What was done:**
- Verified live GET periods already returns `status`. Hid **Активировать** when `status === 'closed'`; `handleActivate` no-ops for closed. H1 (`draft`) keeps the button.
- Removed the Welcome «Итоговая оценка» / bonus-index formula card entirely (`Welcome.jsx`). No new copy.
- Deployed via `./scripts/deploy_epe_frontend.sh`. Re-checked as admin in the browser. Did not activate H1.

**Results:**
- Release **`20260819T181012Z`**. Previous **`20260819T120100Z`** still on disk.
- Periods: H1 has Activate; Annual 2025 actions cell empty. Welcome: no formula heading or Σ line.
- End state: H1 draft/inactive, evaluations 0, registered 1, 25 workflows active, 2025 fingerprint unchanged.
- Full report: `docs/COSMETIC_PRELAUNCH_2026-08-2x.md`.

**Notes / Gotchas:**
- A tab left open from the previous release can still show the old Welcome until refresh (hashed chunk `Welcome-Cs7JXa32.js`).
- n8n public SHA moved on `insights_raw` 220→270 only; workflow rows unchanged.

## 2026-08-19 — Deferred routes behind Auth Guard

**What was done:**
- Verified the deferred set is 10 data routes, not ~16. CORS handler left inactive. 25 launch workflows and `EPE: Auth Guard` were not edited (guard GET md5 `de58de075d66a621e832aac9a2dd3d14` unchanged).
- Generated guarded payloads, PUT them inactive, proved no_token/forged/expired/wrong_role/ownership/valid plus identity-conflict and freeze 409. `c_level_direct` submit still 422.
- Two generator defects found in proof (f-string ate `={{ }}`; analytics missing Respond link) were fixed, re-PUT, and re-proven. SQL/formulas untouched.
- Proof rows and sessions rolled back. H1 stayed draft except a temporary activate for freeze proofs.

**Results:**
- End state: evaluations 0, corrections 0, sessions 0, registered 1, H1 draft/inactive, invite id=4 unused, 25 workflows active, 28 webhooks, 2025 fingerprint `21d323b0…` unchanged.
- Five questions left for Alexander: delete vs keep employee-self-review and get-admin-data; HR on company-wide reporting; mid_level rule; keep 422 on `c_level_direct`.
- Full report: `docs/ROUTE_GUARD_DEFERRED_2026-08-2x.md`.

**Notes / Gotchas:**
- Cleanup deleted Alexander’s two browser sessions to meet `sessions=0`.
- Live `score_corrections.period_id` already exists; upsert uses it. No new column.
- 2026 has no manager-role skip-level user; `mid_level` 200 was not proven. First-line manager → 403.

## 2026-08-19 — `c_level_direct` enabled; matrix activated

**What was done:**
- Dumped `epe_2026` and n8n `public` (restore-tested); 2025 fingerprint `21d323b0…` before and after.
- Deleted inactive `API: Get Employee Self Review` and `API: Get Admin Data Fixed` (GET 404). Auth Guard GET md5 `de58de075d66a621e832aac9a2dd3d14` unchanged.
- `API: Submit Evaluation`: dropped 422 `SOURCE_NOT_SUPPORTED`; `c_level_direct` allowed for admin or c_level; evaluator = token actor; subject `can_be_evaluated`, in scope, not cem/hemra/mekan. Insert formula still `AVG(score_val::numeric)`.
- Activated `API: evaluations-matrix` (guard already admin + c_level). score-correction and the other deferred routes stayed inactive (POST correction = 404).
- Re-proved submit-evaluation at the H1 bar for manager / upward / `c_level_direct`. Browser as Alexander: matrix opened (88 rows), C-level cell for Tishkina submitted, row `source=c_level_direct` period 2.

**Results:**
- End state: evaluations 0, sessions 0, registered 1, H1 draft/inactive, invite id=4 unused, **26 workflows active**, 29 webhooks, 58 workflows total.
- Full report: `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md`.

**Notes / Gotchas:**
- 2025 had **zero** `c_level_direct` evaluation rows. Admin acted at C-level via `score_corrections`. Implemented admin+c_level; confirm if admin should stay a writer.
- Matrix UI sends no `period_id` and a client `evaluator_id`; server overwrites both. Residual risk is display (no period filter; stars on out-of-scope / read-only rows; second save 409). Not fixed.
- Login Keychain password 401’d; browser pass used a minted admin JWT, then that session was deleted.

## 2026-08-19 — Matrix / calibration surface fixed

**What was done:**
- Pre-checked Jemal in live `epe_2026`: id=47, role=`c_level`, `can_evaluate=true`. Previous C-level report missed her. Org row not edited.
- Bound evaluations-matrix GET to one period (default = active; optional `?period_id=`; empty + draft banner when none). `manager_score` by `evaluation_source='manager'`.
- Activated score-correction; period bind is now `is_active AND status='active'` only (draft POST → 409 `NO_ACTIVE_PERIOD`).
- UI: stars only on in-scope evaluable non-C-level subjects; «Изменить» prefills and saves via update-evaluation; final cell averages manager + mid + c_level the same way the money paths already did.
- Deployed frontend `20260819T203659Z` (previous `20260819T181012Z` kept). Browser pass as Alexander: star, save, reopen, update 200, correction 200, final 8.0 then 7.7; then full rollback.
- Proof sessions deleted (12); Alexander’s pre-existing session kept (1). 2025 fingerprint `21d323b0…` unchanged.

**Results:**
- End state: evaluations 0, corrections 0, registered 1, sessions 1 (Alexander), H1 draft/inactive, invite id=4 unused, **27 workflows active**, 30 webhooks, 58 workflows total.
- Full report: `docs/MATRIX_CALIBRATION_FIX_2026-08-2x.md`.

**Notes / Gotchas:**
- After H1 is closed this screen goes empty until a period selector is added or H1 stays active through calibration. API already accepts `?period_id=`.
- Displayed final for Alina c3 proof was `(6+8+10)/3=8.0`, then `(6+8+9)/3=7.7`. Rows rolled back.
- 2026 still has no skip-level manager; live `mid_level` 200 unproven. First-line → 403.
- Login Keychain password still 401; browser used a minted admin JWT. Alexander’s real session was not deleted.

## 2026-08-20 — Reporting surface: period bind, defects, HR routing

**What was done:**
- Activated and period-bound the five remaining reporting routes (all-evaluations, analytics, details-by-user, manager-subordinates-matrix, manage-criteria GET) plus update-admin-data (write-frozen 409 while a period is active). Pattern = matrix: one named active period, empty-state when none, optional `?period_id=` inspect.
- Closed CALCULATION_MAP defects on these routes: all-evaluations row multiplication (`DISTINCT ON` the upward join); details-by-user `detail_type` made real (unknown → 422); manager-subordinates-matrix `manager_score` by `evaluation_source='manager'` + actor-tree-only.
- Frontend: `ReportingRoute` (admin + c_level) on `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix`. HR dossier buttons hidden; TeamView dossier handlers unset. Period banners on the five screens.
- Auth Guard GET md5 `6ea30fc47b8f51180a4b963fdae79732` unchanged. Matrix, score-correction, submit/update/self-review/login not edited.
- Frontend `20260820T063333Z` (previous `20260819T203659Z` kept). Browser as Alexander with H1 temporarily active; proof writes rolled back.

**Results:**
- End state: evaluations 0, corrections 0, registered 1, sessions 1 (Alexander), H1 draft/inactive, invite id=4 unused, **33 workflows active**, 37 webhooks, 58 workflows total.
- 2025 fingerprint `21d323b0…` unchanged. Full report: `docs/REPORTING_SURFACE_2026-08-2x.md`.

**Notes / Gotchas:**
- `detail_type` now filters (`all` / `self` / `received_from_manager` / `from_subordinates` / `gave_to_manager` / `gave_to_subordinates`). `c_level_direct` as evaluator is listed under evaluations-to-subordinates.
- Analytics AVG formula unchanged; the number moved because rows are period-bound. Proof set: unbound 7.00 → H1 5.00. `period_trends` is 0–1 row for the shown period, not a history of both cycles.
- HR is not half-empty: statuses + employee table remain; company-wide dossier hidden. Typed `/admin` (criteria) is still AdminRoute; API 403.
- TeamView list still calls admin-only `admin-users-data` — pre-existing, not this brief.
- Login Keychain still 401; minted admin JWT for the browser pass. Alexander’s real session was not deleted.

## 2026-08-20 — Drafts UX: self-review + upward (D1 / D6 category / D7)

**What was done:**
- Reused `evaluationDrafts.js` (prefix `epe:evaluation-draft`, 7-day expiry) on self-review and upward. Keys: self `user:user`, upward `user:manager`. Manager modal unchanged.
- Copy: Russian plural «3 критерия»; modal «Категория: общие»; register greeting trimmed (DOM has no space before `!`).
- Frontend `20260820T065435Z` (previous `20260820T063333Z` kept). Browser: Alina self-review + upward refresh/401-relogin/submit; Akmyrat modal 6/8/7 no regression. H1 temporarily active, then draft.
- Proof rows rolled back. Alexander session `f443cfa5-…` kept. Invite id=4 unused.

**Results:**
- End state: evaluations 0, registered 1, sessions 1 (Alexander), H1 draft/inactive, 33 workflows active, 2025 fingerprint `21d323b0…` unchanged.
- Full report: `docs/DRAFTS_UX_2026-08-2x.md`.

**Notes / Gotchas:**
- Shared-computer leftover: logout/401 do not sweep draft keys (same as the manager modal). Forms do not leak into another account because keys include user id. Surface in the report — not changed.
- D3 / D8 / D9 and the upward grade chip were not touched.

## 2026-08-20 — Mail only to Alexander unless he confirms the recipient

**What was done:**
- Recorded Alexander’s rule: executors send mail only to `alexander@sedamedical.com` until he names another mailbox in that conversation.
- Wrote it as a hard constraint in `AGENTS.md`, D-0820-8 in `DECISIONS.md`, and HANDOVER §8.

**Results:**
- Future sessions must stop and ask before any employee verification code or SMTP test to a third party.

## 2026-08-20 — Docs hygiene (HANDOVER vs live)

**What was done:**
- Read-only live check of n8n `workflow_entity`, `epe_2026`, frontend `current`, certificate, and n8n image. No PUT, no deploy, no DB write.
- Rewrote `docs/HANDOVER.md` to the live snapshot (33 active / 58 total, 37 webhooks). Preserved §4 verbatim.
- Added this week’s one-line decisions to `DECISIONS.md`. Created `PROJECT_RULES.md` from compose + SSH-tunnel facts. Updated `AGENTS.md` to point at it. Closed brief-fixed defects in `bugs.md`; kept BUG-008; added leftovers.

**Results:**
- Live: users 89, registered 1, evaluations 0, H1 id=2 draft/inactive, invite id=4 unused, sessions 1, frontend `20260820T065435Z`, Auth Guard `updatedAt=2026-08-18T16:34:30.674Z`.
- Full report: `docs/DOCS_HYGIENE_2026-08-2x.md`.

**Notes / Gotchas:**
- Auth Guard GET md5 is not a stable check (reports quoted two hashes). Use `updatedAt`.
- `REPORTING_SURFACE` leftover list overstated employee-route period holes: `check-self-review`, `check-evaluated`, and `get-my-manager` already bind; `my-profile` and `evaluation-history` do not.

## 2026-08-20 — Shared invite vs one employee (docs check)

**What was done:**
- Read-only: `docs/SHARED_INVITE_2026-08-20.md`, `docs/INVITATION_WAVES.md`, `docs/LAUNCH_RUNBOOK_H1.md`, `AdminPeriods.jsx`, `create-invite` / `register` workflows. No live DB query this turn.

**Results:**
- «Получить ссылку» on Admin → Periods is the company-wide reusable invite (id=4 until 2026-09-18). Same URL for one person or for a wave. Identity is the work email already in `users`, not a per-person token. Live token status this turn: unverified.

## 2026-08-20 — User-facing copy & visibility audit (read-only)

**What was done:**
- Dumped the live n8n workflows from `workflow_entity` (repo `n8n_workflows/` is stale and was not used), the full `performance_db.criteria` catalogue, and the period-2 scope/roster from `epe_2026`. No PUT, no deploy, no DB write, no mail.
- Rendered `/login`, the registration-help and forgot-password modals, `/register` (no token) and `/reset-password` (no token) on a local vite server. Authenticated screens could not be rendered — 88/89 accounts have no password and the one registered account's password is unavailable — so all authenticated statements are code-derived and labelled as such.
- Wrote `docs/USER_FACING_COPY_2026-08-2x.md`: verbatim copy per journey and role (incl. out-of-scope registrant and read-only C-level), visibility & timing matrix with the query behind each cell, mechanics facts, and a separate executor-observations section.

**Results:**
- No period-close visibility gate exists anywhere; every artifact is either visible on submit or never.
- `API: Check Self Review` ignores `user_id` (`WHERE e.subject_id = ${actorId}`), so the manager form shows the manager their **own** self-review labelled as the subordinate's.
- `/api/hr/evaluation-status` is `hr/admin/c_level` only and is swallowed by `.catch` in `useDashboardData`, so a plain manager sees every subordinate as "nothing done".
- `has_manager_subordinates` is never set on the login user, so the `/team-scores` mid-level correction surface has no nav entry.
- `/api/criteria` has `required_roles: []` and no `c_level_only` filter — every employee can read the C-level criteria and all level texts.
- Subject-side confidentiality (manager score, upward score, per-criterion detail) is enforced in the browser only; `my-profile` + `evaluation-details` return the numbers to the subject.

**Notes / Gotchas:**
- `errorHandler.js` discards the server message for 401/403/429, so `NOT_IN_SCOPE`, `ROLE_FORBIDDEN` and `CAPABILITY_FORBIDDEN` all reach users as `Доступ запрещен. Недостаточно прав`.
- Read-only C-level (Cem/Hemra/Mekan) are blocked from evaluation forms by `can_evaluate=false`, but `API: Score Correction` never checks that flag — they can write `c_level` corrections.
- Nothing was fixed this session; the document is factual material for the architect's HR-level assessment.

## 2026-08-20 — Pre-launch visibility & user-facing correctness

**What was done:**
- Committed workflow/generator baseline (`2375005`) before editing.
- Server-side: gated `user_id` on check-self-review; sealed non-self scores/comments on my-profile; evaluation-details ownership (evaluator / admin / c_level / own self-review); employees payload gained three completion flags + `actor_is_in_scope`; c_level_only level texts stripped below admin/c_level; score-correction requires `can_evaluate`; `grade_coefficient` hidden below admin/c_level; Russian 400/404/409/422 strings.
- Frontend: dashboard flags from `/api/employees`; out-of-scope notice (exact copy); confirmation reminder; details-modal copy; per-criterion self-review comments in the manager modal.
- Proof on throwaway DB `epe_prelaunch_20260820_1328` + isolated n8n `:25679`. `npm test` 182/182. PUT 21 workflows; frontend `20260820T154749Z`.

**Results:**
- Live H1 still `draft,false`. Evaluations 0. Auth Guard `updatedAt=2026-08-18T16:34:30.674Z`. 33 active / 58 total. 2025 fingerprint `21d323b0…` unchanged.
- `/api/employees` remains direct-reports-only for every role including admin/c_level (no silent narrowing; matrix still covers c_level_direct beyond that list).
- Full report: `docs/PRELAUNCH_FIXES_2026-08-2x.md`.

**Notes / Gotchas:**
- Regression: check-self-review began ignoring `user_id` in the 2026-08-19 H1 Route Guard rewrite (`QRkUvs24DkcC3WBW`).
- 403 capability errors still surface via the interceptor, not the English workflow string.
- Live registered=2 / sessions=4 were already present before this PUT.
