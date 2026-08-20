/**
 * EvaluationBlock - Блок оценки с критериями
 * 
 * Назначение: Отображение оценки со всеми критериями и сравнением с самооценкой
 * Используется в: AdminAllEvaluations
 * 
 * Props:
 * - evaluation: object - данные оценки
 * - title: string - заголовок блока
 * - bgColor: string - CSS классы фона
 * - selfEvaluation: object | null - самооценка для сравнения
 * - formatDate: function - функция форматирования даты
 */

import React from 'react';

const EvaluationBlock = ({ evaluation, title, bgColor, selfEvaluation, formatDate }) => {
  if (!evaluation) return null;

  // Создаём Map самооценок по criteria_id для быстрого поиска
  const selfScoresMap = {};
  if (selfEvaluation && selfEvaluation.criteria) {
    selfEvaluation.criteria.forEach(criterion => {
      selfScoresMap[criterion.criteria_id] = criterion.score_value;
    });
  }

  return (
    <div className={`${bgColor} rounded-xl p-6 mb-4`}>
      {/* Заголовок */}
      <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
        {title}
        <span className="text-2xl font-bold ml-auto">{evaluation.calculated_score}</span>
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Оценил: {evaluation.evaluator_name} • {formatDate(evaluation.updated_at)}
      </p>

      {/* Критерии */}
      <div className="space-y-4">
        {evaluation.criteria.map((criterion, idx) => {
          const selfScore = selfScoresMap[criterion.criteria_id];
          
          return (
            <div key={idx} className="bg-white rounded-lg p-4 shadow-sm">
              {/* Название и оценка */}
              <div className="flex justify-between items-start mb-3">
                <span className="font-medium text-gray-900">{criterion.criteria_title}</span>
                <span className="text-xl font-bold text-indigo-600">{criterion.score_value}</span>
              </div>
              
              {/* Прогресс-бар оценки менеджера */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Оценка менеджера</span>
                  <span>{criterion.score_value}/10</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className="bg-indigo-600 h-3 rounded-full transition-all"
                    style={{ width: `${(criterion.score_value / 10) * 100}%` }}
                  />
                </div>
              </div>

              {/* Прогресс-бар самооценки (если есть) */}
              {selfScore !== undefined && (
                <div className="mb-2">
                  <div className="flex justify-between text-xs text-blue-600 mb-1">
                    <span className="font-medium">⭐ Самооценка</span>
                    <span className="font-bold">{selfScore}/10</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all"
                      style={{ width: `${(selfScore / 10) * 100}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Комментарий */}
              {criterion.comment && (
                <p className="text-sm text-gray-600 mt-3 italic border-l-2 border-gray-300 pl-3">
                  "{criterion.comment}"
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EvaluationBlock;

