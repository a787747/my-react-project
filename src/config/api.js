/**
 * api.js - Конфигурация API эндпоинтов
 * 
 * Назначение: Централизованное хранение всех URL адресов API
 * Используется в: Все хуки и компоненты, работающие с API
 * 
 * Примечание: Пути должны точно соответствовать n8n workflows!
 */

// Базовый URL API (можно переопределить через .env)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/webhook';

export const API_ENDPOINTS = {
  // ============================================
  // АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
  // ============================================
  LOGIN: `${API_BASE_URL}/auth/login`,
  REGISTER: `${API_BASE_URL}/api/register`,
  VERIFY_INVITE: `${API_BASE_URL}/api/verify-invite`,
  CREATE_INVITE: `${API_BASE_URL}/api/admin/create-invite`,
  SEND_VERIFICATION_CODE: `${API_BASE_URL}/api/send-verification-code`,
  VERIFY_CODE: `${API_BASE_URL}/api/verify-code`,
  REQUEST_PASSWORD_RESET: `${API_BASE_URL}/api/request-password-reset`,
  RESET_PASSWORD: `${API_BASE_URL}/api/reset-password`,
  
  // ============================================
  // СОТРУДНИКИ
  // ============================================
  EMPLOYEES: `${API_BASE_URL}/api/employees`,
  
  // ============================================
  // ОЦЕНКИ
  // ============================================
  SUBMIT_EVALUATION: `${API_BASE_URL}/api/submit-evaluation`,
  UPDATE_EVALUATION: `${API_BASE_URL}/api/update-evaluation`,
  EVALUATION_DETAILS: `${API_BASE_URL}/api/evaluation-details`,
  EVALUATION_HISTORY: `${API_BASE_URL}/api/evaluation-history`,
  CHECK_EVALUATED: `${API_BASE_URL}/api/check-evaluated`,
  
  // ============================================
  // КРИТЕРИИ
  // ============================================
  CRITERIA: `${API_BASE_URL}/api/criteria`,
  MANAGE_CRITERIA: `${API_BASE_URL}/manage-criteria`,  // n8n: manage-criteria (без /api/)
  
  // ============================================
  // ПРОФИЛЬ И САМООЦЕНКА
  // ============================================
  MY_PROFILE: `${API_BASE_URL}/api/my-profile`,
  GET_MY_MANAGER: `${API_BASE_URL}/api/get-my-manager`,
  SELF_REVIEW_SUBMIT: `${API_BASE_URL}/api/self-review-submit`,
  CHECK_SELF_REVIEWS: `${API_BASE_URL}/api/check-self-review`,
  EMPLOYEE_SELF_REVIEW: `${API_BASE_URL}/api/employee-self-review`,
  
  // ============================================
  // ПЕРИОДЫ
  // ============================================
  PERIODS: `${API_BASE_URL}/api/periods`,
  PERIODS_CREATE: `${API_BASE_URL}/api/periods/create`,
  PERIODS_ACTIVATE: `${API_BASE_URL}/api/periods/activate`,
  
  // ============================================
  // АДМИН: ПОЛЬЗОВАТЕЛИ
  // ============================================
  ADMIN_USERS_DATA: `${API_BASE_URL}/api/admin-users-data`,
  ADMIN_SAVE_USER: `${API_BASE_URL}/admin/save-user`,  // n8n: admin/save-user (без /api/)
  
  // ============================================
  // АДМИН: ОЦЕНКИ
  // ============================================
  ADMIN_ALL_EVALUATIONS: `${API_BASE_URL}/api/admin/all-evaluations`,
  ADMIN_EVALUATION_DETAILS_BY_USER: `${API_BASE_URL}/api/admin/evaluation-details-by-user`,
  ADMIN_EVALUATIONS_MATRIX: `${API_BASE_URL}/api/admin/evaluations-matrix`,
  ADMIN_SCORE_CORRECTION: `${API_BASE_URL}/api/admin/score-correction`,
  
  // ============================================
  // МЕНЕДЖЕРЫ: МАТРИЦА ПОДЧИНЁННЫХ
  // ============================================
  MANAGER_SUBORDINATES_MATRIX: `${API_BASE_URL}/api/manager-subordinates-matrix`,
  
  // ============================================
  // АНАЛИТИКА
  // ============================================
  ANALYTICS: `${API_BASE_URL}/api/analytics`,
  
  // ============================================
  // HR: СТАТУСЫ ОЦЕНОК
  // ============================================
  HR_EVALUATION_STATUS: `${API_BASE_URL}/api/hr/evaluation-status`,
  
  // ============================================
  // АДМИН: КОЭФФИЦИЕНТЫ ОЦЕНОК
  // ============================================
  SCORE_COEFFICIENTS: `${API_BASE_URL}/api/score-coefficients`,
  UPDATE_ADMIN_DATA: `${API_BASE_URL}/update-admin-data`,
  
  // ============================================
  // АДМИН: ОЧИСТКА ТЕСТОВЫХ ДАННЫХ
  // ============================================
  ADMIN_CLEAR_TEST_EVALUATIONS: `${API_BASE_URL}/api/admin/clear-test-evaluations`
};

// Экспорт базового URL для возможного использования
export { API_BASE_URL };
