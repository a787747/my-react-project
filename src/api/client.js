/**
 * client.js - Централизованный HTTP клиент
 * 
 * Назначение: Настроенный axios instance с interceptors для авторизации и обработки ошибок
 * Используется в: Все хуки и компоненты, работающие с API
 * 
 * Функционал:
 * - Автоматическое добавление токена авторизации в заголовки
 * - Централизованная обработка ошибок
 * - Автоматический logout при 401
 */

import axios from 'axios';
import { handleApiError, isAuthError } from '../utils/errorHandler';

// Создаем настроенный axios instance
const apiClient = axios.create({
  timeout: 30000, // 30 секунд
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * Добавляет токен авторизации в заголовки каждого запроса
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * Обрабатывает ошибки и выполняет автоматический logout при 401
 */
apiClient.interceptors.response.use(
  // Успешный ответ - возвращаем как есть
  (response) => response,
  
  // Обработка ошибок
  (error) => {
    // При ошибке авторизации (401) - разлогиниваем пользователя
    if (isAuthError(error)) {
      // Очищаем localStorage
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      
      // Редирект на страницу входа (если мы не на ней уже)
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // Возвращаем ошибку с понятным сообщением
    const errorMessage = handleApiError(error);
    
    // Создаем новый объект ошибки с сохранением оригинальных данных
    const enhancedError = new Error(errorMessage);
    enhancedError.originalError = error;
    enhancedError.response = error.response;
    enhancedError.request = error.request;
    enhancedError.config = error.config;
    enhancedError.userMessage = errorMessage;
    
    return Promise.reject(enhancedError);
  }
);

export default apiClient;
