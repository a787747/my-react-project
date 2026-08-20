# Cosmetic pre-launch — D2 / D4

**Date of work:** 2026-08-19 (local evening) / 2026-08-20  
**Origin:** `https://epe.sedamedical.com`  
**Scope:** frontend only. D2 (closed-period Activate) and D4 (Welcome bonus-index formula). No workflow, schema, data, throttle, or scoring change.

---

## Verdict

Both fixes are live. H1 was **not** activated. Annual 2025 has no Activate control. Welcome no longer shows the formula block. Previous release remains on disk for rollback.

---

## 1. What was verified before editing

Live GET `API: Manage Periods` already selects `status` (confirmed on the running n8n node `Build Periods Query`):

```
SELECT id, name, start_date, end_date, is_active, status, period_type, parent_period_id, …
```

Live rows: id=1 Annual 2025 `closed`/`false`; id=2 H1-2026 `draft`/`false`. The frontend was ignoring `status` and rendering **Активировать** for every `!is_active` row. No backend change was required. The stop condition in the brief did not apply.

Welcome.jsx still contained the whole «Итоговая оценка» card, including  
`Итоговая оценка = Σ (Оценка по критерию × Вес критерия × Коэффициент)`. Same component for every role — no employee-only gate. Removing the card removes it for employees and for admin.

---

## 2. Changes

### D2 — `src/pages/AdminPeriods.jsx`

**Mechanism: hide, not disable.** Matches the existing pattern (`{!period.is_active && (…button…)}` / `{period.is_active && (…badge…)}`). A closed period gets an empty actions cell. No new copy.

1. Render Activate only when `!period.is_active && period.status !== 'closed'`.
2. `handleActivate` returns immediately if the target is missing or `status === 'closed'`, so the POST cannot be fired from this screen even if the button were forced.

H1 (`draft`) still shows **Активировать**. Closed Annual 2025 does not.

Activate SQL on the server already refuses `status = 'closed'` (404 «Period not found or is already closed»). Unchanged; the UI now matches that rule.

### D4 — `src/pages/Welcome.jsx`

Removed the entire «Итоговая оценка» card (heading, explanatory paragraphs, formula box) and the unused `Calculator` import. No rewording. Neighbouring blocks («Дополнительные критерии», «Критерии оценки») left as they were.

Employee view was not walked (no test registration). Same file, no role branch around that card — gone for every signed-in user.

---

## 3. Deploy

Pipeline: `./scripts/deploy_epe_frontend.sh` (`npm ci`, `VITE_API_URL=/webhook npm run build`, refuse if legacy `:5678` remains or `/webhook` is absent).

| | Value |
|---|---|
| New release | **`20260819T181012Z`** |
| `current` | `releases/20260819T181012Z` |
| Previous release still on disk | **`20260819T120100Z`** (`index.html` present — rollback path intact) |
| Public `index.html` `Last-Modified` | Wed, 19 Aug 2026 18:10:19 GMT |
| New chunks observed | `Welcome-Cs7JXa32.js`, `AdminPeriods-Com2UHfb.js` |

Rollback remains the script’s `ln -sfn` of the previous `releases/…` if a later deploy fails, or a manual `ln -sfn releases/20260819T120100Z /var/www/epe/current`.

---

## 4. Browser re-check (admin, Alexander)

Login succeeded. **Активировать was not clicked.**

**Периоды** (`AdminPeriods-Com2UHfb.js`):

| Period | Status column | Coverage | Actions |
|---|---|---|---|
| H1-2026 | Неактивен | 87 / 89 | **Активировать** (one button on the page) |
| Annual 2025 | Неактивен | 0 / 0 | empty |

**Welcome** (`Welcome-Cs7JXa32.js`): after «Дополнительные критерии» the next heading is «Критерии оценки». No «Итоговая оценка», no «Формула расчета». `document.body.innerText` confirmed `hasFormula=false`.

First navigation after deploy still showed the old Welcome from the previous tab’s JS cache. A load of the new hashed chunk (`Welcome-Cs7JXa32.js`) showed the removed block. Anyone with a tab left open from before this release will see the old formula until they refresh.

No error overlay and no 401 text on the two pages. A captured console stream was not kept (Console.enable was attached after the pages had already loaded).

---

## 5. End state

| Check | Value |
|---|---|
| H1 id=2 | `draft`, `is_active=false` |
| Annual 2025 id=1 | `closed`, `is_active=false` |
| users / registered | 89 / **1** (`alexander@sedamedical.com`) |
| evaluations / scores | **0** / **0** |
| workflows | **25 / 60** |
| 2025 fingerprint | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e` — **unchanged** |

n8n public SHA before ≠ after. Workflow count, active set, and `workflow_history` (73) unchanged. `execution_entity` stayed 111. `insights_raw` 220 → 270 — n8n insights from this admin login and the periods GET. Not a workflow edit.

---

## 6. Surface for decision

None that blocked the work. `status` was already on the periods payload.

Observation only: a closed period now has a blank actions cell, not a «Закрыт» badge. That was the hide choice so no new copy was invented. If a label is wanted, that is a later wording decision.
