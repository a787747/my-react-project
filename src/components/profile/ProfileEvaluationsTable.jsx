/**
 * ProfileEvaluationsTable - Таблица истории оценок
 * 
 * Назначение: Отображение списка всех оценок пользователя
 * Используется в: Profile
 * 
 * Props:
 * - evaluations: array - массив всех оценок
 * - formatDate: function - функция форматирования даты
 * - onViewDetails: function(evaluation) - открыть детали
 * - hideManagerEvaluations: boolean - скрыть оценки менеджера (показывать только самооценки)
 * - showWeightedScore: boolean - показывать взвешенный балл (для Admin/C-level)
 */

import React from 'react';
import { Eye } from 'lucide-react';

const ProfileEvaluationsTable = ({ evaluations, formatDate, onViewDetails, hideManagerEvaluations = false, showWeightedScore = false }) => {
  if (!evaluations || evaluations.length === 0) return null;

  // Фильтруем оценки, если нужно скрыть оценки менеджера
  const filteredEvaluations = hideManagerEvaluations
    ? evaluations.filter(e => e.is_self_evaluation)
    : evaluations;
  
  if (filteredEvaluations.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-800">
          История оценок
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Период
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Тип оценки
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Оценка
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Оценил
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Дата
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredEvaluations.map((evaluation) => (
              <tr 
                key={evaluation.evaluation_id} 
                className={`hover:bg-gray-50 ${evaluation.is_self_evaluation ? 'bg-blue-50' : ''}`}
              >
                {/* Период */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {evaluation.period_name}
                  </span>
                </td>
                
                {/* Тип оценки */}
                <td className="px-6 py-4 whitespace-nowrap">
                  {evaluation.is_self_evaluation ? (
                    <span className="px-3 py-1 inline-flex text-sm leading-5 font-bold rounded-full bg-gradient-to-r from-blue-500 to-purple-600 text-white">
                      ⭐ САМООЦЕНКА
                    </span>
                  ) : (
                    <span className="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full bg-gray-100 text-gray-700">
                      Оценка менеджера
                    </span>
                  )}
                </td>
                
                {/* Оценка */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <span className="text-2xl font-bold text-gray-900">
                      {parseFloat(evaluation.score).toFixed(1)}
                    </span>
                    <span className="text-sm text-gray-500 ml-1">/10</span>
                    
                    {/* Взвешенный балл для Admin/C-level */}
                    {showWeightedScore && evaluation.weighted_score && (
                      <div className="text-xs text-purple-600 mt-1">
                        Взвешенный: {parseFloat(evaluation.weighted_score).toFixed(2)}
                      </div>
                    )}
                  </div>
                </td>
                
                {/* Оценщик */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {evaluation.is_self_evaluation ? 'Вы сами' : evaluation.evaluator_name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {evaluation.is_self_evaluation ? 'Самостоятельно' : evaluation.evaluator_title}
                    </div>
                  </div>
                </td>
                
                {/* Дата */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {formatDate(evaluation.updated_at)}
                </td>
                
                {/* Действия */}
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button
                    onClick={() => onViewDetails(evaluation)}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    Детали
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ProfileEvaluationsTable;

