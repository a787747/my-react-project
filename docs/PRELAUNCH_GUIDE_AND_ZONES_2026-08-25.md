# PRELAUNCH_GUIDE_AND_ZONES — rating guide in-product; score zones = norm 6 (2026-08-25)

Frontend, tests and docs only. Labels, colours, copy and docs. No score-value, coefficient,
payload, validation or workflow change. No DB write, no mail, no stand, catalogue untouched.

**Outcome in one line: the ten H1 rules are in the product verbatim; every score band now
treats 6 as the first «хорошо» (5 = attention); criteria 13/14 have their own labels;
H1 stays active / not started / four tables 0.**

**Checked this session:** live `epe_2026` SELECT (periods, four data tables); Caddy access log
for `POST /webhook/api/periods/activate`; HANDOVER §3 channels; CRITERIA_HR_REVIEW §4.3–4.4;
CATALOGUE_FIX_H1; Welcome tracks; CriterionSlider / EvaluationModal / SelfReview /
ManagerEvaluation / matrix legends; `npm test` before and after; local Vite screenshots;
deploy via `./scripts/deploy_epe_frontend.sh`.

H1 activation timestamp **read from live**, not from the brief: Caddy
`POST /webhook/api/periods/activate` **2026-08-24 19:07:36 GMT**, status 200, Chrome from
`/admin/periods`. No `activated_at` column exists. n8n `execution_entity` is pruned
(last row 2026-08-22). No `POST …/start-evaluation` exists in the log (only the 17:14–17:15Z
HEAD/GET probes that 404).

---

## 1. Where the guide renders

Text source: `src/content/ratingGuideH1.js`. Markup only: `src/components/RatingGuide.jsx`.
Title and ten rules equal the brief character-for-character (pinned in
`tests/ratingGuideAndZones.test.js`).

| Surface | Route / component | Who sees it | What is shown |
|---|---|---|---|
| Welcome manager track | `/welcome` when `user.has_subordinates` | managers (and anyone with that org flag) | all 10 rules, expanded |
| Welcome employee track | `/welcome` otherwise | employees without subordinates | rules **1, 7, 8** |
| Manager evaluation form | `EvaluationModal` (Dashboard) | the rater of a subordinate | all 10, **collapsed**; one click on the title opens it |
| Upward rating | `/manager-evaluation` | employee rating their manager | rules **1, 7, 8** above the sliders |
| Self-assessment page | `/self-review` | employee doing self-review | rules **1, 7, 8** |
| Self-assessment form | `SelfReviewModal` | same | rules **1, 7, 8** |

The employee caption under the title («Правила 1, 7 и 8 — …») is chrome, not a paraphrase
of a rule.

DEV-only preview `/__guide-preview` (`src/pages/GuidePreview.jsx`, registered only when
`import.meta.env.DEV`) was used for local screenshots. It is not a production route.

---

## 2. Score bands — before → after

Numbers, scoring and payloads unchanged. `calculateFinalScore` still returns the plain
average to two decimals (test: `{a:5,b:7}` × 1 → `6.00`).

### 2.1 `getScoreZone` — `src/utils/evaluationUtils.js`

Used by CriterionSlider, EvaluationModal confirmation, SelfReviewModal, details modals,
ManagerEvaluation last-score chip, CalculationCard.

Second argument is optional: criterion `id` / `criteria_id`. **13** = volume scale.
**14** = beyond-role (norm 2). Anything else, including aggregates, uses the default
quality scale.

**Default (before)** — `parseInt`, then:

| Scores | Label | Colour |
|---|---|---|
| ≤ 3 | Зона риска | red |
| ≤ 6 | Зона нормы | yellow |
| ≤ 8 | Зона роста | green |
| else | Зона исключительности | purple |

**Default (after)** — 6 is the first «хорошо»; 5 is not good:

| Scores | Label | Colour |
|---|---|---|
| 1–2 | Зона риска | red |
| 3–4 | Ниже ожиданий | orange |
| **5** | **В целом справляется, требует внимания** | amber |
| **6–7** | **Хорошо** | green |
| 8 | Выше нормы | emerald |
| 9–10 | Зона исключительности | purple |

**Criterion 14 (after)** — did not exist as a separate band before (used default, so 2 was
«Зона риска»):

| Scores | Label | Colour |
|---|---|---|
| 1 | Ниже нормы | red |
| **2** | **Норма** | blue |
| 3–6 | Сверх роли | teal |
| 7–10 | Крупный вклад сверх роли | purple |

**Criterion 13 (after)** — before, 2–3 were «Зона риска» (bad-work colour):

| Scores | Label | Colour |
|---|---|---|
| 1–3 | Малый объём | slate (not red) |
| 4–5 | Умеренный объём | sky |
| 6–7 | Норма объёма | green |
| 8–10 | Высокий объём | indigo |

`SCORE_ZONES` in `src/config/constants.js` updated to the default table (was 1–3
«Критический» / 4–5 «Ниже ожиданий» / 6–7 «Соответствует» / 8–10 «Превосходит»).
That constant was unused by `getScoreZone`.

### 2.2 Manager subordinates matrix — `ManagerSubordinatesMatrix.jsx`

Cell colours now go through `getScoreBandChipClasses` (criterion-aware). Legend:

| | Before | After |
|---|---|---|
| green | 8+ Отлично | 9+ Зона исключительности (purple); 8 Выше нормы (emerald) |
| yellow | **5–7 Хорошо** | **6–7 Хорошо** |
| — | (5 sat inside Хорошо) | **5** В целом справляется, требует внимания |
| orange | 3–4 Требует улучшения | 3–4 Ниже ожиданий |
| red | <3 Критично | 1–2 Зона риска |

### 2.3 `ScoreDetailModal.jsx`

Local `getScoreStyle` before: ≥8 Отлично / **≥5 Хорошо** / ≥3 Требует улучшения / else Критично.
After: delegates to `getScoreZone(score, criterion)` (default or 13/14).

### 2.4 `EmployeeScoresModal.jsx`

Before: ≥8 green / **≥5 yellow** / else red (no orange band; 5–7 = «good» colour).
After: `getScoreBandChipClasses(score, criterion)`; correction cells stay amber
(«есть корректировка», not a score band).

### 2.5 `FinalScoresMatrixTable.jsx` — per-criterion cells only

`getScoreColor` before: ≤1 red / ≤3 amber / **≤5 blue** / else green (6+ green, 5 with 4).
After: `getScoreZone(score, criterion).text`.

`getFinalScoreColor` on `final_weighted_score` **not changed** — that number is formula #3
(bonus index), not a 1–10 rating. Surfaced.

### 2.6 `EvaluationsMatrixTable.jsx`

Before: every scored cell was **green** (amber only if a correction exists) — no value band.
After: chip uses `getScoreBandChipClasses` (criterion-aware); correction still amber.

### 2.7 `Analytics.jsx` — display colours/labels only

`getScoreColor` / badge `getScoreZone` / bar-chart legend: 6 is first «хорошо»; 5 is
attention; <5 is the red swatch. **Pie `scoreDistribution` buckets left as they were**
(≥8 / ≥6 / ≥4 / else) with the old labels «Отлично (8-10)», «Хорошо (6-8)», «Средне (4-6)»,
«Требует внимания (<4)». That count is a computation. Surfaced.

### 2.8 Self-review zone promise (copy)

Removed the sentence that 85–90% of staff fall in the yellow and green zones
(`src/pages/SelfReview.jsx`). Honesty / one-shot / no money-impact sentences stay.
The employee guide (rules 1, 7, 8) sits above the warning.

---

## 3. Screenshots — local Vite (`http://127.0.0.1:5173/__guide-preview`)

Campaign is not started, so live Welcome/forms against the API do not open the manager
modal. Screenshots are from the local build of the same components.

| File | What it shows |
|---|---|
| `docs/prelaunch_guide_and_zones/01-manager-track.png` | Manager track: all 10 rules; employee track: 1, 7, 8 |
| `docs/prelaunch_guide_and_zones/03-score-bands.png` | One-click control on the manager form, expanded after the click |
| `docs/prelaunch_guide_and_zones/04-bands-quality.png` | Criterion 3 at **5** (attention, amber) and **6** (Хорошо, green) |
| `docs/prelaunch_guide_and_zones/05-bands-14-13.png` | Criterion 14 at **2** (Норма, blue); criterion 13 at **3** (Малый объём, slate) |

---

## 4. Tests

`npm test` **before: 313/313**. **After: 326/326** (+13 in `tests/ratingGuideAndZones.test.js`).

---

## 5. Deploy and live

Script: `./scripts/deploy_epe_frontend.sh`. Release **`20260825T065554Z`**.
Previous **`20260824T182054Z`** retained (`/var/www/epe/releases/20260824T182054Z/index.html` still present).
`readlink /var/www/epe/current` → `releases/20260825T065554Z`.

**Live after deploy** (SELECT, `postgres_n8n`, user `admin`, db `epe_2026`):

| Check | Result |
|---|---|
| H1 id 2 | `status=active`, `is_active=true`, `evaluation_started_at` NULL, `evaluation_started_by` NULL |
| Annual 2026 id 5 | `draft`, not active, not started |
| Four data tables | `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` all **0** |

No DB write, no mail, no stand, catalogue not touched.

### 5.1 Chunk md5 — local `dist/` = disk `/var/www/epe/current` = served `https://epe.sedamedical.com`

| File | md5 |
|---|---|
| `Welcome-OsSNTMIG.js` | `d25ee869b1a37eae3d67235f26f4214b` |
| `evaluationUtils-CKHXI99z.js` | `62dd9f808a4223f57387f38794381528` |
| `SelfReview-CQT8CMZN.js` | `395aba179156002df978644bf680ecdc` |
| `ManagerEvaluation-Bb7EQz3k.js` | `0c01f55bc3f3bd87177b5a63954c56ea` |
| `Dashboard-B8Em7xUO.js` | `b904cc24112ae383ca28367245571368` |
| `index-C_mvqGch.js` | `7358202c6fb8bcbf0bc56dd7ea781205` |
| `index.html` | `46b93fd441ee184f98f109a3ac279baf` |

### 5.2 Guide text in the served bundle

The ten rules are **not** in `Welcome-OsSNTMIG.js` (lazy page; it only mounts the component).
They are in the shared chunk **`index-C_mvqGch.js`**. That file, local = disk = served, contains
the title and every lead + body **verbatim** (character-for-character against
`src/content/ratingGuideH1.js`). `__guide-preview` / `GuidePreview` are absent from the
production bundle and from `index.html`.

`evaluationUtils-CKHXI99z.js` contains the new labels (`В целом справляется, требует внимания`,
`Хорошо`, `Малый объём`, `Сверх роли`, `Норма объёма`) and does **not** contain the old
`Зона нормы` / `Зона роста`.

---

## 6. Surfaced, not resolved

1. **Analytics pie buckets are a computation.** `scoreDistribution` still counts
   ≥8 / ≥6 / ≥4 / else. Relabelling those slices to «5 = attention» would change
   which departments land in which slice. Display badges and the bar-colour legend
   were updated; the pie was not.
2. **`getFinalScoreColor` / `CalculationCard` apply rating-zone colours to formula #3.**
   `final_weighted_score` / `final_score` there is the bonus index (weighted sum ×
   grade coefficient, no 1–10 ceiling). Thresholds ≤3 / ≤5 / ≤7 were left. A 46.32
   index still paints as the top band.
3. **No letter template in the repo says «Хорошо от 5».** Searched `n8n_workflows/`,
   `docs/INVITATION_WAVES.md`, `docs/MAIL_AND_RUNBOOK_2026-08-19.md`. The SelfReview
   warning that promised yellow/green zones was product UI, not a letter, and is gone.
4. **`docs/LAUNCH_RUNBOOK_H1.md` body below the period line is still the 31 Aug
   morning Activate script.** The period line now states H1 is active since
   2026-08-24 19:07:36Z, not started, and points at HANDOVER §7. The numbered
   «Активировать» steps were not rewritten.
5. **Score colours are client-only.** No live route returns a zone label. Nothing
   on the server to change.

---

## 7. Docs

- `docs/HANDOVER.md` §1 / §3 / §7 (and the header, the one stale «draft» line in §2,
  and the §6 intro so they do not contradict). **§2 frontend row** (this commit):
  release **`20260825T065554Z`**, **22** on disk. **§4 byte-locked:** md5
  `0b2e854c22dc41f1d96e169b375b6350` before and after (slice: `## 4.` through the
  byte before `\n## 5.`, including the trailing `---\n` — same lock as
  `docs/DOCS_HYGIENE_2026-08-24.md`).
- `docs/LAUNCH_RUNBOOK_H1.md` period line: H1 active since 2026-08-24 19:07:36Z,
  not started; points at HANDOVER §7.
- `AGENTS.md` current goal: H1 active since 2026-08-24 19:07:36Z, not started.
- `PROGRESS.md` entry with release id.

---

## 8. Closing table — documents to re-upload (md5)

| File | md5 |
|---|---|
| `docs/PRELAUNCH_GUIDE_AND_ZONES_2026-08-25.md` | `2d745579b4f5cd75979f55749af66d13` (body above this table) |
| `docs/HANDOVER.md` | `8eda4e1cab280d584e77beb96dcfa30c` |
| `docs/LAUNCH_RUNBOOK_H1.md` | `088c34665a44f5486ad9d88bc6a53347` |
| `AGENTS.md` | `df29b238ede53e7a07a2d328e190d661` |
| `PROGRESS.md` | `6a02142257887976a4d4fc457e498f82` |
| `src/content/ratingGuideH1.js` | `fb9cd81d03478243dd506a266fda608b` |
| `src/components/RatingGuide.jsx` | `942119e0a441cc1f4822801d661e8525` |
| `src/utils/evaluationUtils.js` | `97d099c40bf345d5095e90790c645b51` |
| `tests/ratingGuideAndZones.test.js` | `32e13a5501461cc731d1b94a5510f0ed` |
