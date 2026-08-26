/**
 * Why a person is out of a period's scope, in the words the reader needs.
 *
 * One module so the person's own Welcome page and their manager's team surface
 * can never say two different things about the same row. Every string a person
 * or a manager reads is the owner's, verbatim (D-0825-11 / D-0825-12); the two
 * marked EXECUTOR WORDING are not, and are flagged as such in the report.
 *
 * `exclusion_reason` is the machine value on
 * `performance_db.evaluation_period_participants`. Four exist today:
 *   `excluded_by_admin`      — taken out by hand (D-0825-10). Tonight that is
 *                              the four people hired after 2026-03-31.
 *   `hired_after_period_end` — written at period creation, hire date past the
 *                              period's last day.
 *   `join_date_missing`      — written at period creation, no hire date at all
 *                              (D-0825-12). Forward-looking; no live row today.
 *   `terminated`             — the person left. Unreachable on Welcome (login
 *                              is refused) and deliberately hidden from the
 *                              manager, but handled so a future path cannot
 *                              fall through to a wrong sentence.
 */

import { formatPeriodDateRu } from './formatPeriodDateRu.js';

export const EXCLUSION_REASONS = {
  EXCLUDED_BY_ADMIN: 'excluded_by_admin',
  HIRED_AFTER_PERIOD_END: 'hired_after_period_end',
  INSUFFICIENT_TENURE: 'insufficient_tenure',
  JOIN_DATE_MISSING: 'join_date_missing',
  TERMINATED: 'terminated',
};

/** Owner's words, verbatim — the person hired after 31 March, on Welcome. */
export const WELCOME_LATE_HIRE =
  'В оценке за первое полугодие (1 января — 30 июня 2026) вы не участвуете: вы приступили '
  + 'к работе после 31 марта, и отработанного периода недостаточно для оценки. Это не оценка '
  + 'вашей работы. В оценке за второе полугодие вы участвуете в полном объёме, и её результат '
  + 'войдёт в ваш годовой результат.';

export const WELCOME_EXCLUDED_BY_ADMIN =
  'В оценке за этот период вы не участвуете по решению администратора. Это не оценка вашей '
  + 'работы. За подробностями обратитесь в HR.';

/** The pre-existing notice, accurate for somebody hired after the period ended. */
export const WELCOME_AFTER_PERIOD_END =
  'Ваш первый цикл оценки начнётся со следующего периода. Сейчас от вас не требуется никаких '
  + 'действий.';

/** EXECUTOR WORDING — no owner text exists for a missing hire date. */
export const WELCOME_JOIN_DATE_MISSING =
  'В оценке за этот период вы пока не участвуете: в вашей карточке не заполнена дата приёма '
  + 'на работу, и её нужно подтвердить. Это не оценка вашей работы. Обратитесь в отдел кадров — '
  + 'после подтверждения даты вас вернут в оценку.';

/** EXECUTOR WORDING — defensive; a terminated person cannot log in. */
export const WELCOME_TERMINATED =
  'В оценке за этот период вы не участвуете. Сейчас от вас не требуется никаких действий.';

export const WELCOME_TITLE = 'Вы вне охвата текущего периода оценки';

/**
 * The body of the out-of-scope notice on Welcome.
 * Falls back to the pre-existing sentence when the reason is absent — an old
 * bundle, a payload without the field, or a state nobody has named yet.
 */
export const welcomeExclusionText = (reason, scopeOverride = null) => {
  switch (reason) {
    case EXCLUSION_REASONS.EXCLUDED_BY_ADMIN:
      // The four H1 marks made before scope_override existed are all the
      // owner's late-hire set and keep his exact text. Every new manual switch
      // writes excluded_by_admin into scope_override and therefore gets an
      // honest neutral explanation instead of a false «после 31 марта».
      return scopeOverride === 'excluded_by_admin'
        ? WELCOME_EXCLUDED_BY_ADMIN
        : WELCOME_LATE_HIRE;
    case EXCLUSION_REASONS.INSUFFICIENT_TENURE:
      return WELCOME_LATE_HIRE;
    case EXCLUSION_REASONS.JOIN_DATE_MISSING:
      return WELCOME_JOIN_DATE_MISSING;
    case EXCLUSION_REASONS.TERMINATED:
      return WELCOME_TERMINATED;
    case EXCLUSION_REASONS.HIRED_AFTER_PERIOD_END:
    default:
      return WELCOME_AFTER_PERIOD_END;
  }
};

/**
 * The line on the person's card in their manager's team surface.
 *
 * Owner's words, verbatim, with the hire date substituted:
 * «Не оценивается в этом периоде: принят(а) [дата], меньше трёх месяцев
 *  в периоде. Оценка — со второго полугодия.»
 *
 * With no hire date that sentence cannot be written at all, so the missing-date
 * state gets its own EXECUTOR WORDING line instead of a sentence with a hole.
 */
export const teamExclusionText = (reason, joinDate, scopeOverride = null) => {
  if (reason === EXCLUSION_REASONS.JOIN_DATE_MISSING) {
    return 'Не оценивается в этом периоде: в карточке не заполнена дата приёма — её нужно '
      + 'подтвердить.';
  }
  if (reason === EXCLUSION_REASONS.EXCLUDED_BY_ADMIN
      && scopeOverride === 'excluded_by_admin') {
    return 'Не оценивается в этом периоде по решению администратора.';
  }
  const formatted = formatPeriodDateRu(joinDate);
  if (!formatted) {
    return 'Не оценивается в этом периоде. Оценка — со второго полугодия.';
  }
  return `Не оценивается в этом периоде: принят(а) ${formatted}, меньше трёх месяцев `
    + 'в периоде. Оценка — со второго полугодия.';
};

/** Short badge label for a row, in the admin roster and on the team card. */
export const EXCLUSION_BADGE_LABELS = {
  [EXCLUSION_REASONS.EXCLUDED_BY_ADMIN]: 'Не оценивается в периоде',
  [EXCLUSION_REASONS.HIRED_AFTER_PERIOD_END]: 'Принят после конца периода',
  [EXCLUSION_REASONS.INSUFFICIENT_TENURE]: 'Менее трёх месяцев в периоде',
  [EXCLUSION_REASONS.JOIN_DATE_MISSING]: 'Нет даты приёма',
  [EXCLUSION_REASONS.TERMINATED]: 'Уволен',
};
