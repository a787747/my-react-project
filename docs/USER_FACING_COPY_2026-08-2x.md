# User-Facing Copy & Visibility Audit — EPE, 2026-08-20

Read-only audit. Nothing was changed: no workflow PUT/activate/deactivate, no deploy, no DB
write, no mail, no frontend edit.

## Evidence base

| Source | How it was obtained |
|---|---|
| Frontend copy | Files under `src/` in this repo, at working-tree state of 2026-08-20 |
| Backend copy & logic | Live n8n workflows dumped from `workflow_entity` in the `postgres_n8n` container on 92.51.45.147, 2026-08-20. The `n8n_workflows/` directory in this repo is **stale** and was not used. |
| Criteria catalogue | `SELECT * FROM performance_db.criteria` on `epe_2026`, 2026-08-20 |
| Roster / scope | `performance_db.users`, `performance_db.evaluation_period_participants` on `epe_2026`, 2026-08-20 |
| Rendered states | Local `vite` dev server on port 5199, browser capture of `/login`, `/register` (no token), `/reset-password` (no token) |

### What was NOT verified by rendering

Only unauthenticated screens were rendered. 88 of 89 accounts have `password_hash IS NULL`
(never registered) and the one registered account's password is not available to this session,
so no authenticated screen was rendered. **Every authenticated-screen statement below is
derived from source code and live workflow definitions, not from an observed screen.** Where a
runtime detail cannot be settled from code alone, it is marked `UNVERIFIED`.

### Database state at time of audit

`epe_2026` contains **0 rows in `performance_db.evaluations`**. Period 1 `Annual 2025` is
`closed`, period 2 `H1-2026` is `draft` (not yet active). 87 of 89 users are `is_in_scope = true`
for period 2; the two out-of-scope users are id 31 `Aysoltan Esenova` and id 35 `Govher Balova`.

---

# 1. Verbatim copy inventory

All strings are quoted verbatim in their original language. Anything I describe rather than
quote is marked **[paraphrase]**. Language mixing is flagged inline as **[EN]**.

## 1.0 Shared plumbing that appears in every journey

### API error messages — `src/utils/errorHandler.js:13-72`

These are produced by the axios interceptor and are what most screens actually display,
because the interceptor overwrites the server's message for several status codes.

| HTTP | String shown to the user | Server message kept? |
|---|---|---|
| 400 | server message, else `Некорректные данные запроса` | yes if present |
| 401 | `Сессия истекла. Пожалуйста, войдите снова` | **no — always discarded** |
| 403 | `Доступ запрещен. Недостаточно прав` | **no — always discarded** |
| 404 | server message, else `Запрашиваемый ресурс не найден` | yes if present |
| 409 | server message, else `Конфликт данных` | yes if present |
| 422 | server message, else `Ошибка валидации данных` | yes if present |
| 429 | `Слишком много запросов. Попробуйте позже` | **no — always discarded** |
| 500 | `Внутренняя ошибка сервера. Попробуйте позже` | **no** |
| 502/503/504 | `Сервер временно недоступен. Попробуйте позже` | **no** |
| other | server message, else `Ошибка сервера (код ${status})` | yes if present |
| no response, offline | `Отсутствует подключение к интернету` | — |
| no response, online | `Нет ответа от сервера. Проверьте подключение к сети` | — |
| timeout (30 s) | `Превышено время ожидания ответа от сервера` | — |
| unknown | `Произошла непредвиденная ошибка` | — |

Consequence for this audit: **all 403 responses reach the user as the same sentence,
`Доступ запрещен. Недостаточно прав`**, regardless of whether the backend said
`NOT_IN_SCOPE`, `ROLE_FORBIDDEN`, `CAPABILITY_FORBIDDEN` or `OWNERSHIP_FORBIDDEN`.

### Auth Guard codes — live workflow `EPE: Auth Guard` (id `L0Zr7nVa8O5YWXd3`)

`TOKEN_MISSING`, `TOKEN_INVALID`, `TOKEN_EXPIRED`, `SESSION_INVALID`, `ROLE_FORBIDDEN`,
`CAPABILITY_FORBIDDEN`. All carry **[EN]** messages. None of them ever reaches the screen —
see the 401/403 rows above.

### Session expiry banner — `src/components/SessionExpiryWarning.jsx:39-40`

Shown when the JWT has ≤ 15 minutes left (`WARNING_WINDOW_MS = 15 * 60 * 1000`, line 5),
re-checked every 30 s:

> `Сессия завершится примерно через {minutes} мин. Завершите форму; незавершённая оценка сохранится локально.`

### Suspense fallback — observed at `/register` and `/reset-password` before chunk load

> `Загрузка страницы...`

### Sidebar — `src/components/Sidebar.jsx`

Product name: `Evaluation Performance Portal`.
Group headings: `Личные`, `Команда`, `HR Панель`, `Аналитика`, `Администрирование`.
Items: `Инструкции`, `Мой Профиль`, `Самооценка`, `Мои оценки`, `Оценить руководителя`,
`Моя Команда`, `Оценки команды`, `Список команды`, `Статусы оценок`, `Сотрудники`,
`Дашборд`, `Все оценки`, `Матрица оценок`, `Итоговые баллы`, `Калькуляция бонусов`,
`Калькуляция баллов`, `Периоды`, `Критерии`, `Коэффициенты`.
Task panel: `Мои задачи`, `Самооценка`, `Сотрудники`, `Руководитель`, `C-level не оценивается`.
Logout: confirm text `Вы точно хотите выйти?`, button `Выйти`.

---

## 1.1 Invite link → registration (all roles)

The invite mail body itself is generated outside the audited endpoints — `API: Create Invite`
returns the token; no invite-mail node was found in the live export. **The invite email text
could not be located and is therefore not quoted here.**

### `/register` with no token — rendered and captured

Header `Регистрация в системе`, sub-header `Как получить доступ`, three numbered steps:

1. `Обратитесь к HR-отделу` / `Попросите HR добавить вас в систему и выслать ссылку для регистрации`
2. `Получите ссылку-приглашение` / `Ссылка придёт на вашу рабочую почту @sedamedical.com`
3. `Завершите регистрацию` / `Перейдите по ссылке, подтвердите email и создайте пароль`

Callout: `Уже есть ссылка?` / `Если у вас уже есть ссылка-приглашение, просто перейдите по ней для регистрации`
Link: `Перейти на страницу входа`

### `/register?token=…` — `src/pages/Register.jsx`

While the token is checked (line 265): `Проверка ссылки...`

Token invalid or expired (lines 283-284): header `Ссылка недействительна`, sub-header
`Срок действия ссылки истёк`, then the API message, then
`Обратитесь к HR-отделу для получения новой ссылки для регистрации`, button
`Перейти на страницу входа`.

API messages that land in that slot, from live `API: Verify Invite`:
`Too many requests. Try again in a few minutes.` **[EN]** and `Token is invalid or expired` **[EN]**.

Step indicators: `Email`, `Код`, `Пароль`.

**Step 1 — email.** Header `Введите email`, sub-header `Укажите ваш рабочий email`,
label `Рабочий Email`, placeholder `name@sedamedical.com`, hint `Только @sedamedical.com`,
button `Отправить код` / `Отправляем...`.
Client-side validation: `Разрешены только email с доменом @sedamedical.com`.
Fallback on failure: `Ошибка отправки кода. Проверьте email.`

Server messages from live `API: Send Verification Code`:
- `email_not_found` → `Email не найден в системе. Проверьте правильность написания или обратитесь в HR.`
- `already_registered` → `Этот аккаунт уже зарегистрирован. Пожалуйста, войдите или сбросьте пароль.`
- `resend_cooldown` → `Код уже отправлен. Подождите {retryAfter} сек. перед повторной отправкой.`
- success → `Код подтверждения отправлен на {email}`

Dedicated screens: `Аккаунт уже существует` (line 371) with
`Этот email уже зарегистрирован в системе`, body
`Этот аккаунт уже был зарегистрирован ранее. Вы можете войти в систему или сбросить пароль, если забыли его.`,
buttons `Войти в систему` / `Использовать другой email`, footer
`Забыли пароль? Обратитесь к HR-отделу (hr@sedamedical.com) для сброса пароля`.
And `Email не найден` (line 438) with `Этот email не зарегистрирован в системе`,
`Проверьте правильность email`, `Убедитесь, что вы правильно написали адрес электронной почты`,
`Обратитесь в HR`, `Если email правильный, попросите HR-отдел добавить вас в систему`,
buttons `Попробовать другой email` / `Перейти на страницу входа`.

**Step 2 — code.** Header `Подтверждение email`, sub-header `Введите код из письма`,
`Здравствуйте, {fullName}!`, `Код отправлен на {email}`, label `Код подтверждения`,
placeholder `000000`, buttons `Назад` / `Подтвердить` / `Отправить код повторно`.
Client validation: `Введите 6-значный код`. Fallback: `Неверный код`.
Server, live `API: Verify Code`: `No valid verification code found. Please request a new code.` **[EN]**,
`Too many attempts. Please request a new code.` **[EN]**,
`Invalid code. {remaining} attempts remaining.` **[EN]**, success `Email verified successfully` **[EN]**.

**Step 3 — password.** Header `Создание пароля`, sub-header `Придумайте надёжный пароль`,
`Email подтверждён: {email}`, label `Пароль`, placeholder `Минимум 8 символов, A-z, 0-9`,
strength labels `Слабый` / `Средний` / `Хороший` / `Отличный`, label `Подтверждение пароля`,
placeholder `Повторите пароль`, button `Завершить регистрацию`.
Validation: `Пароль должен содержать: {errors}`, `Пароли не совпадают`. Fallback: `Ошибка регистрации`.
Server, live `API: Register`: `Registration link or verification code is invalid` **[EN]**,
success `Registration successful! You can now login.` **[EN]** (overridden by the frontend, below).

Success screen: `Регистрация успешна!`, `Добро пожаловать, {fullName}!`,
`Перенаправление на страницу входа...`.

### System email — verification code (live `API: Send Verification Code`, node `Send Email`)

Subject: `Код подтверждения регистрации - SEDA Medical`
Body (Russian, HTML): `Здравствуйте, {full_name}!` / `Ваш код подтверждения для регистрации:` /
`{code}` / `⏱️ Код действителен 10 минут` /
`Если вы не запрашивали регистрацию, просто проигнорируйте это письмо.`

---

## 1.2 Login and forgot-password (all roles)

### `/login` — rendered and captured, `src/pages/Login.jsx`

![Login screen](/var/folders/n8/smrynkb96r9g4mn8b5s3sgf80000gn/T/cursor/screenshots/epe_login.png)

Header `Evaluation Portal` (line 118) — **[EN]** — sub-header `Войдите в систему для продолжения`.
Label `Email`, placeholder `name@company.com` (note: **not** `@sedamedical.com`, unlike every
other email field in the product). Label `Пароль`, placeholder `••••••••`.
Link `Забыли пароль?`. Button `Войти` / `Вход...`. Footer `Нет аккаунта? Зарегистрироваться`.

Server, live `API: Auth Login (No Params)`: `Неверный email или пароль`.
Throttle response is a 429, so the user sees the interceptor's
`Слишком много запросов. Попробуйте позже`, never the backend's retry-after wording.

### Registration-help modal — rendered and captured

![Registration help modal](/var/folders/n8/smrynkb96r9g4mn8b5s3sgf80000gn/T/cursor/screenshots/epe_register_help.png)

Same three steps as `/register` with no token, plus dismiss button `Понятно`.

### Forgot-password modal — `src/pages/Login.jsx:341-342`, verified in the rendered DOM

Header `Забыли пароль?`, sub-header `Как восстановить доступ`, label `Рабочий email`,
placeholder `name@sedamedical.com`, hint
`Ссылка одноразовая и действует 30 минут. Ответ одинаков для существующих и неизвестных адресов.`,
button `Отправить ссылку` / `Отправляем...`.
Success (frontend-hardcoded): `Если такой аккаунт существует, ссылка для сброса отправлена на рабочую почту.`
Failure: `Не удалось отправить запрос. Попробуйте ещё раз позже.`
The backend's own success string is `If the account exists, a reset link has been sent.` **[EN]**
and is never displayed.

### System email — password reset (live `API: Request Password Reset`)

Subject: `Сброс пароля — SEDA Medical`
Body: `Здравствуйте, {full_name}.` / `Для создания нового пароля перейдите по ссылке:` /
link text `Создать новый пароль` / `Ссылка одноразовая и действует 30 минут.`

### `/reset-password` — rendered and captured

![Reset password screen](/var/folders/n8/smrynkb96r9g4mn8b5s3sgf80000gn/T/cursor/screenshots/epe_reset_no_token.png)

Header `Новый пароль`, sub-header `Ссылка одноразовая и действует 30 минут.`,
labels `Новый пароль` and `Повторите пароль`, button `Сохранить пароль` / `Сохраняем...`.
Validation: `Ссылка для сброса пароля недействительна.`,
`Пароль должен содержать минимум 8 символов.`, `Пароли не совпадают.`
Server: `Reset link is invalid or expired` **[EN]** → shown via the 400/404 path, and
`Password reset successful. Please sign in again.` **[EN]** → **never shown**; the frontend
substitutes `Пароль изменён. Все старые сессии завершены.` with button `Перейти ко входу`.

Note on the captured screenshot: with **no token at all** in the URL the page still renders the
full form. The user only learns the link is unusable after filling both fields and pressing
`Сохранить пароль`.

---

## 1.3 First screen after login, by role

Routing: `src/App.jsx` sends `hr` to `/hr-dashboard` and every other role to `/welcome`.

### `/welcome` — `src/pages/Welcome.jsx`

Title `Добро пожаловать в систему оценки!` /
`Эта страница поможет вам понять, как работает система оценки производительности в нашей компании`

`Обращение к сотрудникам`:
> `Система оценки производительности предназначена для объективного анализа вашей работы, выявления сильных сторон и областей для развития. Мы стремимся создать прозрачную и справедливую систему, которая поможет каждому сотруднику расти профессионально. Все данные оценок доступны только руководству компании (C-level менеджерам) для обеспечения конфиденциальности и объективности процесса. Оценивается не разовое поведение сотрудника, а совокупность за период.`

`Ваши задачи` / `Активный период оценки` — tiles `Самооценка`, `Сотрудники`, `Руководитель`,
badge `Выполнено`, and `C-level менеджеры не оцениваются подчиненными`.

`Процесс оценки (для менеджеров с подчиненными)` /
`Если у вас есть подчиненные, процесс оценки включает дополнительные этапы`:

- `Самооценка и оценка вашего менеджера` — `Внимательно прочитайте критерии оценок. Сначала вы выполняете самооценку по установленным критериям. Затем вы оцениваете своего руководителя.`
- `Важно: Анонимность оценки вами своего менеджера` — `Оценка вашего менеджера остается анонимной - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.`
- `Оценка качества управления от подчиненных` — `Ваши подчиненные оценивают вас по критериям качества управления. Эта оценка также остается анонимной для вас.` / `Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.`
- `Критерий для оценки руководителя` — `Руководители (сотрудники, у которых есть прямые подчиненные) также будут оценены по критерию "Критерий для оценки руководителя". Оценка проводится каждым сотрудником отдела и непосредственным руководителем оцениваемого менеджера.`
- `Оценка ваших подчиненных` — `Вы оцениваете своих подчиненных по установленным критериям. Оценка вашего менеджера остается для вас недоступна, чтобы избежать искажения.` / `Оценка вашего менеджера недоступна вам, чтобы обеспечить независимость и объективность ваших оценок подчиненных.`
- `Оценка старшего менеджера (опционально)` — `Старший менеджер может поставить вам свою оценку. В этом случае оценки вашего менеджера и старшего менеджера усредняются для получения финального результата.`
- `Оценка C-level менеджеров` — `C-level менеджеры оценивают вас по специальным критериям, доступным только для руководства компании.`

`Процесс оценки (для сотрудников без подчиненных)` — same steps minus the subordinate-rating one.

`Дополнительные критерии`:
> `Некоторые категории сотрудников будут оцениваться также и по дополнительным критериям. Например, участники проектов могут иметь специальные проектные критерии, а сотрудники определенных отделов - критерии, специфичные для их области деятельности.`

`Готовы начать?` / `Перейдите в раздел "Самооценка" для начала процесса оценки или в "Мой Профиль" для просмотра ваших текущих результатов.`

### Manager first dashboard — `/dashboard`, `src/pages/Dashboard.jsx:162-172`

Header `Моя команда` / `Сотрудники в вашем подчинении`.
Empty state, campaign active: `Нет сотрудников в этой кампании` /
`В активном периоде нет подчинённых в охвате оценки.`
Empty state, campaign not active: `Кампания ещё не открыта` /
`Список для оценки появится, когда HR откроет период.`

Employee card — `src/components/EmployeeCard.jsx`: badges `Самооценка ✓` / `Самооценка`,
`Оценил рук-ля ✓` / `Оценка рук-ля`, `Оценен вами`, `Балл: {score}`; fields `Отдел {name}`,
`Grade: {code}` **[EN label]**; `Критерии оценки:` with `Общие: {n}`, `Проект: {n}`,
`Руководство: {n}`, `C-level: {n}`; button `Оценить` or `Редактировать`.

### HR first screen — `/hr-dashboard`, `src/pages/HRDashboard.jsx`

Header `Статусы оценок` / `Мониторинг прогресса оценок сотрудников`, button `Обновить`.
Stat cards `Самооценки`, `Оценили руководителя`, `Оценили подчинённых`, `Полностью завершили`,
each with sub-label `{value} из {total}`.
Search placeholder `Поиск по имени, email или должности...`;
filter options `Все сотрудники`, `Завершили оценки`, `Не завершили`.
Table headers `Сотрудник`, `Самооценка`, `Оценка руководителя`, `Оценка подчинённых`, `Общий статус`.
Status badges `Завершено`, `Нет самооценки`, `Не оценил руководителя`, `Не оценил {n} подчин.`, `{n} задачи`.
Empty: `Нет результатов` / `Попробуйте изменить параметры поиска`.
Error: `Ошибка загрузки` + message + `Повторить`.

---

## 1.4 Self-review form

### `/self-review` — `src/pages/SelfReview.jsx`

Header `Самооценка` / `Оцените свою работу в текущем периоде`.

Exempt state for `admin` / `c_level` (line 105): `Самооценка не требуется` /
`Для {roleLabel} самооценка не предусмотрена в системе оценки.`

The warning block, `Важная информация` (line 134), verbatim:
> `Самооценка проводится ОДИН РАЗ и не подлежит пересмотру. После сохранения вы не сможете изменить свои оценки. Будьте честны и объективны при оценке своих результатов. Самооценка не влияет на материальную составляющую мотивации и нужна для планирования развития сотрудников. Пожалуйста, старайтесь следовать логике в описании оценок, они построены таким образом, что 85-90% сотрудников попадают в желтую и зеленую зоны, редкие сотрудники в красную и фиолетовую по определенным критериям. Явное завышение или занижение не будет добавлять вам никаких преимуществ.`

Status card — `src/components/self-review/SelfReviewStatusCard.jsx`:
- not started: `Готовы начать?` / `Вам доступно {n} {критерий|критерия|критериев} для оценки. Это займет не более 5-10 минут.` / button `Начать самооценку`; if none: `Нет доступных критериев`
- done: `✅ Вы уже оценили себя в этом периоде`, `Итоговая оценка:`, `Дата самооценки:`, `Период:`, `🎉 Все {n} критериев оценены`
- new criteria appeared: `🆕 Появились новые критерии оценки` / `Администратор добавил новые критерии ({n} шт.), требующие вашей оценки.` / button `Оценить новые критерии`

Modal — `src/components/self-review/SelfReviewModal.jsx`: title `Самооценка` (or
`Оценка новых критериев`), `{userName}`, `{n} вопросов`, notice `Черновик восстановлен`,
comment label `Комментарий (необязательно)` with placeholder
`Добавьте пояснение к вашей оценке...`, progress `Оценено: {n} из {total}` / `Осталось: {n}`,
buttons `Отмена`, `Сохранить самооценку` / `Сохранение...`, disabled state
`Оцените все критерии ({n})`.
Confirmation step: `Подтверждение самооценки` / `Проверьте ваши оценки перед сохранением`,
`Средний балл: {avg}`, buttons `Изменить` / `Подтвердить`.

Failure path — `src/pages/SelfReview.jsx:78`: a browser `alert()` containing
`result.error || 'Ошибка при сохранении'`.

Server, live `API: Submit Self Review`: `INVALID_SCORE`, `SCORE_OUT_OF_RANGE`,
`INVALID_WEIGHTED_SCORE` **[EN]**; `NOT_IN_SCOPE` → `No active period or actor is not in scope` **[EN]**;
`DUPLICATE_SELF_REVIEW` → `Self-review already exists for this period` **[EN]** or
`Self-review already exists (concurrent submission).` **[EN]**.

## 1.5 Upward form (subordinate rates their manager)

### `/manager-evaluation` — `src/pages/ManagerEvaluation.jsx`

Header `Оценка руководителя` / `Оцените качество управления вашего непосредственного руководителя`.

No manager (line 146): `Руководитель не назначен` /
`В системе не указан ваш непосредственный руководитель. Обратитесь к HR-отделу для уточнения информации.`,
button `Обновить данные`.

Manager is C-level or admin (line 192): `Оценка недоступна` /
`Ваш непосредственный руководитель является менеджером уровня C-level.` /
`C-level менеджеры не оцениваются подчиненными в рамках данной программы оценки.` /
`Если у вас есть вопросы или предложения, пожалуйста, обратитесь к HR-отделу или администратору системы.`

Form: `Критерии оценки` / `Оцените работу руководителя по каждому критерию`, notice
`Черновик восстановлен`, button `Отправить оценку` / `Сохранение...`, hint
`Пожалуйста, оцените все критерии перед отправкой`.
Success: `Оценка успешно сохранена!` / `Итоговый балл: {score}`.
Already done: `Вы уже оценили своего руководителя` /
`Ваша оценка была успешно сохранена. Текущий балл: {score}`.
No criteria: `Критерии оценки не настроены` /
`Обратитесь к администратору для настройки критериев оценки руководителей.`
Badges: `Оценено`, `Ожидает оценки`.

**There is no confidentiality statement anywhere on this page.** See §3.3.

## 1.6 Manager form (manager rates a subordinate)

### `EvaluationModal` — `src/components/EvaluationModal.jsx`

Header shows `{full_name}` / `{job_title}`. Info bar: `Категория: {categoryLabel}`,
`Участник проекта`, `Черновик восстановлен`, `⭐ Самооценка: {score}`.
Loading: `Загрузка данных...`. No criteria: `Нет активных критериев для категории "{category}".`

Criterion groups (lines 113-152), each rendered as `{title}` + `{subtitle} • {n} критериев`:

| Group | Title | Subtitle | Shown when |
|---|---|---|---|
| self | `⭐ Основные критерии` | `Самооценка + Оценка руководителя` | always |
| general | `📋 Общие критерии` | `Оценка руководителя` | always |
| project | `🎯 Проектные критерии` | `Для участников проектов` | `employee.is_project_participant` |
| management | `📊 Критерии управления` | `Для руководителей` | `employee.has_subordinates` |
| c_level | `👑 C-level критерии` | `Только для руководства` | actor role ∈ {admin, c_level} |

Per-criterion UI — `src/components/CriterionSlider.jsx`: `{score}/10`, empty state
`Выберите оценку от 1 до 10`, zone label, level description (fallback
`Описание для этого уровня не задано`), `Самооценка сотрудника:` + `{score}`,
`Комментарий сотрудника:` + `"{comment}"`, and the manager's own field
`Ваш комментарий (необязательно)` with placeholder `Добавьте комментарий к оценке...`.

Confirmation: `Подтверждение оценки` / `Проверьте оценки для {employeeName}`, buttons
`Изменить` / `Подтвердить`. Footer buttons `Отмена`, `Сохранить оценку` or `Обновить оценку`,
`Сохранение...`, disabled `Оцените все критерии ({n})`, `Закрыть`.

Server, live `API: Submit Evaluation`: `INVALID_SOURCE`, `ROLE_FORBIDDEN`, `INVALID_SUBJECT`,
`SELF_EVALUATION_FORBIDDEN`, `SCOPE_MISMATCH`, `CANNOT_EVALUATE` **[EN]**, and
`DUPLICATE_EVALUATION` → `Evaluation already exists for this evaluator/subject/source/period tuple. Use /api/update-evaluation.` **[EN]**.

## 1.7 My profile / evaluation history

### `/profile` — `src/pages/Profile.jsx`

Header `Мой профиль` / `{fullName} • {jobTitle}`. Loading `Загрузка профиля...`.
Error `Ошибка загрузки данных. Попробуйте обновить страницу.` Missing `Нет данных профиля`.

Self-evaluation card — `src/components/profile/SelfEvaluationCard.jsx`: `⭐ Ваша самооценка`,
badge `САМООЦЕНКА`, fields `Оценка`, `Дата`, `Период`, link `Посмотреть детали самооценки`.

Sections: `История самооценок` (regular employees only), `Оценки от руководителя` with rows
`Оценен руководителем: {evaluatorName}` and badge `✓ Оценено`; `Оценки от подчиненных` /
`Оценки качества управления от вашей команды` with rows `Оценен подчиненным: {evaluatorName}`
and `Всего оценок от подчиненных: {n}`.
Empty: `Вы еще не были оценены` /
`Как только ваш менеджер проведет оценку, результаты появятся здесь.`

Detail modal for a regular employee — `src/components/profile/EvaluationDetailsModal.jsx`:
> `Оценка менеджера` / `Детали оценки недоступны` /
> `Вы можете видеть только факт того, что менеджер провел оценку. Детальные результаты доступны только администраторам.`
> button `Закрыть`

Detail modal for admin/c_level: `Детали оценки`, badge `⭐ САМООЦЕНКА`,
`Итоговая оценка` `{score}/10`, `Это ваша собственная оценка своей работы`,
`Оценка по критериям`, `Загрузка деталей...`, `Ошибка загрузки деталей`, `Закрыть`.

Table — `src/components/profile/ProfileEvaluationsTable.jsx`: `История оценок`, headers
`Период`, `Тип оценки`, `Оценка`, `Оценил`, `Дата`, `Действия`; type `⭐ САМООЦЕНКА` or
`Оценка менеджера`; `{score}/10` plus `Взвешенный: {weightedScore}` for admin/c_level only;
evaluator `Вы сами` / `Самостоятельно`; button `Детали`.

Criteria overview — `src/components/profile/CriteriaOverview.jsx`: header `Критерии оценки` /
`Ниже представлены критерии, по которым вы оцениваетесь в системе`; groups
`Критерии для самооценки`, `Критерии для оценки менеджером`, `Критерии для оценки C-level`,
`Критерии качества управления`, `Критерии для участников проектов`, each with the explanatory
subtitle quoted in §3.6; per-criterion toggle
`Показать описания уровней (1-10)` / `Скрыть описания уровней`; warnings
`Внимание: Критерии загружены, но не найдено активных критериев, соответствующих вашей категории работы.`,
`Всего загружено критериев: {n}`, `Критерии оценки загружаются...`.

### `/evaluation-history` — `src/pages/EvaluationHistory.jsx`

Header `Мои оценки` / `Все оценки, которые вы провели` / `(Всего: {n})`.
Sections `Оценки руководителя` / `Оценки, которые вы дали своему руководителю ({n})` and
`Оценки подчиненных` / `Оценки, которые вы дали своим подчиненным ({n})`.
Empty: `Оценок пока нет` / `Здесь будут ваши оценки, когда вы их проведете.` and
`Оценок подчиненных пока нет` / `Здесь будут оценки ваших подчиненных, когда вы их оцените.`

## 1.8 Reporting screens, by reachable role

Period banner shared by reporting screens — `src/components/common/PeriodBanner.jsx`:
`Период: {name} — активен` or `— {status}`; empty state prints the screen's own `emptyCopy`
plus `{draftName} сейчас черновик. Числа появятся после активации.` or
`Активируйте период, чтобы увидеть оценки этого цикла.`

| Screen | Route | Roles that can open it | Key copy |
|---|---|---|---|
| Аналитика по отделам | `/analytics` | admin, c_level, hr | `Аналитика по отделам` / `Сравнение показателей и средние баллы подразделений. Числа — одного периода.`; empty `Пока нет данных для аналитики`; sections `Средний балл по отделам`, `Детализация по отделам` / `Нажмите на заголовок для сортировки`, `Распределение отделов` / `По зонам эффективности`, `Лучшие сотрудники` / `Топ-5 по среднему баллу`, `Требуют внимания` / `Сотрудники с низким баллом` |
| Все оценки | `/admin/all-evaluations` | admin, c_level | header per `AdminAllEvaluations.jsx:89` |
| Матрица оценок | `/admin/evaluations-matrix` | admin, c_level | header per `AdminEvaluationsMatrix.jsx:186`; export alerts `Файл "{filename}" успешно сохранён!`, `Ошибка при экспорте данных`; C-level write alerts `C-level оценка сохранена!`, `Ошибка при сохранении оценки` |
| Итоговые баллы | `/admin/final-scores` | admin, c_level | header per `AdminFinalScores.jsx:113` |
| Калькуляция бонусов | `/bonus-calculation` | admin, c_level | `Калькуляция бонусов` / `Расчет бонусов сотрудников на основе итоговых оценок`; period line `Нет активного периода — числа не смешиваются между циклами.`; `Параметры расчёта`, `Общий бюджет бонусов` (placeholder `3 000 000`, unit `TMT`), hint `Введите сумму — стоимость балла рассчитается автоматически`, `Стоимость одного балла` (placeholder `150.00`, unit `TMT`), hint `Или введите стоимость балла — бюджет рассчитается автоматически`, stats `Сотрудников:` / `Сумма баллов:` / `Итого бонусов:`, buttons `Обновить`, `Экспорт CSV`; empty `Нет данных` |
| Калькуляция баллов | `/admin/score-calculator` | admin only | header per `AdminScoreCalculator.jsx:196` |
| Оценки команды | `/team-scores` | manager-of-managers, c_level, admin — **but see §4.2, the nav item never renders** | `Оценки команды` / `Корректировка оценок сотрудников ваших подчинённых менеджеров. Нажмите на оценку для просмотра деталей и добавления корректировки.`; period empty copy `Нет активного периода — матрица не смешивает строки.`; empty state `Нет данных для отображения` / `У ваших подчинённых менеджеров пока нет оценённых сотрудников, или у вас нет подчинённых с правами менеджера.`; filter `Все менеджеры`, `Всего сотрудников: {n}` |
| Периоды | `/admin/periods` | admin, c_level | `Регистрация сотрудников`, `Создать период оценки`; alerts `Не удалось активировать период`, `Не удалось создать период` |
| Критерии | `/admin/settings` | admin, c_level | `Очистка тестовых данных` |
| Коэффициенты | `/admin/scoring` | admin, c_level | `Коэффициенты грейдов` / `Множитель итогового балла для каждого грейда сотрудника`; `Веса и коэффициенты критериев` / `Настройка веса каждого критерия и коэффициентов для уровней оценки (1-10)`; alerts `Коэффициенты успешно сохранены!`, `Ошибка при сохранении` |
| Сотрудники | `/admin/users` | admin, c_level in the nav; **backend is admin-only** → c_level gets `Доступ запрещен. Недостаточно прав` | header per `AdminUsers.jsx:268` |

Score detail modal shared by the two matrices — `src/components/admin/ScoreDetailModal.jsx`:
group headers `⭐ Основной критерий` / `Самооценка + Оценка руководителя`,
`📋 Общий критерий` / `Оценка руководителя`, `🎯 Проектный критерий` / `Для участников проектов`,
`👑 C-level критерий` / `Оценка руководства`; rows `Самооценка`, `Оценка руководителя`,
`C-level оценка`, `Коррекция менеджера` / `Mid-level`, `Коррекция C-level` / `Высшее руководство`;
score labels `Нет оценки`, `Отлично` (≥8), `Хорошо` (≥5), `Требует улучшения` (≥3), `Критично`;
comparison `Оценки совпадают` / `Самооценка выше на {n} баллов` / `Оценка руководителя выше на {n} баллов`;
correction block `Корректировка C-level` / `Корректировка Mid-level`, `Добавить` / `Изменить`,
`Ваша оценка:`, `Расчёт итоговой оценки:`, `Отмена`, `Сохранить` / `Сохранение...`,
hint `💡 Вы можете скорректировать оценку. Итоговый балл будет средним всех корректировок.`,
result block `Итоговая оценка`, footer `Закрыть`, failure alert `Ошибка при сохранении корректировки`.

## 1.9 Out-of-scope registrant (hired after 30 June) — Esenova, Balova

These two users are role `employee`, `can_evaluate = true`, `can_be_evaluated = true`, and
`is_in_scope = false` for period 2. **The UI has no concept of "out of scope".** They receive:

- `/welcome` with the full instruction text and the `Ваши задачи` tile `Самооценка`
  (`TaskStatusContext` sets `needsSelfReview = !isCLevel`, `src/context/TaskStatusContext.jsx:39-40`)
- the sidebar `Личные` group including `Самооценка` and `Оценить руководителя`
- `/self-review` renders the full warning block and `Начать самооценку` with the real criteria count
- `/manager-evaluation` renders the real manager card and the upward form

They only discover their status at submit time, as a browser `alert()` reading
`Доступ запрещен. Недостаточно прав` — the backend's `NOT_IN_SCOPE` /
`No active period or actor is not in scope` is discarded by `errorHandler.js:32-33`.

## 1.10 Read-only C-level (Cem id 21, Hemra id 40, Mekan id 61)

All three are `role = c_level`, `can_evaluate = false`, `can_be_evaluated = false`,
`is_in_scope = true`. Cem has `has_subordinates = true`; Hemra and Mekan do not. None of the
three has a `manager_id`.

`TaskStatusContext` calls `/api/employees` inside a `Promise.all` **without a `.catch`**
(`src/context/TaskStatusContext.jsx:53-57`). `/api/employees` requires
`required_capability: 'can_evaluate'` (live `API: Get Employees (Smart Role Based)`,
node `Prepare Guard Input`), so for these three the call 403s, the whole `try` block aborts at
line 112, and **every task flag stays at its initial `false`**. Rendered consequence:

- `/welcome` shows the `Ваши задачи` heading and `Активный период оценки` with **no tiles at all**
  (self-review tile suppressed because `needsSelfReview` is false for c_level; the other two
  tiles suppressed because `hasSubordinates` and `hasManager` are false)
- the sidebar `Мои задачи` panel renders with **no indicators**
- the sidebar `Команда` group never appears
- `/self-review` shows `Самооценка не требуется` / `Для {roleLabel} самооценка не предусмотрена в системе оценки.`
- `/manager-evaluation` shows `Руководитель не назначен` /
  `В системе не указан ваш непосредственный руководитель. Обратитесь к HR-отделу для уточнения информации.`
- `/profile` shows `Вы еще не были оценены` / `Как только ваш менеджер проведет оценку, результаты появятся здесь.`
- `/evaluation-history` shows `Оценок пока нет` / `Здесь будут ваши оценки, когда вы их проведете.`
- all `Аналитика` reporting screens are reachable and populated

**[UNVERIFIED]** the above is derived from code paths, not from a rendered session.

---

# 2. Visibility & timing matrix

There is **no period-close gate anywhere in the codebase.** No endpoint and no component
branches on `period.status = 'closed'` before revealing a score. Everything below is therefore
either visible **immediately on submit** or **never**, and the "after period close" column is
empty by construction. That is itself a finding — see §4.1.

Legend: **imm** = visible as soon as the row is written; **never** = no code path exposes it;
**API-only** = the HTTP response contains it but the UI does not render it, so it is one
browser-devtools step away for any logged-in user.

| Artifact | Subject | Their manager | Manager-of-manager | C-level writer (Bayram, Jemal) | Read-only C-level | HR | Admin | Evidence |
|---|---|---|---|---|---|---|---|---|
| Own self-review score | imm | never (see note) | never | imm | imm | imm (flag only) | imm | `API: Check Self Review` (self); `API: My Profile V5`; `API: evaluations-matrix` `self_score` |
| Own self-review per-criterion content | imm | **never — broken, see §4.3** | never | imm | imm | never | imm | `API: Check Self Review` `WHERE e.subject_id = ${actorId}` |
| Someone else's self-review flag (done/not) | — | imm | — | imm | imm | imm | imm | `API: HR Evaluation Status`, guard `["hr","admin","c_level"]`; manager gets 403 → §4.4 |
| Manager rating of subject, score | **API-only** | imm (own) | imm | imm | imm | never | imm | `API: My Profile V5` returns `calculated_score` to the subject; `Profile.jsx` + `EvaluationDetailsModal.jsx` hide it behind `Детали оценки недоступны` |
| Manager rating, per-criterion + visible comment | **API-only** | imm (own) | imm | imm | imm | never | imm | `API: Get Evaluation Details FIXED` — no subject-side gate on `scores`; UI gate only |
| `private_comment` | never | imm (own) | never | imm | imm | never | imm | `API: Get Evaluation Details FIXED`, `isPrivileged \|\| isEvaluator` |
| Upward rating of a manager, score | never | — | imm | imm | imm | never | imm | subject-side: `evaluations-matrix` `subordinate_avg_score` is admin/c_level only; `My Profile V5` returns the row to the subject → see next line |
| Upward rating, **evaluator identity** | **redacted** | — | imm | imm | imm | never | imm | `API: My Profile V5`, `Format Response`: `evaluator_name: row.evaluation_source === 'subordinate' ? null : row.evaluator_name`; same rule in `API: Get Evaluation Details FIXED` |
| Upward rating, **score visible to the rated manager** | **yes, API-only** | — | — | — | — | — | — | `API: My Profile V5` returns `calculated_score` for `evaluation_source='subordinate'` rows with no redaction; `Profile.jsx` renders only `✓ Оценено` + `Всего оценок от подчиненных: {n}` |
| mid_level correction | never | never | imm (own) | imm | imm | never | imm | `API: evaluations-matrix` `mid_level_correction`; write via `API: Score Correction`, `correctionLevel = 'mid_level'` when `skip_level_id === actor` |
| c_level correction | never | never | imm | imm | imm | never | imm | same query; write allowed for `role in ('admin','c_level')` — **including the three read-only C-level, see §4.5** |
| Final cell (manager + corrections averaged) | never | never | imm | imm | imm | never | imm | computed client-side, `src/utils/matrixUtils.js:68-94`; never sent to a subject |
| Bonus screen | never | never | never | imm | imm | never | imm | `App.jsx` `ReportingRoute`; `/bonus-calculation` |
| Index / score-calculator screen | never | never | never | never | never | never | imm | `App.jsx` `AdminRoute` on `/admin/score-calculator` |
| Grade code | imm (own, on cards) | imm | imm | imm | imm | imm | imm | `API: Get Employees` returns `grade_code`; `EmployeeCard.jsx` renders `Grade: {code}` |
| Grade coefficient | **API-only** | **API-only** | **API-only** | imm | imm | **API-only** | imm | `API: Get Employees` and `API: Get My Manager` both return `grade_coefficient` to any caller who passes the guard; only `/admin/scoring` renders it |
| Criteria weights and level descriptions, **including `c_level_only` criteria** | **imm, all of them** | imm | imm | imm | imm | imm | imm | `API: Get Criteria With Levels` has `required_roles: []` and selects every row with no filter — see §4.6 |

### What the subject sees of their own results during the active period

Rendered in the UI: their own self-review score, date, period and per-criterion breakdown;
the *fact* that a manager evaluation exists (`✓ Оценено` plus the evaluator's name); the *count*
of upward evaluations received (`Всего оценок от подчиненных: {n}`) with names suppressed. No
manager score, no manager comment, no correction, no final cell, no bonus figure.

Returned by the API to the same user, but not rendered: `calculated_score` and `weighted_score`
for **every** evaluation where they are the subject — manager evaluations and upward evaluations
alike (`API: My Profile V5`, `Build Profile Query` selects both columns for all rows;
`Format Response` redacts only `evaluator_name` and `evaluator_title`). And, given an
`evaluation_id` from that same response, `API: Get Evaluation Details FIXED` returns the full
per-criterion scores and visible comments to the subject; only `private_comment` and — for
`subordinate`-source rows — `evaluator_name` are withheld.

So the honest statement is: **the confidentiality of manager scores and of upward scores is
enforced in the browser, not on the server.** Identity of upward raters *is* enforced on the
server. See §4.7.

---

# 3. Mechanics facts

## 3.1 The warning before self-review submit, and the second attempt

The warning is the `Важная информация` block quoted in full in §1.4. It is displayed on the
page above the start button, not inside the confirmation dialog. The confirmation dialog itself
says only `Подтверждение самооценки` / `Проверьте ваши оценки перед сохранением`, lists the
scores, shows `Средний балл: {avg}`, and offers `Изменить` / `Подтвердить`. **The one-shot,
no-revision warning is not repeated at the moment of commitment.**

A second submit attempt: `API: Submit Self Review` inserts with
`ON CONFLICT (subject_id, period_id) WHERE is_self_evaluation = true DO NOTHING` and returns
HTTP 409 `DUPLICATE_SELF_REVIEW` with message `Self-review already exists for this period`
**[EN]**. `errorHandler.js:36-37` keeps the server message for 409, and
`src/pages/SelfReview.jsx:78` renders it as a browser `alert()`. So the user sees a native OS
dialog containing an English sentence.

The same 409 fires on the `Оценить новые критерии` path: the workflow's duplicate check does not
consider the frontend's `is_update` flag, so that button can never succeed. It is only reachable
if criteria change mid-period, which the period freeze is supposed to prevent.

## 3.2 Does a manager see the subject's self-review while writing their evaluation?

The UI is built to show it and does show a block labelled as such — but **the data in that block
is the manager's own self-review, not the subordinate's.**

`src/components/EvaluationModal.jsx:180-188` requests
`GET /api/check-self-review?user_id={employee.id}`. The live workflow `API: Check Self Review`,
node `Build Self Review Query`, carries the comment
`// Actor is always the subject; body/query user_id is ignored for auth.` and builds
`WHERE e.subject_id = ${actorId} AND e.is_self_evaluation = true`. The query parameter is
discarded.

Rendered consequence: the info bar `⭐ Самооценка: {score}` and, per criterion,
`Самооценка сотрудника: {score}` and `Комментарий сотрудника: "{comment}"`
(`src/components/CriterionSlider.jsx`) display the **evaluating manager's own** scores and
free-text comments, attributed to the subordinate. If the manager has not done their own
self-review, `has_self_review` is false and nothing is shown, which reads as "the subordinate
hasn't self-assessed yet".

With 0 evaluations in the database, no manager has been able to observe this yet. It will
appear on the first day of H1.

## 3.3 Is upward-evaluation confidentiality stated in the UI?

**Not on the form.** `/manager-evaluation` (`src/pages/ManagerEvaluation.jsx`) contains no
statement about anonymity, about who will see the rating, or about how it is aggregated.

It is stated only on `/welcome` (`src/pages/Welcome.jsx`), and only inside the manager-track
narrative, which a rank-and-file employee reads as being about someone else:

> `Оценка вашего менеджера остается анонимной - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.`

and

> `Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.`

Both claims are **partially false as implemented**: a manager-of-manager sees subordinate
averages in `/team-scores`, HR sees completion status, admin sees everything, and the rated
manager's own API response contains the upward `calculated_score` (see §2 and §4.7).

## 3.4 401 / session expiry mid-form

Warning before it happens: the amber banner in §1.0, top-right, from T-15 minutes, refreshed
every 30 s. It is the only place the product tells the user a draft exists.

At the moment of expiry, `src/api/client.js:54-62` clears `user` and `token` from localStorage
and executes `window.location.href = '/login'`. This is a full page navigation: **all in-memory
form state is lost, and no message is displayed on the login screen explaining why the user is
there.** The interceptor also builds the string `Сессия истекла. Пожалуйста, войдите снова`, but
nothing renders it before navigating. **[UNVERIFIED]** whether the calling component's
`alert()` wins the race against the navigation in practice — the code path assigns
`location.href` before rejecting the promise.

Drafts: `src/utils/evaluationDrafts.js` stores under `epe:evaluation-draft:{evaluatorId}:{subjectId}`
in localStorage with `version: 1` and a 7-day max age (`DRAFT_MAX_AGE_MS`, line 3). Drafts are
**not** cleared by logout or by the 401 handler — `client.js:56-57` removes only `user` and
`token`. On return the user sees a `Черновик восстановлен` chip
(`EvaluationModal.jsx`, `SelfReviewModal.jsx`, `ManagerEvaluation.jsx`). Drafts are restored
only for a *new* evaluation, not in edit mode (`EvaluationModal.jsx:162-164`).

The user is never told which fields were restored, when the draft was saved, or that the draft
lives only in that one browser.

## 3.5 Dashboard / empty-state copy for read-only C-level and out-of-scope users

Covered in full, with the code path for each state, in §1.9 and §1.10. Summary of the two
headline strings:

- out-of-scope employee at submit: a browser `alert()` reading `Доступ запрещен. Недостаточно прав`
- read-only C-level on `/welcome`: the heading `Ваши задачи` / `Активный период оценки` above
  an empty region, because the task-status loader aborts on the 403 from `/api/employees`

## 3.6 Criteria catalogue, verbatim

Source: `performance_db.criteria` on `epe_2026`, read 2026-08-20. Eight rows, all
`is_active = true`. `score_definitions` is `NULL` for all eight. There is **no `level_0_desc`**
on any criterion, although the UI and the API both carry the field.

| id | title | category | target_audience | weight | selfassesment | c_level_only | for_manager |
|---|---|---|---|---|---|---|---|
| 1 | Стратегическая значимость роли | dynamic | all | 5.0 | false | **true** | false |
| 2 | Качество управления и развитие команды | management | managers_only | 3.0 | false | false | true |
| 3 | Личная результативность и эффективность | dynamic | all | 3.0 | **true** | false | true |
| 4 | Надежность и взаимодействие с руководителем | dynamic | all | 1.5 | **true** | false | true |
| 8 | Взаимодействие и надежность в проекте | project | project_participants | 1.4 | false | false | true |
| 10 | Оценка C-Level и соответствие культуре | executive | all | 1.6 | false | **true** | false |
| 12 | Профессиональное развитие и обмен знаниями | dynamic | all | 1.0 | **true** | false | true |
| 13 | Объем проектной работы и загрузка | project | project_participants | 1.8 | false | false | true |

Which means, concretely:

- **Self-review is three criteria** for everyone: 3, 4, 12. A project participant does **not**
  self-assess on the project criteria.
- **The upward form is a single criterion**, id 2, filtered by
  `src/hooks/useManagerEvaluation.js:101-103` (`c.is_active && c.target_audience === 'managers_only'`).
- **The manager form** shows 3, 4, 12 (group `self`) — there are no criteria in group `general`
  at all, because every non-self, non-c_level, non-project criterion is `managers_only`. It adds
  8 and 13 if the subject is a project participant, 2 if the subject has subordinates, and 1 and
  10 if the evaluator is admin or c_level.

### Descriptions, verbatim

**1 — Стратегическая значимость роли**
> `Оценка стратегической значимости для бизнеса компании. Определяет «вес» роли в цепочке создания стоимости. Оценивается насколько критична его функция для существования и прибыли бизнеса. Эта оценка устанавливается c-level менеджментом. Оценивается не только позиция, но и фактическая роль сотрудника и влияние на генерирование дохода.`

1 `Базовая поддержка (Уборка, охрана)` · 2 `Поддержка специалистов (Водители, ассистенты)` ·
3 `Линейное исполнение (Поддерживают процессы в рабочем состоянии).` ·
4 `Квалифицированный исполнитель (Специалисты, выполняющие стандартные задачи).` ·
5 `Основной бизнес-персонал. Те, кто непосредственно зарабатывает деньги или реализует продукт компании, но в рамках локальной ответственности.` ·
6 `Экспертный уровень. Специалисты, чья квалификация напрямую влияет на качество проектов и репутацию и генерацию дохода.` ·
7 `Ключевой специалист, эксперт и руководитель. Руководители отделов поддержки. Люди, которые организуют работу других или решают нестандартные задачи.` ·
8 `Руководитель направления существенно влияющего на генерацию прибыли, но не участвующий в коммерческой деятельности прямо.` ·
9 `Руководители, носители уникальных компетенций, определяющих конкурентное преимущество компании и оказывающие существенную роль на генерацию дохода.` ·
10 `Руководитель ключевого направления генерирующего доход  прямо участвующий в коммерческой деятельности.`

**2 — Качество управления и развитие команды**
> `Оценка управленческих компетенций. Умение добиваться результатов чужими руками. Оценивается: дисциплина исполнения, качество постановки задач, вовлечение сотрудников (объяснение "зачем"), наставничество, создание рабочей атмосферы без токсичности, а также обеспечение взаимодействия со смежными отделами.`

1 `Токсичный вредитель. Намеренно играет против интересов компании или руководства. Унижает сотрудников, создает интриги, присваивает чужие заслуги. Разрушает команду.` ·
2 `Некомпетентный руководитель. Полный хаос в задачах. Не пользуется уважением подчиненных. Игнорирует проблемы, допускает конфликты или сам их провоцирует. Результаты отдела систематически провальные.` ·
3 `Слабый авторитет / Популист. Идет на поводу у сотрудников в ущерб бизнесу ("хороший парень", но плохой начальник). Боится требовать дисциплины и качества. Задачи выполняются, только если сотрудники сами захотят.` ·
4 `Формальный администратор. Работает как "передатчик" задач сверху вниз без объяснений. Не вовлекается в проблемы сотрудников ("разбирайтесь сами"). Результат есть, но команда демотивирована, инициативы нет.` ·
5 `Ручной режим управления. Старается, но не умеет делегировать. Постоянно "тушит пожары" и делает работу за подчиненных. Контролирует каждый шаг (микроменеджмент), из-за чего тормозит процессы. Отдел держится на его личных переработках.` ·
6 `Эффективный операционный руководитель. Обеспечивает дисциплину и своевременное выполнение планов. Четко ставит задачи и контролирует результат. Требователен, но справедлив. Если сотрудник не справляется — помогает или учит.` ·
7 `Вовлекающий руководитель. Не просто спускает задачи, а объясняет контекст и решения руководства. Обеспечивает отличный сервис для внутренних и внешних клиентов. Активно взаимодействует со смежными отделами, устраняя барьеры.` ·
8 `Руководитель-наставник. Сильный лидер, транслирующий ценности компании. Системно растит замену и развивает сотрудников через обратную связь и менторство. Его команда показывает стабильно высокие результаты без авралов.` ·
9 `Автономный лидер. Построил систему, которая работает сама. Вырастил сильных замов. Мыслит интересами всей компании, а не только своего отдела. Его сотрудники — кадровый резерв для повышения.` ·
10 `Создатель лидеров (Role Model). Эталон управления в компании. Создал "школу кадров": его бывшие подчиненные успешно руководят другими подразделениями. Обеспечивает исключительную лояльность команды и сверх-результаты.`

**3 — Личная результативность и эффективность**
> `Оценка личной результативности и профессионального поведения. Фокус не только на «что сделано», но и «как сделано». Оценивается: качество, соблюдение сроков, инициатива, самостоятельность в решении проблем («приносит решения, а не проблемы»), готовность брать ответственность и выходить за рамки инструкций ради общего дела.`

1 `Деструктивное отношение. Открытый саботаж, токсичность к клиентам или коллегам. Категорический отказ выполнять задачи («это не входит в мои обязанности»). Грубые ошибки, наносящие ущерб репутации.` ·
2 `Критическая некомпетентность. Регулярно повторяет одни и те же ошибки. Результат работы требует полной переделки руководителем. Постоянные жалобы от клиентов или смежников. Полная пассивность.` ·
3 `Позиция «Жертва». При любой сложности ищет оправдания («меня не обучили», «мне не сказали»). Выполняет работу формально, без интереса к результату. Требует постоянного контроля («пинка»), чтобы начать делать.` ·
4 `Нестабильный исполнитель. Чередует нормальную работу с провалами. Пасует перед трудностями, возвращая обезьяну руководителю. Не проявляет инициативы, делает строго от и до.` ·
5 `Исполнитель с оговорками. В целом справляется, но требует регулярного внимания. Не хватает автономности: останавливается при возникновении препятствий и ждет указаний. Ошибки редки, но нет стремления сделать лучше.` ·
6 `Качественный профи (Нижняя граница нормы). Надежный сотрудник. Выполняет задачи качественно и в срок без напоминаний. Внимателен к деталям. С ним комфортно работать, он закрывает свой участок, но редко выходит за его рамки.` ·
7 `Проактивный профессионал. Не просто делает работу, а проявляет неравнодушие. Если видит проблему — сигнализирует или исправляет. Помогает коллегам, берет дополнительные задачи. Работает на опережение.` ·
8 `Лидер задач (Problem Solver). Приносит руководителю решения, а не проблемы. Берет на себя ответственность за сложные, нестандартные ситуации. Высокая автономность: ему можно поручить задачу и забыть, зная, что она будет сделана отлично.` ·
9 `Драйвер изменений. Инициировал и реализовал улучшения, которые сэкономили ресурсы или ускорили процессы компании. Демонстрирует высокий лидерский потенциал, ведет за собой других в сложных ситуациях.` ·
10 `Game Changer (Исключительный вклад). Совершил профессиональный подвиг в рамках года. Спас критический проект, закрыл невозможную сделку или внедрил инновацию, изменившую работу отдела. Результат превзошел самые смелые ожидания.`

**4 — Надежность и взаимодействие с руководителем**
> `Оценка «управленческой стоимости» сотрудника. Насколько руководителю комфортно и легко работать с сотрудником. Оценивается: уровень доверия, автономность, готовность подставить плечо в задачах отдела (даже вне прямых обязанностей) и отсутствие необходимости в микроменеджменте. Сотрудник либо экономит время руководителя, либо тратит его.`

1 `Крайняя ненадежность. Руководитель не доверяет сотруднику. Постоянное скрытие проблем, перекладывание вины или токсичность. Взаимодействие вызывает стресс и конфликты.` ·
2 `Высокая "управленческая стоимость". Руководитель вынужден тратить несоразмерно много времени на контроль и исправление ошибок за сотрудником. Проще сделать самому, чем поручить ему.` ·
3 `Пассивное сопротивление. Формально работает, но при любой дополнительной просьбе находит причины для отказа. Не проявляет интереса к целям отдела. Требует жесткого контроля на каждом этапе.` ·
4 `Исполнитель с контролем. Справляется с рутиной, но пасует перед сложностями или новыми задачами. Руководитель делегирует задачи с опаской, ожидая вопросов или ошибок.` ·
5 `Предсказуемый сотрудник. Работает ровно, но строго в рамках инструкций. На него можно положиться в стандартных вопросах, но он не готов брать ответственность за форс-мажоры или общие задачи отдела.` ·
6 `Надежная опора (Базовая норма). С сотрудником комфортно работать, он не создает проблем. Спокойно берется за задачи, важные для отдела, даже если они выходят за рамки привычного. Не требует перепроверки.` ·
7 `Автономный помощник. Понимает руководителя с полуслова. Сам видит, где в отделе "горит", и подключается без приказа. Разгружает руководителя от текучки, требуя минимального внимания.` ·
8 `Доверенное лицо. Руководитель полностью доверяет ему сложные участки. Сотрудник готов разделить ответственность за результаты отдела. В отсутствие начальника способен подхватить управление процессами.` ·
9 `Внутренний эксперт-советник. Руководитель регулярно советуется с сотрудником при принятии решений. Он видит картину шире своей должности и действует в интересах всего подразделения проактивно.` ·
10 `Партнерская позиция. Уровень взаимодействия "Партнер". Действует так, как действовал бы сам руководитель. Абсолютная надежность и лояльность. Незаменим для функционирования отдела.`

**8 — Взаимодействие и надежность в проекте**
> `Оценка работы в проектных командах (в т.ч. на объектах). Оценивается вклад в общий результат, а не только выполнение своей функции. Ключевые факторы: готовность выходить за рамки роли (например, помогать на монтаже), предвосхищение проблем, предложение решений, качественная передача информации смежникам и конструктивное поведение в стрессовых условиях (командировки, стройка). Оцениваются только участники проектов.`

1 `Деструктивное поведение. Саботаж работы на объекте. Создание конфликтов, отказ помогать коллегам в критической ситуации. Токсичность, деморализующая команду в командировке.` ·
2 `Узколобый формализм ("Не моя работа"). Категорически отказывается выходить за рамки должностной инструкции, даже если проект горит. Игнорирует проблемы смежников. На стройке ведет себя как сторонний наблюдатель.` ·
3 `Пассивный участник / Прокрастинатор. Ждет прямых указаний, сам инициативу не проявляет. В сложной ситуации теряется или устраняется. Создает "узкие горлышки" в коммуникации, задерживая информацию.` ·
4 `Исполнитель своей функции. Качественно делает свой участок, но не смотрит по сторонам. Если видит ошибку коллеги или риск — может промолчать. Взаимодействие ограничено передачей результатов.` ·
5 `Контактный исполнитель. Поддерживает нормальную связь, но не берет на себя лишнего. Помогает, только если попросят лично. Надежен в своей зоне, но не является драйвером общего процесса.` ·
6 `Надежный партнер (Норма). Не просто передает информацию, а убеждается, что коллега её понял и принял. Готов подставить плечо и помочь руками на объекте, даже если это не его прямая задача. Не создает проблем.` ·
7 `Активный участник. Работает на опережение: видит риски и заранее предупреждает руководство или смежников. Предлагает варианты решений при накладках. Способствует слаженной работе разных функций (монтаж/логистика).` ·
8 `Координатор решений. В полевых условиях берет на себя ответственность за стыковку процессов. Находит выход из тупиковых ситуаций, предлагает альтернативы. Активно помогает коллегам, поддерживая темп работ.` ·
9 `Системный интегратор. Своим участием "склеивает" проект. Устраняет межфункциональные барьеры. Его рекомендации существенно улучшили ход работ или сэкономили бюджет. Лидер на площадке де-факто.` ·
10 `Ключевой фактор успеха. Обеспечил бесшовное взаимодействие в сложнейших условиях. Взял на себя критическую нагрузку сверх роли. Без его вклада и решений проект мог бы остановиться или потерять качество.`

**10 — Оценка C-Level и соответствие культуре**
> `Оценка сотрудника высшим руководством. Требует выслушать мнение взаимодействующих с сотрудником коллег и наложить собственное мнение. Учитывает: уровень доверия, соответствие корпоративным ценностям (ДНК компании) и видимость успехов сотрудника для топ-менеджмента. Показывает, считает ли руководство сотрудника своим кадровым активом.`

1 `Крайне негативная репутация (Токсичный актив). Известен руководству только по скандалам, конфликтам или грубым ошибкам. Воспринимается как кадровый балласт. C-Level считает его найм ошибкой.` ·
2 `Проблемная зона. Руководство регулярно получает сигналы о неэффективности или сложном характере сотрудника. Есть сомнения в его соответствии корпоративной культуре.` ·
3 `Низкое доверие. Руководство не уверено в компетентности сотрудника. Требуется внимание к его участку, так как нет гарантии стабильного результата.` ·
4 `Отсутствие информации. Топ-менеджмент не знает сотрудника или не видит результатов его работы. Вклад в общее дело неочевиден для руководства.` ·
5 `Закрытая функция. C-Level знает, что позиция занята и там нет острых проблем, но личность сотрудника и его достижения руководству неизвестны.` ·
6 `Подтвержденная компетентность (Норма). Руководство знает сотрудника как надежного специалиста. Есть уверенность, что на его участке "всё в порядке". Вопросов к качеству нет.` ·
7 `Заметные успехи. Сотрудник периодически отмечается руководством за качественную работу или правильное поведение в сложных ситуациях. Репутация крепкого профессионала.` ·
8 `Высокий потенциал (HiPo). C-Level видит в сотруднике носителя ценностей компании. Его рассматривают как надежного члена команды и кандидата на рост.` ·
9 `Экспертное доверие. Топ-менеджмент обращается к сотруднику за мнением или советом при принятии решений, минуя иерархию. Ему доверяют конфиденциальные или сложные задачи.` ·
10 `Стратегический партнер. Полное доверие. C-Level воспринимает сотрудника как "своего человека", разделяющего ответственность за бизнес. Его мнение весомо влияет на решения компании.`

**12 — Профессиональное развитие и обмен знаниями**
> `Оценка желания сотрудника расти и развивать других. Критерий задает вектор на будущее: в компании ценится не только накопление экспертизы, но и обязательная передача знаний. "Закрытость" и отказ учить коллег расцениваются негативно. Оценивается самообразование, проведение внутренних тренингов, написание инструкций и освоение новых направлений.`

1 `Токсичный эксперт ("Черный ящик"). Намеренно скрывает знания, чтобы казаться незаменимым. Отказывается обучать других. Либо полная профессиональная деградация и потеря квалификации.` ·
2 `Сопротивление новому. Активно саботирует внедрение новых инструментов или методик. Работает "по старинке", игнорируя требования времени. Отказывается от обучения.` ·
3 `Пассивный потребитель. Посещает обучение только по принуждению ("из-под палки"). Знания не применяет. Информацией с коллегами не делится, занимает позицию "меня это не касается".` ·
4 `Минимальное развитие. Обучается только в рамках обязательных требований. Знаниями делится неохотно, только по прямому запросу. Инициативы в росте нет.` ·
5 `Поддержание статуса-кво. Владеет необходимыми навыками для текущей работы, но не стремится узнать больше. Помогает коллегам только в простых вопросах. Не выходит за рамки привычного.` ·
6 `Самостоятельный ученик (Базовая норма). Не ждет пинка: сам изучает мануалы, разбирается в новом оборудовании/ПО на практике. Открыт к вопросам коллег, никогда не отказывает в профессиональном совете.` ·
7 `Инициативный профи. Глубоко изучил новое направление или сложный инструмент за прошедший период. Активно транслирует опыт: пишет памятки, делится лайфхаками в чатах, помогает новичкам адаптироваться.` ·
8 `Внутренний тренер. Системно занимается развитием команды. Провел не менее 2-х обучающих мероприятий (тренинги, семинары) для коллег за период. Разработал качественные инструкции или регламенты.` ·
9 `Эксперт-новатор. Внедрил передовую практику или технологию, которой раньше не было в компании. Его экспертиза существенно повысила эффективность работы всего отдела.` ·
10 `Двигатель прогресса / Гуру. Создал уникальную базу знаний или систему наставничества, которая стала активом компании. Признанный авторитет, который выращивает лидеров и экспертов.`

**13 — Объем проектной работы и загрузка**
> `Количественная оценка вклада. Учитывает фактический объем выполненных задач и время, проведенное на объектах. Позволяет дифференцировать сотрудников с полной проектной загрузкой (длительные командировки) от консультантов и временных участников.`

1 `Минимальное участие. Удаленные консультации, решение разовых вопросов. Без выездов на объект.` ·
2 `Эпизодическое участие. Краткосрочное подключение к задаче. Вклад в общий объем работ незначителен.` ·
3 `Вспомогательная роль. Периодическая помощь по запросу или короткие, редкие выезды. Выполнение небольшого изолированного участка работ.` ·
4 `Частичная занятость. Регулярная работа над проектом, но с совмещением других обязанностей. Время на объекте ограничено (менее 30%).` ·
5 `Средняя загрузка. Выполнение своего блока работ в стандартном графике. Присутствие на объекте только по необходимости.` ·
6 `Высокая загрузка (Норма). Полноценная работа в проекте. Длительные командировки, нахождение на объекте большую часть времени. Выполнение основного объема задач.` ·
7 `Значительный объем. Плотная работа на объекте. Закрытие крупного и сложного блока работ. Высокая плотность задач.` ·
8 `Высокая интенсивность. Длительное непрерывное нахождение на объекте или работа в условиях сжатых сроков. Выполнен объем работ выше среднего.` ·
9 `Сверхнагрузка. Выполнение объема работ за нескольких специалистов или совмещение ролей. Работа в режиме постоянного аврала на объекте.` ·
10 `Максимальный вклад. Сотрудник выполнил ключевой объем физических или организационных работ по проекту. Рекордная длительность пребывания на объекте и максимальная выработка.`

### The scale as presented

The control is a 1–10 slider. Empty state: `Выберите оценку от 1 до 10`. Selected state:
`{score}/10`. Below it the chosen level's `level_N_desc` text, with fallback
`Оценка {N} из 10` (`src/utils/evaluationUtils.js:157-161`) or, in the self-review modal,
`Описание для этого уровня не задано`.

Anchor labels, `src/utils/evaluationUtils.js:142-149`:

| Range | Label | Colour |
|---|---|---|
| unset | `Не оценено` | grey |
| 1–3 | `Зона риска` | red |
| 4–6 | `Зона нормы` | yellow |
| 7–8 | `Зона роста` | green |
| 9–10 | `Зона исключительности` | purple |

A second, **conflicting** four-band scheme exists in `src/config/constants.js:91-96` —
`Критический` 1–3, `Ниже ожиданий` 4–5, `Соответствует` 6–7, `Превосходит` 8–10 — with
different boundaries and different names. It is exported but never imported anywhere; the
product uses the `evaluationUtils` version only.

A third scheme lives in `src/components/admin/ScoreDetailModal.jsx:92-98` and is what
admins/C-level actually read in the matrix: `Критично` <3, `Требует улучшения` 3–4,
`Хорошо` 5–7, `Отлично` ≥8.

---

# 4. Executor observations

Labelled as required. These are HR-process judgements on top of the factual material above,
not additional scope. Nothing here was fixed.

## 4.1 There is no "publish" moment — the system has no concept of period close for visibility

I searched for a visibility gate keyed to `period.status` and found none. Every score becomes
visible to everyone entitled to see it the instant it is written. In practice that means a
C-level writer sees a manager's rating before the manager has finished the team, and a
manager-of-manager can correct a score the same minute it lands. There is no calibration
window, because there is no state in which scores are complete-but-not-yet-actionable.

For H1 this is survivable if calibration is run as a meeting rather than as a system state.
It should not survive into Phase 3.

## 4.2 The mid-level correction surface is not reachable from the UI

`/team-scores` (`ManagerSubordinatesMatrix`) is the only place a manager-of-managers can enter a
`mid_level` correction. Its sidebar entry is gated on `safeUser.has_manager_subordinates`
(`src/components/Sidebar.jsx:203,206`). That property is never written into the user object —
login stores a fixed field list, `UserContext` just rehydrates it, and the only assignment of
`has_manager_subordinates` in the codebase is `ManagerSubordinatesMatrix.jsx:493` passing
`{...user, has_manager_subordinates: true}` down into its own child modal.

Consequence: **the two-level correction described on `/welcome`
(`Старший менеджер может поставить вам свою оценку…`) has no entry point in the navigation.**
The route works if you type the URL. `ScoreDetailModal`'s `canCorrect` check
(line 45) reads the same missing flag, so even a manager who reaches the page by URL gets the
correction block only through the `has_manager_subordinates: true` that page injects.

Practical effect for H1: mid-level corrections will not happen unless someone is told the URL.

## 4.3 The manager form shows the manager their own self-review, labelled as the subordinate's

Full mechanism in §3.2. In HR terms this is the most damaging bug in the list, because it does
not fail loudly — it silently anchors every manager to their own numbers while they rate
someone else, and the free-text `Комментарий сотрудника: "…"` makes it look authoritative. A
manager who scored themselves 8 will see "8" next to their subordinate's name on every shared
criterion.

It also means the answer to the brief's question "can a manager see the subject's self-review"
is: **no, and worse than no.**

## 4.4 A plain manager's dashboard reports every subordinate as having done nothing

`useDashboardData` (`src/hooks/useDashboardData.js:54`) fetches `/api/hr/evaluation-status` with
`.catch(() => ({ data: { employees: [] } }))`. That endpoint's guard is
`required_roles: ["hr","admin","c_level"]`, so a manager gets 403 and the map stays empty. Every
`EmployeeCard` therefore renders `Самооценка` and `Оценка рук-ля` in the grey "not done" state
regardless of reality (`src/components/EmployeeCard.jsx`).

Managers will chase people who have already finished, and HR will field the complaints.

## 4.5 Read-only C-level are read-only only in the evaluation forms, not in corrections

`can_evaluate = false` blocks `/api/employees` and the evaluation submit path. It does **not**
appear anywhere in `API: Score Correction`, whose `Decide Level` node grants
`correctionLevel = 'c_level'` to anyone with `role in ('admin','c_level')`. Cem, Hemra and
Mekan can therefore write `c_level` corrections on any subject, from `/admin/evaluations-matrix`,
which they can reach.

If "read-only" is a governance commitment rather than a convenience, this is a gap.

## 4.6 Every employee can read the C-level criteria and every level description

`API: Get Criteria With Levels` has `required_roles: []` and its query is a bare
`SELECT … FROM performance_db.criteria ORDER BY id ASC` with no filter on `c_level_only`. So the
response any logged-in employee receives contains criterion 1 `Стратегическая значимость роли`
with level 1 = `Базовая поддержка (Уборка, охрана)` and level 10 =
`Руководитель ключевого направления генерирующего доход…`, and criterion 10
`Оценка C-Level и соответствие культуре` with level 1 =
`Крайне негативная репутация (Токсичный актив)`.

The UI half-hides this: `CriteriaOverview` renders the C-level group's titles and descriptions
but passes `showLevelDescriptions=false`, and `/welcome` says
`C-level менеджеры оценивают вас по специальным критериям, доступным только для руководства компании.`
That sentence is false as stated — the criteria are not access-controlled, only their level
texts are visually collapsed — and the raw text is one network-tab click away.

Separately: telling employees that a criterion exists which ranks their role from "cleaning and
security" to "revenue-generating executive", with a weight of 5.0 (the highest in the
catalogue), while describing it as "for management only", is a conversation that will happen
whether or not it is planned for.

## 4.7 Confidentiality is enforced in the browser, not on the server

Three claims made in `/welcome` — that the manager does not see upward scores, that only C-level
see the data, and that detailed results are admin-only — are implemented as conditional
rendering. `API: My Profile V5` returns `calculated_score` and `weighted_score` for every
evaluation where the caller is the subject, including `subordinate`-source rows, and
`API: Get Evaluation Details FIXED` will hand the same caller the per-criterion breakdown and
visible comments for any `evaluation_id` from that list. Only `private_comment` and the upward
rater's name are gated server-side.

The `Детали оценки недоступны` /
`Вы можете видеть только факт того, что менеджер провел оценку. Детальные результаты доступны только администраторам.`
modal is therefore an assertion about the UI, not about the system. In a company where at least
some staff are technical, I would not rely on it holding for a full H1 cycle.

## 4.8 Copy that contradicts behaviour, in one list

| Where | What it says | What actually happens |
|---|---|---|
| `Welcome.jsx` | `Оценка вашего менеджера остается анонимной - он не видит конкретные баллы` | the rated manager's own `/api/my-profile` response contains the upward `calculated_score`; only the name is redacted |
| `Welcome.jsx` | `Все данные видят только C-level менеджеры` | admin, HR (status), and manager-of-manager (`/team-scores`) also see data |
| `Welcome.jsx` | `Критерий для оценки руководителя` used as if it were the criterion's name | the criterion is called `Качество управления и развитие команды`; no criterion in the catalogue has that name |
| `Welcome.jsx` | `C-level менеджеры оценивают вас по специальным критериям, доступным только для руководства компании` | `/api/criteria` serves them to every authenticated user |
| `EvaluationDetailsModal.jsx` | `Детальные результаты доступны только администраторам` | the subject's own API response carries them |
| `SelfReview.jsx` | `Самооценка проводится ОДИН РАЗ и не подлежит пересмотру` | true, but `SelfReviewStatusCard` also offers `Оценить новые критерии`, which always returns 409 |
| `SelfReviewStatusCard.jsx` | `Оценить новые критерии` | `API: Submit Self Review` ignores `is_update`; the button cannot succeed |
| `ManagerEvaluation.jsx` | `Руководитель не назначен` / `Обратитесь к HR-отделу для уточнения информации.` | shown to Cem/Hemra/Mekan, who correctly have no manager, and to read-only C-level whose task loader 403'd |
| `SessionExpiryWarning.jsx` | `незавершённая оценка сохранится локально` | true for self-review, upward, and manager forms; the user is not told the draft is browser-local and expires in 7 days |
| `Login.jsx` | placeholder `name@company.com` | registration and password reset both require `@sedamedical.com` |

## 4.9 Language mixing, summarised

Russian is the product language. English leaks in at five points a user can reach:

1. every backend error that survives the interceptor — 400/404/409/422 — e.g.
   `Self-review already exists for this period`, `Token is invalid or expired`,
   `Invalid code. {remaining} attempts remaining.`
2. `Evaluation already exists for this evaluator/subject/source/period tuple. Use /api/update-evaluation.` —
   an API path shown to a manager in a native `alert()`
3. the login page title `Evaluation Portal` and the sidebar product name
   `Evaluation Performance Portal`
4. `Grade: {code}` on every employee card, `Mid-level` and `C-level` as correction labels
5. success strings the frontend happens to override today
   (`Registration successful! You can now login.`, `Password reset successful. Please sign in again.`,
   `If the account exists, a reset link has been sent.`) — these are one refactor away from
   surfacing

## 4.10 Smaller things worth recording

- The self-review commitment warning appears on the landing card but **not** in the confirmation
  dialog. The dialog is where the decision is actually made.
- `Вам доступно {n} … для оценки. Это займет не более 5-10 минут.` — the self-review is three
  criteria. 5–10 minutes is roughly ten times the honest estimate, which trains people to expect
  every other estimate in the product to be wrong.
- The self-review warning tells employees that `85-90% сотрудников попадают в желтую и зеленую зоны`.
  Yellow is `Зона нормы` 4–6 and green is `Зона роста` 7–8, so the sentence quietly defines the
  expected distribution as 4–8. Nothing enforces it and nothing reports against it.
- `Профиль` never shows the subject their own weighted score; `ProfileEvaluationsTable` prints
  `Взвешенный: {n}` only for admin/c_level. Since the grade coefficient is not applied on the
  client anyway (the login payload has `grade_id` but no `grade_coefficient`, so
  `calculateWeightedScore` defaults to 1.0), the weighted column currently equals the plain
  average for everyone.
- `EmployeeCard` prints `Критерии оценки:` counts including `C-level: {n}`, so a manager sees
  that C-level criteria exist for their subordinate even though they cannot open them.
- `groupCriteria`'s `general` bucket is empty for the current catalogue, so the manager form's
  `📋 Общие критерии` / `Оценка руководителя` section never renders. Harmless, but the group
  header text was written for a catalogue that no longer exists.
- No criterion has `level_0_desc`, yet the slider utilities, the matrix query, and the criteria
  API all carry level 0. A score of 0 is not reachable from the UI (`min="1"`), so this is dead
  surface rather than a live risk.
- `/reset-password` with no token renders the whole form and only fails at submit. The message
  it then shows, `Ссылка для сброса пароля недействительна.`, does not tell the user to request a
  new link.
