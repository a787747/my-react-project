/**
 * LoadingSpinner - Компонент индикатора загрузки
 * 
 * Назначение: Показывает анимированный спиннер во время загрузки данных
 * Используется в: Практически на всех страницах при загрузке данных
 * 
 * Props:
 * - size: 'sm' | 'md' | 'lg' | 'xl' - размер спиннера (по умолчанию 'md')
 * - text: string - опциональный текст под спиннером
 * - fullScreen: boolean - занимать ли весь экран (по умолчанию true)
 * - overlay: boolean - показывать как оверлей поверх контента
 * 
 * Accessibility:
 * - role="status" для screen readers
 * - aria-live="polite" для объявления состояния
 * - aria-label с описанием
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingSpinner = ({ 
  size = 'md', 
  text = '', 
  fullScreen = true,
  overlay = false 
}) => {
  // Определяем размер иконки
  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };

  const textSizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  };

  const spinnerContent = (
    <div 
      className="text-center" 
      role="status" 
      aria-live="polite"
      aria-label={text || 'Загрузка'}
    >
      <Loader2 
        className={`${sizeClasses[size]} text-brand-600 animate-spin mx-auto`} 
        aria-hidden="true"
      />
      {text && (
        <p className={`text-slate-500 mt-4 font-medium ${textSizes[size]}`}>
          {text}
        </p>
      )}
      {/* Screen reader only text if no visible text */}
      {!text && <span className="sr-only">Загрузка...</span>}
    </div>
  );

  // Оверлей поверх контента
  if (overlay) {
    return (
      <div 
        className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-inherit"
        aria-busy="true"
      >
        {spinnerContent}
      </div>
    );
  }

  // Полноэкранный режим
  if (fullScreen) {
    return (
      <div 
        className="flex items-center justify-center min-h-screen bg-surface-raised"
        aria-busy="true"
      >
        {spinnerContent}
      </div>
    );
  }

  return spinnerContent;
};

export default LoadingSpinner;
