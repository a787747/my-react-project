# Bug Tracker

## Statistics
| Status | Count |
|--------|-------|
| 🔴 Open | 30 |
| 🟡 In Progress | 0 |
| 🟢 Closed | 47 |

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

### BUG-032: The daily backup dumps the 2025 archive, not the live campaign database
- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: host `92.51.45.147`, `crontab`: `0 3 * * * /root/backups/epe/backup-performance-db.sh`; the script runs `docker exec postgres_n8n pg_dump -U admin -d postgres -n performance_db …`.
- Description: `-d postgres` is the **2025 archive** database. The live campaign database is `epe_2026` (same schema name `performance_db`, different database), and **no cron job, systemd timer or script anywhere on the host dumps it**. Verified 2026-08-21: the only backup job is the one above; `grep -rl 'epe_2026' /etc/cron* /etc/systemd/system` returns nothing; and the 2026-08-21 dump's table list contains `invite_tokens` and `score_corrections` but **not** `period_results`, `auth_sessions` or `evaluation_period_participants` — three tables that exist only in `epe_2026`. The job itself is healthy: 10 dumps, 14-day prune, clean log, ~34 KB each.
- Why it matters: `epe_2026` holds the users, the password hashes, the H1 participant scope, and — from the first submission — every evaluation of the campaign. Closing a period is irreversible by design: there is no reopen route and no route that writes or deletes `period_results`, so **the documented recovery from a mistaken or premature close is "a database restore"** — of a database that has no restore point. Today the loss would be 89 user rows and two registrations; after H1 opens it is the campaign.
- How to fix: add `epe_2026` to the same script (a second `pg_dump -d epe_2026`, its own filename stem, the same size check and prune), then verify by restoring one dump into a throwaway DB — the project's established evidence standard. Do it before H1 is activated. Pairs with [BUG-014] (still no off-host copy).
- H1 impact: no wrong number today. It is the blast radius of every other risk in the campaign.
- Found: 2026-08-21 docs hygiene, `docs/DOCS_HYGIENE_2026-08-21.md`. Not named in any brief report — `docs/HANDOVER.md` said only "Backups: daily on-host, 14 days, restore-verified", which was true of the archive and read as true of live.
- Also found while fixing: the same archive job dumps `-n performance_db` only, so the **n8n application schema** `postgres.public` — 58 workflows, 7 credentials, 8 settings, 41 webhook registrations — was covered by nothing either. No cron line, no systemd timer, and `docker inspect n8n-n8n-1` shows **zero mounts**, so it existed in exactly one place. Losing it meant rebuilding 58 workflows and every credential by hand.
- Fix (2026-08-21): new host job `/root/backups/epe/backup-epe-live.sh`, cron `20 3 * * *` (00:20 UTC, twenty minutes after the archive job so they never contend). It dumps `epe_2026` in full and `postgres -n public` separately — `-n public` rather than the whole database because the archive job already owns `-n performance_db`, so the two jobs cover every schema of both databases with no overlap. Same 14-day window, `-Fc | gzip -9`, `chmod 600`, size check and shared `backup.log` as the archive job. Pruning is stem-scoped, so neither job can delete the other's files. `backup-performance-db.sh` is byte-identical before and after — md5 `a9f748541cad6379d8949ce91dab51e0` — and its 10 dumps were still 10 after the new job ran. Tracked copies: `scripts/backup-epe-live.sh`, `scripts/verify-restore.sh`.
- Verification (2026-08-21): the entry point was fired **by cron**, not by hand — `/var/log/syslog` `CRON[542920]: (root) CMD (/root/backups/epe/backup-epe-live.sh)` at 11:45:01 UTC — and both restore proofs used the files that run produced. `epe_2026` dump restored into throwaway `epe_bkverify_epe_2026_20260821_114620`: `pg_restore --exit-on-error` exit 0, **17 tables, 0 mismatches** against live (users 89, participants 178, coefficients 80, evaluations/scores/`period_results` 0). n8n dump restored into `epe_bkverify_n8n_app_20260821_114608`: exit 0, **52 tables, 0 mismatches** (`workflow_entity` 58, `webhook_entity` 41, `credentials_entity` 7, `settings` 8). Both throwaways dropped; `pg_database` back to `epe_2026` + `postgres`. Retention proven with two 20-day-old decoy files: the cron run logged `pruned=1 retained=1` per stem and no decoy survived — note the archive job's own prune has never fired (every line reads `pruned=0`; its oldest dump is 9 days old). Failure path proven by running the real script against a nonexistent container: exit 1, `FAIL` line in `backup.log` carrying `pg_dump`'s own stderr, `FAIL` in the status file, partial dump removed. Disk: 34 GB free of 50 GB (33 % used); the new dumps add 387 400 B/day, ≈5.3 MB per 14-day window.
- Not covered by this fix, deliberately: no off-host copy ([BUG-014], still open — Alexander has not named a target), no alerting push (the status file is a pull check; there is no MTA on the host), no point-in-time recovery (daily logical dumps, worst case ~24 h of campaign writes), and `N8N_ENCRYPTION_KEY` is a Portainer env var in no dump — the 7 credential rows restore but are unreadable under a different key.
- Report: `docs/BACKUP_FIX_2026-08-2x.md`.

---

### BUG-041: `update-evaluation` deletes score rows even when its own ownership/period re-assertion rejects the write

- Status: 🟢 CLOSED
- Severity: ⚠️ High (silent, permanent, on the money-bearing table — but needs a narrow race window, and no data was ever at risk)
- Location: LIVE `API: Update Evaluation WITH PERIOD` (`LWuZNTehzMDJkE8u`, `updatedAt=2026-08-22T06:38:03.201Z`) → node `Build Update SQL`, the `removed_scores` CTE.
- Description: the statement re-asserts evaluator ownership and "period is not closed" **inline** in `updated_header`'s `WHERE` — the node's own comment says this exists "to close the validation/mutation race between the prior SELECT check and this DML". `upserted_scores` inherits that gate because it selects `FROM updated_header`. `removed_scores` does not: it is `DELETE FROM performance_db.evaluation_scores WHERE evaluation_id = ${evalId} AND criteria_id NOT IN (SELECT crit_id FROM score_rows)`, referencing neither `updated_header` nor anything else conditional, and the outer `SELECT` never reads it. PostgreSQL executes data-modifying `WITH` clauses "exactly once, and always to completion, independently of whether the primary query reads all (or indeed any) of their output". So when the re-assertion selects zero rows, the header `UPDATE` and the score `INSERT` write nothing, `Format POST Response` correctly returns 403 — **and the DELETE has already run.**
- Why it matters: the caller is told the write was refused while score rows were permanently removed. The rows are the per-criterion detail behind `calculated_score`, the matrix and the frozen `period_results.bonus_index`; there is no soft-delete, no history table and no audit row, so the loss is silent and unrecoverable short of a database restore. It also defeats precisely the protection the inline re-assertion was added to provide, on the one branch where failure is destructive rather than merely a no-op.
- Repro (not run — the recon brief that found this is read-only, and running it requires a write): as an evaluator, open an existing evaluation and save a **narrower** set of criteria; have an admin close the period, or change the evaluation's `evaluator_id`, in the window between `Execute Ownership Check` and `Execute Update`. Response is 403 `Изменение недоступно…`; the criteria omitted from the payload are gone from `evaluation_scores`. Not reachable without the race: `Validate Update` → `Execute Ownership Check` returns 404/403 before the SQL is built, so an unauthorized caller never reaches it.
- How to fix: gate the DELETE on the same CTE the other two branches use — `DELETE … WHERE evaluation_id IN (SELECT id FROM updated_header) AND criteria_id NOT IN (SELECT crit_id FROM score_rows)`. That makes all three branches share one gate, and a failed re-assertion changes zero rows everywhere. Worth deciding at the same time whether a narrower submitted set should delete at all — see the reclassification recon, which found the same DELETE is the only mechanism that can remove criteria after a classification switch, and is destructive by construction.
- H1 impact: none today — `evaluation_scores` has 0 rows and no period is active (measured 2026-08-22). Fix before H1 is activated; the exposure begins with the first evaluation and peaks during September calibration, when closing a period and editing evaluations happen in the same window.
- Fix (2026-08-22): `removed_scores` now carries `AND EXISTS (SELECT 1 FROM updated_header)`, so all three CTE branches share one gate and a failed re-assertion changes zero rows everywhere. Closed inside the lifecycle brief rather than filed for later because that brief rewrites the same `WHERE` clause: the inline re-assertion became "period is active AND started" instead of "period is not closed", which would otherwise have **widened** the destructive race by one more trigger. Fixing it was the alternative to knowingly making it worse (D-0820-21 — defects found on the way are fixed immediately).
- Verification: `tests/routeGuardWorkflows.test.js` asserts both the widened inline re-assertion (`p.status = 'active'`, `p.is_active = true`, `p.evaluation_started_at IS NOT NULL`) and the `AND EXISTS (SELECT 1 FROM updated_header)` gate. The race itself was **not** reproduced at that point — this was a code-level close, not a runtime one.
- **Runtime repro (2026-08-24, throwaway stand `epe_reclass_20260824_0602`; compared values in `backups/2026-08-24-reclass/reclass_proof.json` → `bug041`).** The exact race the RECON described — "the period was closed in the window between Execute Ownership Check and Execute Update" — executed deterministically at statement level against a closed period, where the header re-assertion matches zero rows:

  | run | statement source | header rows returned | score rows before | score rows after |
  |---|---|---|---|---|
  | pre-fix | RECON §7.2 verbatim (old `!= 'closed'` re-assertion, ungated DELETE) | 0 (the 403 path) | `{3, 4, 12}` | **`{3}` — rows 4 and 12 destroyed** |
  | post-fix | byte-sourced from the deployed `Build Update SQL` template | 0 (the 403 path) | `{3, 4, 12}` (restored) | **`{3, 4, 12}` — zero rows deleted** |

  The HTTP route itself was also exercised post-close: `POST api/update-evaluation` → 403 `PERIOD_CLOSED` with the row set unchanged. The DELETE still works when the header matches (the in-campaign narrowing edit deleted actively-removed rows on the same stand), so the gate refuses the race without deadening the branch.
- Residual: whether a narrower submitted set should delete score rows **at all** was answered by D-0822-3 on 2026-08-24: deletion is reserved for criteria the evaluator **actively removed from the currently-applicable set**; rows excluded by the current classification survive an ordinary edit (proven on the same stand — a general subject's project-criteria rows survived a 200 edit). See `docs/RECLASS_2026-08-2x.md`.
- Source: `docs/RECON_RECLASS_COEFF_2026-08-2x.md` §7.2 and §8, from the live workflow definition. Closed in `docs/LIFECYCLE_COEFF_2026-08-2x.md`; runtime-proven in `docs/RECLASS_2026-08-2x.md`.

---

### BUG-051: Admin evaluations-matrix rows skip non-applicable project cells, misaligning every later column against the header

- Status: 🟢 CLOSED
- Severity: ⚠️ High
- Location: `src/components/admin/EvaluationsMatrixTable.jsx` — header derives its criterion columns from `employees[0].criteria`, each body row maps its OWN `groupCriteria(emp.criteria)`.
- Description: the header renders all catalogue criteria as columns (walkthrough stand: name + 9 criterion columns, order 3,4,12,14,8,13,2,1,10, no colspans). A body row for a subject without project criteria emits `<td>`s only for its own criteria — 8 cells instead of 10 — so every cell after the general group shifts two columns left: the «Как руководитель» N/A renders under the «Взаимодействие и надежность в проекте» header, and any C-level scores land under «Объем проектной работы…» / «Качество управления…». Rows for project subjects (10 cells) align; general rows do not. DOM evidence in `docs/BROWSER_WALKTHROUGH_2026-08-2x.md` §I (browser walkthrough, 2026-08-24): header row 2 = 10 `th`; WT Employee G row = 8 `td`, WT Employee N/P rows = 10 `td`.
- Why it matters: most of the company is non-project, so most rows of the admin matrix are misaligned. A C-level score for a general employee displays in a project column; an admin reading the matrix (or comparing against the final-scores screen, which uses a shared column list and is NOT affected) attributes numbers to the wrong criteria. This is the screen calibration decisions are read from.
- Fix (2026-08-24, prelaunch fix batch): one shared column list for header AND rows. `buildSharedCriteriaGroups(employees)` (new, `src/utils/matrixUtils.js`) unions every row's criteria in first-seen order — employees[0] alone was also a broken header source (a general first row would have dropped the project columns entirely). Every body row maps the HEADER's group lists, looks its own cell up by `criteria_id`, and renders a placeholder in its own column when the criterion is absent: N/A in project/management columns, «—» elsewhere. Header criterion objects (another row's data) never render as data cells. Presentation only — no formula, weight or payload touched.
- Verification (2026-08-24, throwaway stand `epe_walk_20260824_1432`, real Chromium, walkthrough-shaped data): all **97 rows emit exactly 10 `td`** under the 10-`th` header (histogram `{10: 97}`; the walkthrough recorded 8 for the general row). Per-column DOM map: general subject G shows `N/A` under both «Проектные» headers, `N/A` under «Как руководитель», C-level cells under C-level; project subject P shows 8 and 7 under their own project headers; a c_level correction on P×crit8 renders **8.5 amber at column index 5** («Взаимодействие и надежность в проекте») while G's same column shows N/A. Money unchanged: with the walkthrough's coefficient set the fixed build reproduces the recorded figures **to the digit** (G Σ 70.20 × 0.60 = 42.12; P Σ 121.30 × 2.20 = 266.86 — final-scores screen, same per-criterion contributions), and under live's current coefficients the screen matches independent arithmetic exactly (см. report §2 — criterion-14 weight moved 1.5→2.0 on live between the walkthrough and this batch, admin-side edit, fully accounted). Tests: `tests/matrixUtils.test.js` (+3), `tests/evaluationsMatrixAlignment.test.js` (new, 4 source pins); suite 284/284. Deployed to live release `20260824T145133Z`; live chunks byte-identical (md5) to the fixed build; drift 30/0 before and after.
- Source: browser walkthrough 2026-08-24 (`docs/BROWSER_WALKTHROUGH_2026-08-2x.md`); closed by `docs/PRELAUNCH_FIX_BATCH_2026-08-2x.md`.

### BUG-056: The deploy script neither refuses a dirty tree nor stamps a commit into the release

- Status: 🔴 OPEN
- Severity: ⚠️ High
- Location: `scripts/deploy_epe_frontend.sh:7` (`RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"`) and lines 25–34 — the whole upload/symlink path.
- Description: a release directory carries a UTC timestamp and nothing else. There is no `git rev-parse` in the script, no version file in `dist/`, and no check that the working tree is clean before `npm run build`. A deploy from a dirty tree is therefore indistinguishable, on the server, from a deploy of a committed state.
- Why it matters: it already happened. On 2026-08-25 the live release `20260825T115748Z` was built from seven uncommitted files; `/var/www/epe/current` pointed at a bundle that existed in no commit and no branch, and the only way to establish what was serving was to rebuild candidate commits and compare CSS-bundle md5s. That is the same exposure class as the 2026-08-22 parallel-session incident. The specific tree was brought under version control as `d1b2d18`, but the script that permits the situation is unchanged. It also blocks rollback-by-checkout: with no commit id in the release, "put back what was serving yesterday" has no mechanical answer.
- How to fix: two lines in the script — refuse when `git status --porcelain` is non-empty (with an explicit `EPE_DEPLOY_ALLOW_DIRTY=1` escape hatch for a deliberate hotfix), and write `git rev-parse HEAD` plus the dirty flag into `dist/RELEASE.txt` before the tar, so every release directory names its own commit. Note that `20260825T065554Z` → `6ca603e` had to be established by rebuild instead.
- Rider found while investigating: rolldown-vite 7.2.5 output is **path-dependent** — rebuilding provably identical source in a different directory reproduced only 4 of 57 asset files and never the JS entry hash. Only the CSS bundle is a stable cross-machine fingerprint. Any future "does this bundle match that commit" check must use the CSS, not the JS.
- Source: `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md` §4.2–§4.3.

## 📌 Medium

### BUG-009: Employee profile and history still have no period filter
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `n8n_workflows/route_guard_h1/my-profile.json`, `evaluation-history.json`.
- Description: Both JOIN `evaluation_periods` for the name only. They do not restrict rows to the active period. `check-self-review`, `check-evaluated`, and `get-my-manager` already bind to `is_active AND status='active'` — `docs/REPORTING_SURFACE_2026-08-2x.md` listed those three as still unbound; that is false in the live generator JSON.
- Why it matters: harmless while `epe_2026` has one campaign period. After H2 exists, profile/history will mix cycles.
- Fix: bind both queries the same way check-* already do. Schedule with persist-period-results after launch.

### BUG-012: `/team` calls an admin-only API
- Status: 🟢 CLOSED (2026-08-25)
- Severity: 📌 Medium
- Location: `src/pages/TeamView.jsx` → `useUsers` → `GET /api/admin-users-data`; route is `ManagerRoute`.
- Description: The page is shown to managers. The API guard is admin-only. Managers get an empty/error list. Pre-existing; reporting-surface brief hid dossier buttons but did not change the list endpoint.
- Why it matters: the “Список команды” item in the sidebar does not work for a manager.
- Fix: either point the list at a manager-scoped employees read, or hide `/team` from managers until that exists.
- H1 impact: managers use `/dashboard` for campaign tasks. `/team` is the leftover.

- Fix (2026-08-25, D-0825-9): `/team` reads `GET /api/employees` through the new `src/hooks/useTeamRoster.js`. The route is actor-scoped and identity-bound — `WHERE users.manager_id = actorId`, joined to `evaluation_period_participants … is_in_scope = true` — so the server decides who the manager may see and a terminated subordinate never arrives. `TeamView` no longer imports `useUsers` and no longer walks the org tree.
- Verification: on a throwaway stand restored from live with the campaign started, Yelena Son (manager, 13 direct reports of whom 2 terminated) logged in through the real form and saw exactly **11** subordinates, both terminated people absent by name and by e-mail, then submitted an evaluation that appeared as «Оценено мной: 1». Console for the whole pass: one pre-login 401 and nothing else. `docs/TEAM_PAGE_AND_DEPLOY_LOCK_2026-08-25.md` §3.
- Behaviour change: `/team` is now direct reports only, not the recursive subtree, and it is empty for everybody until «Запустить оценку» is pressed — with a notice that says so. See BUG-065.
### BUG-016: npm production/dev advisories
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `npm audit` 2026-08-20.
- Description: 15 advisories (11 high, 3 moderate, 1 low). Production-only (`--omit=dev`): 5 (4 high, 1 moderate).
- Why it matters: known high-severity frontend dependencies. Not a campaign blocker.
- Fix: after H1 launch, upgrade in a dedicated pass and rebuild.

---

### BUG-033: After a period closes, no screen can spend the frozen bonus index
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `src/hooks/useFinalScoresMatrix.js:149` (requests the matrix with no `period_id`); `src/pages/BonusCalculation.jsx`; `src/pages/AdminAnnualRollup.jsx`.
- Description: the money screens ask `API: evaluations-matrix` without `period_id`, so the server falls back to `WHERE is_active = true AND status = 'active'`. The moment H1 closes there is no active period: the API returns `no_period → data: []` and Итоговые баллы, Калькуляция бонусов **and** the evaluations matrix all render empty. The frozen `bonus_index` then exists only on Годовые итоги, which has no budget field, no point-value field, no payout column and no grade-A exclusion filter — all of which live on `BonusCalculation.jsx`.
- Why it matters: the bonus is paid **after** the period closes. The screen that computes payouts goes blank at exactly the moment it is needed, and the number that was carefully frozen cannot be spent from it.
- Fix: add a period selector (the server already accepts `?period_id=` and `useEvaluationsMatrix(periodId)` already takes the argument — nobody passes it), or read `period_results` on the money screens.
- H1 impact: none in August. Needed in September.
- Source: M3 of `docs/PERIODS_VERIFY_2026-08-2x.md`; still listed open in `docs/POSTVERIFY_BATCH_2026-08-2x.md`.

### BUG-034: Admin → Сотрудники evaluation circles never load (`setLoadingStatuses` has no state)
- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `src/pages/AdminUsers.jsx` (the undeclared `setLoadingStatuses` effect is gone).
- Description: the status-loading effect throws `ReferenceError` on its first line inside the `try`, is swallowed by the `catch`, and then throws again in the `finally` — an unhandled rejection. `selfReviewsStatus` and `evaluationStatuses` are never populated, so the evaluation-status circles stay empty for every row.
- Why it matters: the classification pass Alexander runs on this screen still works (the circles are not classification), but the screen silently reports that nobody has done anything, and the console carries an unhandled rejection on every list load.
- Fix (2026-08-24): **circles removed**, not loaded. No admin-allowed route returns the subject-centric metrics the column claimed (self score, received-from-manager, received-from-subordinates). `GET /api/check-self-review` is single-subject; `GET /api/hr/evaluation-status` is allowed for admin/c_level/hr but answers evaluator-task flags under different field names, keyed on an active period (empty while H1 is draft), and strips scores. `API: Get Employee Self Review` is deleted. The broken effect and the status column on AdminUsers are gone (`showEvaluationStatus={false}`); no unhandled rejection.
- Remaining: `src/pages/TeamView.jsx` still calls undeclared `setLoadingSelfReviews` (same class, `/team`, BUG-012 territory) — surfaced, not fixed.
- Source: §6 of `docs/ADMIN_USERS_SORT_2026-08-2x.md`; closed in `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md`.
- Closed: 2026-08-24

### BUG-036: Copy that contradicts behaviour, including a button that can only 409
- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `src/components/self-review/SelfReviewStatusCard.jsx`, `src/pages/Welcome.jsx`, `src/components/SessionExpiryWarning.jsx`, `src/pages/Login.jsx`, `src/pages/ManagerEvaluation.jsx`.
- Description: rows 2, 3, 7, 8, 9 and 10 of the §4.8 copy-vs-behaviour table are still open after the 20 Aug fixes closed rows 1 and 5. The functional one is row 7: «Оценить новые критерии» is rendered, is clickable, and **always** returns 409. The rest are false or incomplete statements — «Все данные видят только C-level менеджеры» (admin, HR statuses and `/team-scores` also see data); «Критерий для оценки руководителя» used as if it were the criterion's name (it is `Качество управления и развитие команды`); «Руководитель не назначен» shown to C-level who correctly have none; the draft notice not saying the draft is browser-local and expires in 7 days; the login placeholder `name@company.com` when registration requires `@sedamedical.com`.
- Why it matters: a button that cannot succeed trains people to distrust the product on their first real task, and a confidentiality promise that is broader than the implementation is the kind of statement an employee will test.
- Fix (2026-08-24, owner decision): button **removed** (no `is_update`, no workflow change). Rows 3, 8, 9, 10: criterion title, C-level no-manager notice, draft 7-day, login `@sedamedical.com` — closed in `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md`. Row 2 (visibility sentence) was rewritten in that batch, then **restored** to the owner's wording and closed by **D-0824-3** (2026-08-24): live definitions + local tests show the evaluated manager gets 404 on `GET /api/evaluation-details`; `GET /api/my-profile` attaches score fields only to self rows and nulls evaluator identity on `evaluation_source='subordinate'`; no comment columns on that route; `GET /api/evaluation-history` is given-only (`evaluator_id = actor`); HR status is flags only; manager-subordinates-matrix has no upward cell; evaluations-matrix and details-by-user are `admin`/`c_level`. See `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md`.
- Remaining: none. `CriteriaOverview.jsx` leftover fake title closed in the same notice brief (live title of criterion 2).
- Source: §4.8 of `docs/USER_FACING_COPY_2026-08-2x.md`; closed in `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md`; row 2 sealed by D-0824-3 in `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md`.
- Closed: 2026-08-24

---

### BUG-029: Criterion weight of 0 silently behaves as 1.0 in the bonus index
- Status: 🟢 CLOSED
- Severity: 🟢 Low–Medium (latent hardening gap — no wrong number ever reached live; no zero weight or zero grade coefficient has ever existed on live)
- Location: LIVE `API: Manage Periods` → `Compute Close Results` (`const weight = Number(crit.weight) || 1.0;`); LIVE `API: Get Score Coefficients` → `Format Response` (`weight: parseFloat(row.weight) || 1.0`); `src/hooks/useFinalScoresMatrix.js:84`.
- Description: `|| 1.0` treats 0 as absent. Setting a criterion's weight to 0 — the natural way an admin would express "this criterion should not count toward the bonus" — makes it count with weight 1.0 instead. The same applies to a grade coefficient of 0. A score *coefficient* of 0 is handled correctly (it zeroes the term); only weight and grade coefficient are trapped.
- Why it matters: the bonus index is the money-allocation number. An admin who zeroes a weight to remove a criterion from the pool gets the opposite of what they asked for, silently, with no validation error. Because the index has no denominator (HANDOVER §4), the mistake inflates that person's share of the pool rather than merely mis-scaling it. Since 2026-08-21 the wrong number is also *frozen* into `period_results` at close and cannot be recomputed.
- Repro: set `criteria.weight = 0` for any active criterion, open Итоговые баллы / Калькуляция бонусов — the criterion contributes `score × coefficient × 1.0`. Close the period — the same value is persisted.
- How to fix: use `Number.isFinite(w) && w >= 0 ? w : 1.0` on both sides (the close compute node and the coefficients API), so an explicit 0 means 0 and only NULL/garbage defaults to 1.0. Add a `CHECK (weight > 0)` or an explicit UI affordance for "exclude this criterion" if 0 must stay illegal. The two sides must change together or the server/client parity breaks.
- H1 impact: none today (no zero weights on live; re-measured 2026-08-21: zero criteria with `weight IS NULL OR weight <= 0`, zero `score_coefficients` rows with `coefficient IS NULL OR coefficient <= 0`). Fix before anyone edits the criteria catalogue.
- Fix (2026-08-22, D-0822-2): **the illegal value can no longer be written.** Both write paths validate before building any SQL and answer 422 with a named error. `POST /api/score-coefficients` → `INVALID_WEIGHT` for a weight that is not finite and `> 0`, `INVALID_COEFFICIENT` for a level coefficient on the same rule, `INVALID_COEFFICIENT_LEVEL` for a level outside 1..10, `INVALID_COEFFICIENT_MAP` for a missing map. `POST /update-admin-data` → `INVALID_GRADE_COEFFICIENT` on the same rule, plus `INVALID_SETTING_KEY` / `INVALID_SETTING_VALUE` on the settings branch, which until now interpolated `setting_value` straight into SQL with no validation at all. The rule is **> 0**, not a numeric floor: any positive weight is a legitimate business value and only 0 is the misread one. The `INVALID_WEIGHT` message names the right remedy — disable the criterion (`is_active`), do not zero its weight.
- Verification (2026-08-22, throwaway stand `epe_lifecycle_20260822_0632`; compared values in `backups/2026-08-22-lifecycle-coeff/lifecycle_proof.json` → `bug_029`):

  | write | request | response | stored before | stored after |
  |---|---|---|---|---|
  | `POST /api/score-coefficients` | criterion 12, `weight: 0` | 422 `INVALID_WEIGHT` | `weight = 1.00` | `weight = 1.00` |
  | `POST /api/score-coefficients` | criterion 12, all ten level coefficients `0` | 422 `INVALID_COEFFICIENT` | level 5 `= 1.00` | level 5 `= 1.00` |
  | `POST /update-admin-data` | grade `S1`, `coefficient: 0` | 422 `INVALID_GRADE_COEFFICIENT` | `0.60` | `0.60` |
  | `POST /api/score-coefficients` | criterion 12, `weight: -1` | 422 `INVALID_WEIGHT` | — | — |
  | `POST /api/score-coefficients` | criterion 12, level `11` supplied | 422 `INVALID_COEFFICIENT_LEVEL` | — | — |

  Static assertions: `tests/routeGuardWorkflows.test.js` (`weight <= 0`, `coef <= 0`, `Number.isFinite`, `INVALID_COEFFICIENT_LEVEL`, and that no undecided numeric floor is present) and `tests/routeGuardDeferred.test.js` (`INVALID_GRADE_COEFFICIENT`, `coefficient <= 0`, both settings errors). Live: `API: Save Score Coefficients` `updatedAt=2026-08-22T06:49:44.483Z`, `API: Update Admin Data` `updatedAt=2026-08-22T06:38:09.942Z`.
- Residual: the **read-side** `|| 1.0` defaults named in the Location line still exist — `Compute Close Results`, `API: Get Score Coefficients` → `Format Response`, `useFinalScoresMatrix.js`. They are now unreachable through the API, because the only value they mis-read (an explicit 0) can no longer be stored. Direct SQL on the host still can. A `CHECK (weight > 0)` / `CHECK (coefficient > 0)` would close that last door and was deliberately not added here: it is a schema change beyond the brief, and its stakes dropped once closed periods stopped re-joining these tables (`period_results`).

### BUG-046: Manager-subordinates matrix ignores the classification applicability filter

- Status: 🟢 CLOSED
- Severity: 📌 Medium (a read surface that contradicts the admin matrix, the frozen close numbers and the reopened-task flag after any classification switch — but produces no money number)
- Location: LIVE `API: Manager Subordinates Matrix` (`EyvFZJGDxQNL20tC`) → `Build Matrix Query`, generated by `scripts/build_route_guard_deferred.py`. Row source: `CROSS JOIN performance_db.criteria c WHERE c.is_active = true AND c.c_level_only = false` — no `(c.target_audience <> 'project_participants' OR u.is_project_participant = true)` clause.
- Description: D-0822-3 put the applicability clause into `Build Matrix Query` (admin matrix) and `Build Close Dataset Query`, so soft-excluded criteria stop being emitted there. The third per-cell matrix surface was not touched: `GET /api/manager-subordinates-matrix` still emits cells for criteria 8/13 — with their scores **and their correction sub-selects** — for a subject who is currently general. `ManagerSubordinatesMatrix.jsx` then computes cell finals (R13) over those cells, so a middle manager sees a rating that includes exactly the rows every other surface now excludes.
- Why it matters: after a project→general switch the same person shows different criteria sets and different means on the admin matrix vs the middle-manager matrix, and the middle manager still sees «project» scores that no longer count anywhere — the exact confusion soft exclusion was built to prevent. No bonus impact: the index is computed only from `evaluations-matrix` (client) and at close (server), both filtered.
- How to fix: the same one clause in the row-source WHERE of this query's `CROSS JOIN`, as in the admin matrix (one line in `build_route_guard_deferred.py`, plus its static test).
- H1 impact: none while the data tables are empty; becomes visible with the first mid-campaign reclassification of anyone in a manager-of-managers span.
- Source: verification gate `docs/GATE_RECLASS_2026-08-2x.md` §8 (adversarial sweep of every corrections-reading surface in the generated corpus). The build's proofs could not see it: the stand exercised the admin matrix and close only.
- Fix (2026-08-24): exactly the named one clause — `AND (c.target_audience <> 'project_participants' OR u.is_project_participant = true)` in the `CROSS JOIN` row source of `MANAGER_MATRIX_INNER_SQL` (`scripts/build_route_guard_deferred.py`), same text and same position as the admin matrix and the close dataset. Static test added (`tests/routeGuardDeferred.test.js`, incl. the row-source-not-sub-select regex). Deployed to live `EyvFZJGDxQNL20tC` (`updatedAt=2026-08-24T08:33:51.330Z`, node-identical to the generator, activation preserved, Auth Guard untouched).
- Verification (2026-08-24, throwaway stand `epe_final_20260824_0828`; compared values in `backups/2026-08-24-finalize/finalize_proof.json` → `bug046`): middle manager 1310 over span {1303, 1304, 1308, 1309}; project subject 1304 evaluated on the full set with a `c_level` correction on criterion 8 and a `mid_level` correction on criterion 13. Emitted cells for 1304: **[2, 3, 4, 8, 12, 13, 14] → project→general switch → [2, 3, 4, 12, 14]** (cells 8/13 gone, no emitted cell carries either correction; the admin matrix emits the same set) **→ switch back → [2, 3, 4, 8, 12, 13, 14]** with both correction values (6/6) returning unchanged. Database rows through all three states: score rows `[3, 4, 8, 12, 13, 14]` and both correction rows intact. Live post-deploy probe: `GET api/manager-subordinates-matrix` → 200 empty no-period state (`backups/2026-08-24-finalize/live_finalize_probe.json`). Report: `docs/FINALIZE_PRELAUNCH_2026-08-2x.md`.

### BUG-052: Score-correction refusals surfaced as a hardcoded alert, discarding the server's readable reason

- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `src/hooks/useEvaluationsMatrix.js` `submitScoreCorrection` catch; `src/components/admin/ScoreDetailModal.jsx` `handleSubmitCorrection` catch.
- Description: a 422 `CRITERIA_NOT_APPLICABLE` (server message: «Критерий 8 — проектный, а сотрудник сейчас не участник проекта») or any 409 from `api/admin/score-correction` reached the admin as the literal `alert('Ошибка при сохранении корректировки')` — the hook returned a hardcoded string and the modal alerted its own literal, so no server reason could ever surface on either correction route. Readable Russian, but indistinguishable from a network failure.
- Why it matters: the applicability refusal is a *decision* (corrections applicability, FINALIZE batch) — an admin who cannot see «критерий не применим» retries or files the refusal as an outage.
- Fix (2026-08-24, browser walkthrough): the hook returns `error.userMessage || …` (the apiClient already maps 409/422 to the server message), the modal alerts `error?.message || …`. The mid-level path (`ManagerSubordinatesMatrix.jsx`) already threaded the message and is unchanged. Deployed to live release `20260824T131920Z`.
- Verification: stale-modal 422 reproduced in a real browser before and after — alert text went from the hardcoded literal to the verbatim server reason; `tests/correctionErrorSurface.test.js` pins all three code paths; suite 277/277. See `docs/BROWSER_WALKTHROUGH_2026-08-2x.md` §J.

### BUG-053: World-readable dumps of live `epe_2026` accumulate in VPS `/tmp` outside the backup regime

- Status: 🟢 CLOSED
- Severity: 📌 Medium
- Location: `root@92.51.45.147:/tmp` — `epe_2026_before.dump` (0644, 19 Aug), `epe_2026_pre013_20260821_0549.dump` (0644), four `epe_2026_pre014_20260822_*.dump` (0644), `epe_2026_pre_mig014_20260822T063731Z.dump` (0644); only `epe_2026_after.dump` is 0600.
- Description: pre-migration safety dumps from the 19–22 Aug briefs were left in `/tmp` with default 0644 permissions. The backup regime (`/root/backups/epe`, chmod 600, 14-day pruning) does not cover them; they are full copies of production personal data readable by any local account and never pruned. The walkthrough stand's own dump was removed at teardown (this brief), but these predate it and were not this session's to delete.
- Why it matters: PROJECT_RULES calls a stray live copy «a second copy of production personal data outside the backup regime». `/tmp` is the most exposed directory on the host and survives until reboot cleanup, which this VPS may never perform.
- Fix (2026-08-24, Alexander approved the deletion in the prelaunch-fix-batch brief): the cleanup sweep found **ten** dumps in `/tmp`, not eight — the filed seven plus `epe_2026_after.dump` (0600) and two n8n application-schema dumps (`n8n_public_before.dump` 0644, `n8n_public_after.dump` 0600, both 19 Aug — the matrix-calibration brief's artifacts). Every one of the ten was first verified byte-identical (md5) to a dated local copy under the repo's gitignored `backups/` (`2026-08-20-matrix-calibration/`, `2026-08-21-periods-hierarchy/`, `2026-08-22-lifecycle-coeff/`). The approved seven were deleted; the three outside the approved list were **moved** to `/root/backups/epe/tmp_rescue_20260824/` (dir 0700, files 0600) rather than deleted. `/tmp` now contains zero dump files. Full before/after listing with sizes, dates and md5 pairs: `docs/PRELAUNCH_FIX_BATCH_2026-08-2x.md` §3.
- Prevention: PROJECT_RULES.md now carries the rule (2026-08-24): stand and rollback artifacts never live in `/tmp` — transient VPS-side artifacts go under root-only `/root/epe_stand_tmp` (0700), teardown includes their removal; `scripts/setup_walkthrough_throwaway.sh` was moved off host `/tmp` accordingly (dump + credential/workflow staging).
- Residual: `/tmp` still holds a few small non-data scraps from earlier briefs (schema `probe*.sql` queries, row-count listings `_live.txt`/`_restored.txt`, `epe-docs-hygiene/guard_nodes.json`, a docker-inspect JSON, an empty `wf_export/`) — no personal data, listed in the report; sweep them opportunistically on the next VPS-touching brief.
- Source: browser-walkthrough teardown sweep 2026-08-24; closed by the prelaunch fix batch the same day.

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
- Status: 🟢 CLOSED (2026-08-26, ROLE_ACCESS_DEPLOY — deployed release 20260826T134725Z; verified live in a real browser: HR typed /admin → redirected to /hr/dashboard, c_level reads the catalogue read-only)
- Severity: 📝 Low
- Location: `src/App.jsx` path `/admin` → `AdminRoute` → `AdminSettings`; `canAccessAdminPanel` includes `hr`.
- Description: Sidebar hides «Критерии» from HR. A typed URL opens the criteria catalogue shell. The API is admin-only (403). Company-wide numbers are not returned.
- Why it matters: HR sees a frozen/error catalogue, not results. Reporting-surface brief left this on purpose.
- Fix: wrap `/admin` in an admin-only route, or keep as-is.
- Fix (2026-08-26, ROLE_ACCESS_HR_CLEVEL, D-0826-6): `/admin` is now `ReportingRoute` — HR is redirected to `/hr/dashboard`, c_level reads the catalogue (read-only, server refuses its writes by role), and a failed load names its reason instead of the empty shell. Pinned in `tests/roleAccessHrClevel.test.js`. Closes when verified on the running system (report §5).

### BUG-014: No off-host backup copy
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: host `/root/backups/epe`; daily on-host dump, 14-day retention.
- Description: Weekly off-host copy (Timeweb S3, write-only key) was not implemented. Outstanding since 13 Aug.
- Why it matters: a host disk failure loses the only copies. Restore-verified on-host dumps exist.
- Fix: pick a target and a write-only key. Alexander said “later”.
- Progress (2026-08-21): **the stakes went up.** BUG-032's fix put `epe_2026` and the n8n application schema (58 workflows, 7 credentials, 8 settings) into the daily on-host job, so the one disk on `92.51.45.147` now holds the live campaign database, the n8n backend and every backup of both. A host or disk loss takes all of it together. Still open — the backup brief made closing it conditional on Alexander naming a target in that conversation, and he did not; no S3 sync was configured. Related: `N8N_ENCRYPTION_KEY` lives only in the Portainer stack environment and is in no dump, so an off-host copy of the dumps alone would still not restore working credentials.

### BUG-015: Stale Keychain admin password
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: macOS Keychain item `EPE auth test password reset 2026-08-18`.
- Description: That password returns 401 on live login (`Неверный email или пароль`). Browser proofs used a minted admin JWT. Alexander’s real session was kept.
- Why it matters: the stored item is wrong; failed attempts can lock the only admin if retried. Not a campaign-code defect.
- Fix: Alexander changes the admin password and updates or deletes the Keychain item.

---

### BUG-035: `errorHandler.js` overwrites 401 / 403 / 429 server messages
- Status: 🟢 CLOSED
- Severity: 📝 Low
- Location: `src/utils/errorHandler.js`.
- Description: the interceptor replaces the server's message for 401, 403 and 429 with fixed Russian strings. `CAPABILITY_FORBIDDEN` therefore reaches the user as the generic «Доступ запрещен. Недостаточно прав». The 20 Aug Russian-message pass covered 400/404/409/422 only, and the workflow strings behind these three codes are still English underneath.
- Why it matters: the read-only C-level trio hitting the correction gate, and any non-admin clicking a `/admin/periods` control, get a message that does not say what actually happened.
- Fix (2026-08-24): `handleApiError` returns `serverMessage` on 401/403/429 when present; the fixed Russian string is the fallback. `isAuthError` / client interceptor (clear `user`+`token`, redirect to `/login`, no draft sweep) unchanged — pinned in `tests/prelaunchCopyBatch.test.js`.
- Source: leftovers of `docs/PRELAUNCH_FIXES_2026-08-2x.md`; closed in `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md`.
- Closed: 2026-08-24

### BUG-037: «Создать период» is still rendered for c_level and HR
- Status: 🟢 CLOSED
- Severity: 📝 Low
- Location: `src/pages/AdminPeriods.jsx` header button.
- Description: `/admin/periods` is wrapped in `AdminRoute`, which admits admin, c_level and hr. The 21 Aug hardening gated the four controls the brief named; the create button was outside that list. The server answers 403 (`POST api/periods/create` is admin-only), so this is presentation, not access.
- Why it matters: same family as [BUG-013] — a non-admin is shown a write control and learns it is forbidden only by clicking it.
- Fix (2026-08-24): the button sits behind the same `canManage = isAdmin(user?.role)` as rename, reparent, activate and close. Pinned in `tests/moneyScreenGuards.test.js` and `tests/prelaunchCopyBatch.test.js`.
- Source: §2 "boundary kept" of `docs/POSTVERIFY_BATCH_2026-08-2x.md`; closed in `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md`.
- Closed: 2026-08-24

### BUG-038: The guard contract fails open when `required_roles` is omitted
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: LIVE `EPE: Auth Guard` → `Authorize`: `if (parsed.required_roles.length && !parsed.required_roles.includes(...))`; `Verify JWT` normalises a missing or non-array value to `[]`.
- Description: a route whose `Prepare Guard Input` omits `required_roles` authenticates without authorizing — any valid session passes. None of the current routes is affected; all declare explicit roles, and the seven periods routes were checked one by one.
- Why it matters: the failure mode of a future route is "silently open", not "loudly broken". That is the wrong default for the only authorization layer in the system.
- Fix: default-deny on an empty/absent `required_roles`, or a test that asserts every generated `Prepare Guard Input` declares one.
- Source: observations of `docs/PERIODS_VERIFY_2026-08-2x.md`.

### BUG-039: The `can_be_evaluated` submit guard and two `finalOf` branches have no test
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `tests/routeGuardWorkflows.test.js` (no assertion on `AND subj.can_be_evaluated = true`); `tests/periodsHierarchy.test.js` (the `c_level_only` and corrections branches of the close computation are covered by static fixtures only).
- Description: LIVE `API: Submit Evaluation` carries `AND subj.can_be_evaluated = true` in all three relation filters — verified 2026-08-21, and it is what keeps ids 21 / 40 / 61 out of every money number (D-0821-4). Nothing fails if a regeneration drops it. Separately, `score_corrections` was empty and no `c_level_direct` evaluation existed on either proof stand, so the correction-averaging and `c_level_only` branches of the close computation never executed end-to-end; both are textually identical to the client's, which production does exercise.
- Why it matters: the first guard is the only thing standing between a data gap and a coefficient-1.00 bonus row for three people. The second pair decides the money for criterion 1, the heaviest in the catalogue (weight 5.00).
- Fix: one assertion in `tests/routeGuardWorkflows.test.js`; seed the next proof stand with a c_level score, at least one correction, and a grade coefficient other than 1.00.
- Source: `docs/POSTVERIFY_BATCH_2026-08-2x.md` ("this guard has no static test") and the observations of `docs/PERIODS_VERIFY_2026-08-2x.md`.

### BUG-042: `useScoreCalculation` still substitutes an empty coefficient set on failure

- Status: 🟢 CLOSED (2026-08-26, ROLE_ACCESS_DEPLOY — deployed release 20260826T134725Z; the allSettled error card is pinned by tests, and the live score-calculator rendered its full 88-employee picker for a real c_level session with no silent fallback path left in the code)
- Severity: 📌 Medium (admin-only screen since 2026-08-22, and the number is a what-if rather than a payout — but it is the same silent-degradation shape as [BUG-030])
- Location: `src/hooks/useScoreCalculation.js:79-80` — `apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS).catch(() => ({ data: { data: [] } }))` and `apiClient.get(API_ENDPOINTS.ADMIN_USERS_DATA).catch(() => ({ data: { options: { grades: [] } } }))`, consumed by `src/pages/AdminScoreCalculator.jsx` (`/admin/score-calculator`).
- Description: the money screens were fixed on 2026-08-21 ([BUG-030]) by moving `useFinalScoresMatrix` to `Promise.allSettled` with an explicit error card, and `useScoreCoefficients` got the same treatment on 2026-08-22. The score calculator was in neither pass: a 401, a 500 or a network blip on either call still resolves to an empty array, `weight` falls back to `1.0` per criterion and every grade coefficient to `1.0`, and the calculator renders a full, plausible, **unweighted** breakdown with no error — including the per-criterion `оценка×коэффициент×вес` strings, which will read `×1.0×1.0`.
- Why it matters: it is a calibration tool. A C-level or admin comparing "what if this person scored 8 instead of 6" gets an answer computed without the weights that decide the actual bonus share, and nothing on screen says so.
- Repro: open `/admin/score-calculator` with `GET /api/score-coefficients` failing (revoke the session between the matrix call and the coefficients call, or block the route). The table renders; every weight shows 1.0.
- How to fix: the [BUG-030] pattern — `Promise.allSettled`, classify each rejection, clear `employees`/`matrixData`/`criteriaWithCoefficients`, and return an error card with retry before any table renders. `src/hooks/useScoreCoefficients.js` (2026-08-22) is the smaller worked example.
- H1 impact: none while nobody uses the calculator; it reads the active period, and there is none today.
- Source: found while making the coefficient screens admin-only in `docs/LIFECYCLE_COEFF_2026-08-2x.md`; the same `.catch`-to-empty family the brief was asked to close in `useScoreCoefficients` only.
- Fix (2026-08-26, ROLE_ACCESS_HR_CLEVEL): the [BUG-030] pattern applied — `Promise.allSettled`, per-request classification, numbers cleared and an error card with retry before any table renders. Became mandatory the moment `/admin/score-calculator` opened to c_level read access (D-0826-6): before this fix a c_level visitor on the undeployed backend would have seen exactly the silent ×1.0 table. Pinned in `tests/roleAccessHrClevel.test.js`. Closes when verified on the running system.

### BUG-043: with no active period, `/api/employees` reports the annual container as the current period

- Status: 🟢 CLOSED
- Severity: 📝 Low (no wrong number; a scope flag computed against the wrong period's participant list while nothing is running)
- Location: LIVE `API: Get Employees (Smart Role Based)` (`bKB4Sb46yWoq1tSV`) → `Build Identity-Bound Query`, the `current_period` CTE: `WHERE (is_active = true AND status = 'active') OR status = 'draft' ORDER BY CASE WHEN … THEN 0 ELSE 1 END, start_date DESC NULLS LAST, id DESC LIMIT 1`.
- Description: when nothing is active the CTE falls back to the newest **draft** period by `start_date DESC, id DESC`. H1-2026 and Annual 2026 both start `2026-01-01`, so `id DESC` decides and the **container** (id 5) wins. Measured live on 2026-08-22 after the lifecycle deploy: every role's `GET /api/employees` returned `current_period_id = 5`, not 2. `actor_is_in_scope` is therefore computed against Annual 2026's 89 inert participant rows instead of H1's 87.
- Why it matters: today it makes the out-of-scope notice too generous — Esenova and Balova are out of scope for H1 but in scope for the container, so before activation they are not shown the notice. It is presentation only while no period is active, and it disappears the moment H1 is activated (an active period sorts first). It also means "the current period" on that route can name a period that can never run a campaign.
- Fix (2026-08-24): the fix went further than excluding containers from the fallback — **the draft fallback is removed entirely**. The current period is the single **active leaf** period (`is_active AND status='active' AND period_type <> 'annual' AND` no children) or explicitly **none**: `current_period_id` null, `actor_is_in_scope` null, no preparation flag. Scope therefore exists from activation (including the preparation window), never from a draft or a container. The same leaf predicate was added to every campaign-surface period resolution — submit-evaluation, self-review-submit, check-self-review, check-evaluated, get-my-manager, score-correction — so an annual period or a container can never be "the campaign period" anywhere, even if one were force-activated by SQL. Reporting reads stay keyed on active alone, unchanged.
- Verification (2026-08-24): **live**, post-deploy (`backups/2026-08-24-reclass/live_reclass_probe.json`): all six probe roles' `GET /api/employees` returned `current_period_id = null`, `actor_is_in_scope = null`, `period_in_preparation = false` — container id 5 nowhere. **Stand** (`reclass_proof.json` → `bug043_draft` / `preparation`): draft state → none for every role; after activation → `current_period_id = 2` (the H1 leaf) with `period_in_preparation = true` and real scope; after close → none again. Static: `tests/authWorkflows.test.js` asserts the fallback is gone and the leaf predicate present; `tests/routeGuardWorkflows.test.js` / `tests/routeGuardDeferred.test.js` assert the leaf clause on every campaign-surface resolution.
- Client note: `TaskStatusContext` treats only `actor_is_in_scope === false` as out-of-scope, so the null answer shows no notice before activation — same visible behaviour as before, now for the right reason. Esenova and Balova get the notice the moment H1 is activated, which is the window that matters.
- Source: the live role×route probe of `docs/LIFECYCLE_COEFF_2026-08-2x.md` (`backups/2026-08-22-lifecycle-coeff/live_role_route_probe.json`). Pre-existing — the CTE's ORDER BY was not changed by that brief. Closed in `docs/RECLASS_2026-08-2x.md`.

### BUG-044: HANDOVER §10 report index omits the two newest reports

- Status: 🟢 CLOSED
- Severity: 📝 Low (documentation integrity, not behaviour)
- Location: `docs/HANDOVER.md` §10 "Where things are", the "Reports, in order:" list (line 339).
- Description: the a6ef553 build wrote two reports — `docs/LIFECYCLE_COEFF_2026-08-2x.md` and (in the preceding f9758d3) `docs/RECON_RECLASS_COEFF_2026-08-2x.md` — and both files exist on disk. The build updated §10's footer counts (`bugs.md` **20 open / 23 closed**, `migrations/001…014`) and added the two reports' names in §3 and §6.11, but did **not** add either to the canonical §10 report list, which still ended at `DOCS_HYGIENE_2026-08-21.md`.
- Why it matters: §9 makes the report index load-bearing — a fresh Cursor session is pointed at `AGENTS.md`, HANDOVER and "the one report relevant to its brief". A reader who scans §10 to find the lifecycle-gate or reclassification-recon report will not find it listed, and "the repo is the memory" (§9) depends on that index being complete.
- Fix (2026-08-24): §10's "Reports, in order" list now carries `RECON_RECLASS_COEFF_2026-08-2x.md` · `LIFECYCLE_COEFF_2026-08-2x.md` · `GATE_LIFECYCLE_COEFF_2026-08-2x.md` · `RECLASS_2026-08-2x.md` — all four reports written since the list last moved — and the §10 bug counters are reconciled to the post-close tally (19 open / 25 closed). Done in the reclassification build (`docs/RECLASS_2026-08-2x.md`), the first brief after the gate that was allowed to touch HANDOVER.
- Source: verification gate `docs/GATE_LIFECYCLE_COEFF_2026-08-2x.md` item 7, comparing §10 against the two report files on disk and the git diff of a6ef553.

### BUG-040: `deploy_epe_frontend.sh` requires `rg` on PATH and fails closed without it
- Status: 🟢 CLOSED (2026-08-25)
- Severity: 📝 Low
- Location: `scripts/deploy_epe_frontend.sh` — the two safety gates (refuse if a legacy `:5678` URL remains; refuse if the `/webhook` base is absent) call `rg`.
- Description: ripgrep is not installed on the delivery laptop, so the deploy refuses. On 2026-08-21 the gates were run by hand and the script re-run with a shell shim mapping `rg -q` to `grep -rqE`; gate semantics were preserved, not bypassed.
- Why it matters: failing closed is correct, but the workaround is manual and undocumented at the point of use, which is exactly where a rushed deploy skips it.
- Fix: install ripgrep, or fall back to `grep -rqE` inside the script when `rg` is absent.
- Source: `docs/POSTVERIFY_BATCH_2026-08-2x.md` live-deploy note.

---

- Fix (2026-08-25, D-0825-9): both gates use `grep -r`, which is POSIX and present on every machine this project runs on, and the script proves the tool works on the bundle before trusting a negative result — `test -s dist/index.html`, `command -v grep`, then `grep -r -q 'assets' dist/index.html`. That third check is the one that matters: without it a gate pointed at an empty or missing `dist` reports «legacy URL absent» and passes, and a vacuous pass reads exactly like a clean bundle. No shim was installed and none is needed.
- Why it mattered more than it looked: the failure was asymmetric. A missing `rg` fails closed; a present `rg` passes. On 2026-08-25 one session's gates ran (Cursor had a real `rg` on PATH) and another's refused, from the same script and the same repository, and nothing recorded which had happened.
- Verification: the deploy that shipped release `20260825T165732Z` printed `gates: legacy :5678 absent, /webhook base present` from the terminal where `bash -c 'command -v rg'` exits 1. `docs/TEAM_PAGE_AND_DEPLOY_LOCK_2026-08-25.md` §5.
### BUG-028: Stale top-level workflow export (evaluations-matrix)
- Status: 🟢 CLOSED
- Severity: 🟢 Low
- Location: `n8n_workflows/API_ evaluations-matrix.json`
- Description: The top-level export was the pre-guard, pre-period-binding 4-node workflow. Live runs the generated version (`scripts/build_route_guard_deferred.py` → `route_guard_deferred/evaluations-matrix.json`). Anything importing or trusting the stale file got an unguarded, all-periods-mixed matrix — it cost the 2026-08-21 throwaway stand one debug cycle.
- Why it matters: A future session or stand that seeds from the stale export silently reintroduces an unauthenticated period-mixing matrix.
- How to fix: Refresh top-level exports from live after each PUT (deploy_periods_hierarchy.py already does this for Manage Periods), or drop top-level duplicates of generator-owned workflows keeping only the id-bearing metadata.
- Fix (2026-08-24): the named instance was refreshed from live by the reclass deploy (`docs/RECLASS_2026-08-2x.md`). `docs/GATE_RECLASS_2026-08-2x.md` §8: "The named BUG-028 instance itself is now current." Hygiene 2026-08-24: top-level `API_ evaluations-matrix.json` has **9** nodes and is **not** in the stale-export set. The wider class remains [BUG-045] (nine other top-level exports still stale).

### BUG-045: The stale-export class is ten files wide, not one

- Status: 🔴 OPEN
- Severity: 📝 Low (repo hygiene; live itself is drift-free — every generator output was proven node-identical to live on 2026-08-24)
- Location: `n8n_workflows/` top level, measured against live `workflow_entity` on 2026-08-24 (gate for 39e34fd).
- Description: [BUG-028]'s named instance is fixed — `API_ evaluations-matrix.json` was refreshed by the reclass deploy and now matches live — but the same comparison run across **all 37** top-level exports found **10 materially stale** (different `jsCode`/queries, not cosmetics): `API_ Admin Get Users Data.json`, `API_ All-evaluation.json`, `API_ Analytics Dashboard - Optimized.json`, `API_ Get Evaluation Details FIXED.json`, `API_ HR Evaluation Status.json`, `API_ Manager Subordinates Matrix.json`, `API_ My Profile V5 (Fixed Empty).json`, `API_ Register.json`, `API_ Reset Password.json`, `API_ evaluation-details-by-user.json`. Four of those (`All-evaluation`, `Analytics`, `Manager Subordinates Matrix`, `evaluation-details-by-user`) are **pre-Auth-Guard** shapes — the exact unguarded-stand hazard BUG-028 records. Two more exports name workflows deliberately deleted from live (`API_ Get Admin Data Fixed.json`, `API_ Get Employee Self Review.json`) and read as available.
- Why it matters: same as BUG-028, ×10 — a stand or a reader that trusts a top-level export gets pre-guard behaviour; deploy scripts refresh only their own targets, so every non-target export decays silently.
- How to fix: one sweep — refresh all top-level exports from live behind `assert_not_a_generator_input` (the deploy_reclass.py mechanism, run over the full set), delete or clearly mark the two deleted-workflow exports, and add a repo check that fails when a top-level export of a generator-owned workflow differs from the generator output.
- Source: verification gate `docs/GATE_RECLASS_2026-08-2x.md` §5, full-corpus comparison.
- Progress (2026-08-24, finalization batch): `API_ Manager Subordinates Matrix.json` — one of the four pre-guard shapes — is now refreshed from verified live (it had also been a *generator input* via a dead `legacy_query` read in `build_route_guard_deferred.py`, which blocked the deploy's refresh step exactly as designed; the dead read was removed, generator output byte-unchanged). `API_ Score Correction.json` refreshed by the same deploy. Nine stale exports remain; `scripts/check_live_drift.py` (added this batch) now gives the full-corpus generator-vs-live comparison on demand — post-deploy run: 30 identical, 0 changed.

### BUG-047: DECISIONS.md D-0822-3 mis-states the full-re-submit response

- Status: 🟢 CLOSED
- Severity: 📝 Low (decision-register accuracy; the code, the report and the runtime proof all agree with each other — only the register differs)
- Location: `DECISIONS.md` → D-0822-3, third bullet: "(a full re-submit stays 409 `DUPLICATE_EVALUATION`)".
- Description: the deployed `Build Insert SQL` answers **any** overlap with already-scored criteria — including a full re-submit — with 409 `CRITERIA_ALREADY_SCORED` naming the ids; `DUPLICATE_EVALUATION` survives only on the concurrent-create race in `Format Response` (ON CONFLICT DO NOTHING → zero rows). The build's own runtime proof records exactly that (`reclass_proof.json` → g_flow: "a full re-submit is refused by the same rule" → 409 `CRITERIA_ALREADY_SCORED`), and `docs/RECLASS_2026-08-2x.md` §1.2 states it correctly. The register sentence describes behaviour that does not exist.
- Why it matters: DECISIONS.md is the single register (§10 HANDOVER); a future session reconciling client copy or tests against it would "fix" the code toward the wrong error name — the §6.11 wrong-premise class.
- How to fix: one-line edit of the parenthetical to "(a full re-submit answers the same 409 `CRITERIA_ALREADY_SCORED`; `DUPLICATE_EVALUATION` remains only on the concurrent-create race)".
- Source: verification gate `docs/GATE_RECLASS_2026-08-2x.md` §7, deployed text vs register text.
- Fix (2026-08-24): the D-0822-3 parenthetical now reads exactly the deployed truth — full re-submit → 409 `CRITERIA_ALREADY_SCORED`; `DUPLICATE_EVALUATION` only on the concurrent-create race in `Format Response` — matching the deployed `Build Insert SQL`, `docs/RECLASS_2026-08-2x.md` §1.2 and the gate's runtime record (`reclass_proof.json` → g_flow). The same D-0822-3 bullet was extended in the same edit to record the approved corrections-applicability decision this batch deployed. Report: `docs/FINALIZE_PRELAUNCH_2026-08-2x.md`.

### BUG-048: FINALIZE §1 mis-describes the submit path's check order; the pre-period 422 is a paused-state classification disclosure submit does not make

- Status: 🟢 CLOSED
- Severity: 📝 Low (report-accuracy; the deployed corrections behaviour itself is exactly as claimed and approved — only one of the three justification sentences is wrong, and the disclosure it waves away is real but marginal)
- Location: `docs/FINALIZE_PRELAUNCH_2026-08-2x.md` §1 "Ordering decision, surfaced", the sentence "the deployed submit path already answers applicability before its relation checks, so this leaks nothing submit does not".
- Description: the deployed `API: Submit Evaluation` → `Build Insert SQL` answers `SCOPE_MISMATCH` 403 (one lookup bundling the actor–subject relation and active-period scope), `PERIOD_NOT_STARTED` 409 and `CANNOT_EVALUATE` 403 **before** its applicability 422 — read from live `workflow_entity` 2026-08-24 (byte-identical to the generator). Submit therefore never reveals applicability while the launch is paused (it answers `SCOPE_MISMATCH` first), whereas the corrections route now answers 422 `CRITERIA_NOT_APPLICABLE` before its period gate — so any role-gated writer (admin / c_level / any manager) can distinguish a subject's current project/general classification for **any** subject id by probing criterion 8, on paused live and mid-campaign pre-ownership.
- Why it matters: DECISIONS/report accuracy is the §6.11 wrong-premise class — a future session citing the sentence would believe the ordering introduces no new information surface. The disclosure itself is minor (classification is visible to admin/c_level on every matrix, and to a manager for their own span), but it is real, was traded deliberately for live provability, and should be recorded as a cost, not denied.
- How to fix: correct the §1 sentence (and mirror the nuance in the D-0822-3 extension note): the refusal is non-mutating and keeps the rule provable on paused live — those two reasons stand — at the cost of a marginal classification probe that submit does not offer. Alternatively reorder the check behind the period gate and accept byte-identity-only deploy verification; that trade-off is Alexander's to re-make, not an executor's.
- Source: verification gate `docs/GATE_FINALIZE_2026-08-2x.md` §2, deployed submit order vs report text.
- Closed (2026-08-24, criterion-9 batch): **accepted behavior by decision D-0824-1** — the pre-period applicability answer is intentional. The two standing reasons (non-mutating refusal; the deployed rule stays provable on paused live) hold; the cost — a role-gated writer can distinguish a subject's current project/general classification pre-period by probing a project criterion, which submit does not offer — is recorded as an accepted cost, not denied. The wrong justification sentence in `docs/FINALIZE_PRELAUNCH_2026-08-2x.md` §1 is corrected in place as a marked correction (2026-08-24). No code change; the deployed ordering stays as approved.

### BUG-049: Migration 006 does not reproduce live's `score_corrections` constraints (criteria FK typo'd to `users`, CASCADE vs live NO ACTION); `schema.sql` predates the table

- Status: 🟢 CLOSED
- Severity: 📝 Low (no live impact — stands restore from live dumps; wrong only for a from-migrations rebuild)
- Location: `migrations/006_add_hierarchical_corrections.sql` (`score_corrections_criteria_id_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.users(id) ON DELETE CASCADE` — criteria FK pointing at **users**, and `ON DELETE CASCADE` on subject/evaluator/criteria); `schema.sql` (no `score_corrections` table at all).
- Description: live `epe_2026` (pg_constraint, read 2026-08-24) has `score_corrections_criteria_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.criteria(id)` and plain `NO ACTION` on all of subject/evaluator/criteria/period FKs. The migration as written would create a criteria FK that only accepts criterion ids that happen to be user ids, and CASCADE deletes that would silently destroy correction history when a user or criterion is removed. Live was evidently built/repaired by another path; the repo's DDL record does not say so anywhere.
- Why it matters: the repo is the memory (§9 HANDOVER). The H2 rewrite, or any stand built from `schema.sql` + `migrations/001…014` instead of a live dump, inherits materially different — and data-destroying — constraints, and the gate that catches it would blame the wrong layer. Live's `NO ACTION` FKs are also what makes the Manage Criteria hard-delete safe (FK-blocked once data references a criterion) — a from-migrations rebuild loses that protection.
- How to fix: a reconcile migration (or a corrective note in 006) stating the live constraint set verbatim, plus a regenerated `schema.sql` snapshot at rewrite time; cheapest correct fix is a new migration `015_reconcile_score_corrections_constraints.sql` that drops-if-exists the typo'd FK and recreates the live set idempotently.
- Source: verification gate `docs/GATE_FINALIZE_2026-08-2x.md` §6 (FK check behind the criterion-delete adversarial question).
- Fix (2026-08-24, criterion-9 batch): `migrations/006_add_hierarchical_corrections.sql` brought to the live FK set — criteria FK now `REFERENCES performance_db.criteria(id)` (was the `users(id)` typo), all three FKs plain `NO ACTION` (were `ON DELETE CASCADE`), constraint names aligned to live (`score_corrections_subject_fkey` / `_criteria_fkey` / `_evaluator_fkey`, without `_id`). Migration file only — live was already correct and was not touched (read-only `pg_constraint` evidence, `epe_2026` 2026-08-24: `score_corrections_criteria_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.criteria(id)`; `_subject_fkey` / `_evaluator_fkey` → `users(id)`; `_period_id_fkey` → `evaluation_periods(id)`; all plain NO ACTION; recorded in `docs/CRITERION9_2026-08-2x.md`). The same read surfaced residual divergences beyond this bug's FK scope — `period_id` absent from the entire migration chain, live's 4-column unique index vs 006's 3-column one, 006's CHECK absent on live, `schema.sql` still without the table — re-filed precisely as BUG-050 so they are not lost in this closure.

### BUG-050: The migration chain cannot rebuild live `score_corrections`: `period_id` (column, FK, unique index) appears in no migration; 006's CHECK is absent on live; `schema.sql` predates the table

- Status: 🔴 OPEN
- Severity: 📝 Low (no live impact — stands restore from live dumps; wrong only for a from-migrations rebuild)
- Location: `migrations/001…014` (no statement adds `score_corrections.period_id`); `migrations/006_add_hierarchical_corrections.sql` (declares `score_corrections_score_check` and the 3-column unique index `idx_score_corrections_unique (subject_id, criteria_id, correction_level)`); `schema.sql` (no `score_corrections` table at all).
- Description: live `epe_2026` (`pg_constraint` + `pg_indexes`, read 2026-08-24) has a `period_id` column with `score_corrections_period_id_fkey FOREIGN KEY (period_id) REFERENCES performance_db.evaluation_periods(id)` and the UNIQUE index `idx_score_corrections_unique_period (subject_id, criteria_id, correction_level, period_id)`, and **no** CHECK constraint on `correction_score`. Nothing in the migration chain creates any of that — BUG-049's fix reconciled 006's FK declarations only. A from-migrations rebuild gets a table without `period_id` — a column `API: Score Correction` writes — and a 3-column uniqueness that allows one correction per subject+criterion+level across **all** periods instead of per period.
- Why it matters: same class as BUG-049 — the repo is the memory (§9 HANDOVER). The H2 rewrite, or any stand built from `schema.sql` + migrations instead of a live dump, inherits a table the deployed workflows cannot write to, and the gate that catches it would blame the workflow layer, not the DDL record.
- How to fix: a reconcile migration `015_reconcile_score_corrections_period.sql` that idempotently adds `period_id` + its FK + the 4-column unique index (dropping the 3-column one) and records the CHECK divergence, plus a regenerated `schema.sql` snapshot at rewrite time.
- Source: live `pg_constraint` / `pg_indexes` read during the criterion-9 batch while closing BUG-049 (`docs/CRITERION9_2026-08-2x.md`).

### BUG-054: The evaluation-history workflow is named «Received» while its SQL is given-only

- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: live workflow `API: My Evaluation History (Received)` (`updatedAt=2026-08-19T08:40:21.096Z`), generated as `route_guard_h1/evaluation-history.json`; node `Build History Query`.
- Description: the workflow's name says Received, but the SQL is `WHERE e.evaluator_id = ${actorId} AND e.is_self_evaluation = false` — the route (`GET /api/evaluation-history`) returns only evaluations the actor **gave**. Received upward content deliberately does not reach this route (D-0824-3); the behaviour is correct, the name is not.
- Why it matters: the name is the first thing the next engineer reads. A future change "fixing" the route to match its name would open the upward channel the server currently seals.
- How to fix: rename the workflow (builder + a live PUT that changes the name only, or fold into the next PUT touching this workflow) to e.g. `API: My Evaluation History (Given)`.
- Source: surfaced in `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md` §4/§8; filed in `docs/EMPLOYEES_PERIOD_META_2026-08-2x.md`.

### BUG-055: Profile prints the label «Оценен подчиненным:» against an evaluator name the server nulls

- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/pages/Profile.jsx:221` and `src/pages/Profile.jsx:316` — `Оценен подчиненным: {evaluation.evaluator_name}`.
- Description: for upward rows (`evaluation_source='subordinate'`) `API: My Profile V5` nulls `evaluator_name`/`evaluator_title` before the row reaches the subject (D-0824-3 anonymity). The Profile card still renders the label with the nulled field, producing «Оценен подчиненным: » followed by nothing.
- Why it matters: cosmetic — an empty-looking label on the subject's own profile once upward evaluations exist. No data leaks; the null is the seal working.
- How to fix: when `evaluation_source === 'subordinate'`, render the label without the name (e.g. just «Оценен подчиненным») or an anonymized wording.
- Source: surfaced in `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md` §4/§8; filed in `docs/EMPLOYEES_PERIOD_META_2026-08-2x.md`.

### BUG-057: The Admin Settings cleanup button calls a route that was deleted from live

- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/pages/AdminSettings.jsx:132` (`apiClient.post(API_ENDPOINTS.ADMIN_CLEAR_TEST_EVALUATIONS)`) and `src/config/api.js:107` (the constant).
- Description: `API: Admin Clear Test Evaluations` was deleted from live on 2026-08-19 under BUG-002. Verified live this session: `SELECT id, name, active FROM public.workflow_entity WHERE name ILIKE '%clear%' OR nodes::text ILIKE '%clear-test-evaluations%'` returns `(0 rows)` — the route is absent by name **and** by node content. The frontend control and its endpoint constant were never removed.
- Why it matters: an admin-visible button that 404s and deletes nothing. Not a hazard — the destructive route is genuinely gone — but it invites someone to "fix" it by restoring the endpoint, which is the exact thing BUG-002 closed. It also misleads anyone reading the admin surface for what the system can still do.
- How to fix: delete the control from `AdminSettings.jsx` and the constant from `api.js`. No server change.
- Note: the previous session declined to file this because asserting the route's absence needed a live probe it could not make (`docs/LAUNCH_READINESS_SMOKE_FACTS_2026-08-25.md` §9). That probe is now done, so the row is filed on a verified premise rather than an assumed one.
- Source: `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md` §4.4.

### BUG-058: Three EPE artefacts survive in VPS `/tmp` after the BUG-053 cleanup

- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: VPS `92.51.45.147` — `/tmp/epe-health-body` (15 B, 18 Aug), `/tmp/epe-n8n-before-recreate.json` (11 388 B, 18 Aug), `/tmp/epe-docs-hygiene/guard_nodes.json` (4 605 B, 20 Aug). All mode `0644`.
- Description: BUG-053's fix removed the seven world-readable `epe_2026` dumps from `/tmp` and established the rule that no brief artefact lives there at all (`PROJECT_RULES` — everything transient goes under root-only `/root/epe_stand_tmp`). These three predate the rule and were not caught, because the cleanup targeted dumps specifically.
- Why it matters: materially smaller than BUG-053 — none of the three contains employee personal data; the largest is an n8n container-config snapshot and the other two are a health-probe body and a workflow-node listing. It is a rule violation and a stale-file question, not an exposure. It is filed because the rule is «no brief artefact in `/tmp`», not «no dumps in `/tmp`».
- How to fix: `rm -rf /tmp/epe-health-body /tmp/epe-n8n-before-recreate.json /tmp/epe-docs-hygiene` from a session authorised to write. Confirm nothing else matches `/tmp/*epe*` afterwards.
- Not done here: `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md` was a read-only brief; its boundary was «surface, do not resolve».
- Source: `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md` §5.2.

### BUG-059: User-row edits leave no trace, and two of them silently invalidated an accepted report

- Status: 🔴 OPEN
- Severity: ⚠️ High
- Location: `performance_db.users` (no `updated_at`, no history table); LIVE `API: Admin Save User (GUI Mode)` (writes nothing to an audit trail); `docs/LAB_DIVISION_HIERARCHY_2026-08-25.md` §2 write #6, §3, §4.
- Description: `performance_db.users` has 20 columns and none of them records when or by whom a row last changed, and the only write route keeps no log. On 2026-08-25 the Caddy access log shows ten `POST /webhook/admin/save-user` calls: six from `Python-urllib/3.12` at 12:41:52–12:42:22 UTC (the D-0825-3 script, fully documented) and **four from a Mac browser at 12:52:31–12:56:27 UTC that no report records**. A full-column diff of all 89 users against the 2026-08-25T00:20:01Z cron dump shows exactly what those four did: `53 Muhammetberdi Garayev` moved from manager 68 to **45**, and `33 Eziz Kurbangeldiyev` moved from manager 47 to **2**. The first contradicts an accepted report: `LAB_DIVISION_HIERARCHY_2026-08-25.md` states write #6 as `53 → 68`, its §3 tree puts Garayev under Hekimov, and its §4 verification table asserts `Hekimov reports [20, 53, 56, 85]` / `Hojayeva reports [1, 6, 55, 68]`. Live at 2026-08-25 13:39 UTC reads `Hekimov [20, 56, 85]` and `Hojayeva [1, 6, 53, 55, 68]`. The report was true when written; it is false now, and nothing in the system says so.
- Why it matters: two separate costs. (1) Any report that quotes a user row is unfalsifiable after the fact — the only way this session could date a change at all was to restore five cron dumps and cross-reference a Caddy log that retains two days. Classification changes older than 2026-08-23 can now be dated only to a 22-hour window, and anything before 2026-08-20 cannot be recovered at all. (2) Classification is a money input (criteria count drives bonus share, HANDOVER §4), so an undated, unattributed change to `work_category` moves someone's share of the pool with no record of who moved it.
- How to fix: the durable fix is an audit row per user write (actor from the guard identity, user id, old value, new value, timestamp) — the same gap already noted for coefficient writes in HANDOVER §7. The cheap interim is an `updated_at` column with a trigger, which at least dates a change even if it cannot attribute it. Separately, `docs/LAB_DIVISION_HIERARCHY_2026-08-25.md` needs a postscript recording the 12:52–12:56 edits, in the same style as the postscript `PRELAUNCH_LIVE_CHECK_2026-08-25.md` already carries.
- Not done here: `docs/ORG_REVIEW_H1_2026-08-25.md` was a read-only brief with the boundary «surface, do not resolve»; neither the data nor the earlier report was touched. Whether Garayev belongs under Hekimov or under Hojayeva is an org-data question for the owner, and it is A1 in the review sheet.
- Source: `docs/ORG_REVIEW_H1_2026-08-25.md` §3 A1/A2 and §4.3.

### BUG-060: A terminated person still occupies a row in the admin money matrix

- Status: 🔴 OPEN
- Severity: 🟡 Medium
- Location: LIVE `API: evaluations-matrix` → `Build Matrix Query`; `src/hooks/useEvaluationsMatrix.js`, `src/hooks/useFinalScoresMatrix.js`, `src/utils/matrixUtils.js` (`filterEmployees` has no scope or employment predicate).
- Description: the matrix query selects every `u.role != 'admin'` and `LEFT JOIN`s `evaluation_period_participants`. It *emits* `COALESCE(epp.is_in_scope, false) AS is_in_scope` per person but never filters on it, and it does not read `users.terminated_at` at all. After D-0825-7 a terminated person therefore still appears as a row in Матрица оценок, Итоговые баллы and Калькуляция бонусов, with empty cells — the same way Esenova (31) and Balova (35) already do because they are out of H1 scope by hire date.
- Why it matters: cosmetic rather than money, and the distinction is the point. The pool is computed at close from `period_results`, where a terminated person freezes as `is_in_scope=false, has_data=false` with every rating and both money columns NULL (`docs/TERMINATED_EMPLOYEES_2026-08-25.md` §3.1 measures this on a stand: pool 410.842 → 302.518, the difference equal to the excluded person's index to four decimals). The C-level write star is already hidden, because `canReceiveCLevel` reads `is_in_scope && can_be_evaluated`. So no number is wrong; the screen is just noisier than D-0825-7's «appears in no list» implies.
- How to fix: needs an owner decision before code. Filtering the matrix on `terminated_at IS NULL` hides former employees but leaves out-of-scope-by-hire-date people visible; filtering on `is_in_scope` hides both. The two populations are different — one has left the company, the other is employed and simply outside this period — and which of them an admin should still see on a money screen is a product question.
- Not done here: the TERMINATED_EMPLOYEES brief's boundary was «anything this brief does not resolve: surface — do not resolve», and it did not enumerate the money matrix among the surfaces that must lose the person. No matrix workflow was touched.
- Source: `docs/TERMINATED_EMPLOYEES_2026-08-25.md` §5.1.

### BUG-061: `admin/save-user` will accept a terminated person as somebody's manager

- Status: 🔴 OPEN
- Severity: 🟡 Medium
- Location: LIVE `API: Admin Save User (GUI Mode)` → `Validate User Data` / `Build User Upsert` (no validation of `manager_id` against `users.terminated_at`).
- Description: since D-0825-7 the admin screen no longer offers a terminated person in the «Руководитель» dropdown — `API: Admin Get Users Data` filters `options.managers` on `!u.terminated_at`. The write route itself has no such check: it accepts any `manager_id` that satisfies the foreign key. A script, the Excel import, or a hand-made request can still point a live employee at a terminated manager.
- Why it matters: that employee would then be evaluated by nobody. A terminated actor is out of scope, so `API: Get Employees` returns them an empty task list (`COALESCE((SELECT is_in_scope FROM actor_scope), false)`), and `API: Submit Evaluation` refuses the manager channel with 403 `SCOPE_MISMATCH`. The subordinate keeps a `manager_id` that looks correct on every screen and produces no manager evaluation — and a missing `rating_manager` means a missing `final_rating` and a missing `bonus_index` at close. It is the same failure mode as the Hojayeva anomaly, arriving from the other direction.
- How to fix: a 422 in `Validate User Data` when the requested `manager_id` names a person with `terminated_at IS NOT NULL`. Cheap in isolation; the reason it was not done here is that `admin/save-user` is a full-row overwrite with `body.role || 'employee'` and `body.work_category || 'general'` defaults, i.e. the most dangerous write path in the system, and the UI already prevents the case.
- Not done here: no change was made to `admin/save-user` in the TERMINATED_EMPLOYEES brief. The client-side guard shipped; the server-side one did not.
- Source: `docs/TERMINATED_EMPLOYEES_2026-08-25.md` §5.2.

### BUG-062: Two sessions can flip the live frontend symlink minutes apart, and nothing notices

- Status: 🟢 CLOSED (2026-08-25)
- Severity: ⚠️ High
- Location: `scripts/deploy_epe_frontend.sh` (no lock, no dirty-tree check, no commit stamp — see BUG-056); `/var/www/epe/current`.
- Description: on 2026-08-25 a second agent session deployed release `20260825T160958Z` at 16:10:06Z while this session was mid-brief in the same checkout. This session had read `current` as `20260825T153640Z` at 16:03Z, built against that assumption, and only discovered the change because it captured `readlink current` again immediately before flipping the symlink. Had it flipped on the stale reading, the other session's live change would have been reverted silently.
- Why it matters: the deploy script's rollback capture (`OLD_LINK`) makes the *last* deploy recoverable, not the *other* session's. Two builds from two different working trees can alternate as `current` with no record of which is which — the release id is a timestamp, not a commit. This is the 2026-08-22 parallel-session incident in a different organ.
- How to fix: an `flock` on a lockfile for the whole deploy, plus refusing to flip when `readlink current` differs from the value captured at the start of the run. Both are a few lines and neither needs the server. Stamping the commit hash into the release (BUG-056) would make «which build is live» answerable at all.
- Not done here: this brief's boundary was the frontend filter row; the deploy script was not modified. The collision was handled by hand — the release was uploaded, the symlink left alone, the build redone on top of what was actually live, and only then flipped.
- Source: `docs/ADMIN_USERS_FILTERS_2026-08-25.md` §7.

- Fix (2026-08-25, D-0825-9): two independent protections in `scripts/deploy_epe_frontend.sh`. **A lock** — atomic `mkdir` on `.epe-deploy.lock` locally and `/var/www/epe/.deploy.lock` on the host, both naming their holder, both released by an `EXIT` trap, neither ever broken automatically. **A compare-and-swap** — `current` is read before the build and re-read inside the same remote command that flips it, so nothing can move between the check and the swap; a mismatch prints `CONFLICT expected=… actual=…`, exits 1 and leaves the symlink alone. The lock catches a concurrent run of this script; the CAS catches what a lock cannot — an older copy of the script, a hand-made `ln -sfn`, or a deploy from another machine.
- Verification (demonstrated, not asserted): deploy A was started with the delay-only test hook `EPE_DEPLOY_PAUSE_BEFORE_FLIP=90`; deploy B was refused by the lock, naming A's pid and start time, exit 1, live unchanged. Then `current` was moved by a raw `ln -sfn` to a byte-identical probe release — the public bundle hash never changed — and A refused at its flip with `CONFLICT expected=releases/20260825T162505Z actual=releases/20260825T000000Z-conflictprobe`, leaving `current` where the other party had put it. `docs/TEAM_PAGE_AND_DEPLOY_LOCK_2026-08-25.md` §4.
- Still open next door: the release id is a timestamp and carries no commit (BUG-056), so the conflict message can say when the other build went live but not what it was.
### BUG-063: `/team` throws — `setLoadingSelfReviews` is called and never declared

- Status: 🟢 CLOSED (2026-08-25)
- Severity: ⚠️ High
- Location: `src/pages/TeamView.jsx:111` and `:136`. No matching `useState` anywhere in the file.
- Description: `loadStatuses` calls `setLoadingSelfReviews(true)` before fetching and `setLoadingSelfReviews(false)` in its `finally`. The setter does not exist, so the first call raises `ReferenceError`. Pre-existing: `git show HEAD:src/pages/TeamView.jsx` carries both calls and no declaration, and `eslint` reports them as `no-undef` — two of the repo's 19-error baseline.
- Why it matters: the effect only runs when `visibleUsers.length > 0`, so the page survives for anyone with no subordinates. A manager with reports hits it on mount. The page also loads its roster from `useUsers()` → `GET /api/admin-users-data`, which is admin-only, so a manager's roster is empty today and the crash is masked — the two defects hide each other, and fixing either alone exposes the other.
- How to fix: declare the state (`const [loadingSelfReviews, setLoadingSelfReviews] = useState(false);`) or delete both calls; then decide whether `/team` should read `/api/employees` instead of the admin route.
- Not done here: `/team` is outside the ADMIN_USERS_FILTERS subject. This session touched `TeamView.jsx` only to pass the new `facets` / `activeFilterCount` props to `UserFilters` and to drop the now-unused `options`; it added no lint error and removed none.
- Source: `docs/ADMIN_USERS_FILTERS_2026-08-25.md` §8.

- Runtime verdict first (2026-08-25): **`/team` never threw for a manager.** `useUsers()` reads the admin-only `GET /api/admin-users-data`, a manager gets 403, `users` stays `[]`, and `loadStatuses` returns at `if (visibleUsers.length === 0) return;` — three lines before the undeclared setter. Proven in a browser on a stand: the manager saw «У вас нет подчинённых в системе» and a console carrying `403` + «Ошибка загрузки пользователей», with no `ReferenceError`. For an **admin** typing the URL it did throw, twice — once inside the `try` (caught and logged) and once in the `finally` (uncaught, surfacing as `Uncaught (in promise)` because `loadStatuses()` is called without `await` or `.catch`) — and the page rendered anyway, with `selfReviewsStatus` and `evaluationStatuses` never populated. The network log for that pass shows the `Promise.all` never ran: no request to `/api/hr/evaluation-status` at all. So the visible symptom was not a crash but status columns that read «nothing done» for everybody.
- Severity, restated: a tidy-up, not a launch blocker. The launch blocker on this page was BUG-012, which is what a manager actually met.
- Fix (2026-08-25, D-0825-9): `loadStatuses` is gone entirely, and the undeclared setter with it. The flags it was fetching now ride on `/api/employees` — `has_self_review` → Self, `evaluated_by_actor` → Рук. — which is where the manager dashboard has read them since BUG-034. `npx eslint src` drops 19 → 15 errors: two `no-undef` and the two dead handlers of the modals this change made unreachable.
- Verification: on the fixed build an admin opening `/team` sees 5 direct reports and a console containing only the pre-login 401. `docs/TEAM_PAGE_AND_DEPLOY_LOCK_2026-08-25.md` §1.
### BUG-064: The user edit form still offers «Tender», which the write route refuses

- Status: 🔴 OPEN
- Severity: 🟢 Low
- Location: `src/components/admin/UserModal.jsx`, the `work_category` select (`<option value="tender">Tender</option>`); live `API: Admin Save User (GUI Mode)` validates `general` / `project` only.
- Description: «Тендер» is a leftover: an unused `work_category_type` enum label carried by zero live rows, which `admin/save-user` answers 422 for (`docs/TENDER_CATEGORY_2026-08-2x.md`). The **filter** row no longer offers it — since 2026-08-25 its category options are derived from the population — but the **edit** form still does.
- Why it matters: an admin who picks it gets a 422 and a generic «Ошибка при сохранении» toast, with nothing saying the value is retired. Small, but it is a money-adjacent field: `work_category` drives project-criterion applicability.
- How to fix: remove the option from `UserModal`, or drive that select from `WORK_CATEGORY_LABELS` in `src/config/constants.js`, which already lists only `general` and `project`.
- Not done here: the brief's subject was the filter row; `UserModal` is the edit path and was not touched.
- Source: `docs/ADMIN_USERS_FILTERS_2026-08-25.md` §8.

### BUG-065: `/team` no longer shows an admin the whole subtree, only direct reports

- Status: 🔴 OPEN
- Severity: 🟢 Low
- Location: `src/hooks/useTeamRoster.js` → `GET /api/employees` (`scoped` CTE: `WHERE users.manager_id = ${actorId}`); `src/pages/TeamView.jsx`.
- Description: until 2026-08-25 `/team` built its list by walking `manager_id` recursively through the admin roster, so an admin who typed the URL saw their whole subtree — 30 people for Alexander. The manager-scoped route returns direct reports only, so the same page now shows 5. For a manager nothing was lost: they never saw anything at all (BUG-012).
- Why it matters: it does not, for the campaign — `/admin/users` is the full roster and is guarded for it, and `/team` is a manager's screen that happens to admit admins through `ManagerRoute`. It is recorded because it is a deliberate behaviour change, not an oversight, and because somebody will notice the number moved.
- How to fix, if the owner wants the old view: a separate screen, or a `?subtree=1` parameter on a route that can prove the actor is above every person it returns. Not a change to `/api/employees`, whose whole value is that its scope is not negotiable by the client.
- Source: `docs/TEAM_PAGE_AND_DEPLOY_LOCK_2026-08-25.md` §2 and §7.

### BUG-066: A missing hire date silently keeps a person in scope of every period ever created

- Status: 🟢 CLOSED (2026-08-26, forward-looking only — see the Fix line)
- Severity: 🟡 Medium
- Location: LIVE `API: Manage Periods` → `Build Create SQL`, the participants CTE; `performance_db.users.join_date`.
- Description: scope is computed once, when a period is created, by `CASE WHEN u.terminated_at IS NOT NULL THEN false WHEN u.join_date IS NOT NULL AND u.join_date > '<end_date>'::date THEN false ELSE true END`. The second branch guards on `join_date IS NOT NULL`, so a person with **no hire date at all** falls through to `ELSE true` — in scope, `exclusion_reason NULL`, indistinguishable in `evaluation_period_participants` from somebody with ten years' service. There is no warning anywhere. Live 2026-08-25 17:2xZ: exactly one such row of 89 — **Cem Durukan (21)**, General Manager, `join_date IS NULL`, in scope of both period 2 and period 5.
- Why it matters: nothing today. Durukan is `can_evaluate=false` and `can_be_evaluated=false` (D-0821-4), has no grade and no manager, and his `c_level` role cannot submit a self-review, so he can neither give nor receive a score and no money number can reach him. The rule is what matters: it fires the same way for **every future period**, including H2, and it is exactly the wrong default for the population it will meet there — somebody entered into the portal before their start date (offer signed in April, first day in September) has a NULL or a future-looking hire date and would be admitted to the period silently. Criteria count drives bonus share, so an unnoticed participant is a money input nobody checked.
- How to fix: this is an owner decision before it is code. Either (a) fill Durukan's `join_date` in and keep the rule, or (b) invert the default so an unknown hire date means **out of scope** with a reason such as `join_date_unknown`, requiring an explicit hand-inclusion — which is now possible, because `POST /api/admin/include-participant` exists (D-0825-10). (b) is safer and noisier: money never lands on somebody nobody looked at, at the cost of a click per advance-entered hire.
- Not done here: the MID_YEAR_HIRES_SCOPE brief's boundary was «anything the brief does not resolve: surface — do not resolve», and it forbade any write to a user row. `API: Manage Periods` was deliberately not touched by that brief at all.
- Fix (2026-08-26, D-0825-12): the owner chose option (b). `Build Create SQL` now reads `WHEN u.terminated_at IS NOT NULL THEN false WHEN u.join_date IS NULL THEN false WHEN u.join_date > '<end_date>'::date THEN false ELSE true`, with reason `join_date_missing`, and the NULL branch is asserted to come **before** the comparison. `POST /api/admin/include-participant` accepts the new reason as well as `excluded_by_admin`, so it is not a state with no exit; `terminated` is still refused there, and reinstatement is still the only way back from that one.
- Deliberately NOT retroactive: no existing participants row was rewritten, so Cem Durukan's H1 row is untouched and the read-only trio stay in H1 scope (D-0821-4). The rule fires for the first time when H2 is created. `/admin/users` now shows «Нет даты приёма» as its own state for a person in scope with a NULL date, so the H1 residue is visible rather than inferred.
- Verification: `tests/prelaunchNightBatch.test.js` («item 2»); live `API: Manage Periods` `updatedAt=2026-08-25T19:47:02.586Z`. No period was created on live to exercise it — the next real exercise is H2.
- Source: `docs/MID_YEAR_HIRES_SCOPE_2026-08-25.md` §1.1, §1.3 and §5.1; owner-facing version in `docs/MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md` §3; fix in `docs/PRELAUNCH_BATCH_NIGHT_2026-08-26.md` §2.

### BUG-067: A person added after a period is created has no participants row, and leaves no trace in the closed period

- Status: 🔴 OPEN
- Severity: 🟡 Medium
- Location: LIVE `API: Manage Periods` → `Build Create SQL` (the only INSERT into `evaluation_period_participants`); `API: Admin Save User (GUI Mode)` and `src/components/admin/UserImportModal.jsx` (both write `users` only); `Build Close Dataset Query` (iterates the participants table).
- Description: participation rows are written exactly once, in the `CROSS JOIN users` of period creation. Nothing else ever inserts one. A person entered into `users` after that moment therefore has **no row** for the periods that already exist. Nobody is in this state on live today — all 89 people have a row on period 2 and on period 5, verified 2026-08-25 — but it is one ordinary `admin/save-user` call away, and the Excel import posts through the same route.
- Why it matters: the read surface treats "no row" exactly like "row with `is_in_scope=false`" — measured on a stand fixture, not inferred: absent from the manager's task list, `actor_is_in_scope=false` on their own read, absent from HR completion and its denominator, absent from `in_scope_count`, 403 on both submit routes, and emitted on the admin matrix as an out-of-scope row with empty cells. **The close is the exception.** `Build Close Dataset Query` builds its dataset by iterating `evaluation_period_participants` for the period, so a person with no row gets **no `period_results` row at all**, where an excluded person gets one saying «was a participant, out of scope, no data». Neither carries a number — the table's two CHECKs forbid it — so this is not money, it is evidence: a year later the closed period cannot be asked whether that person existed in it.
- How to fix: user creation should insert a participants row into every non-closed period, computed by the same rule period creation uses. Cheap in isolation; the reason it was not done is that `admin/save-user` is a full-row-overwrite route with `body.role || 'employee'` and `body.work_category || 'general'` defaults — the most dangerous write path in the system (BUG-061 was left open for the same reason).
- Not done here: `POST /api/admin/exclude-participant` (D-0825-10) deliberately **refuses** such a person by name — 404 `NOT_A_PARTICIPANT`, with a message saying they were entered after the period was created and are already out of scope — rather than inventing a participation row they never had. That is a refusal, not a fix.
- Source: `docs/MID_YEAR_HIRES_SCOPE_2026-08-25.md` §1.4 and §5.2.

### BUG-068: Score correction never checks period scope

- Status: 🔴 OPEN
- Severity: 🟢 Low
- Location: LIVE `API: Score Correction` → `Validate Input` / `Decide Level` (the SQL joins `users`, `criteria` and `evaluation_periods`, and never `evaluation_period_participants`).
- Description: the correction route checks the actor's role and ownership (`mid_level` = the subject's manager's manager, `c_level` for admin/c_level), the classification applicability of the criterion, and that a period is active **and started**. It does not check that the subject — or the actor — is in scope of that period. A correction row can therefore be written about somebody who is out of scope for any of the three reasons: `terminated` (D-0825-7), `hired_after_period_end`, or `excluded_by_admin` (D-0825-10).
- Why it matters: it cannot move money. At close, `Compute Close Results` starts from `let hasData = inScope && …`, so an out-of-scope person freezes with `has_data=false` and NULL money columns, and `period_results`' two CHECKs make a number impossible on such a row — the correction is simply never read. The cost is a row in `score_corrections` asserting a judgement about a person who is not in the period, which contradicts what every other write path enforces and what the admin screen implies.
- How to fix: join the participants row for subject and actor in `Validate Input`'s SQL, exactly as `API: Submit Evaluation` does, and return 403 when either is out of scope.
- Not done here: pre-existing since D-0820-9; neither introduced nor fixed by MID_YEAR_HIRES_SCOPE, whose boundary was additive-only and whose deploy asserts it writes no existing workflow. `score_corrections` is empty on live (0 rows), so nothing is wrong today.
- Source: `docs/MID_YEAR_HIRES_SCOPE_2026-08-25.md` §5.3.

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

### BUG-069: HR is told they have evaluation tasks and given no way to reach them

- Status: 🟢 CLOSED (2026-08-26)
- Severity: ⚠️ High
- Location: `src/components/Sidebar.jsx` — the `Личные` NavGroup was wrapped in `{!isHR(safeUser.role) && …}` and `showTaskPanel` was `!isHR(safeUser.role)`.
- Description: found by the day-one walkthrough on a stand with the gate pressed, logged in as a real HR account. Both HR people are in H1 scope with `can_be_evaluated=true`; `API: Submit Self Review` carries `required_roles: ["employee","manager","hr"]`; the Welcome page renders «Ваши задачи: Самооценка / Руководитель» for them. The sidebar showed exactly two links — «Статусы оценок» and «Сотрудники» — and the task panel was suppressed, so there was no route in the product to `/self-review` or `/manager-evaluation`. Both pages render and submit correctly when reached by URL; only the navigation was missing.
- Why it matters: on day one, 2 of 80 in-scope people are told they have tasks and cannot open them — and they are the two people the rest of the company will ask about the campaign. Not money: a self-review never feeds the bonus index (HANDOVER §4), and their manager is `c_level`, so the upward channel is closed to them by D-0825-6 anyway.
- Fix (2026-08-26): the personal group and the task panel render for every role, including `hr`. The HR panel group and the manager-only team group are unchanged. D-0825-15.
- Verification: `tests/prelaunchNightBatch.test.js` — «item 9: HR can reach the tasks the portal tells them they have»; browser walkthrough as `liya@sedamedical.com` on the night stand. Frontend release `20260825T194735Z`.

### BUG-070: The HR completion card counts two different populations and names neither

- Status: 🔴 OPEN
- Severity: 🔵 Low
- Location: LIVE `API: HR Evaluation Status`; rendered by `src/pages/HRDashboard.jsx`.
- Description: the four tiles on «Статусы оценок» read «Самооценки N из 81», «Оценили руководителя N из 81», «Оценили подчинённых N из 17» and «Полностью завершили N из 87» (numbers from the night stand, 2026-08-26). Three different denominators, none labelled. They are each defensible on their own — 81 is the people who owe a self-review, 17 the managers, 87 everybody in scope — but nothing on screen says so, and «Полностью завершили 5 из 87» sits beside «Самооценки 2 из 81» as though the two counted the same people.
- Why it matters: HR reads this screen to decide whether to chase somebody. A denominator that moves between tiles without explanation makes «завершили» unreadable, and the natural conclusion — «six people are missing from the self-review count» — is wrong.
- How to fix: label each tile with the population it counts, the way the `/admin/users` header was fixed under D-0825-8. Out of the PRELAUNCH_BATCH_NIGHT brief's scope (items 1–8 plus day-one breaks); this is a readability defect, not a break.
- Source: `docs/PRELAUNCH_BATCH_NIGHT_2026-08-26.md` §9.

### BUG-071: A criterion cell that cannot be filled is still emitted for the two heaviest criteria

- Status: 🔴 OPEN
- Severity: 🔵 Low
- Location: LIVE `API: evaluations-matrix` → `Build Matrix Query`; `src/utils/matrixUtils.js:canReceiveCLevel`.
- Description: applicability in the matrix is now filtered on two dimensions — `project_participants` against `is_project_participant`, and `managers_only` against `has_subordinates` (this session, in lockstep with the close dataset). The third is not filtered: criteria 1 «Стратегическая значимость роли» (weight 5.00) and 10 «Оценка C-Level и соответствие культуре» (weight 1.60) are `c_level_only`, and `canReceiveCLevel` refuses `role IN ('admin','c_level')` and anybody with `can_be_evaluated=false` — yet both columns are emitted for all five C-level people, who can never be scored on them.
- Why it matters: cosmetic today, and shrinking. Since this session the cells render «н/п» versus «-» from the client's own applicability map, so a blank column no longer reads as «behind schedule» for the two dimensions that ARE filtered; for these five rows it still does. Not fixed server-side on purpose: the natural predicate is `can_be_evaluated`, which the owner edits at will, and tying the matrix's emitted criteria set to a column that can flip mid-campaign would let one checkbox move a person's criteria count — and therefore their index — with no evaluation changing.
- How to fix: decide whether `c_level_only` applicability is a property of the person's role (stable) or of `can_be_evaluated` (editable), then filter on the stable one. Needs the owner.
- Source: `docs/PRELAUNCH_BATCH_NIGHT_2026-08-26.md` §6.

### BUG-072: Two C-level evaluations on one person, and the money read whichever was touched last

- Status: 🟢 CLOSED (2026-08-26)
- Severity: 🔴 High
- Location: LIVE `API: evaluations-matrix` → `Build Matrix Query` and `API: Manage Periods` → `Build Close Dataset Query`; the `'c_level_score'` sub-select in each.
- Description: `c_level_direct` is the only channel that feeds the bonus index on criteria 1 «Стратегическая значимость роли» (weight 5.00) and 10 «Оценка C-Level и соответствие культуре» (1.60), the heaviest pair in the catalogue, and **three** people hold the right to file it (Alexander id 2, Bayram id 18, Jemal id 47). Nothing was lost at write time — the unique index on `evaluations` is `(subject_id, evaluator_id, evaluation_source, period_id)`, so a second C-level person gets their own row and both rows persist — but both readers took `ORDER BY e.updated_at DESC LIMIT 1`, so the number that reached the screen, the payload and the frozen `period_results` was whichever evaluation was touched last. The upward channel next to it in the same query has averaged in SQL since it was written.
- Why it matters: money, and silently. Measured on a stand: two C-level evaluators scoring one person 8 and 4 on criterion 1 and 7 and 9 on criterion 10 froze `bonus_index` **124.8360** under the old code (the last writer's 4 and 9) against **132.8520** averaged — a 6.4 % swing on one person from a submission-order accident, with no screen anywhere showing that a second opinion existed.
- Fix (2026-08-26, D-0826-1): one grouped CTE, `c_level_direct_scores`, character-for-character identical in both workflows, produces `AVG` and `COUNT` in a single scan; the cell reads `ROUND(avg, 2)` and a new `c_level_count` travels beside it into the payload and onto every screen that shows the channel (matrix cell badge «×N», tooltips, employee modal, score-detail modal, Excel detail sheet). No schema change: `period_results` stores one row per person and a count is a property of one cell.
- Verification: `backups/2026-08-26-clevel-averaging/clevel_close_proof.json` — two copies of one dump, control on the workflow surface at HEAD and treatment on the working tree, each closed through its own real `POST /api/periods/close`, 29/29 checks. Round 1 (one evaluator): 832 frozen money cells, **zero moved**. Round 2 (two evaluators): exactly one person's row differs, in `final_rating` and `bonus_index` only, by exactly the hand figures; the other 103 rows byte-identical. `tests/clevelAveraging.test.js` (21 assertions); suite 401/401. Live: `docs/CLEVEL_AVERAGING_2026-08-26.md`.

### BUG-073: A C-level score correction on a C-level criterion is accepted, stored, and then ignored

- Status: 🟢 CLOSED (2026-08-26, PRELAUNCH_GATE — the route now refuses)
- Severity: 🟡 Medium
- Location: LIVE `API: Score Correction` → `Decide Level` (no `c_level_only` check); `src/utils/matrixUtils.js:getCriterionFinalScore` and the `finalOf` copy in `API: Manage Periods` → `Compute Close Results` (the `c_level_only` branch returns the channel value and never consults a correction).
- Description: `POST /api/admin/score-correction` validates the range and the project-participation dimension and nothing about `c_level_only`. Measured on a stand 2026-08-26: a correction of 3 on criterion 1 for a subject returned **200**, was stored (`score_corrections` id 10, level `c_level`), and reached the matrix payload as `c_level_correction: 3` on that cell — and the frozen `period_results` came back **132.8520**, byte-identical to the same close without the correction. The row is written, transported and discarded. Separately, `score_corrections` is unique on `(subject_id, criteria_id, correction_level, period_id)` with no evaluator in the key, so corrections are last-writer-wins across C-level people even where they do count.
- Why it matters: a calibration action that the API accepts with a 200 and that changes no number is worse than a refusal. Nobody can tell from the screen or the response that the correction did nothing. `score_corrections` is empty on live, so nothing is wrong today.
- How to fix: the owner decides what a `c_level` correction means against an averaged C-level score — replace the mean, or enter it as one more opinion in the mean — and the route then either implements it or refuses `c_level_only` criteria by name. Surfaced deliberately by D-0826-1 rather than resolved; see `docs/CLEVEL_AVERAGING_2026-08-26.md` §3 for both options costed.
- Source: `docs/CLEVEL_AVERAGING_2026-08-26.md` §3.
- Fix (2026-08-26, D-0826-3, PRELAUNCH_GATE): the owner chose the refusal. `Validate Input` now also fetches the `c_level_only` criteria ids, and `Decide Level` answers **422 `CRITERIA_NOT_APPLICABLE`** for any of them — before the period gate, mirroring the project-criterion refusal, so the rule is provable on live while no campaign runs. Corrections calibrate the manager channel; the C-level channel is calibrated by being averaged (D-0826-1). The evaluator-less unique key on `score_corrections` (last-writer-wins across C-level people on the criteria where corrections DO count) is narrowed but **not** part of this fix and stays recorded here.
- Verification: `backups/2026-08-26-prelaunch-gate/` — `gate_drive_proof.json` (criteria 1 and 10 → 422 on the treatment stand, both before and after the gate press; criterion-3 corrections still 200; project 422 and ownership 403 unchanged; BUG-068 behaviour unchanged) and `gate_close_proof.json` (control at HEAD with the correction stored vs treatment with it refused: **all 100 frozen `period_results` rows identical** — the refusal moves no money). Live after deploy (`gate_live_verify.json`, 20/20): criteria 1/10 → 422 through Caddy, criterion 3 → 409 at the unpressed gate, `score_corrections` still 0. `tests/clevelAveraging.test.js` pin inverted; suite 401/401. Report: `docs/PRELAUNCH_GATE_2026-08-26.md`.

### BUG-074: The submit routes accept criteria that do not belong to the channel, and the score pollutes the archival ratings

- Status: 🔴 OPEN
- Severity: 🟡 Medium
- Location: LIVE `API: Submit Evaluation` → `Build Insert SQL` (grades are validated for range and for the project dimension only; the insert's `calculated_score` is `AVG(score_val)` over **every** submitted row); same shape on the additive path and on `API: Update Evaluation WITH PERIOD`.
- Description: a hand-crafted request can attach any active criterion to any channel. Measured on the gate stand 2026-08-26: a manager submit carrying criterion 1 (`c_level_only`) among ordinary grades → **200**, the row stored; a manager submit for a no-reports subject carrying criterion 2 (`managers_only`) → **200**; an upward submit carrying criterion 3 → **200**; a `c_level_direct` submit carrying criterion 3 → **200**. Every reader of per-criterion cells filters these rows out (`c.c_level_only = false` on the manager cell, the `managers_only`/`project` emission predicates, the c_level CTE's `c_level_only = true`), so **no money number moves** — proven by the close: the frozen `bonus_index` figures equal the hand arithmetic that ignores the smuggled rows. But `calculated_score` is the average of *all* submitted rows, and the archival ratings are averages of `calculated_score`: the polluted fixtures froze `rating_manager` **8.29** where the honest figure is 8.17, and **7.50** where the honest figure is 6.00.
- Why it matters: the ratings are the feedback surface (formula 1) and September's calibration reads them. The UI forms never submit an inapplicable criterion, so this needs a hand-made request by an authenticated manager / C-level — low likelihood, but the write path is the last line the project's own doctrine (D-0822-3 applicability "on every write path") says should hold, and on this dimension it does not.
- How to fix: extend the existing applicability check in `Build Insert SQL` (and the additive/update/self paths) to the audience and channel dimensions: manager/upward submits refuse `c_level_only` criteria; `managers_only` criteria require the subject's `has_subordinates`; `c_level_direct` submits accept only `c_level_only` criteria. Same 422 `CRITERIA_NOT_APPLICABLE` shape as the project dimension.
- Source: `docs/PRELAUNCH_GATE_2026-08-26.md` §3 (gate stand, `gate_drive_proof.json`, `gate_close_proof.json`).

### BUG-075: The close path silently applies grade coefficient 1.00 to a person with no grade — and the coefficient snapshot's note claims the opposite

- Status: 🔴 OPEN
- Severity: 🟢 Low (latent: today every no-grade person on live also has `can_be_evaluated=false`, so no such row can acquire data)
- Location: LIVE `API: Manage Periods` → `Compute Close Results` (`const gradeCoefficient = Number(row.grade_coefficient) || 1.0`); the same `|| 1.0` on the client (`useFinalScoresMatrix`); `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md` §3's closing sentence.
- Description: measured on the gate stand 2026-08-26: an evaluable employee with `grade_id NULL` (fixture GT NoGrade) was evaluated normally and the close froze `bonus_index` **102.9200** = Σ(score × level coef × weight) × **1.00** — the fallback applied, silently, in the frozen record. The screen at least marks the row («без грейда (×1.00)», D-13 of PRELAUNCH_BATCH_NIGHT), but the snapshot document says «A person with no grade is **not** given 1.00 silently on the close path», which is the opposite of what the close does. The self-review path genuinely refuses (`NO_GRADE_COEFFICIENT` 422, re-measured on the same stand); the close does not.
- Why it matters: a grade is a money input worth ×0.30…×3.00. If the owner ever grants `can_be_evaluated` to a person without assigning a grade (one `admin/save-user` edit), their index freezes at a coefficient nobody chose, and the closed period cannot be recomputed. Today unreachable on live: the only three no-grade people (21, 40, 61) are the read-only trio.
- How to fix: either the close refuses to run while an in-scope evaluable participant has no grade (a named 422 listing the people — the BUG-030 doctrine), or the frozen row for such a person carries NULL money like the no-data case. And one sentence in the snapshot doc corrected to match the code.
- Source: `docs/PRELAUNCH_GATE_2026-08-26.md` §3 (gate stand, `gate_close_proof.json` — frozen `1705.bonus_index = 102.9200`).

### BUG-076: Admin employee roster recomputes the full period list once per user
- Status: 🔴 OPEN
- Severity: 🔵 Low (performance)
- Location: LIVE `API: Admin Get Users Data` → `Build Users Query`, correlated `period_scopes` subquery.
- Description: the new employee-card participation controls need every period by name, so the roster query builds a JSON period list for each user through a correlated subquery. At the current 89 users × 3 periods this is small and the browser walkthrough is responsive, but work grows as users × periods rather than scanning and grouping once.
- Why it matters: not an H1 correctness defect. It becomes page latency on a larger employee or period history and makes the whole admin roster wait before one card can open.
- How to fix: pre-aggregate `(user_id, period_scopes)` in one CTE or `LEFT JOIN LATERAL`, then join it to users; preserve rows with no participant entry and periods with no active status.
- Source: `docs/HIRE_DATE_AND_SCOPE_TOGGLE_2026-08-26.md` §8, post-build code review.

### BUG-077: The tracked generator-output snapshots are stale (subdirectory instance of the BUG-045 family)
- Status: 🔴 OPEN
- Severity: 🔵 Low (repo hygiene — live is unaffected; the generators, which are the deploy source, are current)
- Location: `n8n_workflows/route_guard_h1/` and `n8n_workflows/route_guard_deferred/` — tracked snapshots of the builders' output.
- Description: regenerating both directories at HEAD (2026-08-26, ROLE_ACCESS_HR_CLEVEL) showed `route_guard_deferred/evaluations-matrix.json`, `route_guard_h1/manage-periods.json` and `route_guard_h1/save-user.json` stale against their own generators — the 2026-08-26 05:16Z/08:52Z rewrites refreshed the top-level `API_ *.json` exports but not these snapshots — and `manage-employment.json` / `manage-period-scope.json` were never committed at all. The ROLE_ACCESS commit regenerated only its own four files and reverted the other three rather than adopt unrelated churn.
- Why it matters: a snapshot that silently lags its generator is the BUG-045 trap one directory deeper — anyone diffing the tracked JSON to answer "what does this route require" reads yesterday's guard.
- How to fix: regenerate both directories in a hygiene commit of their own (canonical ids `VNbfkY8IKbEzn88B` / `L0Zr7nVa8O5YWXd3`), add the two missing files, and decide whether a test should pin snapshots == generators (the deferred/h1 test suites already regenerate to a temp dir, so the tracked copies may instead be deleted as redundant — owner's call).
- Source: `docs/ROLE_ACCESS_HR_CLEVEL_2026-08-26.md` §4.4.
