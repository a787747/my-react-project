/**
 * Modal - Базовый компонент модального окна
 * 
 * Назначение: Унифицированный компонент модального окна с анимациями
 * Используется в: EvaluationModal, UserModal, SelfReviewModal и др.
 * 
 * Props:
 * - isOpen: boolean - открыто ли модальное окно
 * - onClose: function - колбэк закрытия
 * - title: string - заголовок модалки (опционально)
 * - subtitle: string - подзаголовок (опционально)
 * - size: 'sm' | 'md' | 'lg' | 'xl' | 'full' - размер модалки
 * - showCloseButton: boolean - показывать ли кнопку закрытия (по умолчанию true)
 * - closeOnEscape: boolean - закрывать ли по Escape (по умолчанию true)
 * - closeOnOverlay: boolean - закрывать ли по клику на оверлей (по умолчанию true)
 * - children: ReactNode - содержимое модалки
 * - footer: ReactNode - футер модалки (опционально)
 * - headerGradient: string - градиент для заголовка (опционально)
 * - headerIcon: ReactNode - иконка в заголовке (опционально)
 */

import React, { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

// Размеры модального окна
const SIZES = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-6xl',
};

const Modal = ({
  isOpen,
  onClose,
  title,
  subtitle,
  size = 'lg',
  showCloseButton = true,
  closeOnEscape = true,
  closeOnOverlay = true,
  children,
  footer,
  headerGradient = 'from-brand-600 to-brand-700',
  headerIcon,
}) => {
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);

  // Обработка Escape
  const handleEscape = useCallback((e) => {
    if (e.key === 'Escape' && closeOnEscape) {
      onClose();
    }
  }, [closeOnEscape, onClose]);

  // Обработка клика на оверлей
  const handleOverlayClick = useCallback((e) => {
    if (e.target === e.currentTarget && closeOnOverlay) {
      onClose();
    }
  }, [closeOnOverlay, onClose]);

  // Эффекты при открытии/закрытии
  useEffect(() => {
    if (isOpen) {
      // Сохраняем текущий активный элемент
      previousActiveElement.current = document.activeElement;
      
      // Блокируем скролл body
      document.body.style.overflow = 'hidden';
      
      // Добавляем обработчик Escape
      document.addEventListener('keydown', handleEscape);
      
      // Фокус на модалку
      setTimeout(() => {
        modalRef.current?.focus();
      }, 100);
    }

    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
      
      // Возвращаем фокус
      if (previousActiveElement.current && !isOpen) {
        previousActiveElement.current.focus?.();
      }
    };
  }, [isOpen, handleEscape]);

  // Не рендерим если закрыто
  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in"
        onClick={handleOverlayClick}
        aria-hidden="true"
      />
      
      {/* Modal Container */}
      <div 
        ref={modalRef}
        tabIndex={-1}
        className={`
          relative w-full ${SIZES[size]} max-h-[90vh] 
          bg-white rounded-2xl shadow-2xl 
          flex flex-col overflow-hidden
          animate-scale-in
        `}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className={`
            relative shrink-0 p-6
            ${title ? `bg-gradient-to-br ${headerGradient} text-white` : 'border-b border-slate-200'}
          `}>
            <div className="flex items-start justify-between gap-4">
              {title && (
                <div className="flex items-center gap-4">
                  {headerIcon && (
                    <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                      {headerIcon}
                    </div>
                  )}
                  <div>
                    <h2 id="modal-title" className="text-xl font-bold">
                      {title}
                    </h2>
                    {subtitle && (
                      <p className={`text-sm mt-1 ${title ? 'text-white/80' : 'text-slate-500'}`}>
                        {subtitle}
                      </p>
                    )}
                  </div>
                </div>
              )}
              
              {showCloseButton && (
                <button
                  onClick={onClose}
                  className={`
                    p-2 rounded-xl transition-colors
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-white/50
                    ${title 
                      ? 'hover:bg-white/20 text-white/80 hover:text-white' 
                      : 'hover:bg-slate-100 text-slate-400 hover:text-slate-600'
                    }
                  `}
                  aria-label="Закрыть"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="shrink-0 p-6 border-t border-slate-200 bg-slate-50">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Modal.Header - Компонент заголовка для кастомного оформления
 */
Modal.Header = ({ children, className = '' }) => (
  <div className={`shrink-0 ${className}`}>
    {children}
  </div>
);

/**
 * Modal.Body - Компонент тела модалки
 */
Modal.Body = ({ children, className = '', padding = true }) => (
  <div className={`flex-1 overflow-y-auto scrollbar-thin ${padding ? 'p-6' : ''} ${className}`}>
    {children}
  </div>
);

/**
 * Modal.Footer - Компонент футера модалки
 */
Modal.Footer = ({ children, className = '' }) => (
  <div className={`shrink-0 p-6 border-t border-slate-200 bg-slate-50 ${className}`}>
    {children}
  </div>
);

/**
 * Modal.Actions - Компонент действий в футере
 */
Modal.Actions = ({ children, className = '' }) => (
  <div className={`flex items-center justify-end gap-3 ${className}`}>
    {children}
  </div>
);

export default Modal;





