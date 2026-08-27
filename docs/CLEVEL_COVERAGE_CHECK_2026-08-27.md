# CLEVEL_COVERAGE_CHECK — live coverage vs the owner's model (2026-08-27, read-only)

**Brief:** CLEVEL_COVERAGE_CHECK (fresh session, on the Mac). **Read-only throughout** — SELECT and
GET only; no write of any kind, no route exercised, no container touched, `evaluation_started_at`
untouched. Every number below was measured against live `epe_2026` and the live `workflow_entity`
definition of `API: Submit Evaluation` between **2026-08-27 08:24 and 08:29 UTC** (each psql batch
stamped with `now()`). The campaign tables were **0 / 0 / 0 / 0** at 08:28:46Z — nobody has
submitted anything yet; scope was 78 of 89 (H1, id 2), unchanged from the 2026-08-26 13:37Z
reading.

**First line, as the brief demands it:** there is **no launch-blocking gap**. The admin account
(id 2) **can** file manager-channel evaluations on its six direct reports — established from the
submit route's own predicates (§3), not from documents.

The one genuine finding is item 5: the `/admin/users` completeness counter deliberately excludes
the `c_level_direct` channel, so under the owner's model (criteria 1 and 10 mandatory for all 72
evaluated people) it can read 72 из 72 while the heaviest criterion in the catalogue (1, weight
5.00) has been filed on nobody. Confirmed from the code, stated in §5, **not fixed** (per brief).
Filed as BUG-079.

---

## Owner-facing summary (Russian, as briefed)

**Главное: блокирующих пробелов нет. Все 72 оцениваемых человека в охвате H1 могут получить
оценку руководителя, и админ-аккаунт может оценить своих шестерых прямых подчинённых через
обычный менеджерский канал — маршрут это разрешает (проверено по коду маршрута, §3).**

### 1. Люди в охвате H1, чей руководитель — C-level или админ

Босс **может** их оценить (у всех троих руководителей `can_evaluate = true`):

Подчинённые Alexander Petrosov (id 2, admin):
- Alyona Dzhafarova (5, manager) — руководитель Alexander Petrosov (admin), оценит: да
- Dovran Soltyyev (27, manager) — руководитель Alexander Petrosov (admin), оценит: да
- Eziz Kurbangeldiyev (33, employee) — руководитель Alexander Petrosov (admin), оценит: да
- Muhammet Davletov (65, manager) — руководитель Alexander Petrosov (admin), оценит: да
- Selbi Muradova (76, employee) — руководитель Alexander Petrosov (admin), оценит: да
- Yelena Son (88, manager) — руководитель Alexander Petrosov (admin), оценит: да

Подчинённые Bayram Urayev (id 18, c_level, `can_evaluate = true`):
- Azat Sherapov (17, manager) — руководитель Bayram Urayev (c_level), оценит: да
- Mekan Hummedov (42, manager) — руководитель Bayram Urayev (c_level), оценит: да
- Jahan Hojayeva (45, manager) — руководитель Bayram Urayev (c_level), оценит: да
- Rejep Annekov (72, employee) — руководитель Bayram Urayev (c_level), оценит: да

Подчинённые Jemal Gulberdiyeva (id 47, c_level, `can_evaluate = true`):
- Aysha Suvhanova (15, manager) — руководитель Jemal Gulberdiyeva (c_level), оценит: да
- Mergen Durdiyev (28, manager) — руководитель Jemal Gulberdiyeva (c_level), оценит: да
- Esmira Bayryyeva (32, manager) — руководитель Jemal Gulberdiyeva (c_level), оценит: да
- Ilyas Muradov (44, employee) — руководитель Jemal Gulberdiyeva (c_level), оценит: да
- Liya Dmitriyeva (52, hr) — руководитель Jemal Gulberdiyeva (c_level), оценит: да
- Sona Rahmanova (80, hr) — руководитель Jemal Gulberdiyeva (c_level), оценит: да
- Svetlana Ismailova (83, manager) — руководитель Jemal Gulberdiyeva (c_level), оценит: да

Босс **не может** их оценить (руководитель — Cem Durukan, id 21, `can_evaluate = false`):
- Alexander Petrosov (2, admin) — но он и сам не оценивается (`can_be_evaluated = false`)
- Bayram Urayev (18, c_level) — но он и сам не оценивается (`can_be_evaluated = false`)
- Jemal Gulberdiyeva (47, c_level) — но она и сама не оценивается (`can_be_evaluated = false`)

Эти трое — единственные в охвате, чей босс не может оценивать, и все трое сами выведены из
оценки по правилу «C-level не оценивается». **Никто из 72 оцениваемых людей не теряет
менеджерскую оценку.**

### 2. Кто подчиняется 21, 40 и 61

- Cem Durukan (21): трое — Alexander Petrosov (2, **admin**), Bayram Urayev (18, c_level),
  Jemal Gulberdiyeva (47, c_level).
- Hemra Ashyrov (40): **никто**.
- Mekan Yusupov (61): **никто**.

Утверждение владельца подтверждается по сути с одним уточнением: под Durukan стоят не только
C-level — один из троих это **админ-аккаунт (роль admin, сам Alexander)**. Все трое действительно
вне оценки (`can_be_evaluated = false`), сами 21/40/61 никого не оценивают и не оцениваются
(`can_evaluate = false`, `can_be_evaluated = false`, менеджера у них нет).

### 3. Может ли админ-аккаунт (id 2) оценивать своих подчинённых менеджерским каналом

**Да.** По предикатам живого маршрута `API: Submit Evaluation` (§3 ниже): менеджерская ветка
требует только «субъект подчинён актору» + `can_be_evaluated`, охват периода для обоих и
`can_evaluate` актора — **ограничения по роли в ней нет**. Все условия для id 2 выполняются.
Его прямые подчинённые (все шестеро в охвате, все оцениваемы):
- Alyona Dzhafarova (5) · Dovran Soltyyev (27) · Eziz Kurbangeldiyev (33) ·
  Muhammet Davletov (65) · Selbi Muradova (76) · Yelena Son (88)

Экран для этого тоже есть: `/manager-evaluation` открыт любой аутентифицированной роли.

### 4. Критерии 1 и 10 — объём и как это будет выглядеть

**Нужно оценить 72 человека** (78 в охвате минус 6 не-оцениваемых C-level/админ). На
2026-08-27 08:28Z оценок `c_level_direct` — **ноль**: не оценён никто из 72.

Как устроена поверхность (`/admin/evaluations-matrix`, «Матрица оценок»):
- **По одному человеку за раз.** Клик по C-level-ячейке строки открывает модальное окно этого
  человека; в нём оба критерия (1 и 10) сразу, оба обязательны к касанию, одна кнопка
  «Сохранить» = один POST. Исправление своей оценки — то же окно.
- **Массового пути нет** — ни мультивыбора, ни импорта. Коллегиальная сессия на всю компанию
  это **72 открытия окна, 144 движка, 72 сохранения** с одного аккаунта.
- **Кто ещё не оценён, видно построчно:** пустая ячейка — пунктирный кружок со звёздочкой
  (подсказка «C-level оценка ещё не выставлена»), заполненная — среднее с «×N» при нескольких
  оценщиках и «ваша оценка: N» в подсказке. Колонки сортируются; **отдельного фильтра «без
  C-level оценки» нет** (фильтры: отдел, грейд, должность, участие в проекте).

### 5. Счётчик «их оценили все, кто должен» и критерии 1/10

**Подтверждено по коду** (`src/utils/campaignSummary.js`): счётчик включает ровно два канала —
менеджерский (если руководитель может оценивать — оценка получена полностью) и восходящий
(получено ≥ ожидаемого). **`c_level_direct` в счётчик не входит намеренно** (комментарий в коде:
общий канал, а не персональный долг 1:1); самооценка тоже не здесь (она в счётчике «Свои задачи
закрыли»). Знаменатель — 72 (в охвате и оцениваемые). Следствие: счётчик может показать
**72 из 72, когда ни один человек не оценён по критерию 1 — самому тяжёлому в каталоге (вес
5.00) — и по критерию 10**. При вашей модели (1 и 10 обязательны) полнота кампании по этому
счётчику не видна. Зафиксировано как BUG-079; **не исправлялось** (по брифу).

### 6. Люди в охвате вообще без оценщика

**Таких нет.** У всех 72 оцениваемых есть руководитель, который в охвате, не уволен и может
оценивать (два независимых запроса, оба пусты); всем 72 доступен и канал `c_level_direct`
(пишущие — 2, 18, 47 — все в охвате). Шестеро в охвате без оценщиков — это 2, 18, 21, 40, 47,
61, все `can_be_evaluated = false`, т.е. вне оценки по решению, а не по пробелу.

---

## Evidence

### §1 The queries and their exact results

All SELECTs ran over live `epe_2026`, schema `performance_db`, via
`ssh root@92.51.45.147 → docker exec postgres_n8n psql -U admin` (the established read
technique). Timestamps: batch 1 at 08:24:49Z, batch 2 at 08:26–08:27Z, final stamp 08:28:46Z.

- **C-level/admin roster** (`role IN ('admin','c_level')`): 2 Alexander Petrosov (admin,
  `can_evaluate=t`, `can_be_evaluated=f`, manager 21) · 18 Bayram Urayev (c_level, t/f, mgr 21) ·
  21 Cem Durukan (c_level, **f**/f, mgr NULL) · 40 Hemra Ashyrov (c_level, **f**/f, mgr NULL) ·
  47 Jemal Gulberdiyeva (c_level, t/f, mgr 21) · 61 Mekan Yusupov (c_level, **f**/f, mgr NULL).
  None terminated.
- **In-scope H1 people with a c_level/admin manager** (join through
  `evaluation_period_participants` period 2, `is_in_scope`): the 17 + 3 rows listed in the
  Russian §1 above, verbatim from the query.
- **Reports of 21/40/61** (all users, any role, any scope): exactly three rows, all under 21 —
  users 2, 18, 47. Zero rows for 40 and 61.
- **Admin's reports** (`manager_id = 2`): 5, 27, 33, 65, 76, 88 — every one `can_be_evaluated=t`,
  none terminated, every one `is_in_scope=true` for period 2.
- **Scope counts** (period 2): 78 in scope, of them **72** `can_be_evaluated=true` and 6 false
  (2, 18, 21, 40, 47, 61 — the c_level set plus admin).
- **No-manager-channel check #1:** in-scope evaluable people with `manager_id IS NULL`, or a
  manager with `can_evaluate` not true, or a terminated manager → **zero rows**.
- **No-manager-channel check #2** (the evaluator-side scope predicate of the route): in-scope
  evaluable people whose manager has no `is_in_scope=true` row for period 2 → **zero rows**.
- **The three `c_level_direct` writers** (2, 18, 47) all have `is_in_scope=true` for period 2,
  so the route's `ep_actor` join passes for each of them.
- **Denylist emails:** users 21/40/61 are exactly `cem@`/`hemra@`/`mekan@sedamedical.com` —
  the three literals in the route's `c_level_direct` branch. The denylist protects nobody else.
- **`c_level_only` catalogue rows:** exactly ids 1 (weight 5.00) and 10 (1.60), both
  `target_audience='all'`, both active.
- **Campaign tables at 08:28:46Z:** `evaluations` 0, `evaluation_scores` 0,
  `score_corrections` 0, `period_results` 0. Zero `c_level_direct` rows in period 2.

### §2 What was NOT found

No in-scope evaluable person without a working manager channel; no person reporting to 40 or 61;
no manager of an in-scope person outside period scope; no terminated manager still carrying
reports in scope.

### §3 The submit route's predicates, verbatim from live

`API: Submit Evaluation` (`workflow_entity` id `tUxHoRn38rJVDxWv`, active,
`updatedAt=2026-08-24 06:10:02.58Z` — unchanged since the pre-gate build). The `Validate
Evaluation` code node builds the relation filter per channel:

```js
if (source === 'manager') {
  relationFilter = `AND subj.manager_id = ${actorId} AND subj.can_be_evaluated = true`;
} else if (source === 'subordinate') {
  relationFilter = `AND actor.manager_id = ${rawSubjectId} AND subj.can_be_evaluated = true AND subj.role NOT IN ('c_level', 'admin')`;
} else {
  relationFilter = `AND actor.role IN ('c_level', 'admin') AND subj.can_be_evaluated = true AND lower(subj.email) NOT IN ('cem@sedamedical.com', 'hemra@sedamedical.com', 'mekan@sedamedical.com')`;
}
```

The surrounding query additionally requires: an active, started, non-annual leaf period; an
`is_in_scope=true` participant row for **both** actor and subject; and `actor.can_evaluate`
(refused 403 `CANNOT_EVALUATE` otherwise). The guard requires capability `can_evaluate` with
`required_roles: []` — **no role check on the manager branch anywhere**. Therefore for actor
id 2 on subjects 5/27/33/65/76/88 every predicate holds (measured in §1), and the answer to the
brief's item 3 is **yes** — from the route, not from documents. `/manager-evaluation` is behind a
plain authenticated `ProtectedRoute` (`src/App.jsx:224`), so the screen is reachable for the
admin account as well.

### §4 The criteria-1/10 surface, from the code

- `src/pages/AdminEvaluationsMatrix.jsx` — the page; C-level zone click →
  `CLevelEvaluationModal` for that one employee (`handleCLevelZoneClick`, gated by
  `canReceiveCLevel`: campaign period shown, subject in scope, `can_be_evaluated`, role not
  admin/c_level).
- `src/components/admin/CLevelEvaluationModal.jsx` — both `c_level_only` criteria in one modal;
  D-0827-3 rule (untouched = dash, submit blocked until both touched); one submit per person.
- `src/hooks/useEvaluationsMatrix.js` (`submitCLevelEvaluation`) — new row →
  `POST /api/submit-evaluation` with `evaluation_source='c_level_direct'`; own existing row →
  `POST /api/update-evaluation`. One subject per call; **no bulk path exists in the codebase**.
- `src/components/admin/EvaluationsMatrixTable.jsx` (C-level cell) — unscored: dashed circle +
  star, tooltip «C-level оценка ещё не выставлена · нажмите, чтобы оценить»; scored: the mean
  that goes into the money (D-0826-1) with `×N` superscript when averaged and «ваша оценка: N»
  in the tooltip. Columns sortable; `MatrixFilters` offers department / grade / job title /
  project participant — no "missing C-level" filter.

### §5 The counter, from the code

`src/utils/campaignSummary.js` — «их оценили все, кто должен `fullyEvaluated` из
`evaluationOwed`» on `/admin/users`:

- Denominator `evaluationOwed` = rows with `is_in_scope` AND `can_be_evaluated` (= 72 today).
- A person counts as fully evaluated iff (`isFullyEvaluatedByOwed`):
  1. **manager channel** — skipped entirely unless the manager exists and
     `manager_can_evaluate`; otherwise `received_manager_eval_complete` must be true;
  2. **upward** — `received_upward_count ≥ expected_upward_count`.
- The module's own header states the design: *«C-level_direct is a shared channel, not a 1:1
  assigned debt. It is not in either counter.»* Self-review sits in the other counter
  («Свои задачи закрыли»), corrections in neither.

So with every manager evaluation and every upward filed but zero `c_level_direct` rows, the
counter reads 72 из 72 — while criteria 1 (weight 5.00) and 10 (1.60) are filed on nobody and
their money cells are NULL. Under the owner's model those two criteria are mandatory for all 72.
**Confirmed; not fixed; BUG-079.**

---

## Session hygiene

- Read-only: SELECT on `epe_2026` and `postgres.workflow_entity`, file reads in the repo. No
  write route, no POST/PUT of any kind, no session minted, no container touched, no stand, no
  mail, no background polling.
- Live drift note: measurements stamped 08:24–08:29Z; campaign tables 0/0/0/0 and scope 78/89
  at both ends of the window — nothing moved under the session.
- `git status` clean before this report; this report + `PROGRESS.md` + `bugs.md` are the only
  repo changes; committed and pushed.

**Commit:** `1e5b0da` (this report, the PROGRESS entry and BUG-079), pushed to `main`.
