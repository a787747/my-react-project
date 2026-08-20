# Docs hygiene — 2026-08-20

**Date of work:** 2026-08-20
**Scope:** documentation and repo files only. No workflow PUT, no deploy, no DB write. 2025 archive not written.
**Live checks:** SSH `root@92.51.45.147`, `postgres_n8n` SQL, `readlink /var/www/epe/current`, `openssl` cert, `docker inspect n8n-n8n-1`, local `npm audit`.

The previous `docs/HANDOVER.md` (as of after LAUNCH_PREP) was stale: it predates seven accepted reports (throttle, shared invite, dress rehearsal, c_level_direct, matrix/calibration, reporting surface, drafts UX). This session rewrote it from the live system, not from those reports.

---

## What changed per file

| File | Change |
|---|---|
| `docs/HANDOVER.md` | Full rewrite of current state. Same 10-section structure. **§4 three-formulas section copied verbatim** (including the now-historical CALCULATION_MAP item 5). Active set is the live 33 names. Open work and leftovers match live + repo. |
| `DECISIONS.md` | Added a 2026-08-20 one-line register: D-0820-6, D-0820-7 (one-line restatements), D-0820-9 … D-0820-15. Longer write-ups above were left in place. |
| `PROGRESS.md` | The six briefs already had dated entries with report filenames (throttle → drafts). Appended this hygiene session. |
| `bugs.md` | BUG-008 kept open. Added leftovers BUG-009 … BUG-016. Closed the defects these briefs actually fixed as BUG-017 … BUG-023. Counts: 9 open / 14 closed. |
| `PROJECT_RULES.md` | **Created.** Smallest honest: there was no reserved port-range file. This file records live Caddy / n8n / SSH-tunnel facts from `infra/caddy-compose.yml`, `infra/n8n-stack.yml`, and `epe-vps-tunnel`. |
| `AGENTS.md` | Environment bullet now points at `PROJECT_RULES.md` as those live facts, not a missing reserved range. Project-files list already named the file. |
| `docs/DOCS_HYGIENE_2026-08-2x.md` | This report. |

No workflow, frontend, schema, or data file was edited.

---

## Live snapshot the new HANDOVER is based on

Queried 2026-08-20 ~07:07–07:15 UTC.

### Counts

| Check | Live |
|---|---|
| `workflow_entity` total | **58** |
| active / inactive unarchived / archived | **33** / **3** / **22** |
| registered webhooks | **37** |
| `epe_2026` users | **89** |
| registered (`password_hash IS NOT NULL`) | **1** — `alexander@sedamedical.com` |
| evaluations / scores / corrections | **0** / **0** / **0** |
| `auth_sessions` | **1** (Alexander; drafts report kept `f443cfa5-…`) |
| `email_verification_codes` | **0** |
| `epe-throttle:%` rows | **0** |
| `auth_login_attempts` (all) | **1** (left in place by drafts UX; not deleted today) |
| H1 id=2 | `draft`, `is_active=false`, `half_year` |
| Annual 2025 id=1 | `closed`, `is_active=false` |
| participants period 2 | **87** in scope / **89** |
| invite id=4 | `is_used=false`, token length **43**, unexpired |
| frontend `current` | **`20260820T065435Z`** |
| previous release on disk | `20260820T063333Z` |
| n8n | 1.121.3, digest `sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, `restart=unless-stopped` |
| certificate | Let's Encrypt `YE1`, `notBefore=2026-08-19`, `notAfter=2026-11-17` |
| Caddy | `epe-proxy-caddy-1` up |
| 2025 archive (`postgres.performance_db`) | 73 users, **234** evaluations, 644 scores, 3 corrections, **0** `c_level_direct` rows |
| 2025 fingerprint | **not re-hashed this session** (no dump). Last computed same day in `docs/DRAFTS_UX_2026-08-2x.md` = `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e` |
| `npm audit` | 15 total (11 high, 3 moderate, 1 low). `--omit=dev`: 5 (4 high, 1 moderate) |

### C-level writers (live `epe_2026`, not edited)

| id | email | role | `can_evaluate` | `can_be_evaluated` |
|---|---|---|---|---|
| 2 | alexander@… | admin | true | false |
| 18 | bayram@… | c_level | true | false |
| **47** | jemal@… | **c_level** | **true** | false |
| 21 / 40 / 61 | cem / hemra / mekan | c_level | false | false |

### Auth Guard (canonical)

```text
id=L0Zr7nVa8O5YWXd3
active=false
updatedAt=2026-08-18T16:34:30.674Z
```

GET-body md5 was **not** recomputed (n8n API GET not called). See inconsistencies.

### Key workflow `updatedAt` (live, matches the reports that last PUT them)

| Workflow | active | `updatedAt` |
|---|---|---|
| `API: Verify Invite` | true | 2026-08-19T13:46:13.004Z |
| `API: Register` | true | 2026-08-19T13:56:52.642Z |
| `API: Submit Evaluation` | true | 2026-08-19T19:43:38.525Z |
| `API: evaluations-matrix` | true | 2026-08-19T20:34:41.748Z |
| `API: Score Correction` | true | 2026-08-19T20:34:42.909Z |
| `API: All-evaluation` | true | 2026-08-20T06:29:08.971Z |
| `API: evaluation-details-by-user` | true | 2026-08-20T06:29:10.451Z |
| `API: Manager Subordinates Matrix` | true | 2026-08-20T06:29:13.367Z |
| `API: Manage Criteria Admin V7` | true | 2026-08-20T06:29:14.973Z |
| `API: Update Admin Data` | true | 2026-08-20T06:29:16.555Z |
| `API: Analytics Dashboard - Optimized` | true | 2026-08-20T06:33:26.304Z |

Inactive unarchived: `EPE: Auth Guard`, `API: Global CORS Handler`, `My workflow 10`.
Deleted (absent from `workflow_entity`): `API: Get Employee Self Review`, `API: Get Admin Data Fixed`.

### Repo checks (not live n8n node bytes)

- Register export: token regex `[A-Za-z0-9_-]{16,128}`; persist no longer `SET is_used=true`.
- Score-correction export: `skip_level_id` = subject's manager's manager; period = `is_active AND status='active'`; else 409 `NO_ACTIVE_PERIOD`.
- Drafts: `evaluationDrafts.js` wired in self-review, upward, manager modal. Logout removes only `user` + `token`.
- Reporting empty-states present on matrix, all-evaluations, analytics, team-scores, criteria, final-scores, bonus, score-calculator.
- `ReportingRoute` on `/analytics`, `/admin/all-evaluations`, `/admin/evaluations-matrix`. `/admin` still `AdminRoute`. `/team` still `ManagerRoute` + `admin-users-data`.
- Employee routes: `my-profile` and `evaluation-history` have **no** period predicate. `check-self-review`, `check-evaluated`, `get-my-manager` **do** bind to the active period.

---

## Live vs report inconsistencies (not papered over)

1. **Auth Guard GET md5 is not a stable identity.** `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md`, `docs/MATRIX_CALIBRATION_FIX_2026-08-2x.md`, and `docs/ROUTE_GUARD_DEFERRED_2026-08-2x.md` quote `de58de075d66a621e832aac9a2dd3d14`. `docs/REPORTING_SURFACE_2026-08-2x.md` quotes `6ea30fc47b8f51180a4b963fdae79732` and says the earlier hash was a different serialization of the same GET. Live `updatedAt` is still `2026-08-18T16:34:30.674Z`. **Canonical check going forward: `updatedAt`, not md5.**

2. **Stale HANDOVER (pre-hygiene) vs live.** Said 26 active / 29 webhooks / score-correction inactive / reporting deferred. Live: **33 / 37**, score-correction and the six reporting PUTs active. Said “14 archived non-EPE prototypes”. Live: **22 archived** (includes two old `API: Check Self Review` and one old `evaluation-details-by-user`, plus foreign prototypes) and **3** inactive unarchived.

3. **Stale HANDOVER §3** said all 89 `password_hash = NULL`. Live registered = 1 (Alexander). `docs/SHARED_INVITE_2026-08-20.md` already called this out; the old HANDOVER was not corrected until today.

4. **`docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md` C-level writer list was incomplete.** It named only Alexander and Bayram. Live Jemal Gulberdiyeva **id=47**, `c_level`, `can_evaluate=true`. `docs/MATRIX_CALIBRATION_FIX_2026-08-2x.md` already corrected this. Org row was not edited in either brief.

5. **`docs/REPORTING_SURFACE_2026-08-2x.md` leftover on employee-route period filters is too broad.** It listed `my-profile`, `evaluation-history`, `get-my-manager`, `check-*` as still unbound. Repo generator JSON (launch `updatedAt` unchanged since 19 Aug): `check-self-review`, `check-evaluated`, and `get-my-manager` already join the active period. Only **`my-profile` and `evaluation-history`** still list every period. The new HANDOVER and BUG-009 use the narrower fact.

6. **§4 item 5 is preserved verbatim and is historically stale.** CALCULATION_MAP (19 Aug) said nine query families had no period filter and `score_corrections` had no period column. Later briefs bound matrix + reporting and activated score-correction on `period_id` (column already existed — `docs/ROUTE_GUARD_DEFERRED_2026-08-2x.md`). The three-formulas section was not edited. New HANDOVER §3 states that item 5 is historical.

7. **Dress rehearsal / throttle reports said 60 workflows, then 25 active.** That was before C-level-direct deleted two inactive workflows (58 total). Not a live contradiction; do not “correct” those reports. Live total is 58.

8. **This session did not re-parse live Register / Score-correction `jsCode` from Postgres** (COPY/JSON extract failed on a pipe-split). Identity of those graphs is the live `updatedAt` stamps above, which match the reports that PUT them. Repo exports contain the reusable-invite regex and the mid_level / active-period SQL.

9. **`PLAN.md` is still a Phase-0 revival plan** (HTTP :8080, closed ports). Out of scope; not rewritten.

---

## Boundaries held

- No n8n PUT / activate / deactivate.
- No frontend deploy.
- No `epe_2026` or 2025 write.
- No mail.
- No commit (not requested).
