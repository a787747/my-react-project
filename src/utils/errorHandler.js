/**
 * errorHandler.js - Утилита для обработки ошибок API
 * 
 * Назначение: Преобразование axios ошибок в понятные пользователю сообщения
 * Используется в: apiClient, компоненты с API вызовами
 */

/**
 * Преобразует axios ошибку в понятное сообщение
 * @param {Error} error - axios ошибка
 * @returns {string} Понятное сообщение об ошибке
 */
export const handleApiError = (error) => {
  // Если ошибка уже строка - возвращаем как есть
  if (typeof error === 'string') {
    return error;
  }

  // Ошибка от сервера с response
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    
    // Пытаемся получить сообщение из ответа сервера
    const serverMessage = data?.message || data?.error || data?.detail;
    
    switch (status) {
      case 400:
        return serverMessage || 'Некорректные данные запроса';
      case 401:
        return serverMessage || 'Сессия истекла. Пожалуйста, войдите снова';
      case 403:
        return serverMessage || 'Доступ запрещен. Недостаточно прав';
      case 404:
        return serverMessage || 'Запрашиваемый ресурс не найден';
      case 409:
        return serverMessage || 'Конфликт данных';
      case 422:
        return serverMessage || 'Ошибка валидации данных';
      case 429:
        return serverMessage || 'Слишком много запросов. Попробуйте позже';
      case 500:
        return 'Внутренняя ошибка сервера. Попробуйте позже';
      case 502:
      case 503:
      case 504:
        return 'Сервер временно недоступен. Попробуйте позже';
      default:
        return serverMessage || `Ошибка сервера (код ${status})`;
    }
  }
  
  // Ошибка сети (нет ответа от сервера)
  if (error.request) {
    if (!navigator.onLine) {
      return 'Отсутствует подключение к интернету';
    }
    return 'Нет ответа от сервера. Проверьте подключение к сети';
  }
  
  // Ошибка при настройке запроса
  if (error.message) {
    // Таймаут
    if (error.code === 'ECONNABORTED') {
      return 'Превышено время ожидания ответа от сервера';
    }
    return error.message;
  }
  
  // Неизвестная ошибка
  return 'Произошла непредвиденная ошибка';
};

/**
 * Проверяет, является ли ошибка ошибкой авторизации (401)
 * @param {Error} error - axios ошибка
 * @returns {boolean}
 */
export const isAuthError = (error) => {
  return error?.response?.status === 401;
};

/**
 * Проверяет, является ли ошибка ошибкой доступа (403)
 * @param {Error} error - axios ошибка
 * @returns {boolean}
 */
export const isForbiddenError = (error) => {
  return error?.response?.status === 403;
};

/**
 * Проверяет, является ли ошибка сетевой
 * @param {Error} error - axios ошибка
 * @returns {boolean}
 */
export const isNetworkError = (error) => {
  return !error.response && error.request;
};

export default handleApiError;





