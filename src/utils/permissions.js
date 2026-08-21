/**
 * permissions.js - Утилиты для проверки прав доступа
 * 
 * Назначение: Централизованные проверки ролей пользователей
 * Используется в: App.jsx, Sidebar.jsx, и другие компоненты
 */

import { ADMIN_ROLES, EVALUATOR_ROLES } from '../config/constants';

/**
 * Проверяет доступ к админ-панели (admin, c_level, hr)
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const canAccessAdminPanel = (role) => 
  ['admin', 'c_level', 'hr'].includes(role);

/**
 * Проверяет права на изменение данных админ-панели (только admin).
 * Страницы админ-панели видят admin, c_level и hr, но записывать может
 * только admin — API отвечает 403 остальным.
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const isAdmin = (role) => role === 'admin';

/**
 * Проверяет доступ к аналитике и расширенным данным (admin, c_level)
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const canViewAnalytics = (role) => 
  ADMIN_ROLES.includes(role);

/**
 * Проверяет, является ли роль менеджером или выше
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const isManagerOrAbove = (role) => 
  ['admin', 'c_level', 'hr', 'manager'].includes(role);

/**
 * Проверяет, является ли роль HR
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const isHR = (role) => role === 'hr';

/**
 * Проверяет, является ли роль C-level
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const isCLevel = (role) => role === 'c_level';

/**
 * Проверяет, является ли роль C-level или Admin (не оценивается подчинёнными)
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const isCLevelOrAdmin = (role) => ADMIN_ROLES.includes(role);

/**
 * Проверяет, может ли пользователь оценивать других
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const canEvaluate = (role) => EVALUATOR_ROLES.includes(role);

/**
 * Проверяет, является ли роль обычным сотрудником (не admin/c_level)
 * @param {string} role - роль пользователя
 * @returns {boolean}
 */
export const isRegularEmployee = (role) => 
  !ADMIN_ROLES.includes(role);

