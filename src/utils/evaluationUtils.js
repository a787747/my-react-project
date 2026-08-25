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

export const SCORE_SCALE = {
  DEFAULT: 'default',
  VOLUME: 'volume',
  BEYOND_ROLE: 'beyond_role',
};

const EMPTY_ZONE = {
  bg: 'bg-gray-50',
  border: 'border-gray-200',
  text: 'text-gray-700',
  label: 'Не оценено',
};

/** Default quality scale: 6 is the first «хорошо»; 5 is attention, not good. */
const DEFAULT_SCORE_BANDS = [
  { max: 2, bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'Зона риска' },
  { max: 4, bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', label: 'Ниже ожиданий' },
  { max: 5, bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', label: 'В целом справляется, требует внимания' },
  { max: 7, bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', label: 'Хорошо' },
  { max: 8, bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', label: 'Выше нормы' },
  { max: Infinity, bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', label: 'Зона исключительности' },
];

/** Criterion 13 — volume, not quality. Low is small load, not bad work. Norm still 6. */
const VOLUME_SCORE_BANDS = [
  { max: 3, bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700', label: 'Малый объём' },
  { max: 5, bg: 'bg-sky-50', border: 'border-sky-200', text: 'text-sky-800', label: 'Умеренный объём' },
  { max: 7, bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', label: 'Норма объёма' },
  { max: Infinity, bg: 'bg-indigo-50', border: 'border-indigo-200', text: 'text-indigo-800', label: 'Высокий объём' },
];

/** Criterion 14 — norm is 2; above 2 is a beyond-role fact, not a quality grade. */
const BEYOND_ROLE_SCORE_BANDS = [
  { max: 1, bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'Ниже нормы' },
  { max: 2, bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', label: 'Норма' },
  { max: 6, bg: 'bg-teal-50', border: 'border-teal-200', text: 'text-teal-800', label: 'Сверх роли' },
  { max: Infinity, bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', label: 'Крупный вклад сверх роли' },
];

const pickBand = (val, bands) => bands.find((band) => val <= band.max) || bands[bands.length - 1];

/**
 * Resolves the colour/label scale for a criterion.
 * Accepts a criterion object (`id` or `criteria_id`) or a numeric id.
 */
export const getScoreScale = (criterion) => {
  const raw = criterion && typeof criterion === 'object'
    ? criterion.id ?? criterion.criteria_id
    : criterion;
  const id = Number(raw);
  if (id === 14) return SCORE_SCALE.BEYOND_ROLE;
  if (id === 13) return SCORE_SCALE.VOLUME;
  return SCORE_SCALE.DEFAULT;
};

/**
 * Определяет зону оценки (цвета и текст).
 * Labels and colours only — does not change the numeric score.
 * @param {number} score - оценка
 * @param {number|Object} [criterion] - criterion id or object; 13 = volume, 14 = beyond-role
 * @returns {Object} {bg, border, text, label}
 */
export const getScoreZone = (score, criterion) => {
  const val = parseInt(score, 10);
  if (isNaN(val)) return EMPTY_ZONE;

  const scale = getScoreScale(criterion);
  if (scale === SCORE_SCALE.BEYOND_ROLE) return pickBand(val, BEYOND_ROLE_SCORE_BANDS);
  if (scale === SCORE_SCALE.VOLUME) return pickBand(val, VOLUME_SCORE_BANDS);
  return pickBand(val, DEFAULT_SCORE_BANDS);
};

/**
 * Chip classes for matrix/list cells. Correction highlight stays amber
 * (that colour means «есть корректировка», not a score band).
 */
export const getScoreBandChipClasses = (score, criterion, options = {}) => {
  if (options.hasCorrection) return 'bg-amber-100 text-amber-700';
  if (score === null || score === undefined || score === '') {
    return options.emptyClass || 'bg-gray-100 text-gray-400';
  }
  const zone = getScoreZone(score, criterion);
  return `${zone.bg} ${zone.text}`;
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