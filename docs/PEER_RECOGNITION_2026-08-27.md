# PEER_RECOGNITION — «Отметить коллегу» (2026-08-27)

**Brief:** PEER_RECOGNITION (Sol xhigh, fresh session, on the Mac).
**Verdict in one line:** the surface is **live** — a separate page, its own
menu item, one nomination per person per period, four server-side refusals,
readers limited to `admin` + `c_level`, **no count of nominations anywhere**,
and **zero contact with any money path**, proven by closing two identical
copies of the same database side by side.

The campaign was open and **moving** throughout this session: the four campaign
tables went **0/0/0/0 → 2/4/0/0 → 3/7/0/0** and registrations **5 → 12 → 13**
while the work ran. That is real employees answering the invitation, not drift.
Nothing in this brief wrote, edited or recomputed one of their rows.

Live now: frontend release **`20260827T114910Z`**, workflow
**`API: Peer Recognition`** id `KLDk6WmWZKsZ8GVX` (active, created
`2026-08-27T11:48:58.060Z`), migration **018** applied at `11:48`Z.

---

## What the owner gets (Russian)

Новая страница **«Отметить коллегу»** в разделе «Личные» — отдельный пункт
меню, а не поле внутри формы оценки. Её видит **любой сотрудник, который может
войти в систему**, включая тех, кто вне охвата H1 и не имеет ни одной задачи по
оценке: именно они видят помощь между отделами.

Человек может отметить **одного** коллегу и описать это тремя короткими
полями — ситуация, действие, результат. Отметку можно **заменить** сколько
угодно раз, пока период не закрыт; в базе она физически одна (ограничение
уникальности, а не обещание кода).

**Нельзя отметить:** себя, своего руководителя, своего подчинённого и
уволенного. Все четыре отказа проверяет сервер при сохранении, а не только
список на экране: прямой вызов маршрута с чужим номером отказывает так же.

**Читают только вы и C-level** — вы, Байрам Ураев, Джемал Гульбердыева, Джем
Дурукан, Хемра Ашыров, Мекан Юсупов. HR отметок не видит. Отмеченный человек
их не видит. Его руководитель их не видит. Проверено на живой системе кодами
ответа: HR — 403, обычный сотрудник — 403, без входа — 401.

**Количество отметок нигде не показывается** — ни числом, ни значком, ни
порядком сортировки, ни столбцом в выгрузке. Список идёт по времени, новые
сверху. Это не голосование и не рейтинг: отметки не входят ни в матрицу, ни в
итоговые баллы, ни в калькуляцию бонусов, ни в замороженные результаты
периода, ни в счётчики выполнения, ни в аналитику.

Тексты — ваши, дословно, без единого изменения. Две фразы написал исполнитель
и они помечены ниже как его (§9).

---

## 1. What was built

| Piece | Where |
|---|---|
| Table `performance_db.peer_recognitions` | `migrations/018_add_peer_recognitions.sql` |
| Workflow `API: Peer Recognition` (3 routes, 23 nodes) | `scripts/build_route_guard_workflows.py` §20 |
| Page «Кто помог вам в этом полугодии» | `src/pages/PeerRecognition.jsx` |
| Reader page «Отметки коллег» | `src/pages/AdminPeerRecognition.jsx` |
| Data hook | `src/hooks/usePeerRecognition.js` |
| Routes `/recognition`, `/admin/recognition` | `src/App.jsx` |
| Menu item «Отметить коллегу» (all) + «Отметки коллег» (admin/c_level) | `src/components/Sidebar.jsx` |
| Endpoints | `src/config/api.js` |

### The table

```
id bigserial PK · period_id → evaluation_periods · author_id → users ·
nominee_id → users · situation text · action text · outcome text ·
created_at · updated_at
UNIQUE (period_id, author_id)          -- one per person per period
CHECK  (author_id <> nominee_id)       -- self-nomination impossible in the DB
CHECK  (btrim of all three <> '')      -- an empty nomination cannot be stored
INDEX  (period_id, created_at DESC)    -- the reader's ordering, by TIME
```

**No numeric column. No foreign key into `evaluations`, `evaluation_scores`,
`score_corrections` or `period_results`, in either direction.** There is
deliberately **no index on `nominee_id`**: the only query it would make cheap is
"how many times was this person named", and that query must never run.

### The three routes

| Route | Who | What |
|---|---|---|
| `GET /api/recognition/form` | any authenticated session, no role required | period, the actor's own nomination, `colleagues` (may be named) and `blocked` (may not, with the reason in words) |
| `POST /api/recognition/save` | any authenticated session | upsert onto `(period, author)`; refuses self / own manager / own report / terminated / unknown / blank |
| `GET /api/recognition/list` | `admin` + `c_level` only | the period's nominations, newest first, with author and nominee names and the three texts |

The save statement re-asserts **every** refusal inside its `target` CTE, so a
body hand-made against a graph that changed a second ago writes zero rows
rather than the wrong row — the BUG-041 rule.

### Period binding, and the one thing this brief decided for itself

The routes bind to the **active leaf period** — `is_active AND status='active'
AND period_type <> 'annual' AND no children` — the same expression the
employment and period-scope routes already use.

**Deliberately NOT gated on `evaluation_started_at`.** The brief requires that
people out of scope of H1 can nominate; they have no evaluation tasks at all,
and a nomination is not an evaluation. Close ends it: once the period closes
there is no active leaf and the save route answers 409 `NO_ACTIVE_PERIOD`,
which is exactly "replaceable until the period closes". **Surfaced for the
owner, not resolved by fiat:** if he wants the surface to open only when the
campaign opens, it is a one-line change to the two SQL predicates.

---

## 2. The stand

Restored from a fresh `pg_dump` of live taken **2026-08-27 11:13:35Z**, md5
equal on both sides — VPS `7f1af05ec224089cb9961cfb4bfb4e8e`, Mac
`~/EPE_ROLLBACK/2026-08-27-peer-recognition/epe_2026_prerecognition_20260827T111335Z.dump`
`7f1af05e…`. Migration 018 was applied **to the stand only**; the campaign came
across already started. Two containers, `epe-recognition-n8n` (:25679) and
`epe-recognition-n8n-ctl` (:25680), both carrying the working-tree surface.

Both databases dropped and both containers removed at teardown;
`/root/epe_stand_tmp` is empty; remaining databases on `postgres_n8n` are
`epe_2026, postgres`.

---

## 3. Proof §1 — the routes (`scripts/prove_recognition.py`, 37/37 PASS)

Artifact: `backups/2026-08-27-peer-recognition/proof_stand.json` (gitignored).

| § | What was proved |
|---|---|
| 1 | form 200 for an employee; self / own manager / own report arrive in `blocked` with the reason; a terminated person is in **neither** list; the nominees ARE offered |
| 2 | one nomination stored, three texts byte-for-byte as sent |
| 3 | replacement → **still exactly one row, the same row id**, new nominee |
| 4 | direct route calls refused: self 422 `RECOGNITION_SELF`, own manager 422 `RECOGNITION_OWN_MANAGER` (the owner's sentence verbatim), own report 422 `RECOGNITION_OWN_REPORT`, terminated 422 `NOMINEE_TERMINATED`, unknown 404 `NOMINEE_NOT_FOUND`, blank 422 `RECOGNITION_TEXT_REQUIRED` — and the row count did not move |
| 5 | Aysoltan Esenova (31), `is_in_scope=false / hired_after_period_end`, sees the form and saves a nomination — 200 |
| 6 | list: admin 200, c_level 200, hr **403**, manager **403**, employee **403**, the nominated person **403**, unauthenticated **401 `TOKEN_MISSING`**; HR can still *nominate* (200 on the form) |
| 7 | the reader sees author + nominee + three texts; ordering is by time alone; **no key matching `count\|total\|rank\|rating\|score\|weight\|index\|top\|leader\|badge` in any recognition payload** |
| 8 | **19 other route payloads walked** — employees (×2), profile, history, check-self-review, check-evaluated, get-my-manager, criteria, evaluations-matrix, all-evaluations, analytics, admin roster, coefficients, HR status, manager-subordinates-matrix, periods, annual roll-up, details-by-user, employee events — all 200, none carries the nomination's marker or the word "recognition". The same check confirms the marker **is** present where it should be, so the walk cannot pass vacuously |
| 9 | campaign tables identical before/after; `evaluation_started_at` unchanged |

---

## 4. Proof §2 — the money, control against treatment (`scripts/prove_recognition_close.py`, 10/10 PASS)

Artifact: `backups/2026-08-27-peer-recognition/proof_close.json`.

Evaluations were seeded on the stand (`scripts/seed_recognition_close.sql`) —
four manager evaluations, two `c_level_direct`, one self-review, deliberately
including **both nominated people** — the database was dumped, and that ONE dump
was restored into two databases. The only difference between them: the control
had its two `peer_recognitions` rows deleted.

Every money input fingerprinted identical on both sides
(`9d24671e3991d08ff65634300ad19922`). H1 was then closed in both by the **real
route** (`POST /api/periods/close`, admin, one container each).

| | treatment (with nominations) | control (without) |
|---|---|---|
| frozen `period_results` rows | **89** | **89** |
| md5 of every frozen row | **`565faa9987d38b062b5a68a6c2b08bb1`** | **`565faa9987d38b062b5a68a6c2b08bb1`** |

Row for row identical, including the four rows that carry money — and two of
those four are the nominated people:

```
period|user|in_scope|has_data|mgr |upw|c_lvl|self|final |index
     2|   4|true    |true    |6.50| ~ |  ~  |  ~ |6.5000| 84.0000
     2|   7|true    |true    |7.25| ~ |7.00 |  ~ |7.1667|207.4800   ← nominated
     2|   8|true    |true    |8.00| ~ |8.50 |7.67|8.1667| 92.2320   ← nominated
     2|  23|true    |true    |5.75| ~ |  ~  |  ~ |5.7500| 53.0200
```

The close response carries no recognition key
(`{"success":true,"closed":true,"period_id":2,"results_stored":89,"in_scope":78,"no_data":74,…}`),
`period_results` has no recognition column, and the nominations survived the
close unrewritten.

---

## 5. Proof §3 — the browser walkthrough (stand, real logins)

Real logins through the real login route (stand-local passwords, dropped with
the stand). Screenshots were taken at each step.

1. **Oksana Borisenkova (70, employee)** — «Отметить коллегу» is in «Личные».
   The page renders the owner's title, three paragraphs, picker and three
   labelled fields with their hints.
2. **Own manager** — searched «Aysha», clicked her: greyed, and the screen
   answers **«Своего руководителя здесь отметить нельзя — для этого есть оценка
   «снизу вверх» в ваших задачах.»**
3. **Self** — searched «Oksana», clicked herself: **«Себя отметить нельзя.»**
4. **Terminated** — searched «Orusov»: **«Никого не найдено»**. He is not in
   the picker at all.
5. **Nomination** — Arslan Annayev + three texts → **«Отметка сохранена»**.
   Row 10 stored, `created_at = updated_at`.
6. **Replacement** — same page, Anton Markin + three new texts → **«Отметка
   обновлена»**. Still row **10**, `nominee_id` 8 → 7, one row for the author.
7. **Own report** — logged in as **Aysha Suvhanova (15, manager)**, searched
   «Oksana»: **«Своего подчинённого здесь отметить нельзя.»**
8. **Out of scope** — logged in as **Aysoltan Esenova (31)**. Her Welcome says
   «Вы вне охвата текущего периода оценки»; she has **no** «Самооценка» and no
   «Оценить руководителя» in the menu — and she **does** have «Отметить
   коллегу», and nominated Arslan Annayev successfully.
9. **HR (Liya Dmitriyeva, 52)** — typed `/admin/recognition` → redirected to
   `/hr/dashboard`; the reader page never renders. Her own session calling the
   API directly: **403 `ROLE_FORBIDDEN`**. Her menu has «Отметить коллегу» (she
   may nominate) and no reader entry. Her completion counters show no
   recognition figure.
10. **Manager (Yelena Son, 88 — manager of BOTH nominated people)** —
    `/dashboard`, `/team`, `/team-scores` walked: her team cards for Anton
    Markin and Arslan Annayev show no badge, no count, no trace. Typed
    `/admin/recognition` → redirected to `/welcome`.
11. **The nominated person (Arslan Annayev, 8)** — `/profile`, `/history`,
    `/welcome` walked: no trace. The only «Отметить коллегу» on his screen is
    his own menu item, i.e. the surface where *he* may name somebody.
12. **C-level (Jemal Gulberdiyeva, 47)** — «Отметки коллег» shows both
    nominations with author names, departments, timestamps and the three texts,
    newest first. Scanned for a tally (`\d+ отмет|раз|шт|из`): **none**.
13. **Admin (Alexander, 2)** — fifteen screens walked and scanned for the
    nomination's text and for the word "recognition": `/admin/users`,
    `/admin/periods`, `/admin` (criteria), `/admin/scoring`, `/analytics`,
    `/admin/all-evaluations`, `/admin/evaluations-matrix`,
    `/admin/final-scores`, `/admin/bonus-calculation`, `/admin/annual-rollup`,
    `/admin/score-calculator`, `/dashboard`, `/team-scores`, `/profile`,
    `/history` — **no trace on any of them**. `/admin/users` still summarises
    the campaign with its own populations and no recognition counter.

---

## 6. Zero drift on everything that already existed

The builder is shared with 19 other workflows, so the deploy proves the change
is additive before it writes anything: it regenerates the whole surface from
`HEAD`'s builder and from the working tree and compares byte for byte.

```
old files: 19   new files: 20
only in NEW: peer-recognition.json
byte differences on the 19 shared files: none
```

`deploy_peer_recognition.py` re-runs that comparison itself and refuses if a
single existing file has moved. It carries **no UPDATES list at all**: a brief
that must not change any existing route should not have the machinery to.

Frontend diff: `+714 / −1` across four files. The one deletion is the
`lucide-react` import line, re-added with `HeartHandshake` appended.

---

## 7. The live operation

| Step | When (UTC) | Evidence |
|---|---|---|
| Baseline read | 11:05:08 | campaign **0/0/0/0**, 89 users, 3 terminated, H1 78/89 in scope, registered 5, coefficients `079177fb…` |
| Dump for the stand | 11:13:35 | md5 `7f1af05e…` both sides, Mac copy outside the repo |
| Re-read before the first write | 11:47:51 | campaign **2/4/0/0**, registered **12** — employees are working |
| **Anchor dump immediately before the migration** | **11:48:06** | md5 `307b08ddd560a84d616b22dc4276e0b8` on the VPS and on the Mac |
| Migration 018 on live | 11:48 | table + 3 constraints + 3 FKs + 2 indexes verified by `\d`; 0 rows; campaign still 2/4/0/0 |
| Workflow created and activated | 11:48:58 | id `KLDk6WmWZKsZ8GVX`; total 60 → **61**, active 35 → **36**; Auth Guard `updatedAt` still `2026-08-18T16:34:30.674Z` |
| Frontend deployed (locked compare-and-swap) | 11:49:10 | `releases/20260827T075704Z` → **`releases/20260827T114910Z`**, gates passed, no conflict |
| Live verification, read-only | 11:50 | 17/17 PASS, below |
| Final invariant read | 11:51:01 | campaign **3/7/0/0**, registered **13**, coefficients `079177fb…` **identical** |

**Rollback.** The anchor dump is the record of live at 11:48:06Z, but restoring
it would now destroy real employee work. The rollback for *this* change is
narrower and lossless: deactivate/delete workflow `KLDk6WmWZKsZ8GVX`, flip
`/var/www/epe/current` back to `releases/20260827T075704Z`, and
`DROP TABLE performance_db.peer_recognitions`. Nothing else in the database was
touched, so nothing else has to come back.

### Live verification (`scripts/verify_recognition_live.py`, 17/17 PASS)

Read-only by construction: every call either reads, or is a save the route must
refuse — and a refused save writes zero rows, re-proved by counting the table
before and after. The only live write was four short-lived `auth_sessions` rows,
deleted in a `finally` block.

- unauthenticated `GET form` / `GET list` / `POST save` → **401 `TOKEN_MISSING`**
- form as an ordinary employee → **200**, bound to period **2**
- that actor, their manager and their reports arrive **blocked**, never offered
- the three terminated people are in **neither** list
- live saves refused: self **422**, own manager **422**, terminated **422**,
  unknown **404**
- list: admin **200**, c_level **200**, **hr 403**, **employee 403**
- no count-shaped key in any live recognition payload
- **`peer_recognitions` 0 rows before and 0 after** — this verification stored
  nothing
- `evaluation_started_at` still `2026-08-26T10:08:54.340312Z`

### Campaign invariants across the whole session

| Quantity | Start (11:05Z) | End (11:51Z) | Reading |
|---|---|---|---|
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | 0 / 0 / 0 / 0 | **3 / 7 / 0 / 0** | **real employees submitting** — untouched by this brief |
| registered accounts | 5 | **13** | real registrations after the invitation |
| `evaluation_started_at` | `2026-08-26 10:08:54.340312Z` | identical | — |
| users / terminated | 89 / 3 | 89 / 3 | — |
| roles | 1 admin, 5 c_level, 13 manager, 68 employee, 2 hr | identical | — |
| H1 participants / in scope | 89 / **78** | 89 / **78** | — |
| Annual 2026 participants / in scope | 89 / 86 | 89 / 86 | — |
| criteria md5 | `fc618757…` | `fc618757…` | = snapshot |
| `score_coefficients` md5 | `317e09e8…` | `317e09e8…` | = snapshot |
| grades md5 | `946b30a5…` | `946b30a5…` | = snapshot |
| **combined** | **`079177fb…`** | **`079177fb…`** | **= `docs/coefficients/H1-2026_coefficients_20260826T044844Z.md`** |

No user, scope, termination, evaluation, score, correction, catalogue,
coefficient, grade or period write. No mail. No invite. No container restart
outside the stand. **§4 of HANDOVER was not edited** — md5 of the section
`4e1aded6c81751eb20fae7b958484f3f` before and after this session's HANDOVER
measurement update.

---

## 8. What this feature can never reach

Proven by walking payloads, not by asserting:

| Surface | How it was shown clean |
|---|---|
| evaluations matrix | payload walk (§3 §8) + admin browser walk |
| final scores | payload walk + admin browser walk |
| bonus calculation | admin browser walk (11 454 chars, no trace) |
| **close dataset** | close response payload inspected; **89 frozen rows md5-identical** with and without nominations |
| `period_results` | column list carries no recognition column; identical row-for-row |
| completion counters | `/api/employees`, HR status, `/admin/users` summary — all walked |
| analytics | payload walk + browser walk |
| every export | no export builder was modified; the only frontend files that mention recognition are the five new/edited ones, none of which is an export path; the admin roster payload behind the Excel button carries no marker |

---

## 9. Surfaced, not resolved

1. **Two sentences are mine, not the owner's.** He wrote the manager refusal;
   the other two blocked reasons had no text in the brief, so I wrote them:
   **«Себя отметить нельзя.»** and **«Своего подчинённого здесь отметить
   нельзя.»** Both live in one place
   (`RECOGNITION_BLOCK_MESSAGES` in the builder) and are a one-line change.
2. **The started gate.** The routes are bound to the active leaf period and
   **not** to `evaluation_started_at` (§1). This is what lets an out-of-scope
   person nominate; it also means the page would work during a future
   preparation window, before «Запустить оценку». His call.
3. **Whether the reader should show the nominee's name.** The brief says a
   reader sees "the author's name and the three texts". The nominee's name is
   shown too — a nomination without the person named is not a record of
   anything. If he wants only the texts, say so.
4. **Nothing ages out.** A nomination stays readable after the period closes,
   through `?period_id=`. There is no retention rule and no deletion route —
   deliberate, but it is a policy decision nobody has made.
5. **A reader can still count by eye.** The system displays no count anywhere,
   but a list of rows can be counted by a human scrolling it. That is inherent
   in showing the content at all; the rule kept is that nothing computes,
   stores, sorts by or displays a tally.
6. **I emptied `/root/epe_stand_tmp`** per the PROJECT_RULES teardown checklist.
   That removed `epe_2026_pre_adminusers_20260827T075552Z.dump`, a leftover the
   previous brief had surfaced. It has a local copy at
   `backups/2026-08-27-admin-users-summary/` — nothing was lost.
7. **`n8n_workflows/API_ Peer Recognition.json`** is a fresh tracked export of
   the live definition. The nine stale top-level exports named in BUG-045 are
   untouched.

---

## 10. Session hygiene

- Read-only until the anchor dump; the dump preceded the first live write; Mac
  copy outside the repo; md5 equal on both sides; VPS copies of both dumps
  removed at teardown.
- Live writes this session: `CREATE TABLE performance_db.peer_recognitions`
  (empty), one workflow created + activated, one frontend release flipped, and
  four short-lived `auth_sessions` rows that were deleted again. **Zero
  nomination rows on live.**
- Stand: two databases, two containers — all four gone. `postgres_n8n` holds
  `epe_2026, postgres`.
- No extension created on live. No container restarted outside the stand.
- `git status` clean at start.
