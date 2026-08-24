# Welcome period notice — 2026-08-24

Frontend, tests and docs only. Launch stays paused. H1 (id 2) stayed `draft` /
`is_active=false` / `evaluation_started_at` NULL. No workflow PUT, no DB write, no
mail, no stand. Money screens and hooks were not opened.

**Checked this session:** live `epe_2026` SELECT (periods, four data tables,
`can_evaluate=false`, criterion-14 levels); live `workflow_entity` code nodes for
the upward-channel routes and `GET api/periods`; `docs/HANDOVER.md` §3; the
Welcome track, `CriteriaOverview`, subject-facing reads and every route a
`manager` session reaches; `npm test` before/after; deploy via
`./scripts/deploy_epe_frontend.sh`.

---

## 1. Period notice

Above the task area on Welcome. Out-of-scope people keep `OutOfScopeNotice`; the
period notice still shows (`embedded` composition).

### Feeding route and guard

| | |
|---|---|
| Route | `GET /api/employees` (`API: Get Employees (Smart Role Based)`, live `updatedAt=2026-08-24T06:10:17.952Z`) |
| Guard | `required_roles: []`, `required_capability: ""` — any authenticated session |
| Fields used | `campaign_active`, `period_in_preparation` |
| Fields absent | `period_name` / `start_date` / `end_date` — `current_period` CTE is `SELECT id, status, is_active, evaluation_started_at` |
| Not called | `GET /api/periods` — live `Prepare Guard Input GET` is `required_roles: ["admin", "hr", "c_level"]`. Employee and manager sessions are 403. No workflow change. |

`GET /api/check-self-review` and `GET /api/get-my-manager` carry no period
name/dates. `GET /api/my-profile` has `period_name`/`start_date`/`end_date` only
on evaluation rows; the four data tables are empty, so that cannot feed the
notice.

Title and scope therefore render **only when those fields appear** on the
employees payload. The body and the state line always render.

### Three states (mocked responses → rendered copy)

`buildPeriodNotice` in `src/utils/periodNotice.js`. Compared values:

| Input | `state` | Title / scope | State line |
|---|---|---|---|
| `{campaign_active:false, period_in_preparation:false}` | `none` | hidden | Период оценки сейчас не открыт. |
| `{campaign_active:false, period_in_preparation:true}` | `preparation` | hidden (no name/dates) | Период открыт для подготовки. Задачи самооценки и оценки появятся в день старта, названный в письме о запуске. |
| same + `period_name`/`start_date`/`end_date` | `preparation` | `Промежуточная оценка: Half-A (1 января 2026 — 30 июня 2026)` and the scope sentence with those dates | same preparation line |
| `{campaign_active:true}` + dates | `started` | title + scope shown | Оценка идёт — ваши задачи ниже. |

Pinned in `tests/welcomePeriodNotice.test.js`. Live today is the first row
(H1 draft → employees returns `campaign_active=false`,
`period_in_preparation=false`, `current_period_id=null`).

The body is always the verbatim twice-yearly sentence. Placeholders are Russian
date form (`1 января 2026`), from data, not from the bundle. `src/` contains
neither `H1-2026` nor `2026-06-30`.

The instructional manager track now keys on `user.has_subordinates` (org flag),
not the campaign-scoped task flag, so a manager who registers in the
preparation window still reads the manager-track purple box. Task cards stay
campaign-gated.

---

## 2. Restored visibility wording

Byte-for-byte from `git show a86e45b:src/pages/Welcome.jsx` (parent of
`c02377d`). Diff of the three strings against that parent: **empty**.

| Surface | Restored (equals `a86e45b`) |
|---|---|
| Anonymity box ×2 | `Оценка вашего менеджера остается <strong>анонимной</strong> - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.` |
| Purple box (manager track) | `Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.` |

The PRELAUNCH_COPY_BATCH rewrite of those three strings is gone. The criterion
title on Welcome stays the real one (`Качество управления и развитие команды`).
`CriteriaOverview` no longer quotes «Критерий для оценки руководителя»; it uses
`criteria.id === 2` title with that same fallback.

---

## 3. Welcome string inventory (all tracks)

`before` = `c02377d` (deployed PRELAUNCH_COPY_BATCH). `after` = this brief.
Unchanged strings are marked `=`.

### Shared chrome

| String | Before | After |
|---|---|---|
| Добро пожаловать в систему оценки! | = | = |
| Эта страница поможет вам понять… | = | = |
| Обращение к сотрудникам | = | = |
| Система оценки производительности предназначена… | = | = |
| Все данные оценок доступны только руководству компании (C-level менеджерам)… | = | = |
| **Period notice title** | — | `Промежуточная оценка: {name} ({start} — {end})` when data present; hidden in `none` and when name/dates missing |
| **Period notice body** | — | `С 2026 года оценка проводится дважды в год — за первое и за второе полугодие; годовой результат складывается из двух полугодовых оценок. В декабре 2025 оценка проводилась один раз за весь год — это первая промежуточная.` |
| **Period notice scope** | — | `Сейчас оценивается работа за период с {start} по {end}. … после {end}…` when data present |
| **State · none** | — | Период оценки сейчас не открыт. |
| **State · preparation** | — | Период открыт для подготовки. Задачи самооценки и оценки появятся в день старта, названный в письме о запуске. |
| **State · started** | — | Оценка идёт — ваши задачи ниже. |
| Ваши задачи | = | = |
| Активный период оценки / Оценка не идёт | = | = |
| CampaignNotStartedNotice (inside task card) | = | = |
| Самооценка / Сотрудники / Руководитель / Выполнено / C-level | = | = |
| C-level менеджеры не оцениваются подчиненными | = | = |
| Дополнительные критерии + paragraph | = | = |
| Готовы начать? + footer | = | = |
| Вы вне охвата текущего периода оценки + body | = | = (still shown; notice now sits above it) |

### Manager track

| String | Before | After |
|---|---|---|
| Процесс оценки (для менеджеров с подчиненными) + intro | = | = |
| Самооценка и оценка вашего менеджера + step body | = | = |
| Важно: Анонимность оценки вами своего менеджера | = | = |
| **Anonymity box** | Оценка вашего руководителя остаётся анонимной для него: … остальные результаты откроются отдельным решением. | owner sentence restored (table §2) |
| Оценка качества управления от подчиненных + step body | = | = |
| **Purple box** | Полученные оценки видят тот, кто оценил, администратор и C-level. … | owner sentence restored (table §2) |
| Качество управления и развитие команды (heading + quote) | = (already the real title) | = |
| Оценка ваших подчиненных + info box | = | = |
| Оценка старшего менеджера (опционально) + body | = | = |
| Оценка C-level менеджеров + body | = | = |

### Employee track

| String | Before | After |
|---|---|---|
| Процесс оценки (для сотрудников без подчиненных) + intro | = | = |
| Step 1 heading + body | = | = |
| **Anonymity box** | batch rewrite | owner sentence restored (same as manager track) |
| Оценка вашего менеджера + info box | = | = |
| Steps 3–4 | = | = |

Track switch: before = campaign `hasSubordinates` (false while H1 is draft, so
managers saw the employee track). After = `user.has_subordinates`.

---

## 4. Upward-channel seal

Expected vs live definitions (active `workflow_entity`, 2026-08-24) and the
generated workflows the tests execute. Compared values, not slogans.

### Subject-facing reads

| Route | Node | Expected | Live / generated compared |
|---|---|---|---|
| `GET /api/evaluation-details` | Build Details Query | Readers: author, `admin`, `c_level`. Evaluated manager: 404 | `privileged = ['admin', 'c_level']`. WHERE: `privileged OR evaluator_id = actor OR (subject_id = actor AND is_self_evaluation = true)`. HR not in the list. Live `updatedAt=2026-08-20T15:46:53.474Z` |
| same | Format Response | empty set if SQL returned nothing | `http_status: 404` / «Оценка не найдена или недоступна вам» |
| `GET /api/my-profile` | Build Profile Query | row reaches the subject | `WHERE e.subject_id = ${actorId}`. No `general_comment` / `private_comment` columns. Live `updatedAt=2026-08-20T15:46:56.673Z` |
| same | Format Response | no score / calculated_score / weighted_score; no comments; no evaluator identity on upward | `if (isSelfEvaluation) { evaluation.score / calculated_score / weighted_score }`. `evaluator_name/title: row.evaluation_source === 'subordinate' ? null : …` |
| `GET /api/evaluation-history` | Build History Query | received upward either absent or stripped | **given-only**: `WHERE e.evaluator_id = ${actorId} AND e.is_self_evaluation = false`. Received upward does not reach this route. Live `updatedAt=2026-08-19T08:40:21.096Z`. Name says Received; SQL is Given |
| `GET /api/hr/evaluation-status` | Build Status Query | flags only | `has_self_review`, `evaluated_manager`, `evaluated_subordinates`. No `calculated_score` / `score_value` / `general_comment` / `private_comment`. Guard `["hr","admin","c_level"]`. Live `updatedAt=2026-08-19T11:52:23.172Z` |

### Manager-role surfaces (no upward scores, comments or aggregates, any subject)

| Surface | Guard | Upward content? | Compared |
|---|---|---|---|
| `/welcome`, `/dashboard`, `/self-review`, `/manager-evaluation` | `ProtectedRoute` | flags only (`has_evaluated_manager`, `evaluated_by_actor`) | `/api/employees` |
| `/profile` | `ProtectedRoute` | row existence + period name; scores/comments/identity stripped (above) | my-profile Format |
| `/history` | `ProtectedRoute` | author's own given rows, including upward they wrote — author is an allowed reader | history WHERE evaluator_id = actor |
| `/team-scores` | `ProtectedRoute` (nav: `has_manager_subordinates`) | no | `API: Manager Subordinates Matrix` `updatedAt=2026-08-24T08:33:51.330Z`. Cells: `self_score`, `manager_score` (`evaluation_source = 'manager'`), corrections. No `evaluation_source = 'subordinate'`, no `avg_subordinate_score` |
| `/team` | `ManagerRoute` | no | `useUsers` → `GET /api/admin-users-data` (admin-only, 403). `SubordinateEvaluationsModal` calls `GET /api/admin/evaluation-details-by-user` (`required_roles: ["admin","c_level"]`) → 403. Client also hides scores below admin/c_level |
| `GET /api/admin/evaluations-matrix` | `["admin","c_level"]` | has `manager_scores_from_subordinates` AVG | manager-role is 403. Page is `ReportingRoute` |
| `GET /api/get-my-manager` | any session | `last_evaluation_score` / `previous_scores` of **the actor's own** upward | author, allowed |

**Verdict:** the server enforces D-0824-3. BUG-036 row 2 is closed by that
decision. No manager-role leak of upward scores, comments or aggregates was
found. Surfaced (not a leak): history is given-only despite the workflow name;
Profile still prints the label «Оценен подчиненным:» against a nulled
`evaluator_name`.

Pinned in `tests/upwardChannelSeal.test.js`.

---

## 5. Tests

| | Count |
|---|---|
| `npm test` before (c02377d / PRELAUNCH_COPY_BATCH) | **295 / 295** |
| `npm test` after | **312 / 312** |

+17: `tests/welcomePeriodNotice.test.js` (three states, Russian dates, git-equal
restored strings, no hardcoded period literals, CriteriaOverview title,
employees feed) and `tests/upwardChannelSeal.test.js` (details 404, profile
strip, history given-only, HR flags, employees fields, periods guard,
manager matrix). `tests/prelaunchCopyBatch.test.js` visibility assertion
inverted to the owner wording.

---

## 6. Deploy

`rg` on PATH. Two gates also run by hand on `dist/` after the script's build:

```
GATE1 OK: legacy :5678 absent
GATE2 OK: /webhook present
```

Release **`20260824T182054Z`** → `/var/www/epe/current`. Previous
`20260824T175642Z` retained (21 releases on disk). Public `index.html`
`Last-Modified` Mon, 24 Aug 2026 18:20:42 GMT.

First SSH after the local build reset; the same `dist/` was uploaded on retry.
Gates by hand on that `dist/`:

```
GATE1 OK: legacy :5678 absent
GATE2 OK: /webhook present
```

Chunk md5 local build = live disk = served origin:

| Chunk | md5 | Notes |
|---|---|---|
| `Welcome-CWMqY5Vy.js` | `b11a56539f9950aafedb77965e73f205` | restored visibility + real criterion title |
| `index-BOLi6bRW.js` | `c28a45b2405a65ee3ec22d016ab5210f` | verbatim period notice (body, three state lines, title placeholder) |
| `useProfile-DfGaubnV.js` | `d75c907f6287bf98f95b89e296fce06c` | CriteriaOverview real title; fake title absent |

Served HTTPS (`https://epe.sedamedical.com/assets/…`): owner anonymity sentence present; purple-box sentence present; notice body and all three state lines present in `index-BOLi6bRW.js`; `H1-2026` / `2026-06-30` absent from the served chunks; fake criterion title absent.

Live campaign after deploy (SELECT 2026-08-24 18:21Z): H1 id 2 `draft` /
`is_active=false` / `evaluation_started_at` NULL on all three; `evaluations` 0,
`evaluation_scores` 0, `score_corrections` 0, `period_results` 0.

---

## 7. Riders

### D-0824-3

Appended to `DECISIONS.md` **verbatim**. D-0820-17 and HANDOVER §6.13 / September
table scoped: later results-release is manager → subordinate only.

### BUG-034 / 035 / 036 / 037

Already closed by PRELAUNCH_COPY_BATCH. This brief: BUG-036 row 2 closed by
D-0824-3 with the table in §4; CriteriaOverview leftover closed. Recount:
**16 `🔴 OPEN` / 37 `🟢 CLOSED`** (16 named OPEN rows including BUG-010's
re-scoped line; 37 CLOSED). Header matches.

### `can_evaluate=false` (SELECT 2026-08-24 ~18:15Z)

| id | name | role |
|---|---|---|
| 21 | Cem Durukan | c_level |
| 40 | Hemra Ashyrov | c_level |
| 61 | Mekan Yusupov | c_level |

Exactly **21 / 40 / 61**. Capability is the universal write gate on the submit
routes by design. The FINALIZE HR leftover (ids 52 / 80 with `can_evaluate=true`)
is closed without code — they are ordinary participants, not the read-only trio.

### Criterion 14 levels (read-only, same SELECT)

Live: `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00`.

Approved: `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00`.

**Not equal.** HANDOVER §3 live-curve note left in place. Coefficients were not
written.

---

## 8. Surfaced, not resolved

1. No employee-readable source for period **name + dates**. State is
   distinguishable. `GET /api/employees` needs `period_name`, `start_date`,
   `end_date` on the existing campaign payload (or a new employee-readable
   period-meta route). `GET /api/periods` already has them and refuses
   `employee` / `manager`.
2. Criterion 14 live level curve ≠ approved curve (owner restores it).
3. `evaluation-history` workflow name says Received; SQL is Given.
4. Profile UI still labels «Оценен подчиненным:» on a nulled identity field.
5. TeamView still calls undeclared `setLoadingSelfReviews` and admin-only APIs
   (BUG-012; not this brief).

---

## 9. Files to re-upload (md5)

No workflow file. Frontend already switched.

| File | md5 | Where |
|---|---|---|
| `Welcome-CWMqY5Vy.js` | `b11a56539f9950aafedb77965e73f205` | live `releases/20260824T182054Z/assets/` |
| `index-BOLi6bRW.js` | `c28a45b2405a65ee3ec22d016ab5210f` | same |
| `useProfile-DfGaubnV.js` | `d75c907f6287bf98f95b89e296fce06c` | same |
| `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md` | `b8559e1e571496c4a689912e513c91b9` | repo (hash of this file before the closing table below) |
| `DECISIONS.md` | `8e10570b055d5692fb71452dd5b7692c` | repo |
| `bugs.md` | `44acef9fb678c298c45d8eccc4839527` | repo |
| `PROGRESS.md` | `f5b74cf2a773f3fe4c0a9fd2185cf0ae` | repo |
| `docs/HANDOVER.md` | `ba0b735782b8d51edb5bb94f8dc93f18` | repo |
| `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md` | `2072ba936c4fdcd8b1d96e77eb5888e4` | repo (unchanged this brief) |

---

## 10. Closing table — documents to re-upload (md5)

Not build chunks.

| File | md5 |
|---|---|
| `docs/WELCOME_PERIOD_NOTICE_2026-08-2x.md` | `b8559e1e571496c4a689912e513c91b9` (body above this table) |
| `DECISIONS.md` | `8e10570b055d5692fb71452dd5b7692c` |
| `bugs.md` | `44acef9fb678c298c45d8eccc4839527` |
| `PROGRESS.md` | `f5b74cf2a773f3fe4c0a9fd2185cf0ae` |
| `docs/HANDOVER.md` | `ba0b735782b8d51edb5bb94f8dc93f18` |
| `docs/PRELAUNCH_COPY_BATCH_2026-08-2x.md` | `2072ba936c4fdcd8b1d96e77eb5888e4` |
