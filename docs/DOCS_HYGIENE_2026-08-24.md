# Docs hygiene — 2026-08-24

**Date of work:** 2026-08-24
**Scope:** documentation and git only. No workflow PUT / activate / deactivate, no deploy, no DB write, no mail, no stand, no dump. 2025 archive read by SELECT only, never written.
**Live checks (read-only):** SSH `root@92.51.45.147`; `docker exec postgres_n8n psql` SELECT against `postgres` (n8n metadata + 2025 archive) and `epe_2026`; `readlink /var/www/epe/current`; `ls /var/www/epe/releases`; `openssl s_client` on 443; `docker inspect` / `docker ps --filter name=epe`; `iptables -S`; `crontab -l`; unauthenticated `GET` to the public origin. Local: `npm test`, `npm audit`, `git`, `python3 scripts/check_live_drift.py`, top-level export vs live count.

`docs/HANDOVER.md` carried 24 Aug edits in §3/§10 but was still headed “As of: 2026-08-21” and still quoted the 21 Aug snapshot. **This session re-measured the live system and corrected the documents toward those measurements and toward the accepted 22–24 Aug reports — never the reverse.**

---

## What changed per file

| File | Change |
|---|---|
| `docs/HANDOVER.md` | Header re-dated; every number in §§1–3 and §§5–10 reset to this session's measurements. **§4 not edited — md5 `0b2e854c22dc41f1d96e169b375b6350` before and after.** §2: frontend `20260824T145133Z` / 19 releases; webhooks **42** (19 GET / 21 POST / 2 OPTIONS); backups 13+4+4 and today's `OK`; host up 11d 19h. §3: Manage Periods `updatedAt=2026-08-24T06:10:13.683Z`, **70 nodes / 8 webhooks** including `start-evaluation`; criterion 14 weight **1.50** (D-0824-2) and the live-vs-approved level-curve note; `evaluation_started_at` NULL on all three periods; `auth_sessions` count removed as an invariant. Note above §4 now quotes **37×4 / 11×5 / 36×6 / 5×7**. §6.11 classification clause corrected to D-0822-3. §7 Done list and September table completed. §10 counters **20/33**; methodology paragraph amended. |
| `DECISIONS.md` | D-0822-1, D-0822-2, D-0822-3, D-0824-1 were **already present** (checked first; no duplicates). Added **D-0824-2** verbatim (criterion 14 weight 1.50). |
| `bugs.md` | Statistics block reset to a counted **20 open / 33 closed**. **BUG-028 closed**: named instance current (GATE_RECLASS + this session: top-level export 9 nodes, not in the stale set). Ledger still BUG-001…053, no gaps, no duplicates. BUG-029 left **closed** — see hypothesis 1. |
| `PROGRESS.md` | Added the three missing gate entries (`GATE_LIFECYCLE_COEFF`, `GATE_RECLASS`, `GATE_FINALIZE`) in chronological position — the same omission `PERIODS_VERIFY` had on 21 Aug. Appended this session. Every 22–24 Aug report now has at least one entry. |
| `PROJECT_RULES.md` | Both 24 Aug rules were **already present** (one working copy / one session; stand artifacts under `/root/epe_stand_tmp`, never `/tmp`). Only drifted fact touched: archive dump count **10 → 13** (measured). |
| `AGENTS.md` | Only the methodology paragraph: the “does not exist” conclusion replaced with the pending-draft sentence. No other edit. |
| `docs/DOCS_HYGIENE_2026-08-24.md` | This report. |

No workflow, frontend, schema, migration, script or data file was edited.

---

## Live snapshot the rewrite rests on

Measured 2026-08-24, 17:14–17:16 UTC.

### n8n

| Check | Live | How |
|---|---|---|
| `workflow_entity` total | **58** | `SELECT count(*) … FROM public.workflow_entity` |
| active / inactive unarchived / archived | **33** / **3** / **22** | same, filtered on `active` / `"isArchived"` |
| registered webhooks | **42** (19 GET, 21 POST, 2 OPTIONS) | `SELECT method, count(*) FROM public.webhook_entity GROUP BY 1` |
| active set names | the 33 in HANDOVER §2 — **identical to the 2026-08-20/21 set** | `SELECT name … WHERE active AND NOT "isArchived" ORDER BY name` |
| inactive unarchived | `EPE: Auth Guard` (`L0Zr7nVa8O5YWXd3`), `API: Global CORS Handler` (`BJwFjunajsGkoNY2`), `My workflow 10` (`2NXBJwobb3I5R2nU`) | same |
| deleted, confirmed absent | `API: Get Employee Self Review`, `API: Get Admin Data Fixed` | not in `workflow_entity`; generators still emit them |
| `EPE: Auth Guard` | `updatedAt = 2026-08-18 16:34:30.674+00`, `active=false`, `isArchived=false` | SELECT |
| `API: Manage Periods` | `M9ljMDdO1mIl8m1h`, `updatedAt = 2026-08-24 06:10:13.683+00`, active, **70 nodes / 8 webhooks** | `json_array_length(nodes)` + `webhook_entity` join |
| periods webhook paths | `GET api/periods`, `GET …/annual-rollup`, `POST …/create`, `…/activate`, `…/rename`, `…/reparent`, `…/close`, **`POST …/start-evaluation`** — **8** | same |
| n8n image | `n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, running, `restart=unless-stopped`, started 2026-08-19T05:32:35Z | `docker inspect n8n-n8n-1` |
| credentials / settings | **7** / **8** | `credentials_entity` / `settings` |

### `epe_2026`

| Check | Live | How |
|---|---|---|
| users | **89** — 1 admin, 5 c_level, 12 manager, 2 hr, 69 employee | `SELECT role, count(*) FROM performance_db.users` |
| registered (`password_hash IS NOT NULL`) | **2** — id 2 `alexander@sedamedical.com` (admin), id 47 `jemal@sedamedical.com` (c_level) | SELECT |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** | four `count(*)` |
| periods | `1 Annual 2025` annual/closed, 0/0, 0 children · `2 H1-2026` half_year/**draft**, parent 5, 89/87, 0 children · `5 Annual 2026` annual/draft, 89/89, 1 child | SELECT + participant subqueries |
| `evaluation_started_at` / `_by` | **NULL on all three** | SELECT |
| `work_category` | **48 general / 41 project**, zero `tender`; `is_project_participant` agrees on every row | SELECT |
| criteria-count distribution | 4 → **37**, 5 → **11**, 6 → **36**, 7 → **5** | CROSS JOIN of active non-`c_level_only` criteria with audience/project/has-subordinates predicate |
| active criteria | **9** (ids 1, 2, 3, 4, 8, 10, 12, 13, **14**); **zero** with `weight IS NULL OR <= 0` | SELECT |
| criterion 14 weight | **1.50** | `SELECT id, title, weight FROM performance_db.criteria WHERE id = 14` |
| criterion 14 levels | **0.70 / 1.00 / 1.00 / 1.10 / 1.20 / 1.50 / 2.00 / 3.00 / 5.00 / 7.00** | `SELECT score_level, coefficient FROM score_coefficients WHERE criteria_id = 14` |
| `score_coefficients` | **90** rows; min **0.30**; **zero** with `coefficient IS NULL OR <= 0` | SELECT |
| read-only trio | 21 Cem / 40 Hemra / 61 Mekan — `c_level`, `can_evaluate=false`, `can_be_evaluated=false`, `grade_id NULL`, `manager_id NULL` | SELECT |
| c_level writers | 18 Bayram (C1, 1.00) and 47 Jemal (C2, 1.00), both `can_evaluate=true`, both `can_be_evaluated=false` | SELECT |
| HR `can_evaluate` | **both** id 52 Liya and id 80 Sona are `true` (FINALIZE leftover; not re-decided) | SELECT |
| invite token id 4 | unused, expires **2026-09-18**, token length 43 | SELECT |
| `evaluation_periods_id_seq` | last_value **5** | SELECT |

Criterion 14 flags (live): `target_audience='all'`, `selfassesment=false`, `for_manager=true`, `c_level_only=false`. Other eight weights unchanged vs HANDOVER catalogue (5.00 / 3.00 / 3.00 / 1.50 / 1.40 / 1.60 / 1.00 / 1.80). Other eight level curves match the RECON 2026-08-22 appendix (spot-check: id 1 = 0.30/0.40/0.60/0.70/1.00/1.20/1.60/2.80/4.00/6.00).

### Migration 013 / 014 — on live

`period_results` columns and both anti-zero CHECKs unchanged from the 21 Aug snapshot. Indexes: `period_results_pkey (period_id, user_id)`, `idx_period_results_user (user_id, period_id)`.

`evaluation_periods` carries `evaluation_started_at` / `evaluation_started_by` (both nullable), `chk_evaluation_periods_started_by_needs_started_at`, FK on `evaluation_started_by`. Status CHECK `draft`/`active`/`closed`; `chk_evaluation_periods_active_status_consistent`. **No CHECK on `period_type`.** No CHECK tying the start mark to `status`.

### Host, frontend, archive

| Check | Live | How |
|---|---|---|
| frontend `current` | **`releases/20260824T145133Z`**; public `index.html` `Last-Modified` Mon, 24 Aug 2026 14:51:39 GMT | `readlink`; `curl -sI https://epe.sedamedical.com`; `stat` |
| releases on disk | **19**, back to `20260819T052840Z` | `ls /var/www/epe/releases` |
| origin | `https://epe.sedamedical.com` 200 via Caddy | GET |
| guard on new routes | `GET /webhook/api/periods` and `GET …/annual-rollup?container_id=5` → **401 `TOKEN_MISSING`**. `GET …/start-evaluation` → 404 “not registered for GET… Did you mean POST” (expected) | `curl -sS` (not `-I`; HEAD is 404) |
| certificate | Let's Encrypt `YE1`, `notBefore` 2026-08-19, `notAfter` **2026-11-17** | `openssl s_client` + `x509 -dates -issuer` |
| firewall | `DOCKER-USER → EPE-DOCKER-USER`; 80/443 RETURN; 5678 DROP on `eth0`; 5432/5431/8000/9000/2377/7946/4789 DROP except source `188.137.254.191` | `iptables -S` |
| databases on `postgres_n8n` | **`epe_2026` and `postgres` only** | `SELECT datname FROM pg_database` |
| stand containers | none (only `epe-proxy-caddy-1` Up 5 days) | `docker ps -a --filter name=epe` |
| `/tmp` dumps | **0** (`ls /tmp/*.dump` → no such file) | host `ls` |
| `/root/epe_stand_tmp` | absent (torn down) | `ls` |
| 2025 archive (`postgres.performance_db`) | 73 users, 234 evaluations, 644 scores, 3 corrections. **Fingerprint not re-hashed** (no dump taken this session) | SELECT |
| backups | two cron lines; `backup-epe-live.status` = **`OK 2026-08-24T00:20:01Z`**; today's `backup.log`: archive ok size=34519 retained=13; epe_2026 ok size=24100 retained=4; n8n_app ok size=366338 retained=4 | `crontab -l`; `cat`; `grep 2026-08-24` |
| host uptime | **11 days, 19 hours** at 2026-08-24 17:14 UTC | `uptime` |

`auth_sessions` was **not** queried and is **not** cited as an invariant.

### Repo / local

| Check | Result |
|---|---|
| `git status` at session start | clean; `main` = `origin/main` = `7ca4496` (`Prelaunch fix batch: …`) |
| `git log -1` | `7ca4496c46ca447214592dee4b0bbc180c2b1cc7` 2026-08-24 19:56:13 +0500 |
| `npm test` | **284 pass / 0 fail** (`# tests 284` / `# pass 284` / `# fail 0`) |
| `npm audit` | 15 total — 11 high, 3 moderate, 1 low (unchanged vs 21 Aug) |
| `check_live_drift.py` | **30 identical, 0 changed**, 2 absent from live (`API: Get Admin Data Fixed`, `API: Get Employee Self Review`) — `drift check OK` |
| stale top-level `n8n_workflows/*.json` vs live | **37** exports: **26** identical, **9** stale, **2** absent-from-live (the two deleted workflows). Named BUG-028 file has **9** nodes and is **not** in the stale set. Stale names match GATE_FINALIZE's nine. Count only; not regenerated. |

Stale nine: `API_ Admin Get Users Data.json`, `API_ All-evaluation.json`, `API_ Analytics Dashboard - Optimized.json`, `API_ Get Evaluation Details FIXED.json`, `API_ HR Evaluation Status.json`, `API_ My Profile V5 (Fixed Empty).json`, `API_ Register.json`, `API_ Reset Password.json`, `API_ evaluation-details-by-user.json`.

---

## Hypotheses — verified

**1. BUG-029 is closed.** `docs/LIFECYCLE_COEFF_2026-08-2x.md` §2.5 prints the 422 table (weight 0 → `INVALID_WEIGHT`, stored 1.00→1.00). `docs/GATE_LIFECYCLE_COEFF_2026-08-2x.md` item 7: “BUG-029 **closed with evidence**”. `bugs.md` Status is `🟢 CLOSED`; the read-side `|| 1.0` residue is recorded **in that closed row**, not re-filed as a new bug. GATE_RECLASS re-verified the residue still present and still unreachable through the API. The September-queue line that still named BUG-029 as if open was stale documentation — removed. HANDOVER §3's “BUG-029 closed” is the true statement.

**2. D-0822-1 / D-0822-2 / D-0822-3 / D-0824-1 were already in `DECISIONS.md`.** Counted `### D-0822-1` … `### D-0824-1` = one heading each. No duplicates created. **D-0824-2** was absent; added verbatim.

**3. The three gate reports had no `PROGRESS.md` entry.** Confirmed by search before this session. Same class as the 21 Aug `PERIODS_VERIFY` omission. Entries added in chronological position, text copied from the gates' own verdicts.

**4. HANDOVER drift** — all six listed mismatches were real. Corrected toward live / reports. Criterion-14 “1.50 → 2.00” annotation removed (live weight is 1.50; D-0824-2).

**5. `PROJECT_RULES.md` already carried both 24 Aug rules** (Sessions; Stand artifacts never in `/tmp`). Present. Only the archive dump count was drifted.

**6. `AGENTS.md` still said the methodology does not exist** — true for the repo. Amended with the pending-draft sentence.

---

## Live vs docs / docs vs docs — nothing papered over

**1. Criterion 14 weight is 1.50; its level curve is not the approved one.**
CRITERION9 (and the verbatim D-0824-2) state the approved curve as `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00` and say it is unchanged. Live SELECT 2026-08-24 17:15 UTC: **`0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00`**. Weight matches the decision. Levels do not. The other eight criteria's curves still match the RECON appendix. Documents state the **live** curve in HANDOVER §3 and leave D-0824-2 verbatim; the disagreement is here, not smoothed. **Surfaced — do not resolve.** Same channel as the weight test (admin coefficients route, no audit trail).

**2. Webhook count 41 → 42; Manage Periods 61/7 → 70/8.**
HANDOVER still quoted the 21 Aug Manage Periods stamp. Live: `updatedAt=2026-08-24T06:10:13.683Z`, 70 nodes, eight paths including `POST api/periods/start-evaluation`. The extra POST is the D-0822-1 route. Corrected.

**3. Frontend release was four (now more) deploys behind.**
HANDOVER §2 said `20260821T072859Z` / 14 releases. Live: **`20260824T145133Z`** / **19** releases. Matches PRELAUNCH_FIX_BATCH.

**4. Archive dump count 10 → 13.**
BACKUP_FIX / old HANDOVER / PROJECT_RULES said 10. Today's archive job log: `retained=13`. Corrected in HANDOVER and PROJECT_RULES.

**5. Note above §4 quoted the pre-criterion-14 distribution.**
The locked §4 last paragraph already has ×4/×5/×6/×7 (24 Aug edit, inside the lock — not touched). The note above §4 still said 37×3 / 11×4 / 36×5 / 5×6. Note corrected to the live 37×4 / 11×5 / 36×6 / 5×7. §4 itself unchanged.

**6. §6.11 still froze classification on first submission.**
That sentence contradicted §3, §6.3 and D-0822-3. Corrected to “stays editable; the 409 is gone”. Weight floor in the same sentence updated to ≥ 0.1 (D-0822-2 amendment) — the old “> 0” was the 22 Aug close of BUG-029, later amended.

**7. `bugs.md` 21/32 was true before this pass and is 20/33 after.**
Counted before edits: 53 `### BUG-` headings, 21 `Status: 🔴 OPEN`, 32 `Status: 🟢 CLOSED`, ids 1–53, no gaps, no duplicates. BUG-028's **text** said the export was still the 4-node pre-guard file; GATE_RECLASS and this session's comparison say the named instance is current (9 nodes, not in the stale nine). Status did not match the reports. Closed; counts 20/33. HANDOVER §10 followed the count.

**8. `PROGRESS.md` omitted the three gates.**
Same class as PERIODS_VERIFY on 21 Aug. Added.

**9. HEAD `curl -sI` on `/webhook/api/periods` is 404; GET is 401.**
21 Aug quoted GET 401. This session's first probe used HEAD and got 404 — n8n does not register HEAD. Re-probed with GET: 401 `TOKEN_MISSING`. Not a defect.

**10. Azure RDP / `assessment.sedamedical.com`.**
Added to the September table from the architect's queue. Azure :3389 was last measured 2026-08-19 (`docs/TLS_CUTOVER_2026-08-19.md`) and was **not re-probed** this session. `assessment.sedamedical.com` does not appear anywhere in the repo; **unverified**. `bk.sedamedical.com` is in TLS_CUTOVER (216.250.12.243).

---

## Leftovers triaged

Every leftover named in the ten 22–24 Aug reports is a `bugs.md` row or a line here.

| Leftover | Source | Triage |
|---|---|---|
| BUG-029 write-side zeros | LIFECYCLE / GATE_LIFECYCLE | **Closed.** Residue (`\|\| 1.0` readers) stays in the closed row; not re-filed. |
| BUG-041 destructive DELETE | RECON / LIFECYCLE / RECLASS | **Closed** (code-level then runtime-proven). |
| BUG-042 empty-coefficient fallback | LIFECYCLE | **Open row.** |
| BUG-043 container as current period | LIFECYCLE / RECLASS | **Closed.** |
| BUG-044 HANDOVER §10 index | GATE_LIFECYCLE / RECLASS | **Closed.** |
| Parallel-session 0.1 floor incident | LIFECYCLE §5.1 / GATE_LIFECYCLE | Became the PROJECT_RULES one-session rule; floor later approved (D-0822-2 amendment). |
| Start mark survives deactivation; emergency stop also stops the campaign | LIFECYCLE §5 | D-0822-1 amended 2026-08-24: both **intended**. |
| Score-correction writes skipped applicability | RECLASS §4.1 | Shipped in FINALIZE; D-0822-3 extended. |
| Flag SQL vs form are two copies of one rule | RECLASS §4.2 | Procedural; no row. |
| Additive disjoint-set `calculated_score` residue | RECLASS §4.3 | Recorded, not a defect (self-heals; unique index holds). |
| `calculated_score` / `rating_*` snapshot split | RECLASS §4.4 | By design, CALCULATION_MAP §A.1. |
| HR id 52 (and 80) `can_evaluate=true` | RECLASS §4.5 / FINALIZE notes | Alexander's call; no row. Re-measured: both still `true`. |
| Self-review `work_category` login snapshot | RECON / RECLASS §4.7 | Known limitation; no self criterion is project-scoped today. |
| BUG-045 stale-export class | GATE_RECLASS / GATE_FINALIZE | **Open row.** Re-counted today: **9** stale + 2 deleted-workflow exports. |
| BUG-046 middle-manager matrix | GATE_RECLASS | **Closed** by FINALIZE. |
| BUG-047 D-0822-3 wording | GATE_RECLASS | **Closed** by FINALIZE. |
| BUG-048 pre-period 422 justification | GATE_FINALIZE | **Closed** by D-0824-1. |
| BUG-049 migration 006 FKs | GATE_FINALIZE | **Closed** by CRITERION9; residue **BUG-050** open. |
| `managers_only` cells emitted for non-managers | GATE_FINALIZE §6 | Observation; out of D-0822-3 scope. |
| Inactive-criterion write/read split | GATE_RECLASS / GATE_FINALIZE | Pre-existing; catalogue freezes at start. No row. |
| Two generator outputs absent from live | BROWSER §9.4 / drift check | Standing decision; drift script now WARNs. No row. |
| Dashboard card “staleness” | BROWSER §9.3 | PRELAUNCH: automation artifact; no bug. |
| Residual non-dump `/tmp` scraps | PRELAUNCH §5.2 | Harmless; `/tmp/*.dump` is 0 today. |
| Report-name `PRELAUNCH_FIXES` vs `PRELAUNCH_FIX_BATCH` | PRELAUNCH §5.3 | Kept the BATCH name; no overwrite of the 20 Aug report. |
| `My workflow 10` unnamed stray | PERIODS_VERIFY / this queue | Operational; still in the inactive-unarchived three. No row. |
| Azure VM open RDP | TLS_CUTOVER; architect queue | September table; **not re-probed**. |
| Legacy domains `bk.` / `assessment.sedamedical.com` | TLS_CUTOVER; architect queue | `bk.` last measured 19 Aug; `assessment.` **unverified** (not in repo). |
| Which figure paid December 2025 bonus | §6.8 | Open Alexander item. |
| Results-visibility release | D-0820-17 / BUG-025 | Open Alexander item. |
| 2025 display in the new portal | §6.10 | Open Alexander item. |
| HR/manager methodology consultation before H2 | architect queue | September table; no row. |
| Coefficient-table versioning | BUG-010 / D-0824-2 | Already BUG-010. |
| Coefficient-write audit log | D-0824-2 | September candidate; no row. |
| Criterion 14 live levels ≠ approved curve | this session | **Surfaced.** Not filed — same class as the owner's weight test; he has not been asked about the levels. |

---

## Boundaries held

- No n8n PUT / activate / deactivate. Active set, Auth Guard `updatedAt`, and campaign emptiness are the live values at read time; nothing was written.
- No frontend deploy. `current` is still `20260824T145133Z`.
- No write to `epe_2026` — all four data tables are still 0; H1 is still `draft`; every `evaluation_started_at` is still NULL. Criterion 14 weight left at the measured 1.50 (not written).
- 2025 archive read by SELECT only; no dump taken, so no fingerprint claim is made.
- No mail (D-0820-8). No stand. No `/tmp` write.
- **§4 md5 before = after = `0b2e854c22dc41f1d96e169b375b6350`.** Slice: from `## 4. The most important thing in this document` through the byte before `\n## 5. Decisions taken` (includes the trailing `---\n`). The three formulas were not annotated.
- Documentation and git only. Working tree was clean at `7ca4496` (in sync with `origin/main`) at session start.

---

## Surface for the architect — not resolved

1. **Criterion 14 level curve on live is not the approved CRITERION9 / D-0824-2 curve.** Weight is 1.50 (the listed abort condition is not triggered). Levels are `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00`. If this was part of the `/admin/scoring` editability test, it was not reverted with the weight. The coefficients route still has no who/when/old→new.
2. H1 is `draft`; `evaluation_started_at` is NULL everywhere; all four data tables are 0. **Not** triggered.
3. No active workflow name is missing from the accepted-report set of 33. **Not** triggered.
4. `backup-epe-live.status` is `OK` today. `/tmp` dumps = 0. **Not** triggered.
5. `assessment.sedamedical.com` is in the architect's September list and **not** in the repo. Unverified.
6. D-0824-2's “level curve … is unchanged” sentence is false against live. The row was copied verbatim as instructed; the measurement is in §3 of HANDOVER and in this report.

---

## `bugs.md` count (this session)

```text
$ python3 -c 'import re,pathlib; t=pathlib.Path("bugs.md").read_text();
print("headings", len(re.findall(r"^### BUG-\d+:", t, re.M)));
print("OPEN", len(re.findall(r"Status: 🔴 OPEN", t)));
print("CLOSED", len(re.findall(r"Status: 🟢 CLOSED", t)))'
headings 53
OPEN 20
CLOSED 33
```

Statistics block equals those counts. Ledger 001…053, no gaps, no duplicates. Each row's status matches its text after the BUG-028 close.

---

## Git

Working tree at session start: clean, `main` = `origin/main` = `7ca4496`. Docs-only commit follows. `git diff --stat` of this session's edits (before commit):

```text
 AGENTS.md                         |  2 +-
 DECISIONS.md                      | 12 ++++++++++
 PROGRESS.md                       | 48 ++++++++++++++++++++++++++++++++++++++
 PROJECT_RULES.md                  |  5 ++--
 bugs.md                           |  9 +++----
 docs/HANDOVER.md                  | 71 +++++++++++++++++++++++++++++++-------------------------
 docs/DOCS_HYGIENE_2026-08-24.md    | new file
```

Docs commit: **`7db31d2affd3f4381bd84bd5c448e5aedbd2009c`**. This footer is recorded in a follow-up commit on top of that hash.

---

## Files to re-upload to project knowledge

| File | md5 |
|---|---|
| `docs/HANDOVER.md` | `2842496ef93f3b281449a9070094160b` |
| `DECISIONS.md` | `cb17772ee802981dc7dca20ac70f409d` |
| `bugs.md` | `7be6aaa9cce84356b3acbef012c29028` |
| `PROGRESS.md` | `3cbe22ecac6a57431ea288909931ea3d` |
| `PROJECT_RULES.md` | `aa98c2075d8e69b37aef7efe2e12dc34` |
| `AGENTS.md` | `a157c88d42ec5279264c2b45b391dbcb` |
| `docs/DOCS_HYGIENE_2026-08-24.md` (blob in `7db31d2`) | `d8a3d754adaea95b7f3780680d3d8da6` |

§4 of HANDOVER (locked slice) md5 **before = after = `0b2e854c22dc41f1d96e169b375b6350`**.

Final commit hash (this footer): filled after the follow-up commit.
