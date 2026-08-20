/**
 * evaluationUtils - Утилиты для работы с оценками
 * 
 * Назначение: Вспомогательные функции для расчета и отображения оценок
 * Используется в: EvaluationModal, SelfReview, CriterionSlider и другие
 */

/**
 * Рассчитывает итоговый балл с учетом коэффициента грейда (простая версия)
 * @param {Object} grades - объект с оценками {criteriaTitle: score}
 * @param {number} coefficient - коэффициент грейда
 * @returns {string} итоговый балл с 2 знаками после запятой
 * @deprecated Используйте calculateWeightedScore для более точного расчета
 */
export const calculateFinalScore = (grades, coefficient = 1.0) => {
  const scores = Object.values(grades);
  if (scores.length === 0) return 0;
  const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  return (average * coefficient).toFixed(2);
};

/**
 * Рассчитывает итоговый балл с учетом весов критериев и коэффициентов оценок
 * 
 * Формула: (Σ(оценка × коэффициент_оценки × вес_критерия) / Σ(весов)) × коэффициент_грейда
 * 
 * @param {Object} evaluationScores - объект с оценками {criteriaId: scoreValue} или {criteriaTitle: scoreValue}
 * @param {Array} criteriaWithCoefficients - массив критериев с весами и коэффициентами
 *   [{id, title, weight, score_coefficients: {0: coef, 1: coef, ...10: coef}}, ...]
 * @param {number} gradeCoefficient - коэффициент грейда сотрудника
 * @returns {string} итоговый балл с 2 знаками после запятой
 */
export const calculateWeightedScore = (evaluationScores, criteriaWithCoefficients = [], gradeCoefficient = 1.0) => {
  // Если нет критериев с коэффициентами, используем простой расчет
  if (!criteriaWithCoefficients || criteriaWithCoefficients.length === 0) {
    return calculateFinalScore(evaluationScores, gradeCoefficient);
  }

  let weightedSum = 0;
  let totalWeight = 0;

  // Преобразуем оценки в массив для обработки
  const scoresEntries = Object.entries(evaluationScores);
  
  for (const [key, scoreValue] of scoresEntries) {
    // Находим критерий по id или title
    const criterion = criteriaWithCoefficients.find(c => 
      c.id === parseInt(key) || c.id === key || c.title === key
    );
    
    if (!criterion) {
      // Если критерий не найден, используем дефолтные значения
      const weight = 1.0;
      const scoreCoef = 1.0;
      weightedSum += scoreValue * scoreCoef * weight;
      totalWeight += weight;
      continue;
    }

    // Получаем вес критерия
    const weight = parseFloat(criterion.weight) || 1.0;
    
    // Получаем коэффициент для данного уровня оценки
    const scoreLevel = Math.round(parseFloat(scoreValue) || 0);
    const clampedLevel = Math.max(0, Math.min(10, scoreLevel)); // Ограничиваем 0-10
    const scoreCoef = criterion.score_coefficients?.[clampedLevel] ?? 1.0;
    
    // Добавляем взвешенное значение
    weightedSum += scoreValue * scoreCoef * weight;
    totalWeight += weight;
  }

  if (totalWeight === 0) return '0.00';

  // Рассчитываем итоговый балл
  const weightedAverage = weightedSum / totalWeight;
  const finalScore = weightedAverage * gradeCoefficient;

  return finalScore.toFixed(2);
};

/**
 * Преобразует оценки из формата {title: score} в формат {criteriaId: score}
 * @param {Object} gradesByTitle - оценки по названию критерия
 * @param {Array} criteria - массив критериев
 * @returns {Object} оценки по ID критерия
 */
export const convertGradesToIds = (gradesByTitle, criteria) => {
  if (!gradesByTitle || !criteria) return {};
  
  const result = {};
  for (const [title, score] of Object.entries(gradesByTitle)) {
    const criterion = criteria.find(c => c.title === title);
    if (criterion) {
      result[criterion.id] = score;
    }
  }
  return result;
};

/**
 * Фильтрует критерии по сотруднику и роли оценщика
 * @param {Array} criteria - массив критериев
 * @param {Object} employee - сотрудник
 * @param {string} userRole - роль оценщика
 * @returns {Array} отфильтрованные критерии
 */
export const filterCriteriaByEmployee = (criteria, employee, userRole = null) => {
  if (!criteria || !employee) return [];
  
  return criteria.filter(c => {
    // Проверка активности
    const isActive = c.is_active === true || c.is_active === 'true';
    if (!isActive) return false;
    
    // Проверка аудитории
    const audience = c.target_audience ? c.target_audience.toLowerCase() : 'all';
    
    // Если критерий только для участников проектов
    if (audience === 'project_participants') {
      if (!employee.is_project_participant) return false;
    }
    
    // Проверка по роли оценщика (c_level_only)
    const isCLevelOnly = c.c_level_only === true || c.c_level_only === 'true';
    
    if (userRole === 'c_level') {
      // C-level видит ВСЁ
      return true;
    } else {
      // Обычный менеджер не видит c_level_only критерии
      return !isCLevelOnly;
    }
  });
};

/**
 * Определяет зону оценки (цвета и текст)
 * @param {number} score - оценка от 0 до 10
 * @returns {Object} объект со стилями {bg, border, text, label}
 */
export const getScoreZone = (score) => {
  const val = parseInt(score, 10);
  if (isNaN(val)) return { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700', label: 'Не оценено' };
  if (val <= 3) return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'Зона риска' };
  if (val <= 6) return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', label: 'Зона нормы' };
  if (val <= 8) return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', label: 'Зона роста' };
  return { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', label: 'Зона исключительности' };
};

/**
 * Получает описание уровня оценки из критерия
 * @param {Object} criterion - критерий с полями level_X_desc
 * @param {number} level - уровень (0-10)
 * @returns {string} описание уровня
 */
export const getLevelDescription = (criterion, level) => {
  if (!criterion) return '';
  const val = parseInt(level, 10);
  const fieldName = `level_${val}_desc`;
  return criterion[fieldName] || `Оценка ${val} из 10`;
};