# Prelaunch live check — H1 second gate (2026-08-25, on the Mac)

**Brief:** PRELAUNCH_LIVE_CHECK. Read-only against live, plus one `pg_dump` and repository hygiene.
Replaces the "last measured / unknown" column of `docs/LAUNCH_READINESS_SMOKE_FACTS_2026-08-25.md`
with readings taken today. Decides nothing about «Запустить оценку».

**Outcome in one line: the gate has not been pressed, the catalogue on live is byte-identical to the
07:23:16Z snapshot, every campaign table is still empty, today's backup ran clean — and the
manager→subordinate edge the smoke test needs does exist inside the named trio (Hekimov → Ruhlyadko),
so no substitution is required.**

## 0. Access — established, not inferred

| Path | Result |
|---|---|
| `ssh root@92.51.45.147` | **works** — `3569961-foreignpay.twc1.net`, up 12 days, server clock `2026-08-25T12:11:01Z` |
| SSH tunnel `epe-vps-tunnel` | already running (pid 2003); `127.0.0.1:25432` accepts TCP |
| `docker exec postgres_n8n psql -U admin -d epe_2026` | works — `current_database=epe_2026`, `current_user=admin` |
| `https://epe.sedamedical.com/` | `HTTP/2 200`, Caddy, `last-modified: Tue, 25 Aug 2026 11:57:54 GMT` |

Every SQL statement below was piped over stdin into that `psql` (no `-c` quoting), so what ran is
exactly what is quoted. Method: `SELECT` / `GET` / `readlink` / `stat` / `pg_dump` only. **No admin
route was called. No write of any kind was made to the application database.** The only bytes written
anywhere were the dump file of §3 and the repository commits of §4.

---

## 1. Today's readings — expected vs found

Source column: `LIVE` = read today by this session; the "expected" column is what
`docs/LAUNCH_READINESS_SMOKE_FACTS_2026-08-25.md` carried as *last measured* or *unknown*.

### 1.1 Period id 2 and the other periods

`SELECT id, name, period_type, status, is_active, evaluation_started_at, evaluation_started_by,
start_date, end_date, parent_period_id FROM performance_db.evaluation_periods ORDER BY id;`
— run at **2026-08-25T12:12:07.291972Z** (server clock, same statement).

| Field | Expected (last measured 07:23:16Z) | **Found today** | Verdict |
|---|---|---|---|
| `status` | `active` | **`active`** | confirmed |
| `is_active` | `true` | **`t`** | confirmed |
| `evaluation_started_at` | NULL | **NULL** | confirmed — **the gate has not been pressed** |
| `evaluation_started_by` | (not stated) | **NULL** | — |
| `start_date` … `end_date` | 2026-01-01 … 2026-06-30 | **2026-01-01 … 2026-06-30** | confirmed |
| `period_type` | `half_year` | **`half_year`** | confirmed |
| `parent_period_id` | 5 «Annual 2026» | **5** | confirmed |
| children of id 2 | none | **none** (only id 5 has a child, and exactly 1) | confirmed |

**Any other active period?** **No.** `count(*) WHERE is_active = true` → **1**;
`count(*) WHERE status = 'active'` → **1**. Full table: id 1 «Annual 2025» `annual`/`closed`/`f`,
id 2 «H1-2026» `half_year`/`active`/`t`, id 5 «Annual 2026» `annual`/`draft`/`f`. Confirms the
report's last-measured state.

**Any period with the start mark set?** **No — zero rows.**
`SELECT id, name, evaluation_started_at FROM performance_db.evaluation_periods WHERE
evaluation_started_at IS NOT NULL;` → `(0 rows)`. This answers the report's largest open question:
nothing was started between 07:23Z and 12:12Z.

**One thing that cannot be re-read, and should be said plainly:** `evaluation_periods` has **ten
columns and none of them is a timestamp of activation** (`id, name, start_date, end_date, is_active,
period_type, parent_period_id, status, evaluation_started_at, evaluation_started_by`). The
"activated at 2026-08-24 19:07:36Z" figure is a Caddy-log/report fact, not a database fact, and no
SELECT can reproduce it. The same structural gap the earlier report found for registration applies
to activation.

### 1.2 Row counts

Single `UNION ALL` count query, same session.

| Table | Expected (07:23:16Z) | **Found today** | Verdict |
|---|---|---|---|
| `evaluations` | 0 | **0** | confirmed |
| `evaluation_scores` | 0 | **0** | confirmed |
| `score_corrections` | 0 | **0** | confirmed |
| `period_results` | 0 | **0** | confirmed |
| `auth_sessions` | 12 | **13** | **+1 — explained below** |
| `auth_login_attempts` | (unknown) | **3** | new reading |
| `users` | 89 | **89** | confirmed |
| `criteria` | 9 | **9** | confirmed |
| `invite_tokens` | (unknown) | **2** | new reading |
| `email_verification_codes` | (empty expected) | **0** | confirmed |
| `password_reset_tokens` | (unknown) | **2** | new reading |
| `evaluation_period_participants` | 89 for id 2 | **178** total: 89 on id 2, 89 on id 5 | confirmed |

**The 13th `auth_sessions` row is an ordinary owner login, not a leak.** All 13 rows read out; the
newest is `user_id=2 Alexander Petrosov · admin · issued 2026-08-25 09:43:07Z · expires 13:43:07Z ·
revoked_at NULL`. Eleven of the 13 are Alexander, one is Jemal Gulberdiyeva (2026-08-20 12:22:21Z).
No row is revoked. The count is not an invariant — it moves with every login and no route deletes.

**Participants on id 2:** 89 total, **87 in scope**, 2 excluded — `user_id 31 Aysoltan Esenova` and
`user_id 35 Govher Balova`, both `exclusion_reason = hired_after_period_end`. Confirms HANDOVER §3.

**`auth_login_attempts` holds no real login failures** — all three rows are
`epe-throttle:verify-invite:<ip>` buckets (216.147.123.106 on 20 Aug, .31 on 20 Aug, .143 on 22 Aug),
each `failed_count=1`, `locked_until` NULL. Exactly the side effect the earlier report described for
`GET api/verify-invite`.

### 1.3 Which accounts have a non-null `password_hash`

`SELECT id, full_name, email, role, length(password_hash) … WHERE password_hash IS NOT NULL;`

| id | name | role | email | hash |
|---|---|---|---|---|
| **2** | Alexander Petrosov | `admin` | alexander@sedamedical.com | 133 chars, `$scrypt$N=16384,` | 
| **47** | Jemal Gulberdiyeva | `c_level` | jemal@sedamedical.com | 133 chars, `$scrypt$N=16384,` |

**`registered_total = 2`**, i.e. **87 of 89 are still unregistered.** This confirms the last recorded
figure (`PRELAUNCH_FIXES` line 167, 2026-08-20) and settles the earlier report's "unknown". The hash
length and prefix match the documented `$scrypt$N=16384,r=8,p=1$<salt>$<key>` format exactly.
Role headcount live: 69 employee, 12 manager, 5 c_level, 2 hr, 1 admin — matches HANDOVER §3.

### 1.4 The nine criteria — byte-identity check

Method: the live rows were re-read with **the same SELECT and the same renderer** that produced the
reference file (`scripts/apply_catalogue_fix2_h1.py` `criteria_rows()` + `snapshot_markdown()`,
lifted verbatim into a read-only script), then compared to
`docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md`.

```
live SELECT at      : 2026-08-25T12:13:35.661996Z
rows returned       : 9   ids = [1, 2, 3, 4, 8, 10, 12, 13, 14]
reference file md5  : e5306c2483ebf19a6e0944f78327b43f   (matches the md5 the FIX2 report certifies)
reference body md5  : 53f34a173ba8c462596d5acd80439d4f
live-today body md5 : 53f34a173ba8c462596d5acd80439d4f
BODY BYTE-IDENTICAL : True
differing fields    : 0
```

The comparison covers, per criterion, the metadata line (`category`, `target_audience`, `weight`,
`selfassesment`, `c_level_only`, `for_manager`, `is_active`, `score_definitions`, `level_0_desc`)
plus `title`, `description` and `level_1_desc` … `level_10_desc` — **117 fields across 9 rows, all
equal.** Only the file's two header lines differ, and only in the timestamp they quote, which is why
the whole-file md5 differs while the body md5 matches.

**Consequence:** the FIX1 wording of criterion 13 and criterion 8, and the five removed level-6 norm
labels, are all still exactly as recorded. **Nothing edited the catalogue between 07:23:16Z and
12:13:35Z**, and the catalogue is still writable — which is the same thing as saying the gate is
still unpressed.

### 1.5 Invite token id 4

| Field | Expected | **Found today** |
|---|---|---|
| `is_used` | `false` | **`f`** |
| `expires_at` | 2026-09-18 | **2026-09-18 11:55:19.124302** |
| unexpired now | yes | **`t`** |
| `used_by` / `used_at` | never written | **NULL / NULL** |
| token length | 43 (base64url) | **43** |
| `created_by` / `created_at` | admin, 19 Aug | **2**, 2026-08-19 11:55:19.124302 |

Confirmed on every field. `invite_tokens` holds exactly two rows; the other is id 1, the 18 Aug
one-hour bootstrap token — `is_used=t`, `used_by=2`, expired since 2026-08-18 17:36Z.
Token id 4's value is **not** reproduced in this report; it was read masked (`6GrMwY…JfXU`).

### 1.6 Backups

```
$ cat /root/backups/epe/backup-epe-live.status
OK 2026-08-25T00:20:01Z stamp=2026-08-25T0020Z
```

**Today's cron run succeeded.** This replaces the report's "today's status is unknown". Today's
`backup.log` lines, verbatim:

```
[2026-08-25T00:00:02Z] start /root/backups/epe/daily/performance_db_2026-08-25T0000Z.dump.gz
[2026-08-25T00:00:02Z] ok size=34519 retained=14 pruned=0
[2026-08-25T00:20:01Z] start /root/backups/epe/daily/epe_2026_2026-08-25T0020Z.dump.gz
[2026-08-25T00:20:01Z] ok epe_2026 size=25361 retained=5 pruned=0
[2026-08-25T00:20:01Z] start /root/backups/epe/daily/n8n_app_2026-08-25T0020Z.dump.gz
[2026-08-25T00:20:01Z] ok n8n_app size=377824 retained=5 pruned=0
[2026-08-25T00:20:01Z] ok epe-live all targets stamp=2026-08-25T0020Z
```

Retention now **5 / 5 / 14** stems (was 4 / 4 / 13 on 24 Aug) — both jobs are accumulating toward
their 14-day window and neither has pruned the other's files. `crontab -l` still reads exactly
`0 3 * * * backup-performance-db.sh` and `20 3 * * * backup-epe-live.sh`. Every dump file in
`/root/backups/epe/daily` is `-rw------- root root`. Disk: 17 G used of 50 G, 33 G free.

**BUG-014 is unchanged:** all 24 dump files, all three stems, sit on `/dev/vda1` — the same disk as
the live database. That is the reason for §3.

---

## 2. Who can evaluate whom — the trio resolves without substitution

### 2.1 The three people, read from live

`SELECT … FROM performance_db.users u LEFT JOIN users m ON m.id=u.manager_id LEFT JOIN departments d
… LEFT JOIN evaluation_period_participants p ON p.user_id=u.id AND p.period_id=2 …`

| | **Nurmammet Hekimov** | **Valeriya Ruhlyadko** | **Jahan Hojayeva** |
|---|---|---|---|
| `id` | **68** | **85** | **45** |
| `email` | nurmammet@sedamedical.com | valeriya@sedamedical.com | jahan.hojayeva@sedamedical.com |
| `role` | **`manager`** | `employee` | `employee` |
| `job_title` | Sales Manager of Clinical Lab Solutions department | Application Specialist | Head of the Lab Solutions Division |
| `manager_id` | 18 (Bayram Urayev, `c_level`) | **68 — Hekimov** | 18 (Bayram Urayev, `c_level`) |
| department | 16 Clinical Lab Solutions | 16 Clinical Lab Solutions | 1 Lab Solution Division |
| direct reports | **3** (ids 20, 56, 85) | 0 | **0** |
| `work_category` | `project` | `project` | `project` |
| `is_project_participant` | `t` | `t` | `t` |
| `has_subordinates` | `t` | `f` | `f` |
| `can_evaluate` | `t` | `t` | `t` |
| `can_be_evaluated` | `t` | `t` | `t` |
| `is_in_scope` (period 2) | `t` | `t` | `t` |
| **registered** (`password_hash IS NOT NULL`) | **`f`** | **`f`** | **`f`** |
| `token_version` | 0 | 0 | 0 |

### 2.2 Does a `manager_id` edge exist inside the trio? — **Yes.**

**`Ruhlyadko.manager_id = 68 = Hekimov`.** The earlier report's repo-based guess was right, and the
Akmyrat Jumahanov ambiguity it flagged is resolved: Jumahanov (id 1) holds the same title in the same
department and has 6 direct reports, but Ruhlyadko is not one of them.

Hekimov's three direct reports, for the record:

| id | name | role | work_category | project | has_subs | can_be_evaluated | registered | in scope |
|---|---|---|---|---|---|---|---|---|
| 20 | Bezirgen Annameredov | employee | `general` | `f` | `f` | `t` | `f` | `t` |
| 56 | Mahriban Ishanova | employee | `project` | `t` | `f` | `t` | `f` | `t` |
| 85 | Valeriya Ruhlyadko | employee | `project` | `t` | `f` | `t` | `f` | `t` |

### 2.3 The relation rule, read from **live** `workflow_entity` (not from the repo builders)

`API: Submit Evaluation` (id `tUxHoRn38rJVDxWv`, `active=t`, `updatedAt 2026-08-24T06:10:02.58Z`),
node `Validate Evaluation`, verbatim:

```js
if (source === 'manager') {
  relationFilter = `AND subj.manager_id = ${actorId} AND subj.can_be_evaluated = true`;
} else if (source === 'subordinate') {
  relationFilter = `AND actor.manager_id = ${rawSubjectId} AND subj.can_be_evaluated = true AND subj.role NOT IN ('c_level', 'admin')`;
} else {
  relationFilter = `AND actor.role IN ('c_level', 'admin') AND subj.can_be_evaluated = true AND lower(subj.email) NOT IN ('cem@sedamedical.com', 'hemra@sedamedical.com', 'mekan@sedamedical.com')`;
}
```

plus, in the same statement, `(p.evaluation_started_at IS NOT NULL) AS period_started`, an
`is_in_scope = true` join for **both** actor and subject, and `SELF_EVALUATION_FORBIDDEN` when
subject = actor. This confirms the earlier report's predicates from the authoritative source and adds
one detail it did not have: `c_level_direct` additionally excludes three C-level mailboxes by name.

### 2.4 Recommendation — **keep the trio as named**

| Channel | Actor → subject | Works? | Why, from the rows above |
|---|---|---|---|
| **manager → subordinate** | Hekimov (68) → Ruhlyadko (85) | **yes** | `subj.manager_id = 68` ✓, `subj.can_be_evaluated = t` ✓, both `is_in_scope` ✓ |
| **upward** | Ruhlyadko (85) → Hekimov (68) | **yes** | `actor.manager_id = 68` ✓, `can_be_evaluated = t` ✓, and Hekimov's role is `manager`, not `c_level`/`admin` ✓ |
| **self-review** | each of the three | **yes** | separate route; needs only in-scope, which all three are |
| **c_level_direct** | — | not exercisable by this trio | none of the three is `c_level` or `admin` |

**Hojayeva contributes a self-review and nothing else** — but not for the reason the earlier report
guessed. Her manager is Bayram Urayev (18), who is `c_level`, and the upward filter excludes
`c_level` subjects, so she has no upward channel; and she has no direct reports, so she has no
manager channel either. She is the sole member of department 1.

Two things to put in front of the owner rather than resolve here:

1. **Her title says «Head of the Lab Solutions Division» but she is `role=employee`,
   `has_subordinates=f`, with zero direct reports.** That is not a flag inconsistency — the
   `has_subordinates` column agrees with the `manager_id` graph for all 89 people, in both
   directions, with zero exceptions. It means the division genuinely has one person in it. The
   consequence is concrete: she is not scored on criterion 2 «Качество управления и развитие
   команды», and nobody reviews her upward. If that is wrong, it is an org-data decision, not a code
   fix.
2. **If a fourth channel is wanted, the cheapest addition is Bayram Urayev (18, `c_level`)** — he
   would exercise `c_level_direct` (criteria 1 and 10) and is the manager of both Hekimov and
   Hojayeva, which also gives a second manager→subordinate pair. Not proposed as a change; stated so
   the choice is informed.

### 2.5 Two blockers the smoke test hits before any of this matters

- **None of the three is registered** (`password_hash IS NULL` on all three, §2.1). The only
  route-based registration path emails a six-digit code to the employee's real mailbox, which is
  `AGENTS.md` hard constraint 5 / D-0820-8, and the pattern was explicitly forbidden after
  2026-08-20. **This needs Alexander's decision before a live smoke test exists at all.**
- **Submit is 409 until the gate is pressed.** `period_started` is false today, so
  manager→subordinate and upward cannot be exercised on live before «Запустить оценку». A smoke test
  of those two channels is *post*-gate by construction — which is exactly why §3 exists.

---

## 3. Pre-gate rollback anchor

`docker exec postgres_n8n pg_dump -U admin -d epe_2026 -Fc --no-owner --no-acl`, taken
**2026-08-25T12:16:17Z**, i.e. after every reading above and with `evaluation_started_at` still NULL.

| | **VPS copy** | **Mac copy** |
|---|---|---|
| path | `/root/epe_stand_tmp/epe_2026_pregate_20260825T121617Z.dump` | `/Users/a.petrosov/EPE_ROLLBACK/2026-08-25-pregate/epe_2026_pregate_20260825T121617Z.dump` |
| size | **80 710 bytes** | **80 710 bytes** |
| md5 | **`4ac406b4c84299263d4d7288ab00a193`** | **`4ac406b4c84299263d4d7288ab00a193`** |
| sha256 | `3980531af713b963f001de36d589e115e3b98d9d51109270b24100bd3e03d007` | `3980531af713b963f001de36d589e115e3b98d9d51109270b24100bd3e03d007` |
| permissions | `600 root:root` | `600`, inside a `700` directory |

Archive verified readable on **both** ends, not just written: `pg_restore -l` on the VPS reports
`Format: CUSTOM · Compression: gzip · TOC Entries: 161 · Dumped from database version 17.0`, and the
same listing on the Mac (with local `pg_restore` 18.1) shows **17 `TABLE DATA` entries** including
`performance_db users / criteria / evaluation_periods / evaluations / auth_sessions`.

**The Mac copy is outside the repository** (`~/EPE_ROLLBACK/…`, not `backups/`), so no git operation
can touch it, and it is the first off-host copy of live this project has ever had — the standing
BUG-014 gap, closed for this one file only.

**Deliberate deviation from PROJECT_RULES, stated so it is not a surprise:** a brief's teardown
normally empties `/root/epe_stand_tmp`. This file is a rollback anchor for a smoke test that has not
run yet, so **it must survive until that smoke test completes**. It is the correct directory
(root-only, `700`, never `/tmp`) but the wrong lifecycle, on purpose. Whoever runs the smoke test
removes it at the end.

---

## 4. Repository hygiene

### 4.1 The report branch is landed and the PR is closed

`origin/claude/launch-readiness-smoke-facts-laz4i7` (`0f36bdb`, `6fec53f`) was merged into `main`
with `--no-ff`, **not rebased** — the report records its own commit hash in its §9, and a rebase
would have invalidated that self-reference. `docs/LAUNCH_READINESS_SMOKE_FACTS_2026-08-25.md` on main
is byte-identical to the branch version (md5 `a237c786d00cf2e00eab00ce74462c15` on both).

One conflict, in `PROGRESS.md`: both sides appended at the end of the file. Resolved by **keeping
both blocks verbatim**, the frontend series first, the smoke-facts entry second. Nothing was dropped
or reworded.

### 4.2 The finding that mattered more than the merge

**The frontend serving live right now was built from code that existed in no commit, on no branch.**

The working tree carried seven uncommitted files — `PROGRESS.md`, `RatingGuide.jsx`,
`PeriodNotice.jsx`, `CriteriaOverview.jsx`, `ratingGuideH1.js`, `Welcome.jsx`,
`ratingGuideAndZones.test.js` — and those files are the source of the deployed bundle:

- repo `dist/index.html` md5 **`26c76622c9e4829f6216ec49a32148a0`** = deployed
  `/var/www/epe/releases/20260825T115748Z/index.html`, byte for byte;
- the CSS bundle rebuilt from that tree is md5 **`1ffb31f244ae8c82542ea10f08dd2efd`** = deployed
  `assets/index-BJGw5vuQ.css`, byte for byte;
- `https://epe.sedamedical.com/` serves `assets/index-BUpMaawX.js` + `assets/index-BJGw5vuQ.css`,
  `last-modified Tue, 25 Aug 2026 11:57:54 GMT`, and `current -> releases/20260825T115748Z`.

This is the same class of exposure as the 2026-08-22 parallel-session incident that
`PROJECT_RULES` "Sessions" was written after. Brought under version control as commit
**`d1b2d18`**, content committed exactly as found, no edit, no reformat; `npm test` **328/328**.
The underlying script defect is filed as **BUG-056** — `deploy_epe_frontend.sh` neither refuses a
dirty tree nor stamps a commit id into the release.

### 4.3 Is release `20260825T065554Z` traceable to a commit on origin? — **Yes: `6ca603e`**

First, a premise correction: **`20260825T065554Z` has not been the live release since 08:30Z.**
`/var/www/epe/current` points at **`20260825T115748Z`**, six releases later. The releases directory
holds `065554Z, 083035Z, 084142Z, 100801Z, 105418Z, 110537Z, 114906Z, 115748Z` for today alone.

There is no traceability metadata to read: `scripts/deploy_epe_frontend.sh` stamps only
`RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"` and writes no commit id anywhere in the release. So
traceability had to be established by rebuild.

**The JS entry hash cannot be used.** Control experiment: the current working tree — provably the
source of live `115748Z` — was rebuilt in a scratch directory and produced `index-DqnNGNEg.js`, not
the deployed `index-BUpMaawX.js`, and only **4 of 57** asset files matched by content. rolldown-vite
7.2.5 output is path-dependent; a build outside the original directory never reproduces the JS
hashes. Anyone comparing bundle filenames across machines should know this before drawing a
conclusion from a mismatch.

**The CSS bundle is a usable fingerprint** — path-independent, and it discriminates between commits:

| Built from | CSS filename | CSS content md5 |
|---|---|---|
| commit `c2b53d2` | `index-DzKyTaIk.css` | (differs — control, proves the fingerprint is not constant) |
| commit **`6ca603e`** | `index-DIEgTiK1.css` | **`3e085a3764f686bbafb54a5be5550520`** |
| deployed **`20260825T065554Z`** | `index-DIEgTiK1.css` | **`3e085a3764f686bbafb54a5be5550520`** |
| current working tree | `index-BJGw5vuQ.css` | **`1ffb31f244ae8c82542ea10f08dd2efd`** |
| deployed **`20260825T115748Z`** | `index-BJGw5vuQ.css` | **`1ffb31f244ae8c82542ea10f08dd2efd`** |

So **`20260825T065554Z` corresponds to the tree of commit `6ca603e` («PRELAUNCH_GUIDE_AND_ZONES_2026-08-25»),
which is on `origin/main`.** The 20-minute gap is consistent: the release was built at 06:55:54Z from
a working tree that was committed at 07:15:32Z. All builds used `VITE_API_URL=/webhook`, as the
deploy script does; the entry-chunk hash is unaffected by that variable.

Strength of the claim: the CSS bundle covers every Tailwind class actually used across the source, so
the markup changes in this series do move it — but it is a fingerprint, not a proof of the JS. Stated
as such.

### 4.4 Live workflow inventory, checked in passing

`postgres_n8n.postgres.public.workflow_entity`: **33 active of 58 total** — matches HANDOVER §2
exactly. `API: Admin Clear Test Evaluations` is **absent from live**, both by name and by node
content (`WHERE name ILIKE '%clear%' OR nodes::text ILIKE '%clear-test-evaluations%'` → `(0 rows)`).
This is the live confirmation the earlier report could not make; BUG-002's closure stands. The
route is genuinely gone, so `src/pages/AdminSettings.jsx:132` is a dead button that 404s — filed as
**BUG-057** now that the premise is verified, not assumed. `EPE: Auth Guard` exists as
`L0Zr7nVa8O5YWXd3`, `active=f` — correct, it is a sub-workflow invoked by Execute Workflow and has
no trigger of its own.

---

## 5. Drift and residue found while reading

Neither was resolved; both are stated with the rows behind them.

**5.1 Classification moved by one person since 2026-08-24.** HANDOVER §7 records «48 general / 41
project» and «37 × 4, 11 × 5, 36 × 6, 5 × 7». Live today:

```
work_category: general 49 / project 40      (is_project_participant agrees on all 89 — 0 mismatches)
criteria per person (period 2): 4 → 38 people, 5 → 11, 6 → 35, 7 → 5      (sums to 89)
```

One person moved project → general. This is expected owner activity — D-0822-3 made classification
editable during the campaign on purpose — but HANDOVER §7's numbers are now stale by one.

**5.2 Three world-readable EPE artefacts remain in VPS `/tmp`.** BUG-053's fix removed the seven
database dumps; these survived and are not dumps: `/tmp/epe-health-body` (15 B),
`/tmp/epe-n8n-before-recreate.json` (11 388 B, an n8n container config snapshot from 18 Aug),
`/tmp/epe-docs-hygiene/guard_nodes.json` (4 605 B, from 20 Aug). All `0644`. No employee personal
data, so this is hygiene rather than exposure — but the rule in `PROJECT_RULES` is that no brief
artefact lives in `/tmp` at all. Not deleted: this brief is read-only and the rule is «surface, do
not resolve». `/root/epe_stand_tmp` was empty before §3 wrote into it.

**5.3 `bugs.md` counters.** 18 `🔴 OPEN` / 37 `🟢 CLOSED` before this session's rows, confirming what
the earlier report found; HANDOVER §10 still says 16 open. The three rows filed here — BUG-056,
BUG-057, BUG-058 — take it to **21 open / 37 closed**, and the file's own Statistics table was
corrected to match.

**5.4 HANDOVER was deliberately not edited.** Its §7 classification figures (5.1) and §10 bug counter
(5.3) are now stale, but the file carries a provenance header saying every number in it was
re-measured in one pass on 2026-08-24 17:14–17:16 UTC. Patching two numbers inside that claim would
make the header false for the rest. The stale figures are named here instead; correcting HANDOVER is
a whole-file re-measurement, which this brief did not ask for.

---

## 6. What this session did **not** do

- Did not press the second gate, did not call `/webhook/api/periods/start`, did not touch
  «Запустить оценку».
- Did not call any admin route, read-only-looking or otherwise. Every fact above came from SQL,
  `readlink`/`stat`, one unauthenticated `GET /` of the site root, or a local rebuild.
- Did not change the catalogue, a coefficient, a user, a classification or a period.
- Did not restart a container, did not touch anything outside this stack.
- Did not resolve 5.1 or 5.2, and did not act on the registration blocker in §2.5.

---

**Live readings in this report were taken between 2026-08-25T12:11:01Z and 12:16:17Z (server clock).**
