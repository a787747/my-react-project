/**
 * ToastContext - Глобальный контекст для уведомлений
 * 
 * Назначение: Централизованное управление toast-уведомлениями
 * Используется в: Любой компонент через хук useToast()
 * 
 * Функционал:
 * - Стекирование нескольких уведомлений
 * - Progress bar для auto-dismiss
 * - Разные позиции (top-right, top-left, bottom-right, bottom-left, top-center, bottom-center)
 * - Анимации входа/выхода
 * - Типы: success, error, warning, info
 * 
 * Экспортирует:
 * - ToastProvider - провайдер контекста
 * - useToast - хук для показа уведомлений
 */

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { UI_CONFIG } from '../config/constants';

const ToastContext = createContext(null);

// Позиции для контейнера
const POSITIONS = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
};

// Конфигурация стилей по типу
const TYPE_CONFIG = {
  success: {
    bg: 'bg-success-600',
    progressBg: 'bg-success-400',
    icon: CheckCircle,
    iconClass: 'text-white',
  },
  error: {
    bg: 'bg-danger-600',
    progressBg: 'bg-danger-400',
    icon: AlertCircle,
    iconClass: 'text-white',
  },
  warning: {
    bg: 'bg-warning-500',
    progressBg: 'bg-warning-300',
    icon: AlertTriangle,
    iconClass: 'text-white',
  },
  info: {
    bg: 'bg-info-600',
    progressBg: 'bg-info-400',
    icon: Info,
    iconClass: 'text-white',
  },
};

/**
 * Компонент отдельного toast-уведомления с progress bar
 */
const ToastItem = ({ id, message, type, duration, onClose, isExiting }) => {
  const [progress, setProgress] = useState(100);
  const intervalRef = useRef(null);
  const config = TYPE_CONFIG[type] || TYPE_CONFIG.info;
  const Icon = config.icon;

  // Progress bar анимация
  useEffect(() => {
    if (duration <= 0) return;

    const startTime = Date.now();
    const updateInterval = 50; // Обновляем каждые 50ms
    
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);
      
      if (remaining <= 0) {
        clearInterval(intervalRef.current);
      }
    }, updateInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [duration]);

  // Пауза progress bar при hover
  const handleMouseEnter = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  const handleMouseLeave = () => {
    // Перезапускаем таймер с оставшимся временем
    if (duration <= 0) return;
    
    const remainingTime = (progress / 100) * duration;
    const startTime = Date.now();
    const startProgress = progress;
    
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, startProgress - (elapsed / remainingTime) * startProgress);
      setProgress(remaining);
      
      if (remaining <= 0) {
        clearInterval(intervalRef.current);
        onClose(id);
      }
    }, 50);
  };

  return (
    <div 
      className={`
        relative overflow-hidden
        ${config.bg} text-white 
        rounded-xl shadow-xl 
        min-w-[320px] max-w-md
        transform transition-all duration-300 ease-out
        ${isExiting ? 'animate-slide-out-right opacity-0' : 'animate-slide-in-right'}
      `}
      role="alert"
      aria-live="polite"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Content */}
      <div className="flex items-start gap-3 p-4">
        <div className="flex-shrink-0 mt-0.5">
          <Icon className={`w-5 h-5 ${config.iconClass}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium leading-relaxed">{message}</p>
        </div>
        <button 
          onClick={() => onClose(id)} 
          className="flex-shrink-0 p-1 rounded-lg hover:bg-white/20 transition-colors"
          aria-label="Закрыть уведомление"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      
      {/* Progress bar */}
      {duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/20">
          <div 
            className={`h-full ${config.progressBg} transition-all duration-50 ease-linear`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
};

/**
 * Контейнер для toast-уведомлений
 */
const ToastContainer = ({ toasts, position, onClose }) => {
  const positionClass = POSITIONS[position] || POSITIONS['top-right'];
  const isBottom = position.startsWith('bottom');
  
  return (
    <div 
      className={`fixed ${positionClass} z-toast flex flex-col gap-3 pointer-events-none`}
      style={{ maxHeight: 'calc(100vh - 2rem)' }}
    >
      <div className={`flex flex-col gap-3 ${isBottom ? 'flex-col-reverse' : ''}`}>
        {toasts.map(toast => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem
              id={toast.id}
              message={toast.message}
              type={toast.type}
              duration={toast.duration}
              onClose={onClose}
              isExiting={toast.isExiting}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Провайдер контекста уведомлений
 */
export const ToastProvider = ({ children, position = 'top-right', maxToasts = 5 }) => {
  const [toasts, setToasts] = useState([]);
  const timeoutRefs = useRef({});

  /**
   * Удаляет уведомление с анимацией выхода
   */
  const removeToast = useCallback((id) => {
    // Сначала помечаем как выходящий для анимации
    setToasts(prev => prev.map(t => 
      t.id === id ? { ...t, isExiting: true } : t
    ));
    
    // Затем удаляем после анимации
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 300);
    
    // Очищаем таймаут
    if (timeoutRefs.current[id]) {
      clearTimeout(timeoutRefs.current[id]);
      delete timeoutRefs.current[id];
    }
  }, []);

  /**
   * Добавляет новое уведомление
   * @param {string} message - текст уведомления
   * @param {'success' | 'error' | 'warning' | 'info'} type - тип уведомления
   * @param {number} duration - время показа в мс (0 = не скрывать автоматически)
   * @returns {string} id уведомления
   */
  const addToast = useCallback((message, type = 'info', duration = UI_CONFIG.TOAST_DURATION) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    setToasts(prev => {
      // Ограничиваем количество уведомлений
      const newToasts = [...prev, { id, message, type, duration, isExiting: false }];
      if (newToasts.length > maxToasts) {
        // Удаляем старые уведомления
        const toRemove = newToasts.slice(0, newToasts.length - maxToasts);
        toRemove.forEach(t => removeToast(t.id));
        return newToasts.slice(-maxToasts);
      }
      return newToasts;
    });
    
    // Автоматическое удаление
    if (duration > 0) {
      timeoutRefs.current[id] = setTimeout(() => {
        removeToast(id);
      }, duration);
    }
    
    return id;
  }, [maxToasts, removeToast]);

  // Очистка таймаутов при размонтировании
  useEffect(() => {
    return () => {
      Object.values(timeoutRefs.current).forEach(clearTimeout);
    };
  }, []);

  // Удобные методы для разных типов уведомлений
  const success = useCallback((message, duration) => addToast(message, 'success', duration), [addToast]);
  const error = useCallback((message, duration) => addToast(message, 'error', duration), [addToast]);
  const warning = useCallback((message, duration) => addToast(message, 'warning', duration), [addToast]);
  const info = useCallback((message, duration) => addToast(message, 'info', duration), [addToast]);

  // Очистить все уведомления
  const clearAll = useCallback(() => {
    toasts.forEach(t => removeToast(t.id));
  }, [toasts, removeToast]);

  const value = {
    addToast,
    removeToast,
    clearAll,
    success,
    error,
    warning,
    info,
    toasts,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      
      {/* Контейнер для toast-уведомлений */}
      {toasts.length > 0 && (
        <ToastContainer 
          toasts={toasts} 
          position={position} 
          onClose={removeToast} 
        />
      )}
    </ToastContext.Provider>
  );
};

/**
 * Хук для доступа к toast-уведомлениям
 * @returns {{ success: Function, error: Function, warning: Function, info: Function, addToast: Function, removeToast: Function, clearAll: Function }}
 */
export const useToast = () => {
  const context = useContext(ToastContext);
  
  if (!context) {
    // Возвращаем no-op функции если контекст не найден
    // (для использования вне провайдера без ошибок)
    return {
      addToast: () => {},
      removeToast: () => {},
      clearAll: () => {},
      success: () => {},
      error: () => {},
      warning: () => {},
      info: () => {},
      toasts: [],
    };
  }
  
  return context;
};

export default ToastContext;
