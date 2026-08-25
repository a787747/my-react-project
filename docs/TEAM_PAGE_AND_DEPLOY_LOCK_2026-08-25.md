# /team was never broken for a manager — it was empty; and two deploys can no longer race (2026-08-25)

**Brief:** TEAM_PAGE_AND_DEPLOY_LOCK. **Decision:** D-0825-9.

**Outcome in one line: the undeclared `setLoadingSelfReviews` never fired for a
manager, because an admin-only API refused them three lines earlier and left the
page empty — so BUG-063 was a tidy-up and BUG-012 was the launch blocker; /team
now reads the manager-scoped route and shows the real team, proven on a
throwaway stand with the campaign actually open, where a manager logged in, saw
her 11 in-scope subordinates with both terminated ones absent, submitted an
evaluation and saw it land; and the deploy script now refuses a concurrent
deploy twice over — demonstrated, not asserted.**

Live now: frontend release **`20260825T165732Z`**, symlink flipped 16:57:41Z.
**No write to `epe_2026` of any kind** — not even a probe session — no workflow
write, second gate still unpressed.

---

## 1. The verdict on /team: no, it did not throw for a manager

The brief asked for this first, and the answer is not the one the bug title
suggests.

### 1.1 What the code did

```js
const loadStatuses = async () => {
  if (visibleUsers.length === 0) return;          // ← the manager stops here
  try {
    setLoadingSelfReviews(true);                  // ← never declared
    const [selfReviewsRes, hrStatusRes] = await Promise.all([ … ]);
    …
  } catch (err) {
    logger.error('Ошибка загрузки статусов:', err);
  } finally {
    setLoadingSelfReviews(false);                 // ← throws again, uncaught
  }
};
loadStatuses();                                    // ← no await, no .catch
```

`visibleUsers` was built by walking the org tree out of `useUsers()`, which reads
`GET /api/admin-users-data` — a route whose guard is `required_roles: ["admin"]`.
A manager gets 403, `users` stays `[]`, `visibleUsers` is `[]`, and the effect
returns on its first line. The undeclared setter is unreachable for them.

### 1.2 What the browser did

Both runs are the **same build** (HEAD `6568461`) against the same stand with the
campaign open. Yelena Son (id 88, manager) logged in through the real form:

> **Моя команда — Подчинённых: 0 | Найдено: 0**
> «У вас нет подчинённых в системе.»

Console, verbatim:

```
[error] Failed to load resource: the server responded with a status of 403 (Forbidden)
[error] Ошибка загрузки пользователей: {… userMessage: Required role is missing, …}
```

No `ReferenceError`. The page rendered. She has **11** subordinates in H1 scope
and was shown none.

Then Alexander Petrosov (id 2, admin) typed the same URL — `/team` is
`ManagerRoute`, which admits `admin`, `c_level`, `hr` and `manager`, while the
sidebar link is rendered only for `role === 'manager'`:

> **Моя команда — Подчинённых: 30 | Найдено: 28**

```
[error] Ошибка загрузки статусов: {… message: setLoadingSelfReviews is not defined}
[error] Uncaught (in promise) {… message: setLoadingSelfReviews is not defined}
```

Twice, exactly as the code predicts: the call inside `try` is caught and logged,
the call in `finally` is not, and because `loadStatuses()` is invoked without
`await` or `.catch` it surfaces as an unhandled rejection rather than a render
error. **The page still rendered.** No white screen.

The damage was silent instead: the network log for that pass contains **no**
request to `/api/hr/evaluation-status` and none to `/api/check-self-review` from
this page — the throw happened before the `Promise.all`, so `selfReviewsStatus`
and `evaluationStatuses` were never populated and all 30 people showed as having
done nothing, whether or not they had.

### 1.3 The plain answer

| question | answer |
|---|---|
| Did `/team` throw for a **manager** before the fix? | **No.** The path is unreachable: the admin-only route 403s first and `visibleUsers.length === 0` returns before the setter. |
| Did it throw for an **admin** who typed the URL? | **Yes** — twice, one caught, one unhandled — and the page rendered anyway with every status column silently blank. |
| Was BUG-063 a launch blocker? | **No.** A tidy-up, with one real consequence for admins: wrong-looking status columns, no error a user would see. |
| Was there a launch blocker on this page? | **Yes — BUG-012.** «Список команды» sits in every manager's sidebar and showed an empty list with a wrong explanation. That is the defect that would have met managers on day one. |

Both are fixed here, because outcome 2 required the page to actually work.

---

## 2. What changed, frontend only

`/team` now reads **`GET /api/employees`** — the same actor-scoped route the
manager dashboard uses. New hook `src/hooks/useTeamRoster.js`; `TeamView` no
longer imports `useUsers`, no longer walks the org tree, and no longer calls the
HR-only status route.

The server decides the scope, and that is the point:

```sql
FROM performance_db.users users
…
JOIN active_period ap ON true
JOIN performance_db.evaluation_period_participants epp
  ON epp.period_id = ap.id AND epp.user_id = users.id
 AND epp.is_in_scope = true
WHERE users.manager_id = ${actorId}
  AND ${actorCanEvaluate}
  AND COALESCE((SELECT is_in_scope FROM actor_scope), false)
```

Three consequences worth stating, because two of them are behaviour changes:

1. **A terminated subordinate cannot appear.** Termination writes
   `is_in_scope=false, exclusion_reason='terminated'` (D-0825-7), and the join
   drops the row. There is nothing to filter client-side — the row never arrives.
2. **Direct reports only, not the recursive subtree.** The old page walked
   `manager_id` recursively through the admin roster; for Alexander that was 30
   people. `/api/employees` is `WHERE users.manager_id = actorId`. `/team` and
   `/dashboard` now answer to one definition of "my team", server-enforced. The
   full roster remains at `/admin/users`, where the guard belongs.
3. **`JOIN active_period ap ON true` is an inner join**, and `active_period` is
   empty until «Запустить оценку» (D-0822-1). So **on live today the list is
   empty for everyone** — and the page now says why:

   > «Период «H1-2026» открыт, но оценка ещё не запущена. Список команды
   > появится, когда администратор её начнёт.»

   measured on the stand with the gate deliberately un-pressed. The old page said
   «У вас нет подчинённых в системе», which was false.

`/api/employees` carries no `role`, no `grade_name` and no `manager_name`, so the
page maps `grade_code → grade_name`, sets the manager column to the actor (true
by construction — they are all their direct reports), and `UserTable` now renders
the role badge only when a role is present. Status columns are the two the
payload can honestly fill: `has_self_review` → **Self**, `evaluated_by_actor` →
**Рук.** The third column («Сотр.», evaluations received from a person's own
subordinates) had no source once the HR route went, and is off.

Removed with it: `ManagerEvaluationDetailsModal` and `SubordinateEvaluationsModal`,
both wired as `onManagerEvaluationClick={undefined}` /
`onSubordinateEvaluationClick={undefined}` since the reporting-surface brief —
unreachable by construction, and fed by the route this change deletes. Their two
`no-unused-vars` errors go with them.

`npx eslint src`: **19 → 15 errors**, 13 warnings unchanged. The four that went
are this file's: two `setLoadingSelfReviews is not defined`, two dead handlers.
`npm test` **351/351**.

---

## 3. The stand walkthrough

**The stand.** `scripts/setup_team_throwaway.sh` → one throwaway DB
`epe_team_20260825_1642` restored from a fresh dump of live, an isolated n8n
`epe-team-n8n` on VPS loopback `:25679` at the same pinned image digest, the full
generated workflow surface, local vite through the tunnel. **No synthetic
people**: the org is the real one — 89 users, the real hierarchy, the owner's two
real terminations. The seed's only change is a password hash on ids 2 and 88 so
two real accounts can log in on the copy; it refuses to run against any database
not named `epe_team_%`, and the hashes are generated per run and passed in, so
nothing credential-shaped is committed.

**The campaign was opened on the stand**, through the real route:
`POST /api/periods/start-evaluation` → `200 {"already_started": false,
"evaluation_started_at": "2026-08-25T16:43:54.246Z"}`. Live was re-read
immediately after and `evaluation_started_at` was still NULL on all three
periods.

**The manager under test** is Yelena Son (88): 13 direct reports, of whom
**2 are terminated** — Kuvvat Garayev (51) and Murad Bayramov (66), both
`is_in_scope=false, exclusion_reason='terminated'` on H1. The page must show 11.

| # | step | on screen | ✓ |
|---|---|---|---|
| 1 | Yelena Son logs in through the real form | portal opens; «Оценка идёт — ваши задачи ниже» | ✓ |
| 2 | opens `/team` | «Список команды — **Найдено: 11** \| Самооценок: 0 \| Оценено мной: 0», «Прямых подчинённых в охвате: 11 · период: H1-2026» | ✓ |
| 3 | the 11 rows, read out of the DOM | Alp-Arslan Mametnazar, Anton Markin, Arslan Annayev, Cheper Atakayeva, Hojamuhammed Ashirov, Jemshit Karajayev, Nargiza Dovletgylyjova, Rakhim Kurbanov, Rovshan Yagmurov, Selbi Muradova, Suleyman Hudayberdiyev | ✓ |
| 4 | the terminated pair | absent by exact name **and** by e-mail; zero rows carry a «Уволен» badge; the employment control reads «Работают (11) · Уволены (0) · Все (вкл. уволенных) (11)» — even «Все» cannot surface them, because the server never sent them | ✓ |
| 5 | `/dashboard` | 11 «Оценить» cards — the same 11 | ✓ |
| 6 | opens the form for Alp-Arslan Mametnazar | «Категория: проектные · Участник проекта», «Самооценка ещё не отправлена», «Оценено: 0 из 6», submit disabled: «Оцените все критерии (6)» | ✓ |
| 7 | scores all six: 7, 8, 6, 9, 7, 8 | «Оценено: 6 из 6», submit enables to «Сохранить оценку» | ✓ |
| 8 | confirmation dialog | all six listed with zone labels — «Хорошо 7», «Выше нормы 8», «Хорошо 6», «Крупный вклад сверх роли 9», «Хорошо 7», «Высокий объём 8» | ✓ |
| 9 | «Подтвердить» | «Оценка сохранена! **Итоговый балл: 7.50**» — (7+8+6+9+7+8)/6, the plain average of formula #1 | ✓ |
| 10 | back on `/dashboard` | the card now reads «Оценен вами», «Балл: 7.5», «Общие: 4 ✓ Проект: 2 ✓», button «Редактировать» | ✓ |
| 11 | back on `/team` | «Найдено: 11 \| Самооценок: 0 \| **Оценено мной: 1**», green check under **Рук.** on Alp-Arslan's row only | ✓ |
| 12 | the stand database | `evaluations` id 31: evaluator 88, subject 4, period 2, source `manager`, `is_self_evaluation=false`, status `completed`, `calculated_score 7.50`; 6 `evaluation_scores` on criteria **3, 4, 8, 12, 13, 14** — the applicable set exactly (c_level_only 1/10 excluded, managers_only 2 excluded: the subject has no subordinates); `AVG(score_value) = 7.50 = calculated_score` | ✓ |
| 13 | the gate reverted on the stand, `/team` reloaded | «Найдено: 0» and «Период «H1-2026» открыт, но оценка ещё не запущена…» — what live shows today | ✓ |
| 14 | admin opens `/team` on the fixed build | «Найдено: 5» — Alexander's 5 direct reports; **no `ReferenceError`** | ✓ |

**Console for the entire fixed pass — steps 1 to 14 — is one line:**

```
[error] Failed to load resource: the server responded with a status of 401 (Unauthorized)
```

the pre-login unauthenticated call made before a token exists. Nothing else: no
403, no `ReferenceError`, no unhandled rejection. The only warning is the
pre-existing dev-only `Module "stream" has been externalized`, from the xlsx
import.

**Live during all of it:** `evaluations / evaluation_scores / score_corrections /
period_results` = **0 / 0 / 0 / 0**, re-read after the submit.

**Teardown:** container removed, `epe_team_20260825_1642` dropped (the drop loop
refuses any name without the prefix), `SELECT datname` reads **`epe_2026,
postgres`** only, the same six containers as before, tunnel closed, stand secrets
deleted. Nothing in host `/tmp`.

---

## 4. BUG-062 — a concurrent deploy now fails loudly

Two independent protections, because they catch different things.

**An exclusive lock**, held locally (`.epe-deploy.lock`, atomic `mkdir`, released
by an `EXIT` trap) and on the host (`/var/www/epe/.deploy.lock`) for the whole
upload-and-flip. Each records who holds it. Neither is ever broken automatically —
the refusal prints the exact `rm -rf` for a human who has checked.

**A compare-and-swap on the symlink**, which catches what a lock cannot: a flip
made by an older copy of the script, by hand, or from another machine. `current`
is read **before the build**, and re-read **inside the same remote command that
flips it**, so nothing can move between the check and the swap:

```sh
CURRENT="$(readlink "$ROOT/current" || true)"
if [ "$CURRENT" != "$BASELINE" ]; then
  printf 'CONFLICT expected=%s actual=%s\n' "$BASELINE" "$CURRENT"; exit 9
fi
ln -sfn "releases/$RELEASE_ID" "$ROOT/current"
```

### Demonstrated

**Two deploys, the second refused.** Deploy A started with the test hook
`EPE_DEPLOY_PAUSE_BEFORE_FLIP=90` (a delay only — it bypasses no gate and skips
no step). Deploy B was launched while A held the lock:

```
Refusing deploy: another deploy is already running in this checkout.
  lock: …/evaluation-portal/.epe-deploy.lock
  held by: pid=21394 user=a.petrosov started=2026-08-25T16:55:10Z
```

exit code **1**, and `readlink current` still `releases/20260825T162505Z`.

**The symlink check, against a flip the lock could not see.** While A was paused,
`current` was moved by a raw `ln -sfn` — exactly how yesterday's collision would
have arrived — to a probe release copied byte-for-byte from the live one
(`diff -r` clean, so the public bundle hash never changed:
`assets/index-BRRGqfGk.js` before and during). A then reached its flip:

```
CONFLICT expected=releases/20260825T162505Z actual=releases/20260825T000000Z-conflictprobe

Refusing deploy: /var/www/epe/current moved while this deploy was running.
  Somebody else deployed. Flipping now would revert their release.
  Nothing was changed: current still points where they left it.
  Release 20260825T165510Z is uploaded and unlinked; rebuild on top of what is
  actually live, then deploy again.
```

exit **1**, `current` still pointing at the probe — **A did not revert the other
party**, which is the whole behaviour yesterday lacked. Both locks were released
by the traps. The probe and A's unlinked release were then removed, `current`
restored to `20260825T162505Z`, release count back to 32, `Last-Modified`
unchanged, and the real deploy run cleanly afterwards.

---

## 5. BUG-040 — the gates no longer depend on the terminal

`rg` on this laptop is a shell function injected by the terminal snapshot;
`bash -c 'command -v rg'` exits 1 and `bash -c 'rg --version'` prints
`bash: rg: command not found`. Yesterday's other session ran the same script from
a terminal where Cursor had put a real `rg` on PATH, and its gates ran. A gate
whose outcome depends on which terminal launched it is not a gate — and the
failure mode is asymmetric: missing `rg` fails closed, present `rg` passes, so
nobody notices which happened.

Both gates now use `grep -r`, which is POSIX and present everywhere this project
runs, and the script **proves the tool works before trusting a negative result**:

```sh
test -s dist/index.html || die "Refusing deploy: dist/index.html is missing or empty."
command -v grep >/dev/null 2>&1 || die "Refusing deploy: grep is not available; the safety gates cannot run."
grep -r -q 'assets' dist/index.html \
  || die "Refusing deploy: the gate tool found nothing in dist/index.html, so a clean result would be meaningless."
```

That third line is the one that matters. Without it, a gate pointed at an empty
or missing `dist` reports "legacy URL absent" and passes — a vacuous pass reads
exactly like a clean bundle. **No shim was installed**, and none is needed: the
gates now run identically in every terminal, and the deploy that shipped this
release printed `gates: legacy :5678 absent, /webhook base present` on its way
through.

---

## 6. Deploy, and the proof that nothing else moved

| | |
|---|---|
| Release | **`20260825T165732Z`** |
| Symlink | `/var/www/epe/current` → `releases/20260825T165732Z` (was `releases/20260825T162505Z`) |
| Public | `index.html` `Last-Modified: Tue, 25 Aug 2026 16:57:41 GMT` |
| Releases on disk | 33 |
| Rollback target | `releases/20260825T162505Z` |

Verified on the served bundle over HTTPS, `assets/TeamView-BrJI74wK.js`:
`/api/employees` present; `setLoadingSelfReviews` **0 occurrences**;
`admin-users-data` **0 occurrences**; the preparation notice present.

### Live invariants after the deploy

| invariant | value |
|---|---|
| H1-2026 (id 2) | `status=active`, `is_active=true` |
| `evaluation_started_at` | **NULL on all three periods** — second gate unpressed |
| `evaluations` / `evaluation_scores` / `score_corrections` / `period_results` | **0 / 0 / 0 / 0** |
| users | **89**, of whom **2** terminated |
| participants in scope on H1 | **85** |
| `employment_events` | 2 — the owner's two terminations, unchanged |
| criteria fingerprint | `84f4d48ec37e658d9ace9dc035553c3a` |
| `score_coefficients` fingerprint | `c1c04b2791443979ebb045d06e008da2` |
| `grades` fingerprint | `dd39822cd44ba86fecfd5451891c2fae` |
| `EPE: Auth Guard` | `updatedAt=2026-08-18T16:34:30.674Z`, `active=false` — unchanged |
| workflow writes after 16:00Z | **0** |
| workflows | 34 active / 59 total |
| `auth_sessions` created after 16:00Z | **0** — no live login, not even a probe |

The three fingerprints are not asserted against a document: they were computed
**both** on live now **and** on the stand database, which was restored from the
`16:42Z` dump taken before any of this session's work and whose catalogue was
never touched. All three match. The catalogue, the level coefficients and the
grade coefficients are byte-identical to their pre-session state.

**The rollback anchor** was refreshed as the brief required — the `153238Z` one
predates the two terminations and is history:

| | |
|---|---|
| File | `epe_2026_teampage_20260825_1642.dump` |
| Taken | 2026-08-25 **16:42Z**, `pg_dump -Fc --no-owner --no-acl` of live `epe_2026` |
| Size | **87 849 bytes** |
| md5 | **`5ecbf2c0c908340f4e28b63a36950129`** — verified equal on the VPS and on the Mac |
| On the Mac | `~/EPE_ROLLBACK/2026-08-25-teampage/`, mode 600, **outside the repository** |

---

## 7. Surfaced, not resolved

- **`/team` is empty on live until «Запустить оценку» is pressed.** That is
  D-0822-1 working as designed, and the page now says so in words. Worth the
  owner knowing before he sends the invitation: a manager who logs in during the
  preparation window sees the notice, not a list.
- **The admin's `/team` shows 5 people, not 30.** Deliberate (§2). If the owner
  wants a whole-subtree view for admins, that is a new screen or a new route
  parameter, not a change to the manager-scoped one. **BUG-065.**
- **BUG-056 stays open.** A release id is a timestamp; nothing stamps the commit
  into the release. The new conflict message can say *when* the other build went
  live but not *what* it was. Three lines would fix it, and it is not this
  brief's subject.
- **BUG-058 grows.** Six world-readable `/tmp/probe*.sql` files from 2026-08-21
  still survive on the VPS. Schema-introspection SQL, no personal data, but
  exactly what the BUG-053 rule forbids. Not deleted: not this session's to
  remove.
- Criterion 14's live level curve is still `0.70/1.00/…/7.00` against the
  approved `0.20/0.25/…/6.00`. Untouched, still unresolved.
- No catalogue, coefficient, criteria, grade, department, period or user write of
  any kind was made on live. **The second gate was not pressed and no route that
  could press it was called.**
