/**
 * constants.js - Константы приложения
 * 
 * Назначение: Централизованное хранение всех констант
 * Используется в: Все компоненты и хуки приложения
 * 
 * Важно: Значения строк должны точно соответствовать ENUM в PostgreSQL!
 */

// ============================================
// РОЛИ ПОЛЬЗОВАТЕЛЕЙ
// Соответствует: performance_db.user_role_type
// ============================================
export const USER_ROLES = {
  ADMIN: 'admin',
  C_LEVEL: 'c_level',
  HR: 'hr',
  MANAGER: 'manager',
  EMPLOYEE: 'employee'
};

// Роли с админ-доступом
export const ADMIN_ROLES = [USER_ROLES.ADMIN, USER_ROLES.C_LEVEL];

// Роли, которые могут оценивать других
export const EVALUATOR_ROLES = [USER_ROLES.ADMIN, USER_ROLES.C_LEVEL, USER_ROLES.MANAGER];

// ============================================
// КАТЕГОРИИ РАБОТЫ
// Соответствует: performance_db.work_category_type
// ============================================
export const WORK_CATEGORIES = {
  GENERAL: 'general',
  PROJECT: 'project',
  TENDER: 'tender'
  // hybrid существует в БД, но не используется во frontend
};

export const WORK_CATEGORY_LABELS = {
  [WORK_CATEGORIES.GENERAL]: 'общие',
  [WORK_CATEGORIES.PROJECT]: 'проектные'
};

export const getWorkCategoryLabel = (category) => {
  if (!category) return '';
  return WORK_CATEGORY_LABELS[String(category).toLowerCase()] || category;
};

// ============================================
// ЦЕЛЕВЫЕ АУДИТОРИИ КРИТЕРИЕВ
// Используется в: AdminSettings, CriteriaForm
// ============================================
export const TARGET_AUDIENCES = [
  { id: 'all', label: 'Все сотрудники' },
  { id: 'project_participants', label: 'Участники проектов' },
  { id: 'project', label: 'Проектная команда' },
  { id: 'tender', label: 'Тендерный отдел' },
  { id: 'back_office', label: 'Бэк-офис' }
];

export const AUDIENCE_IDS = {
  ALL: 'all',
  PROJECT_PARTICIPANTS: 'project_participants',
  PROJECT: 'project',
  TENDER: 'tender',
  BACK_OFFICE: 'back_office'
};

// ============================================
// СТАТУСЫ ОЦЕНОК
// Соответствует: performance_db.evaluations.status
// ============================================
export const EVALUATION_STATUS = {
  DRAFT: 'draft',
  COMPLETED: 'completed'
};

// ============================================
// UI КОНФИГУРАЦИЯ
// ============================================
export const UI_CONFIG = {
  ITEMS_PER_PAGE: 20,
  DEBOUNCE_DELAY: 300,      // мс - задержка поиска
  TOAST_DURATION: 4000,     // мс - время показа уведомления
  MAX_SCORE: 10             // максимальная оценка
};

// ============================================
// ЗОНЫ ОЦЕНОК (для UI стилизации)
// ============================================
export const SCORE_ZONES = {
  CRITICAL: { min: 1, max: 3, label: 'Критический', color: 'red' },
  BELOW: { min: 4, max: 5, label: 'Ниже ожиданий', color: 'amber' },
  MEETS: { min: 6, max: 7, label: 'Соответствует', color: 'blue' },
  EXCEEDS: { min: 8, max: 10, label: 'Превосходит', color: 'green' }
};




