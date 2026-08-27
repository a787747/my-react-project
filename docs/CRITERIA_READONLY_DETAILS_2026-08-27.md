# CRITERIA_READONLY_DETAILS — C-level can read the ten level texts (2026-08-27)

**Brief:** CRITERIA_READONLY_DETAILS (Grok 4.6, Mac). **Campaign OPEN** since
2026-08-26 10:08:54.340312Z. Catalogue frozen by the second gate — no criterion
text was changed.

**Outcome in one line: a read-only user on `/admin` can open any criterion and
read its description and all ten level texts, with no save / delete / add /
edit control on the page or in the detail; admin editing is unchanged; the
texts on screen match the live catalogue character-for-character; frontend
release `20260827T060913Z`; H1 still active with `evaluation_started_at`
unmoved; tables 0/0/0/0; 89 / 3 / 78; coefficients md5-identical to the
2026-08-26 snapshot.**

---

## 0. What was checked before any UI change

- Working tree at session start: **clean** (`main` `0f7673b`). No owner edits
  in this checkout then or at deploy time. Only this brief's files were
  changed; nothing was stashed or reverted.
- Live before the change (SSH `SELECT`, 2026-08-27): H1 id 2 `active` /
  `is_active=true`, `evaluation_started_at=2026-08-26 10:08:54.340312+00`;
  tables **0/0/0/0**; **89** users, **3** terminated, H1 in-scope **78**;
  catalogue / coefficients / grades md5
  `fc618757f6aa2c27db5bce7613fc28c7` / `317e09e8326edde500bfcde2bad81e78` /
  `946b30a5ea8b8594321ebb5fc645bd32` — equal to
  `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`.
- Frontend then live: `releases/20260826T134725Z` (ROLE_ACCESS_DEPLOY).
- **`manage-criteria` GET already returns `SELECT c.*`.** A minted session as
  Jemal Gulberdiyeva (id 47, `c_level`) against live loopback received **200**,
  **9** rows, keys including `description`, `level_1_desc`…`level_10_desc`
  (and `weight`, which this page does not newly display — it already sits on
  the money screens granted by D-0826-6). Every active row has all ten level
  texts present; `level_0_desc` is empty on all nine. **No backend route was
  extended.** Probe `auth_sessions` row deleted; leftover jti count 0; tables
  still 0/0/0/0.
- **Fresh `pg_dump` was not taken**, and was not needed: this brief writes
  nothing to a campaign, catalogue, coefficient, grade, user, period or
  evaluation table. The only live writes were two short-lived `auth_sessions`
  probe rows (session state), both deleted.

§4 of HANDOVER was not edited. Nothing here touches a formula, a weight, a
coefficient or any money computation.

---

## 1. The gap, and the other C-level surfaces

ROLE_ACCESS (D-0826-6) let `c_level` onto `/admin`. The ten level texts lived
only inside `CriteriaForm`, which `canEdit` (admin-only) gates. C-level saw
titles and the one-line description in the table, and could not open the
scale. The same texts already travel on `GET /api/criteria` and render inside
every evaluator slider — a display gap, not a disclosure question.

The other surfaces C-level was granted were walked in code and, for the
roster, in the live browser:

| Surface | Same gap? | What was found |
|---|---|---|
| `/admin` (criteria) | **yes — closed** | scale only inside the edit form |
| `/admin/users` | no | roster already lists name, role, category, department, grade, manager, period-state; card stays admin-only. `job_title` / full hire-date sit in that card but also on the matrix and calculator this role already reads. Not scale texts. |
| `/admin/all-evaluations` | no | details modal is not `canEdit`-gated |
| `/analytics` | no | no edit form wrapping a payload |
| `/admin/evaluations-matrix` | no | ScoreDetail / employee-scores / c_level-eval modals open for this role |
| `/admin/final-scores` | no | table already shows the read payload (weights included) |
| `/admin/score-calculator` | no | calculation cards already show the read payload |

No other granted surface hid evaluator-facing catalogue texts inside an
unopenable edit form. Nothing was added to a payload; nothing the role
already receives was stripped.

---

## 2. What was built (frontend only)

- `src/components/admin/CriteriaReadout.jsx` — read-only description + levels
  1–10 from the existing criterion object. No input, textarea, select, save,
  delete or add.
- `CriteriaTable.jsx` — every row, every role, has «Показать шкалу (1–10)».
  Opening it renders the readout. Write column / add / cleanup stay behind
  `canEdit === admin`. `CriteriaForm` is byte-identical in behaviour.
- Tests: `tests/criteriaReadonlyDetails.test.js` (4 pins). Full suite
  **443/443** (439 baseline + 4).

No write route, no n8n workflow, no SQL, no catalogue field.

---

## 3. Deploy

`./scripts/deploy_epe_frontend.sh` (exclusive lock + compare-and-swap).

- Baseline at start: `releases/20260826T134725Z`
- Gates: legacy `:5678` absent, `/webhook` present
- **FLIPPED `releases/20260827T060913Z`**
- Symlink target: `/var/www/epe/releases/20260827T060913Z`
- Rollback target remains `20260826T134725Z`

---

## 4. Browser walkthrough on live

Minted JWTs + `auth_sessions` for Jemal (47) and Alexander (2); both deleted
after. No password, no mail.

**C-level (Jemal, 47) on `https://epe.sedamedical.com/admin`:**
- Subtitle: «Каталог критериев — только чтение. Изменения доступны администратору.»
- Nine «Показать шкалу (1–10)» controls. No «Добавить критерий», no «Действия»,
  no «Редактировать», no «Удалить», no «Сохранить», no Excel, no test-data
  cleanup. Sidebar: no Периоды, no Коэффициенты, no Калькуляция бонусов.
- Criterion 1 opened. Description and all ten level texts on screen.
- Roster `/admin/users`: «Найдено: 86», no add / Excel / edit / terminate.

**Admin (Alexander, 2) on `/admin`:**
- «Добавить критерий», «Очистить тестовые оценки», nine «Редактировать»,
  nine «Удалить навсегда», plus the nine scale toggles.
- First criterion opened in the existing form: title, description, audience,
  activity toggle, role checkboxes, «Описания уровней оценки (1-10)»,
  «Отмена», **«Сохранить»**. Cancelled. No save was sent.

---

## 5. Texts on screen vs the live catalogue

Criterion 1, quoted from the live C-level page (DOM `textContent`) and
compared to the live `manage-criteria` GET and to
`docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md`. Match,
including the two spaces in level 10 («доход  прямо»).

**description:** Оценка стратегической значимости для бизнеса компании. Определяет «вес» роли в цепочке создания стоимости. Оценивается насколько критична его функция для существования и прибыли бизнеса. Эта оценка устанавливается c-level менеджментом. Оценивается не только позиция, но и фактическая роль сотрудника и влияние на генерирование дохода.

**level_1_desc:** Базовая поддержка (Уборка, охрана)

**level_2_desc:** Поддержка специалистов (Водители, ассистенты)

**level_3_desc:** Линейное исполнение (Поддерживают процессы в рабочем состоянии).

**level_4_desc:** Квалифицированный исполнитель (Специалисты, выполняющие стандартные задачи).

**level_5_desc:** Основной бизнес-персонал. Те, кто непосредственно зарабатывает деньги или реализует продукт компании, но в рамках локальной ответственности.

**level_6_desc:** Экспертный уровень. Специалисты, чья квалификация напрямую влияет на качество проектов и репутацию и генерацию дохода.

**level_7_desc:** Ключевой специалист, эксперт и руководитель. Руководители отделов поддержки. Люди, которые организуют работу других или решают нестандартные задачи.

**level_8_desc:** Руководитель направления существенно влияющего на генерацию прибыли, но не участвующий в коммерческой деятельности прямо.

**level_9_desc:** Руководители, носители уникальных компетенций, определяющих конкурентное преимущество компании и оказывающие существенную роль на генерацию дохода.

**level_10_desc:** Руководитель ключевого направления генерирующего доход  прямо участвующий в коммерческой деятельности.

Nothing was reworded.

---

## 6. After deploy — campaign invariants

| Check | Value |
|---|---|
| Release / symlink | `20260827T060913Z` → `/var/www/epe/releases/20260827T060913Z` |
| H1 `evaluation_started_at` | `2026-08-26 10:08:54.340312+00` (unchanged) |
| H1 status / active | `active` / `true` |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0/0/0/0** |
| Users / terminated / H1 in-scope | **89 / 3 / 78** |
| criteria / score_coefficients / grades md5 | `fc618757…` / `317e09e8…` / `946b30a5…` = snapshot |

Probe sessions: 2 inserted, 2 deleted, 0 leftover. Browser `localStorage`
cleared. No mail. No container restarted. No schema write.

---

## 7. Session hygiene

- Owner files in this checkout: **none**. Built files are this brief's only.
- `EPE: Auth Guard` untouched.
- Decision: **D-0827-1**.
- Implementation commit: `1a57b81f87c4f4160bc5aecdf1e45404cc5ce42e`.
