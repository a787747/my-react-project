# Prelaunch fix batch — 2026-08-24

Closes the two findings of the browser walkthrough (BUG-051 matrix alignment, BUG-053 `/tmp`
dumps), answers the refresh question by hand, and ships the riders. Launch stays paused; the only
live changes are the frontend deploy of the BUG-051 fix and the approved `/tmp` cleanup. Live
`epe_2026` saw no activation and no campaign write (verified §6).

**Report name.** The brief asked for `docs/PRELAUNCH_FIXES_2026-08-2x.md`; that file already
exists — it is the accepted 20 Aug report (in HANDOVER §10's list and cited by bugs.md).
Overwriting an accepted report was not this session's call, so this report is
`PRELAUNCH_FIX_BATCH_2026-08-2x.md`, after the brief's own title.

## 1. The stand

Same trio as the walkthrough (`setup_walkthrough_throwaway.sh` + `seed_walkthrough_throwaway.sql`),
re-run today: DB `epe_walk_20260824_1432` restored from a dated dump of live (89 users, 9 active
criteria verified), `epe-walk-n8n` on VPS loopback :25679 with the full generated surface (28
active), HEAD via `vite` :5299, Chromium (browser pane). One setup change made first, under the new
`/tmp` rule (§3): the script now stages its dump and credential/workflow files under root-only
`/root/epe_stand_tmp` (0700), not host `/tmp`.

Campaign data was written **through the real API with logged-in fixture JWTs** (activate → start →
self-review G → manager→G → manager→P), reproducing the walkthrough's exact scores; N (1308) was
deliberately left unevaluated for the refresh check. Stored rows verified by SQL: G self
`calculated_score 7.00 / weighted_score 5.66` (server-computed, same as the walkthrough), manager
rows 7.00 (G) / 7.50 (P); score rows G {3:7, 4:6, 12:8, 14:7} + self {3:7, 4:8, 12:6},
P {3:8, 4:7, 12:9, 14:6, 8:8, 13:7}.

Teardown at the end: container removed, `epe_walk_*` dropped (`epe_2026` is the only `epe*` DB
left), `/root/epe_stand_tmp` removed, tunnel killed, vite stopped.

## 2. BUG-051 — one shared column list for the admin matrix (fixed, deployed, CLOSED)

**The fix** (`src/components/admin/EvaluationsMatrixTable.jsx`, `src/utils/matrixUtils.js`):

- Header: `buildSharedCriteriaGroups(employees)` — the union of **every** row's criteria in
  first-seen order, grouped as before. `employees[0]` alone was also a broken header source: the
  server emits only the criteria applicable to each subject (D-0822-3), so a general first row
  would have dropped the project columns for everyone.
- Body rows: each row maps the HEADER's group lists and looks its own cell up by `criteria_id`.
  A criterion the row does not carry renders a placeholder **in its own column** — `N/A` in the
  project and management columns, «—» elsewhere. Header criterion objects (which are another row's
  data objects) never render as data cells.
- Presentation only: no formula, weight, payload or server change. Suite pins:
  `tests/evaluationsMatrixAlignment.test.js` (header from the union; rows map headerGroups, never
  their own `groupCriteria`; placeholder present; no data renderer receives a header object) and
  three `buildSharedCriteriaGroups` tests in `tests/matrixUtils.test.js`.

**Browser proof** (stand, real Chromium, walkthrough-shaped data — the walkthrough's broken
baseline for the same screen was 8 `td` under a 10-column header):

| # | Check | Result (verbatim DOM) |
|---|---|---|
| 2.1 | Every row matches the header | header row 2 = 10 `th`; td-count histogram over all rows: **`{10: 97}`** (`allRowsUniform: true`) |
| 2.2 | General row G, cell-by-cell | `7 / 7` · `8 / 6` · `6 / 8` under the three self headers; `7` under «Ответственность сверх роли»; **`N/A` under «Взаимодействие и надежность в проекте»**; **`N/A` under «Объем проектной работы и загрузка»**; `N/A` under «Качество управления…»; C-level cells under the two C-level headers |
| 2.3 | Project row P, cell-by-cell | `- / 8` · `- / 7` · `- / 9` (no self-review, manager scores); `6` under crit-14; **`8` and `7` under their own project headers**; `N/A` management; C-level cells in place |
| 2.4 | Unevaluated general row N | all dashes in its own columns, `N/A` in the project columns, 10 `td` |
| 2.5 | Corrected cell stays in its column | c_level correction 9 on P×crit8 (route `api/admin/score-correction`, 200) → matrix cell at **column index 5 = «Взаимодействие и надежность в проекте»**: `8.5`, amber (`bg-amber-100`); G's cell at the same index stays `N/A`; both rows still 10 `td` |
| 2.6 | Screenshot | both row types side by side under the full header (department filter «Lab Solution Division», 10 rows), P showing 8/7 in the purple project columns directly above G showing N/A·N/A |

**Money unchanged — reconciled to the digit.** Final-scores screen, same fixture data:

- Walkthrough parity: with criterion-14 weight at the walkthrough's **1.50** (stand-only
  round-trip, restored afterwards), the fixed build renders **exactly the recorded §3.6 figures**:
  G `27.30 | 9.90 | 12.00 | 21.00 → Σ 70.20 → ×0.60 = 42.12`;
  P `38.40 | 12.60 | 16.20 | 13.50 | 17.92 | 22.68 → Σ 121.30 → ×2.20 = 266.86`.
- Live-truth check: under live's **current** coefficients the same screen shows
  G `Σ 77.20 → 46.32`, P `Σ 125.80 → 276.76` — matching independent arithmetic exactly; the whole
  delta against the walkthrough is criterion 14's weight (see §5.1), `7×2.00×(2.0−1.5)=7.00` for G
  and `6×1.50×(2.0−1.5)=4.50` for P, zero residue.
- (Both money reads pre-date the §2.5 correction, as the walkthrough's did.)

**Deploy**: gates run by hand (`rg` still absent — BUG-040): legacy `:5678` absent, `/webhook`
present. Release **`20260824T145133Z`** → `/var/www/epe/current` (previous retained). Live 200;
`AdminEvaluationsMatrix-DMNIYQCv.js` and `matrixUtils-DY8RrZFq.js` on live are **md5-identical**
to the local fixed build. `check_live_drift.py` before and after: 30 identical, 0 changed.

## 3. BUG-053 — `/tmp` dumps cleaned (Alexander approved; CLOSED)

**Before** (`ls -la --time-style=long-iso /tmp/*.dump`, with md5):

| File | Perms | Size | Date | md5 | Local dated copy (md5-identical) |
|---|---|---|---|---|---|
| epe_2026_before.dump | 0644 | 73 391 | 2026-08-19 23:47 | ad44f490… | backups/2026-08-20-matrix-calibration/ |
| epe_2026_pre013_20260821_0549.dump | 0644 | 73 814 | 2026-08-21 08:49 | 03d2a358… | backups/2026-08-21-periods-hierarchy/ |
| epe_2026_pre014_20260822_0617.dump | 0644 | 77 705 | 2026-08-22 09:17 | e2684eab… | backups/2026-08-22-lifecycle-coeff/ |
| epe_2026_pre014_20260822_0623.dump | 0644 | 77 705 | 2026-08-22 09:23 | f67c2816… | backups/2026-08-22-lifecycle-coeff/ |
| epe_2026_pre014_20260822_0628.dump | 0644 | 77 705 | 2026-08-22 09:28 | 5282aea7… | backups/2026-08-22-lifecycle-coeff/ |
| epe_2026_pre014_20260822_0632.dump | 0644 | 77 705 | 2026-08-22 09:32 | d05b4c78… | backups/2026-08-22-lifecycle-coeff/ |
| epe_2026_pre_mig014_20260822T063731Z.dump | 0644 | 77 705 | 2026-08-22 09:37 | acf2de90… | backups/2026-08-22-lifecycle-coeff/ |
| epe_2026_after.dump | 0600 | 73 456 | 2026-08-19 23:47 | 72dca3bf… | backups/2026-08-20-matrix-calibration/ |
| n8n_public_before.dump | **0644** | 501 738 | 2026-08-19 23:47 | 195b34f9… | backups/2026-08-20-matrix-calibration/ |
| n8n_public_after.dump | 0600 | 505 007 | 2026-08-19 23:47 | 6ec22b52… | backups/2026-08-20-matrix-calibration/ |

The sweep found **ten** dumps, not the filed eight: two n8n application-schema dumps (workflow
definitions + encrypted credentials) from the matrix-calibration night were also sitting there,
one of them world-readable. Every file was verified **byte-identical (md5) to a dated local copy**
under the repo's gitignored `backups/` before anything was touched — none needed the
no-local-copy fallback.

**Actions**: the approved seven `epe_2026` world-readables — **deleted**. The three outside the
approved list (`epe_2026_after.dump`, both `n8n_public_*.dump`) — **moved**, not deleted, to
`/root/backups/epe/tmp_rescue_20260824/` (dir 0700, files 0600), per the bug's own fallback.

**After**: `ls /tmp/*.dump` → `No such file or directory`. Residual non-data scraps remain in
`/tmp` (schema `probe*.sql` queries, row-count listings `_live.txt`/`_restored.txt`,
`epe-docs-hygiene/guard_nodes.json`, one docker-inspect JSON, an empty `wf_export/`) — no personal
data, other sessions' diagnostic leftovers, left in place and listed here for an opportunistic
sweep (§5.2).

**Prevention**: PROJECT_RULES.md now carries the rule — stand and rollback artifacts never live in
`/tmp`; transient VPS-side artifacts go under root-only `/root/epe_stand_tmp` (0700, files 0600);
teardown includes their removal; a dump worth keeping is kept as the local dated copy.
`scripts/setup_walkthrough_throwaway.sh` complies as of this batch (dump + staging moved off host
`/tmp`; container-internal `/tmp` is exempt — it dies with the container) and this session's stand
ran through the compliant script end-to-end.

## 4. Refresh check by hand — the card DOES update; no bug filed

As `wt.manager` in the stand browser, WT Employee N's card read «Оценить» (no evaluated badge).
Real flow: «Оценить» → 4 sliders (3/4/12/14 — general subject) → «Сохранить оценку» →
«Подтверждение оценки» → «Подтвердить» → `POST api/submit-evaluation` (exactly one call in the
page's XHR log) → panel «Оценка сохранена! Итоговый балл: 7.00» → «Закрыть».

Observed, **without any page reload** (the in-page XHR recorder survived the whole sequence —
a reload would have wiped it):

- While the success panel was still open: N's card behind it still read «Оценить», zero
  `/api/employees` calls since submit — the refresh deliberately rides the close.
- On «Закрыть»: the log gained `GET /api/employees?user_id=1302&role=manager` (the dashboard
  refetch plus the sidebar TaskStatus refresh, alongside criteria/check-evaluated/
  check-self-review/get-my-manager) and N's card flipped to **«Оценен вами · Балл: 7.0» /
  «Редактировать»** — matching G and P.

**Answer**: the dashboard updates without reloading; refetch fires in `handleFinalClose`
(`Dashboard.jsx` → `EvaluationModal.handleFinalClose`), and all three close affordances of the
modal route through it. The walkthrough's §9.3 observation is an automation artifact: its driving
clicked the next card programmatically **through** the modal overlay while the success panel was
open, which skips `handleFinalClose`; a human cannot click through the overlay. No bug filed; no
fix needed.

## 5. Surfaced for decision

1. **Criterion 14 weight is now 2.00 on live, not 1.50.** Discovered because the stand mirrors
   live: the walkthrough's 12:36Z dump still carries `weight = 1.50` (re-verified from the dump
   itself), today's 14:32Z dump carries `2.00`. The write channel is the admin-only coefficients
   screen (legal until close, D-0822-2); the admin (id 2) logged into live at 11:41Z, inside the
   window; live n8n does not persist successful executions of that route, so there is no
   server-side audit row. Everything reconciles arithmetically (§2), and the catalogue docs
   (HANDOVER §3 table) are annotated. **If Alexander did not make this change, say so
   immediately** — then it is an incident, not an edit. If he did: no action needed, the number is
   his to set; the walkthrough report's §3.6 figures simply pre-date it.
2. **Residual `/tmp` scraps** (§3 list): harmless, other sessions' leftovers; delete on the next
   VPS-touching brief or leave.
3. **Report-name collision** (header note): the brief's literal filename would have overwritten
   the accepted 20 Aug PRELAUNCH_FIXES report; this batch published under PRELAUNCH_FIX_BATCH
   instead. If a different name is wanted, it is one `git mv`.

## 6. Riders

- `EVALUATION_METHODOLOGY.md` was **not attached** → skipped per the brief (not drafted).
- `check_live_drift.py` now prints `WARNING: generator output absent from live: <name>` per
  absent output (stderr) and says `drift check OK (2 generator output(s) absent from live — see
  warnings)` instead of a bare OK; exit code unchanged (the two absentees are a standing decision,
  BROWSER_WALKTHROUGH §9.4). Both pre- and post-deploy runs this session show the new warnings.
- HANDOVER §10 counters reconciled: **21 open / 32 closed**; report list extended; §3 criterion-14
  row annotated with the live weight move.
- bugs.md: BUG-051 and BUG-053 closed with evidence; statistics table 21/32.

## 7. Acceptance

- Browser evidence for item 1, both row types: §2 (DOM maps for G and P verbatim, uniformity
  histogram over all 97 rows, corrected-cell column index, screenshot).
- Money reconcile: §2 — walkthrough figures reproduced to the digit (42.12 / 266.86) under the
  recorded coefficient set; current-live figures matched by independent arithmetic; the one moved
  input identified and surfaced (§5.1).
- `/tmp` listing before/after with local-copy verification: §3 (md5 pairs for all ten files;
  after-state empty).
- Refresh answer with evidence: §4 (XHR log + card state transitions, no reload).
- Suite green: **284/284** (`npm test`; +7 over the walkthrough's 277: three
  `buildSharedCriteriaGroups` tests, four alignment source pins).
- Drift clean before and after deploy: 30 identical / 0 changed both times (§2), with the new
  explicit absent-from-live warnings.
- Live period state verified untouched after everything (§2 deploy + teardown): H1-2026 `draft`,
  `is_active = false`, `evaluation_started_at NULL`; evaluations / scores / corrections /
  period_results all 0; 89 users, 0 fixtures; Annual 2025 `closed`, Annual 2026 `draft`.
- Stand torn down (§1); committed and pushed with this report.
