import { formatPeriodDateRu } from './formatPeriodDateRu.js';

export const PERIOD_NOTICE_BODY =
  'С 2026 года оценка проводится дважды в год — за первое и за второе полугодие; годовой результат складывается из двух полугодовых оценок. В декабре 2025 оценка проводилась один раз за весь год — это первая промежуточная.';

export const PERIOD_NOTICE_STATE_LINES = {
  none: 'Период оценки сейчас не открыт.',
  preparation:
    'Период открыт для подготовки. Задачи самооценки и оценки появятся в день старта, названный в письме о запуске.',
  started: 'Оценка идёт — ваши задачи ниже.',
};

const pickFirst = (sources, keys) => {
  for (const source of sources) {
    if (!source || typeof source !== 'object' || Array.isArray(source)) continue;
    for (const key of keys) {
      const value = source[key];
      if (value != null && value !== '') return value;
    }
  }
  return null;
};

/**
 * Pull optional period name/dates from a payload that already carries
 * campaign flags. Today's GET /api/employees has id/status/flags only —
 * name and dates light up if that response later grows them.
 */
export const extractPeriodMeta = (payload) => {
  const root = payload && typeof payload === 'object' && !Array.isArray(payload)
    ? payload
    : {};
  const first = Array.isArray(payload) ? payload[0] : null;
  const nested = root.period && typeof root.period === 'object' ? root.period : null;
  const sources = [root, nested, first];
  return {
    periodName: pickFirst(sources, ['period_name', 'current_period_name']),
    startDate: pickFirst(sources, [
      'start_date',
      'period_start_date',
      'current_period_start',
      'period_start',
    ]),
    endDate: pickFirst(sources, [
      'end_date',
      'period_end_date',
      'current_period_end',
      'period_end',
    ]),
  };
};

export const resolvePeriodNoticeState = ({ campaignActive, periodInPreparation }) => {
  if (campaignActive) return 'started';
  if (periodInPreparation) return 'preparation';
  return 'none';
};

export const buildPeriodNotice = ({
  campaignActive = false,
  periodInPreparation = false,
  periodName = null,
  startDate = null,
  endDate = null,
} = {}) => {
  const state = resolvePeriodNoticeState({ campaignActive, periodInPreparation });
  const start = formatPeriodDateRu(startDate);
  const end = formatPeriodDateRu(endDate);
  const hasPeriodData = Boolean(periodName && start && end);
  const showTitleAndScope = state !== 'none' && hasPeriodData;

  return {
    state,
    showTitle: showTitleAndScope,
    showScope: showTitleAndScope,
    title: showTitleAndScope
      ? `Промежуточная оценка: ${periodName} (${start} — ${end})`
      : null,
    body: PERIOD_NOTICE_BODY,
    scope: showTitleAndScope
      ? `Сейчас оценивается работа за период с ${start} по ${end}. Оценивайте только этот период: то, что произошло после ${end}, относится ко второму полугодию и будет учтено в следующей оценке.`
      : null,
    stateLine: PERIOD_NOTICE_STATE_LINES[state],
  };
};
