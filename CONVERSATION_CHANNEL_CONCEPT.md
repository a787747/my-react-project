# Management Listening Channel — «Поговорить с руководством»

Approved concept, 2026-09-06. Supersedes the two earlier drafts in the
2026-09-06 architect session. Incorporates the HRD review of the same date.

This is the business contract for the surface. Code conforms to it, not the
reverse. UI strings below are Russian and normative — they are the product, not
decoration; the wording is what makes the channel usable instead of a complaints
box.

---

## 1. What this is and is not

**Is:** a management *listening* channel. Its primary output is an early
organisational radar — the distribution of concerns across ~86 employed people —
and only secondarily a small number of one-on-one conversations.

**Is not:** complaint management, a survey, a service desk, an anonymous channel,
or part of the evaluation. It is never called «жалобы», «проблемы» or «1-on-1».

**Origin (owner, 2026-08-27):** equipment-fitting projects are in acute phases,
load is high, people hold problems in and discuss them among themselves; a
conversation with C-level would explain reasons and release tension. Some people
also want to draw attention to a manager's or a C-level manager's actions.

---

## 2. Three HR instruments kept separate (HRD, 2026-09-06)

The earlier drafts mixed pulse/signal, a conversation with leadership, and an
escalation channel for sensitive matters. One gate question separates them
without asking the employee to rate the severity of their own problem:

**«Есть ли сейчас тема, которую вам важно обсудить с руководством?»**

1. `У меня всё в порядке, срочных тем для обсуждения нет` → recorded, done.
2. `Есть тема, но отдельная встреча сейчас не нужна` → topic only. Signal, no
   promise of a meeting.
3. `Да, мне нужен разговор` → topic + counterparts + urgency + group readiness.

Rejected: a 1–2–3 «criticality» scale. It forces the employee to dramatise, and
it makes a human channel look like a service desk.

---

## 3. First screen — normative copy

> ## Поговорить с руководством
>
> Сейчас во многих направлениях компании сохраняется высокая рабочая нагрузка:
> продолжаются проекты оснащения клиник, поставки расходных материалов, установка
> оборудования, обучение конечных пользователей и другие текущие задачи.
>
> В периоды высокой интенсивности отдельные вопросы, сложности или разногласия
> могут накапливаться быстрее, чем успевают обсуждаться напрямую.
>
> Причины таких ситуаций могут быть разными. Иногда речь идёт о проблеме, которая
> требует дополнительного внимания. Иногда руководство может не видеть отдельных
> обстоятельств, находясь вне конкретного рабочего процесса. В других случаях
> ситуация зависит от внешних факторов, ограничений или обстоятельств, которые
> не всегда очевидны всем участникам. Бывает и так, что различие в восприятии
> связано просто с недостатком информации или контекста.
>
> Обсуждать рабочие вопросы с коллегами естественно, однако некоторые ситуации
> проще и полезнее прояснить непосредственно с теми, кто располагает необходимой
> информацией, отвечает за соответствующее направление или может посмотреть на
> вопрос с другой стороны.
>
> Если у вас есть тема, которую вы считаете важным обсудить с руководством, вы
> можете обозначить её здесь. При необходимости вы также можете запросить
> отдельный разговор с одним или несколькими C-level руководителями.
>
> Этот раздел не является частью процедуры оценки сотрудников и рассматривается
> отдельно от неё. Его задача — дать возможность своевременно обозначить важный
> для вас вопрос, получить дополнительный контекст или обратить внимание
> руководства на ситуацию, которая, на ваш взгляд, требует обсуждения.
>
> **Ответить можно до 10 сентября.**
>
> **Есть ли сейчас тема, которую вам важно обсудить с руководством?**

**Wording rules that are load-bearing:**

- Never promise «последствий для вас не будет». The company cannot keep it: a
  disclosed violation or conflict may organisationally touch the discloser. The
  promise is non-retaliation for a good-faith conversation, not the absence of
  consequences (HRD).
- Never write that discussing things with colleagues «усиливает тревогу». People
  will always discuss; the problem is assumptions substituting for information.
- No free text anywhere in the form. Owner's decision, 2026-09-06.
- The word «конфиденциально» appears nowhere: the sole reader is the owner and
  the page says so honestly rather than promising anonymity it cannot deliver.

---

## 4. Topic list (HRD wording, normative)

Same list for answers 2 and 3. One topic per response.

1. Хочу понять позицию руководства по ситуации или решению
2. Нагрузка и объём работы
3. Ресурсы или организация работы на проекте
4. Моя роль, ответственность или рабочие приоритеты
5. Карьерный рост и развитие
6. Обучение и развитие компетенций
7. Оплата или признание моего вклада
8. Есть идея или предложение по улучшению работы
9. Отношения в команде, конфликт или токсичная атмосфера
10. Действия моего непосредственного руководителя
11. Считаю ситуацию или решение несправедливым
12. Есть личный вопрос, который хочу обсудить напрямую

Order is deliberate and must not be re-sorted: topic 1 is *not* promoted to the
top, because putting it first nudges people toward the comfortable reading «вы
просто чего-то не знаете» and distorts the radar the owner actually needs.

**Sensitive subset — 9, 10, 11, 12.** For these the group-readiness question
defaults to «только индивидуально».

---

## 5. Answer 3 — the meeting request

- **С кем** — a multiple choice over C-level, plus two special options:
  `Не знаю, с кем лучше обсудить — помогите определить` (expected to be popular;
  it is the default state) and `Со всеми сразу`.
- **Rule:** when topic 10 «Действия моего непосредственного руководителя» is
  chosen, the employee's own manager is never offered as a counterpart. Enforced
  server-side, not by hiding a control.
- **Urgency** — two values only:
  `Хочу обсудить в рамках этого цикла` /
  `Желательно поговорить в ближайшее время — ситуация уже влияет на мою работу`.
- **Group readiness** — «Если выяснится, что такой же вопрос есть у нескольких
  коллег, готовы ли вы обсудить его вместе?» → `Да` / `Только индивидуально`.
  Default `Только индивидуально` for the sensitive subset.
- The general copy makes **no promise** of group meetings. Group format suits
  load, resources, project organisation, priorities, explaining a decision,
  training and general proposals; it does not suit topics 7, 9, 10, 11, 12.

---

## 6. Decisions that shape the build

**D-TALK-1 — waves, not periods.** The record is attached to a *wave*, never to
`period_id`. Wave 1 closes 2026-09-10. «Один ответ на человека» is a property of
a wave, not an HR policy (HRD): after H1 closes the same surface can be reopened
routinely without touching the period model. Consequence: nothing about this
surface can reach the period close path, the way BUG-079 taught.

**D-TALK-2 — the «нет» answer is recorded, and non-response is counted
separately.** Silence is not «всё в порядке». Without the recorded first answer
there is no denominator and no radar. The dashboard shows four numbers: three
answers plus «не ответили».

**D-TALK-3 — sole reader is `admin`.** `c_level`, `hr`, `manager`, `employee`
all get 403 server-side; unauthenticated 401. This differs deliberately from
peer recognition, whose readers are `admin` + `c_level`: here the owner routes
requests to the other C-level managers himself. The residual limit is accepted
and stated openly — a conversation about the owner's own actions has no route
through this page.

**D-TALK-4 — entry inside the campaign flow, not a separate email campaign.**
The window is short *because* the moment is right: people are already in the
system reflecting on their work. The page must meet them there — a banner on the
dashboard and a prompt after an evaluation is submitted, plus the sidebar item.
The banner disappears only when the person answers, including answering «всё в
порядке»; that is what produces the denominator.

**D-TALK-5 — statuses stay minimal for wave 1.** The employee sees «Ответ
получен» (and, for answer 3, that they will be contacted). Scheduling states live
in the admin screen only. A visible state machine is deferred; a two-day build
must not promise machinery that does not exist.

**D-TALK-6 — editable while the wave is open.** Answer can be changed or
withdrawn until the wave closes: Monday's «всё в порядке» may become Wednesday's
request. Same upsert-onto-unique-key shape as peer recognition.

**D-TALK-7 — scope is all employed people (~86)**, independent of evaluation
scope. The period-scope rule (D-0826-4/5) does not apply: a person hired six
weeks ago on an acute project is exactly who needs this. Terminated people are
excluded, per D-0825-7.

**D-TALK-8 — total isolation from the money path.** Separate table, no numeric
column, no foreign key into `evaluations`, `evaluation_scores`,
`score_corrections` or `period_results`, absent from the matrix, the close
dataset, every export, every completion counter and every analytics figure.

**D-TALK-9 — a closing communication after the wave.** A short letter from
leadership: which themes came up most and what leadership says about them, no
names. Without it the channel remains a private service for ten people, while the
purpose is to reach the eighty who talk among themselves. This is a management
action, not code.

**D-TALK-10 — Russian only.** No Turkmen version for wave 1 (owner,
2026-09-06).

**Retention** — no free text exists in this surface, so the BUG-080 risk class
does not apply. Retention of the structured rows is decided at the close of
Annual 2026, together with peer recognition.

---

## 7. Success shape (HRD, expected, not a target)

Of ~86 people: 40–50 answer «всё в порядке», 15–20 flag a topic without a
meeting, 8–15 ask for a conversation. High conversion is not wanted and is not a
measure of success.

---

## 8. Wave 1 timetable

| | |
|---|---|
| Build + deploy | 2026-09-07 … 08 |
| Wave 1 open | from deploy |
| Wave 1 closes | 2026-09-10 |
| Conversations | September, routed personally by the owner |
| Closing letter (D-TALK-9) | after the wave, before the H1 close |
