# Dress rehearsal — browser walkthrough of epe.sedamedical.com

**Date of work:** 2026-08-19 (local evening) / 2026-08-20  
**Origin walked:** `https://epe.sedamedical.com`  
**Period used:** H1 id=2, activated for the walkthrough, returned to `draft` / `is_active=false` at the end.

No workflow logic change. No scoring change. No schema change. The only file edit is the runbook wording in `docs/LAUNCH_RUNBOOK_H1.md` (`проект / полевые` → `general` / `project`).

Invite token, passwords, and email codes are not in this file.

---

## Verdict

**Ready for 31 Aug: yes.**

No functional launch blocker. Registration, employee writes, manager write, period binding (`period_id=2`), evaluator-from-token, 87/89 coverage, exclusion, and employee-cannot-open-admin all held in the browser or (where login was impossible) by API.

The required mid-form draft check **failed** for self-review and upward evaluation. Only the manager→subordinate modal persists a draft across refresh. That is a launch-experience decision, not a 31 Aug stop: those forms are short (1–3 sliders) and self-review already warns it is one-shot.

Surface the items in §8 before the company-wide mail goes out. The operational risk to keep in mind is the **Активировать** button still sitting on Annual Review 2025.

---

## 0. Baseline (before activation)

Checked live `epe_2026` and n8n `public` over SSH before any UI click.

| Check | Live |
|---|---|
| Users | 89 |
| Registered (`password_hash IS NOT NULL`) | 1 — `alexander@sedamedical.com` |
| Evaluations / scores / sessions / codes | 0 / 0 / 0 / 0 |
| H1 id=2 | `draft`, `is_active=false` |
| Participants period 2 | 87 in scope / 89 |
| Invite id=4 | unused, 43-char base64url, unexpired |
| Workflows | **25 active / 60** |

Dumps (restore-verified) in `backups/2026-08-20-dress-rehearsal/` (gitignored) and `/root/backups/epe/2026-08-20-dress-rehearsal/` on the host:

| Artefact | SHA-256 | Bytes | Restore |
|---|---|---|---|
| `epe_2026_before.dump` | `5a48c60690518a39e884b7f1728834863cbe821e151a9b236e0f54213830749d` | 73275 | users=89 evals=0 h1=`draft,false` |
| `n8n_public_before.dump` | `f9dcdafb92ab30206fd01f56594092a71c71b56aecddddca62b2fb2142b73c2b` | 464686 | workflows=60 active=25 |
| 2025 fingerprint before | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e` | — | unchanged vs known archive |

Accounts used (real people, not fixtures):

| id | Name | Email | Role | How registered this session |
|---|---|---|---|---|
| 2 | Alexander Petrosov | alexander@sedamedical.com | admin | already registered — not touched |
| 3 | Alina Naubatova | alina@sedamedical.com | employee | **browser** via invite id=4 |
| 1 | Akmyrat Jumahanov | akmyrat@sedamedical.com | manager | **API** via the same invite (browser login after) |
| 31 | Aysoltan Esenova | esenova@sedamedical.com | employee, excluded | unregistered; login 401 |
| 35 | Govher Balova | govher@sedamedical.com | employee, excluded | not login-tested |

---

## 1. Activate H1 (admin UI)

Logged in as Alexander. Admin → Периоды.

**Screen:** H1 showed **Неактивен**, coverage **87 / 89**, button **Активировать**. Annual Review 2025 (closed) also showed **Активировать** with coverage **0 / 0**.

Confirm dialog: «Активировать этот период? Текущий активный период будет деактивирован.»

After click: H1 **Активен** (green) + badge **Текущий период**. Coverage still **87 / 89**.

**DB after activate:** `evaluation_periods.id=2` → `status=active`, `is_active=true`.

«Получить ссылку» returned `https://epe.sedamedical.com/register?token=…` (43 characters). Invite id=4 remained `is_used=false`.

---

## 2. Registration via shared invite (browser, Alina)

Opened the invite URL in a clean session. Path `/register`.

**Screen, step 1:** email field, helper «Только @sedamedical.com». After send: greeting **«Здравствуйте, Alina Naubatova !»** (space before `!`).

Code was read from `email_verification_codes` (columns `is_verified`, `verified_at`, `attempts` — no `used_at`). After success the row was gone (`codes=0`).

**Screen, password:** strength meter reached **«Отличный»**. Submit auto-redirected to `/login`.

**After register:**

- `password_hash` set for id=3.
- Registered count = 2 (Alexander + Alina).
- Invite id=4 still `is_used=false` (reusable, as `SHARED_INVITE_2026-08-20`).
- Codes = 0.

Akmyrat was registered later by the same invite through curl (`send-verification-code` → DB code → `verify-code` → `register`) so the manager flow could be walked in the browser. Invite id=4 still unused after that second register. Register JSON returned `user_id: null` while the hash was written — see §7.

---

## 3. Employee flow (Alina, browser)

Login succeeded. Sidebar showed only **Личные** (no admin / analytics / HR).

### 3.1 Welcome / tasks

Welcome showed a self-review task. After that, `/self-review`.

### 3.2 Self-review

**Screen:** warning that the review can be submitted **ОДИН РАЗ**. Status card: **«Вам доступно 3 критериев для оценки.»** (grammar). Three general criteria. Button «Начать самооценку».

Filled 7 / 8 / 6 plus a comment on the first criterion. Confirmation modal **«Подтверждение самооценки»**. Submitted.

**Draft check — failed.** After filling sliders, before submit, `localStorage` held only `user` and `token`. Refresh returned the page to «Начать самооценку»; values were gone. Draft keys `epe:evaluation-draft:*` are written only by `EvaluationModal` (manager→subordinate). `SelfReviewModal` and the upward page do not persist.

**DB row created:**

```
evaluations.id=10
  subject_id=3  evaluator_id=3  source=self  period_id=2
  calculated_score=7.00  weighted_score=9.44
scores: criterion 3→7, 4→8, 12→6
```

**Screen after submit:** «✅ Вы уже оценили себя… Итоговая оценка: 7.00».

### 3.3 Upward evaluation

`/manager-evaluation` showed **Akmyrat Jumahanov**, grade **S4-M1** visible to the subordinate, criterion «Качество управления и развитие команды». Submitted **8**.

**Draft:** none. Same as self-review.

**DB row created:**

```
evaluations.id=11
  subject_id=1  evaluator_id=3  source=subordinate  period_id=2
  calculated_score=8.00
```

### 3.4 Employee dashboard / admin URL / console

Employee dashboard called only launch-set webhooks (all **active**): `check-self-review`, `get-my-manager`, `employees`, `my-profile`, `criteria`. No deferred (inactive) route was observed on the employee dashboard. No 401 loop.

`/admin/periods` as Alina redirected to `/` then `/welcome`. `App.jsx` sends `/` → `/welcome` for every signed-in user.

---

## 4. Manager flow (Akmyrat, browser)

Logged in as Akmyrat (registered via API, see §2).

**Screen `/dashboard` («Моя Команда»):** five names — Alina Naubatova, Asadbek Usmanov, Halykberdi Orusov, Muhammet Gylyjov, Shasenem Tishkina. **Esenova absent.**

Alina card showed **«Категория: general»** (raw English enum) and «Общие: 3».

Opened evaluate-Alina. Sliders 6 / 8 / 7. Draft key `epe:evaluation-draft:1:3` written.

**Draft check — passed on this form.** Refresh kept the key. Reopening the modal restored sliders **6, 8, 7**. Submit «Сохранить оценку». Draft cleared after submit.

**DB row created:**

```
evaluations.id=12
  subject_id=3  evaluator_id=1  source=manager  period_id=2
  calculated_score=7.00   -- mean of 6, 8, 7
scores: criterion 3→6, 4→8, 12→7
```

Evaluator is the token subject (id=1), not a client-supplied id. `period_id=2`.

---

## 5. HR / admin view

### 5.1 Evaluation status

`GET /webhook/api/hr/evaluation-status` as Alexander → **200**.

Quoted fields:

- `in_scope_count=87`
- `campaign_active=true`
- `total=84` (87 minus admin minus two HR)
- Esenova and Balova **absent**
- Alina: `has_self_review=true`, `evaluated_manager=true`
- Akmyrat: `evaluated_subordinates=1`, `total_subordinates=5`, `has_self_review=false`

`/hr/dashboard` as **admin** redirected to `/`. `isHR` is `role === 'hr'` only. Admin has no HR screen. Campaign progress for Alexander = employees badges + this API, not that page.

### 5.2 Admin → Сотрудники

89 users. Search «Alina» → **Найдено: 1**. `UserTable.jsx` renders «Зарегистрирован» / «Не зарегистрирован» when `user.is_registered != null`. A dedicated screenshot of the green badge after the filter landed was **not** captured (navigation left the page too early). Text + code evidence only.

Category filter options include **Tender**. Live `work_category` enum is `general` / `project` only.

### 5.3 Periods coverage with H1 active

Admin → Периоды, H1 active: **«В охвате 87 / 89»**. Matches `evaluation_period_participants` for period 2 (`is_in_scope` 87 / 89).

---

## 6. Negative checks

### 6.1 Excluded participant — no tasks

Esenova `password_hash` was NULL. Cannot log in. Browser login was not possible.

`POST /webhook/auth/login` as Esenova → **401** `{success:false, message:'Неверный email или пароль'}`. Generic; does not say «unregistered».

Exclusion proven without her session:

- Manager UI (Akmyrat): 5 names, Esenova not listed.
- HR status API: Esenova and Balova absent.

Balova was not login-tested (same unregistered state).

### 6.2 Employee cannot open admin screens

Alina → `/admin/periods` bounced to `/welcome`. Sidebar had no admin entries.

---

## 7. Every deviation (any severity)

| # | Severity | What | Where | Consequence |
|---|---|---|---|---|
| D1 | High (experience) | Self-review and upward forms have **no draft**. Refresh mid-form loses values. | `SelfReviewModal` / `ManagerEvaluation.jsx` vs `EvaluationModal` `epe:evaluation-draft:*` | Self-review is one-shot. An accidental refresh means starting over; if they already submitted, they cannot retry. |
| D2 | High (ops) | Annual Review 2025 still has **Активировать** next to H1. | Admin → Периоды | A mis-click activates the closed 2025 period. Runbook says do not touch it; the UI does not hide the button. |
| D3 | Medium (experience) | Welcome subtitle «Активный период оценки» was visible to Alexander **while H1 was still draft**. Admin also sees a self-review-shaped task card, yellow «1» on «Руководитель C-level», copy «C-level менеджеры не оцениваются» / sidebar «C-level не оценивается». | `Welcome.jsx`, `Sidebar.jsx` | Admin is exempt from self-review but the home page still talks like a campaign participant. |
| D4 | Medium (experience) | Welcome CTA / formula «Итоговая оценка = Σ (Оценка × Вес × Коэффициент)» shown to employees. | `Welcome.jsx` ~459 | That is bonus-index language. Employees will read it as «my rating». |
| D5 | Medium (experience) | Login «Зарегистрироваться» opens a modal: «Обратитесь к HR», link comes to work email. Already-registered register screen says email **hr@sedamedical.com** for reset. Login already has working «Забыли пароль?». | `Login.jsx`, `Register.jsx` | Plan is one company-wide mail from Alexander, not an HR ticket. People will write HR or hunt for a link that is already in their inbox. |
| D6 | Medium (experience) | Manager modal shows **«Категория: general»**. Upward page shows the manager **grade** (S4-M1) to the subordinate. | `EvaluationModal.jsx` L450; `ManagerEvaluation.jsx` | English enum and a grade the employee did not need. |
| D7 | Low | «Вам доступно **3 критериев**». Space before `!` in «Alina Naubatova !». Mix of «Evaluation Portal» / «Email» with Russian UI. | `SelfReviewStatusCard.jsx` L89; register greeting | Looks unfinished. |
| D8 | Low | Admin cannot open `/hr/dashboard`. | `App.jsx` / `isHR` | Alexander cannot watch campaign progress on that screen. API works. |
| D9 | Low | Category filter and user modal include **Tender**. | `UserFilters.jsx`, `UserModal.jsx` | Filter that matches nobody / implies a third category that does not exist. |
| D10 | Low | `API: Register` returned `user_id: null` for Akmyrat while `password_hash` was written. | Register response | Harmless if the UI only cares about success + redirect. Misleading if anyone logs the payload. |
| D11 | Info | n8n public dump SHA changed (see §9). Workflow count, active set, and `workflow_history` row count did not. | `execution_entity` 106→111, `insights_raw` 0→220 | Operational n8n telemetry from this rehearsal, not a logic change. |
| D12 | Info | `epe_2026` dump SHA changed after cleanup because sequences advanced (`evaluations_id_seq` last_value=12, `evaluation_scores_id_seq`=43) even though rows were deleted. | sequences | Next live evaluation will be id=13. No leftover score or evaluation rows. |

No console 401 loop. No deferred-route breakage on the employee dashboard. No write landed on the wrong period or the wrong evaluator.

---

## 8. Surface for decision (do not treat as already decided)

These are things a non-technical employee will hit. They are not code defects to silently patch in this brief.

1. **Tell people not to refresh mid-self-review**, or accept that a later brief adds drafts to self-review and upward. Today only the manager form remembers sliders.
2. **Who do people write when stuck?** The login modal says HR; the register-already-exists screen says `hr@sedamedical.com`; the real plan is Alexander’s company-wide mail plus «Забыли пароль?». Pick one sentence for the 26 Aug email.
3. **Hide or disable Активировать on Annual 2025** before 31 Aug, or accept that only Alexander clicks periods and the runbook is enough.
4. **Show «Категория: general» to managers?** Replace with a Russian label, or leave the enum.
5. **Show the manager’s grade to the subordinate** on the upward page?
6. **Show the bonus-index formula on Welcome** to every employee?
7. **Admin home page** talking about self-review / C-level-not-evaluated — leave it, or send admin straight to Периоды.

Recommendation: for 31 Aug, keep the system as walked. Put in the company mail: the link is in that email (do not ask HR for a second one); self-review is once, finish it without closing the tab; password reset is on the login screen. Treat D2 (2025 Activate) as the one ops reminder on the day you activate H1 for real.

---

## 9. Cleanup proof

Deleted rehearsal artefacts only. Alexander’s `password_hash` left in place. Invite id=4 left unused. 2025 archive (`postgres.performance_db`) not written.

```
DELETE evaluations WHERE period_id=2;          -- 3 rows (ids 10, 11, 12); scores CASCADE
UPDATE users SET password_hash=NULL WHERE id IN (1,3);
DELETE auth_sessions;                          -- 4 rows
DELETE email_verification_codes;               -- 0 leftover
DELETE auth_login_attempts;                    -- 2 (Esenova probe)
UPDATE evaluation_periods SET status='draft', is_active=false WHERE id=2;
```

**Live end state (queried after COMMIT):**

| Check | Value |
|---|---|
| users | 89 |
| registered | **1** — `alexander@sedamedical.com` |
| evaluations | **0** |
| evaluation_scores | **0** |
| score_corrections | 0 |
| auth_sessions | **0** |
| email_verification_codes | **0** |
| auth_login_attempts | **0** |
| H1 id=2 | `draft`, `is_active=false` |
| Annual 2025 id=1 | `closed`, `is_active=false` |
| invite id=4 | `is_used=false` |
| participants period 2 | 87 / 89 |
| workflows | **25 / 60** (same as start) |

After-dumps, restore-verified, copied to the host:

| Artefact | SHA-256 | Bytes | Restore |
|---|---|---|---|
| `epe_2026_after.dump` | `a5de3a87d0499ba66fe521fd986800c02c83adb6c2601a5229665811ae7a77a7` | 73274 | users=89 evals=0 h1=`draft,false` reg=1 |
| `n8n_public_after.dump` | `0fdd35f99601bccbc35e514dcb335f1b2f4abddbaa29ea3ccf1b1fb1d9c13b13` | 477540 | workflows=60 active=25 |
| 2025 fingerprint after | `21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e` | — | **unchanged=true** |

n8n public SHA **≠** before. Compared restored dumps table-by-table:

- `workflow_entity` 60, active 25, `workflow_history` 73 — same
- `webhook_entity` 28 — same
- `execution_entity` / `execution_data` 106 → **111**
- `insights_raw` 0 → **220**

That is n8n writing its own execution/insights rows because the rehearsal called live webhooks. Workflow JSON / activation set did not change.

`epe_2026` SHA differs because sequences moved (`evaluations_id_seq=12`, `evaluation_scores_id_seq=43`) after insert+delete. Row counts match the before-state.

---

## 10. Runbook wording

`docs/LAUNCH_RUNBOOK_H1.md` line now:

> Не меняйте **классификацию** (`general` / `project`) после первой отправленной оценки — система вернёт 409, это не поломка.

Was: «проект / полевые и т.д.». Those labels are not the stored values.

---

## 11. What was not captured

- Screenshot of the «Зарегистрирован» badge on the filtered Alina row (search hit + source confirmed; photo missed).
- Browser login as Balova (same unregistered state as Esenova; exclusion already on HR API).
- Mailbox-side proof that Alina’s verification email landed in inbox vs spam (code was read from the DB, as in the shared-invite brief).
- A saved HAR of the employee dashboard. Webhook names above are from the session observation, not a downloaded HAR file.
