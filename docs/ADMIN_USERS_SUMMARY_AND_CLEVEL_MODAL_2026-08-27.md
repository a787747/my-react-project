# ADMIN_USERS_SUMMARY_AND_CLEVEL_MODAL (2026-08-27)

**Brief:** ADMIN_USERS_SUMMARY_AND_CLEVEL_MODAL (Grok 4.6, Mac). **Campaign OPEN**
since 2026-08-26 10:08:54.340312Z. §4 of HANDOVER was not edited. Nothing here
touches a formula, a weight, a coefficient or any money computation.

**Outcome in one line: the C-level modal no longer prefills 5 and cannot be
submitted until every applicable C-level criterion is touched (BUG-078);
`/admin/users` now names registration and both campaign directions against
explicit populations; live frontend `20260827T075704Z`; workflow
`API: Admin Get Users Data` PUT at 2026-08-27T07:56:39.858Z; H1
`evaluation_started_at` unmoved; tables 0/0/0/0; 89 / 3 / 78; coefficients
md5-identical to the 2026-08-26 snapshot.**

---

## 0. What was checked before any write

Working tree at session start: **clean** (`main` `d2e280a`).

Live before the change (SSH `SELECT`): H1 id 2 `active` / `is_active=true`,
`evaluation_started_at=2026-08-26 10:08:54.340312+00`; tables **0/0/0/0**;
**89** users, **3** terminated, H1 in-scope **78**; catalogue / coefficients /
grades md5 `fc618757f6aa2c27db5bce7613fc28c7` /
`317e09e8326edde500bfcde2bad81e78` / `946b30a5ea8b8594321ebb5fc645bd32` —
equal to `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`
(combined `079177fbb9d52ea4c5b942fcecaed1c2`). Frontend then live:
`releases/20260827T065624Z`.

The route `GET /api/admin-users-data` already returned `is_registered`,
`period_is_in_scope`, `self_review_done` and a `manager_review_status` that is
`LIMIT 1` on any non-self row. It could not honestly compute either campaign
direction or tell the six (`can_be_evaluated=false`) from the people who are
actually evaluated. A **read-payload extension** was required. No write route
was touched.

Invited population, decided before the UI was built: **employed (86 on live)**,
not 89 and not 78. The company-wide letter is for people still in staff.
Terminated people are not invited. Out-of-scope employed people still get the
letter. The invitation has not been sent yet — this is the intended list.

`c_level_direct` is a shared channel, not a 1:1 assigned debt. It is in
neither Welcome counter.

§4 of HANDOVER was not edited.

---

## 1. BUG-078 — C-level modal (demonstrated, not assumed)

Same rule as D-0827-2. The slider thumb may rest at 1. Until the evaluator
touches a criterion the badge is `—`, no zone label is shown, and submit stays
disabled (`Оцените все критерии (N)`). An existing actor score is a prior
choice: it is shown and remains editable. The payload omits untouched keys; it
never invents a 5.

Demonstrated in Google Chrome against Vite `:5299` → stand `:25679` (the
Cursor browser MCP was not registered in this session). Login
`wt.clevel.writer@sedamedical.com`. Proof:
`backups/2026-08-27-admin-users-summary/browser_proof.json` (PASS).

| Step | What the browser showed |
|---|---|
| Open C-level on WT Employee R (no prior actor score) | title `👑 C-level оценка`; badges `—`, `—`; no zone; submit disabled `Оцените все критерии (2)` |
| Click the disabled submit | modal still open, still disabled |
| Touch both sliders (7 and 6) | badges `7`, `6`; submit enabled `Сохранить` |
| Submit | alert `C-level оценка сохранена!`; modal closed |
| Open existing eval on WT Employee G | title `👑 Изменить C-level оценку`; badges `8`, `6`; submit enabled `Сохранить` |

Criteria 1 (weight 5.00) and 10 (1.60) are the two C-level cards. They no
longer open as a pre-selected 5.

---

## 2. Numbers established on the stand before the line was trusted

Throwaway `epe_adminusers_20260827_0749` restored from a dated live dump
(md5 `1bf59defcfbeeee1a06d6154f4a11252`), walkthrough fixture 1301–1310, then
eight seeded evaluation rows across self / manager / upward / `c_level_direct`.
Stand dropped before live deploy. Remaining databases on `postgres_n8n`:
`epe_2026`, `postgres`.

Independent SQL vs `GET /api/admin-users-data` vs `buildCampaignSummary`
(`scripts/prove_admin_users_summary.py`, PASS). Every counter matched.

| Counter | SQL | API+JS |
|---|---|---|
| everyone | 99 | 99 |
| terminated | 3 | 3 |
| employed / invited | 96 | 96 |
| inScope | 88 | 88 |
| evaluatedBySomeone / evaluationOwed | 78 | 78 |
| registeredInvited | 13 | 13 |
| tasksAssigned | 82 | 82 |
| tasksDone | 2 | 2 |
| fullyEvaluated | 2 | 2 |

Two populations differ, on purpose:

- **25 David Asatryan** — employed, `can_be_evaluated=true`, **out of H1
  scope**. Not in `inScope`, not in `tasksAssigned`, not in `evaluationOwed`.
- **21 Cem Durukan** — one of the six: **in scope**, `can_be_evaluated=false`.
  In `inScope` (88). Not in `evaluatedBySomeone` (78). Cannot complete.

Two directions are not the same people:

- **1303 WT Employee G** — fully evaluated BY the manager-path; own Welcome
  tasks not finished (upward still owed).
- **1308 WT Employee N** — own Welcome tasks finished; manager-path eval not
  received.

`c_level_direct` on 1303 was seeded and did not move either Welcome counter.

Quoted as the stand `/admin/users` rendered it (full-access account, default
«работающие» filter):

```
Найдено: 96
Всего в базе: 99 · работают 96 · уволены 3
H1-2026: в охвате 88 · оцениваются кем-то 78
Зарегистрировались 13 из 96 работающих
Свои задачи закрыли 2 из 82 · их оценили все, кто должен 2 из 78
```

Live, the same line will read (SQL on `epe_2026` after deploy, campaign
tables still empty):

```
H1-2026: в охвате 78 · оцениваются кем-то 72
Зарегистрировались 3 из 86 работающих
Свои задачи закрыли 0 из 75 · их оценили все, кто должен 0 из 72
```

«Найдено» stays the filtered list (already on screen). With the default
employment filter that is 86, not 89.

---

## 3. What each number means (plain Russian)

These sentences are for the owner to check the line against reality without
reading code.

1. **Найдено** — сколько строк сейчас видно в таблице при текущих фильтрах.
2. **Всего в базе** — сколько учётных записей есть в системе вообще.
3. **Работают** — сколько из них не отмечены уволенными.
4. **Уволены** — сколько отмечены уволенными.
5. **В охвате** — сколько людей входит в текущий период (сейчас H1-2026).
6. **Оцениваются кем-то** — сколько из тех, кто в охвате, вообще подлежат
   оценке; шестеро, которых по решению владельца никто не оценивает, сюда не
   входят, хотя они в охвате.
7. **Зарегистрировались N из M работающих** — сколько людей завели пароль, из
   тех, кому уходит общее приглашение (ещё в штате; уволенные в знаменатель
   не входят).
8. **Свои задачи закрыли N из M** — из тех, кому на Welcome назначена хотя бы
   одна задача (самооценка, оценка своего руководителя, либо оценки всех
   своих подчинённых в охвате), сколько закрыли все свои.
9. **Их оценили все, кто должен N из M** — из тех, кого вообще оценивают,
   сколько уже получили полную оценку своего руководителя и все положенные
   оценки снизу. Канал C-level_direct в это число не входит: это общая
   оценка, а не долг одного человека одному человеку.

BUG-070 (HR «Статусы оценок») is a different screen and stays open. This line
does not silently reuse those three unlabelled denominators.

---

## 4. Deploy

Dated dump of live `epe_2026` before any live write:
`~/epe-live-dumps/2026-08-27-admin-users-summary/epe_2026_pre_adminusers_20260827T075552Z.dump`
(md5 `75f9ebae4228f36789d6e27bd6cf979a`, matched VPS / home / repo-backup
copy). No `epe_2026` row was written by this session.

`check_live_drift.py --expect-changed "API: Admin Get Users Data"` — OK. The
only intended delta.

Workflow PUT: `API: Admin Get Users Data` (`AwID96McjHKyk8WI`),
`updatedAt` 2026-08-26T13:46:55.454Z → **2026-08-27T07:56:39.858Z**, stayed
active, webhook path unchanged. Auth Guard `updatedAt` still
`2026-08-18T16:34:30.674Z`. Export refreshed:
`n8n_workflows/API_ Admin Get Users Data.json`. `route_guard_h1/` snapshots
were not regenerated.

Frontend: `./scripts/deploy_epe_frontend.sh` (lock + CAS).
**`releases/20260827T075704Z`** ← `current`. Previous
`releases/20260827T065624Z`.

After deploy (SSH `SELECT` / `readlink`):

| Check | Value |
|---|---|
| `current` | `releases/20260827T075704Z` |
| H1 `evaluation_started_at` | `2026-08-26 10:08:54.340312+00` (unchanged) |
| tables | **0/0/0/0** (no owner rows appeared) |
| users / terminated / in-scope | **89 / 3 / 78** |
| criteria / levels / grades md5 | identical to the 2026-08-26 snapshot |
| combined | `079177fbb9d52ea4c5b942fcecaed1c2` |

`npm test` **463/463**.

---

## 5. What was not done

- No write to a user, scope, termination, evaluation, catalogue, coefficient,
  grade or period row on live.
- Period not closed; `evaluation_started_at` not touched.
- `docs/EVALUATION_METHODOLOGY.md` was not created.
- BUG-070 left open (HR completion card).
- Mail was not sent.
