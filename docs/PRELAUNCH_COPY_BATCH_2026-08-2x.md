# Prelaunch copy batch — 2026-08-24

Frontend-only. Closes BUG-034 / 035 / 036 / 037. Launch stays paused. H1 (id 2) stayed `draft` / `is_active=false` / `evaluation_started_at` NULL. No workflow PUT, no DB write, no mail, no stand. `useFinalScoresMatrix` and `useScoreCalculation` were not opened.

**Checked this session:** live `epe_2026` SELECT (periods, four data tables, criterion-14 levels, HR 52/80); live `workflow_entity` Prepare Guard Input nodes; `docs/HANDOVER.md` §3; bugs.md rows 034–037 and their source reports; the listed source files; `npm test` before and after; deploy via `./scripts/deploy_epe_frontend.sh` plus the two gates by hand; HTTPS origin + served chunks.

---

## 1. BUG-036 row 7 — button removed

`src/components/self-review/SelfReviewStatusCard.jsx`: the mid-period branch (`hasReview && newCriteriaCount > 0`) is gone. `if (hasReview)` now always renders the completed card. `onStartReview` is only wired to «Начать самооценку». `is_update` was not implemented. No workflow change.

Component diff (the deleted branch):

```jsx
// REMOVED
if (hasReview && newCriteriaCount > 0) {
  return (
    … «🆕 Появились новые критерии оценки» …
    <button onClick={onStartReview}>Оценить новые критерии</button>
  );
}
```

Search after the change (`src/`, this session):

| Path | Hit | Route? |
|---|---|---|
| `SelfReviewStatusCard.jsx` | none | — |
| `SelfReview.jsx` | none (still passes `isUpdate={hasReview}` / `newCriteria`, but nothing opens the modal once `hasReview` is true) | dead props, not a control |
| `EvaluationModal.jsx:616` | «Оценить новые критерии» | **manager additive path** (D-0822-3). Legitimate. Left in place. |

Served `SelfReview-BGHvbXQm.js`: string absent.

---

## 2. BUG-036 rows 2, 3, 8, 9, 10 — five strings

### Visibility sentence (row 2) — `Welcome.jsx`, both tracks + the purple subordinate box

**Old** (anonymity boxes, twice):

> Оценка вашего менеджера остается анонимной - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.

**Old** (purple box, manager track):

> Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.

**New** (anonymity boxes, twice):

> Оценка вашего руководителя остаётся анонимной для него: он не видит ваши баллы и комментарии. Кто что видит: руководитель видит самооценку своего подчинённого; полученные человеком оценки видят тот, кто его оценил, администратор и C-level; HR видит статусы выполнения, не баллы; сотрудник видит только свою самооценку — остальные результаты откроются отдельным решением.

**New** (purple box):

> Полученные оценки видят тот, кто оценил, администратор и C-level. HR видит статусы выполнения, не баллы. Сам руководитель эти оценки не видит.

Clause → HANDOVER §3 / deciding row / enforcing route:

| Clause | Backing | Route |
|---|---|---|
| Руководитель видит самооценку подчинённого | §3 «The manager form serves the subordinate's real self-review»; D-0820-16 | `GET /api/check-self-review` (`API: Check Self Review`) honours `user_id` when actor, direct report, or `admin`/`c_level` |
| Полученные оценки видят оценивший, admin и C-level | §3 subject-side visibility; D-0820-17 | `GET /api/evaluation-details` (`API: Get Evaluation Details FIXED`) returns a row only to the evaluator, `admin`/`c_level`, or the subject of their **own** self-evaluation |
| HR видит статусы выполнения, не баллы | §3 / D-0820-11; HR is not privileged on details | `GET /api/hr/evaluation-status` (`hr`/`admin`/`c_level`) — flags only, scores stripped; evaluation-details does **not** admit `hr` |
| Сотрудник видит только свою самооценку | §3; D-0820-17 | `GET /api/my-profile` (`API: My Profile V5`) attaches `score`/`calculated_score`/`weighted_score` only to self rows |
| Остальные результаты — отдельным решением | §3; D-0820-17; BUG-025 still open as the release mechanism | **no release route exists** — the sentence states the absence, it does not invent one |
| Оценка руководителя анонимна для него (баллы/комментарии) | §3 «Upward evaluator identity is nulled to the subject» | same details route: the rated manager is the subject of an upward row, not the evaluator → 404; identity nulled |

No clause was left without an enforcing route or an explicit «no route / later decision» (the release clause).

### Criterion title (row 3) — `Welcome.jsx` (heading + quoted name, twice)

| Old | New |
|---|---|
| `Критерий для оценки руководителя` | `Качество управления и развитие команды` (live `criteria.id=2`) |

### C-level / read-only trio notice (row 8) — `ManagerEvaluation.jsx`

| Actor | Old | New |
|---|---|---|
| `role` `c_level` or `admin` (includes ids 21 / 40 / 61) | «Руководитель не назначен» / «Обратитесь к HR-отделу…» | «Оценка руководителя не предусмотрена» / «Для руководителей C-level и администратора оценка непосредственного руководителя в этой программе не проводится: руководитель вам не назначается.» |
| anyone else without a manager | unchanged | unchanged |

### Draft notice (row 9) — `SessionExpiryWarning.jsx`

| Old | New |
|---|---|
| незавершённая оценка сохранится локально. | незавершённая оценка сохранится в этом браузере и истечёт через 7 дней. |

Backed by `epe:evaluation-draft:{evaluator}:{subject}`, 7-day expiry, D-0820-15.

### Login placeholder (row 10) — `Login.jsx`

| Old | New |
|---|---|
| `name@company.com` | `name@sedamedical.com` |

Matches `Register.jsx` (`endsWith('@sedamedical.com')`).

---

## 3. BUG-035 — 401 / 403 / 429 pass the server message

`src/utils/errorHandler.js`: 401, 403 and 429 now return `serverMessage || <fixed Russian fallback>`, same pattern as 400/404/409/422.

401 session-expiry / redirect **unchanged** (`src/api/client.js`): `isAuthError` is still `status === 401`; interceptor still removes `user` and `token` only, redirects to `/login` when not already there, does not sweep draft keys. Pinned in `tests/prelaunchCopyBatch.test.js`.

---

## 4. BUG-037 — «Создать период» behind `canManage`

`src/pages/AdminPeriods.jsx` header button wrapped in `{canManage && (…)}`, same `isAdmin(user?.role)` as rename / reparent / activate / close. Pinned in `tests/moneyScreenGuards.test.js` and `tests/prelaunchCopyBatch.test.js`.

---

## 5. BUG-034 — circles removed, not loaded

**Which:** the evaluation-status column on Admin → Сотрудники is **removed** (`UserTable` `showEvaluationStatus={false}`; the `setLoadingStatuses` effect and the three detail modals that only opened from the circles are gone).

**Why:** no admin-allowed route returns the subject-centric metrics the column claimed to show (self score, received-from-manager, received-from-subordinates).

| Candidate | Admin allowed? | What it actually answers |
|---|---|---|
| `GET /api/check-self-review` | yes (any session; `user_id` gated) | **one** subject — the actor, a direct report, or any subject for admin/c_level. Not a map. The page called it with no `user_id` and treated the body as `{[userId]: …}`. |
| `GET /api/hr/evaluation-status` | yes (`hr`/`admin`/`c_level`) | evaluator-task flags (`has_self_review`, `evaluated_manager`, `evaluated_subordinates`) on the **active** period. Field names are not `was_evaluated_by_manager` / `subordinate_evaluations_received`. Scores stripped. Empty while H1 is draft. |
| `GET /api/employee-self-review` | — | workflow **deleted** (HANDOVER §2). |
| `GET /api/employees` | any session | campaign flags, **active AND started**. Wrong questions (`evaluated_by_actor` = «did I evaluate them»). Empty while paused. |

Declaring the missing `useState` and keeping empty grey circles would have kept the original user-facing lie («nobody has done anything»). So the column went.

Remaining (surfaced): `TeamView.jsx` still calls undeclared `setLoadingSelfReviews` — same class, `/team`, BUG-012 territory. Not this brief.

---

## 6. Tests

| | Count |
|---|---|
| `npm test` before | **284 / 284** |
| `npm test` after | **295 / 295** |

+11 in `tests/prelaunchCopyBatch.test.js` (401/403/429 pass-through + fallback; 401 interceptor unchanged; button gone; visibility clauses; criterion title; C-level notice; draft 7-day; login placeholder; create gated; AdminUsers no `setLoadingStatuses`). One extra assertion on the existing periods-gate test in `tests/moneyScreenGuards.test.js`.

---

## 7. Deploy

`rg` **was** on PATH in this session (Cursor-bundled ripgrep 15.1.0). The two gates were still run by hand on `dist/` after the script's build:

```
GATE1 OK: legacy :5678 absent
GATE2 OK: /webhook present
```

Release **`20260824T175642Z`** → `/var/www/epe/current`. Previous **`20260824T145133Z` retained** on disk (20 releases). Public `index.html` `Last-Modified` Mon, 24 Aug 2026 17:56:48 GMT.

Chunk md5 local build = live disk = served origin:

| Chunk | md5 |
|---|---|
| `Welcome-DkTds-bF.js` | `4c223bd94cd4fe23f1430bd399f76f02` |
| `SelfReview-BGHvbXQm.js` | `6cf06d11f6a1f5328143202e9175dd71` |
| `ManagerEvaluation-BlbzVPvh.js` | `1e23ee7275451d6f9afa8d4034ab320c` |
| `AdminPeriods-CUAqBzPS.js` | `511126cba4f43592e273ce917c053856` |
| `AdminUsers-BQ_XmRUe.js` | `17b967868d9ee28b1327dbe6fcc68a2a` |
| `index-BqZ_U8Sp.js` (login placeholder + draft notice + 401 client) | `12a66f50b932014d348f667c10cbfffa` |

Served HTTPS (`https://epe.sedamedical.com/assets/…`): visibility sentence present; fake criterion title absent from Welcome; SelfReview button absent; «Оценка руководителя не предусмотрена» present; `name@sedamedical.com` present; «истечёт через 7 дней» present; `setLoadingStatuses` absent from AdminUsers.

Live campaign after deploy (SELECT 2026-08-24 17:57:33Z): H1 id 2 `draft` / `is_active=false` / `evaluation_started_at` NULL on all three; `evaluations` 0, `evaluation_scores` 0, `score_corrections` 0, `period_results` 0.

---

## 8. Riders

### D-0824-2 amendment

Appended to `DECISIONS.md` **verbatim**. The owner restores the approved criterion-14 curve himself.

### HANDOVER §7 steps 1 and 3

Both now name the runbook comparison: nine weights, 90 level coefficients, nine grade coefficients vs the approved tables (CRITERION9 appendix for criterion 14, RECON 2026-08-22 appendix for the rest, DECISIONS; the methodology once committed) — before «Запустить оценку» and before close.

### Criterion 14 levels (read-only, session end 17:57:33Z)

Live: `0.70/1.00/1.00/1.10/1.20/1.50/2.00/3.00/5.00/7.00`.

Approved: `0.20/0.25/0.30/0.35/0.50/0.70/1.00/2.00/3.60/6.00`.

**Not equal.** HANDOVER §3 live-curve note left in place. Coefficients were not written.

### HR ids 52 and 80 (`can_evaluate=true`)

Live: Liya Dmitriyeva (52) and Sona Rahmanova (80), both `hr`, `can_evaluate=true`, `can_be_evaluated=true`, `manager_id=47`, `has_subordinates=false`.

Every live `Prepare Guard Input` was read from `workflow_entity`. Routes whose **answer changes** because of that flag (vs `can_evaluate=false`):

| Route | Guard | Change |
|---|---|---|
| `POST /api/submit-evaluation` | `required_roles: []`, `required_capability: "can_evaluate"` | 403 `CAPABILITY_FORBIDDEN` → guard passes, then relation SQL. **Capability alone.** |
| `POST /api/update-evaluation` (POST path) | same | same. **Capability alone.** |

`POST /api/admin/score-correction` has `required_roles: ["admin","c_level","manager"]` **and** `can_evaluate` — HR is `ROLE_FORBIDDEN` either way. `POST /api/self-review-submit` admits `hr` with no capability — unchanged by the flag. Every other live route has `required_capability: ""`.

Expected «none beyond role gates» is **false** for those two write routes. Surfaced, not fixed (BUG-038). Both HR have no subordinates, so a manager-source submit would still fail the relation check; the guard answer has already changed.

### `assessment.sedamedical.com`

Resolves: **A `216.250.12.243`**. PTR empty. TCP 80 / 443 / 8080: connection refused. Does **not** serve EPE (`epe.sedamedical.com` is `92.51.45.147`). Recorded in the September table with that finding.

---

## 9. Surfaced, not resolved

1. Criterion 14 live level curve ≠ approved curve (owner restores it; runbook step added).
2. `POST /api/submit-evaluation` and `POST /api/update-evaluation` key on `required_capability` with empty `required_roles` (BUG-038). HR 52/80 therefore pass those guards.
3. `TeamView.jsx` still calls undeclared `setLoadingSelfReviews` (circles on `/team`).
4. `CriteriaOverview.jsx` still quotes «Критерий для оценки руководителя» — not one of the five strings.
5. No batch admin-allowed route exists that could honestly refill the AdminUsers circles; building one is a workflow change.

---

## 10. Files to re-upload (md5)

No workflow file. Frontend already switched.

| File | md5 | Where |
|---|---|---|
| `Welcome-DkTds-bF.js` | `4c223bd94cd4fe23f1430bd399f76f02` | live `releases/20260824T175642Z/assets/` |
| `SelfReview-BGHvbXQm.js` | `6cf06d11f6a1f5328143202e9175dd71` | same |
| `ManagerEvaluation-BlbzVPvh.js` | `1e23ee7275451d6f9afa8d4034ab320c` | same |
| `AdminPeriods-CUAqBzPS.js` | `511126cba4f43592e273ce917c053856` | same |
| `AdminUsers-BQ_XmRUe.js` | `17b967868d9ee28b1327dbe6fcc68a2a` | same |
| `index-BqZ_U8Sp.js` | `12a66f50b932014d348f667c10cbfffa` | same |
