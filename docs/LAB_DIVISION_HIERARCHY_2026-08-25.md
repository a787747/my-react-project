# Lab Solutions Division — hierarchy corrected on live (2026-08-25)

**Brief:** owner statement in session, 2026-08-25 — «Джахан Ходжаева действительно менеджер дивизиона
Lab Solutions Division, куда структурно входят Special Lab Solutions (без лидера) и два подотдела
Clinical Lab Solutions (один возглавляет Нурмамет Хекимов, второй Акмырат Джумаханов)». Decision
**D-0825-3**.

**Outcome in one line: live had the entire Lab Solutions branch flat under the COO and the division
head recorded as a rank-and-file employee with zero reports; six writes through the admin route put
the branch under Jahan Hojayeva, with zero drift on any other field of any of the 89 people.**

---

## 1. What was wrong

`performance_db.departments` carries only `id, name, description` — **there is no parent column**, so
the nesting the owner describes cannot be stored there at all. The evaluation hierarchy exists solely
in `users.manager_id`, and that graph did not match the org:

| id | person | department | reported to | role | reports |
|---|---|---|---|---|---|
| 45 | Jahan Hojayeva | 1 Lab Solution Division | Bayram Urayev (18, `c_level`) | **`employee`** | **0** |
| 1 | Akmyrat Jumahanov | 16 Clinical Lab Solutions | Bayram Urayev (18) | `manager` | 6 |
| 68 | Nurmammet Hekimov | 16 Clinical Lab Solutions | Bayram Urayev (18) | `manager` | 3 |
| 6 | Anastasiya Kostina | 18 Special Lab Solution | Bayram Urayev (18) | `employee` | 0 |
| 55 | Muhammet Muhammedov | 18 Special Lab Solution | Bayram Urayev (18) | `employee` | 0 |
| 53 | Muhammetberdi Garayev | 16 Clinical Lab Solutions | **Bayram Urayev (18)** | `employee` | 0 |

Three consequences that were live and would have shipped into H1:

1. **Hojayeva was not scored on management.** Criterion 2 «Качество управления и развитие команды»
   is gated on `users.has_subordinates` — verified in the live `API: Get Employees (Smart Role Based)`
   SQL, `AND (c.target_audience <> 'managers_only' OR users.has_subordinates = true)`. With zero
   reports she had 6 criteria, not 7, and the division head's core responsibility was unmeasured.
2. **Five people had no upward channel.** The live submit filter for `subordinate` is
   `actor.manager_id = <subject> AND subj.role NOT IN ('c_level','admin')`. Their manager was the
   COO, so the filter excluded him and their upward review had nowhere to go.
3. **Garayev sat in Clinical Lab Solutions under neither sub-department head** — the only person in
   department 16 reporting outside it.

Two ambiguities were put to the owner rather than guessed, and answered in session: Special Lab
Solution's two people go to Hojayeva (the sub-department has no leader), and Garayev joins Hekimov.

## 2. What was changed

Six writes, each a separate `POST /webhook/admin/save-user` call:

| # | user | field | from | to |
|---|---|---|---|---|
| 1 | 45 Jahan Hojayeva | `role` | `employee` | **`manager`** |
| 2 | 68 Nurmammet Hekimov | `manager_id` | 18 | **45** |
| 3 | 1 Akmyrat Jumahanov | `manager_id` | 18 | **45** |
| 4 | 6 Anastasiya Kostina | `manager_id` | 18 | **45** |
| 5 | 55 Muhammet Muhammedov | `manager_id` | 18 | **45** |
| 6 | 53 Muhammetberdi Garayev | `manager_id` | 18 | **68** |

Hojayeva continues to report to Urayev — she is a division head under the COO, which was already
right and was left alone.

### Why the route and not SQL, and the trap it carries

`scripts/apply_lab_division_hierarchy.py` writes **only** through
`POST admin/save-user` (`API: Admin Save User (GUI Mode)`, guard `required_roles: ["admin"]`), never
raw SQL on `users` — the same discipline D-0825-1/2 used for the catalogue.

That route's UPDATE is a **full-row overwrite** with dangerous defaults:

```js
const workCategory = String(body.work_category || 'general').trim();
const role         = String(body.role || 'employee').trim();
```

```sql
UPDATE performance_db.users
SET full_name = …, email = …, role = …, job_title = …, work_category = …,
    is_project_participant = …, department_id = …, grade_id = …, manager_id = …
WHERE id = …
```

An omitted `role` silently demotes a manager; an omitted `work_category` silently reclassifies a
project participant to general and, through `is_project_participant`, removes two criteria and
changes their bonus. So every payload was the **live row read fresh immediately before its own
write**, all nine writable columns resent, with only the one intended field replaced — and every
field was read back and compared to what was sent before the next call was made.

### `has_subordinates` was deliberately not written

`performance_db` carries `trg_update_has_subordinates`, `AFTER INSERT OR DELETE OR UPDATE OF
manager_id … FOR EACH ROW`, which recomputes the flag on **both** the old and the new manager. The
route does not write the column and must not. The run asserts the trigger did its job rather than
setting the value.

## 3. What it looks like now

```
Bayram Urayev (18, c_level, COO) — 4 direct reports
└── Jahan Hojayeva (45, manager, Head of the Lab Solutions Division) — 4 direct reports
    ├── Akmyrat Jumahanov (1, manager, Clinical Lab Solutions) — 6
    │   └── Naubatova 3 · Usmanov 10 · Esenova 31 · Orusov 39 · Gylyjov 54 · Tishkina 79
    ├── Nurmammet Hekimov (68, manager, Clinical Lab Solutions) — 4
    │   └── Annameredov 20 · Garayev 53 · Ishanova 56 · Ruhlyadko 85
    └── Special Lab Solution (no leader)
        └── Kostina 6 · Muhammedov 55
```

Urayev keeps Sherapov (17), Hummedov (42), Hojayeva (45) and Annekov (72) — nine reports down to four.

## 4. Verification

Every check below is an assertion inside the run (`backups/2026-08-25-lab-division/lab_division_proof.json`,
`failures: []`), re-read independently afterwards by a separate SQL pass.

**Gates before any write** — H1 `active` / `is_active` / `evaluation_started_at IS NULL`; all four
data tables 0; the six subjects all still reporting to 18 (premise re-asserted, not assumed);
Hojayeva still `employee`; `has_subordinates` already agreeing with the graph for all 89;
`/root/epe_stand_tmp` holding nothing but the pre-gate rollback anchor.

**Dump first**, per AGENTS.md hard constraint 1: `epe_2026_20260825_124132.dump`, 80 710 bytes,
md5 `fa56a4f2103da8429ae083e2a72e7670`, in gitignored `backups/2026-08-25-lab-division/`. The VPS
copy was removed at teardown (`vps_dump_removed: removed`).

**All six calls returned 200**, and each stored row was compared field by field against the payload
before the next call.

**After:**

| Check | Result |
|---|---|
| Hojayeva `role` / manager / reports | `manager` / 18 / `[1, 6, 55, 68]` |
| Hekimov reports | `[20, 53, 56, 85]` |
| Jumahanov reports | `[3, 10, 31, 39, 54, 79]` |
| Urayev reports | `[17, 42, 45, 72]` |
| `has_subordinates` vs the graph, all 89 | **0 disagreements** |
| `role=manager` ⇔ has direct reports, all 89 | **0 exceptions** (13 managers) |
| people with no evaluator (`manager_id` NULL, not c_level/admin) | **0** |
| management-chain cycles | **0**, max chain depth 4 |
| **drift outside the six intended fields, all 89 users, all columns** | **none** |
| frozen columns (`employment_type`, `join_date`, `salary_current`, `salary_proposed`, `created_at`, `password_hash`, `can_evaluate`, `can_be_evaluated`, `token_version`) | **untouched on all 89** |
| H1 after | `active` / `is_active` / `evaluation_started_at` NULL — **gate still unpressed** |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | 0 / 0 / 0 / 0 |
| `auth_sessions` | 13 → 13; the probe session was minted and deleted in a `finally` |
| registered accounts | 2, unchanged |

## 5. What this changes for H1

**Criteria distribution** moved by exactly one person — Hojayeva, from 6 criteria to 7:

```
before: 4 → 38 people,  5 → 11,  6 → 35,  5 people × 7
after : 4 → 38 people,  5 → 11,  6 → 34,  6 people × 7        (89 both ways)
```

**New evaluation channels that did not exist before:**

- Hojayeva now has four manager→subordinate tasks (Jumahanov, Hekimov, Kostina, Muhammedov).
- Those four gain an upward review of Hojayeva — previously impossible, because their manager was
  `c_level` and the upward filter excludes that role.
- Garayev moves from the COO's list to Hekimov's, and gains an upward review of Hekimov.
- Hojayeva herself still has no upward channel: her manager is Urayev, `c_level`.

**For the smoke test:** the trio named in `docs/PRELAUNCH_LIVE_CHECK_2026-08-25.md` still works
exactly as reported — Hekimov→Ruhlyadko and Ruhlyadko→Hekimov are untouched — and Hojayeva is no
longer limited to a self-review: she can now be exercised as a manager and as an upward subject.
The two blockers named there are unchanged: none of the three is registered, and submit is 409 until
«Запустить оценку» is pressed.

---

**Run:** `scripts/apply_lab_division_hierarchy.py` (supports `--dry-run`, which runs every gate and
prints the six payloads without writing). Proof: `backups/2026-08-25-lab-division/lab_division_proof.json`.
Writes were made **2026-08-25 12:41–12:42Z**.
