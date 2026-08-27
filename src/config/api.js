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
  // Второй шлюз (D-0822-1): активация открывает окно подготовки,
  // старт открывает саму оценку. Необратим.
  PERIODS_START_EVALUATION: `${API_BASE_URL}/api/periods/start-evaluation`,
  PERIODS_RENAME: `${API_BASE_URL}/api/periods/rename`,
  PERIODS_REPARENT: `${API_BASE_URL}/api/periods/reparent`,
  PERIODS_CLOSE: `${API_BASE_URL}/api/periods/close`,
  PERIODS_ANNUAL_ROLLUP: `${API_BASE_URL}/api/periods/annual-rollup`,
  
  // ============================================
  // АДМИН: ПОЛЬЗОВАТЕЛИ
  // ============================================
  ADMIN_USERS_DATA: `${API_BASE_URL}/api/admin-users-data`,
  ADMIN_SAVE_USER: `${API_BASE_URL}/admin/save-user`,  // n8n: admin/save-user (без /api/)
  ADMIN_EXCLUDE_PARTICIPANT: `${API_BASE_URL}/api/admin/exclude-participant`,
  ADMIN_INCLUDE_PARTICIPANT: `${API_BASE_URL}/api/admin/include-participant`,
  ADMIN_EMPLOYEE_EVENTS: `${API_BASE_URL}/api/admin/employee-events`,
  // Увольнение — состояние, а не удаление (D-0825-7). Обе операции обратимы,
  // ни одна строка оценок не удаляется и ничего не пересчитывается.
  ADMIN_TERMINATE_EMPLOYEE: `${API_BASE_URL}/api/admin/terminate-employee`,
  ADMIN_REINSTATE_EMPLOYEE: `${API_BASE_URL}/api/admin/reinstate-employee`,
  ADMIN_EMPLOYMENT_EVENTS: `${API_BASE_URL}/api/admin/employment-events`,
  
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
  // ОТМЕТИТЬ КОЛЛЕГУ (PEER_RECOGNITION, 2026-08-27)
  // ============================================
  // Не оценка, не голосование, не деньги. Отдельная таблица
  // performance_db.peer_recognitions без единой числовой колонки и без внешних
  // ключей в evaluations / evaluation_scores / score_corrections /
  // period_results. Количество отметок не возвращает ни один из трёх маршрутов.
  RECOGNITION_FORM: `${API_BASE_URL}/api/recognition/form`,
  RECOGNITION_SAVE: `${API_BASE_URL}/api/recognition/save`,
  // Читают только admin и c_level — сервер отказывает по роли (403), а не
  // прячет пункт меню.
  RECOGNITION_LIST: `${API_BASE_URL}/api/recognition/list`,

  // ============================================
  // АДМИН: ОЧИСТКА ТЕСТОВЫХ ДАННЫХ
  // ============================================
  ADMIN_CLEAR_TEST_EVALUATIONS: `${API_BASE_URL}/api/admin/clear-test-evaluations`
};

// Экспорт базового URL для возможного использования
export { API_BASE_URL };
