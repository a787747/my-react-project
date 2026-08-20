/**
 * ProfileChart - График динамики оценок
 * 
 * Назначение: Визуализация истории оценок в виде столбчатой диаграммы
 * Используется в: Profile
 * 
 * Props:
 * - evaluations: array - массив оценок менеджера
 */

import React from 'react';

const ProfileChart = ({ evaluations }) => {
  // Показываем график только если есть минимум 2 оценки
  if (!evaluations || evaluations.length < 2) return null;

  const maxScore = 10;

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
      <h2 className="text-xl font-bold text-gray-800 mb-4">
        Динамика оценок менеджера
      </h2>
      <div className="h-64 flex items-end justify-around space-x-2">
        {evaluations.slice().reverse().map((evaluation, index) => {
          const heightPercent = (parseFloat(evaluation.score) / maxScore) * 100;
          
          return (
            <div key={index} className="flex flex-col items-center flex-1">
              {/* Столбец */}
              <div className="w-full bg-gray-200 rounded-t-lg relative" style={{ height: '200px' }}>
                <div 
                  className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t-lg absolute bottom-0 flex items-center justify-center text-white font-bold transition-all duration-500"
                  style={{ height: `${heightPercent}%` }}
                >
                  {evaluation.score}
                </div>
              </div>
              {/* Подпись */}
              <div className="text-xs text-gray-600 mt-2 text-center">
                {evaluation.period_name}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ProfileChart;

