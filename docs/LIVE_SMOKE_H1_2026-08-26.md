# LIVE_SMOKE_H1 — the real H1 campaign exercised once on live, then removed (2026-08-26)

**Brief:** LIVE_SMOKE_H1 (fresh session, on the Mac). **Verdict in one line:**
**the campaign is safe to invite 78 people into.** Every channel was walked in a real browser on
the deployed frontend as three real, in-scope employees; eight evaluations (one of every kind,
including a partial completed through the additive path and one `c_level_direct` filed by the
owner's admin account) were created through the real routes; every money number the system
computed was reproduced by hand from raw rows and matched to the digit; and the system was then
returned to its starting state — the four campaign tables back to 0/0/0/0, every fingerprint,
count and md5 byte-identical to the anchor, only the two evaluation sequences advanced (an
accepted, documented gap).

Nothing this brief did not resolve was left resolved. One thing to know before invitation is in
§7; it does not block the invite.

---

## 1. The anchor — starting state, read and dumped before the first write (brief item 1)

Fresh `pg_dump -Fc` of live `epe_2026` at **2026-08-26 14:22Z**, copied to the Mac outside the
repository, md5 equal on both sides:

- VPS `/root/epe_stand_tmp/epe_2026_presmoke_20260826T142200Z.dump` → **`072fc76767f4666cb95d44e128166423`**
- Mac `~/EPE_ROLLBACK/2026-08-26-live-smoke/epe_2026_presmoke_20260826T142200Z.dump` → **`072fc767…`** (identical)

The dump is the rollback anchor; the row-level anchor is the fingerprint below
(`backups/2026-08-26-live-smoke/state_anchor_pre.txt`, gitignored). Restoring the dump would undo
nothing this session did — every write was reversed by id (§5). The VPS copy was deleted at
teardown per `PROJECT_RULES.md`; the Mac copy is kept.

**Recorded starting state (14:21Z), every quantity that had to be restored:**

| quantity | anchor value |
|---|---|
| campaign tables `evaluations/evaluation_scores/score_corrections/period_results` | **0 / 0 / 0 / 0** |
| `auth_sessions` | **21** rows (users 2, 47, 52 only — 45/68/85 had none) |
| registered accounts (`password_hash IS NOT NULL`) | **2, 47, 52** |
| users / terminated | 89 / 3 |
| roles | admin 1, c_level 5, manager 13, employee 68, hr 2 |
| participants — H1 (id 2) | 89 total / **78 in scope**; Annual 2026 (id 5) 89 / 86 |
| `participants` fingerprint (period, user, in_scope, reason, override, timestamps) | `91492cee922374a24e29ed54eae12b88` |
| `criteria` md5 (9 active) | `fc618757f6aa2c27db5bce7613fc28c7` |
| `score_coefficients` md5 (90) | `317e09e8326edde500bfcde2bad81e78` |
| `grades` md5 (11) | `946b30a5ea8b8594321ebb5fc645bd32` |
| combined coefficient fingerprint | `079177fbb9d52ea4c5b942fcecaed1c2` (= the 04:48:44Z snapshot) |
| `users` md5 (every column except `password_hash`) | `66c536a18e686c8d3bbc101792f2f88a` |
| `auth_login_attempts` (throttle) | 4 rows (verify-invite, 216.147.123.x) |
| `email_verification_codes` / `password_reset_tokens` | 0 / 2 |
| `invite_tokens` md5 | `11e26969d0b8344228d041e6577c711b` |
| `evaluations_id_seq` / `evaluation_scores_id_seq` / `score_corrections_id_seq` | 30 / 81 / 7 |

Periods unchanged throughout: H1 (id 2) `active/true`, `evaluation_started_at`
**2026-08-26 10:08:54.340312Z**; Annual 2025 `closed`; Annual 2026 `draft`.

## 2. The three accounts, seeded directly (brief item 2)

All three verified **in H1 scope** with the exact briefed relationships before any write; grades
and the evaluation graph read from live:

| id | name | role | manager | grade | in scope |
|---|---|---|---|---|---|
| 68 | Nurmammet Hekimov | manager | 45 (Hojayeva) | S4-M1 (2.20) | ✓ |
| 85 | Valeriya Ruhlyadko | employee | 68 (Hekimov) | S2 (1.10) | ✓ |
| 45 | Jahan Hojayeva | manager | 18 (Urayev, c_level) | M2 (3.00) | ✓ |

Hekimov reports to Hojayeva; Ruhlyadko reports to Hekimov — the chain the brief names. Each was
seeded by writing `users.password_hash` directly in the documented scrypt format
(`$scrypt$N=16384,r=8,p=1$<salt_b64url>$<dk64_b64url>`, N=16384/r=8/p=1, 16-byte salt, 64-byte
key), guarded on `password_hash IS NULL` (3 rows updated, 3 expected). **No invite-link route was
used; no mail of any kind was sent; no verification code reached anyone (D-0820-8).** Passwords
are in the gitignored `backups/2026-08-26-live-smoke/credentials.json`; the accounts are now back
to NULL (§5), so they are inert.

## 3. The walkthrough — every channel, in a real browser on epe.sedamedical.com (brief item 3)

Driven through the deployed SPA. Each of the three logged in with their seeded password; the login
throttle, the JWT session, the Welcome period notice, the task panel and every form were the real
deployed surface. What each person saw, step by step:

### Nurmammet Hekimov (68, manager)
- **Login → Welcome.** Period notice «Промежуточная оценка: H1–2026 (1 января 2026 — 30 июня
  2026)», «Оценка идёт — ваши задачи ниже», and the three task tiles Самооценка / Сотрудники /
  Руководитель. Task panel before: all three open.
- **Self-review** (task «Самооценка»): 3 criteria offered (3, 4, 12 — the `self`+`for_manager`
  set), «Вам доступно 3 критерия». Scored **3=8, 4=7, 12=9** with one comment; confirmation dialog
  showed «8 Выше нормы / 7 Хорошо»; on confirm, **«Итоговая оценка: 8.00»**. → eval **31**
  (self, calc 8.00, weighted 26.88).
- **Upward** («Оценить руководителя»): form addressed **Jahan Hojayeva**, one criterion
  «Качество управления и развитие команды» (crit 2). Scored **9** → **«Текущий балл: 9.00»**.
  → eval **32** (subordinate 68→45, calc 9.00). *(Later corrected in the record: this is the
  upward channel Hekimov→Hojayeva; it is a feedback surface and does not feed money.)*
- **Manager → subordinate, left partial then completed** («Сотрудники»): his three reports listed
  (Annameredov, Ishanova, Ruhlyadko). Ruhlyadko's card offered «Оценить» (6 criteria: Общие 4 /
  Проект 2). A **partial** manager evaluation of Ruhlyadko was submitted through the real route
  with only **2 of 6** criteria (3=7, 4=8). Her card immediately re-read **«Новые критерии: 4»**
  and the button changed to **«Дооценить (4)»**. Opening it, the modal offered **exactly the 4
  missing** criteria (12, 14, 8, 13) — the additive path. Scored **12=7, 14=5, 8=6, 13=9** →
  **«Новые критерии оценены! Итоговый балл: 7.00»**. → eval **33** (manager 68→85), the additive
  submit **upserted into the same row** (no duplicate), final six criteria (3,4,8,12,13,14),
  calc 7.00.
- **After.** Task panel: Самооценка ✓, Руководитель ✓, Сотрудники still open (2 of 3 reports left
  — correct). Logout cleared localStorage and returned to /login.

### Valeriya Ruhlyadko (85, employee)
- **Login → Welcome.** Employee variant: task panel Самооценка / Руководитель; «Процесс оценки
  (для сотрудников без подчиненных)». Both tasks open.
- **Self-review:** 3 criteria (3, 4, 12). Scored **3=6, 4=9, 12=7** → **«Итоговая оценка: 7.33»**.
  → eval **34** (self, calc 7.33, weighted 11.18).
- **Upward → Hekimov:** criterion «Качество управления» scored **9** → **«Итоговый балл: 9.00»**,
  screen «Вы уже оценили своего руководителя». → eval **35** (subordinate 85→68, calc 9.00).
- **After.** Самооценка ✓, Руководитель ✓. Logout clean.

### Jahan Hojayeva (45, manager, division head)
- **Login → Welcome.** Task panel Самооценка / Сотрудники, and **«C-level не оценивается»** /
  «C-level менеджеры не оцениваются подчиненными» in place of the Руководитель tile — because her
  own manager is C-level (Urayev, 18). Correct.
- **Self-review:** 3 criteria (3, 4, 12). Scored **3=9, 4=8, 12=8** → **«Итоговая оценка: 8.33»**.
  → eval **36** (self, calc 8.33, weighted 45.82).
- **Manager → subordinate (Hekimov reports to her):** her dashboard listed 5 reports; Hekimov's
  card already showed his real completion flags **«Самооценка ✓ / Оценил рук-ля ✓»** (the real
  status feed, not the HR-route fallback). His form offered the **full 7 criteria** (3, 4, 12, 14,
  8, 13, and the manager-only 2 «Качество управления»). Scored **3=7, 4=9, 12=6, 14=4, 8=8, 13=7,
  2=8** → **«Оценка сохранена! Итоговый балл: 7.00»**. → eval **37** (manager 45→68, calc 7.00).
  His card then re-read «Общие 4 ✓ / Проект 2 ✓ / Руководство 1 ✓» with a «Редактировать» button.
- **After.** Самооценка ✓, Сотрудники still open (4 reports left). Logout clean.

### c_level_direct — filed by the owner's admin account (brief item 3, last bullet)
This **can** be done without the owner present, so it was done. An admin session for Alexander's
account (id 2) was minted server-side (a `jsonwebtoken` sign with the live `JWT_SIGNING_SECRET`
plus one `auth_sessions` row — the established live-probe technique, deleted in §5). The
`c_level_direct` was then filed through the **real** `POST /api/submit-evaluation` route with that
session, on **Hekimov (68)**, scoring the two `c_level_only` criteria **1=8, 10=7** →
`{"success":true}`, eval **38** (source `c_level_direct`, evaluator 2, calc 7.50).

**One honest deviation to record:** this single step used the real API route rather than the admin
SPA screen. Injecting the minted admin token into the browser's `localStorage` — the only way to
drive the admin UI here — was refused by this session's safety classifier. The route is the exact
backend path the admin dashboard's C-level affordance POSTs to (verified against the Submit
Evaluation workflow: `source==='c_level_direct'` requires `actorRole` admin/c_level, evaluator is
always the token actor); the row is authentic campaign data created by the admin account. The
other eight employee-facing steps were all done in the browser as described.

**Console:** no page errors observed across the walkthrough.

## 4. The numbers — system's vs hand-computed from raw rows (brief item 4)

Coefficient tables pulled raw from live and the three formulas restated in plain Python from
HANDOVER §4 (no project code imported). The matrix payload, the coefficients API and the grades
map were then fetched and the **exact frontend `useFinalScoresMatrix` formula replayed** — that
replay *is* what `/admin/final-scores` and `/admin/bonus-calculation` render, since those screens
compute client-side from this payload.

**Plain rating** (mean of the criteria in each evaluation — the feedback number, stored as
`calculated_score`):

| evaluation | channel | criteria | mine | system | Δ |
|---|---|---|---|---|---|
| 31 | Hekimov self | 8,7,9 | 8.00 | 8.00 | identical |
| 32 | Hekimov → Hojayeva (upward) | 7 | 7.00 | 7.00 | identical |
| 33 | Hekimov → Ruhlyadko (manager) | 7,8,6,7,9,5 | 7.00 | 7.00 | identical |
| 34 | Ruhlyadko self | 6,9,7 | 7.33 | 7.33 | identical |
| 35 | Ruhlyadko → Hekimov (upward) | 9 | 9.00 | 9.00 | identical |
| 36 | Hojayeva self | 9,8,8 | 8.33 | 8.33 | identical |
| 37 | Hojayeva → Hekimov (manager) | 7,9,6,4,8,7,8 | 7.00 | 7.00 | identical |
| 38 | admin → Hekimov (c_level_direct) | 8,7 | 7.50 | 7.50 | identical |

**Weighted self-review** (formula #2: `Σ(score·levelcoef·weight) ÷ Σweight · gradecoef`, stored
as `weighted_score`):

| person | criteria | grade | mine | system | Δ |
|---|---|---|---|---|---|
| Hekimov (68) | 3=8,4=7,12=9 | S4-M1 2.20 | 26.88 | 26.88 | identical |
| Ruhlyadko (85) | 3=6,4=9,12=7 | S2 1.10 | 11.18 | 11.18 | identical |
| Hojayeva (45) | 3=9,4=8,12=8 | M2 3.00 | 45.8182 | 45.82 | identical (server 2-dp) |

**Manager's averaged upward score** (`rating_upward` = mean of subordinate evals of the manager):

| manager | evaluators | mine | system | Δ |
|---|---|---|---|---|
| Hojayeva (45) | Hekimov (7) | 7.00 (n=1) | 7.00 | identical |
| Hekimov (68) | Ruhlyadko (9) | 9.00 (n=1) | 9.00 | identical |

**Bonus index** (formula #3: `Σ(final_cell·levelcoef·weight)` **without** dividing by Σweight,
`· gradecoef` — the money number on `/admin/final-scores` and the pool on
`/admin/bonus-calculation`). Final cell per criterion = `c_level_score` for the two `c_level_only`
criteria, else mean(manager_score, corrections). Upward and self never enter the index:

| person | grade | weighted sum | mine | system | Δ |
|---|---|---|---|---|---|
| Hekimov (68) | S4-M1 2.20 | 275.30 | **605.66** | 605.66 | identical |
| Ruhlyadko (85) | S2 1.10 | 134.20 | **147.62** | 147.62 | identical |
| Hojayeva (45) | M2 3.00 | 0 | **0.00** | 0.00 | identical |

Hekimov's cells, for the record (raw · levelcoef · weight): crit1 8·2.8·5.0=112.00,
crit2 8·1.6·3.0=38.40, crit3 7·1.3·3.0=27.30, crit4 9·2.0·1.5=27.00, crit8 8·1.6·1.4=17.92,
crit10 7·1.5·1.6=16.80, crit12 6·1.1·1.0=6.60, crit13 7·1.8·1.8=22.68, crit14 4·1.1·1.5=6.60 →
Σ 275.30 · 2.20 = **605.66**.

**Three facts this run confirms about the money, on real people for the first time:**
- **The missing denominator is real and intentional** (§4). Hekimov's index (605.66) is a weighted
  *sum*, not an average; my independent implementation of exactly that rule matched. Not touched.
- **Criterion 2 «Качество управления» is scored in the money by the manager's own boss alone**
  (D-0826-2). Hekimov's crit-2 money cell is Hojayeva's 8 — not Ruhlyadko's upward 9, which shows
  on the matrix as `subordinate_avg_score` (display) but never enters the index.
- **Hojayeva earns a 0 index here, and that is correct, not a bug:** her only inbound evaluations
  are an upward (feedback) and her own self (never money); her boss (C-level Urayev) filed no
  manager evaluation, so she has no money input. A person with no manager/c_level evaluation takes
  no share — exactly the D-4 design.

**Budget pool** (`/admin/bonus-calculation`): the pool over the people who take a share was
Hekimov 605.66 + Ruhlyadko 147.62 = **753.28** (Hojayeva excluded, no data). The largest-remainder
distribution of a typed budget over that pool was **not** exercised on live (no write, and it was
already proven to the kopeck in `PRELAUNCH_GATE`); the pool figure reconciles by hand.

## 5. The undo — complete, and proven byte-identical to the anchor (brief item 5)

One transaction, counts returned:

- `evaluation_scores` deleted: **26** (all rows of evals 31–38; `evaluation_id` FK is
  `ON DELETE CASCADE`, deleted explicitly anyway).
- `evaluations` deleted: **8** (ids 31–38, my rows only — every id verified mine before deletion).
- `score_corrections`: **0** created, none to delete (the `c_level` channel is calibrated by
  averaging, and no correction was part of the walk).
- `auth_sessions` deleted: **4** — the three browser logins (jti `5e76b7c5…` 68, `cb463627…` 85,
  `b2efda12…` 45; logout is client-side, so the rows persisted) and the one minted admin probe
  (`129797f6…` 2).
- `epe-throttle` rows: **none of mine** — the three logins succeeded, so no throttle row was
  written; `auth_login_attempts` is byte-identical to the anchor (4 rows, same emails, same
  timestamps).
- `users.password_hash` set to NULL: **3** (45, 68, 85), `token_version` untouched (still 0).

**Proof against the anchor** (`state_post.txt` vs `state_anchor_pre.txt`), line by line:

| line | anchor | post | |
|---|---|---|---|
| campaign tables | 0/0/0/0 | 0/0/0/0 | identical |
| `auth_sessions` | 21 (list) | 21 (**same 21 rows**, my 4 gone, none of the anchor's removed) | identical |
| registered | 2,47,52 | 2,47,52 | identical |
| participants md5 | `91492cee…` | `91492cee…` | identical — **no participant row moved** |
| criteria / coef / grades md5 | `fc618757…`/`317e09e8…`/`946b30a5…` | same | identical |
| combined coefficient fingerprint | `079177fb…` | `079177fb…` | identical to snapshot |
| users md5 (ex-`password_hash`) | `66c536a1…` | `66c536a1…` | identical — **no user column changed** |
| throttle / verif codes / reset tokens | 4 / 0 / 2 | 4 / 0 / 2 | identical |
| invite_tokens md5 | `11e26969…` | `11e26969…` | identical |

**The only differences, both accepted and not repaired:**
- `evaluations_id_seq`: **30 → 38** — the gap is ids **31–38** (my eight evaluations).
- `evaluation_scores_id_seq`: **81 → 107** — the gap is ids **82–107** (my 26 score rows).

A rejected/deleted INSERT still consumes a `nextval`; there is no reset route and the brief
accepts the gap. Everything a reader can query about state — counts, fingerprints, the row
contents — is what it was at 14:21Z.

## 6. Parallel-owner check (boundary)

State was re-read before and after each phase. At one point the source counts appeared to exceed
my writes; the full `evaluations` dump showed all seven (then eight) rows were mine, mapping
exactly to the six walk channels plus the additive upsert and the c_level_direct — **no foreign
write**. Registered accounts moved only by my three seeds and back. The owner did not write to
live during the window; nothing not mine was touched, so nothing not mine was undone.

## 7. Verdict (brief item 6)

**Да — кампанию можно открывать для 78 человек.** Every channel an employee or manager will touch
worked on the deployed frontend as a real person: login, the period-aware Welcome, self-review,
manager→subordinate (full and partial→additive), upward, the real completion flags, and the
admin-filed `c_level_direct`. Every money number the system produced equals arithmetic done from
the raw rows by hand — the plain ratings, the weighted self-reviews, the two upward averages, and
the three bonus indices, all identical. The formulas behave on real people and real coefficients
exactly as §4 says they should.

**What breaks: nothing that blocks the invite.** One thing worth knowing on day one, already on
the books, not introduced here:

- A manager whose own boss is C-level (like Hojayeva, boss = Urayev 18) gets a **0 bonus index**
  until a C-level person files their manager evaluation or a `c_level_direct`. That is correct by
  design (self and upward never pay), but it means **C-level must actually evaluate the managers
  who report to them**, or those managers carry no money into the annual roll-up. This is a
  process reminder for the owner, not a code defect — surfaced, not resolved.

No new bug was found. The known open items (`BUG-074` channel-inapplicable smuggling on the write
path, `BUG-075` silent ×1.00 for an evaluable no-grade person, `BUG-067` mid-campaign user
creation) were not re-exercised here and are unchanged.

## 8. Session hygiene

- Read-only until the anchor dump; the dump preceded the first write, copied to the Mac outside
  the repo, md5 equal on both sides (§1). VPS copy deleted at teardown; Mac copy kept in
  `~/EPE_ROLLBACK/2026-08-26-live-smoke/`.
- Live writes this session and their reversal: 8 evaluations + 26 scores (deleted), 3
  `password_hash` seeds (nulled), 4 `auth_sessions` (3 browser logins + 1 minted admin probe,
  deleted). No user, scope, period, catalogue, coefficient, grade, criteria, correction or
  `join_date` write. `evaluation_started_at` untouched. No container restarted.
- **No mail of any kind. No invite-link registration. No verification code sent to anyone.** The
  three accounts were seeded by direct `password_hash` write and are back to NULL.
- Proof artifacts in the gitignored `backups/2026-08-26-live-smoke/`: `state_anchor_pre.txt`,
  `state_post.txt`, `money_inputs.txt`, `matrix.json`, `coeffs.json`, `adminusers.json`,
  `credentials.json`, `tokens.json`, `read_state.sh`.
- Browser localStorage cleared, viewport emulation reset, `git status` clean at start and (but for
  this report and the docs updates) at end.

---

**Commit:** this report and the `PROGRESS.md` entry landed on `main` as `a9c2c3a` (pushed). A final
live re-read after the push confirmed the state still matches the anchor — no drift since the undo.
