# EMPLOYEE_SURFACES_POLISH — employee first-use surfaces (2026-08-26)

**Outcome:** the welcome task icons now open the task they describe; the
employee-only rating-guide subset reads as a self-contained 1–3 list without
changing any approved rule text; the own-profile page now shows the employee
card, current-period participation and reason, task status, self-assessment and
the fact of a manager evaluation. The manager's numeric score remains absent
from both the profile payload and the screen. No compensation or money-input
field was added to any touched payload.

The brief arrived with an obsolete live premise. Read-only verification before
editing found that Alexander had already started H1 at
`2026-08-26 10:08:54.340312Z` and had manually excluded Jeren Atabayeva (49) at
`10:11:52.401252Z`. The owner explicitly authorized continuing against that
new baseline. Nothing in this session called the start route or changed scope.

## 1. Before-build inventory — what the own profile showed

The table below was delivered before implementation. One line is one field a
non-admin employee could see on the old profile.

| Поле на экране до этой работы | Откуда оно бралось |
|---|---|
| ФИО | Ответ входа в систему, сохранённый в браузере; не `my-profile` |
| Должность | Ответ входа в систему; не `my-profile` |
| Балл последней самооценки | `my-profile.evaluations[].score` |
| Дата самооценки | `my-profile.evaluations[].updated_at` |
| Период самооценки | `my-profile.evaluations[].period_name` |
| Тип строки «Самооценка» | `is_self_evaluation` |
| Кто оценил: «Вы сами» | Подпись строилась экраном по `is_self_evaluation` |
| Факт оценки руководителем: «Оценено» | Наличие несамооценочной строки; числового балла в ответе не было |
| Период оценки руководителя | `period_name` |
| Имя руководителя | `evaluator_name` |
| Дата оценки руководителя | `updated_at` |
| Для менеджера: факт оценки подчинённым | Наличие строки `evaluation_source=subordinate`; без балла и комментария |
| Для менеджера: период и дата такой оценки | `period_name`, `updated_at` |
| Для менеджера: число оценок подчинённых | Количество таких строк на экране |
| В деталях самооценки: итоговый балл | Отдельный защищённый `evaluation-details` |
| В деталях самооценки: название критерия | `evaluation-details.scores[].criteria_title` |
| В деталях самооценки: балл по критерию | `evaluation-details.scores[].score_value` |
| В деталях самооценки: описание критерия | `evaluation-details.scores[].criteria_description` |

The old `my-profile` payload also carried fields that the ordinary employee
screen did not display:

- envelope: `success`, `has_evaluations`;
- evaluation routing: `evaluation_id`, `evaluation_source`,
  `is_self_evaluation`;
- period dates: `start_date`, `end_date`;
- evaluator job title: `evaluator_title`;
- self-row aliases: `calculated_score`, `weighted_score`;
- summary: `total_evaluations`, `average_score`, `latest_score`,
  `latest_period`, `latest_date`.

Department, manager, grade label, hire date, current-period scope/reason and
tasks were absent from `my-profile`. The live workflow definition was
byte-identical to the generator before editing, so this was not inferred from a
stale export.

## 2. Surface findings

### Task block

The owner's `/admin/users` location did not match the repository:

- the icon block existed only in `src/pages/Welcome.jsx` (`/welcome`);
- `/dashboard` was the manager's subordinate list;
- `/admin/users` was the admin roster and did not render this block.

The block is now `TaskSummary`, shared by `/welcome` and `/profile`. Every
rendered task icon is a real React Router link:

| Icon | Route |
|---|---|
| Самооценка | `/self-review` |
| Сотрудники | `/dashboard` |
| Руководитель | `/manager-evaluation` |

A C-level manager is not represented as a dead task icon; the existing
explanation remains text below the task list.

### Self-review instruction

The filter was exactly:

```text
EMPLOYEE_GUIDE_RULE_NUMBERS = [1, 6, 7]
```

That employee variant is rendered on both `/welcome` and `/self-review`.
The source rule objects and every approved word remain unchanged. Only the
employee presentation changed:

- title: `Краткая инструкция`;
- subtitle: `3 правила — для оценки руководителя и самооценки`;
- visible numbers: 1, 2, 3.

The manager/full guide still reads `Как ставить оценки — 8 правил H1` and
remains numbered 1–8.

## 3. Profile read extension

`GET /api/my-profile` remains identity-bound to the Auth Guard actor. Its SQL
now also reads:

- `employee`: `id`, `full_name`, `job_title`, `department_name`,
  `manager_name`, `grade_label`, `join_date`;
- `current_period`: `id`, `name`, `status`, `start_date`, `end_date`,
  `is_in_scope`, `exclusion_reason`, `scope_override`.

Date columns are formatted as `YYYY-MM-DD` in SQL before crossing the n8n
Postgres node. Grade is `grades.code` only. The query does not select a grade
coefficient, criterion weight, level coefficient, bonus index, salary or any
other compensation column.

The screen adds:

- employee data card: department, position, manager, grade label, hire date;
- participation card: current period and strict true/false/unknown state;
- the existing owner wording from `welcomeExclusionText` when out of scope;
- the linked task summary and each task's completion state;
- the existing self-assessment card and score;
- manager evaluation as `✓ Оценено`, still without a number.

The old descending query was also paired with
`selfEvaluations[selfEvaluations.length - 1]`, so it selected the oldest
self-assessment. It now uses the first row, the actual latest assessment.

## 4. Privacy seals

### D-0820-17 — manager numeric score absent

The stand employee had both:

- self evaluation 31: score `7.00`;
- manager evaluation 32: stored score `5.75`.

The external profile payload returned the manager row with exactly these keys:

```text
evaluation_id, updated_at, is_self_evaluation, evaluation_source,
period_name, start_date, end_date, evaluator_name, evaluator_title
```

It returned no `score`, `calculated_score` or `weighted_score` for that row.
The screen showed `Оценен руководителем: WT Manager` and `✓ Оценено`; `5.75`
appeared nowhere. The format node still assigns numeric fields only inside
`if (isSelfEvaluation)`.

### Compensation and employee-facing money inputs

A recursive key walk over the actual stand profile response found zero keys
matching:

```text
salary, compensation, bonus_index, grade_coefficient,
criteria_weight, score_coefficient
```

The profile SQL and formatter contain none of those names. The existing hidden
`weighted_score` remains confined to the employee's own self row; it is the
self-review metric already present before this brief, not a salary, payout or
bonus-index field.

## 5. Throwaway stand and browser walkthrough

Stand:

- database `epe_walk_20260826_1044`, restored from a fresh live dump;
- container `epe-walk-n8n`, pinned to the same n8n image digest;
- H1 restored as active and started;
- frontend at local `:5299`, API through the loopback-only stand tunnel;
- real fixture logins using the production login workflow.

Ordinary employee (`WT Employee G`, 1303):

1. Clicked `Самооценка` on `/welcome` → `/self-review`.
2. Verified the instruction reads 1, 2, 3 with the approved rule texts.
3. Submitted a 7/6/8 self-assessment through the real form; stored result 7.00.
4. Clicked `Руководитель` on `/welcome` → `/manager-evaluation`.

Manager (`WT Manager`, 1302):

1. Saw all three linked task icons.
2. Clicked `Сотрудники` → `/dashboard`.
3. Submitted 7/6/8/2 for employee 1303 through the real manager form; stored
   result 5.75.

Own profile for employee 1303 showed real fixture values in every requested
field:

```text
Lab Solution Division · Walkthrough employee G · WT Manager · S1
1 January 2025 · H1-2026: participates · self 7.0 · manager: completed
```

Out-of-scope employee (`WT Employee R`, 1309) had fixture hire date
`2026-04-15` and reason `insufficient_tenure`. Their profile showed:

> В оценке за первое полугодие (1 января — 30 июня 2026) вы не участвуете: вы
> приступили к работе после 31 марта, и отработанного периода недостаточно для
> оценки. Это не оценка вашей работы. В оценке за второе полугодие вы
> участвуете в полном объёме, и её результат войдёт в ваш годовой результат.

It also stated that there were no tasks because the employee did not
participate in the period.

The stand container was removed, its database was dropped, its VPS dump was
removed, and the final database inventory was `epe_2026,postgres`. No
non-stand container was restarted.

## 6. Review and validation

Automated:

- `npm test`: **423/423**;
- production build: passed;
- changed-file ESLint: zero errors; one unchanged Fast Refresh warning in
  `TaskStatusContext.jsx`;
- workflow drift before deploy: exactly `My Profile` changed;
- workflow drift after deploy: 32 identical, 0 changed; the two longstanding
  generator-only workflows remain absent.

Independent review found one correctness issue: `is_in_scope=null` produced a
green card with the text `Не участвуете`. Fixed before deployment with strict
true/false/unknown rendering. It also recommended passing `isOutOfScope`
explicitly from Welcome; fixed. Five additional contract tests were added for
the no-evaluation shape, null period/scope state and approved subset.

No new unresolved defect was found, so this brief adds no `bugs.md` row.

## 7. Backup and deployment

Before the first live write, dump pair `20260826T110252Z` was created on the VPS
under root-only staging and copied to the Mac outside the repository:

```text
~/EPE_ROLLBACK/2026-08-26-employee-surfaces-polish/
epe_2026  9ffe553448ebb991d77227db17ada5ea
n8n_app   5f5a812d142287868134519820e2d526
```

Each md5 was identical on VPS and Mac. VPS staging copies were removed after
verification; local rollback copies remain.

Live writes:

1. one PUT to `API: My Profile V5 (Fixed Empty)` at
   `2026-08-26 11:04:26.001Z`; active before/after, webhook remained
   `GET api/my-profile`, Auth Guard unchanged;
2. frontend release `20260826T110433Z`, flipped by the locked
   compare-and-swap deploy from `20260826T085259Z`.

No period, participant, user, evaluation, score, correction, result,
catalogue, coefficient or grade row was written on live.

## 8. Live after

Measured after both deploys:

```text
release/symlink  releases/20260826T110433Z
users            89
terminated       3
H1 in scope      79
campaign tables  0 / 0 / 0 / 0
H1               active / true / started 2026-08-26 10:08:54.340312Z by id 2
workflows         60 total / 35 active / 22 archived
profile workflow  active, updated 2026-08-26 11:04:26.001Z
Auth Guard        inactive, updated 2026-08-18 16:34:30.674Z
```

Money-input fingerprints remain byte-identical to
`docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`:

```text
criteria            fc618757f6aa2c27db5bce7613fc28c7
score_coefficients  317e09e8326edde500bfcde2bad81e78
grades              946b30a5ea8b8594321ebb5fc645bd32
combined            079177fbb9d52ea4c5b942fcecaed1c2
```

HANDOVER §4 formulas, catalogue values, coefficients, grades and every money
path were untouched.

**Implementation commit:** `0c464b1`.
