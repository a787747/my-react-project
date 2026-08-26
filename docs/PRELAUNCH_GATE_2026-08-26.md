# PRELAUNCH_GATE — the acceptance gate before «Запустить оценку» (2026-08-26)

**Brief:** PRELAUNCH_GATE (adversarial, fresh session, on the Mac). **Decision implemented:** D-0826-3.

**Outcome in one line: every money number the four reports claim was recomputed independently from
raw database rows and matches the payload, the screen and the frozen result to the digit — 1 922
matrix cells, 100 frozen rows, three budget distributions to the kopeck; every boundary case in the
brief behaves; the second gate's semantics were established from the live graphs and measured on a
stand; the coefficient snapshot is identical to live, value for value; the one permitted fix —
BUG-073's 422 refusal — is deployed and proven money-neutral by two closes of two copies of one
dump; the verdict is YES, the owner can press.**

Live writes this session: **one** workflow PUT (`API: Score Correction`, 07:57:50.177Z), one probe
`auth_sessions` row per verification pass (deleted in a `finally`). No `epe_2026` row was written
outside those probe sessions: no user, scope, period, catalogue, coefficient, grade or criteria
write. **The second gate was not pressed on live and no route that could press it was called** —
it was pressed only on the throwaway stand, through the real route, twice per database.

---

## 0. What was tested against what

| The reports' claim | My measurement | Result |
|---|---|---|
| Live state 89 / 3 / 80, tables 0/0/0/0, `evaluation_started_at` NULL ×3, release `20260826T051630Z` | SELECT/readlink 07:27:25Z, again 07:59:02Z | **identical** |
| Coefficient snapshot `H1-2026_coefficients_20260826T044844Z.md` (three md5, every raw value) | recomputed md5 07:27:38Z + full raw dump diffed by eye | **identical** — the owner has changed nothing since 04:48:44Z |
| The `c_level_direct_scores` CTE byte-equal in both money readers | extracted from live `workflow_entity`, compared | **identical** (493 = 493 bytes) |
| Generators at HEAD == live, all workflows | `check_live_drift.py` | 32 identical, 0 changed |
| Matrix payload == raw rows | my own Python recompute, no project helper imported | **1 922 cells, zero mismatches** |
| Screen == payload == frozen | browser on the stand + two real closes | **identical**, figures below |
| Budget distributes to the kopeck | my own largest-remainder arithmetic vs the screen | **15/15 amounts identical** across three budgets |

Proof artefacts: `backups/2026-08-26-prelaunch-gate/` — `gate_drive_proof.json` (123 checks),
`gate_recompute_proof.json` (51), `gate_close_proof.json` (33), `gate_live_verify.json` (20/20),
plus the stand scripts and my recompute (`gate_mine_ctl.json`). Two of the drive checks are
recorded as failed: both are the checker's own string format (`f` vs psql's `false` under `||`),
and the values they compared are re-asserted correctly in `gate_close_proof.json`.

## 1. The money, recomputed from raw rows (brief item 1)

**The stand.** Two databases restored from one fresh dump of live (07:43Z), seeded identically
with my own fixtures 1701–1712 (none of any previous brief's), and two isolated n8n containers:
control carrying the workflow surface **at HEAD** (byte-identical to live, per the drift check),
treatment carrying the working tree (item 5's one-file change — asserted to be exactly one file
before the stand would build). All evaluations were submitted through the real routes with minted
tokens; the gate was pressed through the real `POST /api/periods/start-evaluation`; both databases
were closed through the real `POST /api/periods/close`.

**The recompute.** Applicability, the final-cell rule, formula #3 and the rounding were restated
in plain Python from HANDOVER §4 and the decisions — importing nothing from the project — and run
against rows pulled straight out of Postgres. Every expected figure was also computed on paper
first and written into the script as a constant with its working.

My figures next to the system's, per person (index = Σ(score × level coef × weight) × grade coef,
**no division by Σ weights — §4, intentional, verified as specified and not "fixed"**):

| fixture | my paper figure | matrix payload | screen (Итог) | frozen `bonus_index` |
|---|---|---|---|---|
| 1701 GT Manager (M2 3.00) | **360.9000** | cells identical | 360.90 | 360.9000 |
| 1702 GT Full (S2 1.10, 2 C-level, 2 corrections) | **243.5620** | cells identical | 243.56 | 243.5620 |
| 1703 GT Partial (A 0.30, 2 of 6 criteria) | **7.4400** | cells identical | 7.44 | 7.4400 |
| 1705 GT NoGrade (grade NULL) | **102.9200** | cells identical | 102.92 | 102.9200 |
| 1708 GT Solo (one C-level evaluator) | **118.2280** | cells identical | 118.23 | 118.2280 |
| pool Σ | **833.0500** | — | 833.05 («Сумма с коэф. грейда») | 833.0500 |

Difference on every surface: **identical.** The three surfaces edited in three places last night
— the matrix payload, `/admin/final-scores`, and the close dataset — still agree, with each other
and with arithmetic done from the raw rows by someone who distrusted all three.

The averaging shipped by D-0826-1, re-proven with my own fixtures: two C-level evaluators at 8 and
4 → cell **6 ×2**, at 7 and 9 → **8 ×2** (tooltip «Среднее по 2 оценкам C-level»); one evaluator's
7 passes through as 7; zero evaluators read null, never 0. `rating_c_level_direct` = 7.00 = the
mean of the two evaluations' own scores, agreeing with the cell path.

**The budget** (`/admin/bonus-calculation`, typed into the real input in a real browser): pool
833.05, my own largest-remainder allocation next to the screen's:

| typed | parsed as | screen total | reconciliation line | my amounts vs screen |
|---|---|---|---|---|
| `3.000.000` (ru dots — the case that used to yield 3) | 3 000 000.00 | 3 000 000,00 TMT | «да, до копейки» | 5/5 identical (1 299 681,89 / 877 121,42 / 425 765,56 / 370 638,02 / 26 793,11) |
| `3 000 000` (spaces) | 3 000 000.00 | same amounts | «да, до копейки» | identical |
| `2,500,000.55` | 2 500 000.55 | 2 500 000,55 | «да, до копейки» | 5/5 identical |
| `999,99` | 999.99 | 999,99 | «да, до копейки» | 5/5 identical |

## 2. The boundaries (brief item 2) — what happened, and what a user would conclude

| boundary | what happened | what a user concludes |
|---|---|---|
| **Zero C-level evaluators** (1703) | cell null, no index contribution, frozen `rating_c_level_direct` NULL | «ещё не оценен» — never a zero |
| **One C-level evaluator** (1708) | the integer passes through unchanged: 7 → 56.00 on criterion 1 | a single opinion reads as itself |
| **Two C-level evaluators** (1702) | mean, ×2 badge, count in payload, frozen index carries the mean | a 6 that is 8-and-4 is visibly not a plain 6 |
| **Out of scope with existing evaluations** (1704, excluded via the real route) | route refused first (409 `HAS_EVALUATIONS`, GAVE/ABOUT counts), then excluded with confirmation; frozen `false/false/NULL`; their **given** upward eval still counts (1701's upward = 6.75 includes it); their received rows survive in the DB | nothing deleted, nothing paid, the record says why |
| **Terminated person's given evaluations** (1707) | terminated via the real route mid-campaign; 1701's `rating_upward` 6.75 includes the leaver's 6 — identical before and after; leaver frozen `false/false/NULL` | the leaver's opinion of the manager survives the leaving |
| **Manager whose subordinate is excluded** (1701) | manager's own money unmoved (360.9000 on both closes); the excluded person is a marked row, out of every total | the manager loses a task, not a number |
| **Person with no grade** (1705) | self-review refused 422 `NO_GRADE_COEFFICIENT`; but manager/C-level evals accepted and the **close froze 102.9200 = Σ × 1.00** — a silent fallback, labeled on the screen («без грейда (×1.00)») but frozen without refusal. **BUG-075**, latent today | the screen warns; the frozen record does not |
| **Criterion applicable on one channel, not another** | the write path accepts smuggled criteria on any channel (manager submit with criterion 1 → 200; criterion 2 for a no-reports subject → 200; upward/c_level submits with criterion 3 → 200). **Money provably unmoved** (frozen figures equal arithmetic that ignores those rows) — but they pollute the **ratings**: `rating_manager` froze 8.29 (honest 8.17) and 7.50 (honest 6.00). **BUG-074.** UI forms cannot produce these requests | the feedback numbers can be nudged by a hand-crafted request; the money cannot |
| **Partially evaluated subject** (1703) | scored cells count, unscored render `-` («ещё не оценен»), inapplicable render `н/п`; index sums only what exists — 7.44, no zero-fill | blank means blank |
| **Person with no participants row** (1709) | on the matrix, marked out of scope; **no frozen row at all** after close — BUG-067 re-measured, unchanged | the closed period cannot be asked whether they existed |
| **In scope, evaluated by nobody** (1706) | frozen `true/false/NULL` — in the pool count, no numbers | present, unpaid, honest |
| **Budget: zero** | all rows «Введите бюджет…», total 0,00, no reconciliation claim | zero is treated as "not entered" |
| **Budget: negative** (−100) | identical to zero — nothing distributed, no negative amounts, no NaN | refused by inertness |
| **Budget: spaces / dots / comma+dot** | all parsed correctly (table above), each reconciling to the kopeck | a ru-locale admin cannot lose six zeros |
| **Empty pool** (live itself, zero evaluations, budget 3 000 000 typed) | «Распределять пока не из чего: сумма итоговых баллов равна нулю… Бюджет сохранён в поле», total 0,00, no NaN | the screen blames the state, not the admin |
| **BUG-068 re-measured** | a correction for the excluded 1704 → 200 on both stands, stored, moves nothing frozen (the row is `has_data=false`) | unchanged by item 5, still open |

One observation on `/admin/final-scores`: an out-of-scope row (the terminated 1707) displays its
would-be figures — Σ 92.58 / Итог 129.61 — marked «вне охвата периода», excluded from every total,
but ranked among the others; the close freezes NULL for the same person. Labeled, admin-only, and
consistent with the D-4 design («rows that take no share stay visible»), so recorded under the
open BUG-060 discussion rather than as a new defect.

## 3. What the second gate actually does (brief item 3) — from the live graphs, then measured

Read from live `workflow_entity` (all 60 workflows, archived included), then measured on the stand:

- **Exactly one write to `evaluation_started_at` exists in the system**: `API: Manage Periods` →
  `Build Start SQL`, `SET evaluation_started_at = now(), evaluation_started_by = <actor>`, gated
  inside the statement on `status='active' AND is_active AND period_type != 'annual' AND
  evaluation_started_at IS NULL AND no children … FOR UPDATE`. **No route sets it back to NULL** —
  ten workflows reference the column; nine only read it. Recovery remains the documented SQL
  emergency stop. Measured: second press → 200 `already_started`, the timestamp does not move;
  refusals — container 422 `CONTAINER_NOT_STARTABLE`, annual 422 `ANNUAL_PERIOD_NOT_STARTABLE`,
  closed 422 `PERIOD_CLOSED`, non-admin 403. The mark **survives close** (history, not state).
- **What freezes at the press: the criteria catalogue and nothing else.** `Manage Criteria Admin
  V7` answers 409 `EVALUATION_STARTED` on writes once a started period exists — the only route
  that keys a refusal on the mark. Coefficients (`Save Score Coefficients`, `Update Admin Data`),
  classification (`Admin Save User`), scope (`Manage Period Scope`), termination
  (`Manage Employment Status`), and period create/rename/reparent contain **no reference to the
  mark at all** — everything built in the last two days keeps working after the press (the scope
  and termination routes gate only on `status <> 'closed'`).
- **What opens: the campaign.** Submits, score-correction and the task/status read surface all
  require started+active (measured: 409 `PERIOD_NOT_STARTED` / `NO_ACTIVE_PERIOD` before the
  press, working after). Admin/reporting reads stay keyed on active alone.
- **Irreversible at the press: the mark itself, and nothing else new.** Close remains the second
  irreversible step, and it worked normally on a started stand period. One nuance worth the
  owner's knowing: the **server** requires only `{period_id}` for start and for close — the typed
  period-name confirmation lives in the browser dialog, not in the API. Anyone with the admin
  token can press either gate with one curl. That is today's design (admin-only, one admin), not
  a regression.
- **Process, not product:** the deploy scripts of the recent briefs refuse to run once a period is
  started (deliberately), so any post-press backend change must be re-proven against a stand with
  data first. That is the correct default and worth remembering in September.

## 4. The coefficient snapshot vs live now (brief item 4)

Recomputed at 07:27:38Z with the snapshot's own SQL, and re-read after the deploy at 07:59:02Z:
`criteria` `fc618757…`, `score_coefficients` `317e09e8…`, `grades` `946b30a5…` — all three equal
the snapshot's. The raw values (9 weights, 90 level coefficients, 11 grade coefficients) were also
dumped and compared value-for-value against the document's printed tables: **identical**. The
owner has changed no money input since the snapshot was taken. Criterion 14's live curve is the
snapshot's curve (D-0826-2). Nothing to retake.

## 5. The one fix: a correction on a c_level_only criterion is refused (brief item 5, BUG-073, D-0826-3)

`API: Score Correction` (`rSZcm0HDMUHLYk8W`): `Validate Input` now also fetches the `c_level_only`
criteria ids in the same lookup as the project list; `Decide Level` refuses any of them with
**422 `CRITERIA_NOT_APPLICABLE`** — before the period gate, exactly like the project-dimension
refusal, so the rule is provable on live while no campaign runs. Message, verbatim from live:

> Критерий 1 оценивается только C-level: этот канал калибруется усреднением оценок C-level,
> корректировка к нему не применяется

- **The refusal, proven on the stand:** criteria 1 and 10 → 422 on the treatment stand, both
  before and after the gate press; the control (HEAD) stand accepted the same correction with 200
  and stored it — the BUG-073 baseline reproduced.
- **Money-neutral, proven by construction:** control closed **with** the stored-and-discarded
  correction, treatment closed **without** it — all **100 frozen `period_results` rows
  identical**. The refusal moves nothing, and the old 200's row provably never mattered.
- **Nothing else moved:** criterion-3 corrections (mid_level by the skip-level, c_level by the
  admin) still 200 on both stands and still average into the cell ((9+5+4)/3 = 6.0 → 19.80*);
  the project-dimension 422, ownership 403, and BUG-068's out-of-scope 200 are byte-for-byte the
  same on both stands; the matrix payloads differ in exactly one field (`1702/crit1/
  c_level_correction: 3` vs absent).
- **Deployed** at 07:57:50.177Z (one PUT; active before and after; webhook path unchanged; Auth
  Guard re-checked; export refreshed; drift check back to 0 changed). **Proven on live through
  Caddy** (20/20): criteria 1 and 10 → 422; criterion 3 → 409 `NO_ACTIVE_PERIOD` at the unpressed
  gate; criterion 8 on a general-category subject → the unchanged project 422; unauthenticated →
  401; `score_corrections` **0** before and after every probe.
- **Repo:** `scripts/build_route_guard_deferred.py` (the generator), `tests/clevelAveraging.test.js`
  (the "route accepts any criterion" pin inverted, with the owner's rationale in the comment;
  suite **401/401**), `scripts/deploy_correction_refusal.py`, `n8n_workflows/API_ Score
  Correction.json` refreshed from live. No frontend change — the screens never offered the
  correction on those cells' money path; the API is simply honest now.

**The rollback anchor**, taken before the deploy: `epe_2026_pregatefix_20260826T075634Z.dump`
(95 180 B, md5 `8b1c61ffe6c295960b109653f46d18cf`) and `n8n_app_pregatefix_20260826T075634Z.dump`
(603 173 B, md5 `6b4ad4a0699ae3778a54d35430c3e589`) — on the VPS in `/root/epe_stand_tmp` (600)
and on the Mac in `~/EPE_ROLLBACK/2026-08-26-prelaunch-gate/`, **outside the repository**, md5
verified equal on both sides. It supersedes `epe_2026_preclevel_20260826T051507Z.dump`. Restoring
`epe_2026` would undo nothing this session did (no row was written); the workflow rollback is
regenerate-from-`bb525ab`-and-PUT, or the n8n dump.

## 6. §4 for the record

The three formulas were recomputed, not re-litigated. The bonus index **is** a weighted sum
without dividing by the sum of weights, times the grade coefficient; my independent implementation
of exactly that rule matches the payload, the screen and the frozen result on every row it was
pointed at. It is intentional, it is consistent, and nothing in this session touched it.

## 7. Verdict (brief item 6)

**Да — владелец может нажимать «Запустить оценку». Ничего чинить перед нажатием не нужно.**

Broken (must be known, none blocks the press):
- **Nothing.** No defect found that would visibly break the campaign on day one.

Untidy, in the order I would care about them:
1. **BUG-074** (new): hand-crafted submits can attach channel-inapplicable criteria — money
   provably immune, archival ratings pollutable. Unreachable from the UI; fix on the write path
   before September calibration reads the ratings.
2. **BUG-075** (new): the close silently freezes ×1.00 for an evaluable no-grade person, and the
   snapshot doc §3 asserts the opposite. Latent today (the only no-grade people cannot be
   evaluated); becomes real the day a `can_be_evaluated` person lacks a grade.
3. **BUG-070 / BUG-071** (already filed): the HR card's unlabelled denominators and the C-level
   rows' unfillable criterion columns — the two things a user will actually squint at on day one.
4. **BUG-067**: a person added to `users` after the press silently joins no period and would leave
   no frozen record. Don't create users mid-campaign without the follow-up exclusion/inclusion.
5. **BUG-060 / BUG-068**: out-of-scope rows still display would-be money on an admin screen, and a
   correction can be written about an out-of-scope person (stored, never paid).
6. **BUG-014**: the off-host backup copy is still the only real infrastructure risk on the table.

## 8. Live, after (07:59:02Z)

89 users · 3 terminated · **80 in H1 scope** · `evaluations/evaluation_scores/score_corrections/
period_results` **0/0/0/0** · `evaluation_started_at` **NULL on all three periods** · H1
`active/true` · extensions `plpgsql` only · catalogue, coefficients and grades **md5-identical to
the 04:48:44Z snapshot** · `EPE: Auth Guard` `2026-08-18T16:34:30.674Z, active=false` · workflows
**60 / 35 active / 22 archived / 48 webhooks** · frontend release **`20260826T051630Z`** (no
frontend deploy this session) · `API: Score Correction` active, 9 nodes,
`updatedAt=2026-08-26T07:57:50.177Z`.

## 9. Session hygiene

- Read-only until the item-5 deploy; the deploy preceded by the dated dump pair copied to the Mac
  outside the repository, md5 equal on both sides (§5).
- Stand: two `epe_gate73_*` databases and two `epe-gate73-n8n-*` containers, created and removed;
  the drop loop refuses names without the `epe_gate73_` prefix; this brief's VPS-side dump deleted
  at teardown. `SELECT datname` afterwards reads `epe_2026, postgres`; `docker ps` shows the same
  six containers as before; nothing outside the stand was restarted. (The eight older dumps from
  previous briefs remain in `/root/epe_stand_tmp`, mode 600 — other sessions' artefacts, not
  removed, same position as CLEVEL_AVERAGING took.)
- Probe sessions on live: minted, used for GETs and non-mutating POST probes only, deleted in
  `finally`; `score_corrections` confirmed 0 after every probe; `auth_sessions` count restored.
- The live browser probe injected a minted token into the SPA's localStorage, read two admin
  screens, wrote nothing, and cleared the storage before the tab closed.
- **No mail of any kind was sent.** The stand browser login used the established stand-only
  fixture password on a stand-only account.
- The working tree carried no other session's edits; `git status` was clean at the start and every
  modified file is this session's.
- `backups/2026-08-26-prelaunch-gate/` (proofs, stand scripts, my recompute) is gitignored.

---

**Commit:** this report, the D-0826-3 row, the BUG-073 closure and BUG-074/075 rows, the builder
change, the inverted test pin, `scripts/deploy_correction_refusal.py` and the refreshed export
land on `main` as one commit; its hash is recorded here by the follow-up commit, per the repo's
rhythm. Commit: `PENDING`.
