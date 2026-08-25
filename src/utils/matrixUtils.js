/**
 * matrixUtils - Утилиты для работы с матрицей оценок
 * 
 * Назначение: Группировка критериев для отображения в матрице
 * Используется в: AdminEvaluationsMatrix
 */

/**
 * Группирует критерии по типам
 * @param {Array} criteria - массив критериев
 * @returns {Object} объект с группами: self, general, project, management, c_level
 */
export const groupCriteria = (criteria = []) => {
  return {
    // Критерии для самооценки
    self: criteria.filter(c => c.selfassesment),
    // Общие критерии (не самооценка, не c_level, не проектные, не для менеджеров)
    general: criteria.filter(c => !c.selfassesment && !c.c_level_only && c.target_audience !== 'project_participants' && c.target_audience !== 'managers_only'),
    // Проектные критерии
    project: criteria.filter(c => !c.selfassesment && !c.c_level_only && c.target_audience === 'project_participants'),
    // Критерии для оценки руководителей (managers_only)
    management: criteria.filter(c => !c.selfassesment && !c.c_level_only && c.target_audience === 'managers_only'),
    // Критерии только для C-level
    c_level: criteria.filter(c => c.c_level_only)
  };
};

/**
 * Общий список колонок матрицы: объединение критериев ВСЕХ сотрудников в
 * порядке первого появления, сгруппированное как groupCriteria. Сервер отдаёт
 * каждой строке только применимые ей критерии (D-0822-3), поэтому ни одна
 * отдельная строка — включая employees[0] — не полна как источник заголовка:
 * у general-строки нет проектных критериев (BUG-051).
 * @param {Array} employees - массив сотрудников с criteria
 * @returns {Object} группы критериев: self, general, project, management, c_level
 */
export const buildSharedCriteriaGroups = (employees = []) => {
  const seen = new Map();
  employees.forEach(emp => {
    (emp.criteria || []).forEach(c => {
      if (c && c.criteria_id != null && !seen.has(c.criteria_id)) {
        seen.set(c.criteria_id, c);
      }
    });
  });
  return groupCriteria([...seen.values()]);
};

/**
 * Извлекает уникальные опции для фильтров из списка сотрудников
 * @param {Array} employees - массив сотрудников
 * @returns {Object} объект с уникальными значениями для фильтров
 */
export const extractFilterOptions = (employees = []) => {
  const departments = [...new Set(employees.map(e => e.department_name).filter(Boolean))].sort();
  const grades = [...new Set(employees.map(e => e.grade_code).filter(Boolean))].sort();
  const jobTitles = [...new Set(employees.map(e => e.job_title).filter(Boolean))].sort();
  
  return { departments, grades, jobTitles };
};

/**
 * Фильтрует сотрудников по заданным критериям
 * @param {Array} employees - массив сотрудников
 * @param {Object} filters - объект с фильтрами
 * @returns {Array} отфильтрованный массив
 */
export const filterEmployees = (employees = [], filters = {}) => {
  return employees.filter(emp => {
    if (filters.department && emp.department_name !== filters.department) return false;
    if (filters.grade && emp.grade_code !== filters.grade) return false;
    if (filters.jobTitle && emp.job_title !== filters.jobTitle) return false;
    if (filters.projectParticipant === 'yes' && !emp.is_project_participant) return false;
    if (filters.projectParticipant === 'no' && emp.is_project_participant) return false;
    return true;
  });
};

/**
 * Вычисляет итоговую оценку критерия с учётом всех корректировок
 * 
 * Логика:
 * - Для C-level критериев: возвращаем c_level_score
 * - Для остальных: усреднение (manager_score, mid_level_correction, c_level_correction)
 * 
 * @param {Object} criterion - объект критерия
 * @returns {number|null} итоговая оценка
 */
export const getCriterionFinalScore = (criterion) => {
  const { manager_score, mid_level_correction, c_level_correction, c_level_score, c_level_only } = criterion;
  
  // Для C-level критериев
  if (c_level_only) {
    return c_level_score ?? null;
  }
  
  // Если нет оценки менеджера
  if (manager_score === null || manager_score === undefined) {
    return null;
  }
  
  // Собираем все оценки для усреднения
  const scores = [manager_score];
  
  if (mid_level_correction !== null && mid_level_correction !== undefined) {
    scores.push(mid_level_correction);
  }
  
  if (c_level_correction !== null && c_level_correction !== undefined) {
    scores.push(c_level_correction);
  }
  
  const sum = scores.reduce((acc, s) => acc + s, 0);
  return sum / scores.length;
};

/**
 * Проверяет, есть ли корректировки у критерия
 * @param {Object} criterion - объект критерия
 * @returns {Object} { hasMidLevel, hasCLevel, hasAny }
 */
export const getCriterionCorrections = (criterion) => {
  const hasMidLevel = criterion.mid_level_correction !== null && criterion.mid_level_correction !== undefined;
  const hasCLevel = criterion.c_level_correction !== null && criterion.c_level_correction !== undefined;
  
  return {
    hasMidLevel,
    hasCLevel,
    hasAny: hasMidLevel || hasCLevel
  };
};

/**
 * C-level star / write: subject is in the shown period's scope, can be
 * evaluated, and is not admin or another C-level. Writes are offered only
 * when the shown period is the active campaign period.
 */
export const canReceiveCLevel = (employee, period) => {
  if (!employee) return false;
  const campaignActive = Boolean(
    period &&
    (period.is_active === true || period.is_active === 'true') &&
    period.status === 'active'
  );
  if (!campaignActive) return false;
  if (!employee.is_in_scope) return false;
  if (!employee.can_be_evaluated) return false;
  if (employee.role === 'admin' || employee.role === 'c_level') return false;
  return true;
};

export const cLevelWritePath = (evaluationId) => {
  return evaluationId ? 'update' : 'submit';
};

export const formatCriterionFinalDisplay = (criterion) => {
  const raw = getCriterionFinalScore(criterion);
  if (raw === null || raw === undefined) return null;
  return Number(raw);
};

export const formatCorrectionTooltip = (criterion) => {
  const parts = [];
  if (criterion.manager_score != null) {
    parts.push(`Менеджер: ${criterion.manager_score}`);
  }
  if (criterion.mid_level_correction != null) {
    parts.push(`Mid-level: ${criterion.mid_level_correction}`);
  }
  if (criterion.c_level_correction != null) {
    parts.push(`C-level: ${criterion.c_level_correction}`);
  }
  const finalScore = getCriterionFinalScore(criterion);
  if (finalScore != null && parts.length > 1) {
    parts.push(`Итого: ${Number(finalScore).toFixed(1)}`);
  }
  return parts.join(', ');
};

/**
 * Плоский список колонок матрицы: объединение критериев ВСЕХ строк, в порядке
 * групп (self → general → project → management → c_level), затем по id.
 *
 * D-0825-11 / вторая половина BUG-051. Прежде `useFinalScoresMatrix` брал
 * заголовок из `employees[0]`, а сервер отдаёт каждой строке только применимые
 * ей критерии — поэтому колонки зависели от того, кто оказался первым по
 * алфавиту. Один щелчок в «Сотрудниках» (снять «участник проекта» с первого
 * по алфавиту человека) убирал проектные критерии из шапки у всех, а
 * `weightedSum` продолжал их считать: сумма в строке переставала сходиться
 * с видимыми ячейками.
 */
export const buildSharedCriteriaList = (employees = []) => {
  const groups = buildSharedCriteriaGroups(employees);
  return [
    ...groups.self,
    ...groups.general,
    ...groups.project,
    ...groups.management,
    ...groups.c_level,
  ];
};

/**
 * Берёт ли человек долю премиального фонда этого периода.
 *
 * D-0825-14, правило «нет результата оценки в этом периоде — нет доли фонда».
 * Ни одного идентификатора: список поддерживает себя сам, потому что оба поля
 * редактирует владелец в «Сотрудниках», а охват меняют маршруты периода.
 *
 * Две части, и они не пересекаются:
 *   `is_in_scope = false`      — человек выведен из периода (уволен, принят
 *                                после конца периода, выведен вручную). Долю
 *                                фонда этого периода он не берёт по построению.
 *   `can_be_evaluated = false` — человека не оценивает никто ни по одному
 *                                каналу: все три реляционных фильтра
 *                                `API: Submit Evaluation` несут
 *                                `subj.can_be_evaluated = true`. Это ровно
 *                                шесть человек (D-0825-6).
 *
 * Грейд НЕ входит в правило: человек без грейда — это дефект карточки, а не
 * решение о фонде, и прятать его из расчёта означало бы прятать ошибку.
 */
export const takesBonusShare = (employee) => {
  if (!employee) return false;
  if (employee.is_in_scope === false) return false;
  if (employee.can_be_evaluated === false) return false;
  return true;
};

/** Почему человек не берёт долю — для подписи в интерфейсе. */
export const bonusShareExclusionReason = (employee) => {
  if (!employee) return null;
  if (employee.is_in_scope === false) return 'out_of_scope';
  if (employee.can_be_evaluated === false) return 'not_evaluated_by_anyone';
  return null;
};

/**
 * Разложить бюджет на суммы, которые складываются в него ТОЧНО.
 *
 * Доли пропорциональны индексу распределения премии (формула 3, §4 HANDOVER —
 * взвешенная сумма БЕЗ деления на сумму весов, × коэффициент грейда). Простое
 * округление каждой доли до копеек не даёт бюджет обратно: на 80 строках
 * расхождение доходит до 0.40. Метод наибольших остатков раздаёт недостающие
 * копейки строкам с наибольшей дробной частью, поэтому сумма выведенных на
 * экран сумм равна введённому бюджету до последней цифры.
 *
 * @param {Array<{key: any, index: number}>} rows
 * @param {number} budget
 * @param {number} decimals
 * @returns {Map<any, number>} key -> сумма
 */
export const distributeBudget = (rows = [], budget = 0, decimals = 2) => {
  const result = new Map();
  const list = Array.isArray(rows) ? rows : [];
  const total = list.reduce((sum, row) => sum + (Number(row.index) || 0), 0);
  if (!(budget > 0) || !(total > 0)) {
    list.forEach((row) => result.set(row.key, 0));
    return result;
  }

  const scale = 10 ** decimals;
  const budgetUnits = Math.round(budget * scale);
  const exact = list.map((row) => {
    const share = (Number(row.index) || 0) / total;
    const units = share * budgetUnits;
    return { key: row.key, floor: Math.floor(units), remainder: units - Math.floor(units) };
  });

  let assigned = exact.reduce((sum, row) => sum + row.floor, 0);
  let leftover = budgetUnits - assigned;
  const byRemainder = [...exact].sort((a, b) => b.remainder - a.remainder);
  let cursor = 0;
  while (leftover > 0 && byRemainder.length > 0) {
    byRemainder[cursor % byRemainder.length].floor += 1;
    leftover -= 1;
    cursor += 1;
  }

  exact.forEach((row) => result.set(row.key, row.floor / scale));
  return result;
};

/**
 * Разбор числа, введённого человеком: пробелы, неразрывные пробелы и точки как
 * разделители тысяч, запятая или точка как десятичный разделитель.
 *
 * `parseFloat('3.000.000')` возвращает 3. Ru-locale администратор, набравший
 * бюджет с точками, получал бюджет в три маната и таблицу нулей.
 */
export const parseHumanNumber = (value) => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
  let text = String(value ?? '').trim();
  if (!text) return 0;
  // \u00a0 non-breaking, \u202f narrow no-break — what a spreadsheet paste carries.
  text = text.replace(/[\s\u00a0\u202f']/g, '');
  const commas = (text.match(/,/g) || []).length;
  const dots = (text.match(/\./g) || []).length;
  if (commas > 0 && dots > 0) {
    // The last separator seen is the decimal one; the other groups thousands.
    const lastComma = text.lastIndexOf(',');
    const lastDot = text.lastIndexOf('.');
    if (lastComma > lastDot) text = text.replace(/\./g, '').replace(',', '.');
    else text = text.replace(/,/g, '');
  } else if (commas > 1) {
    text = text.replace(/,/g, '');
  } else if (commas === 1) {
    text = text.replace(',', '.');
  } else if (dots > 1) {
    text = text.replace(/\./g, '');
  }
  const parsed = Number.parseFloat(text);
  return Number.isFinite(parsed) ? parsed : 0;
};
