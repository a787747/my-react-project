# EVALUATION_FORM_READABILITY — full criterion text, untouched is not a 1 (2026-08-27)

**Brief:** EVALUATION_FORM_READABILITY (Grok 4.6, Mac). **Campaign OPEN** since
2026-08-26 10:08:54.340312Z. Catalogue frozen — no criterion or level text was
changed. §4 of HANDOVER was not edited.

**Outcome in one line: every evaluator form now shows the whole criterion
description; an untouched criterion is a dash and no zone, not «1/10» /
«Зона риска»; submit stays blocked until every applicable criterion is
touched; the ten-level scale opens on demand from the same readout built
yesterday; this is visual, not money — an untouched key never reaches the
route as a 1; frontend `20260827T065624Z`; H1 still active with
`evaluation_started_at` unmoved; tables 0/0/0/0; 89 / 3 / 78; coefficients
md5-identical to the 2026-08-26 snapshot.**

---

## 0. What was checked before any UI change

- Working tree at session start: **clean** (`main` `89d47c6`). Only this
  brief's files were changed.
- Live before the change (SSH `SELECT`): H1 id 2 `active` / `is_active=true`,
  `evaluation_started_at=2026-08-26 10:08:54.340312+00`; tables **0/0/0/0**;
  **89** users, **3** terminated, H1 in-scope **78**; catalogue / coefficients
  / grades md5 `fc618757f6aa2c27db5bce7613fc28c7` /
  `317e09e8326edde500bfcde2bad81e78` / `946b30a5ea8b8594321ebb5fc645bd32` —
  equal to `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`
  (combined `079177fbb9d52ea4c5b942fcecaed1c2`).
- Frontend then live: `releases/20260827T060913Z` (CRITERIA_READONLY_DETAILS).
- Live `CriterionSlider-DAbizQQ8.js` still had `line-clamp-2` on the
  description (the owner's mid-sentence cut «Оценивается: качество работы и
  соблюдение…» is criterion 3). Live `SelfReview` was already unclamped; the
  manager/upward slider was the clamp. Badge/zone on live slider were already
  gated on a selected value — the owner's «1/10» + «Зона риска» is the HTML
  range thumb sitting at 1 plus the first click landing on 1, not a stored
  default.

§4 of HANDOVER was not edited. Nothing here touches a formula, a weight, a
coefficient or any money computation.

---

## 1. Item 2 — diagnosis (answered before the visual change shipped)

Three questions, with the quoted payload. Verdict: **visual, not money. Do
not stop.** An untouched criterion cannot reach the database as a 1 through
the form. A crafted API call can store a partial set, but it stores only the
keys sent — never invents a 1.

### 1.1 What the submit route receives for an untouched criterion

**The key is absent.** Client state starts as `{}`. The HTML range thumb may
rest at 1 (`value={currentScore ?? 1}`) because a range input cannot be
empty; that 1 is not written into form state until `onChange`.
`gradesPayloadFromState` copies only touched keys.

Stand proof (`backups/2026-08-27-form-readability/prove.json`, PASS, all
`ok: true`):

| Call | Request `grades` | Route | Stored scores |
|---|---|---|---|
| empty self-review | `{}` | **422 `NO_GRADES`** — body `"Необходимо указать хотя бы одну оценку"` | nothing |
| forced partial self-review | `{ "3": 8 }` | 200 | `3=8` only |
| manager first subset | `{ "3": 7 }` | 200 `"Evaluation saved successfully"` | `3=7` only |
| manager additive | `{ "4": 6 }` | 200 `"Evaluation extended"`, `scores_added: 1` | `3=7,4=6` |

Quoted empty-form payload the route actually received:

```json
{"grades": {}}
```

Quoted partial payload (criterion 12 never sent, never stored as 1):

```json
{"grades": {"3": 7}}
```

Stand `evaluation_scores` had **zero** `score_value=1` rows after those
calls.

### 1.2 Can the form be submitted while any applicable criterion is untouched?

**No on the UI.** Self-review, manager→subject and upward buttons stay
disabled (`Оцените все критерии (N)`). `handleSubmit` / `submitReview` /
upward `handleSubmit` return early via `untouchedCriterionIds`. Demonstrated
on the stand in a real browser (employee: disabled at `(3)` then `(2)` after
one touch; manager: disabled at `(4)` then `(3)`).

**Yes if the API is called directly.** `NO_GRADES` only when `grades` is
empty. A non-empty subset is inserted as sent. The server does not require a
complete set and does not invent a 1. That is a pre-existing write-route
fact; this brief does not change a write route.

### 1.3 Does the partial / additive path treat such a criterion as missing?

**Yes.** Additive writes only `score_rows` from the payload (`CROSS JOIN
score_rows`). Missing ids stay missing (`missing_criteria_ids`). The stand
additive of `{ "4": 6 }` left criterion 12 (and 14) missing — not stored as 1.

### 1.4 Out of the stop condition, filed not fixed

`CLevelEvaluationModal.jsx` prefills `actor_c_level_score || 5` and can
submit without a touch. That is a **5, not a 1**, so it is outside this
brief's money stop. **BUG-078**, open. Default-5 was not changed.

Self-review `is_update` is still ignored on the server (second self-review →
409 `DUPLICATE_SELF_REVIEW`). Pre-existing; not this brief.

---

## 2. What was built (frontend only)

- `src/utils/evaluationGrades.js` — `isCriterionTouched`,
  `gradesPayloadFromState`, `untouchedCriterionIds`. Untouched keys are
  omitted. The payload never invents a 1.
- `CriterionSlider.jsx` — `line-clamp-2` removed; description is
  `whitespace-pre-wrap` as stored. Corner badge is `—` until a touch; zone
  label only after a touch. Thumb may rest at the left end.
- `SelfReviewModal.jsx` — same badge/zone rule; description was already
  unclamped.
- `EvaluationModal.jsx` / `useSelfReview.js` / `ManagerEvaluation.jsx` —
  submit payload and the submit block use the helper. Buttons stay disabled
  while any visible criterion is untouched.
- `CriterionScaleToggle.jsx` — collapsed «Показать шкалу (1–10)», reuses
  yesterday's `CriteriaReadout` with `showDescription={false}` (the card
  already shows the description). Closed by default.
- `CLevelEvaluationModal.jsx` — description unclamped + the same scale
  toggle. Default-5 **unchanged** (BUG-078).
- `CriteriaReadout.jsx` — optional `showDescription` (default true) so the
  form toggle does not repeat the paragraph.

Forms that show a criterion description, all checked: self-review modal,
manager→subject slider (`EvaluationModal` → `CriterionSlider`), upward
slider (`ManagerEvaluation` → `CriterionSlider`), C-level modal. No
criterion text was reworded; they render the payload field as-is.

The confirmation dialog still `line-clamp-1`s the **title** in the
self-review summary list. That is not the description.

Tests: `tests/evaluationGrades.test.js`,
`tests/evaluationFormReadability.test.js`; readout pin updated. Full suite
**453/453**.

No write route, no workflow PUT, no SQL on live campaign / catalogue /
coefficient / grade / user / period tables.

---

## 3. Throwaway stand

Fresh `pg_dump` of live `epe_2026` (read; no live write) →
`epe_readability_20260827_0644`. VPS + Mac md5
**`5d4b8183b84994f33048ff9f02e3b2b8`**. Isolated n8n `epe-readability-n8n`
on VPS loopback :25679, walkthrough fixture seeded (guard rewritten to
`^epe_readability_`). Campaign inherited open from live.

`scripts/prove_form_readability.py` wrote only to that stand DB (employee G
1303 self-review `3=8`; manager scores on 1303 `3=7,4=6`). Employee N 1308
was reserved for the browser walk and received no stand write from prove.

Stand dropped before deploy: container removed, `epe_readability_20260827_0644`
dropped, `/root/epe_stand_tmp` this-brief files emptied. Remaining databases
on `postgres_n8n`: `epe_2026`, `postgres`.

**Nothing was written to live** except the dump read. No frontend deploy
until after teardown.

---

## 4. Browser walkthrough on the stand

Playwright against the working-tree Vite (`:5299` → stand `:25679`) as
**WT Employee N** (1308, ordinary employee) and **WT Manager** (1302)
evaluating Employee N. Evidence:
`backups/2026-08-27-form-readability/walk.json` (gitignored) and six
screenshots beside it.

**Employee self-review**
- Untouched: badge `—`, no «Зона риска», hint «Выберите оценку от 1 до 10»,
  submit disabled `Оцените все критерии (3)`.
- After first slider → 6: badge `6`, level-6 text «Качественный профи…»
  appears; criteria 4 and 12 still `—`; submit still disabled `(2)`.
- Scale toggle opens `criteria-readout`; level 1 text is the catalogue
  level_1_desc for criterion 3.
- Cancel and reopen: criterion 3 stays 6; 4 and 12 stay `—`; submit still
  `(2)` disabled. (React state held the partial form; the manager remount
  additionally showed «Черновик восстановлен».)

**Manager → subject (Employee N, 4 applicable criteria: 3, 4, 12, 14)**
- Untouched: badge `—`, no zone, submit disabled `(4)`.
- After first slider → 7: badge `7`; others `—`; submit disabled `(3)`.
- Scale open; cancel and reopen: «Черновик восстановлен», 7 kept, untouched
  still `—`.

No form was submitted from the browser. Employee N has no stand evaluation
row from this walk.

---

## 5. Texts on screen vs the live catalogue

Criterion 3 / 4 / 12 descriptions, quoted from the stand DOM (`innerText`)
on both forms, compared to stand `GET /api/criteria` and to
`docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md`.
Character-for-character match (507 / 406 / 345).

**Criterion 3 description (self-review and manager, identical):**
Оценка личной результативности и профессионального поведения. Фокус не только на «что сделано», но и «как сделано». Оценивается: качество работы и соблюдение стандартов и требований (в том числе регуляторных и документационных), соблюдение сроков, результат для внутреннего и внешнего клиента, инициатива, самостоятельность в решении проблем («приносит решения, а не проблемы»), ответственность за результат своей функции. Вклад за пределами своей функции оценивается критерием «Ответственность сверх роли».

**Criterion 4 description:**
Оценка «управленческой стоимости» сотрудника. Насколько руководителю комфортно и легко работать с сотрудником. Оценивается: уровень доверия, автономность, готовность подставить плечо в задачах отдела и отсутствие необходимости в микроменеджменте. Сотрудник либо экономит время руководителя, либо тратит его. Разовый вклад за пределами прямых обязанностей оценивается критерием «Ответственность сверх роли».

**Criterion 12 description:**
Оценка желания сотрудника расти и развивать других. Критерий задает вектор на будущее: в компании ценится не только накопление экспертизы, но и обязательная передача знаний. "Закрытость" и отказ учить коллег расцениваются негативно. Оценивается самообразование, проведение внутренних тренингов, написание инструкций и освоение новых направлений.

**Criterion 3 level 1** (opened from both forms):
Деструктивное отношение. Открытый саботаж, токсичность к клиентам или коллегам. Категорический отказ выполнять задачи («это не входит в мои обязанности»). Грубые ошибки, наносящие ущерб репутации.

Nothing was reworded.

---

## 6. Deploy

`./scripts/deploy_epe_frontend.sh` (exclusive lock + compare-and-swap).

- Baseline at start: `releases/20260827T060913Z`
- Gates: legacy `:5678` absent, `/webhook` present
- **FLIPPED `releases/20260827T065624Z`**
- Symlink target: `/var/www/epe/releases/20260827T065624Z`
- Rollback target: `20260827T060913Z`

Live bundle: `CriterionSlider-BYA8C5YX.js` has `whitespace-pre-wrap` and no
`line-clamp-2`; `CriterionScaleToggle-FXrPnkCD.js` has «Показать шкалу» /
«Скрыть шкалу». `SelfReview-P13rR-o_.js` still has one `line-clamp-1` on the
confirmation **title** list.

---

## 7. After deploy — campaign invariants

| Check | Value |
|---|---|
| Release / symlink | `20260827T065624Z` → `/var/www/epe/releases/20260827T065624Z` |
| H1 `evaluation_started_at` | `2026-08-26 10:08:54.340312+00` (unchanged) |
| H1 status / active | `active` / `true` |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0/0/0/0** |
| Users / terminated / H1 in-scope | **89 / 3 / 78** |
| criteria / score_coefficients / grades md5 | `fc618757…` / `317e09e8…` / `946b30a5…` = snapshot |
| combined md5 | `079177fbb9d52ea4c5b942fcecaed1c2` |

Owner evaluation rows during the session: **none**. Campaign tables stayed
empty. No mail. No container of this project restarted except the throwaway
stand, which was removed. No schema write.

---

## 8. Session hygiene

- Owner files in this checkout: **none**. Built files are this brief's only.
- `EPE: Auth Guard` untouched. No write-route PUT.
- Decision: **D-0827-2**.
- Finding filed, not fixed: **BUG-078** (C-level modal prefills 5).
- Implementation commit: `54c2cebf89bdde5989ffcb67f60a070ccfeeb328`.
