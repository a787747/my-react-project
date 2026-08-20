/**
 * EvaluationHistoryCard - Карточка оценки в истории
 * 
 * Назначение: Отображение краткой информации об оценке в виде карточки
 * Используется в: EvaluationHistory
 * 
 * Props:
 * - evaluation: object - данные оценки
 * - formatDate: function - функция форматирования даты
 * - onClick: function - клик по карточке
 * - variant: string - вариант стиля ('default' | 'manager')
 */

import React from 'react';
import { User, Calendar, Award, Crown } from 'lucide-react';

const EvaluationHistoryCard = ({ evaluation, formatDate, onClick, variant = 'default' }) => {
  // Стили в зависимости от варианта
  const isManagerVariant = variant === 'manager';
  
  const styles = {
    default: {
      border: 'border-gray-100 hover:border-indigo-200',
      iconBg: 'bg-indigo-50 group-hover:bg-indigo-100',
      iconColor: 'text-indigo-600',
      scoreColor: 'text-indigo-600',
      periodColor: 'text-indigo-600',
      hoverText: 'text-indigo-600',
      badge: null
    },
    manager: {
      border: 'border-purple-100 hover:border-purple-300',
      iconBg: 'bg-purple-50 group-hover:bg-purple-100',
      iconColor: 'text-purple-600',
      scoreColor: 'text-purple-600',
      periodColor: 'text-purple-600',
      hoverText: 'text-purple-600',
      badge: 'Оценка руководителя'
    }
  };

  const currentStyle = styles[variant] || styles.default;
  const Icon = isManagerVariant ? Crown : User;

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl shadow-sm border p-6 hover:shadow-lg transition-all cursor-pointer group ${currentStyle.border}`}
    >
      {/* Бейдж для оценки руководителя */}
      {currentStyle.badge && (
        <div className="mb-3">
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
            <Crown className="w-3 h-3" />
            {currentStyle.badge}
          </span>
        </div>
      )}

      {/* Header карточки */}
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-lg transition-colors ${currentStyle.iconBg}`}>
          <Icon className={`w-6 h-6 ${currentStyle.iconColor}`} />
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${currentStyle.scoreColor}`}>
            {evaluation.final_score ? parseFloat(evaluation.final_score).toFixed(1) : '0.0'}
          </div>
          <div className="text-xs text-gray-500">балл</div>
        </div>
      </div>

      {/* Имя сотрудника */}
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        {evaluation.evaluatee_name || 'Неизвестный сотрудник'}
      </h3>
      <p className="text-sm text-gray-500 mb-4">{evaluation.job_title || 'Должность не указана'}</p>

      {/* Детали */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center text-sm text-gray-600">
          <Calendar className="w-4 h-4 mr-2 text-gray-400" />
          {formatDate(evaluation.evaluation_date)}
        </div>
        <div className="flex items-center text-sm text-gray-600">
          <Award className="w-4 h-4 mr-2 text-gray-400" />
          {evaluation.grade_name || '-'} • {evaluation.department_name || '-'}
        </div>
      </div>

      {/* Период */}
      <div className="pt-4 border-t border-gray-100">
        <div className="flex items-center text-xs text-gray-500">
          <Calendar className="w-3 h-3 mr-1" />
          Период:
          <span className={`ml-1 font-medium ${currentStyle.periodColor}`}>
            {evaluation.period_name || 'Не указан'}
          </span>
        </div>
      </div>

      {/* Hover эффект */}
      <div className={`mt-4 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity ${currentStyle.hoverText}`}>
        Посмотреть детали →
      </div>
    </div>
  );
};

export default EvaluationHistoryCard;

