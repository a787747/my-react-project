/**
 * annualRollup - Семантика ячеек годовой сводки (D-0819-1, D-0821-3)
 *
 * Назначение: Чистые функции для отображения годовой сводки по контейнеру.
 * Используется в: AdminAnnualRollup
 *
 * Правила:
 * - Годовой рейтинг и индекс приходят С СЕРВЕРА, посчитанные только по
 *   сохранённым результатам закрытых периодов (period_results). Клиент их
 *   не пересчитывает — только отображает.
 * - «Вне охвата» исключается из среднего (без подстановки нуля).
 * - «Нет данных» — человек был в охвате, но не был оценён; виден, но
 *   исключён из среднего.
 * - Незакрытый дочерний период не даёт ничего.
 */

export const CELL_STATES = {
  NOT_CLOSED: 'not_closed',
  CLOSED_NO_RESULTS: 'closed_no_results',
  OUT_OF_SCOPE: 'out_of_scope',
  NO_DATA: 'no_data',
  OK: 'ok',
};

export const CELL_LABELS = {
  [CELL_STATES.NOT_CLOSED]: 'период не закрыт',
  [CELL_STATES.CLOSED_NO_RESULTS]: 'нет сохранённых результатов',
  [CELL_STATES.OUT_OF_SCOPE]: 'вне охвата',
  [CELL_STATES.NO_DATA]: 'нет данных',
};

/**
 * Состояние одной ячейки (человек × дочерний период).
 * @param {Object} child - дочерний период из ответа annual-rollup
 * @param {Object|null} result - persisted-результат человека по этому периоду
 *   ({in_scope, has_data, final_rating, bonus_index}) или undefined/null
 * @returns {{state: string, final_rating: number|null, bonus_index: number|null}}
 */
export const cellState = (child, result) => {
  if (!child || child.status !== 'closed') {
    return { state: CELL_STATES.NOT_CLOSED, final_rating: null, bonus_index: null };
  }
  if (!child.has_results) {
    return { state: CELL_STATES.CLOSED_NO_RESULTS, final_rating: null, bonus_index: null };
  }
  if (!result || result.in_scope !== true) {
    return { state: CELL_STATES.OUT_OF_SCOPE, final_rating: null, bonus_index: null };
  }
  if (result.final_rating === null || result.final_rating === undefined) {
    return { state: CELL_STATES.NO_DATA, final_rating: null, bonus_index: null };
  }
  return {
    state: CELL_STATES.OK,
    final_rating: Number(result.final_rating),
    bonus_index: result.bonus_index !== null && result.bonus_index !== undefined
      ? Number(result.bonus_index)
      : null,
  };
};

/** Подпись ячейки без числа (или null, если ячейка числовая). */
export const cellLabel = (state) => CELL_LABELS[state] ?? null;

/** Рейтинг: 2 знака, «—» когда нет значения. */
export const formatRating = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(2);
};

/** Индекс: 2 знака, «—» когда нет значения (нет данных ≠ ноль). */
export const formatIndex = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

/**
 * Сколько дочерних периодов закрыто и сколько из них реально дало числа.
 * Годовые значения складываются только из закрытых периодов с сохранёнными
 * результатами; без этого счётчика годовая строка молча выглядит полной,
 * даже когда за ней стоит одно полугодие из двух.
 * @param {Array} children - дочерние периоды из ответа annual-rollup
 * @returns {{total: number, closed: number, contributing: number}}
 */
export const coverageSummary = (children = []) => {
  const list = Array.isArray(children) ? children : [];
  return {
    total: list.length,
    closed: list.filter((c) => c && c.status === 'closed').length,
    contributing: list.filter((c) => c && c.status === 'closed' && c.has_results).length,
  };
};

/** «закрыто 1 из 2 дочерних периодов» — подпись охвата для шапки сводки. */
export const coverageLabel = (children = []) => {
  const { total, closed } = coverageSummary(children);
  const noun = total === 1 ? 'дочернего периода' : 'дочерних периодов';
  return `закрыто ${closed} из ${total} ${noun}`;
};

/** Диапазон дат периода: «01.01.2026 — 30.06.2026»; «—» без дат. */
export const formatDateRange = (period) => {
  const asDate = (value) => {
    if (!value) return null;
    const parts = String(value).slice(0, 10).split('-');
    return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : null;
  };
  const start = asDate(period?.start_date);
  const end = asDate(period?.end_date);
  if (!start || !end) return '—';
  return `${start} — ${end}`;
};
