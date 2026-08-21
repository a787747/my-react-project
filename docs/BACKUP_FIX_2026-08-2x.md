# Daily backup of the live database — BUG-032

**Date of work:** 2026-08-21 · **Scope:** host backup schedule only.
**Boundaries held:** the 2025 archive job (`backup-performance-db.sh`, cron `0 3 * * *`) was not edited and its
10 dumps were not touched; no write to `epe_2026`; no workflow PUT / activate / deactivate; no deploy; no mail.
Two throwaway databases were created for the restore proof and both were dropped.

---

## 1. What was wrong

`crontab -l` held exactly one line. `/root/backups/epe/backup-performance-db.sh` runs

```
docker exec postgres_n8n pg_dump -U admin -d postgres -n performance_db --no-owner --no-acl -Fc
```

`-d postgres -n performance_db` is the **read-only 2025 archive**. Proven from the dump's own table of
contents rather than from the command line — `pg_restore -l` on `performance_db_2026-08-21T0000Z.dump.gz`
lists **12** tables, all of them archive tables. The live campaign database `epe_2026` has **17** tables;
five of them (`auth_sessions`, `auth_login_attempts`, `evaluation_period_participants`,
`password_reset_tokens`, `period_results`) do not exist in the archive at all and appear in no dump.

Second, larger gap, not named in BUG-032: the same `postgres` database also carries the **n8n application
schema** `public` — 58 workflows, 7 credentials, 8 settings rows, 41 registered webhooks. The archive job
dumps `-n performance_db` **only**, so `public` was covered by nothing either.

**Answer to the question the brief asked explicitly: no. Before today the n8n application database was
backed up by nothing** — no cron line, no systemd timer (`systemctl list-timers` has 15, none related),
no `/etc/cron.d` entry, and no container volume to snapshot: `docker inspect n8n-n8n-1` shows **zero
mounts**. Every workflow, credential and setting existed in exactly one place, `postgres.public`.

---

## 2. The schedule as installed

```
0 3 * * * /root/backups/epe/backup-performance-db.sh     <- pre-existing, untouched
20 3 * * * /root/backups/epe/backup-epe-live.sh          <- installed by this brief
```

Host timezone is `Europe/Moscow`, so 03:20 MSK = **00:20 UTC**, twenty minutes after the archive job, so the
two never contend for the same `pg_dump`. `backup-performance-db.sh` is byte-identical before and after this
session — md5 `a9f748541cad6379d8949ce91dab51e0`.

`/root/backups/epe/backup-epe-live.sh` (md5 `d5953e90a1701de77f1261e523c135be`, mode `700`) writes two dumps
into the same `daily/` directory as the archive job:

| Target | Command | Output stem |
|---|---|---|
| Live campaign DB, all schemas | `pg_dump -U admin -d epe_2026 --no-owner --no-acl -Fc` | `epe_2026_<stamp>.dump.gz` |
| n8n application schema | `pg_dump -U admin -d postgres -n public --no-owner --no-acl -Fc` | `n8n_app_<stamp>.dump.gz` |

`-n public` rather than the whole `postgres` database on purpose: the archive job already owns
`-n performance_db` in that database. The two jobs together cover **every schema of both databases** with no
overlap and no duplicated bytes.

**Pruning is stem-scoped.** Each job's `find … -mtime +14 -delete` is keyed on its own filename stem, so the
new job can never delete a `performance_db_*` file and the archive job can never delete an `epe_2026_*` or
`n8n_app_*` one. Same 14-day window, same `-Fc | gzip -9`, same `chmod 600`, same minimum-size check, same
append-only `backup.log` as the archive job — deliberately the same discipline, not a new one.

The scripts are now version-controlled: `scripts/backup-epe-live.sh` and `scripts/verify-restore.sh` are
byte-identical copies of the host files (md5s match). The host copies remain authoritative.

---

## 3. Proof that the **scheduled entry point** works, not just a manual run

A manual run proves nothing about cron: cron gives the job a minimal `PATH` and no login shell. So the
installed entry point was fired **by cron itself**. A one-shot line with a command string byte-identical to
the daily line was added, allowed to fire, and then removed.

`/var/log/syslog`:

```
Aug 21 14:45:01 3569961-foreignpay CRON[542920]: (root) CMD (/root/backups/epe/backup-epe-live.sh)
```

`backup.log`, that run:

```
[2026-08-21T11:45:01Z] start /root/backups/epe/daily/epe_2026_2026-08-21T1145Z.dump.gz
[2026-08-21T11:45:01Z] ok epe_2026 size=23924 retained=1 pruned=1
[2026-08-21T11:45:01Z] start /root/backups/epe/daily/n8n_app_2026-08-21T1145Z.dump.gz
[2026-08-21T11:45:01Z] ok n8n_app size=363476 retained=1 pruned=1
[2026-08-21T11:45:01Z] ok epe-live all targets stamp=2026-08-21T1145Z
```

Both restore proofs below use **those two files** — the ones cron produced, not ones typed by hand. The
one-shot line was then removed; the final `crontab -l` is the two lines in §2.

---

## 4. Restore proof — row counts, throwaway vs live

`/root/backups/epe/verify-restore.sh` gunzips the newest dump of a stem, `createdb`s a throwaway,
`pg_restore --exit-on-error`, counts **every** table on both sides, prints the comparison, then drops the
throwaway. The throwaway name always begins `epe_bkverify_` and the drop refuses any name that does not —
the same load-bearing-prefix rule the stand scripts use, so `epe_2026` can never be a drop candidate.

### 4.1 `epe_2026` — source `epe_2026_2026-08-21T1145Z.dump.gz` (23 924 B), throwaway `epe_bkverify_epe_2026_20260821_114620`

`pg_restore` exit **0** with `--exit-on-error`.

| Table | Restored | Live | |
|---|---:|---:|---|
| `performance_db.auth_login_attempts` | 2 | 2 | MATCH |
| `performance_db.auth_sessions` | 6 | 6 | MATCH |
| `performance_db.criteria` | 8 | 8 | MATCH |
| `performance_db.departments` | 18 | 18 | MATCH |
| `performance_db.email_verification_codes` | 0 | 0 | MATCH |
| `performance_db.evaluation_period_participants` | 178 | 178 | MATCH |
| `performance_db.evaluation_periods` | 3 | 3 | MATCH |
| `performance_db.evaluations` | 0 | 0 | MATCH |
| `performance_db.evaluation_scores` | 0 | 0 | MATCH |
| `performance_db.global_settings` | 0 | 0 | MATCH |
| `performance_db.grades` | 11 | 11 | MATCH |
| `performance_db.invite_tokens` | 2 | 2 | MATCH |
| `performance_db.password_reset_tokens` | 2 | 2 | MATCH |
| `performance_db.period_results` | 0 | 0 | MATCH |
| `performance_db.score_coefficients` | 80 | 80 | MATCH |
| `performance_db.score_corrections` | 0 | 0 | MATCH |
| `performance_db.users` | 89 | 89 | MATCH |

**TABLES=17 MISMATCHES=0.** Throwaway dropped.

### 4.2 n8n application schema — source `n8n_app_2026-08-21T1145Z.dump.gz` (363 476 B), throwaway `epe_bkverify_n8n_app_20260821_114608`

`pg_restore` exit **0** with `--exit-on-error`.

| Table | Restored | Live | | Table | Restored | Live | |
|---|---:|---:|---|---|---:|---:|---|
| `annotation_tag_entity` | 0 | 0 | MATCH | `oauth_access_tokens` | 0 | 0 | MATCH |
| `auth_identity` | 0 | 0 | MATCH | `oauth_authorization_codes` | 0 | 0 | MATCH |
| `auth_provider_sync_history` | 0 | 0 | MATCH | `oauth_clients` | 0 | 0 | MATCH |
| `chat_hub_agents` | 0 | 0 | MATCH | `oauth_refresh_tokens` | 0 | 0 | MATCH |
| `chat_hub_messages` | 0 | 0 | MATCH | `oauth_user_consents` | 0 | 0 | MATCH |
| `chat_hub_sessions` | 0 | 0 | MATCH | `processed_data` | 0 | 0 | MATCH |
| **`credentials_entity`** | **7** | **7** | MATCH | `project` | 1 | 1 | MATCH |
| `data_table` | 0 | 0 | MATCH | `project_relation` | 1 | 1 | MATCH |
| `data_table_column` | 0 | 0 | MATCH | `role` | 11 | 11 | MATCH |
| `equipment` | 0 | 0 | MATCH | `role_scope` | 369 | 369 | MATCH |
| `event_destinations` | 0 | 0 | MATCH | `scope` | 158 | 158 | MATCH |
| `execution_annotations` | 0 | 0 | MATCH | **`settings`** | **8** | **8** | MATCH |
| `execution_annotation_tags` | 0 | 0 | MATCH | `shared_credentials` | 7 | 7 | MATCH |
| `execution_data` | 124 | 124 | MATCH | `shared_workflow` | 58 | 58 | MATCH |
| `execution_entity` | 124 | 124 | MATCH | `tag_entity` | 0 | 0 | MATCH |
| `execution_metadata` | 0 | 0 | MATCH | `test_case_execution` | 0 | 0 | MATCH |
| `folder` | 1 | 1 | MATCH | `test_run` | 0 | 0 | MATCH |
| `folder_tag` | 0 | 0 | MATCH | `user` | 1 | 1 | MATCH |
| `insights_by_period` | 1414 | 1414 | MATCH | `user_api_keys` | 3 | 3 | MATCH |
| `insights_metadata` | 44 | 44 | MATCH | `user_requests` | 3 | 3 | MATCH |
| `insights_raw` | 0 | 0 | MATCH | `variables` | 0 | 0 | MATCH |
| `installed_nodes` | 0 | 0 | MATCH | **`webhook_entity`** | **41** | **41** | MATCH |
| `installed_packages` | 0 | 0 | MATCH | `workflow_dependency` | 0 | 0 | MATCH |
| `invalid_auth_token` | 0 | 0 | MATCH | **`workflow_entity`** | **58** | **58** | MATCH |
| `migrations` | 116 | 116 | MATCH | `workflow_history` | 60 | 60 | MATCH |
| | | | | `workflows_tags` | 0 | 0 | MATCH |
| | | | | `workflow_statistics` | 147 | 147 | MATCH |

**TABLES=52 MISMATCHES=0.** Throwaway dropped. `workflow_entity` 58 and `webhook_entity` 41 are the live
counts in `docs/HANDOVER.md` §2, measured independently this morning.

After both proofs, `pg_database` on `postgres_n8n` holds `epe_2026`, `postgres`, `template0`, `template1` —
nothing left behind.

**One caveat on the n8n dump, and it is not cosmetic.** `credentials_entity.data` is encrypted with
`N8N_ENCRYPTION_KEY`, which is set as a container environment variable in the Portainer stack and lives in
**no file this job backs up**. The 7 credential rows restore, but a restore into an n8n started with a
different key yields 7 unusable credentials. Row counts prove the data survives; they do not prove the
credentials are usable. Keeping that key recoverable is a separate item — see §8.

---

## 5. Retention proof — the prune actually fires

The archive job's 14-day prune has **never run**: every one of its 10 log lines reads `pruned=0`, because its
oldest dump is 2026-08-12, nine days old. "Pruning proven" was proven for the new job, on purpose.

Two decoy files were planted with the two new stems and an mtime of 2026-08-01 (20 days old):

```
-rw------- 1 root root 22 2026-08-01 00:00 epe_2026_2026-08-01T0000Z.dump.gz
-rw------- 1 root root 22 2026-08-01 00:00 n8n_app_2026-08-01T0000Z.dump.gz
```

Both matched `find … -mtime +14` before the run. The **cron-fired** run of §3 logged `pruned=1` for each stem
and `retained=1` for each — and afterwards no `2026-08-01` file remains. The 10 `performance_db_*` files were
still 10 after the run, which is the stem-scoping working: the new job walked the same directory and deleted
nothing of the archive job's.

---

## 6. Failure visibility

There is **no MTA on this host** (`sendmail`, `mail`, `mailx` all absent), so cron discards job output and
cron mail is not an alarm channel. The trace has to be on disk.

`backup-epe-live.sh` sets `set -Eeuo pipefail` with an `ERR` trap. Any failure: removes the partial dump,
appends a `FAIL` line to `backup.log`, writes `FAIL <ts> <reason>` to
`/root/backups/epe/backup-epe-live.status`, prints to stderr, and **exits 1**. A successful run overwrites the
status file with `OK <ts> stamp=<stamp>`.

Proven, not asserted — the real script was run against a container that does not exist
(`PGC=postgres_no_such_container`, an override that exists solely so the failure path is testable; cron passes
no environment, so the scheduled run always uses `postgres_n8n`):

```
$ PGC=postgres_no_such_container /root/backups/epe/backup-epe-live.sh
epe-live backup FAILED: epe_2026 pg_dump failed
EXIT=1

backup.log:
[2026-08-21T11:42:12Z] start /root/backups/epe/daily/epe_2026_2026-08-21T1142Z.dump.gz
Error response from daemon: No such container: postgres_no_such_container
[2026-08-21T11:42:12Z] FAIL epe-live epe_2026 pg_dump failed

status file:
FAIL 2026-08-21T11:42:12Z epe_2026 pg_dump failed
```

`pg_dump`'s own stderr is captured into the log, so the FAIL line is accompanied by the actual cause. No
partial `epe_2026_…1142Z` file was left in `daily/`. The status file is now `OK 2026-08-21T11:45:01Z
stamp=2026-08-21T1145Z`, set by the cron-fired run.

**The one-line health check:** `cat /root/backups/epe/backup-epe-live.status` — if it does not start with `OK`
and today's date, the backup did not run.

Honest limit: this is a *pull* check. Nothing pages anyone. If the host is down or cron is not running at all,
the status file simply stops changing and no one is told. Turning that into a push alert needs an off-host
observer, which is the same missing piece as BUG-014.

---

## 7. Disk headroom

| Measure | Value |
|---|---|
| `/` (`/dev/vda1`) | 50 GB total, **16 GB used, 34 GB available, 33 %** |
| Inodes | 408 102 used of 3 276 800, **13 %** |
| `epe_2026` database | 9 091 kB → dump 23 924 B |
| `postgres` database | 15 MB → `public` dump 363 476 B |
| Archive dump | ~34.5 kB |
| **New bytes per day** | 23 924 + 363 476 = **387 400 B (≈ 378 kB)** |
| **New 14-day steady state** | ≈ **5.3 MB** (all three stems together ≈ 5.8 MB) |
| Headroom ratio | 34 GB free ÷ 5.8 MB ≈ **5 800×** |

`epe_2026` barely grows: last year's full campaign — 234 evaluations, 644 scores — compresses to a 34 kB
dump, so H1 adds tens of kilobytes, not megabytes. The variable term is n8n's `execution_data`, currently
1 104 kB for 124 executions; every guarded API call during H1 creates an execution. Even at **100×** today's
execution volume the 14-day set stays under ~600 MB, i.e. under 2 % of free space. n8n is 1.121.3 with no
`EXECUTIONS_DATA_PRUNE*` environment override, so its default execution pruning applies; the oldest execution
on record is 9 days old, which is consistent with the 14-day default — but I did not force a prune to prove
n8n's own retention, so treat that as observed, not verified.

Conclusion: headroom is not a constraint, now or after H1.

---

## 8. What is and is not covered after this brief

**Covered — daily, on-host, 14 days, restore-proven today:**

| What | Job | File stem |
|---|---|---|
| `epe_2026`, all 17 tables — users, password hashes, H1 participant scope, periods, criteria, coefficients, and every evaluation the campaign will write | `backup-epe-live.sh` 03:20 MSK | `epe_2026_*` |
| `postgres.public` — 58 workflows, 7 credentials, 8 settings, 41 webhook registrations, execution history | `backup-epe-live.sh` 03:20 MSK | `n8n_app_*` |
| `postgres.performance_db` — the read-only 2025 archive | `backup-performance-db.sh` 03:00 MSK, **unchanged** | `performance_db_*` |

**Not covered — stated plainly:**

1. **Off-host copy. Still nothing.** All three stems live on one disk on one VPS. A host or disk loss takes
   the database and every backup of it together. **BUG-014 stays open** — the brief made closing it
   conditional on Alexander naming a target in this conversation, and he has not; no S3 sync was configured.
   This is now the single largest remaining gap in the regime, and it is larger than it was this morning,
   because there is now more on that one disk worth losing.
2. **`N8N_ENCRYPTION_KEY`.** Set as a container env var in the Portainer stack; in no file, no volume, and no
   dump. Restoring `n8n_app_*` into an n8n started with a different key gives 58 working workflows and 7
   unreadable credentials. The key is not written into this repo or this report. Alexander should hold a copy
   somewhere he can reach if the VPS is gone.
3. **Alerting.** The status file is a pull check. Nothing notifies anyone if the job stops running (§6).
4. **Point-in-time recovery.** These are daily logical dumps. Worst-case loss is up to ~24 h of campaign
   writes. No WAL archiving, no replica. Adequate for a half-year evaluation cycle; stating it so nobody
   assumes otherwise.
5. **Frontend releases, Caddy config, the n8n container definition.** Out of scope here. The frontend is
   rebuildable from the repo, 14 releases sit in `/var/www/epe/releases`, and the Portainer stack is
   documented in `infra/n8n-stack.yml`. Not backed up by this job, and not claimed to be.

**What close-recovery looks like now** — the reason BUG-032 was High. If a period is closed prematurely,
the previous night's `epe_2026_*` dump restores into a throwaway with `verify-restore.sh`, the pre-close
`evaluation_periods` and `period_results` rows are read out of it, and the fix is applied to live by SQL.
Before today that dump did not exist and there was nothing to read.

---

## 9. Files

| File | Change |
|---|---|
| `/root/backups/epe/backup-epe-live.sh` (host) | **New.** The daily job. md5 `d5953e90a1701de77f1261e523c135be` |
| `/root/backups/epe/verify-restore.sh` (host) | **New.** Restore-proof harness. md5 `d99e7133d8e68f3f3165acc3792b14da` |
| `root` crontab | **One line added**, `20 3 * * * …`. Prior crontab saved to `/root/backups/epe/crontab.before-2026-08-21` |
| `/root/backups/epe/backup-performance-db.sh` | **Untouched** — md5 `a9f748541cad6379d8949ce91dab51e0` before and after |
| `scripts/backup-epe-live.sh`, `scripts/verify-restore.sh` | **New**, byte-identical copies of the host files |
| `bugs.md` | BUG-032 closed with the evidence above; BUG-014 given a progress line and left open |
| `PROJECT_RULES.md` | New **Backups** section — what, where, retention, how to restore |
| `docs/HANDOVER.md` | Three lines that are now false were corrected: the §2 Backups row, §6 item 5, and the September-queue row |
| `PROGRESS.md` | This session |

---

## 10. Boundaries held

- **2025 archive:** read by `SELECT` and by `pg_restore -l` on an existing dump. Counts unchanged, 73 / 234 /
  644 / 3. Its script and cron line are byte-identical; its 10 dumps are still 10.
- **No write to `epe_2026`.** `pg_dump` is a read. Live counts after the session: users 89, evaluations 0,
  scores 0, `period_results` 0 — the morning's numbers.
- **No workflow PUT / activate / deactivate:** `workflow_entity` 58 total, 33 active, before and after.
- **No deploy, no mail.**
- **Throwaways dropped.** Three were created (one of them by a restore attempt that failed on a benign
  `schema public already exists` before the script tolerated it); all three are gone, and `pg_database` is
  back to `epe_2026` + `postgres` + the two templates.
