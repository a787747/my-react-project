# Admin → Сотрудники — column sorting

**Date of work:** 2026-08-20  
**Origin:** `https://epe.sedamedical.com/admin/users`  
**Scope:** frontend only. No n8n, schema, or data change. No new API.  
**H1:** not touched (still draft / inactive).

Rendered proof is Alexander’s own check on the live page immediately after this deploy. He is the sole user of this screen.

---

## Verdict

The employees table is sortable in the browser. Sort, filters, page, and scroll survive a pencil → save. Previous release **`20260820T154749Z`** is still on disk.

---

## 1. Sortable columns

Click the header label. First click = ascending, second click = descending. The active column shows a chevron (up / down); inactive sortable headers show a faint up-down arrow.

| Header | Field used | Notes |
|---|---|---|
| Сотрудник | `full_name` | |
| Рег. | `is_registered` | Badge already under the name. Asc = not registered first. |
| Роль | `role` | |
| Категория | `work_category` | `general` then `project` on asc. The classification column. |
| Отдел | `department_name` | Empty last-ish via empty string. |
| Грейд | `grade_name` | Stable alphanumeric (`Intl.Collator` numeric). A1, A2, A10, S1. |
| Менеджер | `manager_name` | Empty («Не назначен») first on asc. |

Equal values keep a stable order by `id`.

**Not sortable (as specified):** evaluation-status circles, pencil.

«Роль / Категория» and «Отдел / Грейд» stay one visual cell each; the two labels in the header are independent sort controls. TeamView uses the same table **without** `onSort` and still has the old static headers.

---

## 2. Composition with search and filters

Sort runs on the current «Найдено» set, after the existing search + four filters, before pagination.

- `filteredUsers.length` (the «Найдено» count) does not change when a header is clicked.
- Changing a filter or the search still resets to page 1 (unchanged).
- Changing sort also goes to page 1 of the new order (so «Категория» starts at the first general / first project row).
- «Сброс» clears filters **and** sort (back to API order).

No new request. Same `GET /webhook/admin-users-data`. The payload already had every sort key (`full_name`, `role`, `work_category`, `department_name`, `grade_name`, `manager_name`, `is_registered`). Backend change was not required.

---

## 3. View state after save

Three layers, all frontend:

1. **React state stays mounted.** Sort, filters, search, and page live in `useUserFilters`. Saving a row does not remount `AdminUsers`, so that state is not reset.
2. **Silent refetch.** `saveUser` still calls the existing `POST /webhook/admin/save-user`, then reloads the list with `fetchData({ silent: true })`. That updates `users` in place and **does not** flip `loading`. The previous path set `loading=true` and replaced the table with a full-page spinner — that was the scroll jump.
3. **Scroll restore.** `handleSave` records `window.scrollY` before the request and restores it after the modal closes (double `requestAnimationFrame`, after body `overflow` is unlocked).

The edit modal and its payload are unchanged. Only the post-save reload and the scroll restore were touched.

A save that changes the sorted field (e.g. category general → project while sorted by Категория) will move that row in the list. That is the new data, not a reset.

---

## 4. Deploy

`./scripts/deploy_epe_frontend.sh` (`npm ci`, `VITE_API_URL=/webhook npm run build`, refuse if legacy `:5678` remains or `/webhook` is absent).

| | Value |
|---|---|
| New release | **`20260820T165040Z`** |
| `current` | `releases/20260820T165040Z` |
| Previous release still on disk | **`20260820T154749Z`** (`index.html` present) |
| Public `index.html` `Last-Modified` | Thu, 20 Aug 2026 16:50:49 GMT |
| New chunks | `AdminUsers-BetntHnc.js`, `useUserFilters-juZdxBWU.js`, `admin-CBzowXpl.js` |

Rollback: `ln -sfn releases/20260820T154749Z /var/www/epe/current`.

`npm test` 192/192 (was 182; +10 in `tests/userSort.test.js`). `npm run build` clean.

---

## 5. Files

- `src/utils/userSort.js` — pure comparator
- `src/hooks/useUserFilters.js` — sort between filter and page
- `src/hooks/useUsers.js` — silent reload after save
- `src/components/admin/UserTable.jsx` — header controls when `onSort` is passed
- `src/pages/AdminUsers.jsx` — wires sort + scroll restore
- `tests/userSort.test.js`

---

## 6. Leftover (not in this brief)

`AdminUsers.jsx` still calls `setLoadingStatuses` with no matching state. That path is an unhandled rejection when the list loads; evaluation circles stay empty. Classification does not use those circles. Not changed.
