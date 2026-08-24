# Browser-driven walkthrough of the campaign UI — 2026-08-24

Retires the standing "not browser-driven" debt: every campaign flow below was executed in a
**real Chromium** against a throwaway stand, as the humans will run it — login form, buttons,
modals, dialogs — with DOM assertions and the browser's own network log as evidence. Live saw
no activation, no campaign write, no mail; the only live change is the frontend deploy of the
one fix made under the brief's latitude (§6).

## 1. The stand

| Thing | Fact |
|---|---|
| Scripts | `scripts/setup_walkthrough_throwaway.sh` + `seed_walkthrough_throwaway.sql` (copies of the finalize trio; prefix `epe_walk_` is load-bearing) |
| DB | `epe_walk_20260824_1236`, restored from a dated dump of live (89 users, 9 active criteria verified); dump kept in `backups/2026-08-24-walkthrough/` (gitignored) |
| n8n | `epe-walk-n8n`, live-pinned image, VPS loopback :25679, guard imported with live id `L0Zr7nVa8O5YWXd3`, **28 workflows active** — the full generated surface (auth login + every route the frontend calls), mail workflows inactive, no SMTP credential |
| Frontend | HEAD via `vite` :5299, `VITE_DEV_API_PROXY=http://127.0.0.1:25679` (`.claude/launch.json` `epe-hier-vite`) |
| Browser | Chromium (Claude Code browser pane), two tabs where a stale-tab race was needed |
| Fixtures | actors 1301–1310 (finalize shape) **plus real scrypt password hashes** — the browser logs in through the actual `auth/login` workflow. Fixture password `Walk2026-Portal!`, emails `wt.*@sedamedical.com` (the login workflow refuses other domains; nothing on the stand can send mail) |
| Teardown | container removed, `epe_walk_*` dropped (`epe_2026` is the only `epe_*` DB left), walkthrough tmp dump removed, tunnel killed |

Two setup traps worth recording: (1) `ssh` inside a `while read` loop eats the heredoc — the
activation loop stopped after one workflow until `ssh -n` (script fixed); (2) `n8n
update:workflow --active=true` does **not** register webhooks — the container must be
restarted afterwards, and the restart kills the local tunnel.

Driving note: the browser pane's modifier/Tab keys do not reach the page, so text fields were
set via the native value setter + `input` event and forms submitted with `requestSubmit()` —
the real React handlers, validation, and XHR run; `window.confirm`/`alert` were intercepted
in-page, which also captures their exact texts as evidence. All flows below are otherwise
clicked through the rendered UI.

## 2. Flow 1 — Employee (`wt.employee.g`, then `wt.employee.r`)

| # | Check | Result | Evidence (verbatim) |
|---|---|---|---|
| 1.1 | Login form → redirect | ✅ | `/login` → «Войти» → `/welcome`; sidebar shows only ЛИЧНЫЕ section; badge «WT Employee G / employee» |
| 1.2 | No active period: zero tasks | ✅ | «Ваши задачи» → «Оценка не идёт» → «Период оценки не открыт» / «Сейчас нет идущего периода оценки. Задачи появятся, когда администратор откроет период и запустит оценку.» |
| 1.3 | Preparation window (after gate 1): zero tasks | ✅ | «Оценка ещё не началась» / «Период открыт, но оценка пока в подготовке. Как только она начнётся, задачи появятся здесь автоматически — ничего делать не нужно.»; `/self-review` full-page shows the same notice |
| 1.4 | After «Запустить оценку»: tasks appear | ✅ | same account: sidebar «МОИ ЗАДАЧИ» (Самооценка / Руководитель); «Ваши задачи» → «Активный период оценки» with two task cards |
| 1.5 | Self-review renders criteria 3/4/12 | ✅ | intro «Вам доступно 3 критерия для оценки.»; modal = exactly «Личная результативность и эффективность», «Надежность и взаимодействие с руководителем», «Профессиональное развитие и обмен знаниями», three 1–10 sliders |
| 1.6 | Submit | ✅ | 7/8/6 → «Сохранить самооценку» → «Подтверждение самооценки» → «Подтвердить» → `POST /webhook/api/self-review-submit` → 200 `{"success":true}`; DB row: `calculated_score 7.00` (simple mean), `weighted_score 5.66` — **computed server-side** |
| 1.7 | **Network: no coefficients fetch, no weighted_score in payload** | ✅ | Employee R, fresh tab, XHR recorder installed before submit. Payload verbatim: `{"user_id":1309,"final_score":6,"grades":{"3":5,"4":6,"12":7},"comments":{},"is_update":false}` — **no `weighted_score`**. Full tab network log = 13 webhook calls (`check-self-review`, `criteria`, `get-my-manager`, `employees`, `self-review-submit`) — **zero `score-coefficients` requests** |
| 1.8 | Done state | ✅ | «Вы уже оценили себя в этом периоде» |

## 3. Flow 2 — Manager (`wt.manager`, `wt.midmanager`), upward, reclassification

| # | Check | Result | Evidence (verbatim) |
|---|---|---|---|
| 2.1 | Team list | ✅ | «Моя команда» / «Сотрудники в вашем подчинении»: 4 cards; counts G/N/R «Общие: 4», P «Общие: 4 · Проект: 2»; G and R carry «Самооценка ✓» |
| 2.2 | Modal, project subject (P) | ✅ | 6 sliders; groups «⭐ Основные / 📋 Общие / 🎯 Проектные»; present = 3,4,12,**14**,**8**,**13**; absent = 1,10 (c-level), **2** (managers-only); «Категория: проектные» + pill «Участник проекта» |
| 2.3 | Modal, general subject (G) | ✅ | 4 sliders; present = 3,4,12,**14** only; «Категория: общие» |
| 2.4 | Criterion 14 for everyone | ✅ | present in every modal (P, G, N, manager-subject) and both admin matrices |
| 2.5 | Criterion 2 only for manager subjects | ✅ | mid-manager's modal for WT Manager: 5 sliders = 3,4,12,14 + «Качество управления и развитие команды» under «Критерии управления»; absent from every employee-subject modal |
| 2.6 | Submits | ✅ | P, G, N → «Подтверждение оценки» → `POST api/submit-evaluation` 200 each; DB rows 33/34/35 (7.50 / 7.00 / 7.00); buttons «Оценить» → «Редактировать» |
| 2.7 | Admin reclassifies general → project in UI | ✅ | `/admin/users` → N row pencil (aria «Редактировать WT Employee N») → `#work_category` General→Project → «Сохранить» → `POST /webhook/admin/save-user` 200 → row shows «Project» |
| 2.8 | «Дооценить» names the missing criteria | ✅ | manager dashboard: amber badge «Новые критерии: 2», title/aria «Добавились критерии: **Взаимодействие и надежность в проекте, Объем проектной работы и загрузка**»; button «Дооценить (2)» |
| 2.9 | Additive modal = ONLY the missing | ✅ | exactly 2 sliders, criteria 8 and 13 only; submit «Оценить новые критерии» → 200 → «Новые критерии оценены!» |
| 2.10 | Flag closes; one evaluation, merged | ✅ | reload: badge gone, button «Редактировать»; DB: still ONE evaluation (id 35), 6 score rows (3,4,8,12,13,14), `calculated_score 7.17` (=43/6) |
| 2.11 | Upward evaluation of own manager | ✅ | G `/manager-evaluation`: «Оценка руководителя», subject WT Manager, «Ожидает оценки», **exactly 1 slider — criterion 2**; slider 8 → «Отправить оценку» → «Оценка успешно сохранена!»; admin matrix manager-row management column shows «8 / -» |

## 4. Flow 3 — Admin

| # | Check | Result | Evidence (verbatim) |
|---|---|---|---|
| 3.1 | `/admin/periods` states | ✅ | one table, all states in sequence: «Контейнер» (+«дочерних периодов: 1») · «Неактивен» · after gate 1 «Активен · подготовка» + «Оценка не запущена — сотрудники не видят задач» + pill «Подготовка» · after gate 2 «Идёт оценка» + «Запущена 24 августа 2026 г.» + pill «Текущий период» · «Закрыт» (Annual 2025) |
| 3.2 | Gate buttons + confirms | ✅ | «Активировать» → confirm «Активировать этот период? Текущий активный период будет деактивирован.» → `POST api/periods/activate` 200; «Запустить оценку» → confirm «Запустить оценку в этом периоде?\n\nСотрудники сразу увидят задачи и смогут отправлять оценки. Каталог критериев будет заморожен. Отменить запуск нельзя.» → `POST api/periods/start-evaluation` 200 |
| 3.3 | `/admin/scoring` renders all 9 criteria | ✅ | 9 sections incl. «Ответственность сверх роли»; 7 grade inputs (0.3/0.6/1.1/1.4/2.2/3/3) + 9 weights (5/3/3/1.5/1.4/1.6/1/1.8/1.5) |
| 3.4 | Coefficient edit round-trips | ✅ | crit-14 weight 1.5→1.6 → «Сохранить» → alert «Коэффициенты успешно сохранены!» → `POST api/score-coefficients` 200 → reload shows 1.6 → reverted to 1.5 → DB `criteria.weight = 1.50` |
| 3.5 | Matrix renders criterion-14 column, plausible numbers | ✅/⚠️ | 97 rows; column «Ответственность сверх роли» under «📋 ОБЩИЕ»; fixture cells exact (G 7/7·8/6·6/8·7; N project cells 7,8 present after reclass; P 8,7). ⚠️ header/body misalignment for non-project rows — **BUG-051** |
| 3.6 | Final scores render criterion 14 + numbers | ✅ | column «Ответственность сверх роли / вес: 1.5»; money to the digit: G Σ 70.20 × 0.60 = **42.12**; N Σ 129.58 × 1.10 = **142.54**; P Σ 121.30 × 2.20 = **266.86**; uniform 13-cell rows (shared column list — not affected by BUG-051) |
| 3.7 | Correction, applicable | ✅ | P × crit 8 cell → «Корректировка C-level» → «Добавить» → slider 9 → preview «Расчёт итоговой оценки: (8 + 9) / 2 = 8.5» → «Сохранить» → `POST api/admin/score-correction` 200 → modal shows «Изменить» + «Итоговая оценка» |
| 3.8 | Correction, inapplicable → readable Russian error | ✅ (after fix) | stale modal on N × crit 8, N reclassed to general in a second tab, save → **422** `{"error":"CRITERIA_NOT_APPLICABLE","message":"Критерий 8 — проектный, а сотрудник сейчас не участник проекта"}`. Before fix: hardcoded «Ошибка при сохранении корректировки» (readable, not raw JSON, but reason discarded — BUG-052). After fix: alert shows the server reason **verbatim** |
| 3.9 | Catalogue frozen after gate 2 | ✅ | banner «Сохранение и удаление критериев заморожены: оценка в текущем периоде уже идёт (409).» (prep-window banner «…каталог можно менять…» shown before gate 2); edit + «Сохранить» → `POST manage-criteria` **409** → alert «Нельзя менять критерии: оценка в периоде «H1-2026» уже идёт» |

## 5. Flow 4 — Error surfaces

| Surface | Result | Evidence |
|---|---|---|
| 409 already-scored | ✅ human | genuine stale-tab double self-review submit → XHR 409 → alert with the **server** message «Самооценка за этот период уже отправлена» |
| 422 applicability | ✅ human (after §6 fix) | «Критерий 8 — проектный, а сотрудник сейчас не участник проекта» in the correction modal alert |
| Period-not-started | ✅ human | the UI gates before the API can 409: full-page «Период оценки не открыт» (draft) / «Оценка ещё не началась» (preparation) on `/welcome`, `/self-review` |
| Catalogue freeze 409 | ✅ human | «Нельзя менять критерии: оценка в периоде «H1-2026» уже идёт» |
| Raw JSON anywhere | none seen | every failure above rendered as an alert/banner in Russian |

## 6. Fix made under the latitude (deployed)

**BUG-052** (closed): both correction routes swallowed the server's 409/422 reason into a
hardcoded alert. Two-line fix — `useEvaluationsMatrix.submitScoreCorrection` returns
`error.userMessage || …`, `ScoreDetailModal` alerts `error?.message || …`; the mid-level path
already threaded the message. Pinned by `tests/correctionErrorSurface.test.js`; re-proven in
the browser on the stand (§4 item 3.8). Suite **277/277**.

Deploy: gates run by hand (`rg` still absent locally — BUG-040): legacy `:5678` absent,
`/webhook` present. Release `20260824T131920Z` → `/var/www/epe/current` (previous release
retained). Live `https://epe.sedamedical.com` 200; chunks `ScoreDetailModal-DXrOwBnC.js` /
`AdminEvaluationsMatrix-DKXgalxg.js` carry the fixed patterns (verified by fetch).
`check_live_drift.py` before and after: 30 identical, 0 changed (the two
generator-outputs-absent-from-live are its long-standing baseline). Dated dump of live taken
this morning by the stand setup predates the deploy; no data was touched.

## 7. Defects

| Bug | Severity | State |
|---|---|---|
| **BUG-051** — admin matrix rows skip non-applicable project cells: non-project rows emit 8 `<td>` under a 10-column header, so «Как руководитель» N/A renders under «Проектные» and C-level scores would shift two columns. Final-scores screen unaffected (shared column list). | High | filed (behavioral — outside latitude) |
| **BUG-052** — correction refusals surfaced as a hardcoded alert | Medium | fixed + deployed, closed |
| **BUG-053** — seven world-readable (0644) dumps of live `epe_2026` from the 19–22 Aug briefs sitting in VPS `/tmp`, outside the backup regime | Medium | filed |

## 8. Riders

- `EVALUATION_METHODOLOGY.md` was **not attached** to the brief → skipped per the brief (not drafted).
- HANDOVER §10 counters reconciled to bugs.md: **23 open / 30 closed** after BUG-051/052/053.

## 9. Surfaced for decision

1. **BUG-051 (matrix misalignment)** — fix approach is mechanical (render rows against the
   header's column list with «—» placeholders, as final-scores already does), but it changes a
   reporting surface the calibration reads; wants its own small brief with a stand proof.
2. **BUG-053 (`/tmp` dumps)** — delete or move under `/root/backups/epe` with 0600. One
   command; they are prior sessions' rollback artifacts, so the executor did not remove them
   unilaterally.
3. **Post-submit dashboard staleness (observation, not filed)** — after an evaluation submit
   the subordinate card kept «Оценить» until a page reload in one instance; the driving here
   clicked the next card while the success panel was still open, which bypasses the refresh
   path, so this may be an artifact of automation rather than a defect. If a human reports the
   same, it reproduces as: submit → immediately open the next card without closing the panel.
4. **Drift-check baseline** — `check_live_drift.py` reports `API: Get Admin Data Fixed` and
   `API: Get Employee Self Review` as generator outputs absent from live and still says OK.
   That tolerance predates this brief; worth an explicit decision on whether those two should
   exist on live (both stayed importable and worked on the stand).

## 10. Acceptance

- Flow-by-flow checklist with per-item evidence: §§2–5 (DOM assertions and dialog texts
  recorded verbatim; browser network log for item 1 including the captured request payload).
- Browser/network evidence for flow 1: §2 items 1.6–1.7.
- Defects filed with severities: §7 (bugs.md updated, statistics 23/30).
- Suite green: **277/277** (`npm test`, includes the new `correctionErrorSurface.test.js`).
- Stand torn down; live campaign-inert (period writes happened only on `epe_walk_*`, which is
  dropped; live `epe_2026` untouched — H1-2026 remains `draft`).
- Committed and pushed with this report.
