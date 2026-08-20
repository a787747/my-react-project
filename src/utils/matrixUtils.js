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
