/**
 * EmptyState - Компонент пустого состояния
 * 
 * Назначение: Показывает заглушку когда нет данных для отображения
 * Используется в: Таблицы, списки, когда нет результатов поиска
 * 
 * Props:
 * - variant: 'default' | 'search' | 'error' | 'noTeam' | 'noEvaluations' | 'success' - тип пустого состояния
 * - icon: React.Component - кастомная иконка (опционально, переопределяет variant)
 * - title: string - заголовок
 * - description: string - описание (опционально)
 * - action: React.Node - кнопка действия (опционально)
 * - actionLabel: string - текст кнопки действия (опционально)
 * - onAction: function - обработчик кнопки действия (опционально)
 * - compact: boolean - компактный режим
 */

import React from 'react';
import { Search, AlertCircle, Users, ClipboardList, CheckCircle, FileQuestion, Inbox, FolderOpen } from 'lucide-react';

/**
 * SVG Иллюстрации для пустых состояний
 */
const Illustrations = {
  // Пустая папка / нет данных
  NoData: () => (
    <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <ellipse cx="100" cy="140" rx="80" ry="12" fill="#e2e8f0" />
      <path d="M40 50 L40 120 L160 120 L160 50 L120 50 L110 35 L70 35 L60 50 Z" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="2" />
      <path d="M60 70 L140 70" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
      <path d="M60 85 L120 85" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
      <path d="M60 100 L100 100" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
      <circle cx="150" cy="45" r="25" fill="#eef2ff" stroke="#c7d2fe" strokeWidth="2" />
      <path d="M142 45 L150 53 L162 38" stroke="#818cf8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  
  // Поиск не дал результатов
  NoResults: () => (
    <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <ellipse cx="100" cy="140" rx="80" ry="12" fill="#e2e8f0" />
      <circle cx="90" cy="70" r="45" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="2" />
      <circle cx="90" cy="70" r="30" fill="white" stroke="#e2e8f0" strokeWidth="2" />
      <path d="M125 105 L155 135" stroke="#cbd5e1" strokeWidth="8" strokeLinecap="round" />
      <path d="M80 60 L100 80 M100 60 L80 80" stroke="#f87171" strokeWidth="3" strokeLinecap="round" />
    </svg>
  ),
  
  // Нет команды
  NoTeam: () => (
    <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <ellipse cx="100" cy="140" rx="80" ry="12" fill="#e2e8f0" />
      <circle cx="100" cy="50" r="25" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="2" />
      <circle cx="100" cy="42" r="10" fill="#cbd5e1" />
      <path d="M85 58 Q100 70 115 58" fill="#cbd5e1" />
      <circle cx="50" cy="80" r="18" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" strokeDasharray="4 2" />
      <circle cx="150" cy="80" r="18" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" strokeDasharray="4 2" />
      <path d="M50 72 L50 88 M42 80 L58 80" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
      <path d="M150 72 L150 88 M142 80 L158 80" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
      <path d="M70 90 Q100 110 130 90" stroke="#e2e8f0" strokeWidth="2" strokeDasharray="4 2" fill="none" />
    </svg>
  ),
  
  // Нет оценок
  NoEvaluations: () => (
    <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <ellipse cx="100" cy="140" rx="80" ry="12" fill="#e2e8f0" />
      <rect x="50" y="30" width="100" height="100" rx="8" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="2" />
      <path d="M70 55 L130 55" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
      <path d="M70 75 L110 75" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
      <path d="M70 95 L90 95" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
      <path d="M100 75 L100 115 L140 95 Z" fill="#fbbf24" stroke="#f59e0b" strokeWidth="2" />
      <circle cx="100" cy="92" r="3" fill="white" />
      <path d="M100 82 L100 87" stroke="white" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  
  // Ошибка
  Error: () => (
    <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <ellipse cx="100" cy="140" rx="80" ry="12" fill="#fee2e2" />
      <circle cx="100" cy="70" r="50" fill="#fef2f2" stroke="#fecaca" strokeWidth="2" />
      <circle cx="100" cy="70" r="35" fill="white" stroke="#fca5a5" strokeWidth="2" />
      <path d="M85 55 L115 85 M115 55 L85 85" stroke="#ef4444" strokeWidth="4" strokeLinecap="round" />
    </svg>
  ),
  
  // Успех / Выполнено
  Success: () => (
    <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
      <ellipse cx="100" cy="140" rx="80" ry="12" fill="#d1fae5" />
      <circle cx="100" cy="70" r="50" fill="#ecfdf5" stroke="#a7f3d0" strokeWidth="2" />
      <circle cx="100" cy="70" r="35" fill="white" stroke="#6ee7b7" strokeWidth="2" />
      <path d="M80 70 L95 85 L125 55" stroke="#10b981" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
};

// Конфигурация вариантов
const VARIANTS = {
  default: {
    illustration: 'NoData',
    icon: Inbox,
    defaultTitle: 'Нет данных',
    defaultDescription: 'Здесь пока ничего нет',
    iconBg: 'bg-slate-100',
    iconColor: 'text-slate-400',
  },
  search: {
    illustration: 'NoResults',
    icon: Search,
    defaultTitle: 'Ничего не найдено',
    defaultDescription: 'Попробуйте изменить параметры поиска',
    iconBg: 'bg-slate-100',
    iconColor: 'text-slate-400',
  },
  noTeam: {
    illustration: 'NoTeam',
    icon: Users,
    defaultTitle: 'Команда не найдена',
    defaultDescription: 'У вас нет прямых подчиненных для оценки',
    iconBg: 'bg-brand-50',
    iconColor: 'text-brand-500',
  },
  noEvaluations: {
    illustration: 'NoEvaluations',
    icon: ClipboardList,
    defaultTitle: 'Нет оценок',
    defaultDescription: 'Вы еще не были оценены',
    iconBg: 'bg-warning-50',
    iconColor: 'text-warning-500',
  },
  error: {
    illustration: 'Error',
    icon: AlertCircle,
    defaultTitle: 'Ошибка загрузки',
    defaultDescription: 'Не удалось загрузить данные. Попробуйте обновить страницу.',
    iconBg: 'bg-danger-50',
    iconColor: 'text-danger-500',
  },
  success: {
    illustration: 'Success',
    icon: CheckCircle,
    defaultTitle: 'Готово!',
    defaultDescription: 'Все задачи выполнены',
    iconBg: 'bg-success-50',
    iconColor: 'text-success-500',
  },
};

const EmptyState = ({ 
  variant = 'default',
  icon: CustomIcon, 
  title, 
  description, 
  action,
  actionLabel,
  onAction,
  compact = false,
  showIllustration = true,
}) => {
  const config = VARIANTS[variant] || VARIANTS.default;
  const Icon = CustomIcon || config.icon;
  const Illustration = Illustrations[config.illustration];
  
  const displayTitle = title || config.defaultTitle;
  const displayDescription = description || config.defaultDescription;

  return (
    <div className={`
      card text-center
      ${compact ? 'p-6' : 'p-8 lg:p-12'}
    `}>
      {/* Иллюстрация или иконка */}
      {showIllustration && Illustration ? (
        <div className={`mx-auto ${compact ? 'w-32 h-24' : 'w-48 h-36'} mb-6`}>
          <Illustration />
        </div>
      ) : Icon && (
        <div className={`
          mx-auto flex items-center justify-center mb-4
          ${compact ? 'w-12 h-12' : 'w-16 h-16'}
          ${config.iconBg} rounded-2xl
        `}>
          <Icon className={`${compact ? 'w-6 h-6' : 'w-8 h-8'} ${config.iconColor}`} />
        </div>
      )}
      
      {/* Заголовок */}
      <h3 className={`
        font-semibold text-slate-900
        ${compact ? 'text-base' : 'text-lg'}
      `}>
        {displayTitle}
      </h3>
      
      {/* Описание */}
      {displayDescription && (
        <p className={`
          text-slate-500 mt-2 max-w-md mx-auto
          ${compact ? 'text-sm' : 'text-base'}
        `}>
          {displayDescription}
        </p>
      )}
      
      {/* Кнопка действия */}
      {(action || (actionLabel && onAction)) && (
        <div className="mt-6">
          {action || (
            <button
              onClick={onAction}
              className="btn btn-primary btn-md"
            >
              {actionLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// Экспортируем иллюстрации для возможного отдельного использования
EmptyState.Illustrations = Illustrations;

export default EmptyState;
