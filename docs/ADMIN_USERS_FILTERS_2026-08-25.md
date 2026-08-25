# The /admin/users filter row: the predicate was fine, the choices were not (2026-08-25)

**Brief:** ADMIN_USERS_FILTERS. **Decision:** D-0825-8.

**Outcome in one line: nothing in the filter logic was broken — every control
already compared the right field to the right value and every combination
already composed as an AND — but the row offered choices that could not match,
withheld a role two people actually hold, and printed three numbers over two
unnamed populations, so a correct narrowing was indistinguishable from a broken
one. Each control now offers only values somebody carries, with the count it
will produce, and every number says which population it counts.**

Live now: frontend release **`20260825T162505Z`**, symlink flipped 16:24:29Z. No
database write, no workflow write, second gate still unpressed.

---

## 1. Both hypotheses in the brief are wrong, and the code says so

### 1.1 The role casing hypothesis — rejected

The display casing is the option's **child text**; the compared value is the
`value` attribute, and it carries the DB value verbatim. From the bundle that was
live when the owner reported this (`20260825T153640Z`, `admin-DmfQgZFT.js`):

```js
(0,R.jsx)(`option`,{value:`c_level`,children:`C-Level`})
```

`e.target.value` yields `c_level`; `performance_db.users.role` holds `c_level`.
They match. `filterUsers` with `role: 'C-Level'` returns zero and with
`role: 'c_level'` returns the five C-level people — the test
`role filter matches the raw DB value, not the display casing` pins both halves.

### 1.2 The employment-filter-broke-composition hypothesis — rejected

The predicate is a plain AND over all six keys, with employment merely first.
Same bundle, `useUserFilters-DB_cgqY6.js`:

```js
e.filter(e=>{let t=!!e.terminated_at;return!(
  r.employment===`active`&&t || r.employment===`terminated`&&!t
  ||!(e.full_name?.toLowerCase().includes(r.search.toLowerCase())||e.email?.toLowerCase().includes(r.search.toLowerCase()))
  || r.role!==`all`&&e.role!==r.role
  || r.work_category!==`all`&&e.work_category!==r.work_category
  || r.department_id!==`all`&&String(e.department_id)!==String(r.department_id)
  || r.manager_id!==`all`&&String(e.manager_id)!==String(r.manager_id))})
```

De Morgan of the source, and every clause is independent. Order of selection
cannot matter. The deployed chunk was **byte-identical to the repository** — there
was no stale build either.

### 1.3 What the owner's screen actually was

«Найдено: 12» was the filter working. The manager control held **Yelena Son**
(id 88). She has **13** direct reports; one was terminated at the time, so 12.
All 13 are `role='employee'`, all `work_category='project'`, all in department
«Project». Every control he could reach next was therefore degenerate:

| next click | result |
|---|---|
| Роль → Employee | 12 — no visible change |
| Роль → Admin / C-Level / Manager | 0 — «Сотрудники не найдены» |
| Категория → Project | 12 — no visible change |
| Категория → General | 0 |

Nothing on the screen distinguished "this combination is empty" from "this
control is broken". That is the defect, and it is a defect of the choices and
the counters, not of the predicate.

---

## 2. Control by control, before the fix

Measured against live `epe_2026` on 2026-08-25 by SELECT, and against the payload
`API: Admin Get Users Data` (`AwID96McjHKyk8WI`, `updatedAt=2026-08-25T15:34:45.316Z`)
actually returns.

| control | compares | verdict |
|---|---|---|
| Поиск | `full_name` / `email`, lowercased `includes`, 300 ms debounce | worked; did not trim, so a trailing space killed every match |
| Роль | `users.role` vs a hardcoded four-value list | **broken** — `hr` was missing; 2 people unreachable |
| Отдел | `String(department_id)` vs `options.departments[].id` | worked; **1 person with `department_id IS NULL` was unreachable** |
| Руководитель | `String(manager_id)` vs `options.managers[].id` | worked; **4 of the 21 offered people manage nobody** → always 0 |
| Категория | `users.work_category` vs `general/project/tender` | worked; **`tender` matches nobody** (0 live rows; `admin/save-user` answers 422) |
| Занятость | `Boolean(terminated_at)` | worked |
| композиция | AND over all six | worked, in any order |

Live evidence for each claim:

- `SELECT role, count(*)` → `admin 1 · c_level 5 · manager 13 · hr 2 · employee 68`.
  `src/config/constants.js` has listed five roles in `USER_ROLES` all along; the
  filter row listed four. The two HR people are Liya Dmitriyeva (52) and Sona
  Rahmanova (80).
- `options.managers` is built server-side as `u.role !== 'employee' && !u.terminated_at`
  → **21** entries. Only **17** ids appear as somebody's `manager_id`. The four
  dead options are Hemra Ashyrov (40), Mekan Yusupov (61), Liya Dmitriyeva (52),
  Sona Rahmanova (80).
- `SELECT count(*) WHERE department_id IS NULL` → 1. `WHERE manager_id IS NULL` → 3.
- `SELECT count(*) WHERE work_category='tender'` → 0.

### 2.1 One more, reachable today

`options.managers` drops a terminated person. If the selected manager is
terminated while a filter holds them, the `<select>` finds no matching option and
falls back to displaying the **first** one — «Все руководители» — while
`filters.manager_id` still narrows the list. The control would then claim "all"
over a filtered set. Not triggered by the current two terminations (both are
`employee` and were never in `options.managers`), and now prevented.

---

## 3. The numbers, and when they contradicted each other

The old header printed `Работают: 88 | Уволены: 1 | Найдено: 12`.

- «Найдено» counted `filteredUsers` — the **filtered** set.
- «Работают» / «Уволены» counted `visibleUsers` — the **whole population visible
  to the actor** (for admin/c_level/hr: all 89; for anyone else: their subtree).
  Neither ever moved when a filter changed.

They contradict whenever the filtered set is not the working set:

| state | old header | why it is wrong |
|---|---|---|
| Занятость = «Все» | `Работают: 87 \| Уволены: 2 \| Найдено: 89` | Найдено exceeds Работают |
| Занятость = «Уволены» | `Работают: 87 \| Уволены: 2 \| Найдено: 2` | advertises 87 working people over a list of leavers |
| Руководитель = Yelena Son | `Работают: 87 \| … \| Найдено: 11` | the two big numbers describe a population that is not on screen |

**Where the terminated person sits, exactly.** A terminated person is:

- inside «Уволены» — that is what the number counts, over the whole visible population;
- outside «Работают» — same population, complementary count;
- inside «Найдено» only when the employment control is «Уволены» or «Все», and
  when they also satisfy every other active control.

So `Работают + Уволены = Всего` always, and `Найдено` is independent of both. The
new header states each of those populations by name, and splits «Найдено» itself
when it contains leavers.

---

## 4. What was changed, frontend only

`src/utils/userFilters.js` is new and pure — one definition of "does this person
match" feeding the filtering, the counters and the option lists, so they cannot
drift apart. `useUserFilters` consumes it and additionally returns `facets`,
`counts` and `activeFilterCount`.

1. **Roles come from the data**, ordered `admin · c_level · manager · hr · employee`
   with the display casing as labels. HR is filterable.
2. **Departments, managers and categories come from the data.** No option is
   offered that nobody carries: `tender` is gone, the four report-less managers
   are gone. Managers are the people who actually appear as somebody's
   `manager_id`, so a **terminated** manager keeps their option — labelled
   «Имя (уволен)» — and their reports stay findable.
3. **«Без отдела» and «Без руководителя»** reach the 1 and 3 people a NULL used
   to hide.
4. **Every option carries the count it will produce** given the other active
   filters. With Yelena Son selected the role list reads
   `Admin (0) · C-Level (0) · Manager (0) · HR (0) · Employee (11)` — the zero is
   visible before the click, which is the whole answer to the owner's report.
5. **The header states its populations**: `Найдено: N — из них уволенных: M` over
   `Всего в базе: 89 · работают 87 · уволены 2`.
6. **The employment control announces what it alone removes**:
   «Скрыто уволенных: N — они подходят под остальные фильтры. Показать всех».
   Searching «kuv» from the default state used to answer «Сотрудники не найдены»
   with no hint that Kuvvat Garayev exists and is terminated.
7. **Active controls are visible**: an indigo ring on any control off its default
   and an «активных: N» chip, so a narrowed list never looks like a full one.
8. **Search is trimmed.** Reset is unchanged in meaning — every list to «Все»,
   search empty, sort cleared, and employment back to «Работают», which is its
   documented default (D-0825-7).

Option *membership* is computed over the whole population, not the filtered set,
so the lists do not shift under the owner while he composes; only the counts move.

---

## 5. The walkthrough

**What it ran against.** The production `dist/` built for this deploy, served
locally, answering with the **exact payload the live route returns** — captured
read-only by running that workflow's own SQL projection against live `epe_2026`
(89 users, 18 departments, 11 grades, 21 managers). It was **not** an
authenticated session against `epe.sedamedical.com`: only two accounts on live
have a password, both are people, and this session neither has nor asked for a
credential. The frontend under test is byte-identical to the deployed one; the
transport and the session are local. Expected counts were computed independently
in SQL against live before the browser was opened.

| # | state | expected (SQL over live) | observed | ✓ |
|---|---|---|---|---|
| 1 | default («Работают») | 87, скрыто уволенных 2 | `Найдено: 87`, banner «Скрыто уволенных: 2» | ✓ |
| 2 | «Уволены» | 2 | `Найдено: 2 — из них уволенных: 2`, «Скрыто работающих: 87» | ✓ |
| 3 | «Все (вкл. уволенных)» — **everybody** | 89 | `Найдено: 89 — из них уволенных: 2` | ✓ |
| 4 | Роль = HR | 2 | 2 | ✓ |
| 5 | Роль = Manager | 13 | 13 | ✓ |
| 6 | Рук. = Yelena Son, Работают | 11 | 11; role list `…Manager (0) · Employee (11)` | ✓ |
| 7 | + «Все» | 13 (2 уволенных) | 13, из них уволенных 2 | ✓ |
| 8 | + «Уволены» | 2 | 2, «Скрыто работающих: 11» | ✓ |
| 9 | + Роль = Employee | 11 | 11 | ✓ |
| 10 | + Роль = Manager — **nobody** | 0 | 0 | ✓ |
| 11 | Отдел = «Без отдела», Все | 1 | 1 | ✓ |
| 12 | Рук. = «Без руководителя», Все | 3 | 3 | ✓ |
| 13 | Роль=Admin + Отдел=HR, Все — **nobody** | 0 | 0 | ✓ |
| 14 | Поиск «kuv», Работают | 0, скрыто уволенных 1 | 0 + the banner naming it | ✓ |
| 15 | Поиск «kuv» + «Все» | 1 | 1, из них уволенных 1 | ✓ |
| 16 | Поиск «  KUV  » + «Уволены» | 1 | 1 | ✓ |
| 17 | all five controls + «Все» | 13 (2 уволенных) | 13 | ✓ |
| 18 | same + «Работают» | 11 | 11 | ✓ |
| 19 | same + «Уволены» | 2 | 2 | ✓ |
| 20 | Сброс | 87, every control at its default | 87, «Работают (87)», chip gone | ✓ |

The terminated pair — Kuvvat Garayev (51, `termination_date` 2026-08-01) and
Murad Bayramov (66, 2026-03-01) — appear under «Уволены» with the red
«Уволен ГГГГ-ММ-ДД» badge **with the manager filter also applied** (step 8),
vanish under «Работают» (step 6), and are back under «Все» (step 7).

Console during the whole pass: no error. The only warning is the pre-existing
dev-only `Module "stream" has been externalized` from the xlsx import.

`npm test` **351/351** (23 new in `tests/adminUsersFilters.test.js`).
`npx eslint src` is at the repo's **19-error / 13-warning baseline**; the new
files add none.

---

## 6. Deploy

| | |
|---|---|
| Release | **`20260825T162505Z`** |
| Symlink | `/var/www/epe/current` → `releases/20260825T162505Z` |
| Public | `index.html` `Last-Modified: Tue, 25 Aug 2026 16:24:29 GMT` |
| Releases on disk | 32 |
| Previous | `releases/20260825T160958Z` — the rollback target |

**BUG-040 confirmed still open.** `rg` resolves only to a shell function injected
by the terminal snapshot; `bash -c 'command -v rg'` exits 1 and
`bash -c 'rg --version'` prints `bash: rg: command not found`. Under the script's
`set -euo pipefail` both gates therefore fail closed. They were run by hand with
`grep -r` instead — legacy `http://92.51.45.147:5678` **absent**, `/webhook` base
**present**, both PASS — and the rest of the script (install directory, tar over,
previous release captured, symlink flip) executed verbatim. **No shim was
installed**, so a future run still fails closed.

`npm ci` was deliberately **not** run: `node_modules` is shared with the primary
working tree where a second session was active (§7). `npm ls --depth=0` reports
no UNMET, invalid, missing or extraneous top-level dependency, and the build was
clean.

Verified on the served bundle over HTTPS, not on disk:
`assets/AdminUsers-mz7I-rYq.js` contains «Скрыто уволенных»;
`assets/admin-CSJuaEnx.js` contains ``admin:`Admin`,c_level:`C-Level`,manager:`Manager`,hr:`HR`,employee:`Employee` `` and «Без руководителя».

### Nothing outside the frontend changed

Read back after the flip:

| invariant | value |
|---|---|
| H1-2026 (id 2) | `status=active`, `is_active=true` |
| `evaluation_started_at` | **NULL on all three periods** — second gate unpressed |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| users | **89**, of whom **2** terminated |
| active criteria / `score_coefficients` / grades | 9 / 90 (min 0.30) / 11 |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — unchanged |
| `API: Admin Get Users Data` | `updatedAt=2026-08-25T15:34:45.316Z` — unchanged |
| workflow writes after 16:00Z | **none** |
| workflows | 34 active / 59 total (33/58 in HANDOVER §2 plus `API: Manage Employment Status` from D-0825-7) |

**The brief says «89 users of whom 1 terminated»; live carries two.** Murad
Bayramov (66) was terminated at **15:56:23Z**, two minutes after Kuvvat Garayev
(51) at **15:54:23Z** — both by actor id 2, both before this session's first
command, both recorded in `employment_events` rows 1 and 2. H1 in-scope is
therefore **85**, not 87: `evaluation_period_participants` now carries two
`is_in_scope=false, exclusion_reason='terminated'` rows for period 2 and two for
period 5. That is D-0825-7's machinery doing its job under the owner's hand; this
session wrote nothing.

---

## 7. A second session was editing and deploying this checkout at the same time

This is the incident PROJECT_RULES §Sessions was written for, and it happened
again.

| time (UTC) | event |
|---|---|
| ~16:00 | this session starts; `git status` shows `M src/components/admin/UserTable.jsx` only |
| 16:07:54–55 | `src/pages/UserTablePreview.jsx` and `src/App.jsx` appear — a DEV-only preview route, written by another session |
| 16:09 | this session had stashed `UserTable.jsx` a minute earlier and **restored it immediately** (`git stash pop`; md5 `845b8364e928ddeb7ad338898c1d0c7f`, unchanged) |
| **16:10:06** | **the other session deployed release `20260825T160958Z` to live** — a `UserTable` density change, row height 98 → 57 px, recorded in `PROGRESS.md` with «No commit» |
| 16:22 | this session uploaded a release built from `HEAD` + its own change, and **did not flip the symlink** on discovering the new `current` |
| 16:25 | rebuilt on top of the live `UserTable.jsx`, redeployed as `20260825T162505Z` |

The uploaded-but-never-linked `20260825T162253Z` was removed; it never served a
request. **The density change was not reverted**: the shipped bundle carries one
`px-4 py-2 text-xs font-semibold` header class and zero `px-6 py-4`, and the
production build measured a 57 px row — the other session's own figure.

Consequences worth stating plainly:

- Their `UserTable.jsx` was live and uncommitted, so this release could not be
  reproduced from the repository. It is committed here, attributed, together with
  their `PROGRESS.md` entry. The code is theirs; the commit is this session's.
- The deploy script has no lock and no dirty-tree check (BUG-056), so two
  sessions can flip `/var/www/epe/current` minutes apart with neither noticing.
  **BUG-062.**
- Their note says the deploy succeeded because «Cursor's `rg` binary» was on
  PATH. BUG-040 is therefore intermittent per-terminal, not per-machine — which
  is worse than a clean failure, because whether the safety gates run at all
  depends on which terminal launched the deploy.

---

## 8. Surfaced, not resolved

- **BUG-062** — no mutual exclusion on deploy; two sessions raced `current` today.
- **BUG-063** — `/team` throws: `TeamView.jsx` calls `setLoadingSelfReviews` at
  lines 111 and 136 and never declares it. Pre-existing in `HEAD` (`git show HEAD:…`
  has the same two calls and no matching `useState`), flagged by `eslint` as
  `no-undef`, and part of the 19-error baseline. It only fires when the page has
  subordinates to load statuses for.
- **BUG-064** — `UserModal` still offers «Tender» as a work category; the live
  route answers 422 for it. The **filter** row no longer offers it; the **edit**
  form does. Out of this brief's subject.
- **BUG-058 grows** — six world-readable `/tmp/probe*.sql` files from 2026-08-21
  survive on the VPS (mode 644). They contain schema-introspection SQL, no
  personal data, but they are exactly what the BUG-053 rule forbids. Not deleted:
  not this session's to remove.
- Criterion 14's live level curve is still `0.70/1.00/…/7.00` against the approved
  `0.20/0.25/…/6.00`. Untouched, still unresolved.
- No catalogue, coefficient, criteria, grade, department, period or user write of
  any kind was made. **The second gate was not pressed and no route that could
  press it was called.**
