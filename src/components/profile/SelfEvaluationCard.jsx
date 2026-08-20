/**
 * SelfEvaluationCard - Карточка самооценки
 * 
 * Назначение: Отображение последней самооценки пользователя
 * Используется в: Profile
 * 
 * Props:
 * - selfEvaluation: object - данные последней самооценки
 * - formatDate: function - функция форматирования даты
 * - onViewDetails: function - открыть детали
 */

import React from 'react';
import { Star, Eye } from 'lucide-react';

const SelfEvaluationCard = ({ selfEvaluation, formatDate, onViewDetails }) => {
  if (!selfEvaluation) return null;

  return (
    <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl shadow-sm p-6 mb-8 border-2 border-blue-200">
      <div className="flex items-start gap-4">
        {/* Иконка */}
        <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
          <Star className="w-8 h-8 text-white" />
        </div>
        
        {/* Контент */}
        <div className="flex-1">
          <h3 className="text-xl font-bold text-gray-900 mb-2 flex items-center gap-2">
            ⭐ Ваша самооценка
            <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">
              САМООЦЕНКА
            </span>
          </h3>
          
          {/* Статистика */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-600">Оценка</p>
              <p className="text-3xl font-bold text-blue-600">
                {parseFloat(selfEvaluation.score).toFixed(1)}
                <span className="text-lg text-gray-400 font-normal">/10</span>
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Дата</p>
              <p className="text-sm font-semibold text-gray-800">
                {formatDate(selfEvaluation.updated_at)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Период</p>
              <p className="text-sm font-semibold text-gray-800">
                {selfEvaluation.period_name}
              </p>
            </div>
          </div>
          
          {/* Кнопка */}
          <button
            onClick={() => onViewDetails(selfEvaluation)}
            className="px-4 py-2 bg-white border-2 border-blue-300 text-blue-700 rounded-lg font-medium hover:bg-blue-50 transition-colors flex items-center gap-2"
          >
            <Eye className="w-4 h-4" />
            Посмотреть детали самооценки
          </button>
        </div>
      </div>
    </div>
  );
};

export default SelfEvaluationCard;

