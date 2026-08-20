/**
 * EvaluationDetailsModal - Модальное окно с деталями оценки
 * 
 * Назначение: Показывает детальную информацию по критериям оценки
 * Используется в: Profile, EvaluationHistory, AdminAllEvaluations
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - evaluation: object - выбранная оценка
 * - details: object - детали оценки (критерии и баллы)
 * - loading: boolean - загрузка деталей
 * - formatDate: function - функция форматирования даты
 * - onClose: function - закрыть окно
 * - hideManagerDetails: boolean - скрыть детали оценок менеджера
 */

import React from 'react';
import { Award, Loader2, Lock } from 'lucide-react';

const EvaluationDetailsModal = ({ 
  isOpen, 
  evaluation, 
  details, 
  loading, 
  formatDate, 
  onClose,
  hideManagerDetails = false
}) => {
  if (!isOpen || !evaluation) return null;

  // Если нужно скрыть детали менеджера и это не самооценка
  if (hideManagerDetails && !evaluation.is_self_evaluation) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
          <div className="p-6 border-b border-gray-200">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-2xl font-bold text-gray-800 mb-1">
                  Оценка менеджера
                </h3>
                <p className="text-gray-600">
                  {evaluation.period_name} • {formatDate(evaluation.updated_at)}
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 text-3xl leading-none"
              >
                ×
              </button>
            </div>
          </div>
          <div className="p-6 text-center">
            <Lock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h4 className="text-lg font-semibold text-gray-800 mb-2">
              Детали оценки недоступны
            </h4>
            <p className="text-gray-600 mb-4">
              Вы можете видеть только факт того, что менеджер провел оценку. 
              Детальные результаты доступны руководству компании.
            </p>
            <button
              onClick={onClose}
              className="w-full bg-gray-600 text-white py-3 rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className={`sticky top-0 border-b border-gray-200 p-6 z-10 ${
          evaluation.is_self_evaluation 
            ? 'bg-gradient-to-r from-blue-50 to-purple-50' 
            : 'bg-white'
        }`}>
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                Детали оценки
                {evaluation.is_self_evaluation && (
                  <span className="px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white text-xs font-bold rounded-full">
                    ⭐ САМООЦЕНКА
                  </span>
                )}
              </h3>
              <p className="text-gray-600 mt-1">
                {evaluation.period_name} • {formatDate(evaluation.updated_at)}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-3xl leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
              <div className="text-gray-600 mt-2">Загрузка деталей...</div>
            </div>
          ) : details ? (
            <>
              {/* Summary */}
              <div className={`rounded-lg p-6 mb-6 ${
                evaluation.is_self_evaluation
                  ? 'bg-gradient-to-r from-blue-50 to-purple-50'
                  : 'bg-gradient-to-r from-blue-50 to-purple-50'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Итоговая оценка</div>
                    <div className="text-4xl font-bold text-gray-800">
                      {details.evaluation?.calculated_score}
                    </div>
                    {evaluation.is_self_evaluation && (
                      <p className="text-sm text-blue-700 mt-2 font-semibold">
                        Это ваша собственная оценка своей работы
                      </p>
                    )}
                  </div>
                  <Award className="w-16 h-16 text-blue-500" />
                </div>
              </div>

              {/* Criteria Breakdown */}
              <div className="space-y-4">
                <h4 className="text-lg font-bold text-gray-800 mb-4">
                  Оценка по критериям
                </h4>
                {details.scores?.map((score, index) => (
                  <div key={index} className="border-b border-gray-200 pb-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium text-gray-800">
                        {score.criteria_title}
                      </span>
                      <span className="text-xl font-bold text-blue-600">
                        {score.score_value}/10
                      </span>
                    </div>
                    {/* Progress Bar */}
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
                        style={{ width: `${(score.score_value / 10) * 100}%` }}
                      />
                    </div>
                    {score.criteria_description && (
                      <p className="text-sm text-gray-600 mt-2">
                        {score.criteria_description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-red-600">
              Ошибка загрузки деталей
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6">
          <button
            onClick={onClose}
            className="w-full bg-gray-600 text-white py-3 rounded-lg hover:bg-gray-700 transition-colors font-medium"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

export default EvaluationDetailsModal;

