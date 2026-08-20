/**
 * AllEvaluationsDetailsModal - Модальное окно деталей оценок
 * 
 * Назначение: Показывает детали оценок в зависимости от типа
 * Используется в: AdminAllEvaluations
 * 
 * Types:
 * - 'self' - Самооценка сотрудника
 * - 'received_from_manager' - Оценка, полученная от руководителя
 * - 'gave_to_manager' - Оценка, данная руководителю
 * - 'gave_to_subordinates' - Оценки, данные подчинённым
 * - 'all' - Все оценки
 */

import React from 'react';
import { X, Loader2, Star, UserCheck, Users, MessageSquare, Award, UserMinus } from 'lucide-react';

const AllEvaluationsDetailsModal = ({ 
  isOpen, 
  employee, 
  detailsData, 
  detailType,
  loading,
  formatDate, 
  onClose 
}) => {
  if (!isOpen || !employee) return null;

  // Заголовки для разных типов
  const typeConfig = {
    self: {
      title: 'Самооценка',
      subtitle: 'Оценки, которые сотрудник поставил себе',
      icon: <Star className="w-6 h-6" />,
      gradient: 'from-blue-600 to-indigo-600'
    },
    received_from_manager: {
      title: 'Оценка от руководителя',
      subtitle: 'Оценка, которую сотруднику поставил его руководитель',
      icon: <UserCheck className="w-6 h-6" />,
      gradient: 'from-green-600 to-emerald-600'
    },
    gave_to_manager: {
      title: 'Оценка руководителю',
      subtitle: 'Оценка, которую сотрудник поставил своему руководителю',
      icon: <UserCheck className="w-6 h-6" />,
      gradient: 'from-teal-600 to-cyan-600'
    },
    gave_to_subordinates: {
      title: 'Оценки подчинённым',
      subtitle: 'Оценки, которые сотрудник поставил своим подчинённым',
      icon: <Users className="w-6 h-6" />,
      gradient: 'from-purple-600 to-pink-600'
    },
    from_subordinates: {
      title: 'Оценки от подчинённых',
      subtitle: 'Как подчинённые оценили этого руководителя',
      icon: <UserMinus className="w-6 h-6" />,
      gradient: 'from-orange-600 to-amber-600'
    },
    all: {
      title: 'Все оценки',
      subtitle: 'Полная информация по оценкам сотрудника',
      icon: <Award className="w-6 h-6" />,
      gradient: 'from-indigo-600 to-purple-600'
    }
  };

  const config = typeConfig[detailType] || typeConfig.all;

  // Рендер блока оценки с критериями
  const renderEvaluationBlock = (evaluation, title, bgClass, borderClass) => {
    if (!evaluation) return null;

    return (
      <div className={`rounded-xl border-2 ${borderClass} overflow-hidden mb-4`}>
        <div className={`${bgClass} px-4 py-3 flex items-center justify-between`}>
          <div>
            <h4 className="font-bold text-gray-900">{title}</h4>
            <p className="text-xs text-gray-600">
              {formatDate(evaluation.updated_at)} • Балл: <span className="font-bold">{evaluation.calculated_score}</span>
            </p>
          </div>
          {evaluation.evaluator_name && (
            <div className="text-right text-sm">
              <p className="text-gray-500">Оценщик:</p>
              <p className="font-medium text-gray-800">{evaluation.evaluator_name}</p>
            </div>
          )}
        </div>
        
        <div className="divide-y divide-gray-100">
          {evaluation.criteria?.map((criterion, idx) => (
            <div key={`crit-${criterion.criteria_id || idx}`} className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">{criterion.criteria_title}</p>
                  {criterion.comment && (
                    <div className="mt-2 flex items-start gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                      <MessageSquare className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
                      <span>{criterion.comment}</span>
                    </div>
                  )}
                </div>
                <div className="shrink-0">
                  <span className={`inline-flex items-center justify-center w-10 h-10 rounded-xl font-bold text-lg ${
                    criterion.score_value >= 8 ? 'bg-green-100 text-green-700' :
                    criterion.score_value >= 5 ? 'bg-yellow-100 text-yellow-700' :
                    criterion.score_value ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-400'
                  }`}>
                    {criterion.score_value ?? '—'}
                  </span>
                </div>
              </div>
            </div>
          ))}
          
          {(!evaluation.criteria || evaluation.criteria.length === 0) && (
            <div className="px-4 py-6 text-center text-gray-500 text-sm">
              Нет детальных оценок по критериям
            </div>
          )}
        </div>
      </div>
    );
  };

  // Рендер списка оценок подчинённым
  const renderSubordinatesEvaluations = (evaluations) => {
    if (!evaluations || evaluations.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          Нет оценок подчинённым
        </div>
      );
    }

    return evaluations.map((evaluation, idx) => (
      <div key={`sub-eval-${evaluation.evaluation_id || idx}`} className="rounded-xl border-2 border-purple-200 overflow-hidden mb-4">
        <div className="bg-purple-50 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold">
              {evaluation.subject_name?.charAt(0)}
            </div>
            <div>
              <h4 className="font-bold text-gray-900">{evaluation.subject_name}</h4>
              <p className="text-xs text-gray-600">{evaluation.subject_job_title}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-purple-600">{evaluation.calculated_score}</div>
            <p className="text-xs text-gray-500">{formatDate(evaluation.updated_at)}</p>
          </div>
        </div>
        
        <div className="divide-y divide-gray-100">
          {evaluation.criteria?.map((criterion, cidx) => (
            <div key={`sub-crit-${criterion.criteria_id || cidx}`} className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">{criterion.criteria_title}</p>
                  {criterion.comment && (
                    <div className="mt-2 flex items-start gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                      <MessageSquare className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
                      <span>{criterion.comment}</span>
                    </div>
                  )}
                </div>
                <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg font-bold text-sm ${
                  criterion.score_value >= 8 ? 'bg-green-100 text-green-700' :
                  criterion.score_value >= 5 ? 'bg-yellow-100 text-yellow-700' :
                  criterion.score_value ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  {criterion.score_value ?? '—'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    ));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className={`bg-gradient-to-r ${config.gradient} text-white p-6 flex justify-between items-start shrink-0`}>
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
              {config.icon}
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">{employee.full_name}</h2>
              <p className="text-white/80 text-sm">{employee.job_title}</p>
              <p className="text-white/60 text-xs mt-1">{config.subtitle}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 min-h-0">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mb-4" />
              <p className="text-gray-500">Загрузка деталей...</p>
            </div>
          ) : detailsData ? (
            <>
              {/* Самооценка */}
              {(detailType === 'self' || detailType === 'all') && detailsData.self_evaluation && (
                <div>
                  {detailType === 'all' && (
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                      <Star className="w-5 h-5 text-blue-600" />
                      Самооценка
                    </h3>
                  )}
                  {renderEvaluationBlock(
                    detailsData.self_evaluation,
                    detailType === 'all' ? `Балл: ${detailsData.self_evaluation.calculated_score}` : 'Самооценка сотрудника',
                    'bg-blue-50',
                    'border-blue-200'
                  )}
                </div>
              )}

              {/* Оценка от руководителя (включая C-Level) */}
              {(detailType === 'received_from_manager' || detailType === 'all') && (detailsData.manager_evaluations?.length > 0 || (detailType === 'received_from_manager' && detailsData.c_level_evaluations?.length > 0)) && (
                <div>
                  {detailType === 'all' && (
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                      <UserCheck className="w-5 h-5 text-green-600" />
                      Оценки от руководителей
                    </h3>
                  )}
                  {detailsData.manager_evaluations?.map((evaluation, idx) => (
                    <React.Fragment key={`manager-eval-${evaluation.evaluation_id || idx}`}>
                      {renderEvaluationBlock(
                        evaluation,
                        `Оценка от ${evaluation.evaluator_name}`,
                        'bg-green-50',
                        'border-green-200'
                      )}
                    </React.Fragment>
                  ))}
                  {/* Для received_from_manager также показываем C-Level оценки */}
                  {detailType === 'received_from_manager' && detailsData.c_level_evaluations?.map((evaluation, idx) => (
                    <React.Fragment key={`clevel-manager-eval-${evaluation.evaluation_id || idx}`}>
                      {renderEvaluationBlock(
                        evaluation,
                        `Оценка от ${evaluation.evaluator_name} (C-Level)`,
                        'bg-amber-50',
                        'border-amber-200'
                      )}
                    </React.Fragment>
                  ))}
                </div>
              )}

              {/* Оценка руководителю */}
              {(detailType === 'gave_to_manager' || detailType === 'all') && detailsData.evaluation_to_manager && (
                <div>
                  {detailType === 'all' && (
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                      <UserCheck className="w-5 h-5 text-teal-600" />
                      Оценка своему руководителю
                    </h3>
                  )}
                  {renderEvaluationBlock(
                    detailsData.evaluation_to_manager,
                    `Оценка для ${detailsData.evaluation_to_manager.subject_name}`,
                    'bg-teal-50',
                    'border-teal-200'
                  )}
                </div>
              )}

              {/* Оценки подчинённым */}
              {(detailType === 'gave_to_subordinates' || detailType === 'all') && detailsData.evaluations_to_subordinates?.length > 0 && (
                <div>
                  {detailType === 'all' && (
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                      <Users className="w-5 h-5 text-purple-600" />
                      Оценки подчинённым ({detailsData.evaluations_to_subordinates.length})
                    </h3>
                  )}
                  {renderSubordinatesEvaluations(detailsData.evaluations_to_subordinates)}
                </div>
              )}

              {/* Оценки ОТ подчинённых (как подчинённые оценили этого руководителя) */}
              {(detailType === 'from_subordinates' || detailType === 'all') && detailsData.subordinate_evaluations?.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                    <UserMinus className="w-5 h-5 text-orange-600" />
                    Оценки от подчинённых ({detailsData.subordinate_evaluations.length})
                  </h3>
                  {detailsData.subordinate_evaluations.map((evaluation, idx) => (
                    <div key={`from-sub-${evaluation.evaluation_id || idx}`} className="rounded-xl border-2 border-orange-200 overflow-hidden mb-4">
                      <div className="bg-orange-50 px-4 py-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-orange-600 rounded-full flex items-center justify-center text-white font-bold">
                            {evaluation.evaluator_name?.charAt(0)}
                          </div>
                          <div>
                            <h4 className="font-bold text-gray-900">{evaluation.evaluator_name}</h4>
                            <p className="text-xs text-gray-600">Подчинённый</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-orange-600">{evaluation.calculated_score}</div>
                          <p className="text-xs text-gray-500">{formatDate(evaluation.updated_at)}</p>
                        </div>
                      </div>
                      
                      <div className="divide-y divide-gray-100">
                        {evaluation.criteria?.map((criterion, cidx) => (
                          <div key={`from-sub-crit-${criterion.criteria_id || cidx}`} className="px-4 py-3 bg-white hover:bg-gray-50 transition-colors">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <p className="font-medium text-gray-900 text-sm">{criterion.criteria_title}</p>
                                {criterion.comment && (
                                  <div className="mt-2 flex items-start gap-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                                    <MessageSquare className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
                                    <span>{criterion.comment}</span>
                                  </div>
                                )}
                              </div>
                              <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg font-bold text-sm ${
                                criterion.score_value >= 8 ? 'bg-green-100 text-green-700' :
                                criterion.score_value >= 5 ? 'bg-yellow-100 text-yellow-700' :
                                criterion.score_value ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-400'
                              }`}>
                                {criterion.score_value ?? '—'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* C-Level оценки */}
              {detailType === 'all' && detailsData.c_level_evaluations?.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                    <Award className="w-5 h-5 text-amber-600" />
                    Оценки C-Level
                  </h3>
                  {detailsData.c_level_evaluations.map((evaluation, idx) => (
                    <React.Fragment key={`clevel-eval-${evaluation.evaluation_id || idx}`}>
                      {renderEvaluationBlock(
                        evaluation,
                        `Оценка от ${evaluation.evaluator_name}`,
                        'bg-amber-50',
                        'border-amber-200'
                      )}
                    </React.Fragment>
                  ))}
                </div>
              )}

              {/* Нет данных для конкретного типа: от подчинённых */}
              {detailType === 'from_subordinates' && (!detailsData.subordinate_evaluations || detailsData.subordinate_evaluations.length === 0) && (
                <div className="text-center py-12 text-gray-500">
                  <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <UserMinus className="w-8 h-8 text-orange-300" />
                  </div>
                  <p className="font-medium">Нет оценок от подчинённых</p>
                  <p className="text-sm mt-1">Подчинённые ещё не оценили этого руководителя</p>
                </div>
              )}

              {/* Нет данных для конкретного типа: от руководителя */}
              {detailType === 'received_from_manager' && 
               (!detailsData.manager_evaluations || detailsData.manager_evaluations.length === 0) && 
               (!detailsData.c_level_evaluations || detailsData.c_level_evaluations.length === 0) && (
                <div className="text-center py-12 text-gray-500">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <UserCheck className="w-8 h-8 text-green-300" />
                  </div>
                  <p className="font-medium">Нет оценок от руководителя</p>
                  <p className="text-sm mt-1">Руководитель ещё не оценил этого сотрудника</p>
                </div>
              )}

              {/* Нет данных вообще (для типа all) */}
              {detailType === 'all' &&
               !detailsData.self_evaluation && 
               !detailsData.manager_evaluations?.length && 
               !detailsData.evaluation_to_manager &&
               !detailsData.evaluations_to_subordinates?.length &&
               !detailsData.subordinate_evaluations?.length &&
               !detailsData.c_level_evaluations?.length && (
                <div className="text-center py-12 text-gray-500">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Star className="w-8 h-8 text-gray-300" />
                  </div>
                  <p className="font-medium">Нет данных для отображения</p>
                  <p className="text-sm mt-1">Оценки ещё не были сделаны</p>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12 text-gray-500">
              Не удалось загрузить детали
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 shrink-0">
          <button
            onClick={onClose}
            className="w-full py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

export default AllEvaluationsDetailsModal;
