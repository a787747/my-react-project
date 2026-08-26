# Mid-year hires — taking an employed person out of one period's scope (2026-08-25)

**Brief:** MID_YEAR_HIRES_SCOPE. **Decision:** D-0825-10.

**Outcome in one line: an admin can now take an EMPLOYED person out of the
scope of an existing period, with a distinct reason and an append-only record,
without touching their employment, their login or their capability columns —
and put them back exactly — proven on a throwaway stand by 152 checks including
two real closes of two copies of one dump, then deployed to live, where 1 958
cells over all 89 people show zero changes, the second gate is still unpressed,
and NOBODY has been excluded.**

Live writes: migration 016 at **17:55Z**, one new workflow created and activated
at **17:56:16Z**. **No existing workflow was written.** **Nobody was excluded on
live.** This session shipped the capability; the list of names is the owner's and
he has not given it yet.

---

## 0. Read this first: the brief's premise moved while it was being written

The brief says «Two terminations have since been applied; 85 are in scope».

At the first live reading of this session — **2026-08-25 17:23Z** — there were
**three** terminations and **84** in scope. The third is **Halykberdi Orusov
(39)**, terminated at **17:11:54Z**, last working day 2026-06-01, actor id 2.
That is twelve minutes before this session's first SELECT, so the owner was
working in the portal while the brief was being written.

Everything in this report is measured against 89 users / 3 terminated / **84**
in scope, not 85. The acceptance line «89 users, 2 terminated, 85 in scope» is
therefore reported as **89 / 3 / 84**, verified, and flagged rather than
silently satisfied.

---

## 1. Read-only first — what the database says

All numbers below are SELECTs taken between **17:23Z and 17:35Z** on live
`epe_2026`, and again at **17:57Z** after the deployment. Nothing was read from
a previous report.

### 1.1 The scope rule, re-verified in the live code

`docs/TERMINATED_EMPLOYEES_2026-08-25.md` §1.2 says `is_in_scope` is written by
exactly one route, at period creation. Re-checked this session against every one
of the **60** workflows in live `workflow_entity`, archived ones included, by
regex over the node graphs:

| workflow | what it does to `evaluation_period_participants` |
|---|---|
| `API: Manage Periods` | one `INSERT` — the participants CTE inside `POST /api/periods/create` |
| `API: Manage Employment Status` | two `UPDATE`s — terminate and reinstate (D-0825-7) |

Nothing else writes it, and seven workflows read it (`evaluations-matrix`,
`Get Employees`, `HR Evaluation Status`, `Submit Evaluation`,
`Submit Self Review`, plus the two writers). So before this session there was
still **no way to take an employed person out of an existing period's scope**
except raw SQL — the gap the brief exists to close.

The rule itself, copied from the live `Build Create SQL` node:

```sql
CASE
  WHEN u.terminated_at IS NOT NULL THEN false
  WHEN u.join_date IS NOT NULL AND u.join_date > '<end_date>'::date THEN false
  ELSE true
END
```

Read the second branch carefully. `join_date IS NOT NULL AND …` means a person
with **no join date at all** falls through to `ELSE true` — in scope, no reason,
no mark. That is the silent case the brief asked about, and §1.3 names the one
person it applies to.

### 1.2 Everyone who joined in 2026 — thirteen people

Full per-person detail, in Russian and one line each, is the owner's marking
sheet: `docs/MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md`. The engineering
summary:

| join date | id | name | dept | category | crit. | H1 (period 2) | Annual 2026 (period 5) |
|---|---|---|---|---|---|---|---|
| 2026-01-07 | 51 | Kuvvat Garayev | Project | project | 6 | **out — `terminated`** (15:54:23Z today) | out — `terminated` |
| 2026-02-05 | 57 | Mahrijemal Annamyradova | Seda Academy Project | project | 6 | in | in |
| 2026-02-20 | 42 | Mekan Hummedov | Pharma Division | general | 5 | in | in |
| 2026-03-02 | 8 | Arslan Annayev | Project | project | 6 | in | in |
| 2026-03-02 | 30 | Amangozel Bayramgeldiyeva | Administration | general | 4 | in | in |
| 2026-03-03 | 71 | Rakhim Kurbanov | Project | project | 6 | in | in |
| 2026-03-24 | 23 | Cheper Atakayeva | Project | project | 6 | in | in |
| 2026-04-09 | 25 | David Asatryan | Technical | project | 6 | in | in |
| 2026-04-27 | 64 | Mive Atayeva | Accounting | general | 4 | in | in |
| 2026-05-01 | 22 | Muhammet-Ali Chariyev | Logistics | general | 4 | in | in |
| 2026-05-01 | 63 | Merjen Jumayeva | Sales | general | 4 | in | in |
| 2026-07-06 | 31 | Aysoltan Esenova | Clinical Lab Solutions | general | 4 | **out — `hired_after_period_end`** | in |
| 2026-07-13 | 35 | Govher Balova | Logistics | general | 4 | **out — `hired_after_period_end`** | in |

**Nobody joined in June.** There is no recorded hire between 2026-05-01 and
2026-07-06. So the owner's report cannot be resolved by re-running the hire-date
rule: if somebody in the January–May block really started in the second half of
the year, the card is wrong, and only he can say which card.

Registration: **2 of 89** people company-wide have a password (Alexander id 2,
Jemal Gulberdiyeva id 47). **None of the thirteen 2026 joiners has registered.**

Participation rows, exact values:

- ids 57, 42, 8, 30, 71, 23, 25, 64, 22, 63 — period 2 `is_in_scope=true`,
  `exclusion_reason=NULL`, `created_at = updated_at = 2026-08-18 14:29:02.470198`
  (never touched since import).
- id 51 — period 2 and 5 `is_in_scope=false`, `exclusion_reason='terminated'`,
  `created_at` as above, `updated_at = 2026-08-25 15:54:23.988670`.
- ids 31, 35 — period 2 `is_in_scope=false`,
  `exclusion_reason='hired_after_period_end'`, `created_at = updated_at =
  2026-08-18 14:29:02.470198`; period 5 **in scope** — correctly, the annual
  container runs 2026-01-01…2026-12-31 and they are inside it.

### 1.3 The dangerous ones: NULL, empty or implausible join dates

**Exactly one: Cem Durukan (21), General Manager.** `join_date IS NULL`. The
only NULL in 89 rows. By §1.1 he was **silently kept in scope** of both periods
— no reason, no flag, indistinguishable in the participants table from somebody
with ten years' service.

Today it costs nothing: he is `can_evaluate=false` and `can_be_evaluated=false`
(D-0821-4), has no grade and no manager, and his `c_level` role cannot submit a
self-review. He can neither receive a score nor give one, so no money number can
reach him. **The rule survives him, though**, and will fire the same way when H2
is created — including for anybody entered in advance of their start date.
Filed as **BUG-066**; not fixed, because whether an unknown hire date should
mean "in" or "out" is the owner's call, and §5 explains why.

Nothing else is out of the ordinary. Earliest hire 2011-02-14, latest
2026-07-13; no future dates; no date before 2011; no join date later than a
termination date; no Jan-1 placeholder block (the most common day is 05-01 with
five people, consistent with real hiring, not with a bulk import default).

### 1.4 People with no participants row — and what "no row" does

**There are none today.** All 89 people have a row on period 2 and on period 5,
and there is no orphan participant row pointing at a missing user.

The question still matters, because participation rows are written **once**, at
period creation. Anybody entered into `users` after 2026-08-18 14:29 would have
no row for H1. Both routes that can create a user (`admin/save-user` and the
Excel import that posts through it) write `users` only.

Answering the brief's question directly — **is "no row" the same as "row with
`is_in_scope=false`"? Everywhere except one place, yes.** Established first by
reading every route that touches the table, then *measured* on the stand with a
fixture (1610) that genuinely has no row for period 2 next to one (1603) that
was excluded through the new route:

| surface | no row | row, `is_in_scope=false` | same? |
|---|---|---|---|
| Manager's task list (`GET /api/employees` → `scoped`) | absent (`JOIN … AND epp.is_in_scope=true`) | absent | **yes** |
| Their own read (`actor_is_in_scope`) | `false` (`COALESCE((SELECT …), false)`) | `false` | **yes** |
| `in_scope_count` on `/api/periods` | not counted | not counted | **yes** |
| HR completion (`in_scope` CTE, `sub_counts`, `in_scope_count`) | absent from both list and denominator | absent from both | **yes** |
| `POST /api/self-review-submit` | 403 `NOT_IN_SCOPE` | 403 `NOT_IN_SCOPE` | **yes** |
| `POST /api/submit-evaluation` (as subject or actor) | 403 | 403 | **yes** |
| Admin matrix / Итоговые баллы (`LEFT JOIN … COALESCE(is_in_scope,false)`) | **row emitted**, marked out of scope, cells empty | **row emitted**, marked out of scope, cells empty | **yes** |
| **`period_results` at close** | **NO ROW AT ALL** | row with `is_in_scope=false, has_data=false`, every rating and both money columns NULL | **NO** |

The close builds its dataset by iterating `evaluation_period_participants` for
the period. No participants row means no frozen row — the person simply is not
in the closed period's record. Measured on the stand: 1610 has no
`period_results` row in either the control or the treatment close, while the
excluded 1603 has one in both, marked out of scope.

**Neither costs a penny** — an out-of-scope frozen row is forbidden by the table's
own CHECKs from carrying a number — so the difference is not money, it is
evidence. An excluded person leaves a record saying "was a participant of this
period, out of scope, no data"; a person with no row leaves nothing, and a year
later the closed period cannot be asked whether they existed. Filed as
**BUG-067**.

---

## 2. What was built

### 2.1 Migration 016 — additive only

`migrations/016_add_period_scope_events.sql`. Applied to live 17:55Z, then
applied a second time to prove idempotence (three `already exists, skipping`
notices, no error).

`performance_db.period_scope_events` — append-only: `id, period_id NOT NULL,
user_id NOT NULL, event_type ('excluded'|'included'), reason, actor_id NOT NULL,
occurred_at, note`, three foreign keys **without** `ON DELETE CASCADE`, two
indexes, and two CHECKs:

- `chk_period_scope_events_type` — the event is `excluded` or `included`.
- `chk_period_scope_events_reason_pairing` —
  `(event_type='excluded') = (reason IS NOT NULL)`. An exclusion without its
  reason is exactly the row that cannot say why the pool lost somebody; an
  inclusion carries no reason because being in scope is the default state.

**No new column on `users`.** Being out of one period is not a property of the
person; it is a property of the (period, person) pair, which
`evaluation_period_participants` already is.

**Why not `employment_events`.** Migration 015's own comment scopes that table to
employment events, and D-0825-7 leans on that. The people this brief is for are
employed, keep their login, and will be evaluated in H2. Filing them under
"employment events" would make a future reader believe they left the company. The
two records also answer different questions: one is "is this person still with
us", the other is "which periods was this person deliberately kept out of, and on
whose signature" — which is why `period_id` is `NOT NULL` here and nullable
there.

On live after the migration: **0 rows**, and **0** people carrying
`exclusion_reason = 'excluded_by_admin'`.

### 2.2 One new workflow — `API: Manage Period Scope`

Live id **`8xK4EnDJrH1b1OJ7`**, 25 nodes, active,
`updatedAt=2026-08-25T17:56:16.087Z`. Three admin-only routes:

| route | body / query |
|---|---|
| `POST /api/admin/exclude-participant` | `{period_id, user_id, note?, confirm_existing_evaluations?}` |
| `POST /api/admin/include-participant` | `{period_id, user_id, note?}` |
| `GET /api/admin/period-scope-events` | optional `?user_id=` / `?period_id=` |

Exclusion is **one SQL statement**. Every precondition is re-asserted inside the
`target` CTE (`is_in_scope = true`, period `status <> 'closed'`, `FOR UPDATE`),
so a lost race selects zero rows and both branches below it change zero rows —
the same one-gate rule the close, termination and additive-submit paths use. It
sets `is_in_scope=false, exclusion_reason='excluded_by_admin', updated_at=now()`
on **one** row, and appends one event. That is the entire write.

**What it deliberately does not do**, each one a line that exists in the
termination route and is absent here:

- no `users` write of any kind — not `terminated_at`, not `token_version`;
- no `auth_sessions` revoke, so a session already held keeps working;
- no `password_reset_tokens` burn, so a reset link is still issued;
- no `can_evaluate` / `can_be_evaluated` write — D-0821-4's policy flags stay the
  owner's;
- **only the named period.** Termination scopes a person out of every non-closed
  period; this touches one row, so H2 and the annual container are untouched.
- **`API: Manage Periods` is NOT changed.** A person excluded from H1 by hand
  must enter H2 normally when H2 is created. The deploy script asserts its
  `UPDATES` list is empty, so a future edit that quietly adds a PUT has to say so
  in the diff.

`exclusion_reason='excluded_by_admin'` is distinct by construction from
`'terminated'` and `'hired_after_period_end'`. The reverse action flips back
**only** rows whose reason is exactly `'excluded_by_admin'`, mirroring what
reinstatement does for `'terminated'`, so the three populations can never blur
and neither reverse action can undo the other's work. Proven, §3.5.

Refusals, each by name and in this order:

| refusal | code | when |
|---|---|---|
| `TOKEN_MISSING` / `TOKEN_INVALID` | 401 | unauthenticated |
| `ROLE_FORBIDDEN` | 403 | any role but `admin` |
| `INVALID_USER_ID` / `INVALID_PERIOD_ID` | 422 | not a positive integer |
| `USER_NOT_FOUND` | 404 | no such person |
| `PERIOD_NOT_FOUND` | 404 | no such period |
| `PERIOD_CLOSED` | 422 | the period is closed — in either direction |
| `NOT_A_PARTICIPANT` | 404 | the person has no participants row for that period (§1.4) |
| `ALREADY_EXCLUDED` | 409 | already out of scope; the message names the reason already there |
| **`HAS_EVALUATIONS`** | **409** | **the person already has evaluation data in that period and the caller did not confirm** |
| `NOT_EXCLUDED_BY_ADMIN` | 409 | reverse action, on somebody in scope or excluded for another reason |
| `SCOPE_CONFLICT` | 409 | the row moved between the pre-check and the statement; nothing written |

**The confirmation gate states the consequence instead of deciding it.** Verbatim
from the stand:

> В периоде «H1-2026» у сотрудника уже есть данные оценки. Ничего не будет
> удалено. Оценки, которые он ПОЛУЧИЛ (2) и его самооценка (1) останутся в базе
> и перестанут на него считаться: при закрытии периода он замёрзнет как «вне
> охвата, данных нет», без единой цифры. Оценки, которые он ПОСТАВИЛ другим (1),
> продолжат считаться этим другим полностью. Корректировок по нему: 0. Повторите
> запрос с confirm_existing_evaluations=true, если это то, чего вы хотите.

The counts are real reads, split GAVE / ABOUT, and the same numbers ride on the
200 response so the record and the screen agree.

### 2.3 Two decisions this brief did not name, surfaced rather than buried

- **Direct reports do not block an exclusion — they are reported.** Termination
  refuses `HAS_DIRECT_REPORTS`, because a terminated manager leaves their reports
  evaluated by nobody. The same is true here: an out-of-scope actor gets an empty
  task list. But a manager who genuinely started in the second half of the year
  must be excludable — id 42 Mekan Hummedov, hired 2026-02-20, is exactly that
  shape with one report — so the route **lists their in-scope direct reports in
  the response and in the `HAS_EVALUATIONS` refusal** and lets the caller
  proceed. Reassigning or also excluding those people is the owner's decision,
  not this route's. Demonstrated on the stand: asking to exclude the fixture
  manager returns
  `reports_in_scope: [{1603 MY LateStart}, {1604 MY Stayer A}, {1605 MY Stayer B}]`
  — and not the fourth report, who was never in scope.
- **Self-exclusion is allowed.** Termination refuses it because reinstatement is
  admin-only and a self-terminated admin would be locked out. Scope is not a
  door: the admin routes do not read `is_in_scope`, so an admin who excludes
  themselves can put themselves back with the same call. Refusing it would have
  been an unreachable guarantee.

### 2.4 No screen was built, and why

Termination shipped with a screen. This did not, deliberately: the working tree
carries **uncommitted frontend edits that are not this session's** (§6), and a
frontend deploy tars the whole tree. Building a screen here would mean either
shipping somebody else's in-flight work or leaving an undeployed component in
the repo as a trap for the next deploy. The owner has not given the list of
names yet, so nothing is blocked today. The hand-run path is §5; a screen is a
follow-up whose cost is an hour, and it is the owner's call whether it is worth
one before he has decided the names.

---

## 3. The stand proof

`scripts/setup_midyear_throwaway.sh` → `scripts/prove_midyear_scope.py` →
`scripts/teardown_midyear_throwaway.sh`. Proof artifact:
`backups/2026-08-25-midyear-scope/midyear_scope_proof.json`, **152 checks, 152
passed, `failures: []`**. Every check records the values it compared on both
sides; the run ends with a meta-check that it compared more than 80 things, so a
vacuous run fails instead of printing a slogan.

**Two databases, one dump.** `epe_mid_20260825_1750_ctl` and `…_trt`, restored
from the same dated dump of live, asserted to start with an identical
evaluations fingerprint (`5548c2cf3569a781d08426a4f94e745f`, 46 rows on both
sides). That is what makes the money claim provable: the two closed
`period_results` sets differ **only** by the exclusion, because they started
byte-identical. Synthetic fixtures 1601–1611 with real scrypt logins, distinct
grade coefficients so no arithmetic can pass on a 1.0 fallback, and distinct
scores so a dropped evaluation moves a printed number instead of hiding in an
average. No real person's row is touched.

Two earlier runs of the same script found **three defects in the proof itself** —
two assertions that the stand's `employment_events` table would be empty (it is a
copy of live, which now carries the owner's three terminations) and a
cross-stand fingerprint that included `updated_at` (the two copies were seeded
microseconds apart). All three were test bugs, none was a build bug; they are
recorded here because a proof that was quietly relaxed to pass is worth nothing.
The stand was rebuilt from scratch and re-run.

### 3.1 The GAVE / ABOUT split, to the digit

1603 «MY LateStart» — join date 2026-02-05, an H1 hire on paper — both gave
(upward → 1602) and received (manager ← 1602, self, c_level ← 1606). Both stands
were closed through the real `POST /api/periods/close`, and `period_results`
compared:

| | control (nobody excluded) | treatment (1603 excluded) |
|---|---|---|
| **1602, the manager they evaluated** | | |
| `rating_manager` | 7.40 | **7.40** |
| `rating_upward` | 6.33 | **6.33** |
| `rating_c_level_direct` | 5.50 | **5.50** |
| `final_rating` | 6.8571 | **6.8571** |
| `bonus_index` | 170.8300 | **170.8300** |
| **1603, the excluded person** | | |
| `is_in_scope` | true | **false** |
| `has_data` | true | **false** |
| `rating_manager` | 7.00 | **null** |
| `rating_c_level_direct` | 6.50 | **null** |
| `rating_self` | 8.00 | **null** |
| `final_rating` | 6.8750 | **null** |
| `bonus_index` | **108.3240** | **null** |

`rating_upward` for 1602 is the load-bearing number. It is the mean of three
upward evaluations — 9.0 from the excluded person, 4.0 and 6.0 from the two who
stayed. If exclusion had dropped the evaluation they *gave*, it would read
**5.00**. It reads **6.33 on both sides**.

**Rows that moved besides 1603's: `[]`** — every other person's stored result is
identical between the two closes, cell by cell, over **99 rows** on each side.
Neither close produced a row the other did not.

**The pool.** Total `bonus_index` over everybody: **410.842** control,
**302.518** treatment, difference **108.324** — equal to the excluded person's
index to four decimals. The pool shrank by exactly their share and by nothing
else.

**Going into the close**, the two participants tables were compared row by row
and differ in **exactly one**: `2:1603`. That is the check that makes
"nobody else moved" mean something.

### 3.2 Every evaluation row, byte-identical

46 evaluation/score rows fingerprinted before and after. md5
`f7a773cbe6ebd5059dd0ee2261d56e6d` before the exclusion,
`f7a773cbe6ebd5059dd0ee2261d56e6d` after, and the same again after the whole
exclude → include → exclude sequence. Row count 46 → 46.

**And the users table did not move either.** A full snapshot of all 100 rows ×
22 columns before and after shows **zero** differences except two deliberate
registrations (§3.3). For the excluded person specifically: **not one column
changed** — not `terminated_at`, not `termination_date`, not `can_evaluate`, not
`can_be_evaluated`, and not `token_version`.

### 3.3 The login stays, and that is the whole point

| claim | evidence |
|---|---|
| Can still log in | `POST /auth/login` → **200** with a working token, after exclusion |
| The session they already held is not revoked | the pre-exclusion token still answers 200 on `/api/employees` — but now reads `actor_is_in_scope=false` |
| Can still register through the shared invite | a never-registered fixture excluded by the route registered **200** and its `password_hash` was set. Under termination the same call is **400** |
| A password reset link is still issued | one row in `password_reset_tokens`. Under termination: zero |
| Cannot be evaluated | manager → 403 `SCOPE_MISMATCH`; `c_level_direct` → 403 |
| Cannot evaluate | self-review → 403 `NOT_IN_SCOPE`; upward on their manager → 403 |
| Leaves the manager's task list | 3 cards → 2, and exactly the excluded person is missing |
| Leaves the HR completion count | `in_scope_count` 93 → 92; the manager's `total_subordinates` 3 → 2; the person absent from the HR list |
| Leaves the campaign counter | `/api/periods` `in_scope_count` 93 → 92 |
| Nothing was deleted | `participant_count` unchanged at 99 |
| The other period is untouched | the period-5 row is byte-identical before and after — unlike a termination, which takes both |
| Somebody else's reason survives | the `hired_after_period_end` fixture is byte-identical throughout |
| The record | actor id, period id, event type, machine reason and the owner's note («вышел на работу в сентябре») |
| Refusals write nothing | after all eleven refusals: evaluations md5 unchanged, zero scope events, zero user-row changes, participants table byte-identical |

### 3.4 The reverse action is exact

`POST /api/admin/include-participant` → 200, and the **entire participants
table** — every period, every person, `is_in_scope` and `exclusion_reason` —
compares equal to its state before the exclusion. The manager's task list returns
to the same membership; the campaign counter returns to 93.

The log keeps the history rather than the state: `['excluded', 'included']` for
one person, with the inclusion carrying `reason = NULL`. The record is readable
through `GET /api/admin/period-scope-events` (200, filterable by `user_id`), and
that route answers **403** to a manager.

The only residue on the row is `updated_at`, which moved twice and is what that
column is for. `token_version` did not move at all — unlike reinstatement, which
deliberately leaves a bumped one behind.

### 3.5 Two reasons in one database, and two reverse actions that do not cross

A real leaver (1611) was terminated through the **real** `POST
/api/admin/terminate-employee` while 1603 was excluded, so all three reasons
stood side by side:

- `excluded_by_admin` — 1603, out of period 2 **only**, period 5 still in scope.
- `terminated` — 1611, out of period 2 **and** 5.
- `hired_after_period_end` — 1607, untouched throughout.

`include-participant` on the leaver → **409 `NOT_EXCLUDED_BY_ADMIN`**, naming
`terminated` as the reason it will not touch. `reinstate-employee` on the leaver
→ 200, and it did **not** put the excluded person back. The two machines share a
column and never each other's rows.

### 3.6 Teardown

Container `epe-mid-n8n` removed; both `epe_mid_*` databases dropped (the drop
loop refuses any name without the prefix, so `epe_2026` can never be a
candidate); `SELECT datname` afterwards lists **`epe_2026, postgres`** only; the
six containers on the host are the same six as before; the stand tunnel is
closed. No container this project does not own was touched, and nothing was
restarted outside the stand. The stand ran twice (§3) and both instances were
torn down.

---

## 4. Live: what changed, and the proof that nothing else did

### 4.1 The rollback anchor

| | |
|---|---|
| File | `epe_2026_premidyear_20260825T175516Z.dump` |
| Taken | 2026-08-25 **17:55:16Z**, `pg_dump -Fc --no-owner --no-acl` of live `epe_2026`, **before the first live write** |
| Size | **87 912 bytes** |
| md5 | **`d7b2260d479814734d671b603e5f3267`** — verified equal on both copies |
| On the VPS | `/root/epe_stand_tmp/epe_2026_premidyear_20260825T175516Z.dump`, mode 600 |
| On the Mac | `~/EPE_ROLLBACK/2026-08-25-midyear-scope/…`, mode 600, **outside the repository** |

**This one supersedes every earlier anchor**, including
`epe_2026_pretermination_20260825T153238Z.dump` (15:32Z) and the two `pregate`
dumps (`121617Z`, `141806Z`) still on the VPS. It is the only anchor taken after
the owner's third termination at 17:11Z; restoring any older one would silently
un-terminate Halykberdi Orusov. The three older files are left in place and are
history.

### 4.2 Drift — cell by cell, independently

The anchor was restored into a throwaway `epe_midverify_20260825175708` and every
column of every user compared against live. `dblink` was **not** created on live
(a previous brief did that by accident and had to undo it); both sides were
exported as JSON instead.

**1 958 cells compared (89 people × 22 columns). Zero changed.**

Migration 016 adds a table, not a column, so the anchor and live share the same
column list and the diff covers all of it — the frozen columns
(`salary_current`, `salary_proposed`, `join_date`, `password_hash`,
`can_evaluate`, `can_be_evaluated`, `token_version`, `employment_type`,
`created_at`) and the two termination columns alike, checked by name as well as
by the full diff. The three terminated people are still exactly three, unchanged.

> **Superseded for future drift checks (D-0826-4, 2026-08-26):** this paragraph
> correctly describes what this 25-August brief was allowed to change. It is no
> longer the product-wide frozen-column list: `join_date` is now admin-editable
> and an intended card change is ordinary owner activity, not an incident.
The throwaway was dropped; `SELECT datname` afterwards is `epe_2026, postgres`.

Every other table, fingerprinted on both sides and **identical**:

| table | md5 |
|---|---|
| `criteria` | `0b1db252890b64f4c7b6a19b3c0a7a19` |
| `score_coefficients` | `c1c04b2791443979ebb045d06e008da2` |
| `grades` | `bb1d249f012ed8ace70d4253399f0af3` |
| `departments` | `e15c12ae4e2e8a5d047cd1259300ff0c` |
| `evaluation_periods` | `1d4a866479c046682e5dc1a4821d2652` |
| `evaluation_period_participants` | `d9d349896b022f4897308070a350e6f5` |

The first five match the values `docs/TERMINATED_EMPLOYEES_2026-08-25.md` §4.2
recorded at 15:3xZ, so the catalogue, the coefficients, the grades, the
departments and the periods have not moved since that brief either. The
participants fingerprint differs from that report's, and correctly so: the
owner's three terminations rewrote six rows between the two readings.

Distributions, recomputed on both sides of the anchor:

```
criteria per person   before: 4 -> 37,  5 -> 10,  6 -> 35,  7 -> 7     (89)
                      after : 4 -> 37,  5 -> 10,  6 -> 35,  7 -> 7     (89)

work_category         before: general 47 / project 42
                      after : general 47 / project 42
```

Unchanged, as intended. (Both differ from HANDOVER §3's `37/11/36/5` and
`48 general / 41 project`: the owner has been editing classification and
hierarchy all day. Those are his edits, not this brief's — the anchor and live
agree exactly, which is the claim being made here.)

### 4.3 Invariants after

| check | result |
|---|---|
| Users | **89** |
| Terminated | **3** (ids 39, 51, 66) — the owner's, untouched |
| In scope of H1 | **84 of 89** |
| H1-2026 | `status=active`, `is_active=true` |
| `evaluation_started_at` | **NULL on all three periods** — the second gate is unpressed and no route that could press it was called |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| `period_scope_events` | **0** — nobody was excluded |
| people with `exclusion_reason='excluded_by_admin'` | **0 of 89** |
| `employment_events` | **3** — the owner's terminations, unchanged |
| Extensions on live | `plpgsql` only |
| `auth_sessions` | 14 → 14; the probe session was minted and deleted in a `finally` |
| Workflows | 59 → **60** (38 unarchived, 35 active, 22 archived); webhooks 45 → **48** |
| Existing workflows written | **none** |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — the frozen value, before and after |

### 4.4 The read surface agrees

Read-only probe through Caddy with a real admin token, session deleted
afterwards:

- `GET /api/admin-users-data` → 200, **89** rows, exactly three carrying
  `terminated_at`.
- `GET /api/admin/period-scope-events` → 200, `events: []`.
- `GET /api/admin/employment-events` → 200, three events.
- `GET /api/periods` → 200, H1 `status=active`, `evaluation_started=false`,
  **84 / 89**.
- `GET /api/employees` → 200, `campaign_active=false`,
  `period_in_preparation=true`.
- The three new routes with an invalid token → **401 `TOKEN_INVALID`** each.

Report: `backups/2026-08-25-midyear-scope/live_verify.json`, **43 checks, 43
passed**.

---

## 5. Surfaced, not resolved

### 5.1 A NULL join date silently keeps a person in scope — BUG-066

§1.1 and §1.3. One person today (Cem Durukan, 21), harmless today, and the rule
is unchanged for H2. Not fixed because the fix is a decision, not a line of code:
either the owner fills the date in, or the rule is rewritten so an unknown hire
date means **out** of scope and needs an explicit hand-inclusion — which is now
possible, because `include-participant` exists. The second is safer (money never
lands on somebody nobody checked) and noisier (every advance-entered hire needs a
click).

### 5.2 A person added after a period exists gets no row, and no frozen record — BUG-067

§1.4. Nobody is in this state today. The read surfaces all behave identically to
an explicit exclusion; the close does not. `admin/save-user` and the Excel import
both write `users` only, so the state is one ordinary admin action away, and the
new `exclude-participant` route refuses such a person by name
(`NOT_A_PARTICIPANT`) rather than inventing a participation they never had. The
durable fix is for user creation to insert a participants row into every
non-closed period — a change to the most dangerous write path in the system,
which is why it is filed rather than made.

### 5.3 Score correction never checks scope — BUG-068

`API: Score Correction` joins no participants row at all. A correction can
therefore be written for somebody out of scope — excluded, terminated, or out by
hire date. It cannot move money (their frozen row is `has_data=false` and the
table's CHECKs forbid a number on it), but it writes a row about a person who is
not in the period. Pre-existing since D-0820-9; this brief neither introduced nor
fixed it, and no correction exists on live.

### 5.4 The screen

§2.4. No UI was built. The hand-run path is §7. Whether a screen is worth
building before the owner has picked the names is his call.

### 5.5 Untouched, and still true

Criterion 14's live level curve is still `0.70/1.00/1.00/1.10/1.20/1.50/2.00/
3.00/5.00/7.00` against the approved `0.20/0.25/…/6.00` (HANDOVER §3, BUG-050
territory). Re-read this session, not touched, still unresolved. No catalogue,
coefficient, criteria, grade, department, period or user write of any kind was
made. **The second gate was not pressed and no route that could press it was
called** — the deploy script refuses to run at all if any period has been
started.

BUG-060 (a person out of scope still occupies a row on the admin money matrix)
applies to this population exactly as it does to leavers, and this brief measured
it again on the stand: the excluded person's matrix row is emitted with
`is_in_scope=false` and empty cells. Cosmetic, not money; still open, still the
owner's product decision.

---

## 6. The working tree was not mine alone

`git status` at session start carried two modified files this session did not
write:

- `src/components/Sidebar.jsx` — a nesting/spacing change to the navigation
  groups.
- `PROGRESS.md` — an entry describing it, deployed to live as release
  **`20260825T170810Z`** and explicitly marked «Not committed».

Per the brief they were **not stashed, not reverted, and not built or deployed by
this session**. No frontend build ran and no frontend release was created here;
live still serves `20260825T170810Z`, which is the other session's own deploy.
They are committed — in their own commit, separate from this brief's, and
labelled as somebody else's already-live work — because PROJECT_RULES makes a
silently dirty tree the thing that turned the 2026-08-22 parallel session into a
live incident, and because the acceptance line asks for a clean `git status`.
Committing is neither stashing, reverting nor deploying, and it is the only one
of the four that is reversible.

**A second session is still working in this checkout.** Its edits reached live at
17:08Z; the owner's `admin/save-user` and termination calls reached live at
12:52, 15:54, 15:56 and 17:11Z. Every measurement in this report carries the
minute it was taken for that reason.

---

## 7. The path the owner has now

Admin token required; all three routes are admin-only.

```bash
TOKEN='<admin bearer token>'

# 1. Look before touching: this refuses and tells you what is there.
curl -sS -X POST https://epe.sedamedical.com/webhook/api/admin/exclude-participant \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"period_id": 2, "user_id": 42, "note": "вышел на работу в сентябре"}'
```

If the person has no evaluation data yet — which is everybody on live today,
because all four data tables are empty — that call **succeeds** and the person
leaves H1. If they do have data, it refuses with `HAS_EVALUATIONS` and prints the
GAVE / ABOUT split; repeat with `"confirm_existing_evaluations": true` to
proceed.

```bash
# 2. Put somebody back — exact, and only for people excluded this way.
curl -sS -X POST https://epe.sedamedical.com/webhook/api/admin/include-participant \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"period_id": 2, "user_id": 42}'

# 3. Read the record, at any time, including after the period closes.
curl -sS https://epe.sedamedical.com/webhook/api/admin/period-scope-events \
  -H "Authorization: Bearer $TOKEN"
```

`period_id` is **2** for H1-2026. Passing 5 (Annual 2026) would take the person
out of the annual container as well, which is almost certainly not wanted: a
person who worked the second half of the year belongs in the annual roll-up.

What this does **not** cover:

- **It does not reassign anybody.** If an excluded person has direct reports,
  those people are left with an evaluator who has no task list. The response
  names them; moving them is a separate `admin/save-user` edit, and that route is
  a **full-row overwrite** — read the live row and send all nine writable columns,
  or a missing field silently demotes a manager to `employee` and moves a project
  person to `general`, which changes their bonus.
- **It does not touch closed periods**, in either direction, by design.
- **It does not recompute anything.** No stored score, rating or index is
  rewritten, now or ever, by any of this.
- **It does not affect H2.** When H2 is created, an excluded person enters it
  normally, because `API: Manage Periods` was deliberately not changed.
- **It does not remove them from the admin money matrix** (BUG-060).
- **It does not delete anything.** The participants row stays, which is what
  makes the size of the pool at calculation time reconstructible.

---

## 8. Session hygiene

- One dated dump of live, taken before the first write, copied to the Mac outside
  the repository, md5-verified on both copies.
- Two throwaway databases per stand run, all dropped; one verification throwaway,
  dropped. `SELECT datname` on `postgres_n8n` reads `epe_2026, postgres`.
- One stand container, created and removed (twice — the proof was rebuilt after
  three test-assumption bugs were fixed). **No container was restarted or stopped
  except the stand's own.** Other projects share this machine; `docker ps` shows
  the same six containers as before.
- No extension was created on live: `pg_extension` reads `plpgsql`.
- Nothing landed in `/tmp` on the host. `/root/epe_stand_tmp` holds four anchors,
  mode 600, and nothing else.
- Probe session minted and deleted in a `finally`; `auth_sessions` 14 → 14.
- No mail of any kind was sent. The registration proof used a verification-code
  row inserted directly into the **stand** database, so no address was ever
  contacted.
- No frontend build, no frontend deploy, no `deploy_epe_frontend.sh` run.

---

## 9. Files

| file | what |
|---|---|
| `migrations/016_add_period_scope_events.sql` | the append-only scope record |
| `scripts/build_route_guard_workflows.py` | `build_manage_period_scope` (new); nothing else changed |
| `scripts/deploy_midyear_scope.py` | the live deploy: guard-frozen gate, migration precondition, unpressed-gate precondition, empty-UPDATES assertion, create-inactive-then-activate |
| `scripts/setup_midyear_throwaway.sh` | the two-copy stand |
| `scripts/seed_midyear_throwaway.sql` | fixtures 1601–1611 |
| `scripts/prove_midyear_scope.py` | the 152 checks |
| `scripts/teardown_midyear_throwaway.sh` | the drop loop |
| `scripts/verify_midyear_live.py` | the live drift and read-surface pass |
| `n8n_workflows/API_ Manage Period Scope.json` | the export, refreshed from live after the write |
| `docs/MID_YEAR_HIRES_MARKING_SHEET_2026-08-25.md` | the owner's marking sheet, in Russian |

`backups/2026-08-25-midyear-scope/` holds `midyear_scope_proof.json` and
`live_verify.json`. It is deliberately **not** tracked — `backups/` is gitignored
because those files carry personal data.

---

**This report, the D-0825-10 row, the three bug rows, migration 016, the
executor scripts and the refreshed workflow export landed on `main` as commit
`489224c`.** The other session's already-live sidebar change was committed
immediately before it, on its own, as `a3326ab`. The proof files under
`backups/2026-08-25-midyear-scope/` are deliberately **not** tracked —
`backups/` is gitignored because those files carry personal data.
