# Bug Tracker

## Statistics
| Status | Count |
|--------|-------|
| 🔴 Open | 22 |
| 🟡 In Progress | 0 |
| 🟢 Closed | 27 |

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

## 📌 Medium

### BUG-009: Employee profile and history still have no period filter
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `n8n_workflows/route_guard_h1/my-profile.json`, `evaluation-history.json`.
- Description: Both JOIN `evaluation_periods` for the name only. They do not restrict rows to the active period. `check-self-review`, `check-evaluated`, and `get-my-manager` already bind to `is_active AND status='active'` — `docs/REPORTING_SURFACE_2026-08-2x.md` listed those three as still unbound; that is false in the live generator JSON.
- Why it matters: harmless while `epe_2026` has one campaign period. After H2 exists, profile/history will mix cycles.
- Fix: bind both queries the same way check-* already do. Schedule with persist-period-results after launch.

### BUG-012: `/team` calls an admin-only API
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `src/pages/TeamView.jsx` → `useUsers` → `GET /api/admin-users-data`; route is `ManagerRoute`.
- Description: The page is shown to managers. The API guard is admin-only. Managers get an empty/error list. Pre-existing; reporting-surface brief hid dossier buttons but did not change the list endpoint.
- Why it matters: the “Список команды” item in the sidebar does not work for a manager.
- Fix: either point the list at a manager-scoped employees read, or hide `/team` from managers until that exists.
- H1 impact: managers use `/dashboard` for campaign tasks. `/team` is the leftover.

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
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `src/pages/AdminUsers.jsx:103` and `:127` call `setLoadingStatuses(true/false)`; no `useState` declares it anywhere in the file or the repo.
- Description: the status-loading effect throws `ReferenceError` on its first line inside the `try`, is swallowed by the `catch`, and then throws again in the `finally` — an unhandled rejection. `selfReviewsStatus` and `evaluationStatuses` are never populated, so the evaluation-status circles stay empty for every row.
- Why it matters: the classification pass Alexander runs on this screen still works (the circles are not classification), but the screen silently reports that nobody has done anything, and the console carries an unhandled rejection on every list load.
- Fix: declare the state, or delete both calls.
- Source: §6 of `docs/ADMIN_USERS_SORT_2026-08-2x.md`, confirmed in the working tree 2026-08-21.

### BUG-036: Copy that contradicts behaviour, including a button that can only 409
- Status: 🔴 OPEN
- Severity: 📌 Medium
- Location: `src/components/SelfReviewStatusCard.jsx` («Оценить новые критерии») against `API: Submit Self Review`, which ignores `is_update`; plus `src/pages/Welcome.jsx`, `src/components/SessionExpiryWarning.jsx`, `src/pages/Login.jsx`, `src/pages/ManagerEvaluation.jsx`.
- Description: rows 2, 3, 7, 8, 9 and 10 of the §4.8 copy-vs-behaviour table are still open after the 20 Aug fixes closed rows 1 and 5. The functional one is row 7: «Оценить новые критерии» is rendered, is clickable, and **always** returns 409. The rest are false or incomplete statements — «Все данные видят только C-level менеджеры» (admin, HR statuses and `/team-scores` also see data); «Критерий для оценки руководителя» used as if it were the criterion's name (it is `Качество управления и развитие команды`); «Руководитель не назначен» shown to C-level who correctly have none; the draft notice not saying the draft is browser-local and expires in 7 days; the login placeholder `name@company.com` when registration requires `@sedamedical.com`.
- Why it matters: a button that cannot succeed trains people to distrust the product on their first real task, and a confidentiality promise that is broader than the implementation is the kind of statement an employee will test.
- Fix: either remove the button or implement `is_update`; correct the five copy strings. Neither needs a workflow change except row 7.
- Source: §4.8 of `docs/USER_FACING_COPY_2026-08-2x.md`; re-checked in the §4.8 table of `docs/PRELAUNCH_FIXES_2026-08-2x.md`.

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
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/App.jsx` path `/admin` → `AdminRoute` → `AdminSettings`; `canAccessAdminPanel` includes `hr`.
- Description: Sidebar hides «Критерии» from HR. A typed URL opens the criteria catalogue shell. The API is admin-only (403). Company-wide numbers are not returned.
- Why it matters: HR sees a frozen/error catalogue, not results. Reporting-surface brief left this on purpose.
- Fix: wrap `/admin` in an admin-only route, or keep as-is.

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
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/utils/errorHandler.js:30-40`.
- Description: the interceptor replaces the server's message for 401, 403 and 429 with fixed Russian strings. `CAPABILITY_FORBIDDEN` therefore reaches the user as the generic «Доступ запрещен. Недостаточно прав». The 20 Aug Russian-message pass covered 400/404/409/422 only, and the workflow strings behind these three codes are still English underneath.
- Why it matters: the read-only C-level trio hitting the correction gate, and any non-admin clicking a `/admin/periods` control, get a message that does not say what actually happened.
- Fix: surface the server's `message` when present; keep the fixed string as the fallback.
- Source: leftovers of `docs/PRELAUNCH_FIXES_2026-08-2x.md`.

### BUG-037: «Создать период» is still rendered for c_level and HR
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `src/pages/AdminPeriods.jsx:393-399` — the header button has no `canManage` gate; rename, reparent, activate and close all do (`:71`, `:557`, `:567`, `:582`, `:604`).
- Description: `/admin/periods` is wrapped in `AdminRoute`, which admits admin, c_level and hr. The 21 Aug hardening gated the four controls the brief named; the create button was outside that list. The server answers 403 (`POST api/periods/create` is admin-only), so this is presentation, not access.
- Why it matters: same family as [BUG-013] — a non-admin is shown a write control and learns it is forbidden only by clicking it.
- Fix: put the button behind the same `canManage`.
- Source: §2 "boundary kept" of `docs/POSTVERIFY_BATCH_2026-08-2x.md`, which names it explicitly as left open for Alexander's decision.

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

- Status: 🔴 OPEN
- Severity: 📌 Medium (admin-only screen since 2026-08-22, and the number is a what-if rather than a payout — but it is the same silent-degradation shape as [BUG-030])
- Location: `src/hooks/useScoreCalculation.js:79-80` — `apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS).catch(() => ({ data: { data: [] } }))` and `apiClient.get(API_ENDPOINTS.ADMIN_USERS_DATA).catch(() => ({ data: { options: { grades: [] } } }))`, consumed by `src/pages/AdminScoreCalculator.jsx` (`/admin/score-calculator`).
- Description: the money screens were fixed on 2026-08-21 ([BUG-030]) by moving `useFinalScoresMatrix` to `Promise.allSettled` with an explicit error card, and `useScoreCoefficients` got the same treatment on 2026-08-22. The score calculator was in neither pass: a 401, a 500 or a network blip on either call still resolves to an empty array, `weight` falls back to `1.0` per criterion and every grade coefficient to `1.0`, and the calculator renders a full, plausible, **unweighted** breakdown with no error — including the per-criterion `оценка×коэффициент×вес` strings, which will read `×1.0×1.0`.
- Why it matters: it is a calibration tool. A C-level or admin comparing "what if this person scored 8 instead of 6" gets an answer computed without the weights that decide the actual bonus share, and nothing on screen says so.
- Repro: open `/admin/score-calculator` with `GET /api/score-coefficients` failing (revoke the session between the matrix call and the coefficients call, or block the route). The table renders; every weight shows 1.0.
- How to fix: the [BUG-030] pattern — `Promise.allSettled`, classify each rejection, clear `employees`/`matrixData`/`criteriaWithCoefficients`, and return an error card with retry before any table renders. `src/hooks/useScoreCoefficients.js` (2026-08-22) is the smaller worked example.
- H1 impact: none while nobody uses the calculator; it reads the active period, and there is none today.
- Source: found while making the coefficient screens admin-only in `docs/LIFECYCLE_COEFF_2026-08-2x.md`; the same `.catch`-to-empty family the brief was asked to close in `useScoreCoefficients` only.

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
- Status: 🔴 OPEN
- Severity: 📝 Low
- Location: `scripts/deploy_epe_frontend.sh` — the two safety gates (refuse if a legacy `:5678` URL remains; refuse if the `/webhook` base is absent) call `rg`.
- Description: ripgrep is not installed on the delivery laptop, so the deploy refuses. On 2026-08-21 the gates were run by hand and the script re-run with a shell shim mapping `rg -q` to `grep -rqE`; gate semantics were preserved, not bypassed.
- Why it matters: failing closed is correct, but the workaround is manual and undocumented at the point of use, which is exactly where a rushed deploy skips it.
- Fix: install ripgrep, or fall back to `grep -rqE` inside the script when `rg` is absent.
- Source: `docs/POSTVERIFY_BATCH_2026-08-2x.md` live-deploy note.

---

### BUG-028: Stale top-level workflow export (evaluations-matrix)
- Status: 🔴 OPEN
- Severity: 🟢 Low
- Location: `n8n_workflows/API_ evaluations-matrix.json`
- Description: The top-level export is the pre-guard, pre-period-binding 4-node workflow. Live runs the generated version (`scripts/build_route_guard_deferred.py` → `route_guard_deferred/evaluations-matrix.json`). Anything importing or trusting the top-level file gets an unguarded, all-periods-mixed matrix — it cost the 2026-08-21 throwaway stand one debug cycle.
- Why it matters: A future session or stand that seeds from the stale export silently reintroduces an unauthenticated period-mixing matrix.
- How to fix: Refresh top-level exports from live after each PUT (deploy_periods_hierarchy.py already does this for Manage Periods), or drop top-level duplicates of generator-owned workflows keeping only the id-bearing metadata.

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

- Status: 🔴 OPEN
- Severity: 📝 Low (report-accuracy; the deployed corrections behaviour itself is exactly as claimed and approved — only one of the three justification sentences is wrong, and the disclosure it waves away is real but marginal)
- Location: `docs/FINALIZE_PRELAUNCH_2026-08-2x.md` §1 "Ordering decision, surfaced", the sentence "the deployed submit path already answers applicability before its relation checks, so this leaks nothing submit does not".
- Description: the deployed `API: Submit Evaluation` → `Build Insert SQL` answers `SCOPE_MISMATCH` 403 (one lookup bundling the actor–subject relation and active-period scope), `PERIOD_NOT_STARTED` 409 and `CANNOT_EVALUATE` 403 **before** its applicability 422 — read from live `workflow_entity` 2026-08-24 (byte-identical to the generator). Submit therefore never reveals applicability while the launch is paused (it answers `SCOPE_MISMATCH` first), whereas the corrections route now answers 422 `CRITERIA_NOT_APPLICABLE` before its period gate — so any role-gated writer (admin / c_level / any manager) can distinguish a subject's current project/general classification for **any** subject id by probing criterion 8, on paused live and mid-campaign pre-ownership.
- Why it matters: DECISIONS/report accuracy is the §6.11 wrong-premise class — a future session citing the sentence would believe the ordering introduces no new information surface. The disclosure itself is minor (classification is visible to admin/c_level on every matrix, and to a manager for their own span), but it is real, was traded deliberately for live provability, and should be recorded as a cost, not denied.
- How to fix: correct the §1 sentence (and mirror the nuance in the D-0822-3 extension note): the refusal is non-mutating and keeps the rule provable on paused live — those two reasons stand — at the cost of a marginal classification probe that submit does not offer. Alternatively reorder the check behind the period gate and accept byte-identity-only deploy verification; that trade-off is Alexander's to re-make, not an executor's.
- Source: verification gate `docs/GATE_FINALIZE_2026-08-2x.md` §2, deployed submit order vs report text.

### BUG-049: Migration 006 does not reproduce live's `score_corrections` constraints (criteria FK typo'd to `users`, CASCADE vs live NO ACTION); `schema.sql` predates the table

- Status: 🔴 OPEN
- Severity: 📝 Low (no live impact — stands restore from live dumps; wrong only for a from-migrations rebuild)
- Location: `migrations/006_add_hierarchical_corrections.sql` (`score_corrections_criteria_id_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.users(id) ON DELETE CASCADE` — criteria FK pointing at **users**, and `ON DELETE CASCADE` on subject/evaluator/criteria); `schema.sql` (no `score_corrections` table at all).
- Description: live `epe_2026` (pg_constraint, read 2026-08-24) has `score_corrections_criteria_fkey FOREIGN KEY (criteria_id) REFERENCES performance_db.criteria(id)` and plain `NO ACTION` on all of subject/evaluator/criteria/period FKs. The migration as written would create a criteria FK that only accepts criterion ids that happen to be user ids, and CASCADE deletes that would silently destroy correction history when a user or criterion is removed. Live was evidently built/repaired by another path; the repo's DDL record does not say so anywhere.
- Why it matters: the repo is the memory (§9 HANDOVER). The H2 rewrite, or any stand built from `schema.sql` + `migrations/001…014` instead of a live dump, inherits materially different — and data-destroying — constraints, and the gate that catches it would blame the wrong layer. Live's `NO ACTION` FKs are also what makes the Manage Criteria hard-delete safe (FK-blocked once data references a criterion) — a from-migrations rebuild loses that protection.
- How to fix: a reconcile migration (or a corrective note in 006) stating the live constraint set verbatim, plus a regenerated `schema.sql` snapshot at rewrite time; cheapest correct fix is a new migration `015_reconcile_score_corrections_constraints.sql` that drops-if-exists the typo'd FK and recreates the live set idempotently.
- Source: verification gate `docs/GATE_FINALIZE_2026-08-2x.md` §6 (FK check behind the criterion-delete adversarial question).

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
