/**
 * evaluationUtils - Утилиты для работы с оценками
 * 
 * Назначение: Вспомогательные функции для расчета и отображения оценок
 * Используется в: EvaluationModal, SelfReview, CriterionSlider и другие
 */

/**
 * Рассчитывает рейтинг — простое среднее оценок (формула #1, HANDOVER §4).
 *
 * Это обратная связь сотруднику по шкале 1–10, а НЕ денежное число. Бонусный
 * индекс (формула #3 — Σ(оценка × коэф_уровня × вес) × коэф_грейда, без деления
 * на сумму весов) считается только на серверных и админских экранах:
 * useFinalScoresMatrix, useScoreCalculation и заморозка периода в
 * `API: Manage Periods`. Взвешенную самооценку (формула #2, с делением)
 * считает сервер при отправке — на клиенте её больше нет (D-0822-2).
 *
 * @param {Object} grades - объект с оценками {criteriaTitle: score}
 * @param {number} coefficient - коэффициент грейда
 * @returns {string} итоговый балл с 2 знаками после запятой
 */
export const calculateFinalScore = (grades, coefficient = 1.0) => {
  const scores = Object.values(grades);
  if (scores.length === 0) return 0;
  const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  return (average * coefficient).toFixed(2);
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