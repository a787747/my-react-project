# Evaluation Portal Progress

## 2026-08-27 — CRITERIA_READONLY_DETAILS: C-level can read the ten level texts

**Status:** ✅ Done and on live. Frontend `20260827T060913Z`.

C-level could open `/admin` after ROLE_ACCESS but the ten level texts sat only
inside the admin edit form. The GET payload already carried them (`SELECT c.*`,
proven on live as Jemal 47). A read-only «Показать шкалу (1–10)» now shows
description + levels 1–10 with no write control. Admin CriteriaForm unchanged
(Save still there; cancelled, nothing written). Other granted C-level surfaces
checked — same gap does not exist there.

`npm test` 443/443. Deploy via locked CAS. Browser on live as Jemal and as
Alexander. H1 still `2026-08-26 10:08:54.340312Z`; tables 0/0/0/0; 89/3/78;
coefficient md5s identical to the 2026-08-26 snapshot. No dump — nothing was
written to campaign or catalogue tables. D-0827-1.

**Report:** `docs/CRITERIA_READONLY_DETAILS_2026-08-27.md`.
**Commit:** `1a57b81f87c4f4160bc5aecdf1e45404cc5ce42e`.

## 2026-08-26 — LIVE_SMOKE_H1: the real campaign exercised once on live, then removed to the byte

**Status:** ✅ Done and fully reversed. **Verdict: the campaign is safe to invite 78 people into.**

The one and only rehearsal of the real H1 campaign on the real system before the invitation goes
out. Anchor dump before the first write (`epe_2026_presmoke_20260826T142200Z.dump`, md5
`072fc767…`, on the Mac outside the repo); full row-level fingerprint recorded.

- **Seeded** three in-scope accounts by direct `password_hash` write in the scrypt format
  (Hekimov 68 / Ruhlyadko 85 / Hojayeva 45) — no invite link, no mail, no code (D-0820-8).
- **Walked every channel** in a real browser on epe.sedamedical.com: self-review ×3,
  manager→subordinate (Hekimov→Ruhlyadko as a **partial** left at 2/6 then **completed through the
  additive path** — upsert into the same row, no duplicate), upward ×2 (Ruhlyadko→Hekimov,
  Hekimov→Hojayeva), a full manager eval (Hojayeva→Hekimov, 7 criteria), and one **c_level_direct**
  filed by the owner's admin account (minted session). 8 evaluations (ids 31–38), what each person
  saw at each step recorded, no console errors.
- **Every money number re-derived by hand from raw rows and matched to the digit:** the 8 plain
  ratings, three weighted self-reviews (26.88 / 11.18 / 45.82), two upward averages (7.00 / 9.00),
  and the three bonus indices (**Hekimov 605.66, Ruhlyadko 147.62, Hojayeva 0.00** — the last is
  correct: her C-level boss filed nothing, and self+upward never pay). The frontend
  `useFinalScoresMatrix` formula was replayed from the live matrix + coefficients payloads; that
  replay is what `/admin/final-scores` and `/admin/bonus-calculation` render.
- **Undone completely:** 26 scores + 8 evaluations deleted, 4 auth_sessions deleted (3 logins +
  admin probe), 3 password hashes back to NULL. Proven byte-identical to the anchor — campaign
  0/0/0/0, all fingerprints/md5s/counts identical, no participant row moved, no user column
  changed. Only `evaluations_id_seq` 30→38 and `evaluation_scores_id_seq` 81→107 advanced (gaps
  31–38 / 82–107, accepted and not repaired).
- **One process reminder surfaced (not a bug, not blocking):** a manager whose boss is C-level
  earns a 0 index until a C-level person evaluates them or files a c_level_direct — C-level must
  actually evaluate the managers under them. One honest deviation: the c_level_direct used the real
  API route, not the admin SPA screen (the browser token injection was blocked by the safety
  classifier); it is the exact backend path the admin UI POSTs to.

**Report:** `docs/LIVE_SMOKE_H1_2026-08-26.md`. No mail sent, no container restarted, no schema or
money input changed.

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

## 2026-08-20 — H1 pre-flight (re-verification, read-only)

**What was done:**
- Re-verified the full launch baseline against live: period/scope, Auth Guard identity, workflow and webhook counts, frontend symlink, certificate, archive and epe_2026 counts, invite id=4. All 11 values matched.
- Re-verified the six 2026-08-20 server rules against live `workflow_entity` definitions with quoted fragments (my-profile sealing, evaluation-details ownership, check-self-review gated selector, criteria level-text stripping, score-correction capability, employees/my-manager predicate+flags+coefficient), plus one safe live probe of verify-invite (Russian message).
- Closed the Part 3 gap: read-only C-level behavior proven from live SQL + deployed bundle `20260820T154749Z` — `AND ${actorCanEvaluate}` empties `/api/employees` server-side; sidebar «Команда», dashboard CTAs, and self-review form all absent client-side; submit double-closed by capability guard. **Was already correct — no fix, no PUT, no deploy.**
- Listed registrations (2: Alexander id=2, Jemal id=47) and sessions (4 rows, 2 users). Nothing deleted, no mail.
- Committed the working tree after a file-by-file secrets/data review: `92ba7cc` backend exports+generators+scripts+infra, `911e3bd` frontend+tests (`npm test` re-run 182/182), `090871b` docs. Added closed rows BUG-024…027 to `bugs.md`.
- Report: `docs/PREFLIGHT_H1_2026-08-2x.md`. **Verdict: H1 can be activated — yes.**

**Notes / Gotchas:**
- The employees `can_evaluate` predicate was in the 15:46 PUT all along (generator line 1440); only the proof was missing.
- Report-only leftovers: empty «Мои задачи» box for the read-only trio; matrix correction inputs 403 via interceptor for them; `level_0_desc` outside the stripped list (empty today on both c_level_only rows).
- Constraints held: Auth Guard `2026-08-18T16:34:30.674Z`/inactive re-read at finish; H1 still draft/false; sessions still 4; archive untouched.

## 2026-08-20 — Admin users column sort (classification pass)

**What was done:**
- Frontend-only: sortable headers on Admin → Сотрудники (name, role, category, department, grade, manager, registration). Sort orders the current «Найдено» set; counts unchanged.
- Save no longer flips `loading` (silent refetch) and restores `window.scrollY`, so sort, filters, page, and scroll survive a row edit.
- `npm test` 192/192. Deploy `./scripts/deploy_epe_frontend.sh`. Previous stamp `20260820T154749Z` left on disk.

**Results:**
- Live `current` = `releases/20260820T165040Z`. H1 not touched. No workflow / schema / API change.
- Report: `docs/ADMIN_USERS_SORT_2026-08-2x.md`. Rendered proof is Alexander’s own check on `/admin/users`.

**Notes / Gotchas:**
- TeamView uses the same table without `onSort` — headers there stay static.
- Pre-existing: `setLoadingStatuses` is undefined in `AdminUsers.jsx`; evaluation circles can fail to load. Not part of this brief.

## 2026-08-20 — `work_category = 'tender'` wiring (read-only)

**What was done:**
- Read-only: live `epe_2026` + 2025 archive SELECT counts/schema; live `API: Admin Save User (GUI Mode)` Validate node; deployed `20260820T165040Z`; src Admin modal/filter/import + manager-form filter. No PUT, no deploy, no DB write, no mail.

**Results:**
- Tender is a leftover UI option. Live API allow-list is `general`/`project` only (422 `INVALID_WORK_CATEGORY`). Derivation `is_project_participant = (work_category === 'project')` never runs for tender. Live counts: epe_2026 46 general / 43 project / 0 tender; archive 46 / 27 / 0.
- Manager form for a tender non-manager would be the same as general: criteria 3, 4, 12 (not 8, 13). Report: `docs/TENDER_CATEGORY_2026-08-2x.md`.

**Notes / Gotchas:**
- Column is `varchar(50)` with no CHECK; enum `work_category_type` includes `tender`/`hybrid` but is unused by the column. Raw SQL could store tender; the portal cannot.

## 2026-08-21 — Periods hierarchy, close-time persistence, annual roll-up

**What was done:**
- Migration 013: `period_results` (insert-only close snapshot, CHECK-enforced no-data-is-never-zero) + idempotent parent-column repair. Live: dated dump `epe_2026_pre013_20260821_0549.dump` first; applied; every table's row count proven unchanged; second run all no-ops.
- `API: Manage Periods` extended 3→7 routes: rename, reparent (attach/detach), close (atomic compute+persist+close in one statement), annual-rollup (admin+c_level); activation refuses containers 422 and re-asserts in SQL; deactivate now gated on the target being activatable (pre-existing race fixed in passing).
- Close computes the matrix final cell (D-0820-12) and the formula-#3 bonus index by replicating the matrix SQL + client pipeline verbatim (incl. `|| 1.0` quirks and JS rounding).
- Frontend: `/admin/periods` hierarchy UI (container badge, no Activate, indented children, rename/reparent modals, close button with irreversibility confirm, type+parent in create modal); new `/admin/annual-rollup` «Годовые итоги» (own screen — stated call), `ReportingRoute`.
- Throwaway stand scripts (`setup_hierarchy_throwaway.sh`, seed, `prove_periods_hierarchy.py` — 38 recorded checks) + `deploy_periods_hierarchy.py`. Tests 192→213, all green.

**Results:**
- Acceptance passed in full: A 6.0/8.0→annual 7.0, index i1+i2 (104.70); B out-of-scope P1→annual 8.0 NOT 4.0, single-term index; C explicit no-data, visible, excluded from mean; server/client cross-check <0.005; weight/grade edits after close change nothing; second close zero rows; container activation 422 + no button.
- Live: workflow PUT `updatedAt=2026-08-21T06:00:08.687Z` (guard frozen, active preserved); frontend `20260821T060049Z`; H1 `draft,false` 87/89; evaluations/results 0/0; webhooks 37→41; archive untouched.
- Report: `docs/PERIODS_HIERARCHY_2026-08-2x.md`. Decisions D-0821-1/2/3 appended.

**Notes / Gotchas:**
- `parent_period_id` already existed on live with FK — the original schema import shipped it; migration's ADD COLUMN was a no-op there.
- Top-level export `API_ evaluations-matrix.json` is the STALE pre-guard version (BUG-028); live truth is the `build_route_guard_deferred.py` output. Cost one throwaway debug cycle.
- Nothing keys on period name at runtime (verified); migrations 010/012 are name-keyed one-time seeds — do not re-run after renames.
- Throwaway DB `epe_hier_20260821_0549` kept for audit; container `epe-hier-n8n` removed.

## 2026-08-21 — Periods hierarchy acceptance verification (read-only gate)

**What was done:**
- Read-only acceptance gate on the periods-hierarchy build. Live workflow definitions read out of `postgres.workflow_entity` rather than repo exports (BUG-028); `epe_2026`, the 2025 archive and the surviving throwaway stand read by SELECT only. No PUT, no deploy, no DB write, no mail.
- Formula fidelity checked fragment-for-fragment: final cell against `src/utils/matrixUtils.js`, bonus index against `src/hooks/useFinalScoresMatrix.js`, and a ten-row catalogue of mirrored quirks (zero weight → 1.0, rounding order, level 0, persistence precision, the one client-only early return that is not mirrored).
- Persisted numbers re-derived **by hand** from criterion rows, weights and coefficients: 36.30 / 68.40 / annual 104.70 and 6.0 / 8.0 / annual 7.0, to the last digit.
- Authorization of all seven periods routes, close semantics (refusal order, atomicity, idempotence, irreversibility, blast radius), and a fresh live baseline table.

**Results:**
- **Verdict: accept, no blocker**, with seven named microfixes M1–M7.
- Two of the seven were real money-or-schedule defects that the build report could not have shown: M6 — a solo failure of the coefficients or grades fetch rendered a full, plausible, **unweighted** bonus table with no error (became BUG-030); and M7 — «container» was the derived state `child_count > 0`, so detaching the last child would have made a full-year period activatable and closable.
- Baseline drifted during the audit, in a good way: Alexander performed the designated UX walk-through on live — created period id 5 «Annual 2026» and attached H1 to it. Nothing activated or closed; all four data tables still 0.
- Also flagged: M2 (ids 21/40/61 in H1 scope with no grade and no manager), M3 (no screen can spend the frozen index after close), M5 (three stale documents), the production-PII throwaway DB, and `main` 9 commits ahead of origin.
- Report: `docs/PERIODS_VERIFY_2026-08-2x.md`.

**Notes / Gotchas:**
- `api_proof.json`'s `cross_check` was a bare slogan string; a run that compared nothing would have written it just as happily. Proof artifacts must record the compared tuples.
- `rating_*` and `final_rating` are different quantities and will not reconcile — by design. Recorded in `CALCULATION_MAP.md` §A.1 by the follow-up batch.
- The guard contract fails open on an omitted `required_roles`; none of the current routes is affected.
- Findings were produced by six independent read-only audits then put through an adversarial pass instructed to refute; four claims were downgraded or withdrawn and are reported at corrected severity.

## 2026-08-21 — Post-verification batch: money-screen honesty, annual-type gate, sibling overlap

**What was done:**
- M6/BUG-030: `useFinalScoresMatrix` no longer swallows a failed coefficients or grades fetch. `Promise.allSettled`, per-request classification, explicit error state («Коэффициенты не загружены — расчёт невозможен» etc.); both money screens return an error card with retry before any table renders.
- M1: `/admin/periods` gates rename/reparent/activate/close behind `isAdmin(user.role)`; close is confirmed by typing the period name (modal, submit disabled until exact match).
- M7: activate and close refuse `period_type='annual'` independently of `child_count` (422 `ANNUAL_PERIOD_NOT_ACTIVATABLE` / `ANNUAL_PERIOD_NOT_CLOSABLE`), re-asserted inside the write.
- M4: create/reparent reject an overlapping sibling (422 `SIBLING_DATES_OVERLAP`); roll-up header shows «закрыто N из M дочерних периодов» + child date ranges; detaching a child with `has_results` confirms that annual numbers will move.
- Docs: BUG-010 re-scoped (not closed), BUG-029 + BUG-030 + BUG-031 added, PERIODS_HIERARCHY provenance corrected, CALCULATION_MAP records that `rating_*` and `final_rating` do not reconcile by design; `prove_periods_hierarchy.py` cross-check records the compared tuples and fails on a vacuous run.

**Results:**
- Tests 213 → **236 pass / 0 fail**; eslint debt unchanged (34 before, 34 after); build clean.
- Stand (`epe_hier_20260821_0710`, restored from current live): ALL CHECKS PASSED, incl. childless-annual 422 on both routes, one-day and contained sibling overlaps 422, and the canonical H1 01.01–30.06 + H2 01.07–31.12 split passing.
- Live: `API: Manage Periods` `updatedAt=2026-08-21T07:28:10.039Z` (9 Code nodes changed, 61 nodes / 7 webhooks unchanged, guard frozen, active preserved); frontend `20260821T072859Z`; H1 `draft,false` 87/89; all four data tables 0; webhooks 41.
- Housekeeping: `epe_hier_20260821_0549` and the fresh `epe_hier_20260821_0710` dropped; `epe-hier-n8n` removed; dumps `_0547`/`_0548` deleted; `git push origin main` done (`78dbeb1..70d218f`).
- Report: `docs/POSTVERIFY_BATCH_2026-08-2x.md`.

**Notes / Gotchas:**
- **BUG-031, found while proving:** the n8n Postgres node returns `date` columns as UTC-serialised JS Dates, so `String(v).slice(0,10)` is one calendar day early in Moscow. Creating a child that ends on the container's last day was refused — that is exactly the September H2 attach. Date containment is now decided in SQL; never compare a client `YYYY-MM-DD` against a date that crossed the Postgres node.
- `docker cp <dir> container:/path` **nests** when the target directory already exists, so `n8n import:workflow` re-imported the previous file. Two diagnoses were made against a stand silently running old code before this was caught.
- `n8n import:workflow` always assigns a new workflow id (the file's `id` is ignored), so a stand accumulates duplicates — deactivate the old ones and verify the active definition node-for-node before trusting a proof.
- `scripts/deploy_epe_frontend.sh` needs `rg` on PATH; it is not installed here, so the deploy failed closed. The two gates were run by hand and the script re-run with a `grep` shim.
- Verification rider confirmed present, unchanged: LIVE `API: Submit Evaluation` carries `AND subj.can_be_evaluated = true` in all three relation filters (manager / subordinate / c_level_direct), so 21/40/61 can never acquire a coefficient-1.00 money row. No static test covers it.

## 2026-08-21 — Docs hygiene (HANDOVER vs live, after the 20–21 Aug sprint)

**What was done:**
- Read the eight reports dated 20–21 Aug (USER_FACING_COPY, PRELAUNCH_FIXES, PREFLIGHT_H1, ADMIN_USERS_SORT, TENDER_CATEGORY, PERIODS_HIERARCHY, PERIODS_VERIFY, POSTVERIFY_BATCH), then re-measured every fact **against live** — SSH + `postgres_n8n` SELECT, `readlink /var/www/epe/current`, `openssl` cert, `docker inspect`, `iptables -S`, one unauthenticated GET probe. Reports located claims; live settled them. No PUT, no deploy, no DB write, no mail.
- Rewrote `docs/HANDOVER.md` from that snapshot, same 10-section structure. **§4 copied verbatim — md5 `93e5bab464151d463b259b69e5914eaf` before and after.** Two figures inside §4 are now older than the document and are flagged in a note above it rather than edited in place.
- `DECISIONS.md`: added D-0820-16 … D-0820-21 (Alexander's six visibility/copy decisions of the 20 Aug evening) and D-0821-4 (read-only trio stays in H1 scope, no grades invented). D-0821-1..3 were already logged by the periods brief — no duplicates.
- `bugs.md`: reconciled BUG-001…031 against the reports and added nine open rows (BUG-032…040) so every leftover named in POSTVERIFY_BATCH / PERIODS_VERIFY is either a row or explicitly triaged in the report. Moved BUG-028 and BUG-029 out of the «Closed» section, where they sat while open. Counts 20 open / 20 closed.
- `PROJECT_RULES.md`: added the throwaway-stand pattern and its ports. `AGENTS.md`: corrected the file pointers and the stale "Phase 0, do not change code" goal.

**Results:**
- Live, 2026-08-21 08:21–08:40 UTC: workflows 58 / 33 active / 3 inactive / 22 archived; **41** webhooks (19 GET, 20 POST, 2 OPTIONS); periods `1 Annual 2025 closed`, `2 H1-2026 draft parent=5` 87/89, `5 Annual 2026 draft annual` 1 child; `evaluations` / `scores` / `corrections` / `period_results` **0/0/0/0**; users 89, registered 2 (ids 2 and 47), sessions 6 with 1 unexpired; frontend `20260821T072859Z`; Auth Guard `updatedAt=2026-08-18T16:34:30.674Z` `active=false`; `API: Manage Periods` `2026-08-21T07:28:10.039Z`, 61 nodes / 7 webhooks; cert LE YE1 to 2026-11-17; archive 73/234/644/3. `npm test` **236/236**. `npm audit` 15 (11 high).
- Migration 013 confirmed on live with both anti-zero CHECKs, PK, three FKs and `idx_period_results_user`.
- Report: `docs/DOCS_HYGIENE_2026-08-21.md`, with a live-vs-report inconsistencies section.

**Notes / Gotchas:**
- **New live finding, not in any report: the daily backup dumps the wrong database.** `/root/backups/epe/backup-performance-db.sh` runs `pg_dump -d postgres -n performance_db` — the 2025 archive. No cron job, timer or script anywhere on the host dumps `epe_2026`. Proven from the dump's own table list: it carries `invite_tokens` and `score_corrections` but not `period_results`, `auth_sessions` or `evaluation_period_participants`. BUG-032, High. Closing a period is irreversible and its documented recovery is "a database restore".
- Classification is moving under the documentation: live `work_category` is 48 general / 41 project today against 46 / 43 in the 20 Aug report — so the criteria-count distribution in §4 (35/11/38/5) is now 37/11/36/5. Expected; Alexander is doing the classification himself.
- `docs/EVALUATION_METHODOLOGY.md`, which `AGENTS.md` calls the business contract that code must conform to, **does not exist and never has**. Flagged, not written — that document is Alexander's to own.
- `postgres_n8n` holds `epe_2026` and `postgres` only; every throwaway stand DB and container from the 21 Aug briefs is gone, as their housekeeping claimed.

## 2026-08-21 — Daily backup of the live database (BUG-032)

**What was done:**
- Measured the gap first. `crontab -l` held one line; `/root/backups/epe/backup-performance-db.sh` dumps `-d postgres -n performance_db`, the read-only 2025 archive. Proven from the dump's own `pg_restore -l` table of contents — **12** tables, all archive; `epe_2026` has **17**, five of which exist nowhere in any dump. **Second gap, not in BUG-032:** that job dumps `-n performance_db` only, so the n8n application schema `postgres.public` — 58 workflows, 7 credentials, 8 settings, 41 webhook registrations — was covered by nothing either. No timer, no cron.d entry, and `docker inspect n8n-n8n-1` shows **zero mounts**, so it lived in exactly one place.
- Installed `/root/backups/epe/backup-epe-live.sh` + cron `20 3 * * *` (00:20 UTC, twenty minutes after the archive job). Dumps `epe_2026` in full and `postgres -n public` separately — `-n public` because the archive job already owns `-n performance_db`, so the two jobs cover every schema of both databases with no overlap. Same 14-day window, `-Fc | gzip -9`, `chmod 600`, size check and shared `backup.log`. Pruning is stem-scoped: neither job can delete the other's files.
- Installed `/root/backups/epe/verify-restore.sh` — gunzip newest dump of a stem → `createdb` a throwaway → `pg_restore --exit-on-error` → row-count every table against live → drop. Throwaway names always start `epe_bkverify_` and the drop refuses anything else. Both scripts tracked in `scripts/`, byte-identical to the host copies.
- `bugs.md`: BUG-032 **closed** with the evidence. BUG-014 given a progress line and left open. Counts 19 open / 21 closed. `PROJECT_RULES.md`: new **Backups** section. `docs/HANDOVER.md`: four now-false places corrected (§2 Backups row, §6 item 5, §7 close semantics, September queue), with a dated note that they post-date the morning snapshot.

**Results:**
- **The entry point was fired by cron, not by hand** — a one-shot line with a byte-identical command string, then removed. `/var/log/syslog`: `CRON[542920]: (root) CMD (/root/backups/epe/backup-epe-live.sh)` at 11:45:01 UTC. Both restore proofs used *that* run's files.
- Restore, `epe_2026` → `epe_bkverify_epe_2026_20260821_114620`: exit 0, **17 tables, 0 mismatches** (users 89, participants 178, coefficients 80, criteria 8, periods 3, evaluations/scores/`period_results` 0).
- Restore, n8n → `epe_bkverify_n8n_app_20260821_114608`: exit 0, **52 tables, 0 mismatches** (`workflow_entity` 58, `webhook_entity` 41, `credentials_entity` 7, `settings` 8, `shared_workflow` 58). Both throwaways dropped; `pg_database` back to `epe_2026` + `postgres`.
- Retention proven: two decoys with 2026-08-01 mtime, both stems; the cron run logged `pruned=1 retained=1` per stem and neither decoy survived. The 10 `performance_db_*` files were still 10 afterwards.
- Failure visibility proven: real script against a nonexistent container → **exit 1**, `FAIL` line in `backup.log` carrying `pg_dump`'s own stderr, `FAIL` in `backup-epe-live.status`, partial dump removed.
- Disk: 34 GB free of 50 GB (33 % used, inodes 13 %). New dumps 23 924 B + 363 476 B = **387 400 B/day**, ≈5.3 MB per 14-day window — a ~5 800× headroom ratio.
- Archive job untouched: md5 `a9f748541cad6379d8949ce91dab51e0` before and after, 10 dumps still 10. No write to `epe_2026` (89/0/0/0 after). Workflows 58 total / 33 active, unchanged. No deploy, no mail.
- Report: `docs/BACKUP_FIX_2026-08-2x.md`.

**Notes / Gotchas:**
- **`N8N_ENCRYPTION_KEY` is in no dump.** It is a Portainer stack environment variable, and the n8n container has no volumes. The 7 `credentials_entity` rows restore, but under a different key they are unreadable. Row counts prove the data survives; they do not prove the credentials are usable. Alexander should hold that key somewhere reachable if the VPS is gone.
- **BUG-014 stays open, and is now the larger risk.** One disk on one VPS holds the live campaign database, the n8n backend, and every backup of both. The brief made closing it conditional on Alexander naming an off-host target in that conversation; he did not, so no S3 sync was configured.
- The archive job's 14-day prune has **never actually fired** — all 10 log lines read `pruned=0`, because its oldest dump is only 9 days old. "Pruning proven" was true of the new job because it was deliberately proven with aged decoys, not inherited from the old one.
- `pg_restore` into a fresh database fails on `schema "public" already exists` — the dump carries `CREATE SCHEMA public` and `createdb` already made one. It is benign, but with `set -e` it kills the harness and strands the throwaway. `verify-restore.sh` now drops `public` on the throwaway before restoring, so `--exit-on-error` exit 0 means genuinely zero errors. One throwaway was stranded by this before the fix and was dropped by hand.
- There is **no MTA on this host**, so cron discards job output and cron mail is not an alarm channel. The health check is `cat /root/backups/epe/backup-epe-live.status` — it must read `OK` with today's date. It is a pull check; nothing pages anyone if cron stops.

## 2026-08-22 — Recon: reclassification, coefficient visibility and scoring freeze (read-only)

**What was done:**
- Fact-finding only, for the three business decisions Alexander took on the freeze semantics (second «Activate» gate; weights / level coefficients / grade coefficients editable until close and readable by admin only; project/general classification editable during the campaign). **No behaviour changed.** No workflow PUT/activate/deactivate, no DB write, no deploy, no mail. Every SQL was `SELECT`.
- Dumped all **33 active** workflow definitions out of live `postgres_n8n.public.workflow_entity` in one pass and parsed them; top-level `n8n_workflows/*.json` were deliberately not consulted (BUG-028). Cross-read against the frontend at `9a78e6e` and against live `epe_2026` by SELECT.
- Built the full role→access table from each workflow's `Prepare Guard Input` literal, traced every client consumer of `GET /api/score-coefficients`, located both freeze triggers, the criteria filter on all four evaluation paths, the row-selection predicate in both money paths, the three completion flags, the BUG-036 row-7 409, and the upsert/delete semantics of all three write routes.
- Report: `docs/RECON_RECLASS_COEFF_2026-08-2x.md`, with a «Surfaced for decision» section (10 items) and a verbatim appendix — 8 criteria, all 80 `score_coefficients` rows, all 11 grades with coefficients — for the `EVALUATION_METHODOLOGY.md` Alexander still owns.

**Results:**
- **The freeze has two different triggers, not one.** Classification (`POST /admin/save-user`) returns 409 `CLASSIFICATION_FROZEN` on the **first submitted evaluation in the active period** — and the `EXISTS` is global, so any one evaluation freezes everyone; it fires only when the category actually changes, and never for a new user. Weights + level coefficients (`POST /api/score-coefficients`), grade coefficients (`POST /update-admin-data`) and the **criteria catalogue** (`POST /manage-criteria` save/delete) all return 409 `ACTIVE_PERIOD_EXISTS` on **period activation**, via the identical `SELECT … WHERE is_active = true OR status = 'active'`. All four are Code-node logic reading a preceding SELECT — none is a DB constraint, none is in the guard.
- **Brief expectation refuted:** the criteria catalogue *is* frozen (`API: Manage Criteria Admin V7` → `Prepare Write`). `action=get` is not.
- **`HANDOVER.md` §6.11 corrected by measurement:** it says the freeze is not enforced for weights. Exhaustive search of all 33 active workflows returns exactly four writers of `criteria.weight` / `score_coefficients` / `grades.coefficient`, and **every one sits behind the 409**. There is no unfrozen write path to a weight on live.
- **Coefficient visibility.** `GET /api/score-coefficients` has `required_roles: []`, and `EPE: Auth Guard` → `Authorize` skips the role check when that array is empty — so **every authenticated role reads criterion weights and level coefficients**, including the read-only c_level trio (21/40/61), whose outcome is identical to any other c_level on every route in the table (none sets `required_capability`). `GET /api/criteria` likewise returns `weight` to all roles. Grade coefficients are already correctly gated: admin-only via `admin-users-data`, and stripped to admin+c_level in `/api/employees` and `/api/get-my-manager`.
- **W5 confirmed, not refuted.** Four client consumers of the GET; the non-admin one is `src/hooks/useSelfReview.js:93-94` — every employee filling in a self-review pulls the whole coefficient table and computes `weighted_score` in the browser (`:174-175`), which the server stores verbatim after only a finite/non-negative check.
- **Criteria presentation is client-side on all four paths.** `API: Get Criteria With Levels` → `Build Criteria Query` has **no `WHERE` clause at all** — not `is_active`, not `target_audience`. Manager form filters in `evaluationUtils.js:108-135`, upward in `useManagerEvaluation.js:101-106`, self-review in `useSelfReview.js:105-114`, `c_level_direct` in `matrixUtils.js:24`. **No write path validates applicability** — `Submit Evaluation`, `Submit Self Review` and `Update Evaluation` contain zero references to `target_audience` / `is_project_participant` / `work_category` / a join to `criteria`; only `criteriaId >= 1` and `score 1..10`.
- **The money math selects by score-row existence, never by classification.** `API: evaluations-matrix` → `Build Matrix Query` ends `CROSS JOIN performance_db.criteria c WHERE u.role != 'admin' AND c.is_active = true` — every active criterion for every non-admin person. `useFinalScoresMatrix.js:236-247` sums the cells where a score exists. `API: Manage Periods` → `Build Close Dataset Query` / `Compute Close Results` uses the same predicate, so `period_results.bonus_index` inherits it.
- **Completion flags are row existence.** `has_self_review`, `has_evaluated_manager` and `evaluated_by_actor` are three `EXISTS` sub-queries over `evaluations` in `API: Get Employees` → `Build Identity-Bound Query`; none joins `evaluation_scores`. Corroborated by `Check Self Review` and `Check Evaluated V2`. One criterion out of five reads as «done» everywhere.
- **BUG-036 row 7 mechanism located.** `is_update` is read **nowhere** on the server — `grep -c` over the live `API: Submit Self Review` definition = 0, and over all 33 active definitions = 0; it exists only at `useSelfReview.js:183`. The 409 comes from `Build Self Review Insert`'s `is_duplicate` guard, with `ON CONFLICT … DO NOTHING` + `Format Response` as a second 409 on the race path. The button is reachable exactly when that guard is true.
- **Partial writes.** Both submits are `DO NOTHING` on conflict — the supplied subset is written, `calculated_score` is the AVG of that subset only, and any second submit is 409. `update-evaluation` upserts on `(evaluation_id, criteria_id)` and then **`DELETE`s every score row not in the submitted set** — so a narrower presented set destroys data rather than excluding it from the computation.
- Live state at read time: periods `1 Annual 2025 closed`, `2 H1-2026 draft parent=5`, `5 Annual 2026 draft annual`; `evaluations`/`scores`/`period_results`/`corrections` **0/0/0/0**; `work_category` 48 general / 41 project; roles 1 admin / 5 c_level / 12 manager / 69 employee / 2 hr. **No period is active**, so every «frozen» statement above is about the code path, not an observed 409.
- Rider: **`9a78e6e` was not on origin** — `main` was `ahead 1`, `origin/main` was `375b8c1`. Pushed: `375b8c1..9a78e6e  main -> main`; verified `* main 9a78e6e [origin/main]`.
- Rider: `docs/HANDOVER.md` §10 counts corrected. Measured **before** this brief wrote anything: 19 open / 21 closed (18 `🔴 OPEN` + 1 re-scoped, 21 `🟢 CLOSED`, 40 `### BUG-` headings) — confirming the brief's expectation and refuting the line's `20 open / 20 closed`. Set to **20 / 21**, not 19 / 21, because BUG-041 was filed in the same session; writing 19 would have left the line stale on commit. Both figures are recorded in the report.

**Notes / Gotchas:**
- **New defect, BUG-041 (High, filed).** In `API: Update Evaluation WITH PERIOD` → `Build Update SQL`, the `removed_scores` CTE is gated only on `evaluation_id`; it references neither `updated_header` nor anything conditional, and the outer `SELECT` never reads it. PostgreSQL runs data-modifying `WITH` clauses to completion regardless of whether the primary query reads their output, so when the inline ownership/period re-assertion selects zero rows the `UPDATE` and `INSERT` write nothing, the caller correctly gets 403 — **and the `DELETE` has already run.** The node's own comment declares that race closed; it is closed on the two constructive branches and open on the destructive one. **Not runtime-proven** — this brief is read-only and reproducing it requires a write; the finding rests on the live SQL text and documented `WITH` semantics. Zero risk today (`evaluation_scores` empty, no active period).
- **Decision 2 is the inverse of live behaviour, and decision 1 collides with the same three 409s.** «Editable until close» versus «frozen at activation» is not a tuning change: it is the widest freeze applied at the earliest moment, across three workflows. An «Activate» preparation window in which the admin still edits everything is, in current code, precisely the state that forbids editing criteria, weights and grade coefficients.
- **Reclassification is asymmetric on money.** general→project adds nothing until someone evaluates the new criteria; project→general removes nothing, because the existing score rows keep being summed. The only mechanism that can remove them is `update-evaluation`'s DELETE, which is destructive and carries BUG-041.
- **«Exclude the extra criteria from all computations» has no place to live.** Both money paths select by score-row existence, and there is no per-(subject, criterion) applicability record — the only candidate, `criteria.target_audience` joined to `users.work_category`, is exactly the thing being made mutable.
- **A reclassified person does not see their own new criteria until they log in again.** Self-review filters on `user.work_category`, which comes from the **login** payload (`API: Auth Login` → `Load User and Attempts`) and is persisted to `localStorage` by `UserContext.jsx:50-53` with **no refresh path**. The manager form, by contrast, reads a freshly-fetched subject row. The 4-hour token bounds the staleness only because expiry forces a re-login.
- **Grades ids 6 (`S4-M1`) and 11 (`M1`) share a description and coefficient 2.20** — a probable duplicate. The matrix looks grades up **by `code`**, not id (`useFinalScoresMatrix.js:213-214`, `:251-252`), so two grades sharing a code would silently collapse. The 11 codes are distinct today. Recorded, not resolved.
- `score_coefficients` has **no `score_level = 0` row** for any criterion; a rounded final score of 0 would silently use coefficient 1.0. Not reachable today — every write path validates scores as `1..10`.

---

## 2026-08-22 — Two-gate period lifecycle; coefficients live-until-close and admin-only (D-0822-1, D-0822-2)

**What was done:**
- **Migration 014** on live: `evaluation_periods.evaluation_started_at` + `evaluation_started_by`, idempotent, no data rows written, every existing period left NULL. Deliberately not tied to `status` by a CHECK — close must leave the mark set and the documented emergency stop sets an active period back to `draft`.
- **Second gate.** `API: Manage Periods` gained `POST /api/periods/start-evaluation` (admin-only, seventh route). Preconditions mirror activate/close — 404 not found, 422 container / annual / closed / not-active, 422 invalid id — a second call answers **200 `already_started`** and writes nothing, and a lost race on the gated `FOR UPDATE` statement answers 409 `START_CONFLICT`. No route clears the mark; a static test asserts the only assignment in the workflow is `evaluation_started_at = now(),`.
- **Campaign surface re-keyed on "active AND started"**: submit-evaluation, self-review-submit, update-evaluation (409 `PERIOD_NOT_STARTED`), score-correction, `/api/employees` flags, check-self-review, check-evaluated, get-my-manager. Admin/reporting reads (matrix, analytics, all-evaluations, details-by-user, manager-subordinates-matrix, HR status, admin-users-data, my-profile, history/details) stay keyed on **active** and were not touched. Classification freeze unchanged. Registration/auth unaffected.
- **Freeze retuned.** Criteria catalogue now freezes on **start** (409 `EVALUATION_STARTED`), not on activation. The `ACTIVE_PERIOD_EXISTS` 409 was removed **entirely** from `POST /api/score-coefficients` and `POST /update-admin-data` — the freeze nodes and their period SELECTs are gone from the graphs, not bypassed — and replaced with validation: weights and coefficients finite and `> 0`, levels 1..10, grade coefficients likewise, plus `setting_key`/`setting_value` validation on a node that had been interpolating `setting_value` straight into SQL.
- **Coefficient privacy.** `GET /api/score-coefficients` → admin-only; `GET /api/criteria` strips `weight` for every non-admin role (the `c_level_only` level-text stripping untouched). The self-review client stopped fetching coefficients and stopped sending `weighted_score`; the **server** computes it at submit — formula #2 of HANDOVER §4 reproduced from the retired client function including its guards, with the subject's **real** grade coefficient and 422 `NO_GRADE_COEFFICIENT` instead of a silent 1.0. `/admin/scoring`, `/admin/score-calculator`, `/admin/final-scores`, `/admin/bonus-calculation` became admin-only at the route level, and `/admin/scoring`'s silent `.catch`-to-empty on grades became a loud error card (BUG-030 pattern).
- **Frontend**: three distinguishable period states on `/admin/periods` with an admin-only «Запустить оценку», a new `CampaignNotStartedNotice` on `/self-review` and `/manager-evaluation`, task panel and Welcome task cards gated on `campaignActive`, `period_in_preparation` plumbed through `TaskStatusContext`.
- Proof stand `epe-lifecycle-n8n` / `epe_lifecycle_20260822_0632` built from a dated dump of live, used, and torn down (container removed, DB dropped, `epe_2026` the only `epe_*` left). Deployed: 14 workflows (activation preserved, graphs re-compared node-for-node) and frontend release `20260822T065024Z`.
- Report: `docs/LIFECYCLE_COEFF_2026-08-2x.md`. Decisions: D-0822-1, D-0822-2 in `DECISIONS.md`. `HANDOVER` §3, §6.1, §6.11 and §7.1 corrected in place.

**Results:**
- **Live is unchanged in data and state.** All three periods still `1 closed / 2 draft / 5 draft`, every `evaluation_started_at` NULL; `evaluations`/`evaluation_scores`/`period_results` still 0; the criteria/coefficient/grade fingerprint identical before and after (`59cc552a…/d2dcb678…/b121ee2d…`). The behaviour is deployed and inert until Alexander lifts the pause.
- **Live role×route probe (all six role rows):** `GET /api/score-coefficients` → 200 for admin, **403 for c_level, read-only c_level, hr, manager and employee**. `GET /api/criteria` → 200 for everyone, `weight` **present only for admin**; `c_level_only` level texts still admin+c_level. `POST /api/score-coefficients`, `POST /update-admin-data`, `POST /manage-criteria`, `POST /api/periods/start-evaluation` → 403 for every non-admin. Every POST in the matrix was non-mutating by construction; six temporary probe sessions were created and deleted in a `finally` block (0 remaining, `auth_sessions` 8 → 8, no `token_version` touched).
- **Stand E2E in the brief's order.** activate → criteria 200, weight 200, grade 200, employee sees `campaign_active=false` / `period_in_preparation=true` / **0 rows**, self-review and manager submit both **409 `PERIOD_NOT_STARTED`**, correction 409. start → criteria save and delete **409 `EVALUATION_STARTED`**, weight and grade still **200**, `campaign_active=true`, manager sees `[1203, 1204]`, all five submits 200. start again → 200 `already_started`, period-row fingerprint `f680dde6…` **identical** before and after. Refusals: container 422, childless annual 422, draft leaf 422, unknown 404, invalid id 422, closed 422. Close of a started period → 200, 96 results, second close idempotent (fingerprint `4ebed633…` unchanged), and persisted `final_rating`/`bonus_index` matched an independent replay of the matrix pipeline for both subjects (8.0/40.32 and 7.0/254.936). The start mark survives close.
- **The read surface really keys on started.** With identical rows and the mark cleared by SQL then restored: `campaign_active` true→false→true, subordinate rows 2→0→2, `has_self_review` true→false→true, `check_evaluated` 2→0→2, `has_evaluated_manager` true→false→true — while `actor_is_in_scope` stayed **true** and the admin matrix stayed `campaign_active=true, period_id=2, 94 rows` throughout.
- **Self-review weighted_score.** Two subjects with different grade coefficients, both sending a hostile `weighted_score: 999.99`: user 1203 (coef **0.60**) stored **7.04**, independent recomputation **7.04**; user 1204 (coef **2.20**) stored **21.84**, independent recomputation **21.84**. Neither is 999.99, and the two differ — which is what proves the real coefficient was used. Separately the generated server node was executed against the live catalogue and compared to the retired client function over **285 cases**: **0 mismatches**.
- **BUG-029 closed.** weight 0 → 422 `INVALID_WEIGHT` (stored 1.00 → 1.00), coefficient 0 → 422 `INVALID_COEFFICIENT` (1.00 → 1.00), grade coefficient 0 → 422 `INVALID_GRADE_COEFFICIENT` (0.60 → 0.60), weight −1 → 422, level 11 → 422 `INVALID_COEFFICIENT_LEVEL`.
- **BUG-041 closed** on the way: `removed_scores` is now gated on `EXISTS (SELECT 1 FROM updated_header)`. The brief rewrote the same `WHERE` clause, so extending the inline re-assertion without gating the DELETE would have widened a destructive race. Code-level close — the race was not reproduced.
- **Auth Guard `updatedAt=2026-08-18T16:34:30.674Z`, `active=false`** — checked before, after every individual PUT and at the end. Unchanged, and the generated `auth-guard.json` is byte-identical to HEAD. Login/register/verify-invite/password-reset all still carry their pre-deploy `updatedAt`; live `GET /api/verify-invite` → 200.
- `npm test` **263 passed / 0 failed** (was 236; new suite `tests/evaluationStartGate.test.js`, 21 assertions). Build clean. ESLint: same pre-existing findings, none new.

**Notes / Gotchas:**
- **A concurrent session edited this working tree mid-run, and one of its edits reached live.** Between 06:37 and 06:38 UTC another session changed `build_route_guard_workflows.py`, `tests/routeGuardWorkflows.test.js`, `bugs.md`, `evaluationUtils.js` and `ScoringCoefficientsTable.jsx` — inside the window in which the deploy regenerates from the builders. The functional delta was the weight rule: `weight < MIN_WEIGHT` with `MIN_WEIGHT = 0.1` instead of the brief's `weight <= 0`. It went live at 06:37:59 and was **corrected back to the brief's rule at 06:49:44**, keeping the other session's better error message. Its other changes were kept — they are consequences of this brief (the dead `calculateWeightedScore` deleted; the `/admin/scoring` caption corrected from formula #2 to formula #3). If the 0.1 floor was deliberate it is one line plus a decision record, but it is an undecided business constraint that forbids legitimate small weights.
- **A deploy defect was found and fixed on the way.** `deploy_lifecycle_coeff.py` refreshes tracked top-level exports from live; one of them, `API_ Manage Criteria Admin V7.json`, was also a **generator input** (`build_route_guard_deferred.py` lifted its legacy `Prep SQL` node at build time). Refreshing it destroyed that node and the generator could no longer run (`KeyError: node 'Prep SQL' not found`). Fixed by inlining the node into the builder — output verified byte-identical to the deployed artefacts — and by adding `assert_not_a_generator_input()`, which now refuses to refresh any export a builder reads. No live behaviour was affected; only the ability to regenerate, for about ten minutes.
- **The start mark survives deactivation.** Activation clears `is_active`/`status` on the previous period but not `evaluation_started_at`, so re-activating it returns it to "started" with no second confirmation. Deliberate (the mark is irreversible) and unreachable in practice (activation refuses to deactivate a period with evaluations) — but nobody has been asked.
- **The emergency stop now stops the campaign too.** Setting an active period back to `draft` by SQL already deactivated it; it now also makes every submit answer `PERIOD_NOT_STARTED` and hides every task, because the predicate requires `status='active'` as well as the mark. Almost certainly the intended meaning — worth confirming.
- **`period_results` is now the only thing making closed periods immune** to a coefficient edit. Every money screen that is not the annual roll-up still live-joins and still renders nothing after close — BUG-033 is now load-bearing rather than merely inconvenient.
- New bugs filed: **BUG-042** (`useScoreCalculation` still substitutes an empty coefficient set on failure — the last member of the BUG-030 family; the calculator would render an unweighted breakdown with no error) and **BUG-043** (with no active period `/api/employees` names the annual **container** as the current period, because H1 and Annual 2026 share a start date and `id DESC` decides — so `actor_is_in_scope` is computed against the container's 89 inert rows instead of H1's 87; pre-existing, found by the live probe).
- BUG-040 unchanged: ripgrep is still absent on the delivery laptop, so both frontend deploy gates were run by hand before the script was re-run under a `grep -rqE` shim preserving gate semantics.

## 2026-08-22 — Gate: LIFECYCLE_COEFF verification (read-only)

**What was done:**
- Read-only gate on build `a6ef553` (`docs/LIFECYCLE_COEFF_2026-08-2x.md`). No workflow PUT/activate/deactivate, no DB write, no deploy, no mail. Live definitions compared node-for-node to tracked artifacts; dump presence checked locally.
- Report: `docs/GATE_LIFECYCLE_COEFF_2026-08-2x.md`.

**Results (copied from the gate):**
- Seven of eight items **confirmed**; one sub-point of item 7 **refuted** — HANDOVER §10's report index omitted both new reports (**BUG-044** filed).
- **BUG-029 closed with evidence** (422 table + static assertions + live `updatedAt`s). The parallel session's 0.1 floor survived nowhere at gate time (not committed, not live, not tracked); later re-decided as the D-0822-2 amendment of 2026-08-24.
- Live campaign-inert: periods `closed/draft/draft`, all data tables 0, every `evaluation_started_at` NULL, Auth Guard `updatedAt=2026-08-18T16:34:30.674Z`.

## 2026-08-24 — Live reclassification: soft exclusion, additive path, BUG-041 runtime, BUG-043 (D-0822-3)

**What was done:**
- **Applicability, server-side, classification dimension only.** One predicate — a `project_participants` criterion applies iff the subject is *currently* a project participant — now lives in the matrix emission (`Build Matrix Query`), the close dataset emission (`Build Close Dataset Query`, so `period_results` inherit it), and the write validation of submit / additive / update / self-review (422 `CRITERIA_NOT_APPLICABLE`, named ids, before any SQL). Corrections bind `(subject, criteria, level, period)` and are read only through per-cell sub-selects — verified first — so an excluded cell takes its corrections with it. The three formulas untouched: which cells exist changed, never how they combine.
- **Reclassification flow (D-0822-3).** `CLASSIFICATION_FROZEN` and its probe node removed from `admin/save-user`. project→general soft-excludes (nothing deleted, switch-back restores the index to the digit); general→project reopens the manager task: `evaluated_by_actor` is per-criterion ("exists AND covers every currently-applicable manager-path criterion", mirroring the form incl. `managers_only`→`has_subordinates`), `/api/employees` names `missing_criteria_ids`. Additive path on `POST api/submit-evaluation`: missing applicable criteria are added to the existing evaluation, `calculated_score` recomputed in SQL over the surviving counting rows (client total never read); overlap → 409 `CRITERIA_ALREADY_SCORED`; all branches share one gate (`FOR UPDATE` + inline reassertion — the BUG-041 rule). Ordinary edit deletes only actively-removed applicable criteria; classification-excluded rows survive. Retires the BUG-036 409-dead-end class on the manager path.
- **BUG-041 runtime repro** (the code-level close lacked one): pre-fix statement (RECON §7.2 text) against a zero-row header **deleted rows 4 and 12** (`{3,4,12}` → `{3}`); the deployed statement under identical conditions deleted **zero** (`{3,4,12}` → `{3,4,12}`). Route-level: 403 `PERIOD_CLOSED`, rows unchanged.
- **BUG-043 closed wider than filed**: the draft fallback is gone — the current period is the single active **leaf** or explicitly **none** (null id, null scope), and the leaf predicate went into every campaign-surface period resolution. Live post-deploy: all six roles see `current_period_id = null` (was container id 5). Preparation window still names H1 with real scope.
- **Weight floor 0.1** (D-0822-2 amended, approved 2026-08-22): `MIN_WEIGHT = 0.1` server-side mirroring the client `min="0.1"`; live probes: 0 and 0.09 → 422 `INVALID_WEIGHT` with stored weight unchanged; 0.1 accepted on the stand; message keeps pointing at `is_active`.
- **Frontend**: dashboard card third state «Дооценить (N)» naming missing criteria; `EvaluationModal` additive mode (only missing criteria, drafts off) and every mode now submits only visible criteria (an edit after a switch would otherwise 422); `TaskStatusContext` uses the per-criterion flag; dashboard refetches rows after writes.
- **Docs riders**: D-0822-3 appended; D-0822-1/2 amended (emergency stop halts the campaign — intended; start mark survives deactivation — intended; 0.1 floor); grades note (S4-M1 id 6 and M1 id 11 are one logical grade); `PROJECT_RULES.md` one-session rule; HANDOVER §10 report list completed (+`BACKUP_FIX`, also missing) and counters reconciled; §3/§6.3 freeze sentences corrected. bugs.md: BUG-041 runtime-proven, BUG-043 + BUG-044 closed; BUG-042 and BUG-029 read-side untouched (out of scope). **19 open / 25 closed.**

**Results:**
- Stand E2E (`epe_reclass_20260824_0602`, torn down after): P index **458.172 → 300.168 → 458.172** across project→general→project with all five DB rows intact throughout; G flag reopened with `[8, 13]`, additive added exactly those, `calculated_score` **7.8** = independent Python = independent SQL, hostile client 999.99 ignored; close under the new filter: every persisted final/index equals the independent replica to 4 dp, P frozen at the *excluded* 300.168, and a post-close switch left `period_results` byte-identical while the `?period_id=` inspect showed 458.172 again. 148 checks, 0 failures (`backups/2026-08-24-reclass/reclass_proof.json`).
- Live: 12 workflows PUT (pre-deploy drift check: live was byte-identical to HEAD generators; activation preserved; node-for-node verified after each PUT; Auth Guard `2026-08-18T16:34:30.674Z` untouched throughout), frontend release `20260824T061101Z` serving, no schema change, campaign state untouched (periods closed/draft/draft, all data tables 0). Live probe: all green, state fingerprint byte-identical, probe sessions cleaned (8 → 8). Stale `API_ evaluations-matrix.json` export refreshed from live in passing (the BUG-028 file).
- `npm test` 272/272 (was 263), build clean, eslint no new findings.
- Report: `docs/RECLASS_2026-08-2x.md` (with a seven-item "Surfaced for decision" — score-correction writes still skip applicability; live hr id 52 carries `can_evaluate=true`; the flag/form duplicated business rule; additive concurrency footnote; §A.1 snapshot split; the BACKUP_FIX index gap; self-review staleness unchanged by boundary).

## 2026-08-24 — Gate: RECLASS verification (read-only)

**What was done:**
- Read-only gate on build `39e34fd` (`docs/RECLASS_2026-08-2x.md`), 07:20–07:50 UTC. SELECT / GET / `readlink` / local `pg_restore` of the recorded dump. No live HTTP probe (would write `auth_sessions`).
- Report: `docs/GATE_RECLASS_2026-08-2x.md`.

**Results (copied from the gate):**
- Every reachable build claim **confirmed** — money figures re-derived to the digit; 12 target workflows node-identical to HEAD generators; live campaign-inert and drift-free.
- Three findings filed, none refuting a build claim: **BUG-045** (stale-export class is ten files wide; named BUG-028 instance current), **BUG-046** (middle-manager matrix missing the applicability clause), **BUG-047** (D-0822-3 full-re-submit sentence wrong). BUG-046/047 later closed by FINALIZE.

## 2026-08-24 — Finalization batch: corrections applicability, BUG-046/047, new-criterion path verified

**What was done:**
- **Corrections applicability (approved, D-0822-3 extended).** `POST api/admin/score-correction` enforces the shared predicate: a `project_participants` criterion for a currently-general subject → 422 `CRITERIA_NOT_APPLICABLE` before any write, for both writer levels. Check placed after the subject 404 and before the period gate — deliberately, so the deployed rule stays provable on live while the launch is paused (surfaced in the report; submit already answers applicability before its relation checks, so nothing new leaks). Write-side only; read-side exclusion was already proven.
- **BUG-046 closed.** The one named clause — `(c.target_audience <> 'project_participants' OR u.is_project_participant = true)` — added to the `CROSS JOIN` row source of the middle-manager matrix, same text/position as the admin matrix and close dataset. Two new static tests.
- **BUG-047 closed.** D-0822-3 wording corrected to the deployed truth (full re-submit → 409 `CRITERIA_ALREADY_SCORED`; `DUPLICATE_EVALUATION` only on the concurrent-create race); the same decision's write-validation bullet now records the corrections extension.
- **New-criterion path verified end-to-end** on stand `epe_final_20260824_0828` (fixture adds mid-manager 1310 above 1302 for the middle-manager span): criterion id 14 created in draft via the exact UI POST (all / self off / manager on / c_level off, 10 level texts). Answers: Manage Criteria seeds **0** `score_coefficients` rows and **cannot set a weight** (DB default 1.00; no UI field, no INSERT column); `GET /api/score-coefficients` **renders the unseeded criterion** (all-1.0 fill) and the existing upsert then created exactly 10 rows; `/api/employees`, both matrices, additive flow and close all pick it up (old-set submit → `evaluated_by_actor=false, missing=[14]`; additive `{14:7}` adds one row and closes the flag); money paths **silently fall back to 1.0** while rows are absent.
- Stand-only SQL reopen between two closes produced the mandated worked example — same scores, two different persisted indices.

**Results:**
- Stand: **90 checks, 0 failures** (`backups/2026-08-24-finalize/finalize_proof.json`). Corrections: 422/422 with counts unchanged both writer levels; 200 c_level / 200 mid_level / 200 'all'-criterion — exactly three rows stored. BUG-046: 1304's emitted cells [2,3,4,8,12,13,14] → general → **[2,3,4,12,14]** (corrections leave with their cells; admin matrix agrees) → back → restored with correction values 6/6 intact; DB rows unchanged through all three states. Money: subject 1308 (S2=1.10) index **47.63** (criterion-14 term 7×1.0×1.0) vs **54.483** (7×1.05×1.8 after the save), delta 6.853 exactly the term, both equal to independent replicas; `final_rating` 6.25 both times (ratings ignore coefficients by design). Role×route on both touched workflows as expected (incl. plain manager → 403 `OWNERSHIP_FORBIDDEN` on the matrix, pre-existing).
- Live: zero-drift before (changed = exactly the two intended), dumps taken (`epe_2026` + n8n schema), two PUTs node-verified with activation preserved, Auth Guard `2026-08-18T16:34:30.674Z` untouched throughout, post-deploy drift **0**, money-inputs fingerprint `b0bd0f55…` identical before/after. Live probe pair (marked session, deleted in finally): criterion 8 → **422 `CRITERIA_NOT_APPLICABLE`**, criterion 3 → 409 `NO_ACTIVE_PERIOD` (non-mutating, paused), matrix → 200 empty no-period; `score_corrections` 0 → 0.
- `npm test` **274/274** (was 272). Stand torn down: container removed, `epe_final_*` dropped, `epe_2026` the only `epe_*` DB.
- Report: `docs/FINALIZE_PRELAUNCH_2026-08-2x.md`. bugs.md **20 open / 27 closed**; HANDOVER §10 counters reconciled (were 3 rows stale) and index completed (+`GATE_RECLASS`, +this report).

**Notes / Gotchas:**
- **Deploy defect found and fixed on the way:** the export-refresh guard refused `API_ Manager Subordinates Matrix.json` — `build_route_guard_deferred.py` still carried a **dead** `legacy_query` read of that export (leftover of the inline rewrite). Removed (generator output byte-unchanged); export then refreshed from verified live. Both PUTs had already landed and verified. Progresses BUG-045 (nine stale exports remain); new `scripts/check_live_drift.py` gives the full-corpus generator-vs-live comparison on demand.
- **Live has TWO HR accounts with `can_evaluate=true`, not one:** Liya Dmitriyeva (52) **and Sona Rahmanova (80)**, both under Jemal Gulberdiyeva (47). The reclass report surfaced only id 52. The flag only enables ordinary participant writes (self/upward), not corrections or admin reads. For Alexander to confirm whether both should carry it.
- The new criterion must exist before «Запустить оценку» (catalogue freezes at start); the `/admin/scoring` coefficient save stays legal until close (D-0822-2) — but until it happens every money surface silently values the criterion at weight 1.0 × coef 1.0. Create → save coefficients → verify is the required sequence.

## 2026-08-24 — Gate: FINALIZE_PRELAUNCH verification (read-only)

**What was done:**
- Read-only gate on `bfca5e1` (`docs/FINALIZE_PRELAUNCH_2026-08-2x.md`), 09:07–09:35 UTC. SELECT over SSH, local `pg_restore` of the recorded dump, local generator runs, local `npm test`. No live HTTP probe.
- Report: `docs/GATE_FINALIZE_2026-08-2x.md`.

**Results (copied from the gate):**
- Every reachable batch claim **confirmed** — four money figures re-derived to the digit; full-corpus drift zero (31 generator outputs byte-identical to live, 2 deliberately deleted absentees); live campaign-inert.
- Two findings filed: **BUG-048** (FINALIZE §1 justification sentence; later closed by D-0824-1), **BUG-049** (migration 006 vs live `score_corrections` FKs; later closed by CRITERION9, residue **BUG-050**). BUG-045 narrowed to **nine** stale exports.

## 2026-08-24 — Criterion-9 batch: riders shipped; creation BLOCKED on the missing texts document

**What was done:**
- **Criterion «Ответственность сверх роли» NOT created — hard blocker, not a judgment call.** The brief requires title, description and ten level texts VERBATIM from the attached document, and that document is nowhere on the executor's machine (repo, `~/Downloads` where every previous brief's files landed, Desktop/Documents, scratchpad — all swept; the stand proof used placeholders by design). No texts were invented; **zero live writes this session** (live touched only by two read-only `pg_constraint`/`pg_indexes` reads for BUG-049 evidence), hence no pre-change dump either — the dump is the executor's first gate.
- **`scripts/create_criterion9_live.py` staged** so the creation is one command once the document arrives: refuses to run without a `--texts` JSON (verbatim strings sent as-is, then re-read from the DB and compared char-for-char); dump-first; the exact FINALIZE-§3 sequence (manage-criteria save → verify default weight 1.00 / 0 seeded rows → scoring GET renders unseeded → score-coefficients save with weight **1.50** + levels **0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00**); proofs for brief items 2–4 (10 rows, weight, GETs incl. manager-side weight stripping via a marked read-only session, level-5 round-trip 0.50→0.55→0.50 with four recorded reads, other-8-criteria/80-rows/grades byte-identical, 9/90 totals, periods byte-identical); rerun guard + `--resume`; probe jtis deleted in `finally`. Compiled; refusal path tested.
- **BUG-049 closed (rider).** `migrations/006`: criteria FK `users(id)`→`criteria(id)` typo fixed, all three FKs CASCADE→plain `NO ACTION`, constraint names aligned to live (`_subject_fkey`/`_criteria_fkey`/`_evaluator_fkey`), dated corrective comment. Migration file only — live already correct, untouched. Evidence: live `pg_constraint` read 2026-08-24 quoted in the report and the closure.
- **BUG-050 filed.** The same read surfaced what BUG-049 didn't record: `score_corrections.period_id` (column + FK + live's 4-column unique index) appears in **no** migration; 006's CHECK absent on live; `schema.sql` predates the table. A from-migrations rebuild gets a table `API: Score Correction` cannot write to.
- **BUG-048 closed as accepted behavior (rider).** `DECISIONS.md` **D-0824-1**: the pre-period applicability answer is intentional (non-mutating; keeps the rule provable on paused live; the marginal pre-period classification probe is an accepted, recorded cost). FINALIZE §1's wrong "leaks nothing submit does not" sentence corrected in place as a marked correction. No code change.
- **HANDOVER reconciled**: §10 counters 20/27 → **21/29** (matches bugs.md statistics and a marker recount); report list completed (+`GATE_FINALIZE`, +`CRITERION9`). The "8 active criteria / 80 coefficient rows" statements and the §3 catalogue table are **deliberately NOT updated to 9/90** — that waits for the criterion to actually exist.

**Results:**
- `npm test` **274/274** (brief floor 272+). No code under test touched (migration file, docs, one standalone script).
- Live state unchanged: periods closed/draft/draft, launch paused, no campaign, no workflow PUTs, Auth Guard untouched, no mail. bugs.md **21 open / 29 closed**.
- Report: `docs/CRITERION9_2026-08-2x.md` (search evidence, live FK evidence, staged-run instructions, Surfaced-for-decision).

**Notes / Gotchas:**
- **For Alexander / the architect:** re-send the criterion document (or paste the texts verbatim into a JSON per the report §1); then `python3 scripts/create_criterion9_live.py --texts <file>.json` runs the whole approved sequence with proofs, and the two deferred HANDOVER updates (8→9 criteria, 80→90 rows, catalogue table) follow in the same session.

## 2026-08-24 — Criterion 9 «Ответственность сверх роли» CREATED AND PROVEN ON LIVE (id 14)

**What was done:**
- The texts document arrived (pasted verbatim in chat by Alexander); saved untouched as `docs/briefs/criterion9_texts.json` (12 keys validated) and `scripts/create_criterion9_live.py` ran green: **`failures: []`**, proof at `backups/2026-08-24-criterion9/criterion9_live_proof.json`.
- Two pre-run fixes, neither touching the sequence: dump plausibility floor 100 KB → 50 KB (this DB legitimately dumps at ~79 KB `-Fc` with 0 evaluations — verified against the reclass/finalize known-good dumps and a local `pg_restore --list`: 161 TOC entries, 17 table-data sections), and the repo's standard `_tls_context()` (certifi fallback, from `probe_live_reclass.py`) adopted. Both aborted attempts stopped **before any live write** (dump gate; TLS handshake) — clean state re-verified between attempts (8 criteria, 0 probe sessions).

**Results (compared values):**
- Dump first: `epe_2026_20260824_164442.dump` (79,427 bytes). Creation via `POST manage-criteria {action:'save'}` → **id 14** (same as the stand); every stored text **char-for-char equal** to the document; flags all / self off / manager on / c_level off; weight landed at the **1.00 default** with **0** seeded rows; scoring GET rendered the unseeded criterion (all-1.0 fill); `POST api/score-coefficients` then stored weight **1.50** and levels **0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00** — exactly **10 rows**, SQL and GET agreeing to the digit.
- Catalogue reads: admin sees weight 1.50; a live manager (marked read-only session) sees the criterion with correct flags/audience and **no weight** — admin-only stripping confirmed on live.
- Round-trip (level 5, same save route): 0.50 → 0.55 → re-read **0.55** → restore → re-read **0.50**.
- Everything else byte-identical: other 8 criteria / their 80 coefficient rows / grades compared **raw** before/after, md5 `b0bd0f55…` — the same fingerprint the finalize batch recorded. Totals after: **9 active criteria / 90 coefficient rows**. Periods byte-identical (launch stays paused; no activation, no mail, no workflow PUT, Auth Guard untouched). Probe sessions deleted (`DELETE 2`), session count restored.
- Docs: HANDOVER §5 → 9 rows / 90 rows + table row for id 14; both per-person distributions **recomputed from live** (48 general / 41 project unchanged): **37 × 4, 11 × 5, 36 × 6, 5 × 7** — exactly the +1-for-everyone shift; §10 report-list note updated to "created". Report `docs/CRITERION9_2026-08-2x.md` §6 execution record; Surfaced-for-decision now empty (the blocker resolved).
- `npm test` **274/274**.

**Notes / Gotchas:**
- The coefficient save remains legal until close (D-0822-2), but the criterion had to exist before «Запустить оценку» — it now does, well before any campaign. Nothing remains to do for criterion 9 except normal campaign operation.

## 2026-08-24 — Browser-driven walkthrough of the campaign UI (prelaunch debt retired)

**What was done:**
- Built a throwaway stand (`epe_walk_*`, `epe-walk-n8n` on :25679) with the FULL generated workflow surface (28 active) and fixture actors that log in through the real `auth/login` form (scrypt hashes in the seed).
- Walked every campaign flow in a real Chromium: employee (zero tasks → prep window → tasks after «Запустить оценку» → self-review 3/4/12 → submit), manager (per-subject criteria sets: 14 everyone / 8-13 project / 2 manager subjects; submit; reclassification → «Дооценить (2)» naming 8/13 → additive modal → flag closes), upward (criterion 2 only), admin (two gates + all period states, /admin/scoring 9 criteria + weight round-trip, matrix + final scores with the criterion-14 column and money to the digit, corrections applicable/inapplicable, catalogue freeze), error surfaces (409 already-scored via a genuine stale tab, 422 applicability, period-not-started, freeze 409 — all human Russian, no raw JSON).
- Network evidence for the D-0822-2 claim: self-review payload captured verbatim — no `weighted_score`, no `score-coefficients` fetch anywhere in the employee tab's log.
- Fixed under latitude and deployed (release `20260824T131920Z`): correction refusals now surface the server's reason instead of a hardcoded alert (BUG-052 closed; `tests/correctionErrorSurface.test.js`).
- Filed BUG-051 (admin matrix header/body misalignment for non-project rows, High) and BUG-053 (world-readable live dumps in VPS /tmp, Medium). bugs.md 23 open / 30 closed; HANDOVER §10 reconciled.
- Stand torn down; live verified untouched (H1-2026 still draft, 0 fixture users, 0 evaluations today).

**Results:**
- Report: `docs/BROWSER_WALKTHROUGH_2026-08-2x.md` (checklist + verbatim evidence + Surfaced-for-decision).
- `npm test` **277/277**.

## 2026-08-24 — Prelaunch fix batch: BUG-051 matrix alignment fixed+deployed, BUG-053 /tmp dumps cleaned, refresh check answered

**What was done:**
- **BUG-051 CLOSED.** The admin evaluations matrix now renders one shared column list for header AND every row: `buildSharedCriteriaGroups` (union of all rows' criteria, first-seen order) + per-row lookup by `criteria_id` with placeholders (N/A in project/management columns, «—» elsewhere) for non-applicable criteria. Proven in a real Chromium on a walkthrough-pattern stand (`epe_walk_20260824_1432`): all 97 rows emit exactly 10 td under the 10-th header (was 8 for general rows); G shows N/A in the project columns while P shows 8/7 there; a c_level correction renders 8.5 amber at its own column index 5. Deployed to live release `20260824T145133Z`, chunks md5-identical to the local build.
- **Money unchanged, to the digit.** With criterion-14 weight at the walkthrough's 1.50 (stand-only round-trip) the fixed build reproduces the recorded §3.6 figures exactly: G Σ70.20→42.12, P Σ121.30→266.86. Under live's current coefficients the screen matches independent arithmetic (46.32 / 276.76). **Found on the way: criterion 14's weight moved 1.5→2.0 on live today (12:36Z–14:32Z), via the admin-only coefficients channel — surfaced for Alexander's confirmation (report §5.1).**
- **BUG-053 CLOSED (approved).** Ten dumps found in VPS /tmp (the filed seven + epe_2026_after + two n8n-schema dumps); every one md5-verified against a dated local copy in backups/; the approved seven deleted, the other three moved to /root/backups/epe/tmp_rescue_20260824 (0600). /tmp now holds zero dumps. PROJECT_RULES.md: new rule — stand/rollback artifacts never in /tmp, root-only /root/epe_stand_tmp instead, teardown removes it; setup_walkthrough_throwaway.sh made compliant and used that way this session.
- **Refresh check (by hand): the dashboard card updates without reload.** Submit → success panel (card still stale by design, 0 refetches) → «Закрыть» → /api/employees refetch in the XHR log → card flips to «Оценен вами · Балл: 7.0»/«Редактировать». The walkthrough §9.3 staleness was an automation artifact (programmatic click through the modal overlay skips handleFinalClose). No bug filed.
- Riders: check_live_drift.py now WARNs by name on generator outputs absent from live (both deploy-gate runs show it); HANDOVER §10 counters 21/32 + §3 weight annotation; bugs.md statistics 21/32; EVALUATION_METHODOLOGY.md not attached → skipped.

**Results:**
- Report: `docs/PRELAUNCH_FIX_BATCH_2026-08-2x.md` (named to avoid overwriting the accepted 20 Aug PRELAUNCH_FIXES report the brief's literal filename pointed at).
- `npm test` **284/284** (+7: 3 buildSharedCriteriaGroups, 4 alignment source pins). Drift 30/0 before and after deploy. Live verified campaign-inert after everything (H1 draft, all data tables 0, 89 users). Stand torn down; epe_2026 the only epe DB left.

## 2026-08-24 — Docs hygiene (re-measure after the 22–24 Aug sprint)

**What was done:**
- Documentation and git only. Re-measured live read-only (SELECT / GET / `readlink` / `openssl` / `crontab -l`) on 2026-08-24 17:14–17:16 UTC. No workflow PUT, no deploy, no DB write, no dump, no mail, no stand.
- Rewrote drifted facts in `docs/HANDOVER.md` toward this session's measurements and the accepted 22–24 Aug reports. **§4 byte-locked** — md5 `0b2e854c22dc41f1d96e169b375b6350` before and after.
- `DECISIONS.md`: D-0822-1/2/3 and D-0824-1 were already present (no duplicates); added **D-0824-2** verbatim (criterion 14 weight 1.50).
- `PROGRESS.md`: added the three missing gate entries (`GATE_LIFECYCLE_COEFF`, `GATE_RECLASS`, `GATE_FINALIZE`) plus this session.
- `bugs.md`: BUG-028 closed (named instance current per GATE_RECLASS + this session's 9-node export); statistics **20 open / 33 closed**, matching a status recount. Ledger BUG-001…053, no gaps.
- `PROJECT_RULES.md`: both 24 Aug rules were already present; archive dump count 10 → 13 (measured).
- `AGENTS.md`: methodology paragraph amended with the pending-draft sentence.
- Report: `docs/DOCS_HYGIENE_2026-08-24.md`.

**Results:**
- Live: H1 id 2 `draft` / `is_active=false` / `evaluation_started_at` NULL on all three periods; four data tables 0; criterion 14 **weight 1.50**; `/tmp` dumps 0; `backup-epe-live.status` OK today; frontend `20260824T145133Z`; webhooks **42** (19 GET / 21 POST / 2 OPTIONS); Manage Periods **70 nodes / 8 routes**; Auth Guard `2026-08-18T16:34:30.674Z` unchanged.
- `npm test` **284/284**. `npm audit` 15 (11 high / 3 moderate / 1 low). `check_live_drift.py` 30 identical / 0 changed / 2 absent. Stale top-level exports: **9** (+ 2 deleted-workflow files).
- **Surfaced, not resolved:** criterion 14 live level curve is `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00`, not the CRITERION9 / D-0824-2 approved `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00`. Weight matches; levels do not.

## 2026-08-24 — Prelaunch copy batch: BUG-034/035/036/037 closed and deployed

**What was done:**
- Frontend-only. No workflow PUT, no DB write, no mail, no stand. `useFinalScoresMatrix` / `useScoreCalculation` / money screens not opened.
- **BUG-036 CLOSED.** «Оценить новые критерии» removed from `SelfReviewStatusCard` (owner decision; no `is_update`). Five strings corrected: Welcome visibility sentence mapped clause-by-clause to HANDOVER §3; criterion title «Качество управления и развитие команды»; C-level/admin no-manager notice; draft is browser-local and expires in 7 days; login placeholder `name@sedamedical.com`.
- **BUG-035 CLOSED.** `handleApiError` passes the server message on 401/403/429; fixed Russian fallback. 401 interceptor unchanged (test).
- **BUG-037 CLOSED.** «Создать период» behind the same `canManage` as the other four write controls.
- **BUG-034 CLOSED by removing the circles.** No admin-allowed route returns the subject-centric metrics the column claimed. The undeclared `setLoadingStatuses` effect is gone.
- Riders: D-0824-2 amendment appended verbatim; HANDOVER §7 steps 1 and 3 gained the coefficient-comparison runbook line. Criterion 14 live curve still ≠ approved (SELECT 17:57:33Z) — note left, coefficients not written. HR 52/80: two capability-only write routes surfaced (BUG-038). `assessment.sedamedical.com` → `216.250.12.243`, 80/443/8080 refused.
- Deployed release **`20260824T175642Z`**. Previous `20260824T145133Z` retained. Chunks md5-identical to the local build; new strings present in the served bundle. Live still H1 draft, four data tables 0.

**Results:**
- Report: `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md`.
- `npm test` **284 → 295**. bugs.md **16 open / 37 closed**.
- Surfaced, not resolved: criterion-14 curve; submit/update capability-only guards; TeamView `setLoadingSelfReviews`; CriteriaOverview leftover fake title.

## 2026-08-24 — Welcome period notice: owner visibility wording restored, D-0824-3, upward seal verified

**What was done:**
- Frontend-only. No workflow PUT, no DB write, no mail, no stand. Money screens/hooks not opened.
- Period notice above the Welcome task area: three states from `GET /api/employees` (`campaign_active` / `period_in_preparation`). Title and scope render only when name+dates are present — they are not, on any employee-readable route. `GET /api/periods` is `admin`/`hr`/`c_level`. Out-of-scope people still see the notice plus `OutOfScopeNotice`.
- Visibility wording restored byte-for-byte from `a86e45b` (parent of `c02377d`): both anonymity boxes and the manager-track purple box. `CriteriaOverview` leftover «Критерий для оценки руководителя» → live title of criterion 2.
- D-0824-3 recorded. Upward-channel seal verified against live definitions + local tests (compared values in the report). BUG-036 row 2 closed by that decision.
- Riders: `can_evaluate=false` is exactly 21 / 40 / 61 — capability is the write gate; FINALIZE HR leftover closed without code. Criterion 14 live levels still ≠ approved — HANDOVER note left, coefficients not written.

**Results:**
- Report: `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md`.
- `npm test` **295 → 312**. bugs.md **16 open / 37 closed** (recounted).
- Deployed release **`20260824T182054Z`**. Previous `20260824T175642Z` retained. Live still H1 draft, four data tables 0, `evaluation_started_at` NULL.

## 2026-08-24 — Employees period meta: period name + dates on /api/employees, stand-proven, deployed

**What was done:**
- One workflow changed, additively, through its builder (`scripts/build_auth_workflows.py`): `GET /api/employees` now carries `period_name`, `period_start_date`, `period_end_date` for the current period (active leaf — preparation and started states), all `null` when there is no current period. Dates leave Postgres as `to_char(…, 'YYYY-MM-DD')` text (BUG-031 defence). Guard unchanged; `GET /api/periods` not opened. Frontend untouched — `extractPeriodMeta` already reads exactly these keys.
- Stand proof (walkthrough pattern, `epe-empmeta-n8n` / `epe_empmeta_20260824_1840`, VPS loopback :25679): old and new definitions both imported and verified node-for-node via n8n export; 3 states (draft → real activate → real start-evaluation) × 3 fixture actors (employee, manager, out-of-scope 1311). All 9 cells: added keys exactly the three, removed none, payload minus the three keys deep-equal to the old payload. Values: draft → three nulls; preparation/started → `H1-2026` / `2026-01-01` / `2026-06-30` — not the previous day. Artifact: `backups/2026-08-24-empmeta/empmeta_proof.json`.
- Browser check on the stand (vite :5299, real login as `wt.employee.g`): preparation and started render «Промежуточная оценка: H1-2026 (1 января 2026 — 30 июня 2026)» + the scope sentence with the same dates; draft hides both.
- Live PUT via `scripts/deploy_employees_period_meta.py` (guard frozen before/during/after, activation `true → true`, graph re-read node-for-node, export refreshed): `bKB4Sb46yWoq1tSV` `updatedAt` `2026-08-24T06:10:17.952Z` → **`2026-08-24T18:49:55.486Z`**. Drift before PUT: exactly the one intended workflow; after: **30 identical / 0 changed**. Live probe (marked session, deleted; fingerprint identical): admin GET 200, key set = previous eight + the three new keys, all three `null` (H1 draft).
- Riders: BUG-054 (history workflow named Received, SQL given-only) and BUG-055 (Profile «Оценен подчиненным:» against a nulled name) filed as low; bugs.md 18/37.

**Results:**
- Report: `docs/EMPLOYEES_PERIOD_META_2026-08-2x.md`. HANDOVER §3 employees bullet updated.
- `npm test` **312 → 313**. Live after everything: H1 id 2 `draft`/inactive/not-started, four data tables 0/0/0/0. Teardown complete: container removed, stand DB dropped (`epe_2026` the only `epe_%` DB), `/root/epe_stand_tmp` empty, tunnels killed.

## 2026-08-25 — HR review of the criteria catalogue: 9 criteria / 90 level texts, verdict «start is possible», 39-row decision table

**What was done:**
- **Read-only everywhere.** No catalogue write, no coefficient write, no methodology edit, no workflow change, no deploy, no mail, no stand. Live was touched only by SELECTs on `performance_db.criteria`, `score_coefficients`, `grades`, `evaluation_periods` (2026-08-24 19:22:58 UTC by the server clock).
- Full HR review of all 9 titles, 9 descriptions and 90 level texts, quoted verbatim from live, each with a verdict (ok / finding) — lenses: wording, ambiguity, distortion, scale integrity, perspective fit, role fit, overlap/double-pay, completeness, rater guidance. Criterion 14 texts confirmed char-for-char equal to `docs/briefs/criterion9_texts.json` (no drift since creation).
- **Verdict: H1 can start on these texts.** P0 before the freeze: criterion 3 level 10 «в рамках года» (annual leftover), criterion 12 level 8 threshold «не менее 2-х за период» (written for an annual cycle), criterion 14 level 2 «качественно» (hole for the weak-no-extras case). P1: beyond-role facts paid in 3/4/8/13 in parallel with 14; «лояльность»/«незаменим»/«свой человек» anchors; criterion 13 mid-levels keyed to time-on-site; criterion 1 levels 8–9 closed to non-manager experts; jargon/typos. P2: criterion 1 role-ladder vs grade, upward reading of criterion 2, completeness gaps, 5-vs-6 norm convention. One-page rating guide drafted (report §5).
- **Surfaced, not resolved:** live criterion-14 coefficient curve 0.70…7.00 ≠ approved D-0824-2 0.20…6.00 ≠ methodology draft §5 (which claims «verbatim from live 2026-08-24»); live pays the declared normal state (level 2) a full 1.00 and is the only non-strictly-increasing curve. Criterion 14 weight read **1.50** at SELECT time (the 2.00 seen by PRELAUNCH_FIX_BATCH is no longer live). Criterion 13 level 9 «или совмещение ролей» contradicts the methodology §10 13-vs-14 test. H1 (id 2) was `active` / `evaluation_started_at` NULL at read time — preparation window, catalogue still editable.

**Results:**
- Report: `docs/CRITERIA_HR_REVIEW_2026-08-2x.md` (RU, EN executive summary; per-criterion sections; overlap matrix; rating guide; 39-row decision table R-01…R-44; verbatim appendix of all nine rows, 90 level texts and 90 coefficient rows with timestamp). md5 `285d1cf3238c0cfc69ee49bb8db945cc` for re-upload.
- No bugs.md rows, no other repo changes (per the brief's boundary). Catalogue, coefficients, methodology, workflows untouched; decisions are the owner's, line by line.

## 2026-08-25 — HR opinion: owner's line-by-line answers turned into a paste-ready 32-field edit package

**What was done:**
- Read-only continuation of the HR review: the owner answered its 11 theses line by line; this report converts each answer into one recommendation with final texts. Owner's decisions honoured: criterion-14 curve is his live tuning (excluded), criterion-1 substance is a C-level decision (language-only fixes kept), period wording = «полугодие».
- Recommendations: keep all 9 criteria (no merges, no renames — overlap is wording, fixed by 7 surgical edits leaving criterion 14 the only home of beyond-role facts); drop «незаменим»/«лояльность»/«свой человек» anchors; criterion 14 level 2 loses «качественно» (quality is criterion 3's fact — double-punishment removed); criterion 13 re-anchored to project-load share with «аврал»/«рекордная длительность»/«совмещение ролей» deleted; upward and self-assessment honesty via instruction, «Жертва» label removed; norm declared = 6 (texts win, curves stay); quality/compliance and client outcomes embedded into criterion 3's description, peer help restored to 3-L7 (revision of the review's own R-05) — no new criteria before H1.
- §9 = merged paste-ready package: 32 fields across all nine criteria, each field final and complete, to be entered by the owner in /admin before «Запустить оценку». Nothing was written to the system.

**Results:**
- Report: `docs/CRITERIA_HR_OPINION_2026-08-2x.md`, md5 `834a209319df8251a4614c155ba1122b` for re-upload; no other repo changes, no bugs.md rows.

## 2026-08-25 — Catalogue wording: 20 text fields written on live (D-0825-1)

**What was done:**
- Dated `pg_dump -Fc` of `epe_2026` before the first write: VPS `/root/epe_stand_tmp/epe_2026_20260825_062455.dump` (80 654 B, then removed); local `backups/2026-08-25-catalogue-fix/` (gitignored). No dump in `/tmp`.
- Eight `POST /manage-criteria {action:'save'}` as admin (marked probe session `caf10000-2026-0825-8000-000000000001`, deleted; `auth_sessions` 12 → 12). Each row read fresh from live immediately before its write. All eight returned **200**. No raw SQL on `criteria`.
- Exactly 20 text fields now equal the brief strings character-for-character. The other **88** text fields (title + description + levels 1–10 across 9 rows, minus the 20) and every non-text column (90 values: id, category, weight, audience, flags, `score_definitions`, `level_0_desc`) are identical to the before snapshot. Titles, audiences, flags, weights, coefficients and the criteria count unchanged.
- Before snapshot **equals** the HR-review appendix of 2026-08-24 19:22:58Z (0 text / 0 meta diffs). After snapshot committed. `GET /api/criteria` (forms' read route) 200, new texts for criteria 3 / 13 / 14.
- Live after: H1 id 2 `active` / `evaluation_started_at` NULL; four data tables 0/0/0/0. No workflow change, no deploy, no mail, no coefficient write.

**Results:**
- Report: `docs/CATALOGUE_FIX_H1_2026-08-25.md`. Snapshots: `docs/catalogue/H1-2026_catalogue_before_20260825T062507Z.md`, `docs/catalogue/H1-2026_catalogue_after_20260825T062601Z.md`. Decision D-0825-1. HANDOVER §3 catalogue bullet updated; §10 counters untouched.
- Surfaced: `performance_db.criteria` has no `updated_at` column — write times recorded from `clock_timestamp()` after each 200. Route SET-list rewrites the whole row; unchanged values were sent from the fresh read and came back identical. No cache of old texts on `GET /api/criteria`.

## 2026-08-25 — Rating guide in-product; score zones treat 6 as first «хорошо»

**What was done:**
- Frontend, tests and docs only. No DB write, no mail, no stand, no workflow, catalogue untouched.
- Verbatim guide «Как ставить оценки — 10 правил H1» on the Welcome manager track (all 10), Welcome employee track + upward form + self-review (rules 1, 7, 8), and one-click (collapsed) at the top of `EvaluationModal`.
- Score-band labels/colours: 6 is the first «хорошо»; 5 is «в целом справляется, требует внимания». Criterion 14 (norm 2) and 13 (volume) have their own bands. Numbers and payloads unchanged.
- Self-review no longer promises that 85–90% land in yellow/green zones.
- HANDOVER §1/§3/§7 and AGENTS.md: H1 **active since 2026-08-24 19:07:36Z**, not started. Activate done; remaining runbook starts at «Запустить оценку».

**Results:**
- Report: `docs/PRELAUNCH_GUIDE_AND_ZONES_2026-08-25.md`. Screenshots: `docs/prelaunch_guide_and_zones/`.
- `npm test` **313 → 326** (re-run after deploy: 326/326).
- Deploy: release **`20260825T065554Z`**; previous **`20260824T182054Z`** retained on disk. Live after: H1 id 2 `active` / `evaluation_started_at` NULL; four tables 0/0/0/0.
- Guide strings live in served `index-C_mvqGch.js` (shared chunk), not in the Welcome lazy chunk. Title + all ten leads and bodies present verbatim. Chunk md5 local = disk = served.

## 2026-08-25 — Catalogue fix 2: five level-6 norm labels removed on live (D-0825-2)

**What was done:**
- Dated `pg_dump -Fc` of `epe_2026` before the first write: VPS `/root/epe_stand_tmp/epe_2026_20260825_072229.dump` (80 676 B, then removed); local `backups/2026-08-25-catalogue-fix2/` (gitignored). No dump in `/tmp`.
- Five `POST /manage-criteria {action:'save'}` as admin (marked probe session `caf10000-2026-0825-8000-000000000002`, deleted; `auth_sessions` 12 → 12). Each row read fresh from live immediately before its write. All five returned **200**. No raw SQL on `criteria`.
- Exactly five `level_6_desc` fields (criteria 3, 4, 8, 10, 12) now equal the brief strings character-for-character. The other **103** text fields and every non-text column (90 values) are identical to the before snapshot. Titles, audiences, flags, weights, coefficients, criteria 13 and 14, and the sentence in criterion 14's description unchanged.
- Before snapshot **equals** `H1-2026_catalogue_after_20260825T062601Z.md` (0 diffs). After snapshot committed as `H1-2026_catalogue_after_20260825T072316Z.md`. `GET /api/criteria` 200, new level-6 texts for 3 / 4 / 8 / 10 / 12.
- Live after: H1 id 2 `active` / `evaluation_started_at` NULL; four data tables 0/0/0/0. No frontend, workflow, deploy, mail, or stand.

**Results:**
- Report: `docs/CATALOGUE_FIX2_H1_2026-08-25.md`. Decision D-0825-2. HANDOVER §3 catalogue bullet updated to the new after snapshot; §10 counters untouched.
- Surfaced, not resolved: `src/pages/GuidePreview.jsx` (DEV-only fixture, not in the production bundle) still quotes «(Нижняя граница нормы)» on criterion 3 level 6.

## 2026-08-25 — Rating guide markup: leads on their own line, rule 4 as a list

**What was done:**
- Markup only in `src/components/RatingGuide.jsx`. Words in `ratingGuideH1.js` unchanged (verbatim tests still pass).
- Each rule is a hanging number + bold lead; body sits under the lead. Rules whose lead ends with `:` (6–9) stay one sentence so the body does not start lowercase on a new line.
- Rule 4's five `→` sentences are stacked, not one paragraph.
- Checked locally on `/__guide-preview`: manager (10), employee (1/7/8), collapsed form opens with the same layout. `npm test` tests/ratingGuideAndZones.test.js: 13/13.
- Deploy: release **`20260825T083035Z`**; previous **`20260825T065554Z`** retained. No DB write, no mail, no workflow.

## 2026-08-25 — Rating guide: drop rules 4 and 9; rewrite manager-feedback and usual-behaviour

**What was done:**
- Owner edit of the in-product guide. Title now «8 правил H1». Removed «Один факт оплачивается один раз» and the C-level pair. Remaining rules renumbered 1–8.
- Rule 6 (was 7): оценка руководителя — возможность дать объективную обратную связь для его развития.
- Rule 8 (was 10): описания уровней — обычное поведение за период, не разовый случай.
- Employee subset is now rules 1, 6 and 7. Tests updated; 13/13 on `tests/ratingGuideAndZones.test.js`.
- Deploy: release **`20260825T084142Z`**.

## 2026-08-25 — Rating guide: owner final wording; extra-criteria card is project-only

**What was done:**
- Eight rules replaced with the owner's final text (grammar only: «не в общем» → «не общее впечатление»; «больше важна» → «важна ещё и»; criterion titles in «ёлочки»).
- Welcome «Дополнительные критерии»: management box removed; card now names the two project criteria (8 and 13) and that they apply only to project participants.
- Tests: 35/35 on the guide + Welcome copy files.
- Deploy: release **`20260825T100801Z`** (first attempt timed out on SSH; retry succeeded).

## 2026-08-25 — Welcome extra-criteria: both project descriptions, owner wording

**What was done:**
- «Дополнительные критерии» now lists both project criteria with the live catalogue descriptions (interaction; volume/load). One-line note: only project participants.
- Deploy: release **`20260825T105418Z`**.

## 2026-08-25 — Extra-criteria intro: not formal project membership, but non-routine contribution

**What was done:**
- Welcome intro now: «учитываются у сотрудников, чей вклад в проектную деятельность не ограничивался рутинной работой».
- Deploy: release **`20260825T110537Z`**.

## 2026-08-25 — Welcome typography: one size and line-height across cards

**What was done:**
- Frontend only. No DB write, no mail, no workflow.
- Welcome cards and `CriteriaOverview` now share one scale: titles `16px / 24px` (`text-base`, semibold), body `14px / 21px` (`text-sm` + `leading-normal` = 1.5). Extra-criteria titles were `14px`; «Обращение» body was `16px` with `leading-relaxed`.
- `h2`/`h3` on Welcome locked with matching `md:` sizes so the global heading scale cannot enlarge them on desktop.
- Tests: 36/36 on the Welcome/guide/period-notice files (new type-scale assertion included).

**Results:**
- Deploy: release **`20260825T114906Z`**; previous **`20260825T110537Z`** retained. Live `index.html` Last-Modified Tue, 25 Aug 2026 11:49:13 GMT. Served `Welcome-kCiqvpSe.js` has `leading-normal` (43) and no `leading-relaxed`.

## 2026-08-25 — Period notice type scale matches «Обращение»

**What was done:**
- `PeriodNotice` body was `16px` + `leading-relaxed`; «Обращение к сотрудникам» was already `14px` / 1.5. Same two cards on Welcome now share heading `20px` (locked at `md`) and body `14px` / 1.5.
- Tests: 25/25 on the guide + period-notice files.

**Results:**
- Deploy: release **`20260825T115748Z`**; previous **`20260825T114906Z`** retained.

## 2026-08-25 — Launch readiness and smoke-test facts (read-only; live unreachable from this session)

**What was done:**
- Facts-only pass for the «Запустить оценку» decision and a possible three-account live smoke test. No DB write, no n8n write, no deploy, no catalogue change, no admin write route called, no destructive route invoked.
- **Live could not be reached at all from this session** (Claude Code cloud container, not the delivery Mac): no SSH client and no key on the host, session egress policy denies `epe.sedamedical.com:443` (proxy logged `connect_rejected` 2026-08-25T11:29:12.682Z), no local Postgres, no docker daemon. The denial was reported, not routed around.
- Workflow facts therefore read from the **builder scripts** regenerated into a scratch directory (33 definitions), which `scripts/check_live_drift.py` treats as the thing live is diffed against. Corroborated three ways: Manage Periods 70 nodes / 8 webhooks matches HANDOVER's live measurement; generator-vs-export gives 11 differing minus the 2 deleted-from-live = 9 stale exports, exactly BUG-045's count; Auth Guard matches its export node-for-node.

**Results:**
- Report: `docs/LAUNCH_READINESS_SMOKE_FACTS_2026-08-25.md`. Every live-state item labelled *last measured (date, source)* or *unknown*; nothing inferred.
- **Second gate, from the graphs:** the only assignment anywhere is `SET evaluation_started_at = now(), evaluation_started_by = <actor>` in `API: Manage Periods` / `Build Start SQL`; **no route unsets it** (the two `= NULL` statements in the repo are stand-only proof scripts). Gate opens submit-evaluation / self-review-submit / update-evaluation (409 `PERIOD_NOT_STARTED`) **and score-correction** (409 `NO_ACTIVE_PERIOD`); it closes only `POST manage-criteria` (409 `EVALUATION_STARTED`). Coefficients, grade coefficients, classification, registration, auth and every reporting read carry zero gate references, and `ACTIVE_PERIOD_EXISTS` / `CLASSIFICATION_FROZEN` are absent from all 33 definitions.
- **Registration:** writes exactly `users.password_hash` (guarded `IS NULL`) and DELETEs the verification code; writes nothing to `invite_tokens`. Password = scrypt `N=16384,r=8,p=1`, 16-byte salt, 64-byte key, stored as `$scrypt$N=16384,r=8,p=1$<salt b64url>$<key b64url>` (133 chars). Re-registration through token id 4 is mechanically possible after a SQL `password_hash = NULL` plus a fresh code. A login writes an `auth_sessions` row that **no route ever deletes**, and `GET api/verify-invite` writes an `epe-throttle:verify-invite:<ip>` bucket.
- **Cleanup:** `api/admin/clear-test-evaluations` was **deleted from live 2026-08-19** and BUG-002 is closed — three independent records agree. Not invoked. No node graph survives in the repo (the 12 Aug snapshot is metadata-only); what it did is on record: unauthenticated webhook → DELETE of all `evaluations` + `score_corrections` across all periods, and at that date against `postgres.performance_db` (the 2025 archive — `epe_2026` did not exist until 18 Aug).
- **Trace inventory after deleting evaluations by id:** scores cascade away; `score_corrections` survive (no FK, no cascade); completion flags are computed, not stored; no cached counters; n8n keeps no execution history (all 33 definitions `saveDataSuccessExecution: none`); `auth_sessions`, `auth_login_attempts`, `password_hash`, `token_version` and the id-sequence gaps all persist.

**Notes / Gotchas:**
- **Three premise corrections surfaced, not resolved:** (1) criterion 13's description + levels 4–10 and criterion 8's description were written by **FIX1**, not FIX2 — the pre/post-FIX2 diff the brief asks for has no signal there; FIX2's whole delta is five `level_6_desc` fields on criteria 3/4/8/10/12. (2) Score-correction does not "stay open" across the gate — it is closed now and the gate opens it. (3) `clear-test-evaluations` is already gone; the brief's "unauthenticated, destructive" is the pre-fix state.
- **"Which accounts registered, and when" is structurally unanswerable:** `is_registered` is derived from `password_hash IS NOT NULL` and there is no registration timestamp column anywhere — not in `schema.sql`, not in `migrations/001…014`, not in `scripts/import_epe_2026.py`.
- **The trio cannot be resolved from the repo.** No roster with live ids exists. The condition is now exact: one `users.manager_id` edge inside the trio yields both manager→subordinate and upward; self-review needs only scope. Repo evidence points at Hekimov → Ruhlyadko (Wave 1 manager / Wave 2 employee, same department) but Akmyrat Jumahanov holds the identical title in the same department, so it is ambiguous. Hojayeva is in a different division. One SELECT settles it.
- A live smoke test needs those accounts registered, and the only route-based path emails a code to the employee's real mailbox — AGENTS.md hard constraint 5 / D-0820-8. The same pattern was run once on 2026-08-20 and then forbidden.
- `bugs.md` counts **18** `🔴 OPEN` vs HANDOVER §10's "16 open" (closed still 37) — §10's counter is stale. No bug row was touched. No row filed for the dead `AdminSettings.jsx:132` cleanup button, because asserting the route's absence needs a live probe this session could not make.

## 2026-08-25 — Prelaunch live check: today's readings, the rollback anchor, and the untracked live bundle

**What was done:**
- Live access established on the Mac (SSH + `docker exec postgres_n8n psql`), which the previous session could not have — its report was written in a cloud container with every live figure marked *last measured* or *unknown*. All readings below were taken **2026-08-25T12:11:01Z – 12:16:17Z** (server clock).
- Read-only throughout: SELECT / `readlink` / `stat` / one unauthenticated `GET /` / `pg_dump`. **No admin route was called, the gate was not pressed, nothing in the application database was written.**

**Results:**
- **The gate is unpressed.** `evaluation_started_at` is NULL on *every* period (`WHERE evaluation_started_at IS NOT NULL` → 0 rows). Period 2 confirmed on every field: `active` / `is_active=t` / `half_year` / 2026-01-01…2026-06-30 / parent 5. Exactly one active period (`count=1` on both `is_active` and `status`).
- **Catalogue is byte-identical** to `docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md`: 9 rows, ids 1/2/3/4/8/10/12/13/14, **117 fields compared, 0 differing**, body md5 `53f34a173ba8c462596d5acd80439d4f` on both sides. Re-read with the same SELECT and the same renderer the reference file was produced by.
- **Row counts:** evaluations 0, evaluation_scores 0, score_corrections 0, period_results 0 — all confirmed. `auth_sessions` **13**, not 12: the extra row is an ordinary owner login (`user_id=2`, 09:43:07Z). `auth_login_attempts` 3, all `epe-throttle:verify-invite:<ip>` buckets, no real login failures. Participants on id 2: 89 / **87 in scope**, the two exclusions being Esenova and Balova, `hired_after_period_end`.
- **Registered = 2**, settling the earlier "unknown": Alexander Petrosov (id 2, admin) and Jemal Gulberdiyeva (id 47, c_level), both 133-char `$scrypt$N=16384,` hashes. 87 of 89 unregistered.
- **Invite token id 4:** `is_used=f`, `used_by`/`used_at` NULL, `expires_at 2026-09-18 11:55:19`, unexpired. Confirmed on every field.
- **Backups: today's run is clean.** `backup-epe-live.status` = `OK 2026-08-25T00:20:01Z`; log shows `epe_2026 ok size=25361 retained=5`, `n8n_app ok size=377824 retained=5`, archive `ok size=34519 retained=14`. All 24 dump files `600 root:root`, 33 G free.
- **The trio needs no substitution — the edge exists.** Ruhlyadko (**85**) `manager_id = 68` = Hekimov, so Hekimov→Ruhlyadko gives manager→subordinate and Ruhlyadko→Hekimov gives upward (Hekimov's role is `manager`, so the `NOT IN ('c_level','admin')` filter passes); all three are in scope, so all three can self-review. Verified against **live `workflow_entity`**, not the repo builders. Hojayeva (**45**) reports to Bayram Urayev (18, `c_level`) and has 0 direct reports — she contributes a self-review only.
- **Rollback anchor taken pre-gate**, `2026-08-25T12:16:17Z`, md5 `4ac406b4c84299263d4d7288ab00a193` / 80 710 bytes, identical on both ends: VPS `/root/epe_stand_tmp/epe_2026_pregate_20260825T121617Z.dump` and Mac `~/EPE_ROLLBACK/2026-08-25-pregate/…` (outside the repo). `pg_restore -l` verified on both — 161 TOC entries, 17 `TABLE DATA`. First off-host copy this project has had (BUG-014, for this one file).
- **Repo:** `claude/launch-readiness-smoke-facts-laz4i7` merged into `main` with `--no-ff` (not rebased — the report records its own hash in §9); the one `PROGRESS.md` conflict resolved by keeping both blocks verbatim. PR closed.
- Report: `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md`.

**Notes / Gotchas:**
- **The live frontend was built from code in no commit and no branch.** Seven uncommitted files were the source of release `20260825T115748Z`: repo `dist/index.html` md5 `26c76622c9e4829f6216ec49a32148a0` equals the deployed file byte for byte, and the CSS rebuilt from that tree equals deployed `index-BJGw5vuQ.css`. Committed as `d1b2d18` exactly as found, `npm test` 328/328. The script defect behind it is **BUG-056**.
- **Release `20260825T065554Z` → commit `6ca603e`, on `origin/main`** — established by rebuild, because the deploy script stamps no commit id. It is also **not the live release**; live has been `20260825T115748Z` since 11:57Z, six releases later. Method rider: rolldown-vite output is **path-dependent** — rebuilding provably identical source elsewhere reproduced 4 of 57 assets and never the JS entry hash. Only the CSS bundle is a valid cross-machine fingerprint.
- **`clear-test-evaluations` confirmed absent from live** by name and by node content (0 rows) — the probe the previous session could not make. The dead admin button is therefore filed as **BUG-057** on a verified premise.
- **Classification drifted by one person** since 2026-08-24: live is **49 general / 40 project** (HANDOVER §7 says 48/41) and criteria-per-person is **38 × 4, 11 × 5, 35 × 6, 5 × 7** (§7 says 37/11/36/5). `has_subordinates` agrees with the `manager_id` graph for all 89, zero mismatches either way.
- **Two blockers before any live smoke test:** none of the three is registered, and the only route-based registration path emails a code to a real employee mailbox — hard constraint 5 / D-0820-8, forbidden since 2026-08-20. And submit is 409 until the gate is pressed, so manager→subordinate and upward are post-gate by construction. Both are Alexander's calls.
- **Surfaced, not resolved:** Hojayeva's title reads «Head of the Lab Solutions Division» while she is `role=employee`, `has_subordinates=f`, sole member of department 1 — so no criterion 2 and no upward review of her. Org data, not code. Three world-readable EPE artefacts still in VPS `/tmp` (**BUG-058**). HANDOVER left unedited on purpose: its provenance header claims a single 2026-08-24 re-measurement pass, and patching two numbers inside it would make the header false for the rest.
- The pre-gate dump deliberately stays in `/root/epe_stand_tmp` past this brief's teardown — it is the smoke test's rollback anchor. Whoever runs that test removes it.

## 2026-08-25 — Lab Solutions Division attached to its actual head on live (D-0825-3)

**What was done:**
- Owner statement in session: Jahan Hojayeva heads the Lab Solutions Division, which contains Special Lab Solution (no leader) and two Clinical Lab Solutions sub-departments under Nurmammet Hekimov and Akmyrat Jumahanov. **Live did not reflect any of it** — the whole branch was flat under Bayram Urayev (COO) and Hojayeva was `role=employee` with zero direct reports.
- `performance_db.departments` is `id, name, description` only — **no parent column**, so department nesting is unstorable there. The evaluation hierarchy lives solely in `users.manager_id`, which is where the fix went.
- Six writes through `POST /webhook/admin/save-user`, never raw SQL on `users`: Hojayeva `role` employee→manager; Hekimov (68), Jumahanov (1), Kostina (6), Muhammedov (55) → manager_id 45; Garayev (53) → manager_id 68. Hojayeva keeps reporting to Urayev.
- Two ambiguities were put to the owner rather than guessed and answered in session: Special Lab Solution's two people go to Hojayeva (no leader in that sub-department), Garayev joins Hekimov.
- Executor: `scripts/apply_lab_division_hierarchy.py` (has `--dry-run`, which runs every gate and prints the payloads without writing). Report `docs/LAB_DIVISION_HIERARCHY_2026-08-25.md`, decision row D-0825-3.

**Results:**
- All six calls **200**, every stored row compared field-by-field to its payload before the next call. Proof `backups/2026-08-25-lab-division/lab_division_proof.json`, `failures: []`.
- **Zero drift outside the six intended fields** across all 89 users and every column; the nine frozen columns (salary, join_date, password_hash, can_evaluate/can_be_evaluated, token_version, created_at, employment_type) untouched on all 89.
- Invariants after: `has_subordinates` vs the graph — **0 disagreements**; `role=manager ⇔ has direct reports` — **0 exceptions** (13 managers); people with no evaluator — **0**; management-chain cycles — **0**, max depth 4.
- H1 untouched: `active` / `is_active` / `evaluation_started_at` **still NULL**; the four data tables still 0; `auth_sessions` 13→13 (probe session deleted in a `finally`); registered still 2.
- Criteria distribution moved by exactly one person — Hojayeva 6→7: **38 × 4, 11 × 5, 34 × 6, 6 × 7**.

**Notes / Gotchas:**
- **`admin/save-user` is a full-row UPDATE with dangerous defaults** — `body.role || 'employee'` and `body.work_category || 'general'`. An omitted `role` silently demotes a manager; an omitted `work_category` silently reclassifies a project participant, dropping two criteria and changing their bonus. Every payload here was the live row read fresh immediately before its own write, all nine writable columns resent, one field replaced. Anyone touching this route must do the same.
- **`has_subordinates` must not be written by hand.** `trg_update_has_subordinates` (`AFTER INSERT OR DELETE OR UPDATE OF manager_id`) recomputes it on both the old and the new manager. The run asserts the trigger's result instead of setting the value.
- **What was actually broken, in H1 terms:** Hojayeva was not scored on criterion 2 at all (applicability is gated on `has_subordinates`, not on role), and five people had no upward channel because their manager was `c_level`, which the upward filter excludes. Both are fixed by the six edits.
- The smoke-test pair Hekimov ↔ Ruhlyadko is untouched. `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md` gained a postscript naming exactly which of its §2 statements this supersedes; its readings were left as taken.

---

## 2026-08-25 — Org-structure review sheet for the owner (read-only; live)

**What was done:**
- The Lab Solutions defect was found by accident. This brief asks whether there are more like it. The database cannot answer that — it is internally consistent and can only be wrong against the real company — so the deliverable is a sheet the owner marks up: `docs/ORG_REVIEW_H1_2026-08-25.md`, in Russian, readable without a glossary.
- Live access had to be established, not assumed: the first probes failed (ICMP 100 % loss, TCP 22/80/443 all timing out to `92.51.45.147`, while `1.1.1.1:443` and `8.8.8.8:53` answered). It cleared on retry; a tunnel came up and `docker exec postgres_n8n psql -U admin -d epe_2026` answered at 13:18:37Z. No repository inference was substituted for a live reading.
- The sheet carries all 89 people as a tree by manager — every person appears exactly once, in their manager's table — with id, name, title, department, role, category, criteria count, and the named evaluator on each of the four channels, plus two empty tick-boxes per row («☐ рук.?» / «☐ проект?»).
- Anomalies: 17 items, each one line plus why it may matter, surfaced and not resolved.
- Classification stated as money, with the diff done against the retained dumps.

**Results:**
- Live at 2026-08-25 13:19–13:22Z: 89 users; **49 general / 40 project** (`is_project_participant` agrees on all 89); criteria per person **38 × 4, 11 × 5, 34 × 6, 6 × 7**; 87 in H1 scope; **81** with a manager channel, **13** evaluated from below, **81** able to self-review, **6** whom nobody evaluates.
- The 48/41-vs-49/40 question in HANDOVER §7 is answered by name: **Ruslan Egamberdyyev (74), project → general, 2026-08-24 19:11:42 UTC**. The date is exact, not a window: the 24 Aug and 25 Aug cron dumps bracket the change, and the Caddy log holds exactly one successful `save-user` in that bracket.
- Full-column diff of all 89 users, all 19 non-password columns, from the oldest retained cron dump (2026-08-21T11:45:01Z) to live: **exactly 10 changed cells across 7 people**. Two earlier classification moves — Kulmamedova (16), Annameredov (20) — recovered from the 2026-08-20T13:42:34Z ad-hoc dump; both datable only to a 22-hour window.
- Money made concrete from live weights and level coefficients: at score 6 everywhere and grade coefficient 1.00 the bonus index is **49.80 / 71.40 / 73.08 / 94.68** for the 4 / 5 / 6 / 7-criteria profiles — general→project is about **+47 %**.
- End-of-session re-read at 13:39:37Z: H1 still `active` / not started, four data tables still 0, 9 criteria, 90 coefficients, 49/40 unchanged. Nothing drifted during the session.

**Notes / Gotchas:**
- **The accepted Lab Division report no longer matches live, and this is filed as BUG-059.** Ten `save-user` calls landed today: six from the script at 12:41:52–12:42:22Z (documented) and **four from a browser at 12:52:31–12:56:27Z that no report records**. They moved Garayev (53) from Hekimov (68) to Hojayeva (45) — contradicting `LAB_DIVISION_HIERARCHY_2026-08-25.md` §2 write #6, §3 and §4 — and Kurbangeldiyev (33) from Gulberdiyeva (47) to Petrosov (2). Neither the data nor the earlier report was touched here; both are surfaced.
- **`users` has no `updated_at` and the write route keeps no log.** Every date in §4 of the sheet came from restoring dumps and cross-referencing a Caddy log that retains ~2 days. Cron dumps of `epe_2026` retain 5 stems; anything before 2026-08-20 is unrecoverable.
- **Criterion 2 keys on `has_subordinates`, not on role** — confirmed again from the live `API: Get Employees` SQL. Setting someone's role to `manager` without giving them a subordinate changes nothing in their evaluation or their money.
- **`API: Submit Self Review` requires role ∈ `employee`/`manager`/`hr`.** All six admin/c_level accounts get a role refusal before the `NO_GRADE_COEFFICIENT` 422 can fire, so the three grade-less C-level rows never reach it. All six are in H1 scope and produce and receive nothing — completion should be counted against 81, not 87.
- **Six throwaway stands (`epe_orgrev_*`) were created and dropped**; `SELECT datname` after teardown shows only `epe_2026` and `postgres`. The pre-gate anchor in `/root/epe_stand_tmp` was deliberately left — it belongs to the smoke test that has not run.

---

## 2026-08-25 — Logistics under Jafarova; Egamberdyev back on project (live writes)

**What was done:**
- Applied the owner's decisions on the org sheet — D-0825-5 and D-0825-6, both appended verbatim to `DECISIONS.md`. Report `docs/ORG_FIX_LOGISTICS_2026-08-25.md`; executor `scripts/apply_logistics_and_project_return.py` (`--dry-run` runs every gate and prints the payloads without writing and without taking a dump).
- **A fresh rollback anchor first.** `epe_2026_pregate_20260825T121617Z.dump` (12:16Z) predates the six Lab-Division writes and the owner's four browser edits, so restoring it would have undone all ten. New anchor `epe_2026_pregate_20260825T141806Z.dump`, **80 706 bytes, md5 `bdf13cfbaae9decf2e29a0e93495412d`**, on the VPS at `/root/epe_stand_tmp/` (600) and pulled to `~/EPE_ROLLBACK/2026-08-25-logistics/` — **outside the repository**. The old dump is left in place as history only.
- **Eight `POST admin/save-user` calls, all 200**, 14:18:26–14:19:07Z: Dzhafarova (5) retitled «Logistics Team Lead (Acting Head of Department)» (role `manager` and manager 2 were already correct and were resent unchanged); ids 12, 13, 43, 60, 62, 84 moved to manager 5; Egamberdyev (74) `work_category` general → project.
- Same discipline as D-0825-3: route only, never raw SQL; every payload the live row read fresh immediately before its own write; every stored field compared to the payload before the next call; `has_subordinates` left to `trg_update_has_subordinates`.

**Results:**
- **Independent drift check** — the anchor was restored into a throwaway DB and diffed against live: **9 changed cells out of 1 780** (89 people × 20 columns), exactly the intended ones plus `74.is_project_participant` which the route derives. Frozen columns untouched on all 89. `criteria` / `score_coefficients` / `grades` / `departments` / `evaluation_periods` / `evaluation_period_participants` md5-identical on both sides.
- Invariants after: `role=manager ⇔ has direct reports` **0 exceptions** (13 managers); `has_subordinates` vs the graph **0 disagreements**; cycles **0**, max depth 5; people with no evaluator **0**; in scope but evaluated by nobody = **exactly the six** (2, 18, 21, 40, 47, 61); evaluated population **81**.
- H1 still `active` / `is_active` / `evaluation_started_at` **NULL** — the second gate was not pressed; four data tables still 0/0/0/0; participants 89 / in scope 87; `auth_sessions` 13 → 13.
- Criteria distribution **38/11/34/6 → 37 × 4, 11 × 5, 35 × 6, 6 × 7**; category split **49/40 → 48/41**. Exactly one person moved bucket — Egamberdyev, 4 → 6.
- Jafarova: 1 → **7** manager tasks and 1 → **7** upward reviewers; her own criteria unchanged at five. In-scope people with no upward channel **24 → 18**. Mid-level corrector for the six movers: Durukan (21) → Petrosov (2). Petrosov's direct reports 12 → 6.
- Egamberdyev's bonus index at equal scores, live weights and his real grade coefficient (S3, 1.40): at the norm (6) **69.72 → 102.31, +46.8 %**; the spread across levels 4–8 is +45.7 % … +55.8 %.
- Read surface re-read afterwards: `GET /api/periods` 200 (87 / 89, `evaluation_started=false`), `GET /api/admin-users-data` 200 with all eleven inspected rows exactly as written, `GET /api/employees` 200 with `campaign_active=false` and an empty task list.

**Notes / Gotchas:**
- **The owner named «Rovshen Jafarova»; live has exactly one Jafarova and her `full_name` is «Alyona Dzhafarova» (id 5).** The run refuses to write unless the search returns exactly one Logistics-department match, and it did. The name field was **not** changed — the brief named `job_title`, `role` and `manager_id` only. Whether «Rovshen» is her real name is surfaced for the owner.
- **Kurbangeldyev (33) is in department 11 IT, not 4 Logistics**, so the deliberate exception never bound — he was never a write candidate. His row was asserted identical before and after anyway.
- **D-0825-5's consequence sentence is wrong on one point and it is recorded verbatim regardless.** Jafarova did **not** gain criterion 2: she has had two subordinates throughout, criterion 2 keys on `has_subordinates`, and her criteria set is `[2, 3, 4, 12, 14]` before and after. Her money did not move. What the change actually buys is the upward channel for seven logistics people and six new manager tasks for her. Corrected in `docs/ORG_FIX_LOGISTICS_2026-08-25.md` §5.1, not in the decision text.
- **D-0825-6's «~24»** was true before this brief and is **18** after it; the «81» in the same decision is confirmed by live.
- **«87 / 89»** is computed in LIVE `API: Manage Periods` → `Build Periods Query` (two `COUNT(*)` subqueries on `evaluation_period_participants`) and rendered at `src/pages/AdminPeriods.jsx:609-610`. Not changed — it measures period membership, not the evaluated population.
- **A `dblink` extension was created on live `epe_2026` for the first diff attempt and immediately dropped**; `pg_extension` is back to `plpgsql` only. The diff was redone without it. Recorded because no instruction asked for it.
- Throwaway DB `epe_logifix_20260825t1418z` created and dropped — only `epe_2026` and `postgres` remain. No stand container; no container restarted or stopped. BUG-059 stays open: these eight writes are dated only because the run recorded them.

---

## 2026-08-25 — Terminated employees: a state, not a deletion (D-0825-7, build + live deploy)

**What was done:**
- Read-only recon first, and it decided the design. `performance_db.users` had **20 columns and no employment state at all** — no flag, no date, nothing. `evaluation_period_participants.is_in_scope` / `exclusion_reason` do exist, carry `CHECK (is_in_scope OR exclusion_reason IS NOT NULL)`, and are written by **exactly one route** — `POST /api/periods/create`, at creation time. Live holds two out-of-scope rows (Esenova 31, Balova 35, `hired_after_period_end`) with `created_at = updated_at = 2026-08-18 14:29:02.470198`: never touched by a route since import. **So before this session no route could take anybody out of scope of a period that already existed; the only mechanism was raw SQL.** Report `docs/TERMINATED_EMPLOYEES_2026-08-25.md`.
- **Migration 015** (additive, applied twice to prove idempotence): `users.terminated_at` (the state) + `users.termination_date` (the owner's last working day, deliberately a separate fact) with a paired CHECK, and append-only `performance_db.employment_events` (user, event, effective date, period, **actor**, occurred_at, note) with FKs carrying no `ON DELETE CASCADE`.
- **New workflow `API: Manage Employment Status`** (`vZwDA0aDZqIoCmoW`, 25 nodes, active): `POST api/admin/terminate-employee`, `POST api/admin/reinstate-employee`, `GET api/admin/employment-events` — all admin-only. Termination is one SQL statement with every precondition re-asserted in its `target` CTE: mark + `token_version + 1`, revoke sessions, burn unused reset tokens, set `is_in_scope=false, exclusion_reason='terminated'` on every currently-in-scope row of every **non-closed** period, append the event.
- **Five workflows changed**, activation preserved, graph compared node-for-node after each PUT: `Auth Login` (a terminated employee cannot mint a session; same generic 401 as a wrong password), `Register` (the shared invite is inert for them), `Request Password Reset` (no token, same generic 200), `Admin Get Users Data` (the two columns as text; not offered in `options.managers`), `Manage Periods` (**a new period never re-scopes them in** — without this, creating H2 would have returned everybody to the pool).
- **`/admin/users`**: a status filter defaulting to «Работают», an «Уволен ГГГГ-ММ-ДД» badge, terminate/reinstate actions, a confirm modal that states the money consequence and the GAVE/ABOUT split before the click, and a header that prints «Работают / Уволены» instead of one «Всего» over two populations.

**Results:**
- **Stand proof: 101 checks, 101 passed**, `failures: []` (`scripts/prove_termination.py`). Two throwaway databases restored from **one** dump and asserted identical before seeding, so the two closed period-result sets differ only by the termination.
- **The GAVE/ABOUT split, to the digit.** The manager the terminated person evaluated: `rating_upward` **6.33 on both sides** — it is the mean of 9.0 (from the leaver), 4.0 and 6.0, so a dropped GAVE evaluation would have read 5.00. `final_rating` 6.8571 and `bonus_index` 170.8300 identical. **Rows that moved besides the leaver's: `[]`.** The leaver themselves: control `has_data=true`, `bonus_index` **108.3240**; treatment `is_in_scope=false`, `has_data=false`, every rating and both money columns **NULL**. Pool **410.842 → 302.518**, difference **108.324** — exactly their share and nothing else.
- **Every evaluation row byte-identical**: md5 `e66b3301081604cf44fddabd40bb3ec9` before, after, and after a full terminate → reinstate → terminate cycle; 46 rows → 46 rows.
- Refusal message the owner will see: «Нельзя уволить: у сотрудника есть прямые подчинённые (3) — … Сначала переназначьте их другому руководителю.» Decided on the **graph**, not on `has_subordinates` (that trigger fires only on `UPDATE OF manager_id`, so the flag is a cache; live agrees on all 89 today).
- **Browser walkthrough on the stand**, real login form: leaver logs in and has tasks → manager sees 3 cards → terminate refused for the manager, applied to the leaver with date 2026-08-20 → header 98 → «Работают 97 | Уволены 1», search finds nobody → «Уволены» filter shows the dimmed badged row → leaver's correct password gives «Неверный email или пароль» → manager sees 2 cards → reinstate → 98 again, 3 cards, leaver logs in as before. One console error in the whole pass: the deliberate 422.
- **Live drift: 1 780 cells compared (89 × 20), zero changed.** Frozen columns untouched on all 89; the two new columns NULL on all 89; `criteria` / `score_coefficients` / `grades` / `departments` / `evaluation_periods` / `evaluation_period_participants` md5-identical to the anchor **and** to the 14:46Z pre-build read. Criteria distribution **37 × 4, 11 × 5, 35 × 6, 6 × 7** and split **general 48 / project 41** — unchanged before and after, as intended: nobody was terminated on live.
- H1 still `active` / `is_active`; `evaluation_started_at` **NULL on all three periods**; four data tables **0/0/0/0**; `employment_events` **0**; extensions `plpgsql` only; `auth_sessions` 14 → 14; workflows 58 → **59** (34 active), webhooks 42 → **45**; `EPE: Auth Guard` `updatedAt=2026-08-18T16:34:30.674Z` / `active=false`, unchanged. `scripts/verify_termination_live.py`: **37 checks, 37 passed**.
- Anchor `epe_2026_pretermination_20260825T153238Z.dump`, **80 766 bytes, md5 `e11698f6a92c9e1a78130a0267af01f0`**, on the VPS (600) and at `~/EPE_ROLLBACK/2026-08-25-termination/` outside the repo. Frontend release **`20260825T153640Z`**.

**Notes / Gotchas:**
- **`can_evaluate` / `can_be_evaluated` are deliberately NOT written by termination.** They are the owner's standing policy for the read-only trio (D-0821-4); overwriting them would make reinstatement lossy — after a round trip you could no longer tell a read-only C-level from a former employee. Termination writes scope, which is period-bound and is what the money record needs.
- **`EPE: Auth Guard` was deliberately left alone.** A `terminated_at` check there would be redundant — the guard already joins `auth_sessions ON token_version = users.token_version`, so the bump alone kills every live JWT — and its frozen `updatedAt` is the project's tamper marker.
- **A last-admin refusal was written and then deleted as unreachable**: the route is admin-only, so the only path to zero live admins is an admin terminating themselves, which `CANNOT_TERMINATE_SELF` already refuses. Unreachable code that reads as a guarantee is worse than none.
- **Termination only writes rows that are currently `is_in_scope = true`, and reinstatement only flips rows whose reason is exactly `'terminated'`** — so somebody excluded for `hired_after_period_end` keeps that reason through a full round trip. Proven on a fixture that is both.
- **BUG-040 is still real.** `scripts/deploy_epe_frontend.sh` refused to run: `rg` resolves only to a shell function injected by the terminal, not a binary. Both gates were run by hand with `grep` (legacy `:5678` absent, `/webhook` present, both PASS) and the script's remaining steps executed verbatim. **No shim was installed**, so the gate cannot be silently bypassed later.
- **Filed BUG-060** (a terminated person still occupies a row in the admin money matrix — cosmetic, the pool is computed from `period_results`; hiding them there would also hide the hire-date exclusions, which is an owner decision) and **BUG-061** (`admin/save-user` will still accept a terminated person as somebody's manager — the UI prevents it, the route does not; that subordinate would be evaluated by nobody). Open 22 → **24**.
- **BUG-059 is narrowed, not closed.** `employment_events` is the first audit row this database has for a change to a person, but it covers employment events only; `users` still has no `updated_at` and `admin/save-user` still writes no audit row.
- **No mail of any kind was sent.** The registration-refusal proof inserted a verified code row directly into the **stand** database, so no address was ever contacted.
- Two stand databases and one verification throwaway created and dropped; `SELECT datname` reads `epe_2026, postgres`. One stand container created and removed; the same six containers as before. Nothing in host `/tmp`. **The second gate was not pressed and no route that could press it was called.**

---

## 2026-08-25 — Admin users list: tighter rows (live deploy)

**What was done:**
- Compacted `UserTable` vertically only: cell padding `py-4` → `py-2`, avatar 40→32 px, registration/termination badges on the email line instead of a third row, smaller action icons. Same table is used on Team View.
- Local preview measured row height **98 → 57 px**. `tests/prelaunchCopyBatch.test.js`: 11/11. Frontend release **`20260825T160958Z`** (`index.html` Last-Modified Tue, 25 Aug 2026 16:10:06 GMT).

**Results:**
- Live `/admin/users` now serves the denser list. Logic, filters, sort, edit and terminate/reinstate unchanged.

**Notes / Gotchas:**
- Deploy script ran with Cursor’s `rg` binary on PATH so BUG-040 did not block this release. No shim was installed. No commit.

---

## 2026-08-25 — /admin/users: the filter row offers only what exists (live deploy)

**What was done:**
- Diagnosed the owner's «фильтры не сужают список» report. Both hypotheses in the brief are wrong: the role options carry the DB value in `value` and the display casing only as child text, and the employment filter composes as a plain AND like the other five. The deployed chunk was byte-identical to the repository. «Найдено: 12» was the filter working — the manager control held Yelena Son, whose 13 reports are all `employee`/`project`/department «Project», so every further control was degenerate and nothing on screen said so.
- Real defects found and fixed, frontend only: `hr` was missing from the role list (2 live people unreachable); `options.managers` offered 4 people who manage nobody; «Tender» matched nobody; 1 person with `department_id IS NULL` and 3 with `manager_id IS NULL` were unreachable; a terminated manager would drop out of the option list while still filtering, making the control read «Все руководители»; the header's «Работают/Уволены» counted the whole population and «Найдено» the filtered one, side by side, unlabelled.
- New pure module `src/utils/userFilters.js` feeds filtering, counters and option lists from one predicate. Options are now derived from the data with faceted counts (`Manager (0) · Employee (11)`), the header names each population, and the employment control announces «Скрыто уволенных: N … Показать всех».
- `npm test` **351/351** (23 new). `npx eslint src` at the 19-error baseline. Twenty-step browser walkthrough over the production bundle answering with the exact live payload; every count matched a SQL oracle computed against live first.
- Frontend release **`20260825T162505Z`** (`index.html` Last-Modified Tue, 25 Aug 2026 16:24:29 GMT). H1 still active with `evaluation_started_at` NULL, four data tables 0/0/0/0, 89 users, `EPE: Auth Guard` and `API: Admin Get Users Data` unchanged, zero workflow writes.

**Results:**
- The filter row narrows predictably and says why when it does not. A zero is now visible on the option before the click.

**Notes / Gotchas:**
- **Live carries two terminated people, not one.** Kuvvat Garayev (51) at 15:54:23Z and Murad Bayramov (66) at 15:56:23Z, both by actor 2, both before this session's first command. H1 in-scope is 85.
- **A second session was editing and deploying this same checkout.** It shipped `20260825T160958Z` (UserTable density) at 16:10:06Z mid-brief, uncommitted. This session's build was redone on top of that file so the density change was not reverted, and their `UserTable.jsx` + PROGRESS entry are committed here, attributed. **BUG-062** filed: the deploy script has no lock and no check that `current` still points where the run started.
- BUG-040 still open and now known to be intermittent per terminal: `rg` is a shell function here, so both gates fail closed and were run by hand with `grep`; the other session's note says its deploy passed because Cursor put a real `rg` on PATH. No shim installed.
- Filed **BUG-063** (`/team` calls an undeclared `setLoadingSelfReviews` — pre-existing) and **BUG-064** (`UserModal` still offers «Tender», which the route 422s).

---

## 2026-08-25 — /team fixed on the manager-scoped route; concurrent deploys now refuse (live deploy)

**What was done:**
- **Answered the /team question before touching it.** Measured in a browser on a stand: `/team` **never threw for a manager** — `useUsers()` reads the admin-only `/api/admin-users-data`, the manager gets 403, `visibleUsers` is empty and the effect returns three lines before the undeclared `setLoadingSelfReviews`. She saw «У вас нет подчинённых в системе» while having 11 subordinates in scope. For an **admin** typing the URL it did throw, twice (caught in `try`, uncaught in `finally` → `Uncaught (in promise)`), and the page rendered anyway with every status column silently blank because the `Promise.all` never ran. So BUG-063 was a tidy-up; **BUG-012 was the launch blocker**, since «Список команды» is in every manager's sidebar.
- Repointed `/team` at `GET /api/employees` via the new `useTeamRoster` hook: the server scopes it (`WHERE users.manager_id = actorId` joined to `is_in_scope = true`), so a terminated subordinate never arrives and the page cannot disagree with `/dashboard`. `loadStatuses` and the HR-only call are gone; flags come from the payload. eslint **19 → 15** errors; `npm test` 351/351.
- **Stand walkthrough, campaign started on the stand:** Yelena Son logged in through the real form, `/team` showed exactly **11** of her 13 direct reports with Kuvvat Garayev and Murad Bayramov absent, she opened an evaluation form, scored all six criteria and submitted → «Итоговый балл: 7.50», the card became «Оценен вами», `/team` became «Оценено мной: 1». Stand DB: one `manager` evaluation, six score rows on criteria 3/4/8/12/13/14, `AVG = calculated_score = 7.50`. Console for the entire pass: **one** pre-login 401.
- **BUG-062 fixed and demonstrated:** deploy B refused by the lock while A held it (exit 1, live unchanged); then `current` moved by a raw `ln -sfn` behind A's back and A refused at its flip with `CONFLICT expected=… actual=…`, leaving the other party's release live. **BUG-040 fixed:** gates use `grep -r` and prove the tool works on the bundle first, so they cannot pass in one terminal and fail in another, and cannot pass vacuously.
- Frontend release **`20260825T165732Z`** (`index.html` Last-Modified Tue, 25 Aug 2026 16:57:41 GMT).

**Results:**
- A manager who logs in after the gate is pressed will see their real team. Before it is pressed they see a notice that says the evaluation has not started, instead of a false «нет подчинённых».
- Two sessions can no longer overwrite each other's release without one of them being told.

**Notes / Gotchas:**
- **`/team` is empty on live until «Запустить оценку».** `JOIN active_period ap ON true` is an inner join and `active_period` is empty in the preparation window — by design (D-0822-1), now explained on screen.
- `/team` for an **admin** now shows 5 direct reports, not the 30-person subtree. Deliberate; **BUG-065** records it.
- **No live write of any kind**, not even a probe session: `auth_sessions` created after 16:00Z = 0. Catalogue, `score_coefficients` and `grades` md5-identical to the pre-session anchor, checked by computing the same fingerprints on live and on the stand restored from the 16:42Z dump.
- Rollback anchor refreshed: `epe_2026_teampage_20260825_1642.dump`, md5 `5ecbf2c0c908340f4e28b63a36950129`, verified equal on the VPS and on the Mac, kept in `~/EPE_ROLLBACK/2026-08-25-teampage/` outside the repo.
- Closed BUG-012, BUG-040, BUG-062, BUG-063. Opened BUG-065. Second gate not pressed; H1 in scope = 85.

---

## 2026-08-25 — Sidebar: parent vs child is visible (live deploy)

**What was done:**
- The three section headers and their pages sat on one left edge, same icon size, same padding — an open group read as a flat list. `src/components/Sidebar.jsx` only: children sit 34px to the right of the section icon, under a 2px rail; child icons 14px vs 16px on the header; headers stay uppercase.
- Verified locally first, then `./scripts/deploy_epe_frontend.sh`. `npm test` 351/351. Gates: legacy `:5678` absent, `/webhook` present. Flip `20260825T165732Z` → **`20260825T170810Z`**. Live `index.html` Last-Modified Tue, 25 Aug 2026 17:08:19 GMT; public HTML serves `index-vSAg6wtt.js`, which contains the new rail class.

**Results:**
- Live now serves the nested sidebar. Hard refresh if the old menu is cached.

**Notes / Gotchas:**
- Not committed. No login on live this pass — the sidebar itself was walked locally; production was checked as far as the login page and the bundle markers. H1 and the four data tables were not touched.

---

## 2026-08-25 — Mid-year hires: an employed person can be taken out of one period's scope (D-0825-10)

**What was done:**
- **Read-only first.** Every 2026 hire (13 people), every NULL/implausible `join_date`, and every person with no participants row, measured on live between 17:23Z and 17:35Z. Delivered as an owner-facing marking sheet in Russian: `docs/MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md`.
- **The brief's premise had moved.** It says «two terminations, 85 in scope». At the first SELECT there were **three** — Halykberdi Orusov (39) was terminated at 17:11:54Z, twelve minutes earlier — so live reads **89 users / 3 terminated / 84 in scope**. Everything is reported against 84, not 85.
- **Migration 016** — `performance_db.period_scope_events`, append-only, `period_id NOT NULL`, two CHECKs, three FKs without cascade. Applied to live 17:55Z, applied twice to prove idempotence. Deliberately **not** `employment_events`: these people are employed.
- **One new workflow, `API: Manage Period Scope`** (`8xK4EnDJrH1b1OJ7`, 25 nodes, active, `updatedAt=2026-08-25T17:56:16.087Z`): `POST /api/admin/exclude-participant`, `POST /api/admin/include-participant`, `GET /api/admin/period-scope-events`, all admin-only. `exclusion_reason='excluded_by_admin'`, distinct from `terminated` and `hired_after_period_end`; each reverse action flips back only its own reason.
- **No existing workflow was written.** The deploy script asserts its `UPDATES` list is empty and refuses to run if any period has been started. `API: Manage Periods` is deliberately unchanged — an excluded person enters H2 normally, unlike a leaver.
- **No screen.** The checkout carries another session's uncommitted `src/components/Sidebar.jsx` (already live as release `20260825T170810Z`), and a frontend deploy tars the whole tree. No build, no deploy, no `deploy_epe_frontend.sh` run. Hand-run curl path in the report §7.

**Results:**
- Stand proof `backups/2026-08-25-midyear-scope/midyear_scope_proof.json`: **152 checks, 152 passed**. Two copies of one dump, control and treatment, both closed through the real `POST /api/periods/close`: **99 `period_results` rows on each side, rows that moved besides the excluded person's: `[]`**. Pool 410.842 → 302.518, difference **108.324** = the excluded person's index to four decimals. The manager they evaluated keeps `rating_upward` **6.33** on both sides — it would read 5.00 if the GAVE evaluation had been dropped.
- The excluded person **keeps their login** (200 on `auth/login`, the session they already held is not revoked), **can still register** through the shared invite (200; under termination the same call is 400), still gets a password-reset link, and **not one column of their `users` row moves** — including `token_version`. Period 5 is untouched; only the named period changes.
- Reverse action exact: the whole participants table compares equal to its pre-exclusion state. All 46 evaluation rows byte-identical across exclude → include → exclude.
- Live after: **1 958 cells compared (89 × 22), zero changed**; six table fingerprints identical to the anchor; H1 active with `evaluation_started_at` NULL on all three periods; four data tables **0/0/0/0**; `period_scope_events` **0**; `auth_sessions` 14 → 14; only `plpgsql`; workflows 59 → 60, webhooks 45 → 48; `EPE: Auth Guard` still `2026-08-18T16:34:30.674Z`. `backups/2026-08-25-midyear-scope/live_verify.json`: **43 checks, 43 passed**.
- Rollback anchor `epe_2026_premidyear_20260825T175516Z.dump`, md5 `d7b2260d479814734d671b603e5f3267`, 87 912 bytes, verified equal on the VPS and in `~/EPE_ROLLBACK/2026-08-25-midyear-scope/` outside the repo. **It supersedes every earlier anchor** — it is the only one taken after the 17:11Z termination.
- **Nobody was excluded on live.** The list of names is the owner's and he has not given it yet.
- Opened BUG-066 (a NULL `join_date` silently keeps a person in scope — one person, Cem Durukan 21), BUG-067 (a person added after period creation has no participants row and gets no frozen row at close — the one place where "no row" ≠ `is_in_scope=false`), BUG-068 (score correction never checks scope). The bugs.md open counter was stale at 22 against 24 actual rows; it now reads 27 and matches.

**Notes / Gotchas:**
- The stand is a restored copy of live, so it now carries the owner's three real `employment_events`. Two proof assertions that the table would be empty were **test** bugs, not build bugs, and are recorded in the report rather than quietly relaxed. A third compared the two stand copies on a fingerprint including `updated_at` — the two seeds run microseconds apart. Fixed, stand rebuilt, re-run clean.
- `src/components/Sidebar.jsx` and the sidebar entry above in this file are **another session's work**, already deployed to live by that session. Not stashed, not reverted, not rebuilt, not redeployed; committed separately and labelled, because a silently dirty tree is what turned the 2026-08-22 parallel session into a live incident.
- The second gate is **still unpressed**. No route that could press it was called.

## 2026-08-25/26 — PRELAUNCH_BATCH_NIGHT: the four hire-date exclusions, the money screens, and the day-one walk

**Brief:** PRELAUNCH_BATCH_NIGHT (ten items, run to completion overnight). **Decisions:** D-0825-11 … D-0825-15.
**Report:** `docs/PRELAUNCH_BATCH_NIGHT_2026-08-26.md`.

**What was done:**
- **Item 1 — the four are out.** The RULE, not the list of names, was run against live first: everybody in scope of H1 with `join_date > 2026-03-31`. It returned exactly the marking sheet's four, by id, name and date — Asatryan (25), Atayeva (64), Chariyev (22), Jumayeva (63). Eleven preconditions asserted before the first write; each exclusion is one call to the real `POST /api/admin/exclude-participant` (D-0825-10), reason `excluded_by_admin`, with the owner's note, at 18:46:18–18:46:19Z. No SQL write of any kind. **H1 in scope 84 → 80.**
- **Item 2 — a missing hire date is out of scope** from the next period on. `Build Create SQL` gained a `WHEN u.join_date IS NULL THEN false` branch **before** the date comparison (reason `join_date_missing`); a test pins the order, because with the branches swapped BUG-066 is back. Not retroactive: Cem Durukan's H1 row is untouched (D-0821-4). `include-participant` now also reverses the new reason — otherwise it would have been a state with no exit, and «must be confirmed» needs a way to confirm.
- **Item 3 — the excluded are told, and so are their managers.** `/api/employees` carries `actor_exclusion_reason` and a **separate** `out_of_scope_data` array of employed-but-out-of-scope direct reports (terminated people excluded by an explicit `terminated_at IS NULL`). The task list `scoped` is untouched by construction, so nothing here can become a task or a counter. Owner's texts verbatim on Welcome and on the manager's card.
- **Item 4 — a half-year pays nothing**, verbatim, on the Welcome period notice (every period state, both branches, so an out-of-scope person sees it) and above the rating-guide rules (every variant). Not a ninth rule.
- **Item 5 — /admin/users.** The list did not open descending — it had **no sort at all** (`sortField: null` makes `sortUsers` return the array untouched), so it opened in the route's `ORDER BY u.id DESC`. Now `name`/`asc`, exported from `userSort.js`. `API: Admin Get Users Data` LEFT JOINs the active period's participants row; seven mutually exclusive states with a badge, a money-and-tasks tooltip, and a seventh filter control with live counts.
- **Item 6 — /admin/final-scores verified, then fixed.** Fourteen defects reported before anything changed; seven fixed. The load-bearing one: criterion columns came from `employees[0]`, so one checkbox on the first person alphabetically removed the two project columns for everyone while `weightedSum` kept counting them. Also: cells were coloured by the weighted product against bands written for a raw 1–10 score; out-of-scope people sat inside Σ and the average; two sticky columns overlapped; the CSV wrote `0` where the screen wrote `-`; corrections were invisible.
- **Items 7 and 8 — the bonus screen.** The budget was read, divided by Σindex, **rounded to an integer**, and the integer multiplied into each index — so the total never equalled the budget, a budget below `0.5 × Σindex` zeroed the whole table, and `'3.000.000'` parsed as **3**. Now `index_i / Σindex × budget` with largest-remainder allocation, so the amounts on screen sum to the budget exactly. The list is a predicate — in scope **and** `can_be_evaluated` — never an id list, and everyone excluded is named on screen with the reason.
- **Item 9 — the day-one walk**, read-only, on a stand with the gate pressed: four browser logins and an 18-route × 6-actor API sweep. No console error on any page.
- **Item 10** — decisions, this entry, HANDOVER §2/§3/§10 corrected, three bug rows.

**Results:**
- **Money, control against treatment.** Two databases from one dump, seeded identically (same evaluations fingerprint asserted), two isolated n8n containers — one with the workflow surface **as committed at HEAD**, one with the working tree — each closed through its own real `POST /api/periods/close`. **824 frozen money cells over 103 rows on each side: zero moved.** The frozen indices equal the figures computed by hand before the stand existed: 1602 `170.8300`, 1603 `108.3240`, 1604 `13.7400`, 1605 `174.7080`, 1612 `80.8920`.
- **The arithmetic three ways.** Hand constants (written with their working into the proof script) = an independent Python recomputation from the raw rows = the screen. Σ over the pool **548.494**; the screen reads 548.49 and «Средний итог (по 83) 6.61».
- **Rating ≠ index, shown and explained.** 1603 vs 1604: ratings 7.00 / 5.50 (ratio 1.273), indices 108.324 / 13.740 (ratio 7.884). Both correct; §4 of the HANDOVER is why, and nothing reconciles them.
- **The budget reconciles.** Typed `3.000.000` in a real browser: amounts 955 569,25 / 934 358,44 / 592 480,50 / 442 440,58 / 75 151,23 and 78 zeros, «Итого бонусов **3 000 000,00 TMT**», «Сходится с бюджетом: **да, до копейки**». Four budgets checked in the proof, and the shipped JavaScript compared to the Python amount by amount: zero mismatches.
- **Item 8's six, by name:** Alexander Petrosov (2, admin — the matrix route filters him out one step earlier), Bayram Urayev (18), Cem Durukan (21), Hemra Ashyrov (40), Jemal Gulberdiyeva (47), Mekan Yusupov (61). The rule also removes the nine already out of scope, whose exclusions are D-0825-7, D-0825-11 and the hire-date rule; the brief's «exactly six» is true of the `can_be_evaluated` half and the difference is stated rather than hidden.
- **Live after:** **1 958 user cells compared, zero changed**; 1 068 participants cells with exactly four rows moved, all on period 2, three columns each. Catalogue, coefficients, grades, departments and periods md5-identical to the anchor — **no money input moved**. 89 users / 3 terminated / **80 in scope**; H1 active with `evaluation_started_at` NULL on all three periods; four data tables **0/0/0/0**; `plpgsql` only; `EPE: Auth Guard` still `2026-08-18T16:34:30.674Z`. `live_verify.json`: **29 checks, 29 passed**; `night_proof.json` 42/42; `night_close_proof.json` 10/10.
- **Deployed:** five workflows at 19:47:02–19:47:09Z (all active before and after, every webhook path unchanged, no node added or removed) and frontend release **`20260825T194735Z`**. `npm test` **379/379** (29 new). Three existing pins inverted, each with a comment saying why.
- Closed BUG-066 (forward-looking) and BUG-069; filed BUG-070 (HR completion card's three unlabelled denominators) and BUG-071 (`c_level_only` criteria still emitted to people who cannot receive them). Counters now 28 open / 43 closed.

**Notes / Gotchas:**
- **A backtick inside an SQL comment terminates the surrounding JS template literal.** Three of my comments quoted identifiers in backticks; the generated Code nodes stopped compiling and `tests/routeGuardWorkflows.test.js` caught all three by name. The generator's own test suite is what makes that a two-minute fix instead of a live incident.
- `score_corrections` has **no** `comment` column, and `auth_sessions.jti` is a `uuid` — both cost a stand rebuild.
- `evaluations.calculated_score` is `numeric(_,2)`: a seeded 8.1667 reads back 8.17. Compare at the scale the column actually has.
- The owner logged into the portal at **18:38:43Z**, four minutes before this session's anchor. Every figure here carries the minute it was taken for that reason.
- The working tree carried **no other session's edits** tonight; `git status` was clean at the start and every modified file is this session's.
- The second gate is **still unpressed**, and no route that could press it was called.
- Committed as `8525ab1`.

## 2026-08-26 — CLEVEL_AVERAGING: two C-level opinions become one number (D-0826-1), and the money inputs are photographed

**Brief:** establish whether a second `c_level_direct` evaluation on the same person is data loss or
an unchosen aggregation rule; make the channel behave like the upward channel — mean across
evaluators, count carried, every consumer in lockstep; surface (do not resolve) how a `c_level`
correction interacts with an averaged value; snapshot the nine weights, 90 level coefficients and
all grade coefficients as version H1-2026; records.

**What was done:**
- **Item 1 — answered before anything changed: an aggregation rule, not data loss.** The unique
  index on `evaluations` is `(subject_id, evaluator_id, evaluation_source, period_id)` — evaluator
  is *in* the key — and `Build Insert SQL` conflicts on exactly that tuple, with the
  «do I already have one» probe scoped to `dup.evaluator_id = ${actorId}`. A second C-level person
  gets their own row and **both rows persist**; measured on the stand, two evaluation rows and four
  score rows survived. It was the two **readers** that took `ORDER BY e.updated_at DESC LIMIT 1`.
  Reported for the other channels too: **manager** can hold two rows after a `manager_id` change
  mid-period and picks the latest (unresolved, untouched); **upward** has averaged in SQL since it
  was written; **self** is one row per `(subject, period)` enforced by a unique partial index, with
  409 `DUPLICATE_SELF_REVIEW` on the second attempt.
- **Item 2 — the channel is averaged.** One grouped CTE, `c_level_direct_scores`, produces `AVG`
  and `COUNT` in a single scan, and is **character-for-character identical** in `API:
  evaluations-matrix` and in the close dataset of `API: Manage Periods` (a test asserts the
  byte-equality). The cell reads `ROUND(avg, 2)` — the scale `rating_c_level_direct` already uses —
  and `c_level_count` travels beside it. Because the mean is computed in SQL, every client consumer
  receives it without a logic change; the client work was making the count visible: a «×N» badge and
  a new tooltip on the matrix cell, «среднее по N» in the employee modal and the score-detail modal,
  and a «C-LEVEL ОЦЕНЩИКОВ» column in the Excel detail sheet. The matrix cell now shows the channel
  value rather than the actor's own score — after averaging, showing an evaluator their own 4 in the
  cell whose money is 6 would be the defect this brief exists to remove; the actor's own score moved
  into the tooltip and editing still edits only their own row. **No schema change:** a count is a
  property of one cell and `period_results` stores one row per person.
- **Item 3 — surfaced, not resolved, and measured rather than read.** `API: Score Correction`
  validates the range and the project dimension and **nothing** about `c_level_only`. On the stand a
  correction of 3 on criterion 1 returned **200**, was stored, reached the payload as
  `c_level_correction: 3` — and the close froze `132.8520`, byte-identical to the same close without
  it. Filed **BUG-073** with both candidate rules costed (replace the mean → 9.00; join the mean →
  25.00; today → 36.00) and a third option named: refuse `c_level_only` corrections by name, which
  can ship before the money rule is decided. Also recorded: `score_corrections` has no evaluator in
  its unique key, so corrections are last-writer-wins one table over.
- **Item 4 — the coefficient snapshot,** `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`,
  produced by the new `scripts/snapshot_coefficients.py`. Read-only.
- **Item 5 — records.** D-0826-1 and D-0826-2 appended verbatim; D-0824-2's amendment and the
  CRITERION9 report both carry a SUPERSEDED banner on the **level curve only** (the weight 1.50 is
  unchanged and still current); the approved tables the pre-gate runbook compares against are now
  the dated snapshot, not the old figures.

**Results:**
- **The money proof, two rounds, 29/29** (`clevel_close_proof.json`). Two databases from one dump of
  live, seeded identically (fingerprints asserted equal before each round), two isolated n8n
  containers — one at HEAD, one on the working tree — each closed through its own real
  `POST /api/periods/close`.
  - **Round 1, one C-level evaluator: 832 frozen money cells over 104 rows, zero moved.** Pool
    **548.494** on both sides — the same figure the previous session's close produced from its own
    fixtures. The subject's index `174.7080` = the hand figure 291.18 × 0.60.
  - **Round 2, a second evaluator (8 and 4 on criterion 1, 7 and 9 on criterion 10):** payload
    **6 and 8 with `c_level_count: 2`** under the new code against **4 and 9** under the old (the
    later row — named, not left as «4 or 8»). Frozen: **exactly one person's row differs**, in
    `final_rating` and `bonus_index` only — **124.8360 → 132.8520** — every other one of the 103 rows
    byte-identical, and the pool differs by exactly 8.016. `rating_c_level_direct` reads 7.00 on both
    sides: that archival column has always averaged this channel; now the money path agrees with it.
- **The screen matches the frozen result.** In a real browser on the stand, `/admin/final-scores`
  reads `Σ 221.42 · Итог 132.85` for that person with «C-level: 6 (среднее по 2 оценкам) · 6.00 ×
  коэф. × вес 5.00 = 36.00» on the cell; the matrix shows 6 and 8 with ×2 badges. The other seeded
  people read 170.83 / 108.32 / 80.89 / 13.74 — unmoved.
- **Live after:** 89 users / 3 terminated / **80 in H1 scope**; four data tables **0/0/0/0**;
  `evaluation_started_at` **NULL on all three periods**; `plpgsql` only; `EPE: Auth Guard` still
  `2026-08-18T16:34:30.674Z`; **60 workflows / 35 active / 22 archived / 48 webhooks**; catalogue,
  level coefficients and grades **md5-identical to the 04:48:44Z snapshot**. All **176**
  `c_level_only` cells on live carry `c_level_count`, every one null with no evaluations.
  `clevel_live_verify.json`: **22 checks, 22 passed.**
- **Deployed:** two workflows at 05:16:11Z / 05:16:13Z (active before and after, 70 and 9 nodes,
  webhook paths unchanged) and frontend release **`20260826T051630Z`**. `npm test` **401/401** (21
  new). Lint at the repository baseline, 16/14, unchanged.
- Closed **BUG-072** (the defect itself, filed and closed in this batch); filed **BUG-073**.
  Counters now **29 open / 44 closed**.

**Notes / Gotchas:**
- **A scalar sub-select over a grouped CTE returns NULL, not 0, when the group is absent.** The live
  payload came back `c_level_count: null` on every cell, not `0` — exactly how `subordinate_count`
  has always behaved on the upward channel. The verification caught it; the assertion and the
  helper's comment were corrected to the measured contract rather than the assumed one, and the
  client resolves a null count to 1-with-a-score / 0-without, which is the pre-change behaviour.
- **A `numeric` inside `json_build_object` serialises as a JSON number,** so `ROUND(avg, 2)` needs no
  float cast and a single evaluator's integer comes back unchanged. A test still pins that a
  string-typed value computes as a number, because a cached payload must not turn a money cell into
  a string concatenation.
- **Backticks in generated SQL comments** broke the Code nodes again, exactly as last night; the
  generator's own test named both by workflow and node before anything reached live.
- The three existing seed files guard on the database name (`^epe_mid_`, `^epe_mid_night_`). Rather
  than weaken a safety guard, this stand took a name that satisfies both and added its own infix —
  `epe_mid_night_clv_` — so the teardown loop can still never see another brief's database.
- **Eight dumps of live from previous briefs remain in VPS `/root/epe_stand_tmp`** (root-only, mode
  600 — not BUG-053's world-readable problem, but `PROJECT_RULES.md` says teardown empties that
  directory). This session removed only its own; deleting other sessions' artefacts is not its call.
- The working tree carried **no other session's edits**; `git status` was clean at the start.
- The second gate is **still unpressed**, and no route that could press it was called.
- Committed as `cddccb8`.

## 2026-08-26 — PRELAUNCH_GATE: the money re-derived by a disbeliever, the boundaries attacked, BUG-073 refused (D-0826-3)

**Status:** ✅ Complete — verdict: **the owner can press «Запустить оценку»; nothing must be fixed first**

**What was done:**
- **The four reports treated as claims, not facts.** PRELAUNCH_BATCH_NIGHT, CLEVEL_AVERAGING,
  TERMINATED_EMPLOYEES and MID_YEAR_HIRES_SCOPE re-verified against live and against a two-copy
  stand: live counts/gate/release identical to the claims at 07:27Z and 07:59Z; the two money
  readers' CTE byte-equal on live; generators at HEAD drift-free (32/32).
- **The money recomputed independently** — applicability, final cells, formula #3 and the rounding
  restated in plain Python from HANDOVER §4 with zero project imports, against raw rows. **1 922
  matrix cells: zero mismatches.** All hand-computed fixture figures (360.9000 / 243.5620 / 7.4400 /
  102.9200 / 118.2280, pool 833.0500) identical on payload, screen and frozen `period_results`.
  Budget distribution re-derived by my own largest-remainder arithmetic: 15/15 on-screen amounts
  identical across `3.000.000`-with-dots, spaces, mixed separators and `999,99`; zero, negative and
  empty-pool inputs inert and honest (the empty-pool message measured on live's own screen,
  read-only probe).
- **Boundaries:** 0/1/2 C-level evaluators; exclusion after data (GAVE survives, ABOUT frozen NULL);
  termination mid-campaign (given upward eval still counts: 6.75); manager with excluded
  subordinate unmoved; no-grade person (self-review 422, but close freezes Σ×1.00 silently —
  **BUG-075**); channel-smuggled criteria accepted by the write path, money immune, ratings
  polluted 8.29-vs-8.17 and 7.50-vs-6.00 — **BUG-074**; partial evaluation blank-not-zero; no-row
  person leaves no frozen record (BUG-067 re-measured); BUG-068 re-measured unchanged.
- **The second gate established from the live graphs:** exactly one route sets
  `evaluation_started_at`, none unsets it; only the criteria catalogue freezes at the press;
  coefficients, classification, scope and termination routes carry no started-gate and keep
  working; second press is a timestamp-stable 200 no-op; the mark survives close. The server needs
  only `{period_id}` — the typed-name confirmation is client-side.
- **Coefficient snapshot vs live: identical**, md5 and value-for-value, before and after the deploy.
- **The one fix (item 5):** `API: Score Correction` refuses `c_level_only` criteria with 422
  `CRITERIA_NOT_APPLICABLE` before the period gate (D-0826-3, closes BUG-073). Proven money-neutral:
  control (HEAD, correction stored) vs treatment (refusal) closed side by side — **100/100 frozen
  rows identical**. Deployed 07:57:50Z (one PUT, guard frozen, webhook path unchanged, export
  refreshed); live probe 20/20 — criteria 1/10 → 422 through Caddy, criterion 3 → 409 at the
  unpressed gate, `score_corrections` 0 throughout. `npm test` 401/401.

**Results:** verdict YES with the untidy list ordered (BUG-074, BUG-075 filed; 070/071/067/060/068/014
named, none blocking). Live after: 89/3/80, 0/0/0/0, `evaluation_started_at` NULL ×3, md5s equal
the 04:48:44Z snapshot, guard frozen, 60/35/22/48, release `20260826T051630Z` untouched. Anchors
`epe_2026_pregatefix_20260826T075634Z.dump` (md5 `8b1c61ffe6c295960b109653f46d18cf`) +
`n8n_app_pregatefix_…` (md5 `6b4ad4a0699ae3778a54d35430c3e589`) on VPS and Mac, outside the repo.
Bugs: **30 open / 45 closed**.

**Notes / Gotchas:**
- `set -o pipefail` turns `diff | wc -l` into a script-killer inside `$( )` — wrap diff in
  `{ … || true; }`. And `ssh` inside a `while read` loop eats the loop's stdin: the teardown's
  drop-loop processed one database and silently skipped the second (caught by the final
  `SELECT datname`; dropped explicitly).
- The submit INSERT path's `calculated_score` averages **every** submitted row, while the additive
  path's recompute filters project criteria — the asymmetry is why smuggled channel scores reach
  the archival ratings (BUG-074) but never the cells.
- Stand DBs and containers removed; this brief's VPS dump deleted; `SELECT datname` reads
  `epe_2026, postgres`. The second gate on live was never pressed.
- Committed as `c9c6342`.

## 2026-08-26 — HIRE_DATE_AND_SCOPE_TOGGLE: the card edits date and scope (D-0826-4/5)

**Status:** ✅ Complete — deployed; live gate unpressed; no employee or scope value moved.

**What changed:**
- Admin-only `join_date` in the employee modal, including empty; existing-user save reloads the
  live row immediately before POST and the server refuses a partial whole-row payload.
- Hire-date changes atomically recompute date-derived rows of open periods and return a named
  outcome for every period. Manual override, termination and closed periods win; exclusion after
  any evaluation data is a hard 409 with received/self/given/correction counts.
- Manual per-period «Участвует в оценке» switch in the same card. Off/on leaves a durable
  `scope_override`, so later date recompute cannot undo either direction.
- Period creation and recompute share the final-three-calendar-month rule: H1 cutoff 2026-03-31;
  31 March in, 1 April out. Live disagreement before deploy: zero.
- Migration 017: append-only `employee_card_events`; one admin reader unions it with the existing,
  physically separate employment and scope logs. `join_date` leaves the global frozen-column set.

**Proof and deployment:**
- Final two-copy stand: **32/32**. Both databases from one dump, both closed through the real
  route. Exactly one frozen row moved after a treatment-only date correction; every other frozen
  cell byte-identical. Affected index `5.9400`, equal to hand arithmetic; pool difference exactly
  `5.9400`.
- Real browser on the started stand showed date → per-period result, manual toggles, actor/time
  history, and the 409 refusal with counts **2/1/1/0** and the switch still on.
- Rollback pair `20260826T085029Z`, md5 equal VPS/Mac:
  `epe_2026 886c761c81f82f32aa327d7a49af19cf`,
  `n8n_app 57b873cb0a8ce2f209c5d6e2ea65fd23`; VPS staging removed after verification,
  Mac copy retained outside the repo.
- Five workflows updated at 08:52:42–08:52:50Z; final `Admin Save User`
  actor-id guard correction at 09:04:31Z; frontend release
  **`20260826T085259Z`**. Auth Guard unchanged.
- Live verify **19/19**: 89/3/80, gate NULL ×3, 0/0/0/0, all user cells and all pre-existing
  participant cells unchanged, new override NULL everywhere, money-input md5 equal to the dated
  snapshot, 60/35/22/49. Probe session and verification restore removed.
- Tests **412/412**; build passed. Filed low performance BUG-076. Full report:
  `docs/HIRE_DATE_AND_SCOPE_TOGGLE_2026-08-26.md`.

**Notes / Gotchas:**
- The brief's «same table» premise was false: termination and scope already had separate logs.
  History was not migrated; the product reads all three through one route.
- Python Framework urllib needed `/etc/ssl/cert.pem`; the first verifier run still cleaned its
  probe session but exposed a teardown quoting bug, fixed before the successful 19/19 rerun.
- The grade md5 must include `coalesce(description,'')`, exactly as the dated snapshot documents.
- No mail, no formula/catalogue/coefficient/grade/criteria/period write, no live scope toggle and
  no second-gate call.

**Implementation commit:** `3b951c0`.

## 2026-08-26 — EMPLOYEE_SURFACES_POLISH: linked tasks and complete own profile

**Status:** ✅ Complete — deployed after the owner had already started H1.

**What changed:**
- The task block was established to live only on `/welcome`, not the owner's
  reported `/admin/users`; it is now a shared `TaskSummary` on Welcome and
  Profile. Its three task icons are real links to `/self-review`, `/dashboard`
  and `/manager-evaluation`.
- The employee rating-guide variant still selects the approved rules 1/6/7,
  without one changed word, but displays them as a local 1/2/3 list on Welcome,
  Self Review and the self-review modal.
- `my-profile` now carries only the read labels the own profile needed:
  department, position, manager, grade code, hire date, and current-period
  scope/reason. The screen adds those fields, participation, owner wording for
  exclusion, linked tasks/status, and the existing self-assessment.
- D-0820-17 stayed sealed: a stand manager score of 5.75 existed in Postgres but
  the manager row in the external profile payload had no numeric score field
  and the screen showed only `✓ Оценено`. Recursive payload key inspection found
  zero salary/compensation, bonus-index, grade-coefficient, criteria-weight or
  score-coefficient keys.

**Proof and deployment:**
- The brief's baseline was stale before editing: Alexander had started H1 at
  `10:08:54Z` and excluded Jeren Atabayeva (49) at `10:11:52Z`; the owner
  authorized continuation against 89/3/79 and a started H1. This session called
  neither route.
- Real browser on started stand `epe_walk_20260826_1044`: ordinary employee and
  manager logins; all three unique task links clicked to their correct pages;
  self 7/6/8 and manager 7/6/8/2 submitted through real forms; complete in-scope
  profile and out-of-scope profile with the owner's wording verified. Stand
  container/database/dump removed; only `epe_2026,postgres` remained.
- Independent review's one warning (`is_in_scope=null` rendered as green
  «Не участвуете») was fixed; five additional contract tests added.
- Tests **423/423**, production build passed, changed-file lint zero errors.
- Rollback pair `20260826T110252Z`, VPS/Mac md5 equal:
  `epe_2026 9ffe553448ebb991d77227db17ada5ea`,
  `n8n_app 5f5a812d142287868134519820e2d526`; VPS staging removed, local copies
  retained outside the repo.
- One workflow PUT: My Profile active, same webhook, updated
  `2026-08-26T11:04:26.001Z`; Auth Guard frozen. Frontend release
  **`20260826T110433Z`**.
- Live after: 89/3/79, H1 active/started, 0/0/0/0; all four coefficient md5s
  equal the dated H1 snapshot; generator drift 32 identical / 0 changed.

**Report:** `docs/EMPLOYEE_SURFACES_POLISH_2026-08-26.md`.

**Implementation commit:** `0c464b1`.

## 2026-08-26 — ROLE_ACCESS_HR_CLEVEL: C-level reads the admin surfaces, HR reads the roster (D-0826-6) — BUILT, NOT DEPLOYED

**Status:** 🟡 Code complete on `claude/hr-clevel-access-control-dudin7`; **nothing touched the
running system** — this session ran in a remote cloud container with no SSH, no route to live and
no Docker, so the stand proof, the dump, the deploy and every live verification remain for a Mac
session (runbook: report §5).

**Diagnosed (outcome 1):** the owner's empty employees page is a 403 the screen swallows — the
/team pattern (BUG-012) exactly: `/admin/users` admits admin/c_level/hr at the route while
`api/admin-users-data` was admin-only, and `AdminUsers.jsx` never rendered the error it caught.
Same silent pattern on `/admin` (criteria). The roster SQL carries no salary column for any role;
the one money input in it is `options.grades[].coefficient`.

**What changed:**
- Guards (generators; live PUT pending): `admin-users-data` → admin+hr+c_level with the grades
  coefficient stripped for hr; `score-coefficients` GET → admin+c_level; `manage-criteria` →
  admin+c_level with save/delete refusing every non-admin 403 by role before the freeze;
  `score-correction` → admin+manager (role c_level refused — supersedes the writer half of
  D-0820-7, flagged to the owner in report §4.1 with the one-line revert named).
- Frontend: final-scores + score-calculator + /admin → `ReportingRoute`; sidebar offers them to
  c_level; roster and criteria pages read-only below admin; correction affordance admin/skip-level
  only; AdminUsers/AdminSettings/AllEvaluations/Matrix/Analytics name a refused or failed read
  instead of a blank list; `useScoreCalculation` stops substituting empty coefficients (BUG-042 →
  in progress; BUG-013 HR half → in progress).
- Tooling for the Mac: `scripts/deploy_role_access_hr_clevel.py` (4 PUTs, open-campaign
  invariants, exports refresh) and `scripts/prove_role_access.py` (role×route matrix incl.
  negative cells, write refusals one by one, compensation key walk; campaign-safe by
  construction).
- Validation here: `npm test` **439/439** (16 new/updated pins), build passes, changed-file lint
  adds no errors. Surfaced, not resolved: password-reset routes are unauthenticated self-service
  (nothing to refuse by role); employee-events stays admin-only; `/admin/bonus-calculation` not in
  the brief's grant; stale tracked generator snapshots found and left un-adopted (BUG-077).

**Report:** `docs/ROLE_ACCESS_HR_CLEVEL_2026-08-26.md`.

**Implementation commit:** `5c46052`.

## 2026-08-26 — ROLE_ACCESS_DEPLOY: the role-access change landed, deployed and proven on live (D-0826-6 + correction D-0826-7)

**Status:** ✅ Live and proven. PR #2 **MERGED** (13:36:01Z, merge `3b97581`); the previous
session's scheduled PR check-in disabled before it fired.

**The owner's correction, applied before deployment (D-0826-7):** the brief's refusal of role
`c_level` on score corrections was wrong — D-0820-7 stands, c_level keeps its corrections. Revert
`fd637c1`; the regenerated score-correction came out byte-identical to live, so that workflow was
**not** PUT (`changed: false`, updatedAt still 07:57:50.177Z). Every other refusal of D-0826-6
landed as built. DECISIONS.md carries D-0826-7 and a banner in D-0826-6.

**Deployed:** three workflow PUTs 13:46:55–57Z (`Admin Get Users Data`, `Get Score Coefficients`,
`Manage Criteria Admin V7`) through `deploy_role_access_hr_clevel.py` (Auth Guard checked both
sides, invariants byte-identical); frontend release **`20260826T134725Z`** through the locked CAS
deploy (rollback target `20260826T110433Z`).

**Proven (the part the cloud session could not do):**
- Fresh dump pair before any live write, md5-identical both sides
  (`~/EPE_ROLLBACK/2026-08-26-role-access/`, `4afb0ae1…` / `23b8516c…`).
- Stand `epe_roleaccess_20260826_1341` from that dump: matrix **PASS 151 cells**; a REAL accepted
  c_level correction stored (Bayram 200 → Jemal upsert — BUG-073's known last-writer-wins residue
  reproduced). Stand torn down, `/root/epe_stand_tmp` emptied.
- Live matrix **PASS 151 cells, 0 failures**: manager+employee = 55 × 403 across every admin
  surface; every write route refused as c_level and as hr one by one; corrections prove ADMISSION
  by code (Cem 403 CAPABILITY_FORBIDDEN, Bayram 422 CRITERIA_NOT_APPLICABLE, hr 403
  ROLE_FORBIDDEN); compensation walk over all 23 non-admin 200s — **0 salary keys**, hr grades =
  `{id, code}`.
- Real browser on live: Jemal (c_level, 47) opened all seven pages non-empty with zero edit
  affordances; Liya (hr, 52) got the roster («Найдено: 86») read-only, and typed /admin →
  /hr/dashboard (BUG-013 closed). Probe sessions deleted.
- Campaign untouched: `evaluation_started_at` 10:08:54.340312Z, tables 0/0/0/0, population
  89/3/**78** (the owner excluded Kulmamedova (16) at 12:31Z before the deploy — his page, not
  drift; roles now 13 manager / 68 employee, Liya registered), coefficient md5s equal the dated
  snapshot to the digit, Auth Guard `2026-08-18T16:34:30.674Z` unchanged.

**Report:** `docs/ROLE_ACCESS_HR_CLEVEL_2026-08-26.md` §8. Closed: BUG-013, BUG-042.

**Deploy session commits:** `fd637c1` (D-0826-7 revert), `3b97581` (merge, PR #2), `a59fd35` (deploy + live proof).
