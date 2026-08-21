# Docs hygiene — 2026-08-21

**Date of work:** 2026-08-21
**Scope:** documentation and git only. No workflow PUT / activate / deactivate, no deploy, no DB write, no mail. 2025 archive read by SELECT only, never written.
**Live checks (read-only):** SSH `root@92.51.45.147`; `docker exec postgres_n8n psql` SELECT against `postgres` (n8n metadata + 2025 archive) and `epe_2026`; `readlink /var/www/epe/current`; `ls /var/www/epe/releases`; `openssl s_client` on 443; `docker inspect` / `docker ps`; `iptables -S`; `crontab -l`; one unauthenticated `GET` to the public origin. Local: `npm test`, `npm audit`, `git`.

`docs/HANDOVER.md` was dated 2026-08-20 and predated eight accepted reports: `USER_FACING_COPY`, `PRELAUNCH_FIXES`, `PREFLIGHT_H1`, `ADMIN_USERS_SORT`, `TENDER_CATEGORY`, `PERIODS_HIERARCHY`, `PERIODS_VERIFY`, `POSTVERIFY_BATCH`. **This session rewrote it from the live system, not from those reports.** The reports were used to find out what to go and look at; every fact in the new document was then measured. Where live and a report disagree, the disagreement is in §3 below rather than smoothed away.

---

## What changed per file

| File | Change |
|---|---|
| `docs/HANDOVER.md` | **Full rewrite from live.** Same 10-section structure. **§4 copied verbatim — md5 `93e5bab464151d463b259b69e5914eaf` before and after the rewrite.** New: the launch is PAUSED and the dates are Alexander's; server-enforced subject-side visibility; the periods hierarchy and the live three-row period table; migration 013's shape and both anti-zero CHECKs; close semantics stated in full (admin-only, typed name, irreversible, annual refuses by type independently of child count); the live criteria catalogue; the September queue mirrored from the reports' leftovers. A note above §4 names the two figures inside it that are now older than the document, without editing them. |
| `DECISIONS.md` | Added **D-0820-16 … D-0820-21** — Alexander's six visibility/copy decisions of the 20 Aug evening — under a new `## 2026-08-20 evening` heading, and **D-0821-4** (read-only trio stays in H1 scope, no grades invented) under a new `## 2026-08-21 decisions` heading. **D-0821-1..3 were checked first: the periods brief had already logged them. No duplicates were created.** |
| `bugs.md` | Reconciled BUG-001…031 against the eight reports. Added nine open rows, **BUG-032 … BUG-040**, so that every leftover named in `POSTVERIFY_BATCH` / `PERIODS_VERIFY` is either an open row or explicitly triaged in §4 below. Moved **BUG-028** and **BUG-029** out of the `## ✅ Closed` section, where they had been appended while OPEN. Counts line **11 → 20 open**; closed unchanged at 20. Ledger is now BUG-001…040, no gaps, no duplicates. |
| `PROGRESS.md` | The seven other briefs of 20–21 Aug already had dated entries. **`PERIODS_VERIFY` had none** — added, in chronological position between the build and the post-verification batch. Appended this hygiene session. |
| `PROJECT_RULES.md` | Added **Throwaway proof stands** (container names, the VPS-loopback port 25679, the `epe_hier_*` / `epe_prelaunch_*` prefix that the drop loop keys on, the local vite ports 5199 / 5299, teardown as a rule) and **Local tooling** (`deploy_epe_frontend.sh` needs `rg`). Ports table gained the stand ports; the firewall line now says the restricted ports are open to **one allowlisted home IP that changes**. Header re-dated. |
| `AGENTS.md` | Corrected only drifted facts: the **Current goal** said "Phase 0 — deep review, read-only. Do not change code, config, workflows, or data", which three weeks of shipped change contradict; the Phase-0 success criteria became a standing quality bar; three file pointers were wrong (`docs/REVIEW.md` → `docs/REVIEW_H1.md`; `docs/REVIEW_CHECKLIST.md` → repo-root `REVIEW_CHECKLIST.md`; `docs/EVALUATION_METHODOLOGY.md` does not exist); Session start now points at `docs/HANDOVER.md` instead of the historical `PLAN.md`, and warns that `n8n_workflows/` exports are untrusted. |
| `docs/DOCS_HYGIENE_2026-08-21.md` | This report. |

No workflow, frontend, schema, migration, script or data file was edited. `PLAN.md` is still the Phase-0 revival plan and was **not** rewritten — it is now labelled historical in `AGENTS.md` instead.

---

## Live snapshot the rewrite rests on

Measured 2026-08-21, 08:21–08:40 UTC.

### n8n

| Check | Live |
|---|---|
| `workflow_entity` total | **58** |
| active / inactive unarchived / archived | **33** / **3** / **22** |
| registered webhooks | **41** (19 GET, 20 POST, 2 OPTIONS) |
| active set names | the 33 in HANDOVER §2 — **byte-identical to the 2026-08-20 set** |
| inactive unarchived | `EPE: Auth Guard` (`L0Zr7nVa8O5YWXd3`), `API: Global CORS Handler` (`BJwFjunajsGkoNY2`), `My workflow 10` (`2NXBJwobb3I5R2nU`) |
| deleted, confirmed absent | `API: Get Employee Self Review`, `API: Get Admin Data Fixed` |
| `EPE: Auth Guard` | `updatedAt = 2026-08-18 16:34:30.674+00`, `active=false`, `isArchived=false` |
| `API: Manage Periods` | `M9ljMDdO1mIl8m1h`, `updatedAt = 2026-08-21 07:28:10.039+00`, active, **61 nodes** |
| periods webhook paths | `GET api/periods`, `POST …/create`, `…/activate`, `…/rename`, `…/reparent`, `…/close`, `GET …/annual-rollup` — **7** |
| n8n image | `n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, running, `restart=unless-stopped` |

### `epe_2026`

| Check | Live |
|---|---|
| users | **89** — 1 admin, 5 c_level, 12 manager, 2 hr, 69 employee |
| registered (`password_hash IS NOT NULL`) | **2** — id 2 `alexander@sedamedical.com` (admin), id 47 `jemal@sedamedical.com` (c_level) |
| `auth_sessions` | **6** rows, 2 distinct users, **1 unexpired**; newest 2026-08-21 04:51 UTC |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| periods | `1 Annual 2025` annual/closed, 0 participants, 0 children · `2 H1-2026` half_year/draft, **parent 5**, 89 participants / **87** in scope, 0 children · `5 Annual 2026` annual/draft, top-level, 89/89, **1 child** |
| `work_category` | **48 general / 41 project**, zero `tender`; `is_project_participant` agrees on every row |
| criteria-count distribution | 3 → **37** people, 4 → **11**, 5 → **36**, 6 → **5** |
| active criteria | **8** (ids 1, 2, 3, 4, 8, 10, 12, 13); **zero** with `weight IS NULL OR <= 0` |
| `score_coefficients` | 80 rows; **zero** with `coefficient IS NULL OR <= 0` |
| read-only trio | 21 Cem / 40 Hemra / 61 Mekan — `c_level`, `can_evaluate=false`, `can_be_evaluated=false`, `grade_id NULL`, `manager_id NULL`, all three **in H1 scope** |
| c_level writers | 18 Bayram (grade C1, coef 1.00) and 47 Jemal (C2, 1.00), both `can_evaluate=true`, both `can_be_evaluated=false` |
| invite tokens | id 1 used; **id 4 unused**, expires 2026-09-18 |

### Migration 013 — `performance_db.period_results`, on live

Columns exactly as declared: `period_id`, `user_id`, `is_in_scope`, `has_data` (default `false`) all NOT NULL; `rating_manager`, `rating_upward`, `rating_c_level_direct`, `rating_self`, `final_rating`, `bonus_index` nullable `numeric`; `closed_at` NOT NULL default `now()`; `closed_by` nullable.

```
period_results_pkey                  PRIMARY KEY (period_id, user_id)
period_results_no_data_is_empty      CHECK (has_data OR (rating_manager IS NULL AND rating_upward IS NULL
                                       AND rating_c_level_direct IS NULL AND rating_self IS NULL
                                       AND final_rating IS NULL AND bonus_index IS NULL))
period_results_out_of_scope_no_data  CHECK (is_in_scope OR NOT has_data)
period_results_period_id_fkey / _user_id_fkey / _closed_by_fkey
idx_period_results_user
```

`evaluation_periods` carries `parent_period_id` (self-FK), `period_type`, `UNIQUE (name)`, a status CHECK (`draft`/`active`/`closed`) and `chk_evaluation_periods_active_status_consistent` — `(is_active = true) = (status = 'active')`. **There is no CHECK on `period_type`;** the annual-vs-half_year rule lives in the workflow, not in the database.

### Host, frontend, archive

| Check | Live |
|---|---|
| frontend `current` | **`releases/20260821T072859Z`**; public `index.html` `Last-Modified` Fri, 21 Aug 2026 07:29:04 GMT |
| releases on disk | 14, back to `20260819T052840Z` |
| deployed chunks | `AdminAnnualRollup-B3kLibOk.js`, `AdminPeriods-Rj7ZXzOy.js`, `useFinalScoresMatrix-D4w0eZxr.js`, `AdminUsers-DOtQPWJ5.js` |
| origin | `https://epe.sedamedical.com` 200 via Caddy; `GET /webhook/api/periods/annual-rollup?container_id=5` → **401 `TOKEN_MISSING`** (guard live on the new route) |
| certificate | Let's Encrypt `YE1`, `notBefore` 2026-08-19, `notAfter` **2026-11-17** |
| firewall | `DOCKER-USER → EPE-DOCKER-USER`; 80/443 RETURN; 5678 DROP on `eth0`; 5432/5431/8000/9000/2377/7946/4789 DROP except source `188.137.254.191` |
| databases on `postgres_n8n` | **`epe_2026` and `postgres` only** — every throwaway stand DB is gone |
| stand containers | none (`epe-hier-n8n` removed, as its report claimed) |
| 2025 archive (`postgres.performance_db`) | 73 users, 234 evaluations, 644 scores, 3 corrections. **Fingerprint not re-hashed** (no dump taken this session) |
| backups | one cron job, `0 3 * * * /root/backups/epe/backup-performance-db.sh`; 10 dumps, 14-day prune, log clean — **and it dumps the wrong database, see §3.1** |

### Repo / local

| Check | Result |
|---|---|
| `npm test` | **236 pass / 0 fail** |
| `npm audit` | 15 total — 11 high, 3 moderate, 1 low (unchanged) |
| `n8n_workflows/API_ evaluations-matrix.json` | **4 nodes**; `route_guard_deferred/evaluations-matrix.json` has **9** — BUG-028 still open |
| `n8n_workflows/API_ Manage Periods.json` | 61 nodes, matches live |
| working tree at session start | clean, `main` in sync with `origin/main` |

---

## Live vs report inconsistencies — nothing papered over

The 2026-08-20 hygiene pass found nine. Looking with the same eyes:

**1. The daily backup dumps the 2025 archive, not the live campaign database. Not named in any report.**
`/root/backups/epe/backup-performance-db.sh` runs `pg_dump -U admin -d postgres -n performance_db`. `-d postgres` is the **archive**; live is `epe_2026`. No cron job, systemd timer or script on the host touches `epe_2026` — `crontab -l` has exactly one line, and `grep -rl 'epe_2026' /etc/cron* /etc/systemd/system` returns nothing. Proven from the dump's own content: the 2026-08-21 file lists `invite_tokens` and `score_corrections` but **not** `period_results`, `auth_sessions` or `evaluation_period_participants`, three tables that exist only in `epe_2026`. The old HANDOVER's «Backups: daily on-host, 14 days, restore-verified» was true of the archive and read as true of live. This matters more now than a week ago: close is irreversible by design, and the documented recovery from a mistaken close is a database restore. **BUG-032, ⚠️ High, open.**

**2. Alexander is editing the classification, so two documented distributions are already stale.**
`docs/TENDER_CATEGORY_2026-08-2x.md` measured 46 general / 43 project on 20 Aug. Live today: **48 / 41**. That moves the criteria-count distribution — and therefore bonus share — from the «35 × 3, 11 × 4, 38 × 5, 5 × 6» printed inside HANDOVER §4 to **37 / 11 / 36 / 5**. §4 is copied verbatim by instruction and was **not** corrected in place; a note immediately above it names both stale figures and points at §6.3 for the live numbers. Neither the report nor §4 is wrong — they are dated measurements of a number Alexander is deliberately changing.

**3. The old HANDOVER's live-state block was stale in five separate lines.** All five are report-confirmed elsewhere; none had been folded back:

| Old HANDOVER said | Live |
|---|---|
| 37 registered webhooks | **41** (Manage Periods grew 3 → 7 routes) |
| Frontend `20260820T065435Z` | **`20260821T072859Z`** — four releases later |
| «88 of 89 users have `password_hash = NULL`; Alexander is the only registered user» | **87 NULL, 2 registered** — Jemal (id 47) registered 2026-08-20 12:22 UTC, recorded in `PREFLIGHT_H1` |
| Periods: id 1 and id 2 | **three rows** — id 5 «Annual 2026» exists and H1 has `parent_period_id = 5` |
| «H1 campaign start 2026-08-31 · 7 working days left» | **launch paused**; no date is enforced anywhere in the system |

**4. `auth_sessions` is not an invariant, and one report quoted it as if it were.**
`PRELAUNCH_FIXES` and `PREFLIGHT_H1` both recorded 4 rows / 2 users, and `PREFLIGHT_H1`'s constraints list says «`auth_sessions` untouched — 4 rows before and after». Live today: **6 rows**, 2 distinct users, 1 unexpired, newest 2026-08-21 04:51 UTC. The drift is ordinary login activity by the two registered accounts, not a defect — but a session count is a moving number and should not be cited as a held constraint. The stable statement is «no session was created *by this brief*».

**5. `PERIODS_VERIFY`'s baseline was superseded within three hours of being written.**
It declares «this table is the new baseline and supersedes the build report's» with frontend `20260821T060049Z`. `POSTVERIFY_BATCH` then deployed `20260821T072859Z` and PUT `API: Manage Periods` again (`06:00:08` → `07:28:10`). Both are honest; the lesson is that during a sprint a report's baseline has a half-life measured in hours, which is the argument for re-measuring rather than inheriting — and is why this document re-measured all of it.

**6. M2 was left open by both reports; the decision now exists and post-dates them.**
`PERIODS_VERIFY` M2 and `POSTVERIFY_BATCH`'s leftovers both record ids 21 / 40 / 61 in H1 scope with no grade and no manager as «Alexander's call, must land before 31 August». It has now landed: **D-0821-4** — they stay in scope, no grades are invented. Logged with that provenance stated in the register, so the two reports do not read as contradicted. The engineering consequence was already verified and is unchanged: `can_be_evaluated=false` in all three relation filters of `API: Submit Evaluation` means they can never acquire a `manager_score`, so their `final_rating` and `bonus_index` persist as NULL rather than as a coefficient-1.00 money row.

**7. `TENDER_CATEGORY` names the wrong column for the C-level criteria.**
It summarises the catalogue as «1/10 `c_level_only`» alongside «3/4/12 `all`», which reads as a `target_audience` value. Live: criteria 1 and 10 have `target_audience = 'all'` and carry a **separate boolean column** `c_level_only = true`. The report's conclusion is right in effect — they behave as C-level criteria — but a later session writing a query against `target_audience = 'c_level_only'` would get zero rows and draw the wrong conclusion. The new HANDOVER prints the catalogue with audience and flags in separate columns.

**8. `Annual 2025` has zero participant rows — stronger than the reason the reports gave.**
`PERIODS_VERIFY` observes that period 1 is closed with no `period_results` and can never obtain them, reasoning from the close route's 409. The measured reason is more basic: `evaluation_period_participants` has **no rows at all** for period 1, so even a hypothetical close would have nothing to iterate and would hit 422 `NO_PARTICIPANTS` first. Same conclusion, sturdier ground, and it confirms that the «нет сохранённых результатов» cell label was written for a state that really exists.

**9. `bugs.md` disagreed with itself and with the HANDOVER, in three ways.**
The old HANDOVER §10 said «`bugs.md` (open: BUG-008 plus leftovers listed in §7)» while the file's own statistics block said 11 open. **BUG-028** and **BUG-029** were filed under the `## ✅ Closed` heading while carrying `Status: 🔴 OPEN` — appended to the end of the file rather than to their severity sections. And BUG-029's severity marker is `🟢 Low–Medium`, where `🟢` is this file's *closed* marker; the text is quoted verbatim from the verification and was left alone, but the marker is misleading. Both rows are relocated; the counts line is now measured, not asserted.

**10. `AGENTS.md` pointed at three files that are wrong or absent — one of them the document it says code must conform to.**
`docs/REVIEW.md` does not exist (the review is `docs/REVIEW_H1.md`). `docs/REVIEW_CHECKLIST.md` does not exist (the checklist is at the repo root). And **`docs/EVALUATION_METHODOLOGY.md` has never existed anywhere in the repo** — while `AGENTS.md` describes it as the business contract Alexander owns, covering role groups, criteria, weights, scale, aggregation and calibration, with «code conforms to it, never the reverse — a divergence is an implementation bug». There is nothing to diverge from. `AGENTS.md` also still opened with «Phase 0 — deep review, read-only. Do not change code, config, workflows, or data», which every brief since 18 August contradicts, and pointed Session start at `PLAN.md`, flagged as historical by the previous hygiene pass and never corrected. Pointers fixed; the missing methodology is stated as missing in both `AGENTS.md` and HANDOVER §10 rather than invented — writing it is Alexander's, not an executor's.

**11. `PROGRESS.md` had no entry for `PERIODS_VERIFY`.** Seven of the eight briefs of 20–21 Aug were logged; the acceptance gate — the one that caught the unweighted bonus screen and the annual-type hole — was not. Added in chronological position.

**12. `POSTVERIFY_BATCH` named a misnamed artifact; it is still misnamed.** `backups/2026-08-21-periods-hierarchy/epe_2026_pre013_20260821_0710.dump` is a **post-013** dump carrying the `pre013` stem from a fixed template in the setup script. Confirmed on disk (77 620 bytes, alongside the genuine `_0549` at 73 814). `backups/` is gitignored, so this is a local-artifact wart, not a repo one — recorded so the next restore does not pick the wrong file. The host still holds `/tmp/epe_2026_pre013_20260821_0549.dump`, left deliberately.

---

## Leftovers triaged without a bug row

Everything named as a leftover or observation in `POSTVERIFY_BATCH` and `PERIODS_VERIFY` is now either a row in `bugs.md` or listed here with the reason it is not one.

| Leftover | Source | Triage |
|---|---|---|
| **M2** — trio in scope with no grade / manager | PERIODS_VERIFY, POSTVERIFY | **Decided:** D-0821-4. Not a defect. |
| `My workflow 10` is an unnamed stray inactive workflow | PERIODS_VERIFY | Operational, one click. Named in HANDOVER §2 and in the September queue; no code, no row. |
| Close staleness guard counts evaluations, cannot see an edit to an existing one or a fresh correction | PERIODS_VERIFY | **Procedural, by design** — the right fix is closing when nothing is in flight, which HANDOVER §7 now says. A `max(updated_at)` fingerprint is a Phase-3 idea, not an H1 defect. |
| ACTIVATE's re-assertions are snapshot-only (no `FOR UPDATE`); a lost activation race returns 404 where siblings return 409 | PERIODS_VERIFY | Pre-existing, unreachable in single-admin operation. Recorded here; would become real only with a second admin. |
| `FOR UPDATE` in close locks only `evaluation_periods` | PERIODS_VERIFY | Sufficient — only a close changes the `status`/`is_active` pair and only one close holds the lock. Not a defect. |
| `period_results` stores `role='admin'` rows; the roll-up hides them | PERIODS_VERIFY | By design, matrix precedent. Stated in HANDOVER §3. |
| `period_results` immutability is product-level; raw SQL can still write | PERIODS_HIERARCHY | Same trust model as every other table. Not a defect. |
| Sidebar task links can flash for one paint while `TaskStatusContext` loads | PRELAUNCH_FIXES | Cosmetic, sub-second, hidden after load. |
| `/admin/periods` errors surface via `alert(handleApiError(...))` | PERIODS_HIERARCHY | Cosmetic; consistent with the page's existing style. Related copy problem is BUG-035. |
| Three content-identical pre-013 dumps; production-PII throwaway DB; `main` 9 commits ahead | PERIODS_VERIFY | **All three resolved by POSTVERIFY's housekeeping and confirmed live today:** `_0547`/`_0548` gone, `postgres_n8n` holds only `epe_2026` + `postgres`, `main` was pushed. |
| `_0710` dump misnamed `pre013` | POSTVERIFY | §3.12 above. `backups/` is gitignored. |
| `.claude/launch.json` committed as stand tooling | PERIODS_HIERARCHY | Harmless; now documented in `PROJECT_RULES.md`. |

---

## Boundaries held

- No n8n PUT / activate / deactivate. Workflow counts, `updatedAt` values and the Auth Guard stamp are identical before and after this session.
- No frontend deploy. `current` is still `20260821T072859Z`.
- No write to `epe_2026` — all four data tables are still 0 and the period rows are unchanged.
- 2025 archive read by SELECT only; no dump taken, so no fingerprint claim is made.
- No mail (D-0820-8).
- Documentation and git only. The working tree contained no non-doc changes at session start (clean at `e6af71a`, in sync with `origin/main`), so no separate commit was needed for anything else.
