/**
 * EvaluationHistoryModal - Модальное окно деталей оценки
 * 
 * Назначение: Показывает детальную информацию по критериям проведенной оценки
 * Используется в: EvaluationHistory
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - evaluation: object - выбранная оценка
 * - details: object - детали оценки
 * - loading: boolean - загрузка деталей
 * - formatDate: function - форматирование даты
 * - onClose: function - закрыть окно
 */

import React from 'react';
import { User, X, Loader2, Star, TrendingUp } from 'lucide-react';

const EvaluationHistoryModal = ({ 
  isOpen, 
  evaluation, 
  details, 
  loading, 
  formatDate, 
  onClose 
}) => {
  if (!isOpen || !evaluation) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white p-6 flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
              <User className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">
                {evaluation.evaluatee_name}
              </h2>
              <p className="text-indigo-100 text-sm">{evaluation.job_title}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-indigo-200 mb-1">
              {formatDate(evaluation.evaluation_date)}
            </div>
            {evaluation.period_name && (
              <div className="text-sm text-indigo-100">
                {evaluation.period_name}
              </div>
            )}
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-full transition-colors ml-4"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
            </div>
          ) : details ? (
            <>
              {/* Итоговый балл */}
              <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-6 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Итоговый балл</div>
                    <div className="text-4xl font-bold text-indigo-600">
                      {details.evaluation?.final_score || details.evaluation?.calculated_score || '0.0'}
                    </div>
                  </div>
                  <div className="p-4 bg-white/50 rounded-full">
                    <Star className="w-12 h-12 text-indigo-600" />
                  </div>
                </div>
              </div>

              {/* Детализация по критериям */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-gray-600" />
                  Детализация по критериям
                  {details.scores && details.scores.length > 0 && (
                    <span className="text-sm font-normal text-gray-500">
                      ({details.scores.length} {details.scores.length === 1 ? 'критерий' : 'критериев'})
                    </span>
                  )}
                </h3>
                {details.scores && details.scores.length > 0 ? (
                  <div className="space-y-4">
                    {details.scores.map((score, index) => (
                      <div 
                        key={score.id || score.criteria_id || index}
                        className="bg-white border border-gray-200 rounded-lg p-5 hover:border-indigo-300 hover:shadow-md transition-all"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="font-semibold text-gray-900 mb-2 text-lg">
                              {score.criteria_title || `Критерий ${index + 1}`}
                            </div>
                            {score.criteria_description && (
                              <div className="text-sm text-gray-600 mb-3 leading-relaxed">
                                {score.criteria_description}
                              </div>
                            )}
                            {(score.comment || score.score_comment) && (
                              <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                <div className="text-xs font-medium text-blue-700 mb-1">Комментарий:</div>
                                <div className="text-sm text-blue-900">{score.comment || score.score_comment}</div>
                              </div>
                            )}
                          </div>
                          <div className="ml-4 flex-shrink-0">
                            <div className="text-3xl font-bold text-indigo-600">
                              {parseFloat(score.score_value || 0).toFixed(1)}
                            </div>
                            <div className="text-xs text-gray-500 text-right mt-1">из 10</div>
                          </div>
                        </div>
                        
                        <div className="mt-4">
                          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                            <div 
                              className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-3 rounded-full transition-all"
                              style={{ width: `${Math.min((parseFloat(score.score_value || 0) / 10) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
                    <TrendingUp className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="font-medium">Детальные оценки отсутствуют</p>
                    <p className="text-sm mt-1">По данной оценке нет детализации по критериям</p>
                  </div>
                )}
              </div>
              
              {/* Общий комментарий, если есть */}
              {details.evaluation?.general_comment && (
                <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="text-sm font-semibold text-amber-800 mb-2">Общий комментарий:</div>
                  <div className="text-sm text-amber-900 leading-relaxed">
                    {details.evaluation.general_comment}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12 text-gray-500">
              Не удалось загрузить детали оценки
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-100 bg-gray-50 sticky bottom-0">
          <button
            onClick={onClose}
            className="w-full py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

export default EvaluationHistoryModal;

