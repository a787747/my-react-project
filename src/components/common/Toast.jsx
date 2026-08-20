/**
 * Toast - Компонент уведомлений
 * 
 * Назначение: Показывает временные уведомления пользователю (успех, ошибка, инфо)
 * Используется в: AdminUsers, и других страницах где нужны уведомления
 * 
 * Props:
 * - message: string - текст уведомления
 * - type: 'success' | 'error' | 'info' - тип уведомления (влияет на цвет)
 * - onClose: function - функция закрытия уведомления
 */

import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { UI_CONFIG } from '../../config/constants';

const Toast = ({ message, type = 'info', onClose }) => {
  // Автоматически закрываем уведомление через UI_CONFIG.TOAST_DURATION мс
  useEffect(() => {
    const timer = setTimeout(onClose, UI_CONFIG.TOAST_DURATION);
    return () => clearTimeout(timer);
  }, [onClose]);

  // Определяем цвет фона в зависимости от типа
  const bgColor = type === 'error' 
    ? 'bg-red-500' 
    : type === 'success' 
      ? 'bg-green-500' 
      : 'bg-blue-500';

  return (
    <div className={`fixed top-4 right-4 z-[100] ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-slide-in`}>
      <span>{message}</span>
      <button onClick={onClose} className="hover:opacity-80">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default Toast;

