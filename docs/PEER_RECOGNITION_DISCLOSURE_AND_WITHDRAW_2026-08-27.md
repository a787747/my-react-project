# PEER_RECOGNITION_DISCLOSURE_AND_WITHDRAW (2026-08-27)

**Brief:** PEER_RECOGNITION_DISCLOSURE_AND_WITHDRAW (Grok 4.6, fresh session, on the Mac).
**Verdict in one line:** the page now says who reads the text, and the author
can remove their own nomination while the period is open — the row is deleted,
not blanked; the server checks identity, not the browser.

The campaign was open and **moving** throughout. Live campaign tables went
**11/23/0/0 → 23/68/0/0** and registrations **16 → 18** while this session
ran; `peer_recognitions` went **1 → 2**. That is real employees writing, not
this brief. Nothing here deleted, edited or recomputed a live evaluation or a
live nomination.

Live now: frontend **`20260827T124349Z`**, workflow `API: Peer Recognition`
(`KLDk6WmWZKsZ8GVX`) PUT **2026-08-27T12:43:34.472Z**, still active, 32 nodes,
four webhooks. Auth Guard `updatedAt` still `2026-08-18T16:34:30.674Z`.
No migration — 018 already on live.

---

## What the owner gets (Russian)

На странице «Отметить коллегу», **над полями и дословно**, появилась фраза:

**«Отметку читает только высшее руководство компании. Отмеченный человек и его
руководитель её не видят.»**

Три прежних абзаца не изменены ни на знак.

Автор может **снять свою отметку**, пока период открыт. Строка удаляется из
базы — не обнуляется. После снятия у автора снова нет отметки, и он может
отметить заново (по-прежнему ровно одну). Чужую отметку снять нельзя: сервер
смотрит на человека из токена, а не на то, что прислали в теле. После закрытия
периода снять нельзя — тот же отказ, что и у замены: **409 `NO_ACTIVE_PERIOD`**.

Это не удаление администратором. Это действие автора над своей строкой.

Тексты кнопки и подтверждения написал исполнитель (ниже, дословно).

**Срок хранения не решён.** Отметки переживают закрытие периода. Что с ними
делать — отдельное решение, не сегодня. Цифры и варианты — в §6.

---

## 1. Disclosure

Owner's sentence, verbatim, fourth paragraph of the existing intro card,
**above** the nominee search and the three text fields:

```
Отметку читает только высшее руководство компании. Отмеченный человек и его руководитель её не видят.
```

The three owner intro sentences are byte-identical to this morning. The
sentence cannot be paraphrased; it rendered as written. Browser walk: the
sentence sits at character 758 of the page text, the field label «Кого вы
отмечаете» at 861.

Live bundle `/var/www/epe/current/assets/PeerRecognition-Bme9KtPO.js` contains
the same sentence.

---

## 2. Withdraw

| Piece | Where |
|---|---|
| `POST api/recognition/withdraw` | `scripts/build_route_guard_workflows.py` — same workflow, fourth webhook |
| Frontend button + confirm | `src/pages/PeerRecognition.jsx` |
| Hook | `src/hooks/usePeerRecognition.js` → `withdraw({ recognitionId })` |
| Endpoint constant | `src/config/api.js` `RECOGNITION_WITHDRAW` |

No new table. No new foreign key. `DELETE FROM performance_db.peer_recognitions`
with `r.author_id =` the token actor **and** the active-leaf predicate
re-asserted (BUG-041). Client `author_id` is ignored.

| Call | Status | Error |
|---|---|---|
| own row, period open | 200 | — ; body `{ withdrawn: true, message: "Отметка снята" }` |
| someone else's row (also with a forged `author_id` in the body) | **403** | `RECOGNITION_NOT_OWN` |
| missing `recognition_id` | **422** | `INVALID_RECOGNITION_ID` |
| unknown id | **404** | `RECOGNITION_NOT_FOUND` |
| no token | **401** | `TOKEN_MISSING` |
| own row, period closed | **409** | `NO_ACTIVE_PERIOD` |

### Executor texts (quote them; they are not the owner's)

| Where | Text |
|---|---|
| Button | **Снять отметку** |
| Confirm | **Снять отметку? Текст будет удалён, и вы снова будете без отметки.** |
| In progress | Снятие... |
| Server success | **Отметка снята** |
| Server, not own | Снять можно только свою отметку |
| Server, missing id | Не указана отметка |
| Server, unknown id | Отметки нет |

The 409 message is the same sentence the save route already uses:
«Сейчас нет открытого периода — отметить коллегу можно только внутри периода».

---

## 3. The stand

Fresh `pg_dump` of live **before the first live write**,
`epe_2026_withdraw_20260827T121801Z.dump`.

| Side | Path | md5 |
|---|---|---|
| VPS | `/root/epe_stand_tmp/epe_2026_withdraw_20260827T121801Z.dump` | `f5e8968e0c283b3b84d9cf756f9601ae` |
| Mac | `~/EPE_ROLLBACK/2026-08-27-peer-recognition-withdraw/` (same filename) | `f5e8968e0c283b3b84d9cf756f9601ae` |

Campaign at dump time (12:18:01Z): **11/23/0/0**, one live nomination
(`id=1`, author 5) copied onto the stand and never rewritten.

Two throwaway databases, both restored from that dump, campaign left open:

| Stand | DB | Container | Port | Role |
|---|---|---|---|---|
| Proof | `epe_recognition_20260827_1218` | `epe-recognition-n8n` | :25679 | API proof, then closed on the stand |
| UI | `epe_recognition_ui_20260827_1226` | `epe-recognition-n8n-ui` | :25681 | Browser walk, period left open until teardown |

No extension on live. No live container restarted.

### API proof (`scripts/prove_recognition_withdraw.py`)

25 of 26 checks passed. The one FAIL is a **test prefix**, not the product:
after author 70 withdrew id 2, the c_level list correctly held `[1, 3]`;
the assertion treated `WD-4K9M-SIT` as a substring of author 31's
`WD-4K9M-SIT2`. The script was corrected; the closed stand was not re-run
because the remaining 25 checks already hold the acceptance codes.

| Check | Result |
|---|---|
| 70 withdraws own row | **200**, message «Отметка снята»; row gone, not blanked; form `my_nomination=null` |
| 31 against 70's row | **403 `RECOGNITION_NOT_OWN`** |
| same call with forged `author_id=70` | **403 `RECOGNITION_NOT_OWN`** |
| missing id / unknown id / no token | **422 / 404 / 401** |
| stand H1 closed by the real `POST /api/periods/close` (89 `period_results`) | 200 |
| 70 withdraws own after that close | **409 `NO_ACTIVE_PERIOD`** |
| both remaining nominations survived the close and the refused withdraw | yes |
| dump-originated id 1 fingerprint | unchanged `1:5:fd1e2ac1…` |
| `evaluation_started_at` | unchanged |
| evaluations / scores / corrections on the stand | **11/23/0** unchanged; `period_results` 89 from the **stand** close only |

### Cross-author on the open UI stand (same stand as the browser)

After the walk, author 70 held id 6. Author 31 withdrawing it:

`403 {"error":"RECOGNITION_NOT_OWN","message":"Снять можно только свою отметку"}`

Forged `author_id` in the body: same 403. Unauthenticated 401, missing id 422,
unknown id 404. Author 31's `UI-31-SIT` row stayed throughout.

### Browser walk (`scripts/walk_recognition_withdraw.mjs`, 15/15 PASS)

Headless Chrome against local Vite `:5199` → UI-stand proxy. Cursor browser MCP
was down (`Server not found`); the walk used Chrome CDP instead.

- Disclosure line present verbatim, **before** the fields; three intro
  sentences unchanged.
- Employee (Oksana, 70) nominates Arslan.
- C-level (Jemal, 47) sees that nomination **and** the other employee's
  `UI-31-SIT`. No tally words on the list.
- Oksana withdraws (confirm overridden to accept). Form returns to «Отметить»,
  no «Вы уже отметили».
- C-level no longer sees Oksana's withdrawn text; still sees `UI-31-SIT`.
- Oksana nominates again (Anton) — exactly one «Вы уже отметили».
- Nominee `/profile` `/history` `/welcome`, manager `/dashboard` `/team`
  `/team-scores`, and the admin screens
  (`/admin/users` `/admin/periods` `/admin` `/admin/scoring` `/analytics`
  `/admin/all-evaluations` `/admin/evaluations-matrix` `/admin/final-scores`
  `/admin/bonus-calculation` `/admin/annual-rollup` `/admin/score-calculator`
  `/dashboard` `/team-scores` `/profile` `/history`) — **no nomination text
  and no count**.

Static builder/page test: **3/3 PASS**.

---

## 4. The live operation

| Step | When (UTC) | Evidence |
|---|---|---|
| Dump before any live write | 12:18:01 | md5 `f5e8968e…` both sides |
| Re-read before first write | 12:43 | campaign **23/68/0/0**, peer **2** (ids 1, 3), registered **18** |
| Workflow PUT | 12:43:34 | `KLDk6WmWZKsZ8GVX` 3 → 4 webhooks; still active; Auth Guard frozen |
| Campaign during PUT | 12:43 | **23/68/0/0**, peer **2** — unchanged |
| Frontend CAS | 12:43:49 | `releases/20260827T114910Z` → **`releases/20260827T124349Z`** |
| Live verify | 12:44 | 8/8 PASS, below |
| Final invariant read | 12:44:58 | campaign **23/68/0/0**, peer **2** (ids 1 author 5, 3 author 12) |

**Rollback of this change, lossless:** PUT the previous `API: Peer Recognition`
graph (three webhooks, export from this morning) and flip
`/var/www/epe/current` back to `releases/20260827T114910Z`. Do **not** restore
the 12:18Z dump — that would destroy real employee work written since.

Restoring the dump would also remove live nomination id 3, which did not exist
at 12:18Z.

### Live verification (`scripts/verify_recognition_withdraw_live.py`, 8/8 PASS)

Constructed so it **cannot** delete a real row: every withdraw either has no
token, a missing id, a fabricated id, or a foreign live id that is not the
actor's. Table ids and count compared before and after.

- unauthenticated withdraw → **401 `TOKEN_MISSING`**
- form still **200**, period 2
- missing id → **422 `INVALID_RECOGNITION_ID`**
- fabricated id 999999 → **404 `RECOGNITION_NOT_FOUND`**
- author 70 against live foreign id (not theirs) → **403 `RECOGNITION_NOT_OWN`**
- c_level list still **200**
- **`peer_recognitions` 2 rows, ids 1,3, before and after**
- `evaluation_started_at` still `2026-08-26 10:08:54.340312+00`

Four short-lived `auth_sessions` rows were inserted for the tokens and deleted
in `finally`. No nomination was stored or removed.

---

## 5. Campaign invariants

| Quantity | Dump (12:18Z) | Before first write (12:43Z) | After verify (12:44Z) | Reading |
|---|---|---|---|---|
| evaluations / scores / corrections / period_results | 11 / 23 / 0 / 0 | **23 / 68 / 0 / 0** | **23 / 68 / 0 / 0** | **employees submitting** — this brief wrote none of them |
| `peer_recognitions` | 1 (id 1) | **2** (ids 1, 3) | **2** (ids 1, 3) | second nomination is a real employee (author 12); not ours |
| registered accounts | 16 | **18** | **18** | real registrations |
| `evaluation_started_at` | `2026-08-26 10:08:54.340312Z` | identical | identical | — |
| users / terminated | 89 / 3 | 89 / 3 | 89 / 3 | — |
| roles | 1 / 5 / 13 / 68 / 2 | identical | identical | — |
| H1 in scope | 78 / 89 | 78 / 89 | 78 / 89 | — |
| criteria md5 | `fc618757…` | `fc618757…` | `fc618757…` | = snapshot |
| `score_coefficients` md5 | `317e09e8…` | `317e09e8…` | `317e09e8…` | = snapshot |
| grades md5 | `946b30a5…` | `946b30a5…` | `946b30a5…` | = snapshot |
| **combined** | **`079177fb…`** | **`079177fb…`** | **`079177fb…`** | **= `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`** |

No user, scope, termination, evaluation, score, correction, catalogue,
coefficient, grade or period write on live. No mail. No invite. No container
restart outside the stand. **§4 of HANDOVER was not edited** — md5 of the
section `4e1aded6c81751eb20fae7b958484f3f` before and after this session's
HANDOVER measurement update.

---

## 6. Retention — report, do not resolve

Nominations **survive the close of a period**. There is no retention policy,
no delete-after-close, no anonymise, no ageing job. The list route can still
read a closed period by `?period_id=`. This brief did not add a deletion
route for anyone except the author, and only while the period is open.

**How many piles will accumulate.** The routes bind to an **active leaf**
(`period_type <> 'annual'`). Annual containers are not nomination periods.
Live periods today:

| id | name | type | status |
|---|---|---|---|
| 1 | Annual 2025 | annual | closed |
| 2 | H1-2026 | half_year | active — **the first pile** |
| 5 | Annual 2026 | annual | draft |

H2-2026 does not exist yet. The table itself is new (migration 018 this
morning), so **zero closed periods** of this free text exist. After this
season, if H2 is created as a leaf: **two** piles (H1-2026 + H2-2026). Then
**+2 per year**, unbounded, for as long as the table is left as it is.

Each pile is free text about a **named** colleague, written by a named
author, readable forever by admin and c_level.

**Options (owner decides later; none of these were built):**

1. **Keep forever** — current behaviour.
2. **Drop on close** — when the leaf closes, delete its nominations (or move
   them out of the reader). Withdraw after close becomes moot.
3. **Retain N years / N half-years**, then drop.
4. **Anonymise after close** — drop names, keep texts (or the reverse).
5. **Drop children when the annual container closes** — H1+H2 of a year
   disappear together after the annual freeze.
6. **Grace-period withdraw after close** — author can still remove their row
   for some days; then it sticks.

A related call already sat in this morning's report (§9.4) and is still open.
Filed as **BUG-080** so it does not vanish into a closed brief.

---

## 7. Session hygiene

- Dump preceded the first live write; Mac copy outside the repo; md5 equal on
  both sides.
- Live writes this session: one workflow PUT, one frontend flip, four
  short-lived `auth_sessions` rows that were deleted again. **Zero nomination
  rows written or deleted on live.**
- Stands: both databases and both containers dropped; `/root/epe_stand_tmp`
  emptied of this dump. Leftover databases: `epe_2026`, `postgres`.
- No extension created on live. No container restarted outside the stand.
- `git status` clean at the end.

**Commit:** `c3a60bf41604f7af894be4ba3ee9be1aed2b6c51`.
