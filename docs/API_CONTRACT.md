# API CONTRACT — EPE frontend → n8n

Captured: 2026-08-12.  
This is the specification a replacement backend must satisfy. Endpoints were **not** called (EPE workflows are deactivated). Shapes come from:

1. The **live production bundle** `http://135.232.120.40:8080/assets/index-C9WM9w28.js` (object `za`, interceptors).
2. Current repo `src/config/api.js`, `src/api/client.js`, pages/hooks that issue the calls.
3. Repo `n8n_workflows/API_*.json` (webhook method/path and Code-node `return { json: … }`).

Where the client is sloppy about wrapping (`data` vs raw array vs `[0].data`), the **n8n response** is the contract. The client already has fallbacks for several of those.

---

## 1. Base URL

| Where | Value |
|-------|--------|
| Live bundle | `http://92.51.45.147:5678/webhook` (compiled in; `VITE_API_URL` not present) |
| Source default | `import.meta.env.VITE_API_URL \|\| 'http://92.51.45.147:5678/webhook'` in `src/config/api.js` |
| Login duplicate | `http://92.51.45.147:5678/webhook/auth/login` hard-coded in `Login.jsx` and in the bundle |

All paths below are appended to that base. Example: `POST /auth/login` → `http://92.51.45.147:5678/webhook/auth/login`.

n8n webhook `httpMethod` defaults to **GET** when omitted in the export.

---

## 2. Transport conventions the client actually uses

| Rule | Detail |
|------|--------|
| Client | axios instance `apiClient`, `timeout: 30000`, `Content-Type: application/json` |
| Absolute URLs | `API_ENDPOINTS.*` are full URLs; axios `baseURL` is the same origin |
| Auth header | If `localStorage.token` is set: `Authorization: Bearer <token>`. Login does **not** send it. n8n does **not** read it. |
| Token value | `'fake-jwt-' + user.id` from login. Not a JWT. |
| CORS | Browser origin is `http://135.232.120.40:8080`. Most workflows set `Access-Control-Allow-Origin: *` and/or an OPTIONS webhook. A replacement must allow that origin (or `*`) for GET/POST/OPTIONS and header `Authorization`. |
| Errors | Client treats HTTP 401 as logout. Login uses 401 for bad password. Other failures are generic. |
| IDs | integers. Criteria keys in `grades` / `comments` objects are **stringified criteria ids**. |
| Scores | 1–10 in current UI (`UI_CONFIG.MAX_SCORE`). Some n8n checks still say 0–10. |

---

## 3. Auth and identity (read this first)

Login is the only call that establishes a session, and it is entirely client-side after the response:

```json
{ "success": true, "user": { /* users row minus password_hash, plus has_manager_subordinates */ }, "token": "fake-jwt-<id>" }
```

Failure: `{ "success": false, "message": "Пользователь не найден" | "Неверный пароль" }` with HTTP 401.

`user` fields the UI relies on: `id`, `full_name`, `email`, `role` (`admin` \| `c_level` \| `hr` \| `manager` \| `employee`), `job_title`, `work_category`, `has_subordinates`, `has_manager_subordinates`, `manager_id`, `grade_id`, `department_id`, `grade_coefficient` (used in self-review weighting; may come later from other calls).

Privileged operations send `user.id` / `evaluator_id` / `admin_id` in query or body. **A replacement that does not add real auth will behave like n8n. A replacement that is supposed to be safe must ignore those fields and use a server session.**

---

## 4. Endpoint table

Query parameters are shown as `?k=`. JSON bodies are request bodies. Response is the n8n Code-node payload unless noted.

| Path | Method | Request | Response | Client call sites |
|------|--------|---------|----------|-------------------|
| `/auth/login` | POST | `{ email, password }` | **200** `{ success: true, user, token }` · **401** `{ success: false, message }` | `Login.jsx` (raw axios, not `apiClient`) |
| `/api/verify-invite` | GET | `?token=` | `{ success, valid, message, data?: { token_id, expires_at } }` | `Register.jsx` |
| `/api/send-verification-code` | POST | `{ email, token }` | success `{ success: true, message, data: { email, full_name, expires_at } }` · fail `{ success: false, error_code: "email_not_found" \| "already_registered", message, data }` | `Register.jsx` |
| `/api/verify-code` | POST | `{ email, code }` | `{ success, verified, message, data: { email, attempts_remaining? } }` | `Register.jsx` |
| `/api/register` | POST | `{ token, email, password, verification_code }` | `{ success: true, message, data: { user_id, full_name, email, role } }` | `Register.jsx` |
| `/api/employees` | GET | `?user_id=` `&role=` | `{ success: true, data: Employee[] }` (client also accepts `response.data[0].data`) | `useDashboardData`, `EvaluationHistory`, `TaskStatusContext` |
| `/api/submit-evaluation` | POST | `{ evaluator_id, subject_id, final_score, grades: { [criteriaId]: number }, comments?: { [criteriaId]: string }, evaluation_source?: "manager" \| "subordinate" \| "c_level_direct" }` Default source in n8n: `"manager"`. | `{ success: true, message: "Evaluation saved successfully" }` | `EvaluationModal` (manager→employee), `useManagerEvaluation` (`evaluation_source: "subordinate"`), `useEvaluationsMatrix` (`"c_level_direct"`) |
| `/api/update-evaluation` | POST | `{ evaluation_id, evaluator_id, subject_id, final_score, grades, comments? }` | `{ status: "success", message: "Evaluation updated", evaluation_id, final_score, scores_saved }` | `EvaluationModal` edit mode |
| `/api/evaluation-details` | GET | `?evaluation_id=` | `{ status: "success", evaluation: EvaluationHeader, scores: ScoreRow[] }` or `{ status: "error", message: "Evaluation not found" }` | `useProfile`, `useEvaluationHistory`, `EvaluationModal` |
| `/api/evaluation-history` | GET | `?evaluator_id=` (n8n also accepts `user_id`) | `{ success: true, data: HistoryRow[] }` | `useEvaluationHistory` |
| `/api/check-evaluated` | GET | `?evaluator_id=` | `{ success: true, details: [{ subject_id, latest_evaluation_id, last_score, updated_at }] }` | `useDashboardData`, `Dashboard`, `TaskStatusContext` |
| `/api/criteria` | GET | none | `{ success: true, data: Criterion[] }` (client also accepts array / `[0].data`) | `useDashboardData`, `useSelfReview`, `useProfile`, `useManagerEvaluation`, `SelfReviewDetailsModal` |
| `/manage-criteria` | POST | `{ action: "get" }` · `{ action: "save", criteria: Criterion }` · `{ action: "delete", criteria: { id } }` | get: `{ data: Criterion[] }` · save/delete: `{ success: true, message: "Operation successful" }` | `useCriteria` (admin settings) |
| `/api/my-profile` | GET | `?user_id=` | `{ success: true, has_evaluations, evaluations: ProfileEval[], stats: { total_evaluations, average_score, latest_score, latest_period, latest_date } }` | `useProfile` |
| `/api/get-my-manager` | GET | `?user_id=` | `{ success: true, has_manager: false, manager: null }` or `{ success: true, has_manager: true, manager: Manager }` | `useManagerEvaluation`, `TaskStatusContext` |
| `/api/self-review-submit` | POST | `{ user_id, final_score, weighted_score?, grades, comments?, is_update? }` n8n uses `weighted_score \|\| final_score`; `is_update` is sent by the client and **not read** in the parse node. | `{ success: true }` | `useSelfReview` |
| `/api/check-self-review` | GET | `?user_id=` optional. Missing/invalid → n8n uses `user_id=0`. | `{ has_self_review, evaluation_id, score, date?, evaluated_criteria_ids, grades, comments }` (false branch: ids/score null, empty objects) | `useSelfReview`, `EvaluationModal`, `SelfReviewDetailsModal`, `TaskStatusContext` **with** `user_id`; `useDashboardData`, `TeamView`, `AdminUsers` **without** `user_id` (those sites read `.data` as a map — n8n does not return a map; they get `{}` via `?.data \|\| {}`) |
| `/api/employee-self-review` | GET | `?user_id=` (n8n) | `{ has_self_review, evaluation_id, total_score?, updated_at?, scores, comments }` | **In the client endpoint map. No call site in `src/`.** Still compiled into the live bundle. Implement it or the unused constant is harmless. |
| `/api/periods` | GET | none | `{ status: "success", data: Period[] }` (`SELECT *` from `evaluation_periods`) | `AdminPeriods` |
| `/api/periods/create` | POST | `{ name, start_date, end_date }` | `{ status: "success", message: "Period created", data: Period }` | `AdminPeriods` |
| `/api/periods/activate` | POST | `{ period_id }` | `{ status: "success", message: "Period activated", data: Period }` | `AdminPeriods` |
| `/api/admin/create-invite` | POST | `{ admin_id, frontend_url }` | `{ success: true, data: { id, token, registration_link, created_at, expires_at, is_new }, message }` | `AdminPeriods` |
| `/api/admin-users-data` | GET | none | `{ users: AdminUser[], options: { departments: [{id,name}], grades: [{id,code,coefficient}], managers: […] } }` | `useUsers`, `useScoreCoefficients`, `useScoreCalculation`, `useFinalScoresMatrix` |
| `/admin/save-user` | POST | `{ id?, full_name, email, job_title, role, work_category, department_id, grade_id, manager_id }` `id` absent/null → create | `{ success: true, user: <row> }` | `useUsers` (single + import loop) |
| `/api/admin/all-evaluations` | GET | none | `{ success: true, data: AllEvalEmployee[] }` | `useAllEvaluations` |
| `/api/admin/evaluation-details-by-user` | GET | `?user_id=` `&detail_type=` (`all` \| `self` \| `received_from_manager` \| `gave_to_manager` \| `gave_to_subordinates` \| `from_subordinates`) `&evaluation_id=` optional | `{ success: true, data: <varies by detail_type> }` | `useAllEvaluations`, `SubordinateEvaluationsModal` (`from_subordinates`), `ManagerEvaluationDetailsModal` |
| `/api/admin/evaluations-matrix` | GET | none | `{ success: true, data: MatrixEmployee[] }` | `useEvaluationsMatrix`, `useScoreCalculation`, `useFinalScoresMatrix` |
| `/api/admin/score-correction` | POST | `{ evaluator_id, subject_id, criteria_id, correction_score, correction_level?: "mid_level" \| "c_level" }` | `{ success: true, message, data: { id, subject_id, criteria_id, correction_score, correction_level } }` | `useEvaluationsMatrix`, `ManagerSubordinatesMatrix` |
| `/api/manager-subordinates-matrix` | GET | `?manager_id=` | `{ success: true, data: MatrixEmployee[] }` | `ManagerSubordinatesMatrix` |
| `/api/analytics` | GET | none | `{ success: true, data: { overall: { total_evaluations, company_avg_score, total_employees, active_evaluators }, departments: [], top_performers: [], low_performers: [], period_trends: [] } }` | `Analytics.jsx` |
| `/api/hr/evaluation-status` | GET | none | `{ success: true, employees: HrEmployee[], total }` | `useHRDashboard`, `useDashboardData`, `TeamView`, `AdminUsers` |
| `/api/score-coefficients` | GET | none | `{ success: true, data: [{ id, title, weight, is_active, score_coefficients: { "1": number, …, "10": number } }] }` | `useScoreCoefficients`, `useSelfReview`, `useScoreCalculation`, `useFinalScoresMatrix` |
| `/api/score-coefficients` | POST | `{ criteria: [{ id, weight, score_coefficients }] }` | `{ success: true, message: "Score coefficients saved successfully" }` | `useScoreCoefficients` |
| `/update-admin-data` | POST | `{ grades: [{ id, coefficient }] }` | `{ success: true, message: "Данные успешно обновлены", updatedCount }` | `useScoreCoefficients` |
| `/api/admin/clear-test-evaluations` | POST | empty body | `{ success: true, message, deleted_count, deleted_evaluations, deleted_corrections }` | `AdminSettings` |

OPTIONS: several workflows also expose OPTIONS on the same path (clear-test-evaluations, update-evaluation, manager-subordinates-matrix) plus `API: Global CORS Handler` on `OPTIONS /admin/*`. A replacement should answer OPTIONS 204/200 with CORS headers for every path above.

---

## 5. Nested types (fields the UI reads)

### Employee (from `/api/employees`)

`id`, `full_name`, `email`, `job_title`, `work_category`, `is_project_participant`, `manager_id`, `has_subordinates`, `department_name`, `grade_code`, `grade_coefficient`

### AdminUser (from `/api/admin-users-data`)

`id`, `full_name`, `email`, `role`, `work_category`, `job_title`, `manager_id`, `department_id`, `grade_id`, `has_subordinates`, `department_name`, `grade_name`, `manager_name`, `self_review_done`, plus manager-evaluation status column from that SQL (name **unverified** beyond the SELECT fragment `status` of the manager evaluation).

### Criterion (GET `/api/criteria` and POST `/manage-criteria` save)

UI form: `id?`, `title`, `description`, `target_audience` (`all` \| `project_participants` \| `project` \| `tender` \| `back_office` \| `managers_only`), `is_active`, `selfassesment`, `for_manager`, `c_level_only`, `level_0_desc` … `level_10_desc`, `weight`, `category`. GET-with-levels returns the level description columns. `useManagerEvaluation` filters `is_active && target_audience === 'managers_only'`.

### Manager (from `/api/get-my-manager`)

`id`, `full_name`, `email`, `job_title`, `role`, `has_subordinates`, `department_name`, `grade_code`, `grade_coefficient`, `has_evaluated_manager`, `last_evaluation_score`, `previous_scores[]`

### EvaluationHeader / ScoreRow (`/api/evaluation-details`)

Header: `evaluation_id`, `evaluation_date`, `final_score`, `status`, `general_comment`, `private_comment`, `subject_id`, `subject_name`, `job_title`, `work_category`, `evaluator_id`, `evaluator_name`, `grade_name`, `department_name`

Score: `id`, `criteria_id`, `criteria_title`, `criteria_description`, `criteria_category`, `score_value`, `comment`

### HistoryRow (`/api/evaluation-history`)

`id`, `final_score`, `evaluation_date`, `evaluation_source`, `evaluatee_name`, `job_title`, `work_category`, `department_name`, `grade_name`, `period_name`

### Period

`id`, `name`, `start_date`, `end_date`, `is_active` (and any other columns `SELECT *` returns)

### HrEmployee (`/api/hr/evaluation-status`)

Client reads: `role`, `has_self_review`, `manager_id`, `evaluated_manager`, `has_subordinates`, `total_subordinates`, `all_subordinates_evaluated`. SQL also joins self-review / manager / subordinate flags for the **active** period only.

### `grades` / `comments` maps

Object keyed by criteria id as string: `{ "12": 8, "15": 6 }`. Comments same keys, string values.

### `evaluation_source` values the client sends

| Value | Who |
|-------|-----|
| omitted / `"manager"` | manager evaluating a subordinate (`EvaluationModal`) |
| `"subordinate"` | employee evaluating their manager |
| `"c_level_direct"` | C-level cell in the admin matrix |

Self-review uses a **different** path (`/api/self-review-submit`), not this field.

### `detail_type` for `/api/admin/evaluation-details-by-user`

`all` \| `self` \| `received_from_manager` \| `gave_to_manager` \| `gave_to_subordinates` \| `from_subordinates`

`data` shape depends on type; the client assigns `response.data.data` to modal state. A replacement should keep the current n8n object (workflow `API: evaluation-details-by-user`).

### Matrix row

`/api/admin/evaluations-matrix` and `/api/manager-subordinates-matrix` return `data` as an array of employee objects with nested per-criterion scores including `manager_score`, `mid_level_correction`, `c_level_correction`. The UI averages those three when present (`ManagerSubordinatesMatrix.getFinalScore`). Exact column list is the SQL in `n8n_workflows/API_ evaluations-matrix.json` / `API_ Manager Subordinates Matrix.json`.

---

## 6. Present in n8n, not called by this client

| Path | Method | Notes |
|------|--------|-------|
| `/get-admin-data` | GET | Workflow `API: Get Admin Data Fixed`. Not in `za` / `api.js`. |
| `OPTIONS /admin/*` | OPTIONS | Global CORS helper. |

Do not require these for a frontend-compatible replacement unless something else still calls them.

---

## 7. Client map vs live bundle

The live `za` object and `src/config/api.js` list the **same 35 paths**. No extra URL appears in the minified bundle besides the login duplicate and library URLs.

`EMPLOYEE_SELF_REVIEW` (`/api/employee-self-review`) is in that map and in n8n; **no React call site**.

---

## 8. What a replacement must not break

1. Login JSON `{ success, user, token }` and HTTP 401 on failure — the login page does not use `apiClient` error handling.
2. Dual wrapping: several GETs are consumed as `data.data` **or** `data[0].data` **or** raw array. Returning `{ success: true, data: [...] }` matches n8n and the happy path.
3. `grades` as a map, not an array.
4. CORS from `http://135.232.120.40:8080` (and later HTTPS origins).
5. `/manage-criteria` and `/admin/save-user` and `/update-admin-data` **without** the `/api/` prefix — the client already special-cases those.
6. GET+POST on the same path `/api/score-coefficients`.
7. `check-self-review` without `user_id` must not 500 (n8n coerces to 0).

---

## 9. Auth finding (contract-level)

The shipped client **does** send `Authorization: Bearer fake-jwt-<id>` on `apiClient` calls. n8n webhooks **do not** consult it. Role gates are `localStorage.user.role`. A replacement backend that only mirrors n8n will stay unsafe; one that enforces auth can keep the same URLs and start honouring the header (today the token is not a real JWT — login would have to start issuing one).
