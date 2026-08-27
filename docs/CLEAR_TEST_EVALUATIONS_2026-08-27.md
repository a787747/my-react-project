# CLEAR_TEST_EVALUATIONS — pre-invite H1 test rows removed (2026-08-27)

**Brief:** CLEAR_TEST_EVALUATIONS (Sol xhigh, fresh session, on the Mac).
**Verdict in one line:** the four campaign tables are **0 / 0 / 0 / 0** again.
One upward test evaluation (id **39**) and its one score row (id **108**) were
deleted by recorded id in one transaction; no `c_level_direct` row existed, so
nothing was held for the owner; registered accounts stay **4** with hashes
untouched; coefficients are md5-identical to
`docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`;
`evaluation_started_at` is still **2026-08-26 10:08:54.340312Z**.

§4 of HANDOVER was not edited. The bulk-clear route was not recreated.

---

## Inventory the owner can read (Russian)

Снято **2026-08-27 09:57:56Z**, до любого удаления. Повторное чтение под
блокировкой **09:59:43Z** — те же строки, новых не появилось.

В открытом периоде H1-2026 (id 2) было ровно одно тестовое действие:

1. **Оксана Борисенкова** (id 70, сотрудник, **зарегистрирована**) оценила
   своего руководителя **Айшу Сувханову** (id 15, менеджер, **не
   зарегистрирована**) снизу вверх (канал `subordinate` / «оценить
   руководителя»).
   - Оценка **6** по критерию 2 «Качество управления и развитие команды».
   - Итог по карточке: **6.00**. Комментариев нет.
   - Когда: **2026-08-27 08:50:06Z**.
   - Строка оценки id **39**, строка балла id **108**.

Корректировок (`score_corrections`) не было. Замороженных итогов периода
(`period_results`) не было. Строк канала **`c_level_direct` не было** —
удаление не останавливалось.

**Зарегистрированные аккаунты (4), кто из них писал:**

| Кто | Роль | Писал в кампанию? |
|---|---|---|
| Alexander Petrosov (2) | admin | нет |
| Jemal Gulberdiyeva (47) | c_level | нет |
| Liya Dmitriyeva (52) | hr | нет |
| Oksana Borisenkova (70) | employee | да — та самая оценка снизу вверх |

Оксана остаётся зарегистрированной. Её пароль не трогали. Письмо-приглашение
по-прежнему не создавалось и не рассылалось.

---

## 1. Anchor dump (before the first delete)

Fresh `pg_dump -Fc --no-owner --no-acl` of live `epe_2026` at
**2026-08-27 09:59:11Z**, copied to the Mac **outside** the repository, md5
equal on both sides:

- VPS `/root/epe_stand_tmp/epe_2026_preclear_20260827T095911Z.dump` →
  **`9c1f873f861bd6517e55556a7998931c`** (removed after the copy, per
  `PROJECT_RULES.md`)
- Mac `~/EPE_ROLLBACK/2026-08-27-clear-test-evaluations/epe_2026_preclear_20260827T095911Z.dump`
  → **`9c1f873f…`** (kept; 101 837 B)

This dump is the only way back if a deleted row later turns out to have been
real.

---

## 2. Delete (one transaction, recorded ids)

Locked the four campaign tables, re-read, then deleted. The locked re-read
matched the first inventory exactly — no second inventory was required.

| table | inventoried | deleted ids | count |
|---|---|---|---|
| `evaluations` | 39 (period 2, `subordinate`, 70→15, 6.00) | **39** | **1** |
| `evaluation_scores` | 108 (eval 39, criterion 2, score 6) | cascade from 39 | **1** |
| `score_corrections` | none | none | **0** |
| `period_results` | none | none | **0** |

Deleted counts match the inventory. `evaluation_scores.evaluation_id` is
`ON DELETE CASCADE` (live constraint
`evaluation_scores_evaluation_id_fkey`). Corrections have no such FK and
were addressed explicitly (zero rows).

After `COMMIT` at **09:59:43.999Z**: **0 / 0 / 0 / 0**. Re-proved at
**09:59:56Z**: still **0 / 0 / 0 / 0**.

---

## 3. What did not move

Compared immediately before the dump and after the delete. Identical on
every line:

| quantity | before | after |
|---|---|---|
| campaign tables | 1 / 1 / 0 / 0 | **0 / 0 / 0 / 0** |
| H1 `evaluation_started_at` / `evaluation_started_by` | `2026-08-26 10:08:54.340312Z` / 2 | same |
| H1 status / `is_active` | `active` / true | same |
| Annual 2025 / Annual 2026 | closed / draft | same |
| registered accounts | 2, 47, 52, **70** | same four names |
| `password_hash` md5 (2 / 47 / 52 / 70) | `6b3bcacd…` / `d11f6ef7…` / `b3183b62…` / `571464b7…` | identical |
| `token_version` | 2 / 0 / 0 / 0 | identical |
| users (every column except `password_hash`) | `6de02e05de8de710aefaaf94f4d5c26e` | identical |
| users / terminated (`terminated_at`) / roles | 89 / 3 / 1+5+13+68+2 | identical |
| H1 participants | 89 / **78** in scope | identical |
| Annual 2026 participants | 89 / 86 in scope | identical |
| participants fingerprint | `e396552f36d5b81ec0721f0dbfff80ef` | identical |
| criteria md5 (9 active) | `fc618757f6aa2c27db5bce7613fc28c7` | identical |
| `score_coefficients` md5 (90) | `317e09e8326edde500bfcde2bad81e78` | identical |
| grades md5 (11) | `946b30a5ea8b8594321ebb5fc645bd32` | identical |
| combined coefficient fingerprint | **`079177fbb9d52ea4c5b942fcecaed1c2`** | = snapshot |
| `employment_events` / md5 | 3 / `6f73e4ba…` | identical |
| `period_scope_events` / md5 | 8 / `54d5f9bb…` | identical |
| `employee_card_events` | 0 | 0 |
| `invite_tokens` md5 | `db57dd364731976e4c05e76aa132b481` | identical |

2025 archive (`postgres.performance_db`, read after the delete): still
**234 evaluations / 644 scores / 3 corrections**. Not written.

No user, scope, termination, reinstatement, catalogue, coefficient, grade,
criterion or period write. No mail. No invite created or rotated. No
container restart.

---

## 4. Sequence gaps (accepted, not repaired)

A deleted `INSERT` still consumes `nextval`. Left as they are:

| sequence | last_value | unused ids from this brief | earlier unused (LIVE_SMOKE) |
|---|---|---|---|
| `evaluations_id_seq` | **39** | **39** | 31–38 |
| `evaluation_scores_id_seq` | **108** | **108** | 82–107 |
| `score_corrections_id_seq` | **7** | none | none |

---

## 5. Surfaced, not resolved

- **A fourth person is registered.** HANDOVER still said three (2, 47, 52).
  Live before this session already had Oksana Borisenkova (70). She
  registered herself and filed the upward row at 08:50Z. She stays
  registered; this brief did not invent or remove an account.
- **`/root/epe_stand_tmp` still holds**
  `epe_2026_pre_adminusers_20260827T075552Z.dump` from an earlier brief.
  This session's dump was removed. That leftover was not touched.

---

## 6. Session hygiene

- Read-only until the dump; the dump preceded the first write; Mac copy
  outside the repo; md5 equal; VPS copy of *this* dump deleted.
- Live writes this session: one `DELETE` of evaluation **39** (score **108**
  cascaded). Zero correction deletes. Nothing else.
- `git status` clean at start. This report, the `PROGRESS.md` entry and the
  HANDOVER measurement update are the only repo changes.
