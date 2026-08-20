/**
 * logger.js - Централизованный логгер
 * 
 * Назначение: Управление логированием с возможностью отключения в production
 * Используется в: Все файлы вместо console.log/error/warn
 * 
 * В production (import.meta.env.PROD) логи отключены
 * В development (import.meta.env.DEV) логи работают как обычно
 */

const isDev = import.meta.env.DEV;

const logger = {
  /**
   * Обычный лог (для отладки)
   */
  log: (...args) => {
    if (isDev) {
      console.log(...args);
    }
  },

  /**
   * Предупреждение (для некритичных проблем)
   */
  warn: (...args) => {
    if (isDev) {
      console.warn(...args);
    }
  },

  /**
   * Ошибка (для критичных проблем)
   */
  error: (...args) => {
    if (isDev) {
      console.error(...args);
    }
  },

  /**
   * Информационное сообщение
   */
  info: (...args) => {
    if (isDev) {
      console.info(...args);
    }
  },

  /**
   * Группировка логов
   */
  group: (label) => {
    if (isDev) {
      console.group(label);
    }
  },

  groupEnd: () => {
    if (isDev) {
      console.groupEnd();
    }
  },

  /**
   * Таблица (для объектов/массивов)
   */
  table: (data) => {
    if (isDev) {
      console.table(data);
    }
  }
};

export default logger;





