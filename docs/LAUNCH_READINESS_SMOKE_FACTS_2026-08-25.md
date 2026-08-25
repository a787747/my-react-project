# Launch readiness and smoke-test facts — H1 second gate (2026-08-25)

**Brief:** LAUNCH_READINESS_AND_SMOKE_FACTS. Read-only. Establishes facts, decides nothing,
changes nothing. No recommendation about pressing «Запустить оценку».

**Repository state this report was written against:** `35ef8843d51f312d498d2fcefa1f83b26a7ea2cf`
(«Remove five H1 level-6 norm labels on live through the admin route (D-0825-2)», 2026-08-25),
working tree clean at the start of the session.
**This report's own commit:** recorded at the end of §9.

**Outcome in one line: this session had no access to the live system, so no number in this
report is a live reading taken today — every live-state item is either "last measured on
<date> by a named earlier session" or "unknown", and everything that is stated as fact was
read out of the repository this session.**

---

## 0. Access — the constraint that shapes the whole report

This session runs in a Claude Code cloud container, not on the delivery Mac. Live could not
be reached by any route:

| Path tried | Result |
|---|---|
| SSH tunnel `epe-vps-tunnel` → `127.0.0.1:25432` | **No SSH client on the host** (`/usr/bin/ssh` absent) and `~/.ssh` is empty — no key, no config |
| `https://epe.sedamedical.com` (any GET) | **Blocked by the session egress policy.** `curl` → `CONNECT tunnel failed, response 403`; the proxy status endpoint records `{"kind":"connect_rejected","host":"epe.sedamedical.com:443","ts":"2026-08-25T11:29:12.682Z"}` |
| Local database | No Postgres on `127.0.0.1:5432` or `:25432`; no `.env` in the checkout |
| Docker | No daemon socket (`/var/run/docker.sock` absent) |

Per the proxy README this is an organisation egress denial, which must be reported rather
than routed around. Nothing was retried after the denial.

**Consequence:** items 1, 2, 8 and the identity half of item 5 are live-state questions and
are reported as *last measured* or *unknown*. Items 3 (wording), 4, 6, 7 and the rule half of
item 5 are answerable from the repository and were answered from it.

### How the workflow facts in this report were obtained

`AGENTS.md` says the tracked `n8n_workflows/` exports are untrusted and that live
`workflow_entity` is the truth. Live is unreachable, so the next-best in-repo source was used:
the **builder scripts**, regenerated this session into a scratch directory —

```
scripts/build_route_guard_workflows.py   → 17 definitions
scripts/build_route_guard_deferred.py    → 10 definitions
scripts/build_auth_workflows.py          →  6 definitions   (33 total, all generated cleanly)
```

These are the correct in-repo mirror because `scripts/check_live_drift.py` exists precisely to
diff *generator output* against live `workflow_entity` and fail on any difference. Three
independent corroborations that the generator set matches live:

1. Generated `API: Manage Periods` = **70 nodes / 8 webhook routes** — identical to HANDOVER §3's
   live measurement (`updatedAt=2026-08-24T06:10:13.683Z`, 70 nodes / 8 webhooks).
2. Comparing generator output to the tracked top-level exports gives **11 differing**; two of
   those (`API: Get Employee Self Review`, `API: Get Admin Data Fixed`) are the pair confirmed
   deleted from live, leaving **9 stale exports** — exactly BUG-045's count.
3. The generated `EPE: Auth Guard` matches the tracked export node-for-node and
   connection-for-connection, consistent with its frozen-since-18-Aug status.

This is still not a live read. Where it matters, the report says so.

---

## 1. Period id 2

Everything below is **last measured**, not read today.

| Field | Value | Source of the reading |
|---|---|---|
| `status` | `active` | live SELECT **2026-08-25T07:23:16Z** (`docs/CATALOGUE_FIX2_H1_2026-08-25.md` §4.5) |
| `is_active` | `true` | same |
| `evaluation_started_at` | **NULL** | same |
| activated at | 2026-08-24 **19:07:36Z** | HANDOVER §1 (`POST /webhook/api/periods/activate`, Caddy 200) |
| `start_date` … `end_date` | **2026-01-01 … 2026-06-30** | `docs/AUTHENTICATION_CORE_2026-08-18.md:62`; re-confirmed as the `/api/employees` payload in `docs/EMPLOYEES_PERIOD_META_2026-08-2x.md:97` |
| `period_type` | `half_year` | same |
| parent container | **id 5 «Annual 2026»** (`annual`, `draft`, 2026-01-01…2026-12-31, 1 child) | `docs/DOCS_HYGIENE_2026-08-24.md:54`; `docs/PERIODS_VERIFY_2026-08-2x.md:596` |
| participants | 89 total / **87 in scope** | `docs/DOCS_HYGIENE_2026-08-24.md:54`, HANDOVER §7 |

**Any other period active?** Last measured **no** — id 1 «Annual 2025» is `annual`/`closed`,
id 5 «Annual 2026» is `annual`/`draft` (2026-08-24). Independently of any reading, the database
makes two active periods impossible: migration 012 installs the partial unique index
`idx_evaluation_periods_single_active` and the CHECK
`chk_evaluation_periods_active_status_consistent` (`is_active = (status = 'active')`).

**Any period with `evaluation_started_at` set?** Last measured **no, on all three** (2026-08-24,
HANDOVER §3 — migration 014 landed with every existing period NULL and nothing retroactively
started). For id 2 specifically the NULL was re-measured at 2026-08-25T07:23:16Z.

**Current values: unknown.** The catalogue was still writable at 07:23Z, which means the gate
had not been pressed as of that moment; nothing in this session can speak for the hours since.

---

## 2. Row counts and registration

| Table | Last measured | When |
|---|---|---|
| `evaluations` | **0** | 2026-08-25T07:23:16Z (`CATALOGUE_FIX2` §4.5) |
| `evaluation_scores` | **0** | same |
| `score_corrections` | **0** | same |
| `period_results` | **0** | same |
| `auth_sessions` | **12** | same (§3 and §4.5: "12 → 12", probe row created and deleted in a `finally`) |

**Which accounts have completed registration: unknown.** The last recorded count is
**registered = 2** (`docs/PRELAUNCH_FIXES_2026-08-2x.md:167`, work dated 2026-08-20), explicitly
noted there as pre-existing rather than created by that brief. No later report re-measures it.
Do not read the six-role live probe (`PROGRESS.md:846`) as evidence of five more registrations —
`scripts/probe_live_coeff_roles.py:122` mints its own JWTs and `INSERT`s the `auth_sessions`
rows directly by SQL, so it proves nothing about `password_hash`.

**"and when" cannot be answered at all, by anyone.** There is no registration timestamp
anywhere in the system:

- `is_registered` is a derived boolean — `(u.password_hash IS NOT NULL) AS is_registered`
  (`scripts/build_route_guard_workflows.py:2857`, served on `/api/admin-users-data`).
- No `registered_at` / `password_set_at` column exists in `schema.sql`, in `migrations/001…014`,
  or in `scripts/import_epe_2026.py`.
- `users.created_at` is the import date, not the registration date.
- The nearest proxy is the earliest `auth_sessions.created_at` for that user — but that records
  a **login**, not a registration, and those rows are freely deletable.

This is a real gap, not a measurement problem: if the owner wants "who registered and when"
after the invitation goes out, the answer has to be built before it goes out, not afterwards.

---

## 3. The catalogue as it stands

### 3.1 The nine criteria

From `docs/catalogue/H1-2026_catalogue_after_20260825T072316Z.md` — a live
`SELECT` of all 9 rows and all columns at **2026-08-25T07:23:16.687383Z** (server clock). The
file's md5 was recomputed this session as `e5306c2483ebf19a6e0944f78327b43f`, which matches the
md5 the FIX2 report certifies in its closing table.

| id | name | weight | target_audience | c_level_only | for_manager | selfassesment |
|---|---|---|---|---|---|---|
| 1 | Стратегическая значимость роли | 5.00 | `all` | true | false | false |
| 2 | Качество управления и развитие команды | 3.00 | `managers_only` | false | true | false |
| 3 | Личная результативность и эффективность | 3.00 | `all` | false | true | true |
| 4 | Надежность и взаимодействие с руководителем | 1.50 | `all` | false | true | true |
| 8 | Взаимодействие и надежность в проекте | 1.40 | `project_participants` | false | true | false |
| 10 | Оценка C-Level и соответствие культуре | 1.60 | `all` | true | false | false |
| 12 | Профессиональное развитие и обмен знаниями | 1.00 | `all` | false | true | true |
| 13 | Объем проектной работы и загрузка | 1.80 | `project_participants` | false | true | false |
| 14 | Ответственность сверх роли | 1.50 | `all` | false | true | false |

### 3.2 Criterion 13 and criterion 8 — the brief's premise needs correcting

The brief asks whether live holds the **pre- or post-FIX2** wording for criterion 13
(description + levels 4–10) and criterion 8 (description). **Those fields were not touched by
FIX2.** Diffing the four snapshots gives the exact deltas:

- **FIX1** (`before 06:25:07Z` → `after 06:26:01Z`) changed **20 text fields**, and those 20
  include criterion 13's `description` + `level_4_desc`…`level_10_desc` (8 fields) and
  criterion 8's `description`. The rest: criterion 2 `level_10`, criterion 3
  `description`/`level_7`/`level_10`, criterion 4 `description`/`level_6`/`level_10`, criterion 8
  `level_10`, criterion 10 `level_10`, criterion 12 `level_8`, criterion 14 `level_2`.
- **FIX2** (`before 07:22:39Z` → `after 07:23:16Z`) changed **exactly 5 fields**, all of them
  `level_6_desc`, on criteria 3, 4, 8, 10, 12 — and nothing else.

The FIX2 before-snapshot is byte-identical to the FIX1 after-snapshot apart from the header line
and its timestamp (verified this session by `diff`). So for criterion 13 and criterion 8's
description, **the pre- and post-FIX2 texts are the same text** — the pre/post-FIX2 question has
no answer because there is no difference to detect. The meaningful question for those fields is
pre- or post-**FIX1**, and the last live reading (07:23:16Z) holds the **post-FIX1** wording.

Whether live still holds it **today** is unknown. The catalogue is writable until the gate is
pressed, so an owner edit since 07:23Z would not be visible from here.

### 3.3 The five level-6 norm labels — removed, verbatim both sides

Last live reading (07:23:16Z): **the norm labels are gone from all five.** Quoted verbatim.

**Criterion 3 «Личная результативность и эффективность»**
- before: `Качественный профи (Нижняя граница нормы). Надежный сотрудник. Выполняет задачи качественно и в срок без напоминаний. Внимателен к деталям. С ним комфортно работать, он закрывает свой участок, но редко выходит за его рамки.`
- **on live:** `Качественный профи. Надежный сотрудник. Выполняет задачи качественно и в срок без напоминаний. Внимателен к деталям. С ним комфортно работать, он закрывает свой участок, но инициативу сверх этого проявляет редко.`

**Criterion 4 «Надежность и взаимодействие с руководителем»**
- before: `Надежная опора (Базовая норма). С сотрудником комфортно работать, он не создает проблем. Спокойно берется за задачи, важные для отдела. Не требует перепроверки.`
- **on live:** `Надежная опора. С сотрудником комфортно работать, он не создает проблем. Спокойно берется за задачи, важные для отдела. Не требует перепроверки.`

**Criterion 8 «Взаимодействие и надежность в проекте»**
- before: `Надежный партнер (Норма). Не просто передает информацию, а убеждается, что коллега её понял и принял. Готов подставить плечо и помочь руками на объекте, даже если это не его прямая задача. Не создает проблем.`
- **on live:** `Надежный партнер. Не просто передает информацию, а убеждается, что коллега её понял и принял. Готов подставить плечо и помочь руками на объекте, даже если это не его прямая задача. Не создает проблем.`

**Criterion 10 «Оценка C-Level и соответствие культуре»**
- before: `Подтвержденная компетентность (Норма). Руководство знает сотрудника как надежного специалиста. Есть уверенность, что на его участке "всё в порядке". Вопросов к качеству нет.`
- **on live:** `Подтвержденная компетентность. Руководство знает сотрудника как надежного специалиста. Есть уверенность, что на его участке "всё в порядке". Вопросов к качеству нет.`

**Criterion 12 «Профессиональное развитие и обмен знаниями»**
- before: `Самостоятельный ученик (Базовая норма). Не ждет пинка: сам изучает мануалы, разбирается в новом оборудовании/ПО на практике. Открыт к вопросам коллег, никогда не отказывает в профессиональном совете.`
- **on live:** `Самостоятельный ученик. Не ждет напоминаний: сам изучает мануалы, разбирается в новом оборудовании/ПО на практике. Открыт к вопросам коллег, никогда не отказывает в профессиональном совете.`

Strength of the "on live" claim: the FIX2 report records an independent `GET /api/criteria`
(the forms' own read route) returning all five new strings, plus a further direct SELECT after
teardown — so it was not a write-cache artefact. Two labels survive **outside** the database:
`src/pages/GuidePreview.jsx:22` still quotes «Качественный профи (Нижняя граница нормы)», but it
is a `import.meta.env.DEV` fixture and is not in the production route table; and the historical
reports keep the old wording by design.

---

## 4. What the second gate changes — read from the workflow graphs

Answers below come from the regenerated definitions (§0), not from the docs.

### 4.1 Which writes change behaviour, in both directions

Only ten of the 33 definitions mention `evaluation_started_at` at all. Grouped by what pressing
the gate does to them:

**A — 409 today, accepted after the gate** (these are what the campaign is waiting on):

| Workflow / route | Refusal today |
|---|---|
| `API: Submit Evaluation` (`POST api/submit-evaluation`) | 409 `PERIOD_NOT_STARTED` — «Оценка ещё не запущена: период в подготовке» |
| `API: Submit Self Review` (`POST api/self-review-submit`) | 409 `PERIOD_NOT_STARTED` — same message |
| `API: Update Evaluation WITH PERIOD` (`POST api/update-evaluation`) | 409 `PERIOD_NOT_STARTED` — «Оценка ещё не запущена или период больше не активен» |
| `API: Score Correction` (`POST api/admin/score-correction`) | 409 `NO_ACTIVE_PERIOD` — «Корректировка доступна только в идущем периоде оценки (период активирован и оценка запущена)» |

**Correction to the brief's premise:** corrections do **not** "stay open" across the gate. Their
period lookup requires `p.evaluation_started_at IS NOT NULL`, so score-correction is *closed
now* and the gate is what *opens* it.

**B — accepted today, 409 after the gate** (this is the only thing the gate freezes):

| Workflow / route | Refusal after the gate |
|---|---|
| `API: Manage Criteria Admin V7` (`POST manage-criteria`) | 409 `EVALUATION_STARTED` — «Нельзя менять критерии: оценка в периоде «<name>» уже идёт» |

**C — the gate does not reach them at all.** Zero references to `evaluation_started_at` /
`evaluation_started_by` in these graphs:

- **Coefficients:** `API: Save Score Coefficients` (`POST api/score-coefficients`) — weights and
  level coefficients.
- **Grade coefficients:** `API: Update Admin Data` (`POST update-admin-data`).
- **Classification:** `API: Admin Save User (GUI Mode)` (`POST admin/save-user`).
- **Registration and authentication:** Register, Auth Login, Request Password Reset, Reset
  Password, Create Invite, and `EPE: Auth Guard` itself.
- **All reporting and admin reads:** all-evaluations, analytics, evaluations-matrix,
  manager-subordinates-matrix, evaluation-details-by-user, HR evaluation status,
  admin-users-data, my-profile, evaluation history, get-evaluation-details, `GET api/criteria`,
  `GET api/score-coefficients` — these stay keyed on **active** alone.

Corroborating that C is a real state and not an oversight: both legacy freeze codes,
`ACTIVE_PERIOD_EXISTS` and `CLASSIFICATION_FROZEN`, are **absent from all 33 definitions** — the
freeze nodes were removed from the graphs, not bypassed (D-0822-2, D-0822-3).

### 4.2 What the gate does NOT do

- Does not change scope or participants — `evaluation_period_participants` is untouched.
- Does not freeze weights, level coefficients or grade coefficients; those stay writable until
  close, with per-value validation instead of a 409.
- Does not freeze the project/general classification.
- Does not touch registration, login, invites or password reset.
- Does not close anything and does not write `period_results`.
- Does not affect admin/reporting reads.
- A second press is a no-op: 200 `already_started`, **zero rows written**.
- It refuses, in this order: 422 `INVALID_PERIOD_ID` → 404 `PERIOD_NOT_FOUND` → 422
  `CONTAINER_NOT_STARTABLE` (any child) → 422 `ANNUAL_PERIOD_NOT_STARTABLE` → 422
  `PERIOD_CLOSED` → 422 `PERIOD_NOT_ACTIVE` → 200 `already_started`. A lost race on the gated
  `FOR UPDATE` statement answers 409 `START_CONFLICT` and changes nothing.

### 4.3 Is there any route that unsets `evaluation_started_at`?

**No.** The single assignment in the entire generated set is in `API: Manage Periods`, node
`Build Start SQL`:

```sql
UPDATE performance_db.evaluation_periods p
SET evaluation_started_at = now(),
    evaluation_started_by = <actor_id>
FROM target t WHERE p.id = t.id
```

guarded by a `FOR UPDATE` CTE that re-asserts `status='active' AND is_active=true AND
period_type != 'annual' AND evaluation_started_at IS NULL AND NOT EXISTS (children)`. The close
route does not clear the mark; nor does activate, rename, reparent, or create.

The only `evaluation_started_at = NULL` statements anywhere in the repository are in two proof
scripts — `scripts/prove_lifecycle_coeff.py:543` and `scripts/prove_empmeta.py:173` — which run
raw SQL against throwaway stand databases, not through any route. So the mark is irreversible at
product level, and recovery is a hand-written SQL statement (or a dump restore).

---

## 5. Valeriya Ruhlyadko, Nurmammet Hekimov, Jahan Hojayeva

### 5.1 Per-person facts: unknown

`user id`, `role`, `manager`, `direct reports`, `work_category` / `is_project_participant` and
`registration status` all live in `epe_2026.performance_db.users`, which is unreachable
(§0). **They are unknown and were not inferred.** No roster carrying live ids exists in the
repository: `scripts/import_epe_2026.py` reads an `.xlsx` that is not tracked, and
`public/шаблон_импорта_сотрудников.xlsx` is a blank template.

What the repository does say, from `docs/INVITATION_WAVES.md` (dated 2026-08-19):

| Person | Recorded |
|---|---|
| **Nurmammet Hekimov** | `nurmammet@sedamedical.com` · Sales Manager of Clinical Lab Solutions · dept **Clinical Lab Solutions** · **Wave 1** |
| **Valeriya Ruhlyadko** | **Wave 2** (Clinical Lab Solutions employees). No email or title recorded |
| **Jahan Hojayeva** | **Wave 8**, **Lab Solution Division**. No email or title recorded |

Wave 1 is defined in that document as "everyone who evaluates or administers" and holds exactly
20 people, against a headcount of admin 1 + C-level 5 + manager 12 + HR 2 + employee 69. So
Hekimov is one of the **12 managers**, and the other two are in employee waves. That is an
inference from the wave structure, not a reading of `users.role`.

From the **2025 archive only** (`postgres.performance_db`, different id space — does not carry
into `epe_2026`): Jahan Hojayeva was manager id **172** and authored a `mid_level` correction on
Shasenem Tishkina; Valeriya Ruhlyadko was the subject of a `c_level` correction from evaluator 1
(`docs/CALCULATION_MAP.md:120`, `docs/CLEVEL_DIRECT_ENABLE_2026-08-2x.md:42-44`).

### 5.2 The criteria set per channel — the rule, fully established

The rule is in the catalogue flags plus `src/components/profile/CriteriaOverview.jsx:112-180`;
the server enforces applicability again at submit. With the nine live criteria of §3.1:

| Channel | Criteria |
|---|---|
| **self-review** | **3, 4, 12** (`selfassesment=true`, audience `all`) |
| **manager → subordinate** | **3, 4, 12, 14** · **+2** if the subject `has_subordinates` · **+8, 13** if the subject `is_project_participant` |
| **upward (subordinate → manager)** | same rule, subject = the manager |
| **c_level_direct** | **1, 10** (`c_level_only=true`) |

That rule reproduces HANDOVER's live distribution to the digit — 4 (general, no reports),
5 (general manager), 6 (project, no reports), 7 (project manager) — against the measured
**37 × 4, 11 × 5, 36 × 6, 5 × 7 = 89**. Which bucket each of the three falls in depends on their
live `is_project_participant` and `has_subordinates`, so **their exact sets are unknown.**

### 5.3 Can this trio exercise manager→subordinate, upward and self-review between them?

**Cannot be answered without one SELECT — but the condition is now exact.** From
`API: Submit Evaluation`, the relation filter per source is:

```
manager        →  subj.manager_id = <actor>  AND subj.can_be_evaluated = true
subordinate    →  actor.manager_id = <subject>  AND subj.can_be_evaluated = true
                  AND subj.role NOT IN ('c_level','admin')
c_level_direct →  actor.role IN ('c_level','admin')  AND subj.can_be_evaluated = true
```

plus, on every source, both actor and subject must be `is_in_scope = true` participants of the
period, and the period must be active **and started**. Self-review is a separate route; the
submit route answers 422 `SELF_EVALUATION_FORBIDDEN` if subject = actor.

Two consequences worth stating plainly:

1. **One single `manager_id` edge inside the trio delivers both directional channels.** If A is
   B's manager, A evaluates B (`manager`) and B evaluates A (`subordinate`). There is no need for
   two separate pairs.
2. **Self-review needs nothing but scope** — all three can do it regardless of hierarchy.

So the trio works **if and only if at least one of them is the direct manager of another** in
live `users.manager_id`. The repository's best evidence points at **Hekimov → Ruhlyadko** (he is
a Wave-1 manager in Clinical Lab Solutions; she is a Wave-2 Clinical Lab Solutions employee),
but this is **not verified**, and there is a live ambiguity: **Akmyrat Jumahanov** holds the
identical title in the identical department, so Ruhlyadko may report to him instead. Jahan
Hojayeva sits in a different division (Lab Solution Division) with no recorded edge to either —
on repo evidence she contributes a self-review only.

**Minimal substitution, if no edge exists** (surfaced, not resolved): keep Hekimov as the
manager and take the other two from his actual direct reports. The candidate pool in his
department (Wave 2) is Alina Naubatova, Asadbek Usmanov, Bezirgen Annameredov, Halykberdi
Orusov, Mahriban Ishanova, Muhammetberdi Garayev, Muhammet Gylyjov, Shasenem Tishkina, Valeriya
Ruhlyadko. One read settles the whole question:

```sql
SELECT id, full_name, email, role, manager_id, work_category,
       is_project_participant, has_subordinates,
       (password_hash IS NOT NULL) AS is_registered
FROM performance_db.users
WHERE full_name IN ('Valeriya Ruhlyadko','Nurmammet Hekimov','Jahan Hojayeva');
```

**One more thing the owner should see before choosing the three.** A live smoke test needs those
accounts registered, and the only route-based registration path emails a six-digit code to the
employee's real mailbox (`API: Send Verification Code` → `email_verification_codes`, consumed by
`API: Register`). That collides with `AGENTS.md` hard constraint 5 / D-0820-8. This exact
pattern was already run once, on 2026-08-20, with two real employees (Alina Naubatova,
Alp-Arslan Mametnazar) and fully rolled back — after which Alexander forbade repeating it
(`docs/SHARED_INVITE_2026-08-20.md` §4: "Do not repeat this proof pattern"). Whether the three
are already registered is exactly the unknown of §2.

---

## 6. Registration and authentication mechanics

### 6.1 What invite-link registration writes

`API: Register` (`POST api/register`), node `Hash Password` — one statement, three CTEs:

| Target | Written |
|---|---|
| `users.password_hash` | **the only column set**, guarded by `WHERE id = <user> AND password_hash IS NULL` |
| `email_verification_codes` | the used code row is **DELETEd** (consumed) |
| `invite_tokens` | **nothing.** The CTE is a bare `SELECT id … WHERE id = <invite> AND expires_at > now()` |

`is_used`, `used_by` and `used_at` are never written — D-0820-6 confirmed from the graph, not
from the docs. Preconditions, all in one JOIN: token matches `^[A-Za-z0-9_-]{16,128}$`, email
ends `@sedamedical.com` and matches a user row, password ≥ 8 characters, code matches `^\d{6}$`
with `is_verified = true` and unexpired, and the user's `password_hash IS NULL`.

### 6.2 How the password is stored

Node.js `crypto.scryptSync` with a fresh 16-byte random salt:

```js
crypto.scryptSync(password, salt, 64, { N: 16384, r: 8, p: 1, maxmem: 64*1024*1024 })
```

stored in `users.password_hash varchar(255)` as five `$`-separated fields:

```
$scrypt$N=16384,r=8,p=1$<salt base64url, 22 chars>$<derived key base64url, 86 chars>
```

— 133 characters. `API: Reset Password` produces the identical format.

### 6.3 Can an account be returned to "never registered" and re-register through token id 4?

**Yes, mechanically — and it has been done on live before.**

- *Returning:* set `users.password_hash = NULL`. **No route does this**; it is a hand-written
  SQL statement. (`API: Reset Password` overwrites the hash and bumps `token_version`; it never
  nulls it.)
- *Re-registering:* the token JOIN checks only `expires_at > now()`. The
  `AND COALESCE(is_used,false) = false` condition was **removed** on 2026-08-20 precisely so the
  company-wide link stays reusable, and the `UPDATE … SET is_used=true` CTE was replaced by a
  SELECT. A **fresh** verification code is required each time, because the previous code row is
  deleted at registration.
- *Token id 4:* recorded as base64url, 43 characters, `is_used=false`, unexpired, **valid to
  2026-09-18** (`docs/INVITATION_WAVES.md`, `docs/SHARED_INVITE_2026-08-20.md`). Because register
  never burns it, `API: Create Invite` will keep handing back **id 4** until that expiry —
  rotating the public link means expiring or marking that row by hand (BUG-008). **Its current
  state is unknown.**
- *Precedent:* on 2026-08-20 two employees registered back-to-back through id 4, `is_used`
  stayed `false`, and the rollback restored `registered = 1`.

### 6.4 What else a login leaves behind

`API: Auth Login (No Params)`:

- **On success:** `INSERT INTO auth_sessions (jti, user_id, token_version, issued_at, expires_at)`
  **and** `DELETE FROM auth_login_attempts WHERE email = …` (clears the throttle bucket).
- **On failure:** upsert into `auth_login_attempts` — `failed_count`, `window_started_at`,
  `locked_until`, `last_failed_at`, 15-minute window.

Two riders that matter for any cleanup:

1. **No route ever deletes an `auth_sessions` row.** Only `API: Reset Password` marks
   `revoked_at`. Rows accumulate until removed by SQL — which is why the count stood at 12 on
   25 August with almost nobody registered.
2. **Merely opening the registration link writes a row.** `GET api/verify-invite` upserts a
   throttle bucket into `auth_login_attempts` keyed `epe-throttle:verify-invite:<ip>`.

`EPE: Auth Guard` validates every request by joining a live `auth_sessions` row on
`jti`, `token_version = users.token_version`, `revoked_at IS NULL` and `expires_at > now()` — so
deleting the session rows logs the person out immediately, which is the clean undo.

Password reset additionally: bumps `users.token_version`, sets `password_reset_tokens.used_at`,
and revokes **every** live session for that user.

---

## 7. Cleanup mechanics

### 7.1 `api/admin/clear-test-evaluations` does not exist any more

**This is the headline of item 7.** The workflow behind that route,
`API: Admin Clear Test Evaluations` (id `U4XURKlDnaZ6XHg3`, `active=true` in the 2026-08-12 live
snapshot), was **deleted from live on 2026-08-19** as an explicit acceptance criterion of the
route-guard brief. BUG-002 is **🟢 CLOSED**, and three independent records agree:

- `docs/briefs/ROUTE_GUARD_H1_2026-08-19.md:29` — "Delete `api/admin/clear-test-evaluations`
  (after the n8n public dump)"; line 52 makes "clear-test-evaluations deleted" an end-state
  criterion.
- `bugs.md` BUG-002, Fix (2026-08-19) — "`API: Admin Clear Test Evaluations` was deleted".
- `docs/LAUNCH_PREP_2026-08-19.md:161`, from the *next* brief — "There is no
  `clear-test-evaluations` route (deleted in the previous brief). Cleanup was SQL delete + dump,
  on purpose."

It is also absent from HANDOVER §2's 33-workflow live active set and from all three builders.
**I did not invoke it.** Its live absence is not verified by this session (§0).

**What it did, and against which database.** No node graph survives in the repository — the
2026-08-12 snapshot is metadata only (`id`, `name`, `active`, `trigger_count`,
`connections: null`). What is on record from the 2026-08-12 live `workflow_entity` read:

- Webhook `authentication: null` — no token, header or secret (`PROGRESS.md:93`).
- First node after the POST: a Postgres `DELETE` of **all** `performance_db.evaluations` and
  `score_corrections` (BUG-002 description).
- It "deliberately reads/deletes across **all periods**" (`docs/REVIEW_H1.md:148`).
- Response shape `{ success, message, deleted_count, deleted_evaluations, deleted_corrections }`
  (`docs/API_CONTRACT.md:99`). It also answered OPTIONS (`docs/SERVER_MAP.md:287`).
- **Database and schema at the time: `postgres`, schema `performance_db` — the 2025 archive.**
  `epe_2026` did not exist until the 2026-08-18 import. That is exactly why BUG-002 reads
  "anyone who can reach `:5678` can wipe **last year's** evaluations".

**Live-unverified residue to surface:** `src/pages/AdminSettings.jsx:132` still calls
`apiClient.post(API_ENDPOINTS.ADMIN_CLEAR_TEST_EVALUATIONS)` and `src/config/api.js:107` still
defines the constant. If the route is indeed gone, that control now returns 404 and deletes
nothing — a dead button, not a hazard. Whether it is still reachable in the shipped bundle
`20260825T065554Z` was not checked and is unknown.

### 7.2 If evaluation rows are deleted by id, what still holds traces

| Thing | After a delete of `evaluations` rows |
|---|---|
| `evaluation_scores` | **Gone with them** — `ON DELETE CASCADE` (`schema.sql:251`) |
| `score_corrections` | **Stays.** No FK to `evaluations`; keyed `(subject_id, criteria_id, correction_level, period_id)` on live. Orphaned corrections survive and re-enter the matrix |
| `period_results` | Not involved before close; written only by close, and immutable after |
| Completion flags | **Nothing stored.** `has_self_review`, `has_evaluated_manager`, `evaluated_by_actor`, `self_review_done`, `manager_review_status` are all computed per request from `evaluations`. They clear by themselves |
| `evaluation_period_participants` | Carries only `is_in_scope` / `exclusion_reason` / timestamps — no completion state |
| Cached counters | **None found.** Every count in the read surface is a live subquery |
| History workflows | `My Evaluation History (Received)`, `Get Evaluation Details FIXED`, matrix, analytics, details-by-user all read `evaluations` live. Nothing is materialised |
| n8n execution history | **None.** All 33 generated definitions carry `saveDataSuccessExecution: "none"`, `saveDataErrorExecution: "none"`, `saveManualExecutions: false` |
| `auth_sessions` | **Stays** — one row per login, never deleted by any route |
| `auth_login_attempts` | **Stays** — including `epe-throttle:verify-invite:<ip>` buckets from opening the link |
| `users.password_hash` | **Stays** — whoever registered stays registered |
| `users.token_version` | **Stays** bumped, if anyone reset a password |
| Sequences | `evaluations_id_seq` / `evaluation_scores_id_seq` do not roll back — permanent id gaps |

The documented full-undo checklist, from the one time this was actually done on live
(`docs/SHARED_INVITE_2026-08-20.md` §4): null the `password_hash` rows, delete those users'
`auth_sessions`, confirm `email_verification_codes` is empty, delete the `epe-throttle:%` rows,
then re-count `registered`. Invite id 4 needs nothing — it is never burned.

---

## 8. Backups

**Last recorded successful `epe_2026` dump: `OK 2026-08-24T00:20:01Z`.**

- Source: `/root/backups/epe/backup-epe-live.status`, read live on 2026-08-24
  (`docs/DOCS_HYGIENE_2026-08-24.md:91`; HANDOVER §2). Same day's `backup.log`: `epe_2026 ok
  size=24100 retained=4`, `n8n_app ok size=366338 retained=4`, archive `ok size=34519
  retained=13`.
- The job is `20 3 * * * backup-epe-live.sh` — 03:20 MSK = **00:20 UTC**.
- **Today's run (2026-08-25T00:20Z) is not recorded anywhere in the repository, so today's
  status is unknown.** There is no MTA on the host, so nothing pages on failure; the status file
  is the only alarm and it is a pull check.

Separately, a **manual** pre-write dump was taken during FIX2 at **2026-08-25T07:22:29Z** —
`epe_2026_20260825_072229.dump`, 80 676 bytes, `pg_dump -Fc --no-owner --no-acl`. The VPS copy
was removed at teardown; the local copy lives in gitignored
`backups/2026-08-25-catalogue-fix2/`, **which is not present in this checkout**. (The size gap
against the cron figure is expected: the cron dumps are gzipped, this one is not.)

Off-host copy is still missing — **BUG-014**, now the only remaining backup gap: one disk holds
the live campaign database, the n8n backend and every backup of both.

The one-line check, for whoever has the Mac:

```
cat /root/backups/epe/backup-epe-live.status     # must read OK with today's date
```

---

## 9. Summary — what is known, what is not

**Established this session, from the repository (durable, re-checkable):** the entire second-gate
contract and the proof that no route unsets it (§4); the registration, password-format, invite-
reuse and login-trace mechanics (§6); the per-channel criteria rule and the exact relation
predicates that decide whether the trio works (§5.2–5.3); the FIX1/FIX2 delta and the verbatim
level-6 texts (§3); the deletion of `clear-test-evaluations` and the full trace inventory (§7);
the structural impossibility of a second active period, and the structural impossibility of
answering "when did they register" (§1, §2).

**Last measured, not re-verified today** (all from 2026-08-24/25 by earlier sessions): period
id 2's state and dates; the four zero row counts; `auth_sessions = 12`; the catalogue's live
content; the backup status of 2026-08-24.

**Unknown, and not inferred:** whether the gate has been pressed since 2026-08-25T07:23Z;
current row counts; how many and which accounts are registered; the trio's user ids, roles,
managers, reports, classification and registration state; whether any `manager_id` edge exists
inside the trio; today's backup status; the current state of invite token id 4; whether the
dead cleanup button is still reachable in the shipped bundle.

**Three premise corrections surfaced, not resolved:**

1. Criterion 13 and criterion 8's description were written by **FIX1**, not FIX2 — the pre/post-
   FIX2 diff the brief asks for has no signal there (§3.2).
2. Score-correction does not "stay open" across the gate; it is closed now and the gate is what
   opens it (§4.1).
3. `clear-test-evaluations` was deleted on 2026-08-19 and BUG-002 is closed — the brief's
   "unauthenticated, destructive" description is the pre-fix state (§7.1).

**Two findings outside the eight items, per the standing quality bar:**

- `bugs.md` now counts **18** `🔴 OPEN` rows against HANDOVER §10's "16 open / 37 closed,
  recounted 2026-08-24". The closed count still matches at 37, so two rows were opened after
  that recount and §10's counter is stale. Counter only — no bug row was touched.
- The dead cleanup button (§7.1) is a candidate defect, but **no `bugs.md` row was filed for
  it**: filing one would assert that the route is absent from live, and this session could not
  verify that. It needs one `GET`/`POST` probe from a machine with access before it becomes a
  row.

No recommendation is made about pressing «Запустить оценку». That decision is Alexander's.

---

**This report's commit:** `0f36bdb3e341e4d3b3a816e96a169cb88dd3b4f3` on branch `claude/launch-readiness-smoke-facts-laz4i7`.
The line above was added in the immediately following commit on the same branch, which changes
nothing else in this file.
