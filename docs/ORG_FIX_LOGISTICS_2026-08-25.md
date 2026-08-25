# Logistics reports to Jafarova; Egamberdyev returns to project (2026-08-25)

**Brief:** ORG_FIX_LOGISTICS, applying the owner's decisions on the org sheet
`docs/ORG_REVIEW_H1_2026-08-25.md` (anomaly A4) and the classification finding of its §4.3.
Decisions **D-0825-5** and **D-0825-6**.

**Outcome in one line: eight writes through the admin route put the whole Logistics department
under Alyona Dzhafarova — retitled Logistics Team Lead (Acting Head of Department) — and returned
Ruslan Egamberdyev to project participant; an independent restore-and-diff of all 89 people over
all 20 columns shows exactly nine changed cells and nothing else, and the second gate is still
unpressed.**

Writes were made **2026-08-25 14:18:26–14:19:07Z**. Run:
`scripts/apply_logistics_and_project_return.py` (supports `--dry-run`, which runs every gate and
prints the payloads without writing and without taking a dump). Proof:
`backups/2026-08-25-logistics/logistics_proof.json`, `failures: []`.

---

## 1. Three things to read before the numbers

### 1.1 The rollback anchor changed. Use the new one.

`epe_2026_pregate_20260825T121617Z.dump` was taken at **12:16Z**, which is *before* the six
Lab-Division writes (12:41–12:42Z) and before the four browser edits the owner made at
12:52–12:56Z. Restoring it today would silently undo all ten of those. It is **history only**.

The anchor for the smoke test is the dump this brief took immediately before its own first write:

| | |
|---|---|
| File | `epe_2026_pregate_20260825T141806Z.dump` |
| Taken | 2026-08-25 **14:18:06Z**, `pg_dump -Fc --no-owner --no-acl` of live `epe_2026` |
| Size | **80 706 bytes** |
| md5 | **`bdf13cfbaae9decf2e29a0e93495412d`** (verified equal on both copies) |
| On the VPS | `/root/epe_stand_tmp/epe_2026_pregate_20260825T141806Z.dump`, mode 600, root-only |
| On the Mac | `~/EPE_ROLLBACK/2026-08-25-logistics/epe_2026_pregate_20260825T141806Z.dump`, mode 600 — **outside the repository**, per the brief |

It captures the state *before* this brief's eight writes. Both dumps were left in place: the older
one is not deleted, only superseded, and nothing in this session depends on it.

### 1.2 The owner named «Rovshen Jafarova»; live has exactly one Jafarova, and her first name is Alyona

The run does not take an id from the brief. It searches live for a person in the Logistics
department whose name contains `afarov` and **refuses to write unless exactly one row matches**.
One row matched:

```
id 5 · Alyona Dzhafarova · Logistics Specialist · department 4 Logistics · role manager · manager 2
```

There is no «Rovshen Jafarova» among the 89. The only other `Rovsh…` on live is **Rovshan Yagmurov
(73)**, Planning and Drawing Engineer in the Project department — not logistics, not a Jafarov, and
not a candidate for anything in this brief. Everything else in the instruction fits id 5 exactly:
Logistics department, already role `manager`, already reporting to Petrosov, already the only
person in that department with subordinates.

**The instruction was applied to id 5. `full_name` was not changed** — the brief names `job_title`,
`role` and `manager_id`, and nothing else. If «Rovshen» is her actual name and «Alyona
Dzhafarova» is a bad import, that is a one-field correction the owner should confirm; it is
surfaced here, not resolved.

### 1.3 Kurbangeldyev (33) is not in the Logistics department, so the exception never bound

The brief instructed that Kurbangeldyev keep the manager the owner set by hand today, even if he
sits in that department. He does not:

| id | person | department | manager | touched by this run |
|---|---|---|---|---|
| 33 | Eziz Kurbangeldiyev | **11 IT**, not 4 Logistics | 2 (Petrosov) — the owner's 12:52–12:56Z edit | **no** |

He was therefore never a candidate for a `manager_id` write, and the exception cost nothing. His
row was still asserted byte-identical before and after, and re-read from the admin API afterwards.
The IT department remains a one-person department (anomaly A9 of the review sheet) — unchanged and
still open.

---

## 2. What was changed

Eight writes, each a separate `POST /webhook/admin/save-user`, all **200**.

| # | id | person | field | from | to |
|---|---|---|---|---|---|
| 1 | 5 | Alyona Dzhafarova | `job_title` | `Logistics Specialist` | **`Logistics Team Lead (Acting Head of Department)`** |
| 1 | 5 | Alyona Dzhafarova | `role` | `manager` | `manager` — **already correct, resent unchanged** |
| 1 | 5 | Alyona Dzhafarova | `manager_id` | `2` | `2` — **already correct, resent unchanged** |
| 2 | 12 | Aygozel Ashgabadova | `manager_id` | 2 | **5** |
| 3 | 13 | Ayna Yazmuradova | `manager_id` | 2 | **5** |
| 4 | 43 | Ilaman Saryhanov | `manager_id` | 2 | **5** |
| 5 | 60 | Aleksandr Maloletenko | `manager_id` | 2 | **5** |
| 6 | 62 | Merdan Rasulov | `manager_id` | 2 | **5** |
| 7 | 84 | Valentin Odinov | `manager_id` | 2 | **5** |
| 8 | 74 | Ruslan Egamberdyyev | `work_category` | `general` | **`project`** |
| 8 | 74 | Ruslan Egamberdyyev | `is_project_participant` | `false` | **`true`** — derived by the route, never sent |

Two of the owner's three instructions about Jafarova were already true on live: her role was
already `manager` and her manager was already Petrosov (2). Only the title actually moved. Both
fields were resent anyway, because the route rewrites the whole row.

**Two people in the Logistics department were already reporting to her and needed no write:**
Muhammet-Ali Chariyev (22) and Govher Balova (35, out of H1 scope, hired after 30 June). The
department is nine people; six moved, two were already right, one is Jafarova herself.

### The department now

```
Alexander Petrosov (2, admin) — 6 direct reports (was 12)
└── Alyona Dzhafarova (5, manager, Logistics Team Lead (Acting Head of Department)) — 8 reports
    ├── Aygozel Ashgabadova (12)      · Ayna Yazmuradova (13)
    ├── Muhammet-Ali Chariyev (22)    · Govher Balova (35, ⚠ out of H1 scope)
    ├── Ilaman Saryhanov (43)         · Aleksandr Maloletenko (60)
    └── Merdan Rasulov (62)           · Valentin Odinov (84)
```

Petrosov keeps Dzhafarova (5), Soltyyev (27), Kurbangeldiyev (33), Davletov (65), Ismailova (83)
and Son (88).

### Why the route and not SQL

`scripts/apply_logistics_and_project_return.py` writes **only** through
`POST admin/save-user` (`API: Admin Save User (GUI Mode)`, guard `required_roles: ["admin"]`),
never raw SQL on `users` — the same discipline as D-0825-1/2/3. That route's UPDATE is a
**full-row overwrite** with dangerous defaults (`body.role || 'employee'`,
`body.work_category || 'general'`), and it additionally lowercases and trims `email`, trims
`full_name`, and stores an empty `job_title` as NULL. So:

- every payload was the live row **read fresh immediately before its own write**, all nine
  writable columns resent, with only the intended field replaced;
- every stored field was read back and compared to what was sent **before the next call was made** —
  a mismatch stops the run with the anchor path printed, and there is no raw-SQL fallback;
- a gate first asserted that **no** row on live would be altered merely by being resent: zero of
  the 89 have a non-lowercase or untrimmed email, an untrimmed name, or an empty job title
  (`rows_a_resend_would_rewrite: []`).

`has_subordinates` was deliberately **not** written — `trg_update_has_subordinates` owns it. The
run asserts the trigger's result instead of setting the value. It did not need to fire for anyone:
Jafarova already had subordinates and Petrosov still has six.

---

## 3. Verification

Every check below is an assertion inside the run, and the drift check was then repeated
**independently** by restoring the anchor into a throwaway database and diffing it against live.

**Gates before any write:** H1 `active` / `is_active=true` / `evaluation_started_at IS NULL`; all
four data tables 0; 89 users; Jafarova uniquely identifiable; Egamberdyev currently `general`
(premise re-asserted, not assumed); `has_subordinates` already agreeing with the graph for all 89;
`/root/epe_stand_tmp` holding nothing but the superseded anchor.

### 3.1 Drift — independent, cell by cell

The anchor was restored into a throwaway database `epe_logifix_20260825t1418z` and every column of
every user compared against live. **1 780 cells compared (89 people × 20 columns). Nine changed:**

```
 5 job_title              'Logistics Specialist' -> 'Logistics Team Lead (Acting Head of Department)'
12 manager_id             2 -> 5
13 manager_id             2 -> 5
43 manager_id             2 -> 5
60 manager_id             2 -> 5
62 manager_id             2 -> 5
84 manager_id             2 -> 5
74 work_category          'general' -> 'project'
74 is_project_participant  False  -> True
```

Nothing else. The frozen columns — `salary_current`, `salary_proposed`, `join_date`,
`password_hash`, `can_evaluate`, `can_be_evaluated`, `token_version`, `employment_type`,
`created_at` — are **untouched on all 89**, on both the in-run check and the independent diff.

Every other table was fingerprinted on both sides and is identical: `criteria` (9),
`score_coefficients` (90), `grades`, `departments`, `evaluation_periods`,
`evaluation_period_participants` (89 / 87 in scope). Same md5 on the anchor and on live.

### 3.2 Invariants after

| Check | Result |
|---|---|
| `role=manager` ⇔ has direct reports | **0 exceptions** (13 managers: 1, 5, 15, 17, 27, 28, 32, 42, 45, 65, 68, 83, 88) |
| `has_subordinates` vs the graph, all 89 | **0 disagreements** |
| Management-chain cycles | **0**, max chain depth 5 |
| People with no evaluator (`manager_id` NULL, not c_level/admin) | **0** |
| In scope but evaluated by nobody | **exactly the six the owner declared intentional** — 2, 18, 21, 40, 47, 61 |
| Evaluated population (in scope **and** `can_be_evaluated`) | **81**, unchanged |
| H1 after | `active` / `is_active=true` / `evaluation_started_at` **NULL** — gate still unpressed |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| Participants / in scope on H1 | 89 / 87, unchanged |
| `auth_sessions` | 13 → 13; the probe session was minted and deleted in a `finally` |

### 3.3 The read surface agrees

Read-only probe after the writes, admin token, session deleted afterwards:

- `GET /api/periods` → 200: H1-2026 `status=active`, `is_active=true`, `evaluation_started=false`,
  `in_scope_count=87`, `participant_count=89`.
- `GET /api/admin-users-data` → 200, 89 rows; ids 5 / 12 / 13 / 22 / 35 / 43 / 60 / 62 / 84 / 74 /
  33 all read back exactly as written.
- `GET /api/employees` → 200 with `campaign_active=false`, `period_in_preparation=true` and an
  empty task list — correct: the second gate is unpressed, so nobody has tasks yet.

---

## 4. What this changes for H1

### 4.1 Criteria-count distribution and the category split

Recomputed from the live applicability rule (`API: Get Employees`: active, not `c_level_only`,
`project_participants` only for current participants, `managers_only` only for a subject with
subordinates):

```
before: 4 -> 38 people,  5 -> 11,  6 -> 34,  7 -> 6      (89)
after : 4 -> 37 people,  5 -> 11,  6 -> 35,  7 -> 6      (89)

work_category   before: general 49 / project 40
                after : general 48 / project 41
```

**Exactly one person moved bucket: Egamberdyev, 4 criteria → 6.** The logistics change moved
nobody: Jafarova already had subordinates before it, so she already had criterion 2, and the six
people who moved gained no criterion by changing manager.

### 4.2 Jafarova — who evaluates her, and whom she evaluates

Derived from the live filters in `API: Submit Evaluation` / `API: Submit Self Review`
(both actor and subject must be `is_in_scope` on the active period).

| Channel | Before | After |
|---|---|---|
| Self-review | yes | yes |
| Manager → her | Petrosov (2) | Petrosov (2) — unchanged |
| Upward → her | **1 person**: Chariyev (22) | **7 people**: 12, 13, 22, 43, 60, 62, 84 |
| C-level direct → her | 2, 18, 47 | 2, 18, 47 — unchanged |
| She evaluates as manager | **1**: Chariyev (22) | **7**: 12, 13, 22, 43, 60, 62, 84 |
| Her own upward review | none — her manager is `admin` | still none, same reason |
| Her criteria | 2, 3, 4, 12, 14 — **five** | 2, 3, 4, 12, 14 — **five, unchanged** |

Balova (35) reports to her but is out of H1 scope, so she produces and receives nothing — which is
why the manager task list is 7, not 8.

**Consequence for the campaign load:** she goes from one manager task to seven, and from one
upward reviewer to seven. Six people who could not evaluate their manager at all now can:
**in-scope people with no upward channel drops from 24 to 18.**

**The mid-level corrector changed for those six.** `mid_level` is the subject's manager's manager
(D-0820-10). For ids 12, 13, 43, 60, 62 and 84 that was **Durukan (21)** and is now
**Petrosov (2)**.

### 4.3 Egamberdyev (74) — the money

Criteria **before: 4** — 3 «Личная результативность», 4 «Надежность и взаимодействие с
руководителем», 12 «Профессиональное развитие», 14 «Ответственность сверх роли».
Criteria **after: 6** — the same four plus 8 «Взаимодействие и надежность в проекте» (weight 1.40)
and 13 «Объем проектной работы и загрузка» (weight 1.80).

Bonus index at equal scores, computed from the **live** weights and level coefficients with his
real grade coefficient (grade S3, **1.40**), by formula #3 — weighted sum *without* dividing by the
weight sum, times the grade coefficient (HANDOVER §4):

| Score on every criterion | Index before | Index after | Difference |
|---|---|---|---|
| 4 | 33.60 | 49.73 | **+48.0 %** |
| 5 | 49.00 | 71.40 | **+45.7 %** |
| **6 (норма)** | **69.72** | **102.31** | **+46.8 %** |
| 7 | 98.00 | 146.22 | **+49.2 %** |
| 8 | 146.16 | 227.70 | **+55.8 %** |

The «roughly +47 %» in D-0825-5 is right at the norm and at the levels around it; it widens above
level 7 because criterion 13's level curve rises faster than the others. Nothing was paid or
recorded — the four data tables are empty — so this changes the starting conditions, not any
existing number.

---

## 5. Surfaced, not resolved

### 5.1 D-0825-5's «Jafarova gains criterion 2» is not what happened

The decision text was appended to `DECISIONS.md` verbatim as instructed. One statement in it is
contradicted by live:

> «Jafarova gains criterion 2 «Качество управления» (weight 3.00)»

She already had it. Criterion 2 keys on `has_subordinates`, not on role or title, and she has had
two subordinates (Chariyev 22, Balova 35) throughout — `has_subordinates=true` before the change,
`jafarova_criteria` `[2, 3, 4, 12, 14]` before and after. **Her criteria count and her bonus index
are identical before and after this brief.** This is the same trap the review sheet flagged in
§5.3: role and title move screens, subordinates move money.

What the logistics change actually buys, in H1 terms, is on the *other* side of the arrow: the
seven logistics people gain an upward channel that pointed at an `admin` and therefore did not
exist, and Jafarova acquires six new manager→subordinate tasks. The money statement in the
decision text is wrong; the decision itself is unaffected.

### 5.2 D-0825-6's «~24 people» is now 18

The decision text says the upward filter leaves «the ~24 people who report directly to C-level»
with no upward task. That was the measurement before this brief. Six of them were logistics staff
reporting to Petrosov and now report to Jafarova, so the live figure is **18**. The «81» in the
same decision is unchanged and confirmed by live.

### 5.3 Where «87 / 89» comes from — read only, not changed

- **Computed** in LIVE `API: Manage Periods` → node **`Build Periods Query`**, as two correlated
  subqueries on `performance_db.evaluation_period_participants`:
  `COUNT(*) … AS participant_count` and `COUNT(*) … WHERE is_in_scope = true AS in_scope_count`.
- **Rendered** at [`src/pages/AdminPeriods.jsx:609-610`](../src/pages/AdminPeriods.jsx#L609) —
  `` `${period.in_scope_count} / ${period.participant_count}` `` in the «В охвате» column.
- Live values today: 89 / 87 for H1 (period 2), 89 / 89 for the Annual 2026 container.
- **Neither figure was changed, and neither is wrong** — they measure period membership and hire-date
  scope, which is what that column is for. What they do *not* measure is the evaluated population:
  six people (2, 18, 21, 40, 47, 61) are in scope and are evaluated by nobody, so completion must be
  read against **81**. That is D-0825-6, and it belongs in EVALUATION_METHODOLOGY §1 and §6 as the
  decision says — the counter itself should stay as it is.

### 5.4 This brief's writes are in BUG-059's blind spot too

`performance_db.users` still has no `updated_at` and `admin/save-user` still writes no audit row.
The eight writes here are dated to the microsecond only because the run recorded them
(`logistics_proof.json`), the same way D-0825-3's six were. That is a compensating control, not a
fix. **BUG-059 stays open.**

### 5.5 A transient change to live, made and reverted

The first attempt at the independent diff ran `CREATE EXTENSION IF NOT EXISTS dblink` on the live
`epe_2026`. It succeeded and was immediately dropped; `pg_extension` on live now lists only
`plpgsql`, its original state. The diff was then redone without any extension, by exporting both
sides as JSON. Recorded here because it was a change to live that no instruction asked for.

---

## 6. Session hygiene

- One throwaway database, `epe_logifix_20260825t1418z`, restored from the anchor for the
  independent diff and **dropped**. `SELECT datname` after teardown lists only `epe_2026` and
  `postgres`.
- **No stand container was created. No container was restarted or stopped.** Other projects share
  this machine; `docker ps` shows the same six containers as before.
- `/root/epe_stand_tmp` holds the two anchors and nothing else, mode 600. Nothing landed in `/tmp`
  (asserted by the run).
- The probe sessions were minted and deleted in `finally` blocks; `auth_sessions` 13 → 13.
- No catalogue, coefficient, criteria, grade, department or period write of any kind. **The second
  gate was not pressed and no route that could press it was called.**
