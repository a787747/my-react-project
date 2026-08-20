# Pre-launch fixes — server-side visibility & user-facing correctness

**Date of work:** 2026-08-20  
**Origin of proof:** isolated n8n `epe-prelaunch-n8n` on `127.0.0.1:25679` against throwaway DB `epe_prelaunch_20260820_1328` (restored copy of `epe_2026` + seed `scripts/seed_prelaunch_throwaway.sql`). Live `epe_2026` was not written.  
**Frontend release:** `20260820T154749Z` (`/var/www/epe/current` → `releases/20260820T154749Z`). Previous stamp `20260820T065435Z` remains on disk.  
**H1:** live period id=2 stays `draft` / `is_active=false`. Nothing was activated.

---

## Verdict

The seven items are live. H1 can be activated after Alexander’s shortened pre-flight. 2025 archive fingerprint is unchanged. Mail was not sent.

---

## `/api/employees` scope (correction 1)

Live SQL before this brief already filtered `WHERE users.manager_id = ${actorId}` for every authenticated role, including `admin` and `c_level`. The generator kept that predicate.

| Actor role | List returned | Flags | `grade_coefficient` |
|---|---|---|---|
| `employee` / `manager` | direct reports in the current active/draft period with `is_in_scope=true` | `has_self_review`, `has_evaluated_manager`, `evaluated_by_actor` (booleans only) | stripped |
| `admin` / `c_level` | the same direct-report predicate — **not** company-wide | same three flags | kept |

This is **not** a narrowing. Bayram/Jemal `c_level_direct` writes outside their own direct reports stay on the evaluations matrix (`API: Manager Subordinates Matrix` / admin matrix), which this brief did not shrink. Proof: c_level writer 1008 received `{1006, 1007}` (seeded `manager_id=1008`), not the manager’s 1002–1005 set.

Authorization rule implemented: any authenticated user may call `/api/employees`; the SQL binds the list to the JWT actor’s direct reports and the current period’s in-scope participants. `required_roles` / `required_capability` on the guard input are empty; identity is token-only.

---

## Regression source (item 7)

`API: Check Self Review` (`QRkUvs24DkcC3WBW`) started ignoring `user_id` in the **H1 Route Guard** rewrite of 2026-08-19 (`docs/ROUTE_GUARD_H1_2026-08-19.md` identity-bound proofs table: `check-self-review | employee 3 / user_id=88 | actor 3 self row`). The generator replaced the old query-parameter subject with `WHERE e.subject_id = ${actorId}`. There is no git commit of the pre-guard SQL — workflows were first tracked in `2375005` already in the actor-only form. Medium-confidence reconstruction of the older node: it read `user_id` from the query/body and used that as `subject_id` with no manager check.

Pattern to log: a token-only identity rewrite that drops a legitimate subject selector, then labels the actor’s own row as someone else’s.

This brief restores a **gated** selector: honor `user_id` when it is the actor, a direct report of the actor, or any subject for `admin`/`c_level`; otherwise fall back to the actor’s own row (no 403, no leak).

---

## What changed

### 1. Manager form serves the subordinate’s self-review

`scripts/build_route_guard_workflows.py` → `API: Check Self Review`. CTE `selected_subject` picks `requestedId` only if self / privileged / `target.manager_id = actorId`. SELECT now includes `e.general_comment`. Unauthorized `user_id` falls back to the actor.

Frontend: `EvaluationModal` loads `CHECK_SELF_REVIEWS?user_id={employee.id}`; missing self-review shows «Самооценка ещё не отправлена». `getSelfComment` reads per-criterion comments (it previously returned `general_comment` for every row).

### 2. Subject-side sealing

`API: My Profile V5`: non-self evaluation objects omit `score` / `calculated_score` / `weighted_score` / comments. Counts and fact-of-evaluation stay. Profile stats (`average_score`, `latest_*`) are computed from self-evaluations only, so the aggregate cannot leak a received score.

`API: Get Evaluation Details FIXED`: caller must be the evaluator, `admin`/`c_level`, or the subject of their own self-evaluation. HR is not privileged (D-0820-11). Anything else → 404 «Оценка не найдена или недоступна вам».

Result release at period close was not built.

### 3. Manager dashboard statuses

Completion flags live on the enriched `/api/employees` payload (see scope table). `useDashboardData` / `Dashboard` no longer call `/api/hr/evaluation-status`.

### 4. Criteria level texts

`API: Get Criteria With Levels` keeps titles and descriptions for everyone. `level_1_desc`…`level_10_desc` of `c_level_only` rows are deleted unless the actor is `admin`/`c_level`. Self-review and upward hooks already skip `c_level_only` criteria, so those forms still render ordinary level texts.

### 5. Out-of-scope users

`/api/employees` returns `actor_is_in_scope`. `TaskStatusContext` sets `isOutOfScope`. Welcome / SelfReview / ManagerEvaluation render `OutOfScopeNotice` with the exact copy. Sidebar hides «Самооценка», «Оценить руководителя», and the task panel. `NOT_IN_SCOPE` on submit routes remains as defense.

### 6. Small fixes

| Item | Change |
|---|---|
| (a) Russian 400/404/409/422 | Duplicate self-review/evaluation, invalid invite, invalid/expired reset, invalid registration, invalid code + remaining attempts, verify-invite throttle. No `/api/` paths in those strings. |
| (b) Self-review confirmation | «Напоминание: самооценка отправляется один раз и не подлежит изменению.» |
| (c) Score Correction | `required_capability='can_evaluate'` (D-0820-7). Read-only c_level → 403 `CAPABILITY_FORBIDDEN`. |
| (d) `grade_coefficient` | Stripped below `admin`/`c_level` on Get Employees and Get My Manager. |
| (e) Details modal | «Детальные результаты доступны руководству компании.» |

---

## Proof

Throwaway period 2 was set `active` **only on `epe_prelaunch_20260820_1328`**. Live H1 stayed draft.

API suite `scripts/prove_prelaunch_fixes.py` → `backups/2026-08-20-prelaunch-fixes/api_proof.json`. Static tests: `npm test` → 182 pass / 0 fail.

| Check | Result |
|---|---|
| Manager 1001 asks `user_id=1002` | score `8.00`, comments `САМООЦЕНКА ПОДЧИНЁННОГО — критерий 3/4/12` (not manager’s own `3.00` / `МОЯ САМООЦЕНКА`) |
| Foreign manager asks `user_id=1002` | fallback to actor’s own row |
| `user_id=1003` (no self-review) | `has_self_review=false` |
| Employees flags for 1001 | 1002 T/T/T; 1004 T/T/F; 1003 F/F/T; 1005 absent (out of scope) |
| Subject 1002 `my-profile` | received evals 2004 and 2010 have no scores/comments; self 2002 keeps `8.00`; stats average = 8 (self only) |
| Subject 1002 opens eval 2004 | 404 |
| Evaluator 1001 opens 2004 | 200, scores and comments present |
| Subject opens own self 2002 | 200 |
| Foreign evaluation_id 2009 as 1002 | 404 |
| Plain employee criteria ids 1 and 10 | title+description present, no `level_1_desc`…`level_10_desc` |
| Admin criteria ids 1 and 10 | level texts present |
| Read-only c_level correction | 403 |
| Duplicate self-review | 409 «Самооценка за этот период уже отправлена» |
| Duplicate evaluation | 409 «Такая оценка уже отправлена в текущем периоде» |
| Invalid invite | `valid: false`, «Ссылка-приглашение недействительна или срок её действия истёк» |
| Invite throttle | «Слишком много запросов. Повторите попытку через несколько минут.» |
| Invalid code | «Неверный код. Осталось попыток: 4.» |

Browser evidence (local vite `:5199` proxied at the throwaway API), saved under `backups/2026-08-20-prelaunch-fixes/`:

- `manager-dashboard-mixed-badges.png` — 1002 all three badges; 1004 self+upward without «оценен вами»
- `manager-modal-subordinate-self-review.png` / `manager-modal-subordinate-comments.png` — subject 1002, badge **Самооценка: 8.00**, per-criterion «САМООЦЕНКА ПОДЧИНЁННОГО»
- `manager-modal-self-review-missing.png` — subject 1003, «Самооценка ещё не отправлена»; level descriptions visible
- `out-of-scope-welcome.png`, `out-of-scope-self-review.png`, `out-of-scope-upward.png` — exact copy; no start-task CTA
- `subject-profile-sealed.png` / `subject-profile-manager-fact-only.png` — self 8.0/10; received manager eval is fact-only (H1-2026, Prelaunch Manager, no 7.00)
- `self-review-confirmation-reminder.png` — reminder sentence in the confirm dialog; form used non-c_level_only criteria with level texts

---

## §4.8 ten-row copy-vs-behavior (re-check)

| # | Where | Status | Notes |
|---|---|---|---|
| 1 | Welcome: upward stays anonymous / manager does not see scores | **closed** | `my-profile` no longer returns `calculated_score` on received/upward rows. Welcome sentence is now true for scores. |
| 2 | Welcome: «Все данные видят только C-level менеджеры» | **open** | Copy unchanged. Admin, HR (statuses), and `/team-scores` still see data. |
| 3 | Welcome: «Критерий для оценки руководителя» as if it were the name | **open** | Catalogue name remains `Качество управления и развитие команды`. Not in this brief. |
| 4 | Welcome: C-level criteria «доступным только для руководства» | **partially** | Level texts of `c_level_only` rows are no longer returned below admin/c_level. Titles and descriptions remain, matching `CriteriaOverview`. |
| 5 | EvaluationDetailsModal: «только администраторам» vs API leak | **closed** | Copy is now «Детальные результаты доступны руководству компании.» API no longer returns received details to the subject. |
| 6 | SelfReview: one-time vs «Оценить новые критерии» | **partially** | Confirmation dialog now carries the one-time reminder. The extra button is still on `SelfReviewStatusCard`. |
| 7 | `Оценить новые критерии` always 409 | **open** | `Submit Self Review` still ignores `is_update`. Not in this brief. |
| 8 | ManagerEvaluation: «Руководитель не назначен» for C-level without manager | **open** | Correct for Cem/Hemra/Mekan; copy unchanged. |
| 9 | SessionExpiryWarning: draft is local / 7-day | **open** | Copy still omits browser-local + expiry. |
| 10 | Login placeholder `name@company.com` vs `@sedamedical.com` | **open** | Unchanged. |

---

## Live PUT / deploy

`EPE: Auth Guard` `updatedAt=2026-08-18T16:34:30.674Z` before and after (sub-workflow, `active=false` as before). 33 workflows active / 58 total.

| Workflow | `updatedAt` after PUT |
|---|---|
| API: Get Employees (Smart Role Based) | 2026-08-20T15:46:09.140Z |
| API: Register | 2026-08-20T15:46:43.694Z |
| API: Reset Password | 2026-08-20T15:46:44.718Z |
| API: evaluation-details-by-user | 2026-08-20T15:46:45.763Z |
| API: Manage Criteria Admin V7 | 2026-08-20T15:46:46.775Z |
| API: Manager Subordinates Matrix | 2026-08-20T15:46:47.821Z |
| API: Score Correction | 2026-08-20T15:46:49.134Z |
| API: Update Admin Data | 2026-08-20T15:46:50.281Z |
| API: Check Self Review | 2026-08-20T15:46:51.305Z |
| API: Get Criteria With Levels | 2026-08-20T15:46:52.342Z |
| API: Get Evaluation Details FIXED | 2026-08-20T15:46:53.474Z |
| API: Get My Manager | 2026-08-20T15:46:54.483Z |
| API: Manage Periods | 2026-08-20T15:46:55.640Z |
| API: My Profile V5 (Fixed Empty) | 2026-08-20T15:46:56.673Z |
| API: Save Score Coefficients | 2026-08-20T15:46:57.706Z |
| API: Admin Save User (GUI Mode) | 2026-08-20T15:46:58.755Z |
| API: Submit Self Review | 2026-08-20T15:46:59.795Z |
| API: Submit Evaluation | 2026-08-20T15:47:00.848Z |
| API: Update Evaluation WITH PERIOD | 2026-08-20T15:47:01.891Z |
| API: Verify Code | 2026-08-20T15:47:39.678Z |
| API: Verify Invite | 2026-08-20T15:47:40.923Z |

Generator-driven siblings (manage-periods, save-user, save-score-coefficients, matrix, manage-criteria, evaluation-details-by-user, update-admin-data, submit/update evaluation) were PUT because they were regenerated with the same Russian-error pass. Activation state was preserved (`active=true` throughout).

Frontend: `./scripts/deploy_epe_frontend.sh` → **`20260820T154749Z`**. Bundle uses `/webhook`; no legacy `:5678`.

Live `epe_2026` after PUT (no writes from this brief): users=89, registered=2, evaluations=0, scores=0, corrections=0, sessions=4, H1 `draft,false`, invite id=4 unused. 2025 fingerprint `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e` unchanged. Registered=2 / sessions=4 were already on live before this PUT; they were not created here.

---

## Leftovers (not this brief)

- `errorHandler.js` still replaces 401/403/429 server messages. `CAPABILITY_FORBIDDEN` therefore reaches the user as «Доступ запрещен. Недостаточно прав» even though the workflow string is still English. In scope of (a) were 400/404/409/422.
- Sidebar task links can flash for one paint while `TaskStatusContext` loads `actor_is_in_scope`. After load they are hidden.
- §4.8 rows 2, 3, 7, 8, 9, 10 remain open.
- Throwaway n8n `epe-prelaunch-n8n` and DB `epe_prelaunch_20260820_1328` were used for proof; they are not production.

---

## Constraints held

- 2025 archive not written.
- No mail (D-0820-8).
- Live `epe_2026` evaluation rows not written.
- Auth Guard `updatedAt` frozen.
- H1 not activated.
