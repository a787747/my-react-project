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
