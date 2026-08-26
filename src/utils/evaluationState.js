/**
 * The evaluation state of one person in the CURRENT period, for Admin → Сотрудники.
 *
 * Why this is not cosmetic (D-0825-11): the owner marks classification on that
 * screen, and classification is a money decision — criteria count drives bonus
 * share. A person whose exclusion he cannot see is money he cannot see moving.
 * Until 2026-08-25 the only visible period signal on that page was the red
 * «Уволен» pill, which is a `users` column; a person out of H1 scope for any
 * other reason looked completely normal.
 *
 * The inputs come from `API: Admin Get Users Data`, which since 2026-08-25
 * LEFT JOINs the participants row of the single active period:
 *   `period_id`               — null when no period is active at all
 *   `has_period_row`          — false when the person has no participants row
 *   `period_is_in_scope`      — the flag
 *   `period_exclusion_reason` — the machine reason, or null
 *   `join_date`, `terminated_at`
 *
 * Precedence is deliberate and is the order below: termination outranks
 * everything (the person has left), an explicit exclusion reason outranks a
 * derived one, and «в оценке» is only ever the last resort.
 */

import { EXCLUSION_REASONS } from './scopeExclusion.js';

export const EVALUATION_STATES = {
  TERMINATED: 'terminated',
  HIRED_AFTER_PERIOD_END: 'hired_after_period_end',
  EXCLUDED_BY_ADMIN: 'excluded_by_admin',
  JOIN_DATE_MISSING: 'join_date_missing',
  NO_PERIOD_ROW: 'no_period_row',
  NO_PERIOD: 'no_period',
  IN_EVALUATION: 'in_evaluation',
};

/**
 * Order matters twice: it is the precedence used by `evaluationStateOf`, and it
 * is the order the filter offers the options in.
 */
export const EVALUATION_STATE_ORDER = [
  EVALUATION_STATES.IN_EVALUATION,
  EVALUATION_STATES.EXCLUDED_BY_ADMIN,
  EVALUATION_STATES.HIRED_AFTER_PERIOD_END,
  EVALUATION_STATES.JOIN_DATE_MISSING,
  EVALUATION_STATES.TERMINATED,
  EVALUATION_STATES.NO_PERIOD_ROW,
  EVALUATION_STATES.NO_PERIOD,
];

export const EVALUATION_STATE_LABELS = {
  [EVALUATION_STATES.IN_EVALUATION]: 'В оценке',
  [EVALUATION_STATES.EXCLUDED_BY_ADMIN]: 'Выведен из периода',
  [EVALUATION_STATES.HIRED_AFTER_PERIOD_END]: 'Менее трёх месяцев в периоде',
  [EVALUATION_STATES.JOIN_DATE_MISSING]: 'Нет даты приёма',
  [EVALUATION_STATES.TERMINATED]: 'Уволен',
  [EVALUATION_STATES.NO_PERIOD_ROW]: 'Нет строки участия',
  [EVALUATION_STATES.NO_PERIOD]: 'Нет активного периода',
};

/** One line saying what the state means for money and for the person's tasks. */
export const EVALUATION_STATE_HINTS = {
  [EVALUATION_STATES.IN_EVALUATION]:
    'В охвате текущего периода: получает задачи и долю премиального фонда.',
  [EVALUATION_STATES.EXCLUDED_BY_ADMIN]:
    'Выведен из охвата этого периода вручную. Работает, входит в портал, участвует '
    + 'в следующем периоде. Задач и доли фонда в этом периоде нет. Обратимо.',
  [EVALUATION_STATES.HIRED_AFTER_PERIOD_END]:
    'Принят позже границы минимального трёхмесячного стажа — вне охвата автоматически. '
    + 'Задач и доли фонда в этом периоде нет.',
  [EVALUATION_STATES.JOIN_DATE_MISSING]:
    'В карточке не заполнена дата приёма — её нужно подтвердить. Пока дата пуста, '
    + 'человек не входит в охват нового периода.',
  [EVALUATION_STATES.TERMINATED]:
    'Уволен: вне списков, задач и расчёта премии. Оценки в базе сохранены.',
  [EVALUATION_STATES.NO_PERIOD_ROW]:
    'У человека нет строки участия в текущем периоде — он появился в системе после '
    + 'создания периода. В замороженные итоги периода он не попадёт.',
  [EVALUATION_STATES.NO_PERIOD]:
    'Активного периода сейчас нет, поэтому охват не определён ни для кого.',
};

/** Tailwind classes per state — «В оценке» is the only quiet one. */
export const EVALUATION_STATE_CLASSES = {
  [EVALUATION_STATES.IN_EVALUATION]: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  [EVALUATION_STATES.EXCLUDED_BY_ADMIN]: 'bg-amber-50 text-amber-800 border-amber-200',
  [EVALUATION_STATES.HIRED_AFTER_PERIOD_END]: 'bg-sky-50 text-sky-700 border-sky-200',
  [EVALUATION_STATES.JOIN_DATE_MISSING]: 'bg-orange-50 text-orange-800 border-orange-300',
  [EVALUATION_STATES.TERMINATED]: 'bg-red-50 text-red-700 border-red-200',
  [EVALUATION_STATES.NO_PERIOD_ROW]: 'bg-violet-50 text-violet-700 border-violet-200',
  [EVALUATION_STATES.NO_PERIOD]: 'bg-slate-50 text-slate-600 border-slate-200',
};

/**
 * A reason value the server may write that this module does not model yet
 * degrades to «Выведен из периода» rather than to «В оценке»: an unknown
 * exclusion must never read as participation.
 */
const REASON_TO_STATE = {
  [EXCLUSION_REASONS.TERMINATED]: EVALUATION_STATES.TERMINATED,
  [EXCLUSION_REASONS.HIRED_AFTER_PERIOD_END]: EVALUATION_STATES.HIRED_AFTER_PERIOD_END,
  [EXCLUSION_REASONS.INSUFFICIENT_TENURE]: EVALUATION_STATES.HIRED_AFTER_PERIOD_END,
  [EXCLUSION_REASONS.EXCLUDED_BY_ADMIN]: EVALUATION_STATES.EXCLUDED_BY_ADMIN,
  [EXCLUSION_REASONS.JOIN_DATE_MISSING]: EVALUATION_STATES.JOIN_DATE_MISSING,
};

export function evaluationStateOf(user) {
  if (!user || typeof user !== 'object') return EVALUATION_STATES.NO_PERIOD;

  // Termination first: it is a property of the person, not of the period, and
  // it is true even when no period is active.
  if (user.terminated_at) return EVALUATION_STATES.TERMINATED;

  // No active period ⇒ nobody has a scope. Said plainly rather than implied.
  if (user.period_id === null || user.period_id === undefined) {
    return EVALUATION_STATES.NO_PERIOD;
  }

  if (user.has_period_row === false) return EVALUATION_STATES.NO_PERIOD_ROW;

  if (user.period_is_in_scope === false) {
    return REASON_TO_STATE[user.period_exclusion_reason]
      ?? EVALUATION_STATES.EXCLUDED_BY_ADMIN;
  }

  // In scope, but with no hire date on file. BUG-066: the rule that built the
  // participants row let a NULL fall through to "in scope" silently. D-0825-12
  // fixes that for periods created from now on and deliberately does not
  // rewrite existing rows, so this state is reachable on a running period and
  // has to be visible rather than inferred.
  if (!user.join_date) return EVALUATION_STATES.JOIN_DATE_MISSING;

  return EVALUATION_STATES.IN_EVALUATION;
}

export const evaluationStateLabel = (state) =>
  EVALUATION_STATE_LABELS[state] ?? EVALUATION_STATE_LABELS[EVALUATION_STATES.NO_PERIOD];
