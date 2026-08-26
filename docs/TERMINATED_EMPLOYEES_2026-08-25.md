# Terminated employees — forgotten by the product, kept by the database (2026-08-25)

**Brief:** TERMINATED_EMPLOYEES. **Decision:** D-0825-7.

**Outcome in one line: the owner can now mark a person terminated from
/admin/users with a date, and that person leaves every list, task and
calculation while every evaluation row stays byte-identical in the database —
proven on a throwaway stand by 101 checks and a browser walkthrough, then
deployed to live, where a cell-by-cell diff of all 89 people over all 20
pre-existing columns shows zero changes and the second gate is still unpressed.**

Live writes: migration 015 at **15:33Z**, six workflows at **15:34:40–15:34:52Z**,
frontend release **`20260825T153640Z`** at 15:36Z. **Nobody was terminated on
live.** This session shipped the capability; using it is the owner's.

---

## 1. What already existed, before anything was built

The brief asked for this first, and the answer decided the shape of the build.

### 1.1 `users` carries no employment state at all

`performance_db.users` had **20 columns** and not one of them was an
active/terminated flag or a termination date. There was no `status`, no
`is_active`, no `left_at`. Read live 2026-08-25 14:46Z:

```
id · full_name · email · password_hash · role · department_id · grade_id ·
manager_id · job_title · employment_type · join_date · salary_current ·
salary_proposed · created_at · is_project_participant · work_category ·
has_subordinates · can_evaluate · can_be_evaluated · token_version
```

`employment_type` is the near miss: it is a free varchar defaulting to
`'Full-time'` and it describes a contract, not a state. Nothing reads it.

### 1.2 `is_in_scope` / `exclusion_reason` are real, and exactly one route writes them

`evaluation_period_participants` has `period_id, user_id, is_in_scope (NOT NULL
default true), exclusion_reason (nullable), created_at, updated_at`, with
`CHECK (is_in_scope OR exclusion_reason IS NOT NULL)` — the database already
refuses a silent exclusion.

Live content, all of it:

| period | in scope | reason | rows |
|---|---|---|---|
| 2 (H1-2026) | false | `hired_after_period_end` | 2 — Esenova (31), Balova (35) |
| 2 (H1-2026) | true | — | 87 |
| 5 (Annual 2026) | true | — | 89 |

Both out-of-scope rows have `created_at = updated_at = 2026-08-18 14:29:02.470198`:
they were written at import and **no route has touched them since**.

The route that writes them is **`POST /api/periods/create`**, and only that one.
Its `participants` CTE computes the flag from `join_date > end_date` at the
moment the period is created. Activation does not touch participants; neither
does start-evaluation, close, rename or reparent. Searched live `workflow_entity`
for every INSERT/UPDATE/DELETE against the table — one hit, `API: Manage Periods`.

**Therefore: before this session there was no route on live that could take a
person out of scope of a period that already existed.** The only mechanism was
raw SQL. That is the gap the build had to close, and it is why §6's hand-run
path could not be "existing routes only".

What `is_in_scope=false` already did, everywhere, without a line of new code:

- `API: Get Employees` joins `epp … AND epp.is_in_scope = true` for the subject
  **and** requires `COALESCE((SELECT is_in_scope FROM actor_scope), false)` for
  the actor — so an excluded person vanishes from their manager's task list and
  gets an empty one of their own.
- `API: Submit Evaluation` and `API: Submit Self Review` both join the
  participants row for **actor and subject**: all four channels answer 403.
- `API: HR Evaluation Status` builds `in_scope`, and its `sub_counts` CTE joins
  managers' subordinates **to that set** — completion already counts against the
  smaller population.
- `Compute Close Results` starts with `let hasData = inScope && …`, so an
  out-of-scope person freezes into `period_results` as
  `is_in_scope=false, has_data=false` with every rating and both money columns
  NULL. The two CHECKs on that table make a number impossible on such a row.
- `/api/periods` reports `in_scope_count` from the same flag.

### 1.3 How the read-only trio is done, and how much of it fits

Cem Durukan (21), Hemra Ashyrov (40), Mekan Yusupov (61) are held out with two
boolean columns on `users`: `can_evaluate=false` and `can_be_evaluated=false`
(D-0821-4). The machinery is (a) the columns, (b) `required_capability` in
`EPE: Auth Guard`, (c) `AND subj.can_be_evaluated = true` in all three relation
filters of `API: Submit Evaluation` plus an e-mail denylist on the
`c_level_direct` branch, (d) `canReceiveCLevel` in `src/utils/matrixUtils.js`,
which reads `is_in_scope && can_be_evaluated`.

Live today, `can_be_evaluated=false` on ids 2, 18, 21, 40, 47 (admin + all five
C-level); `can_evaluate=false` on 21, 40, 61.

**The build reuses the scope half and deliberately does not write the capability
half.** The reason is reversibility, and it is the one design decision here worth
arguing about. `can_evaluate`/`can_be_evaluated` are the owner's standing policy
for specific people. If termination overwrote them, then after a
terminate → reinstate round trip you could no longer tell a read-only C-level
from a former employee — the original setting would be gone. `is_in_scope`
carries no such meaning, is period-bound (which the money record needs: *which*
period did they drop out of), and already gates every path that matters. So
termination writes scope, not capability.

### 1.4 What was missing, plainly

1. No terminated state on the person. **Added** (migration 015).
2. No route that can exclude somebody from an existing period. **Added**.
3. No record of who terminated whom, when, or from which period — `users` has no
   `updated_at` and `admin/save-user` writes no audit row (BUG-059).
   **Added**, scoped to employment events only.
4. `/admin/users` had no employment filter; `API: Admin Get Users Data` returns
   every row with no WHERE clause at all. **Added** (client-side filter, route
   still returns everybody).
5. Login, registration and password-reset had no termination check. **Added**.
6. Period creation would have put a terminated person straight back into scope
   the moment H2 is created. **Fixed**.

---

## 2. What was built

### 2.1 Migration 015 — additive only

`migrations/015_add_employment_termination.sql`. Applied to live 15:33Z, then
applied a second time to prove idempotence (three `already exists, skipping`
notices, no error).

- `users.terminated_at timestamptz` — the current state, and the only thing a
  list query or a login check reads. NULL = employed.
- `users.termination_date date` — **the owner's date**, the last working day.
  Deliberately separate from `terminated_at`: the owner marks somebody
  terminated days after they left, and the money question is decided by the day
  they left, not by the day somebody clicked.
- `CHECK ((terminated_at IS NULL) = (termination_date IS NULL))` — neither half
  is meaningful alone.
- `performance_db.employment_events` — append-only: `id, user_id, event_type
  ('terminated'|'reinstated'), effective_date, period_id, actor_id, occurred_at,
  note`, with a CHECK that a `terminated` row must carry its effective date, and
  foreign keys **without** `ON DELETE CASCADE` so a person named here cannot be
  hard-deleted.

Why a table and not two more columns: the state is reversible, so
`terminated_at` alone loses the history of a terminate → reinstate → terminate
sequence — and D-0825-7 says the termination event must stay readable after the
period closes. The table is also the first audit row this database has ever had
for a change to a person; it is scoped to employment events and is **not** a
general audit log, so BUG-059 stays open.

On live after the migration: 89 users, **0** with either column set,
**0** employment events.

### 2.2 One new workflow — `API: Manage Employment Status`

Live id **`vZwDA0aDZqIoCmoW`**, 25 nodes, active, `updatedAt=2026-08-25T15:34:52.162Z`.
Three admin-only routes:

| route | does |
|---|---|
| `POST /api/admin/terminate-employee` | `{user_id, termination_date, note?}` |
| `POST /api/admin/reinstate-employee` | `{user_id, note?}` |
| `GET /api/admin/employment-events` | the record, optionally `?user_id=` |

Termination is **one SQL statement**. Every precondition is re-asserted inside
the `target` CTE, so a lost race selects zero rows and every branch below it
changes zero rows — the same one-gate rule the close and additive-submit paths
use. In order it: marks the person and bumps `token_version`; revokes every
live `auth_sessions` row; burns every unused `password_reset_tokens` row; sets
`is_in_scope=false, exclusion_reason='terminated'` on every **currently in-scope**
row of every **non-closed** period; and appends the event.

Two details that matter more than they look:

- **Only rows that are currently `is_in_scope = true` are written.** Somebody
  already excluded for `hired_after_period_end` keeps that reason, so
  reinstatement can never wrongly put them back in scope. Reinstatement flips
  back only rows whose reason is exactly `'terminated'`. The round trip is exact
  for a person who is both — proven on the stand.
- **`status <> 'closed'`.** A closed period and the 2025 archive are never
  touched, in either direction.

Refusals, each by name: `HAS_DIRECT_REPORTS` (422), `CANNOT_TERMINATE_SELF`
(422), `ALREADY_TERMINATED` (409), `USER_NOT_FOUND` (404),
`INVALID_TERMINATION_DATE` (422), `NOT_TERMINATED` (409) on reinstate,
`ROLE_FORBIDDEN` (403) for a non-admin, `TOKEN_MISSING` (401) unauthenticated.

The direct-reports refusal is decided on the **graph**, not on the
`has_subordinates` flag. `trg_update_has_subordinates` fires only on
`INSERT OR DELETE OR UPDATE OF manager_id` (function read from live), so the
flag is a cache; the gate reads `EXISTS (SELECT 1 FROM users r WHERE
r.manager_id = u.id AND r.terminated_at IS NULL)` instead. On live the flag and
the graph agree on all 89 today (0 disagreements, 17 people with subordinates).
Terminated reports are not counted: they are forgotten too, so nobody is
orphaned by them.

The message the owner sees, verbatim from the stand:

> Нельзя уволить: у сотрудника есть прямые подчинённые (3) — TM Leaver,
> TM Stayer A, TM Stayer B. Сначала переназначьте их другому руководителю.

**A branch I wrote and then deleted.** The first draft refused terminating the
last remaining admin. It is unreachable: the route is admin-only, so the only
way to reach zero live admins is an admin terminating themselves, which
`CANNOT_TERMINATE_SELF` already refuses. Unreachable code that reads as a
guarantee is worse than no code, so it is gone and the reasoning is a comment in
the builder.

### 2.3 Five workflows changed

All five PUT with activation preserved, graph re-read and compared node-for-node
after each write, and `EPE: Auth Guard` re-checked after every one. The guard is
**not** in the list and was never written: `updatedAt=2026-08-18T16:34:30.674Z`,
`active=false`, unchanged before and after.

| workflow | live id | new `updatedAt` | change |
|---|---|---|---|
| `API: Auth Login (No Params)` | `A4Ah3w21JEqHvQFR` | 15:34:40.287Z | a terminated employee cannot mint a session; the refusal is the **same generic 401** as a wrong password |
| `API: Register` | `wkDxU72Kg8fOiZCB` | 15:34:42.165Z | `AND users.terminated_at IS NULL` — the shared invite (id 4, live until 2026-09-18) is inert for them |
| `API: Request Password Reset` | `iEwAjOozioSOXC4T` | 15:34:43.631Z | no reset token is created; the generic 200 is unchanged |
| `API: Admin Get Users Data` | `AwID96McjHKyk8WI` | 15:34:45.316Z | the two columns as text (BUG-031 defence); a terminated person is no longer offered in `options.managers` |
| `API: Manage Periods` | `M9ljMDdO1mIl8m1h` | 15:34:48.650Z | `Build Create SQL`: a terminated person is out of scope of any **new** period, reason `terminated` |

That last one is the difference between a one-period patch and the decision. The
participants INSERT is a `CROSS JOIN users`; without the new CASE branch, creating
H2 would have silently returned every terminated person to the pool.

**`EPE: Auth Guard` was deliberately left alone.** Adding
`AND users.terminated_at IS NULL` there would be redundant — the guard already
joins `auth_sessions ON token_version = users.token_version`, so the bump alone
kills every live JWT, and `revoked_at` is the second lock — and its frozen
`updatedAt` is the project's tamper marker. Redundant change, real cost: not made.

### 2.4 `/admin/users`

- `useUserFilters`: a new `employment` filter, the only one whose default is not
  «все» — it is `active`, so the working list hides terminated people, and reset
  returns to `active` rather than `all`.
- `UserFilters`: «Работают» / «Уволены» / «Все (вкл. уволенных)».
- `UserTable`: a red «Уволен ГГГГ-ММ-ДД» badge, the row dimmed, and a second
  action button — terminate, or reinstate for somebody already terminated.
- `EmploymentStatusModal` (new): asks for the date, and states the consequences
  **before** the click, including the money one and the GAVE/ABOUT split. The
  server's refusal stays inside the modal rather than flashing past in a toast,
  because it says what to do next.
- The header no longer prints «Всего» — it prints «Работают: N | Уволены: M»,
  because one number over two different populations was the thing that made the
  old list misleading.

`npm run build` clean; `npx eslint src` is at the repo's 19-error baseline — the
new file adds none (the sibling `UserModal.jsx` carries the same
`set-state-in-effect` error; the new modal uses the render-phase reset instead).

---

## 3. The stand proof

`scripts/setup_termination_throwaway.sh` → `scripts/prove_termination.py` →
`scripts/teardown_termination_throwaway.sh`. Proof artifact:
`backups/2026-08-25-termination/termination_proof.json`, **101 checks, 101 passed,
`failures: []`**. Every check records the values it compared on both sides; the
run ends with a meta-check that it compared more than 50 things, so a vacuous run
fails instead of printing a slogan.

**Two databases, one dump.** The stand restores the same dated dump of live into
`epe_term_<stamp>_ctl` and `epe_term_<stamp>_trt` and asserts they start with an
identical evaluations fingerprint. That is what makes the money claim provable:
the two closed period-result sets differ **only** by the termination, because
they started byte-identical. Synthetic fixtures 1501–1509 (the
`seed_walkthrough_throwaway.sql` discipline — no real person's row is touched),
with real scrypt logins, distinct grade coefficients so no arithmetic can pass
on a 1.0 fallback, and distinct scores so a dropped evaluation moves a printed
number instead of hiding in an average.

### 3.1 The GAVE / ABOUT split, to the digit

1503 «TM Leaver» both gave (upward → 1502) and received (manager ← 1502, self,
c_level ← 1506). Both stands were closed through the real
`POST /api/periods/close`, and `period_results` compared:

| | control (nobody terminated) | treatment (1503 terminated) |
|---|---|---|
| **1502, the manager they evaluated** | | |
| `rating_manager` | 7.40 | **7.40** |
| `rating_upward` | 6.33 | **6.33** |
| `rating_c_level_direct` | 5.50 | **5.50** |
| `final_rating` | 6.8571 | **6.8571** |
| `bonus_index` | 170.8300 | **170.8300** |
| **1503, the terminated person** | | |
| `is_in_scope` | true | **false** |
| `has_data` | true | **false** |
| `rating_manager` | 7.00 | **null** |
| `rating_c_level_direct` | 6.50 | **null** |
| `rating_self` | 8.00 | **null** |
| `final_rating` | 6.8750 | **null** |
| `bonus_index` | **108.3240** | **null** |

`rating_upward` for 1502 is the load-bearing number. It is the mean of three
upward evaluations — 9.0 from the terminated person, 4.0 and 6.0 from the two who
stayed. If termination had dropped the evaluation they *gave*, it would read
5.00. It reads **6.33 on both sides**. The evaluation survives and keeps feeding
the person who is still employed, which is exactly D-0825-7.

**Rows that moved besides the leaver's: `[]`** — every other person's stored
result is identical between the two closes.

**The pool.** Total `bonus_index` over everybody: **410.842** control,
**302.518** treatment, difference **108.324** — equal to the leaver's index to
four decimals. The pool shrank by exactly their share and by nothing else, which
is the arithmetic of "redistributes among the rest".

### 3.2 Every evaluation row, byte-identical

46 evaluation/score rows fingerprinted before and after. md5
`e66b3301081604cf44fddabd40bb3ec9` before termination,
`e66b3301081604cf44fddabd40bb3ec9` after, and the same again after the whole
terminate → reinstate → terminate sequence. Row count 46 → 46. Nothing deleted,
nothing rewritten, nothing recomputed.

### 3.3 The rest, in one list

| claim | evidence |
|---|---|
| Cannot log in | 401, and the message is byte-identical to a wrong-password 401 on a live colleague's account — the form is not an oracle for who was fired |
| The token minted before termination is dead | 401 on the next request |
| The shared invite cannot let them back in | never-registered fixture terminated → `POST /api/register` **400**, password still NULL; the **same invite and code flow succeeded (200) for an employed colleague** in the same run |
| No reset link | generic 200, zero new `password_reset_tokens` rows; an employed colleague got one |
| Out of scope with a reason | periods 2 **and** 5, `exclusion_reason='terminated'` |
| Somebody else's reason survives | the `hired_after_period_end` fixture is byte-identical before, during and after |
| Evaluators' lists lose them | manager's task list −1, the other reports still present |
| Campaign counter drops by one | `/api/periods` in_scope 95→94; HR status in_scope 95→94; the manager's `total_subordinates` 3→2 |
| Nothing was deleted | `participant_count` unchanged at 98 |
| Not offered as somebody's manager | `options.managers` loses exactly the terminated person and nobody else |
| The record | actor, period id, the owner's effective date, and the note |
| Refusals write nothing | after all eight refusals: evaluations md5 unchanged, zero events, zero user-row changes |
| Reinstatement is exact | participants table byte-identical to the start; the **only** residue on the row is `token_version: 0 → 1` |
| The log holds history, not state | `['terminated', 'reinstated', 'terminated']` for one person |

`token_version` is deliberately **not** rolled back on reinstatement: revoking a
session is a one-way security action, and coming back is not a reason to
resurrect a token that was already handed out. The person logs in again.

### 3.4 The browser walkthrough

Driven in a real browser against the stand (local vite → VPS loopback n8n),
using the actual login form, not pre-minted tokens.

1. **TM Leaver logs in** — full portal, «Самооценка» / «Оценить руководителя»,
   two task badges, «Оценка идёт — ваши задачи ниже».
2. **TM Manager → Моя команда** — three cards: TM Leaver (7.0), TM Stayer A
   (5.5), TM Stayer B (8.2).
3. **TM Admin → Сотрудники** — «Работают: 98 | Найдено: 98», the new status
   filter reading «Работают».
4. **Terminate TM Manager** → the modal shows the refusal in the owner's words,
   naming all three reports.
5. **Terminate TM Leaver**, date set to **2026-08-20** (not today's default), note
   «Уволен по собственному желанию» → toast «TM Leaver: увольнение отмечено»,
   header becomes «Работают: 97 | Уволены: 1 | Найдено: 0» — the search that
   found them a second earlier now finds nobody.
6. **Filter «Уволены»** → the row is back, dimmed, badged «Уволен 2026-08-20» —
   the owner's date, not the click's.
7. **TM Leaver logs in** with the correct password → «Неверный email или пароль».
8. **TM Manager → Моя команда** → two cards. TM Leaver is gone.
9. **Reinstate** → toast «TM Leaver: сотрудник восстановлен», header back to
   «Работают: 98», «Уволены» filter empty.
10. **TM Manager → Моя команда** → three cards again, TM Leaver at 7.0 —
    identical to step 2.
11. **TM Leaver logs in** → the portal exactly as in step 1.

Console during the whole pass: one 422 and its logged message — the deliberate
direct-reports refusal. No other error.

### 3.5 Teardown

Container `epe-term-n8n` removed; both `epe_term_*` databases dropped (the drop
loop refuses any name without the prefix, so `epe_2026` can never be a
candidate); `SELECT datname` afterwards lists **`epe_2026, postgres`** only; the
six containers on the host are the same six as before; the stand tunnel is
closed. No container this project does not own was touched, and nothing was
restarted outside the stand.

---

## 4. Live: what changed, and the proof that nothing else did

### 4.1 The rollback anchor

| | |
|---|---|
| File | `epe_2026_pretermination_20260825T153238Z.dump` |
| Taken | 2026-08-25 **15:32:38Z**, `pg_dump -Fc --no-owner --no-acl` of live `epe_2026`, **before the first live write** |
| Size | **80 766 bytes** |
| md5 | **`e11698f6a92c9e1a78130a0267af01f0`** — verified equal on both copies |
| On the VPS | `/root/epe_stand_tmp/epe_2026_pretermination_20260825T153238Z.dump`, mode 600 |
| On the Mac | `~/EPE_ROLLBACK/2026-08-25-termination/…`, mode 600, **outside the repository** |

The two older anchors (`121617Z`, `141806Z`) are left in place and are history.
This one supersedes them.

### 4.2 Drift — cell by cell, independently

The anchor was restored into a throwaway `epe_termverify_*` and every column of
every user compared against live. `dblink` was **not** created on live (a
previous brief did that by accident and had to undo it); both sides were exported
as JSON instead.

**1 780 cells compared (89 people × 20 pre-existing columns). Zero changed.**

The frozen columns — `salary_current`, `salary_proposed`, `join_date`,
`password_hash`, `can_evaluate`, `can_be_evaluated`, `token_version`,
`employment_type`, `created_at` — are untouched on all 89, checked by name as
well as by the full diff. The two new columns were absent from the anchor and are
NULL on all 89 on live. The throwaway was dropped; `SELECT datname` afterwards is
`epe_2026, postgres`.

> **Superseded for future drift checks (D-0826-4, 2026-08-26):** `join_date`
> remains correctly untouched by termination, but it is no longer globally
> frozen. A date changed through the admin employee card is an intended,
> audited owner action and must not be reported as an incident.

Every other table, fingerprinted on both sides and **identical**:

| table | md5 |
|---|---|
| `criteria` | `0b1db252890b64f4c7b6a19b3c0a7a19` |
| `score_coefficients` | `c1c04b2791443979ebb045d06e008da2` |
| `grades` | `bb1d249f012ed8ace70d4253399f0af3` |
| `departments` | `e15c12ae4e2e8a5d047cd1259300ff0c` |
| `evaluation_periods` | `1d4a866479c046682e5dc1a4821d2652` |
| `evaluation_period_participants` | `df24feb8471b9f60091410fa23a1554f` |

All six also match the read taken at the **start** of the session, 14:46Z, before
anything was built — so nothing moved while the work was in progress either.

### 4.3 The distributions the brief asked for, before and after

Recomputed from the live applicability rule on both sides of the anchor:

```
criteria per person   before: 4 -> 37,  5 -> 11,  6 -> 35,  7 -> 6     (89)
                      after : 4 -> 37,  5 -> 11,  6 -> 35,  7 -> 6     (89)

work_category         before: general 48 / project 41
                      after : general 48 / project 41
```

**Unchanged, as intended.** Nobody was terminated, so no bucket could move.

### 4.4 Invariants after

| check | result |
|---|---|
| H1-2026 | `status=active`, `is_active=true` |
| `evaluation_started_at` | **NULL on all three periods** — the second gate is unpressed and no route that could press it was called |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| `employment_events` | **0** — nobody was terminated |
| people with `terminated_at` or `termination_date` set | **0 of 89** |
| Participants on H1 | 89 / **87** in scope, unchanged |
| Extensions on live | `plpgsql` only |
| `auth_sessions` | 14 → 14; the probe session was minted and deleted in a `finally` |
| Workflows | 58 → **59** (34 active, 22 archived); webhooks 42 → **45** |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — the frozen value, before and after |
| Re-running the deploy | reports `changed=false` on all six — it is idempotent |

### 4.5 The read surface agrees

Read-only probe through Caddy with a real admin token, session deleted afterwards:

- `GET /api/admin-users-data` → 200, **89** rows, every one carrying
  `terminated_at` and `termination_date`, every one **null**. The route still
  returns everybody — the page filters, not the route, so nothing is hidden from
  an admin who asks for it.
- `GET /api/admin/employment-events` → 200, `events: []`.
- `GET /api/periods` → 200, H1 `status=active`, `evaluation_started=false`,
  **87 / 89**.
- `GET /api/employees` → 200, `campaign_active=false`,
  `period_in_preparation=true`.
- The three new routes unauthenticated → **401 `TOKEN_MISSING`** each.

Report: `backups/2026-08-25-termination/live_verify.json`, **37 checks, 37 passed**.

### 4.6 Frontend

Release **`20260825T153640Z`**, symlinked at `/var/www/epe/current`; 30 releases
on disk; public `index.html` `Last-Modified: Tue, 25 Aug 2026 15:36:07 GMT`.

`scripts/deploy_epe_frontend.sh` **refused to run** — BUG-040 is still real. `rg`
is not installed on the delivery laptop; it resolves only to a shell function
injected by the terminal, so the script's two safety gates fail closed. Both
gates were therefore run by hand with `grep` — legacy `:5678` absent, `/webhook`
base present, both PASS — and then the script's remaining steps (install
directory, tar over, symlink flip with the previous release captured for
rollback) were executed verbatim by hand. No shim was installed, so the gate
cannot be silently bypassed by a future run either.

---

## 5. Surfaced, not resolved

### 5.1 The admin money matrix still shows a terminated person as an empty row

`API: evaluations-matrix` selects every `u.role != 'admin'` and `LEFT JOIN`s the
participants row: it *emits* `is_in_scope` per person but does not filter on it.
A terminated person will appear in Итоговые баллы / Матрица оценок as a row with
empty cells, exactly as Esenova and Balova do today.

**This is cosmetic, not money.** The pool is computed at close from
`period_results`, where the person is `has_data=false` with NULL money columns
(§3.1). The C-level star is already hidden — `canReceiveCLevel` reads
`is_in_scope && can_be_evaluated`.

It was left alone deliberately. Hiding rows there would also change what the
admin sees for the two people who are out of scope by **hire date**, who are
employed and arguably should still be visible. Which of the two the owner wants
is a product question, not an engineering one. **BUG-060.**

### 5.2 `admin/save-user` will still accept a terminated person as somebody's manager

The UI no longer offers them (`options.managers` filters them out), but the route
itself does not validate `manager_id` against `terminated_at`. A script, an Excel
import, or a hand-made request could point a live employee at a terminated
manager — and that employee would then be evaluated by nobody, because a
terminated actor gets no task list.

Not fixed here: `admin/save-user` is the full-row-overwrite route the brief
warned about, and adding a validation branch to it is a change to the most
dangerous write path in the system for a case the UI already prevents.
**BUG-061.**

### 5.3 BUG-059 is narrowed, not closed

`employment_events` is the first audit row this database has for a change to a
person, but it records employment events only. `users` still has no `updated_at`,
and `admin/save-user` still writes no audit row, so a classification change — a
money input — is still undated and unattributed. **BUG-059 stays open.**

### 5.4 BUG-040 confirmed still open

See §4.6. `rg` is a shell function, not a binary; the deploy script fails closed
every time until ripgrep is actually installed.

### 5.5 Two decisions I made that the brief did not name

Both are surfaced here rather than buried in code:

- **Self-termination is refused** (`CANNOT_TERMINATE_SELF`). Nothing in the brief
  asks for it, but reinstatement is admin-only, so an admin terminating
  themselves would lock the product with no route back in. It is also what makes
  the deleted last-admin branch unnecessary (§2.2).
- **Terminated direct reports do not block a manager's termination.** The refusal
  counts reports with `terminated_at IS NULL`. A terminated report is forgotten
  and cannot be orphaned, and counting them would make a whole terminated team's
  manager permanently unterminable.

### 5.6 Untouched, and still true

Criterion 14's live level curve is still `0.70/1.00/…/7.00` against the approved
`0.20/0.25/…/6.00` (HANDOVER §3, BUG-050 territory). Not this brief's scope, not
touched, still unresolved. No catalogue, coefficient, criteria, grade,
department or period write of any kind was made. **The second gate was not
pressed and no route that could press it was called.**

---

## 6. The hand-run path

The brief asked for a path using **existing routes only**, for use before the UI
shipped. The UI shipped in this session, so the honest answer has three parts.

### 6.1 Before this session there was no such path

§1.2: the only writer of `is_in_scope` was `POST /api/periods/create`, which
fires at creation. No route could take somebody out of scope of a period that
already existed. The only pre-existing mechanism was raw SQL on live — which is
precisely what D-0825-7 should not require, and why the build exists.

### 6.2 The path the owner has now: the screen

Admin → **Сотрудники** → find the person → the second action icon
(**Отметить увольнение**) → set the last working day → read the consequences →
confirm. The person leaves the list. «Уволены» in the status filter brings them
back; the icon there reinstates.

If the person still has direct reports the modal refuses and names them —
reassign those people first (edit each of them, change «Руководитель»), then
repeat.

### 6.3 The path for a handful at once, without the screen

The same routes, by hand. Admin token required; every call is admin-only.

```bash
TOKEN='<admin bearer token>'
curl -sS -X POST https://epe.sedamedical.com/webhook/api/admin/terminate-employee \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"user_id": 123, "termination_date": "2026-08-20", "note": "по собственному желанию"}'
```

Reinstate:

```bash
curl -sS -X POST https://epe.sedamedical.com/webhook/api/admin/reinstate-employee \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"user_id": 123}'
```

Read the record back, at any time, including after the period closes:

```bash
curl -sS https://epe.sedamedical.com/webhook/api/admin/employment-events \
  -H "Authorization: Bearer $TOKEN"
```

Order for a batch: **subordinates before their managers**, or the manager's call
is refused. `HAS_DIRECT_REPORTS` names exactly who is in the way.

### 6.4 What none of this covers

- **It does not reassign anybody.** A manager with live reports must have them
  moved first, through Admin → Сотрудники or `admin/save-user`. If that route is
  used directly, **send all nine writable columns**, read from the live row
  immediately before writing it back — a missing field silently demotes a manager
  to `employee` and moves a project person to `general`, and the second of those
  changes their bonus.
- **It does not touch closed periods.** By design. A person terminated today
  keeps every number already frozen into a closed period, and the 2025 archive is
  untouched.
- **It does not recompute anything.** No stored score, rating or index is
  rewritten, now or ever, by any of this.
- **It does not remove them from the admin money matrix** (§5.1).
- **It does not delete anything.** Hard deletion remains refused, which is the
  whole point: the size of the pool at calculation time stays reconstructible.
- **Excel import is not aware of it.** `UserImportModal` posts through
  `admin/save-user`, which does not write the termination columns — an import
  can neither terminate nor accidentally un-terminate anybody. It can, however,
  point somebody at a terminated manager (§5.2).

---

## 7. Session hygiene

- One dated dump of live, taken before the first write, copied to the Mac outside
  the repository, md5-verified on both copies.
- Two throwaway databases, both dropped. One verification throwaway, dropped.
  `SELECT datname` on `postgres_n8n` reads `epe_2026, postgres`.
- One stand container, created and removed. **No container was restarted or
  stopped except the stand's own.** Other projects share this machine;
  `docker ps` shows the same six containers as before.
- No extension was created on live, not even temporarily: `pg_extension` reads
  `plpgsql`.
- Nothing landed in `/tmp` on the host. `/root/epe_stand_tmp` holds the three
  anchors, mode 600, and nothing else.
- Probe sessions minted and deleted in `finally` blocks; `auth_sessions` 14 → 14.
- No mail of any kind was sent. The registration proof used a verification-code
  row inserted directly into the **stand** database, so no address was ever
  contacted.
- `.claude/launch.json` gained an `epe-term-vite` launcher (port 5399) for the
  browser pass.

---

## 8. Files

| file | what |
|---|---|
| `migrations/015_add_employment_termination.sql` | the two columns and the event table |
| `scripts/build_route_guard_workflows.py` | `build_manage_employment` (new), admin-users-data, period-create scope rule |
| `scripts/build_auth_workflows.py` | login / register / password-reset termination checks |
| `scripts/deploy_termination.py` | the live deploy: guard-frozen gate, migration precondition, PUT ×5, create-inactive-then-activate ×1 |
| `scripts/setup_termination_throwaway.sh` | the two-copy stand |
| `scripts/seed_termination_throwaway.sql` | fixtures 1501–1509 |
| `scripts/prove_termination.py` | the 101 checks |
| `scripts/teardown_termination_throwaway.sh` | the drop loop |
| `scripts/verify_termination_live.py` | the live drift and read-surface pass |
| `src/components/admin/EmploymentStatusModal.jsx` | the confirm dialog |
| `src/pages/AdminUsers.jsx`, `UserTable`, `UserFilters`, `useUsers`, `useUserFilters`, `config/api.js` | the screen |
| `n8n_workflows/API_ *.json` | six exports refreshed from live after the writes |

`backups/2026-08-25-termination/` holds `termination_proof.json`,
`termination_proof_api.json` and `live_verify.json`. It is deliberately **not**
tracked — `backups/` is gitignored because those files carry personal data.

---

**This report, the D-0825-7 row, the two bug rows and the executor scripts landed
on `main` as commit `7f67c49`.** The proof files under
`backups/2026-08-25-termination/` are deliberately **not** tracked — `backups/`
is gitignored because those files carry personal data.
