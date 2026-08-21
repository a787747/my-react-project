# `work_category = 'tender'` — what it is wired to

**Date:** 2026-08-20  
**Method:** read-only. Live `epe_2026` + 2025 archive (`postgres.performance_db`) SELECT only; live `workflow_entity` for `API: Admin Save User (GUI Mode)` (`JCjzhRJtIDW0z8mI`, `updatedAt=2026-08-20 15:46:58.755+00`, active); deployed frontend `releases/20260820T165040Z`. No PUT, no deploy, no DB write, no mail.

**Verdict:** «Тендер» is a leftover UI option and an unused Postgres enum label. It is **not** a third classification. The live save API rejects it. Criteria 8 and 13 (bonus share) follow `is_project_participant`, which is true only for `work_category = 'project'`.

---

## 1. Accepted values

**Live DB (`epe_2026.performance_db.users.work_category`):** `varchar(50)`, nullable, default `'general'`. No CHECK, no FK, no trigger. Type `performance_db.work_category_type` exists (`general`, `project`, `hybrid`, `tender`) but the **column does not use it**. Same shape on the 2025 archive.

**Admin → Сотрудники UI** (`AdminUsers.jsx` composes these; options are not in the page file itself):

- Edit modal `UserModal.jsx`: `general` / `project` / `tender` (labels General / Project / Tender).
- Filter `UserFilters.jsx`: same three plus «Все категории».
- Excel import `UserImportModal.jsx`: `VALID_CATEGORIES = ['general', 'project', 'tender']`.
- Deployed `admin-CBzowXpl.js` still ships those options.

**Live API `API: Admin Save User (GUI Mode)`**, node `Validate User Data`:

```js
const VALID_WORK_CATEGORIES = ['general', 'project'];
const workCategory = String(body.work_category || 'general').trim();
if (!VALID_WORK_CATEGORIES.includes(workCategory)) {
  return { json: { http_status: 422, body: { error: 'INVALID_WORK_CATEGORY', ... } } };
}
```

`tender` (and `hybrid`) → **422**. Import uses the same POST, so an Excel `tender` row also fails.

---

## 2. Live counts

| Source | general | project | tender | other |
|---|---:|---:|---:|---:|
| `epe_2026` users (89) | 46 | 43 | **0** | 0 |
| 2025 archive users (73), SELECT count only | 46 | 27 | **0** | 0 |

`epe_2026`: zero rows where `work_category = 'project'` disagrees with `is_project_participant`.

---

## 3. `is_project_participant` derivation

**Live save-user** (after the allow-list, so `tender` never reaches this line):

```js
const isProjectParticipant = workCategory === 'project';
```

Written atomically with `work_category` on INSERT/UPDATE. For `'tender'` the rule would be **false** — but the 422 fires first.

**Import script** `scripts/import_epe_2026.py` `project_values()`: department/title heuristic → `("project", True)` or `("general", False)`. It never emits `tender`.

---

## 4. Other branches

**No live workflow mentions the string `tender`.** Other routes only SELECT `work_category` as a display field (login, employees, admin-users-data, evaluation-details, evaluation-history). Submit-evaluation and submit-self-review do not read it. Matrix / all-evaluations / manager-subordinates-matrix key off `is_project_participant`, not `work_category`. `GET /api/criteria` returns the full catalogue with no user filter.

Frontend that actually branches:

| Place | What it does with `tender` |
|---|---|
| Manager form `filterCriteriaByEmployee` | Ignores `work_category`. Extra criteria 8/13 only if `is_project_participant`. |
| Self-review `useSelfReview.js` | Keeps a criterion when `target_audience === 'all'` **or** `=== work_category`. No live row has `target_audience = 'tender'`. |
| Profile `CriteriaOverview.jsx` | Same audience === category match. |
| Labels `getWorkCategoryLabel` | No Russian label; would show raw `tender`. |
| Criteria-admin `TARGET_AUDIENCES` | Offers «Тендерный отдел» as a *criterion* audience. Unused: live catalogue has no such row. |
| Score-calculator sort / `CalculationCard` | Would group a criterion with `target_audience === 'tender'` under «проектные». Dead: no such criterion. |

`docs/EVALUATION_METHODOLOGY.md` does not mention tender.

---

## 5. Net effect — manager form, tender non-manager, today’s catalogue

Live catalogue (8 active rows): 3/4/12 `all` + selfassesment; 8/13 `project_participants`; 2 `managers_only`; 1/10 `c_level_only`.

A tender-classified non-manager **cannot be saved**. If the flag were forced to `is_project_participant = false` (the derivation), the manager form is identical to **general**:

- **3 criteria:** 3, 4, 12.
- **Not** 8 or 13 (those need `is_project_participant`).
- **Not** 2 (`has_subordinates` is false).
- 1 and 10 only if the *evaluator* role is `c_level` (same as general). A line-manager evaluator does not see them.

Bonus-index share therefore matches a general non-manager (3 weights), not a project participant (5).

---

## Recommendation

Ignore «Тендер». Classify each of the 89 as **project** (criteria 8+13 on, larger bonus share) or **general** (off). Cost of picking Tender in the modal: save fails; the person stays as they were.
