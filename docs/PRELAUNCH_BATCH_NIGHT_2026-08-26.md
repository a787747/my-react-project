# PRELAUNCH_BATCH_NIGHT — the four hire-date exclusions, the money screens, and the day-one walk (2026-08-25/26)

**Brief:** PRELAUNCH_BATCH_NIGHT. **Decisions:** D-0825-11 … D-0825-15.

**Outcome in one line: the four post-31-March hires are out of H1 scope and told why in the
owner's words, their managers see them present and marked, every employee is told a half-year
pays nothing, /admin/users shows and filters the period state, the bonus screen distributes a
budget that reconciles to the digit over a pool defined by a rule and not by a list of names —
proven on two throwaway stands whose closes agree cell for cell, and on live, where 1 958 user
cells are unchanged and exactly four participants rows moved.**

Live writes tonight: four calls to `POST /api/admin/exclude-participant` at **18:46:18–18:46:19Z**,
five workflow PUTs at **19:47:02–19:47:09Z**, frontend release **`20260825T194735Z`** at
**19:47:35Z**. **The second gate was not pressed and no route that could press it was called.**
Every number below carries the minute it was taken, because the owner logged into the portal at
18:38:43Z and was working while this ran.

---

## 0. What the acceptance list asked for, and where it is

| # | Asked | Where |
|---|---|---|
| 1 | four out of scope, reversible, six other 2026 hires untouched, 84 → 80 | §1 |
| 2 | NULL hire date out of scope, forward-looking only | §2 |
| 3 | stand walkthrough: the excluded person's Welcome, their manager's team surface, a terminated person still hidden | §3 |
| 4 | the sentence quoted from the deployed bundle, both surfaces | §4 |
| 5 | /admin/users ascending, the state, the filter | §5 |
| 6 | the matrix verified, then fixed; rating ≠ index shown and explained | §6 |
| 7 | budget entered, amounts shown, sum equals the budget | §7 |
| 8 | the pool list, the six named | §8 |
| 9 | findings, each with what was on screen | §9 |
| 10 | decisions, progress, handover | §10 |
| — | live after: release, gate, tables, counts, drift | §11 |

---

## 1. Item 1 — the four are out, and only the four

**Live agreed with the marking sheet before anything was written.** The rule, not the list of
names, was run against live at 18:42Z: everybody in scope of period 2 with `join_date >
2026-03-31`. It returned exactly four, with the sheet's ids, names and dates:

| id | name | hired | department | was |
|---|---|---|---|---|
| 25 | David Asatryan | 2026-04-09 | Technical | in scope, reason NULL |
| 64 | Mive Atayeva | 2026-04-27 | Accounting | in scope, reason NULL |
| 22 | Muhammet-Ali Chariyev | 2026-05-01 | Logistics | in scope, reason NULL |
| 63 | Merjen Jumayeva | 2026-05-01 | Sales | in scope, reason NULL |

`scripts/apply_hiredate_exclusions.py` asserts eleven preconditions **before its first write** and
aborts on any of them: H1 active, `evaluation_started_at` NULL on all three periods, the four data
tables empty, `period_scope_events` empty, nobody carrying `excluded_by_admin`, 89 users / 3
terminated / 84 in scope, the rule's output equal to the sheet's four by id **and** by name and
date, all four in scope with reason NULL and not terminated, and seven other people hired in 2026
on or before the cutoff of whom six are in scope and the seventh is the owner's leaver. All eleven
passed. The script issues **no SQL write of any kind** — each exclusion is one call to the real
`POST /api/admin/exclude-participant` built by D-0825-10.

Note recorded for the record: the brief says «the other six 2026 hires untouched». Live carries
**seven** people hired 2026-01-01…03-31 — the seventh is Kuvvat Garayev (51), whom the owner
terminated at 15:54Z today, so six of the seven are in scope. The script asserts that shape rather
than the brief's number.

The four events, read back from `period_scope_events`:

```
1 | 2 | 25 | David Asatryan        | excluded | excluded_by_admin | actor 2 | 18:46:18.349588Z
2 | 2 | 64 | Mive Atayeva          | excluded | excluded_by_admin | actor 2 | 18:46:18.881419Z
3 | 2 | 22 | Muhammet-Ali Chariyev | excluded | excluded_by_admin | actor 2 | 18:46:19.407738Z
4 | 2 | 63 | Merjen Jumayeva       | excluded | excluded_by_admin | actor 2 | 18:46:19.919388Z
note: «принят(а) после 31 марта 2026 — менее трёх месяцев в периоде H1;
       оценка со второго полугодия (D-0825-11)»
```

**Reversible, exactly**, by `POST /api/admin/include-participant` with the same period and user id
— the reverse action D-0825-10 shipped and proved. Their login, their `can_evaluate` /
`can_be_evaluated` flags, their token version and their Annual-2026 row are all untouched (§11).

---

## 2. Item 2 — a missing hire date is out of scope, from the next period on

`API: Manage Periods` → `Build Create SQL`, the participants CTE. Before:

```sql
WHEN u.join_date IS NOT NULL AND u.join_date > '<end>'::date THEN false
ELSE true                      -- a NULL fell through here, silently (BUG-066)
```

After (live `updatedAt=2026-08-25T19:47:02.586Z`):

```sql
WHEN u.terminated_at IS NOT NULL THEN false
WHEN u.join_date IS NULL         THEN false     -- reason 'join_date_missing'
WHEN u.join_date > '<end>'::date THEN false     -- reason 'hired_after_period_end'
ELSE true
```

The order matters and is asserted by a test: with the NULL branch after the comparison, the
comparison's own NULL result falls through to `ELSE true` and the bug is back.

**Not retroactive.** No existing participants row was rewritten. Cem Durukan's H1 row is exactly as
it was — in scope, reason NULL — because D-0821-4 keeps the read-only trio in H1 scope. The new
rule fires for the first time when H2 is created.

**One thing the brief did not resolve, resolved rather than surfaced, and here is why.**
`include-participant` restored only rows whose reason was exactly `excluded_by_admin`. A
`join_date_missing` row would therefore have been a state with **no exit** — the owner's own words
are «must be confirmed», which needs a way to confirm. The reverse route now accepts both reasons.
`terminated` is still refused there, so the two machines still never touch each other's rows.

BUG-066 is closed forward-looking; its row says so in those words.

---

## 3. Item 3 — the excluded are told, and so are their managers

### 3.1 What was in the way

`GET /api/employees` carried the boolean and nothing else: `actor_scope` selected
`epp.is_in_scope`, and the subject list **inner-joined** `epp … AND epp.is_in_scope = true`. So an
out-of-scope person was shown one fixed sentence — «Ваш первый цикл оценки начнётся со следующего
периода» — which is true for a July hire and false for somebody employed since April; and their
manager's list had no row to mark, because the row was joined away.

### 3.2 What changed

- `actor_scope` now also selects `exclusion_reason` and the actor's hire date, and `Format
  Response` passes `actor_exclusion_reason` / `actor_join_date` through its allow-list.
- A **new CTE**, `out_of_scope_team`: the actor's direct reports who are out of scope **and
  `terminated_at IS NULL`**, emitted on their own response key `out_of_scope_data`.
- **`scoped` is untouched.** The task list, every completion flag, every counter and every submit
  path key off `data`, and an out-of-scope person must not be able to reach it. A test pins both
  halves.
- `TaskStatusContext` carries the reason; `OutOfScopeNotice` branches on it; `useTeamRoster` and
  `useDashboardData` expose the new array; one shared component renders it on `/team` and on the
  Dashboard.

Texts are the owner's, verbatim, in `src/utils/scopeExclusion.js`, pinned character for character
by `tests/prelaunchNightBatch.test.js`.

### 3.3 The walkthrough, on a stand with the gate pressed

Fixtures: 1614 «MY Excluded» — employed, reports to 1602, out of scope with reason
`excluded_by_admin`, hired 2026-04-09. 1615 «MY GoneQuiet» — same manager, **terminated**. Both
exist so «the excluded are shown» and «the terminated are hidden» are two behaviours of one join,
demonstrated in one run.

**The excluded person's own Welcome**, logged in as `my.excluded@sedamedical.com`:

> **Вы вне охвата текущего периода оценки**
>
> В оценке за первое полугодие (1 января — 30 июня 2026) вы не участвуете: вы приступили к работе
> после 31 марта, и отработанного периода недостаточно для оценки. Это не оценка вашей работы.
> В оценке за второе полугодие вы участвуете в полном объёме, и её результат войдёт в ваш годовой
> результат.

`/api/employees` for them: `actor_is_in_scope=false`, `actor_exclusion_reason="excluded_by_admin"`,
`actor_join_date="2026-04-09"`, `data` length **0**.

**Their manager's team surface** (both «Моя команда» and «Список команды»), logged in as
`my.manager@sedamedical.com` — four evaluable cards, then a separate block:

> **Не оцениваются в этом периоде**
> Эти сотрудники работают и остаются вашими подчинёнными. Оценивать их в этом периоде не нужно —
> задач по ним не будет.
>
> **MY Excluded** · Night stand excluded by admin · `Без оценки в периоде`
> Не оценивается в этом периоде: принят(а) 9 апреля 2026, меньше трёх месяцев в периоде.
> Оценка — со второго полугодия.

**MY GoneQuiet appears nowhere on that page** — not in the table, not in the section, not in the
page text (`document.body.innerText.includes('GoneQuiet') === false`). Same query, same manager,
same run.

API side, same stand: `data = [1603, 1612, 1604, 1605]`, `out_of_scope_data = [(1614,
excluded_by_admin, 2026-04-09)]`, and 1615 in neither.

### 3.4 Wording that is mine, not the owner's

Two strings, flagged as `EXECUTOR WORDING` in the source and repeated here:

- a person out of scope for `join_date_missing` (nobody today; reachable from H2 on);
- the manager's card line when a hire date is absent, because the owner's sentence contains the
  date and cannot be written without one.

---

## 4. Item 4 — a half-year pays nothing, on both surfaces

Two places, one constant each, identical strings, both asserted equal to the owner's text:

- **Welcome** — `PERIOD_NOTICE_NO_BONUS`, rendered by `PeriodNotice` in **every** period state
  (none / preparation / started) and on **both** Welcome branches, so an out-of-scope person sees
  it too. That is the only block on the page an out-of-scope person reaches.
- **The rating guide** — `RATING_GUIDE_STANDING_NOTE`, above the numbered rules, in every variant,
  so the employee subset (rules 1, 6, 7) carries it as well. Deliberately **not** a ninth rule:
  it is not an instruction about how to score, and making it one would have renamed «8 правил H1».

**Quoted from the deployed bundle over HTTPS** (`assets/index-CfYKJhk3.js`, release
`20260825T194735Z`), with its surroundings:

```js
…результат складывается из двух полугодовых оценок. В декабре 2025 оценка проводилась
один раз за весь год — это первая промежуточная.`,
noBonus:`Оценка за первое полугодие — промежуточная. По её итогам премия не выплачивается:
результат первого полугодия войдёт в годовую оценку вместе с результатом второго полугодия
и повлияет на годовой результат.`,
scope:c?`Сейчас оценивается работа за период с ${o} по ${s}. …
```

```js
…children:s}),o&&jsx(`p`,{className:`px-5 pt-4 text-sm text-slate-700 leading-normal`,
"data-testid":`rating-guide-standing-note`,
children:`Оценка за первое полугодие — промежуточная. По её итогам премия не выплачивается:
результат первого полугодия войдёт в годовую оценку вместе с результатом второго полугодия
и повлияет на годовой результат.`}),o&&jsx(`ol`,{…children:a.map(…
```

The catalogue was not touched. Confirmed by md5 in §11.

---

## 5. Item 5 — /admin/users opens A→Z and says where each person stands

### 5.1 The sort was not descending — there was none

`useUserFilters` opened with `sortField = null`, and `sortUsers` returns the array **untouched**
when the field is null. The visible order was therefore the route's own `ORDER BY u.id DESC` —
newest employee first, an order nothing on screen explained and no header showed as active. It now
opens on `DEFAULT_SORT_FIELD='name'` / `'asc'`, exported from `userSort.js` so the default and the
comparator cannot drift, and «Сброс» returns to the same default rather than to no sort.

Walkthrough: the table opens `Akmyrat Jumahanov · Aleksandr Maloletenko · Alexander Petrosov ·
Alina Naubatova · Alp-Arslan Mametnazar · Alyona Dzhafarova …`.

### 5.2 The state, and the reason

`API: Admin Get Users Data` now LEFT JOINs the active period's participants row and returns
`join_date`, `period_is_in_scope`, `period_exclusion_reason`, `has_period_row` and `period_id`.
**LEFT**, deliberately: an inner join would empty the whole page whenever no period is active, and
would drop a person who has no participants row — the one case that most needs to be visible.

`evaluationStateOf` maps those to seven mutually exclusive states, in this precedence:

| state | badge | when |
|---|---|---|
| `terminated` | Уволен | `terminated_at` set — a property of the person, true even with no period |
| `no_period` | Нет активного периода | no active period at all |
| `no_period_row` | Нет строки участия | no participants row (BUG-067) |
| `hired_after_period_end` | Принят после конца периода | out, that reason |
| `excluded_by_admin` | Выведен из периода | out, that reason |
| `join_date_missing` | Нет даты приёма | out, that reason — **or** in scope with a NULL hire date |
| `in_evaluation` | В оценке | everything else |

An exclusion reason this table does not know degrades to «Выведен из периода», never to «В
оценке»: an unknown exclusion must not read as participation. Each badge carries a `title` saying
what the state means for tasks and for the share of the pool.

### 5.3 The filter

A seventh control, built on the same D-0825-8 contract: options derived from the population,
each with the count it will produce given the other active filters. On the stand:

```
Любое состояние | В оценке (89) | Выведен из периода (5) | Принят после конца периода (3)
                | Нет даты приёма (2) | Уволен (0) | Нет строки участия (1)
```

`89 + 5 + 3 + 2 + 0 + 1 = 100` = the working population, and «Уволен (0)» is visible **before** the
click because the employment control's default hides leavers. Selecting «Выведен из периода»
narrows to five, by name: David Asatryan, Merjen Jumayeva, Mive Atayeva, Muhammet-Ali Chariyev, MY
Excluded — the four live exclusions of §1 plus the fixture.

The column and the control are **off** on `/team`, which shares `UserTable` and `UserFilters` but
is fed by `/api/employees`, a payload with no participants columns: every row there would have
computed to «нет активного периода».

---

## 6. Item 6 — /admin/final-scores: what was wrong before anything was changed

Reported first, as the brief asked. Fourteen defects were established by reading; the seven that
were fixed are marked, and the reasons for not fixing the rest are given.

| # | Defect | Fixed |
|---|---|---|
| D-1 | Criterion columns came from `employees[0]` alone. One checkbox on the first person alphabetically removed the two project columns (weights 1.40 and 1.80) **for everyone**, while `weightedSum` kept counting them — a row's Σ could exceed its visible cells by up to 117.6. The union helper `buildSharedCriteriaGroups` already existed and was wired into the sibling table; this screen never used it. Unrepaired half of BUG-051. | **yes** |
| D-2 | The upward channel is computed by a dedicated SQL CTE and never read by the money path. | no — by design, §4 |
| D-3 | The self channel is transported and never read by the money path. | no — by design, §4 |
| D-4 | `is_in_scope` was inert: out-of-scope and terminated people sat inside Σ, inside «Сумма с коэф. грейда» and inside «Средний итог», and «Сотрудников 88» read as the pool size while the period's own scope table said 84. | **yes** |
| D-5 | `managers_only` and `c_level_only` cells were emitted to people who can never be scored on them: criterion 2 was a permanently empty column for 72 of 88. | **partly** |
| D-6 | Cells were coloured by `getScoreZone(weightedScore, criterion)` — bands written for a raw 1–10 score, fed the weighted product. Criterion 14 at its documented norm of **2** painted «сверх роли» (2 × 1.00 × 1.50 = 3.00); criterion 12 at **7** painted «зона исключительности» (7 × 1.30 × 1.00 = 9.10). The colour was the weight, not the person. | **yes** |
| D-7 | The «Итог» badge bucketed an unbounded index on 3/5/7. An A-grade person with sixes everywhere reads 35.68 and an M3 reads 356.76 — both green. The only way out of green was an all-ones A-grade row. | **yes** |
| D-8 | Two sticky columns, the second pinned at `left-10` inside a first column ~52–57 px wide, so the employee cell painted over the rank cell in the header, every row and the ИТОГО row as soon as the table scrolled. | **yes** |
| D-9 | The CSV wrote `0` where the table wrote `-`, and carried no scope flag. | **yes** |
| D-10 | A cell that is the average of a manager's 2 and a C-level's 10 was visually identical to a pure 6. | **yes** |
| D-11 | A correction on a criterion the manager skipped is silently discarded. | no — unexercised, `score_corrections` empty on live; filed under the existing BUG-068 territory |
| D-12 | Two C-levels filing `c_level_direct` on the same person: last writer wins, no averaging, no count. Inconsistent with the upward channel, which the SQL does average. | no — needs the owner's rule |
| D-13 | A missing grade became a silent ×1.00 on a screen whose stated doctrine (BUG-030) is to refuse rather than substitute. Three people have no grade. | **marked, not refused** |
| D-14 | `getCriterionFinalScore` is duplicated; this screen uses the private copy. | no — behaviour-neutral, out of scope |

**What was actually changed:**

1. Columns are the union of every row's criteria, in group order, and a cell now renders **three**
   distinguishable states where it used to render one dash: a number, `-` («ещё не оценен») and
   `н/п` («не применяется к этому сотруднику»), each with a title saying which.
2. `managers_only` applicability was added server-side **to the matrix and to the close dataset in
   lockstep** — the manager form has always gated criterion 2 on `has_subordinates`, so this makes
   the matrix agree with the form and the frozen result agree with the matrix. `c_level_only` was
   deliberately **not** filtered; the reason is BUG-071 and it is the owner's call.
3. Σ, «Сумма с коэф. грейда» and «Средний итог» count the pool, not the page. Rows that take no
   share stay visible and carry «вне охвата периода» / «не оценивается никем»; the tiles and the
   ИТОГО label name their population («ИТОГО (83 чел. в фонде, 19 вне)»).
4. Colour reads the raw 1–10 score. The final badge is one neutral colour: the index is not a
   rating and no threshold on it means anything.
5. A corrected cell carries `*` and a tooltip: «Менеджер: 9, Mid-level: 5, C-level: 4, Итого: 6.0
   · 6.00 × коэф. × вес 3.00 = 19.80».
6. The rank column has a fixed width and the employee column is offset to match.
7. The CSV writes an empty cell where the screen writes a dash, and carries a «Берёт долю фонда»
   column.

### 6.1 The numbers, computed by hand before the stand existed

Written into `scripts/prove_night.py` as constants with their working, then compared against a
**second, independent** recomputation from the raw database rows — no import of the JavaScript, no
shared helper, applicability restated from the methodology. All five agree exactly:

| person | grade | Σ(score × level-coef × weight) | × grade | index | on screen |
|---|---|---|---|---|---|
| 1602 MY Manager | S2 1.10 | 155.30 | 170.830 | **170.830** | 170.83 |
| 1603 MY LateStart | S1 0.60 | 180.54 | 108.324 | **108.324** | 108.32 |
| 1604 MY Stayer A | A 0.30 | 45.80 | 13.740 | **13.740** | 13.74 |
| 1605 MY Stayer B | S1 0.60 | 291.18 | 174.708 | **174.708** | 174.71 |
| 1612 MY Partial | S3 1.40 | 57.78 | 80.892 | **80.892** | 80.89 |

Σ over the whole pool: **548.494**. The screen's «Сумма с коэф. грейда» reads **548.49** and
«Средний итог (по 83)» reads **6.61** = 548.49 / 83.

Two of these are independent corroboration rather than my own arithmetic: 170.8300 and 108.3240
are the figures the previous session's close produced on its own stand, from its own fixtures,
before this brief existed.

### 6.2 The rating and the index disagree, and that is the design

`1603` and `1604`, side by side:

| | plain rating (formula 1) | bonus index (formula 3) |
|---|---|---|
| 1603 MY LateStart, project, 6 criteria, S1 (0.60) | **7.00** | **108.324** |
| 1604 MY Stayer A, general, 4 criteria, A (0.30) | **5.50** | **13.740** |
| ratio | **1.273** | **7.884** |

The rating says one is 27 % better than the other. The index says one takes eight times the share.
**Both are correct and they are not the same question.** The rating is feedback on a 1–10 scale.
The index is a share of a pool, and it is a weighted sum **without** dividing by the sum of
weights (HANDOVER §4): more criteria means deeper project involvement means a larger share, because
the company earns on projects. On top of that the grade coefficient doubles the gap (0.60 vs 0.30)
and the level coefficients are convex, so a higher score is worth more than proportionally more.
Nothing in this session reconciles them, and nothing should.

### 6.3 Every criterion and every channel, measured

| claim | measurement |
|---|---|
| all four channels reach the payload | manager, self, `c_level_direct` and upward all non-null on the fixture set |
| upward is an average, not a last writer | `subordinate_avg_score = 6.30`, `subordinate_count = 3` from scores 9, 4, 6 |
| corrections reach the screen | `manager_score 9`, `mid_level 5`, `c_level 4` → cell 19.80 from a final of 6.0, marked `*` |
| a project participant gets 8 columns | `[1, 3, 4, 8, 10, 12, 13, 14]` |
| a general employee gets 6 | `[1, 3, 4, 10, 12, 14]` |
| only a manager gets criterion 2 | true for 1602, false for 1603 and 1604 |
| a partial evaluation is blank, not zero | 1612: scored `[3, 8, 13]`, applicable-but-empty `[4, 12, 14]`, `н/п` on 2 |
| an out-of-scope person is a marked row, not a hidden one | 1614 and 1607 emitted with `is_in_scope=false` |

**Which channels feed the money, stated plainly for the record:** the index is built from the
manager path and the `c_level_direct` path only. Self never feeds it (HANDOVER §4) and upward does
not either — so criterion 2 «Качество управления», weight 3.00, is scored in the money by the
manager's own boss alone, and the 360° numbers are display-only. That is the current design, it is
not a defect this session found, and it is worth the owner knowing in one sentence.

---

## 7. Item 7 — the budget

### 7.1 The diagnosis

The screen was a **point-price calculator**, not a budget distributor. The budget was read
(`BonusCalculation.jsx:107`), divided by Σindex, **rounded to an integer**, and the integer — not
the budget — was multiplied into each person's index. Four separate breaks:

1. **Σ bonus ≠ budget.** The residual is `budget − round(budget/Σindex)·Σindex`, bounded by
   ±0.5 × Σindex, so the money that fails to be allocated grows with headcount. The screen showed
   the drifted total next to the typed budget with no flag.
2. **`roundToInt` could zero the whole table.** Any budget below `0.5 × Σindex` rounded the point
   price to 0, every bonus to 0, and every cell back to the «введите бюджет» placeholder — with the
   typed budget still in the field.
3. **With no evaluations the guard `totalPoints > 0` fails**, so typing a budget changed only the
   characters in that input, and the placeholder blamed the admin for an empty database.
4. **`parseFormattedNumber('3.000.000')` returned 3.** `parseFloat` stops at the second dot, and
   `String.replace(',', '.')` replaces only the first comma. A ru-locale admin typing thousand
   separators got a three-manat budget and, via (2), a table of zeros.

### 7.2 The fix

`bonus_i = index_i / Σindex × budget`, allocated by **largest remainder** at two decimals so the
amounts on screen sum to the budget exactly rather than to within a few kopecks. `roundToInt` is
gone; the point price stays as a derived, unrounded display. Number parsing moved to
`parseHumanNumber`, which handles spaces, non-breaking spaces, dots and commas as group or decimal
separators. The screen now distinguishes «no budget entered» from «Σ index = 0», and states
whether the total reconciles.

### 7.3 Proven, on the stand and against hand figures

Typed into the real input, in a real browser, as `3.000.000` — dots, the case that used to return 3:

| person | index | share | amount |
|---|---|---|---|
| MY Stayer B | 174.71 | 31.85 % | 955 569,25 TMT |
| MY Manager | 170.83 | 31.15 % | 934 358,44 TMT |
| MY LateStart | 108.32 | 19.75 % | 592 480,50 TMT |
| MY Partial | 80.89 | 14.75 % | 442 440,58 TMT |
| MY Stayer A | 13.74 | 2.51 % | 75 151,23 TMT |
| 78 others | 0.00 | 0.00 % | 0,00 TMT |
| **ИТОГО (83)** | **548,49** | **100.00 %** | **3 000 000,00 TMT** |

«Итого бонусов: **3 000 000,00 TMT**» · «Сходится с бюджетом: **да, до копейки**» · point price
5 469,52 = 3 000 000 / 548.494.

Four budgets were also reconciled in the proof script — 1 000 000, 2 500 000.55, 999.99 and 1 —
each summing to the entered figure at two decimals, and the **shipped JavaScript** was executed
against the same rows and compared to the Python amount by amount: zero mismatches. A degenerate
case (an index of zero, an empty pool, a zero budget) returns zeros, never NaN.

---

## 8. Item 8 — the pool list maintains itself

**Rule, no identifiers:** a person takes a share iff `is_in_scope` **and** `can_be_evaluated`.
`src/utils/matrixUtils.js:takesBonusShare`. A test asserts no id from `{18, 21, 40, 47, 61}` and no
e-mail from the `Submit Evaluation` denylist appears anywhere in the rule or the screen.

**The rule's output splits cleanly, and the two halves are disjoint.** Measured on the stand,
which carries live's own 89 people:

*Evaluated by nobody — `can_be_evaluated = false`:*

| id | name | role | grade |
|---|---|---|---|
| 2 | Alexander Petrosov | admin | C3 |
| 18 | Bayram Urayev | c_level | C1 |
| 21 | Cem Durukan | c_level | — |
| 40 | Hemra Ashyrov | c_level | — |
| 47 | Jemal Gulberdiyeva | c_level | — |
| 61 | Mekan Yusupov | c_level | — |

Exactly the six the brief names, and exactly D-0825-6's population. **Five of them appear on the
screen's exclusion list; the sixth, Alexander Petrosov (2), does not — `Build Matrix Query` filters
`u.role <> 'admin'`, so the admin never reaches this screen at all.** The rule would exclude him
too; the route excludes him first.

*Out of scope — the nine already decided elsewhere:* Aysoltan Esenova (31) and Govher Balova (35)
by hire date; Halykberdi Orusov (39), Kuvvat Garayev (51) and Murad Bayramov (66) terminated by the
owner (D-0825-7); David Asatryan (25), Mive Atayeva (64), Muhammet-Ali Chariyev (22) and Merjen
Jumayeva (63) by §1.

**Where this differs from the brief, said plainly.** The brief expects the rule to yield «exactly
the six». It yields **fifteen** on live: six by the flag and nine by scope. The brief's condition
for applying neither is that the two definitions do not coincide — and on the population the brief
names they coincide exactly, `can_be_evaluated = false ⟺ {2, 18, 21, 40, 47, 61}`. The other nine
are not a disagreement: they are people who are out of the period, whose exclusion is D-0825-7,
D-0825-11 and the existing hire-date rule, and who cannot take a share of a pool they are not in.
The rule was therefore applied, and both halves are named on screen so nobody has to infer which
is which.

Live effect: **74 of 88** matrix rows take a share. Nobody is silently removed — the screen carries
a «Не берут долю фонда: 19» section listing every excluded person with their reason.

---

## 9. Item 9 — the day-one walk

Read-only, on a stand with the gate pressed, after everything above was built: four real browser
logins (admin, manager, employee, HR) plus an 18-route × 6-actor API sweep. Console: **no errors on
any page**.

| # | What was on screen | What a user would conclude | Verdict |
|---|---|---|---|
| 1 | HR sidebar: «Статусы оценок», «Сотрудники». HR Welcome: «Ваши задачи: Самооценка / Руководитель». `/self-review` renders and submits when typed into the address bar. | «I am told I have a self-review and the portal has no such page.» | **fixed** — BUG-069, D-0825-15 |
| 2 | «Самооценки 2 из 81», «Оценили руководителя 3 из 81», «Оценили подчинённых 1 из 17», «Полностью завершили 5 из 87» | «Six people are missing from the self-review count» — wrong; they are three different populations, none labelled | filed, **BUG-070** |
| 3 | Criteria 1 (weight 5.00) and 10 (1.60) are columns for the five C-level people and can never be filled | «C-level scored zero on the strategic criteria» | filed, **BUG-071** |
| 4 | Analytics: «Средний балл компании 6.61», «Отделов в системе 1» | the company average mixes self, manager, upward and C-level; the department count counts only departments with evaluations | pre-existing and documented (HANDOVER §3); no new row |
| 5 | `/team-scores` as an ordinary manager → 403 `OWNERSHIP_FORBIDDEN` «доступно только руководителю руководителей» | correct: it is a skip-level surface, and the sidebar only offers it to `has_manager_subordinates` | not a defect |
| 6 | An out-of-scope person still occupies a row on the money matrix | now marked «вне охвата периода» and out of every total | BUG-060 mitigated, still open as a product decision |

**The only fix beyond items 1–8 is #1**, and the reason is the brief's own test: two of eighty
in-scope people would have been told on day one that they had tasks they could not open, and they
are the two people the company will ask about the campaign. It is one line of navigation; no route,
guard or payload changed. Everything else was filed.

Also walked and correct, for the record: the manager's additive form for a partially-evaluated
subject opens on exactly the three unscored criteria («Оценено: 0 из 3 · Осталось: 3»); the
employee profile shows their own self-review score and shows the manager's evaluation as «Оценено»
without the number (the D-0820-17 seal); `/admin/periods` reads «Идёт оценка» with the in-scope
count; the HR completion screen loads and lists everyone.

---

## 10. What changed, file by file

**Backend (5 live workflows, PUT at 19:47:02–19:47:09Z, all active before and after, webhook paths
identical):**

| workflow | id | change |
|---|---|---|
| `API: Manage Periods` | `M9ljMDdO1mIl8m1h` | NULL hire date → out of scope; `managers_only` applicability in the close dataset |
| `API: Admin Get Users Data` | `AwID96McjHKyk8WI` | participants LEFT JOIN + `join_date` |
| `API: Manage Period Scope` | `8xK4EnDJrH1b1OJ7` | `include-participant` also reverses `join_date_missing` |
| `API: evaluations-matrix` | `yQNNr0i4UBFNVgMv` | `managers_only` applicability |
| `API: Get Employees (Smart Role Based)` | `bKB4Sb46yWoq1tSV` | actor reason + `out_of_scope_data` |

Every diff was inspected node by node against the surface generated from `HEAD` before the write:
no node added or removed anywhere, and every changed node's diff is this session's own.

**Frontend:** `src/utils/scopeExclusion.js` and `src/utils/evaluationState.js` (new),
`src/components/common/OutOfScopeTeamSection.jsx` (new), plus edits to `periodNotice.js`,
`PeriodNotice.jsx`, `ratingGuideH1.js`, `RatingGuide.jsx`, `OutOfScopeNotice.jsx`,
`TaskStatusContext.jsx`, `Welcome.jsx`, `SelfReview.jsx`, `ManagerEvaluation.jsx`,
`useTeamRoster.js`, `useDashboardData.js`, `TeamView.jsx`, `Dashboard.jsx`, `Sidebar.jsx`,
`userSort.js`, `userFilters.js`, `useUserFilters.js`, `UserTable.jsx`, `UserFilters.jsx`,
`AdminUsers.jsx`, `matrixUtils.js`, `useFinalScoresMatrix.js`, `FinalScoresMatrixTable.jsx`,
`AdminFinalScores.jsx`, `BonusCalculation.jsx`.

**Tests:** `tests/prelaunchNightBatch.test.js`, 29 assertions over all ten items. Three existing
pins were **inverted** and each says why in a comment: the `/admin/users` filter-key list, the
Welcome mount of `OutOfScopeNotice`, and the zone-helper call site (which pinned the D-6 defect).
`npm test` **379/379**. `npx eslint src` is at **15 errors / 13 warnings** — the repo baseline,
which is four errors below HANDOVER's «19/13» because BUG-063's `no-undef` pair was fixed by
`ed390ac`; none of this session's files contribute an error.

**Executors:** `apply_hiredate_exclusions.py`, `verify_prelaunch_night_live.py`,
`setup_night_throwaway.sh`, `seed_night_extra.sql`, `prove_night.py`, `prove_night_close.py`,
`teardown_night_throwaway.sh`, `deploy_prelaunch_night.py`.

---

## 11. Live, after

### 11.1 The anchor

| | |
|---|---|
| File | `epe_2026_prenight_20260825T184211Z.dump` |
| Taken | 2026-08-25 **18:42:11Z**, `pg_dump -Fc --no-owner --no-acl`, **before the first live write** |
| Size | **94 844 bytes** |
| md5 | **`3ecd8fa9cb8f1b6d8f956aded1c13882`** — equal on both copies |
| On the VPS | `/root/epe_stand_tmp/`, mode 600 |
| On the Mac | `~/EPE_ROLLBACK/2026-08-25-prelaunch-night/`, mode 600, **outside the repository** |

**It supersedes `epe_2026_premidyear_20260825T175516Z.dump` (17:55:16Z)** and every earlier anchor.
Restoring it undoes tonight's four exclusions and nothing else — no other epe_2026 row moved.
Rolling back the five workflows is a separate operation: regenerate from `HEAD` and PUT, or restore
last night's `n8n_app` dump.

### 11.2 Drift, cell by cell, against that anchor

The anchor was restored into a throwaway on the VPS and both sides exported as JSON; `dblink` was
never created on live. Throwaway dropped; `SELECT datname` reads `epe_2026, postgres`.

- **1 958 user cells (89 × 22): zero changed.** Not `terminated_at`, not `can_evaluate`, not
  `can_be_evaluated`, not `join_date`, not `token_version`, not `password_hash`, not a salary.
- **1 068 participants cells (178 × 6): exactly four rows moved**, all on period 2 — `(2,22)`,
  `(2,25)`, `(2,63)`, `(2,64)` — and each moved exactly three columns:
  `is_in_scope true→false`, `exclusion_reason NULL→excluded_by_admin`, `updated_at`.
- Every other table md5-identical to the anchor:

| table | md5 |
|---|---|
| `criteria` | `0b1db252890b64f4c7b6a19b3c0a7a19` |
| `score_coefficients` | `35c52a842f09ef34277a454971f957c1` |
| `grades` | `bb1d249f012ed8ace70d4253399f0af3` |
| `departments` | `e15c12ae4e2e8a5d047cd1259300ff0c` |
| `evaluation_periods` | `1d4a866479c046682e5dc1a4821d2652` |

The catalogue, grades, departments and periods hashes are also identical to the **17:55Z** anchor
of the previous brief. `score_coefficients` differs from the hash that report printed — checked
directly by restoring the 17:55Z dump and diffing all 90 rows: **no difference**. The earlier
figure was a different projection, not a change. **No money input moved tonight.**

### 11.3 Invariants

| check | value |
|---|---|
| Users | **89** |
| Terminated | **3** (39, 51, 66 — the owner's, untouched) |
| In scope of H1 | **80 of 89 participants** — 84 → 80 |
| In scope of Annual 2026 | **86** — untouched |
| H1-2026 | `status=active`, `is_active=true` |
| `evaluation_started_at` | **NULL on all three periods** — the gate is unpressed |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| `period_scope_events` | **4** |
| `employment_events` | **3** — untouched |
| `exclusion_reason='excluded_by_admin'` | **4** |
| Extensions | `plpgsql` only |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — before and after every PUT |
| Frontend release | **`20260825T194735Z`**, symlink `/var/www/epe/current → releases/20260825T194735Z` |
| Releases on disk | 35 · previous `20260825T170810Z` is the rollback target |
| Workflows | **60 total** = 38 unarchived (**35 active** + 3 inactive) + 22 archived; **48** webhooks (21 GET / 25 POST / 2 OPTIONS) |
| `auth_sessions` | probe minted and deleted in a `finally`; count unchanged |

Read surface through Caddy with a real admin token: `/api/periods` → H1 `active`,
`evaluation_started=false`, **80 / 89**; `/api/admin/period-scope-events` → four exclusions;
`/api/admin-users-data` → 200 with all 89, exactly three terminated; `/api/employees` →
`campaign_active=false`, `period_in_preparation=true`.

`backups/2026-08-25-prelaunch-night/live_verify.json` — **29 checks, 29 passed**.

### 11.4 The money claim, control against treatment

Two databases restored from one dump of live, seeded identically (asserted: the same evaluations
fingerprint `db71b35d55581831e544e8218d87b19e` on both), and two isolated n8n containers — one
carrying the workflow surface **as committed at HEAD**, one carrying the **working tree**. Both
were closed through their own real `POST /api/periods/close`.

| | |
|---|---|
| Frozen rows | 103 on each side; neither produced a row the other did not |
| Money cells compared | **824** (103 × 8) |
| **Cells that moved** | **0** |
| Pool total | identical to the last digit |
| Frozen indices | 1602 `170.8300` · 1603 `108.3240` · 1604 `13.7400` · 1605 `174.7080` · 1612 `80.8920` — the hand figures |
| An excluded person | freezes `is_in_scope=false, has_data=false`, every rating and both money columns NULL |
| A person with no participants row | has **no frozen row at all** — BUG-067, unchanged and re-measured |

`backups/2026-08-25-prelaunch-night/night_close_proof.json` — 10 checks, 10 passed.
`night_proof.json` — 42 checks, 42 passed.

---

## 12. Surfaced, not resolved

- **BUG-070** — the HR completion card's three unlabelled denominators.
- **BUG-071** — `c_level_only` criteria are still emitted to people who cannot receive them; the
  natural predicate (`can_be_evaluated`) is editable mid-campaign and tying an emitted criteria set
  to it would let one checkbox move a person's index with no evaluation changing. Owner's call.
- **D-11 / D-12 / D-14** of §6, each with the reason for not fixing it.
- **Upward and self do not feed the bonus index.** Not a defect — §4 — but it means criterion 2
  «Качество управления», weight 3.00, is scored in the money by the manager's own boss alone. The
  owner may or may not intend the 360° numbers to stay display-only.
- **Criterion 14's live level curve** is still `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00`
  against the CRITERION9 / D-0824-2 approved `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00`.
  Re-read tonight (`score_coefficients` md5 unchanged), not touched, still unresolved.
- **BUG-040** did not trip: `deploy_epe_frontend.sh` no longer depends on `rg`, and both gates ran
  («legacy :5678 absent, /webhook base present»).
- No catalogue, coefficient, criteria, grade, department, period or user write of any kind was
  made. **The second gate was not pressed and no route that could press it was called.**

---

## 13. Session hygiene

- One dated dump before the first live write, copied to the Mac outside the repository,
  md5-verified on both copies; the anchor it supersedes is named in §11.1.
- Two throwaway databases and two throwaway n8n containers, all removed. The drop loop refuses any
  name without the `epe_mid_night_` prefix, so `epe_2026` can never be a candidate. Afterwards
  `SELECT datname` reads `epe_2026, postgres` and `docker ps` shows the same six containers as
  before. **No container this project does not own was touched, and nothing outside the stand was
  restarted.**
- One verification throwaway, dropped in a `finally`.
- No extension created on live: `pg_extension` reads `plpgsql`.
- Nothing written to `/tmp` on the host; stand artefacts live in `/root/epe_stand_tmp`, mode 600.
- Probe sessions minted and deleted in a `finally`.
- **No mail of any kind was sent.** The HR walkthrough used a password set directly on the STAND
  database, never on live, and no address was contacted.
- The working tree carried **no other session's edits** at any point tonight; `git status` at the
  start was clean and every modified file is this session's.
- `backups/` is gitignored — the proof artefacts and the dumps under
  `backups/2026-08-25-prelaunch-night/` are deliberately not tracked.
