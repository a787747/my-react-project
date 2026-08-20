/**
 * EvaluationModal - Модальное окно проведения оценки сотрудника
 * 
 * Назначение: Форма для оценки сотрудника менеджером по критериям
 * Используется в: Dashboard
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - оцениваемый сотрудник
 * - criteria: array - список критериев
 * - isEditMode: boolean - режим редактирования существующей оценки
 * - evaluatedDetails: object - данные об уже проведенных оценках
 * - user: object - текущий пользователь (оценщик)
 * - onClose: function - закрыть окно
 * - onSuccess: function - колбэк успешного сохранения
 */

import React, { useState, useEffect, useMemo } from 'react';
import apiClient from '../api/client';
import { X, Loader2, CheckCircle, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';
import { calculateFinalScore, filterCriteriaByEmployee, getScoreZone } from '../utils/evaluationUtils';
import { groupCriteria } from '../utils/matrixUtils';
import { USER_ROLES, ADMIN_ROLES, getWorkCategoryLabel } from '../config/constants';
import {
  clearEvaluationDraft,
  getEvaluationDraftKey,
  loadEvaluationDraft,
  saveEvaluationDraft
} from '../utils/evaluationDrafts';
import CriterionSlider from './CriterionSlider';
import logger from '../utils/logger';

const EvaluationModal = ({ 
  isOpen, 
  employee, 
  criteria, 
  isEditMode, 
  evaluatedDetails,
  user,
  onClose,
  onSuccess 
}) => {
  // Состояния формы
  const [evaluations, setEvaluations] = useState({});
  const [comments, setComments] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [loadingExisting, setLoadingExisting] = useState(false);
  
  // Самооценка сотрудника для сравнения
  const [employeeSelfReview, setEmployeeSelfReview] = useState(null);
  const [employeeSelfReviewStatus, setEmployeeSelfReviewStatus] = useState('idle');
  const [loadingSelfReview, setLoadingSelfReview] = useState(false);

  // Состояние свернутости групп
  const [collapsedGroups, setCollapsedGroups] = useState({});
  
  // Состояние окна подтверждения
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [draftRestored, setDraftRestored] = useState(false);

  const draftStorageKey = useMemo(
    () => getEvaluationDraftKey(user?.id, employee?.id),
    [user?.id, employee?.id]
  );

  // Фильтруем критерии для данного сотрудника (мемоизация для оптимизации)
  const filteredCriteria = useMemo(
    () => filterCriteriaByEmployee(criteria, employee, user?.role),
    [criteria, employee, user?.role]
  );
  
  // Группируем критерии (мемоизация для оптимизации)
  const groupedCriteria = useMemo(
    () => groupCriteria(filteredCriteria),
    [filteredCriteria]
  );

  // Конфигурация групп (нужно определить раньше для расчета видимых критериев)
  const groupConfigData = useMemo(() => [
    { key: 'self', condition: true },
    { key: 'general', condition: true },
    { key: 'project', condition: employee?.is_project_participant },
    { key: 'management', condition: employee?.has_subordinates },
    { key: 'c_level', condition: ADMIN_ROLES.includes(user?.role) }
  ], [employee?.is_project_participant, employee?.has_subordinates, user?.role]);

  // Получаем список критериев, которые РЕАЛЬНО отображаются на экране
  const visibleCriteria = useMemo(() => {
    let result = [];
    groupConfigData.forEach(group => {
      const criteriaList = groupedCriteria[group.key] || [];
      // Проверяем условие отображения группы
      if (!group.condition) return;
      if (criteriaList.length === 0) return;
      result = [...result, ...criteriaList];
    });
    return result;
  }, [groupedCriteria, groupConfigData]);

  // Проверяем, все ли ОТОБРАЖАЕМЫЕ критерии оценены
  const evaluatedCount = useMemo(() => {
    return visibleCriteria.filter(c => evaluations[c.id] !== undefined && evaluations[c.id] !== null).length;
  }, [visibleCriteria, evaluations]);
  
  const allCriteriaEvaluated = evaluatedCount === visibleCriteria.length && visibleCriteria.length > 0;
  
  const unevaluatedCriteria = useMemo(() => {
    return visibleCriteria.filter(c => evaluations[c.id] === undefined || evaluations[c.id] === null);
  }, [visibleCriteria, evaluations]);

  // Конфигурация групп для отображения
  const groupConfig = useMemo(() => [
    { 
      key: 'self', 
      title: '⭐ Основные критерии', 
      subtitle: 'Самооценка + Оценка руководителя',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200'
    },
    { 
      key: 'general', 
      title: '📋 Общие критерии', 
      subtitle: 'Оценка руководителя',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200'
    },
    { 
      key: 'project', 
      title: '🎯 Проектные критерии', 
      subtitle: 'Для участников проектов',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      condition: employee?.is_project_participant
    },
    { 
      key: 'management', 
      title: '📊 Критерии управления', 
      subtitle: 'Для руководителей',
      bgColor: 'bg-teal-50',
      borderColor: 'border-teal-200',
      condition: employee?.has_subordinates
    },
    { 
      key: 'c_level', 
      title: '👑 C-level критерии', 
      subtitle: 'Только для руководства',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      condition: ADMIN_ROLES.includes(user?.role)
    }
  ], [employee?.is_project_participant, employee?.has_subordinates, user?.role]);

  // Загрузка данных при открытии модалки
  useEffect(() => {
    if (!isOpen || !employee) return;

    // Создаём AbortController для отмены запросов при закрытии
    const abortController = new AbortController();
    const signal = abortController.signal;

    const savedDraft = !isEditMode
      ? loadEvaluationDraft(draftStorageKey)
      : null;

    // Existing evaluations always come from the server. New evaluations can
    // resume a local draft after a token-expiry redirect or page refresh.
    setEvaluations(savedDraft?.evaluations || {});
    setComments(savedDraft?.comments || {});
    setDraftRestored(Boolean(savedDraft));
    setSubmitResult(null);
    setLoadingSelfReview(true);
    setLoadingExisting(isEditMode);
    setEmployeeSelfReview(null);
    setEmployeeSelfReviewStatus('loading');
    setCollapsedGroups({});
    setShowConfirmation(false);

    const loadData = async () => {
      // 1. Загружаем самооценку сотрудника
      if (API_ENDPOINTS.CHECK_SELF_REVIEWS) {
        try {
          const response = await apiClient.get(API_ENDPOINTS.CHECK_SELF_REVIEWS, {
            params: { user_id: employee.id },
            signal
          });
          if (!signal.aborted && response.data?.has_self_review) {
            setEmployeeSelfReview(response.data);
            setEmployeeSelfReviewStatus('submitted');
          } else if (!signal.aborted) {
            setEmployeeSelfReviewStatus('missing');
          }
        } catch (error) {
          if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
            logger.error('Ошибка загрузки самооценки:', error);
            setEmployeeSelfReviewStatus('unavailable');
          }
        } finally {
          if (!signal.aborted) setLoadingSelfReview(false);
        }
      } else {
        setLoadingSelfReview(false);
        setEmployeeSelfReviewStatus('unavailable');
      }

      // 2. Загружаем существующую оценку (в режиме редактирования)
      if (isEditMode) {
        try {
          const evaluationDetail = evaluatedDetails[employee.id];
          if (evaluationDetail?.latest_evaluation_id) {
            const response = await apiClient.get(API_ENDPOINTS.EVALUATION_DETAILS, {
              params: { evaluation_id: evaluationDetail.latest_evaluation_id },
              signal
            });

            if (!signal.aborted) {
              const details = response.data;
              const existingScores = {};
              const existingComments = {};
              if (Array.isArray(details.scores)) {
                details.scores.forEach(score => {
                  existingScores[score.criteria_id] = score.score_value;
                  if (score.comment) {
                    existingComments[score.criteria_id] = score.comment;
                  }
                });
              }
              setEvaluations(existingScores);
              setComments(existingComments);
            }
          }
        } catch (error) {
          if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
            logger.error('Ошибка загрузки оценки:', error);
          }
        } finally {
          if (!signal.aborted) setLoadingExisting(false);
        }
      } else {
        setLoadingExisting(false);
      }
    };

    loadData();

    // Cleanup: отменяем запросы при размонтировании или изменении зависимостей
    return () => {
      abortController.abort();
    };
  }, [
    isOpen,
    employee,
    isEditMode,
    evaluatedDetails,
    user?.role,
    draftStorageKey
  ]);

  // Обработчик изменения оценки
  const handleSliderChange = (criterionId, value) => {
    setEvaluations(prev => {
      const nextEvaluations = {
        ...prev,
        [criterionId]: parseInt(value)
      };
      if (!isEditMode) {
        saveEvaluationDraft(draftStorageKey, nextEvaluations, comments);
      }
      return nextEvaluations;
    });
  };

  // Обработчик изменения комментария
  const handleCommentChange = (criterionId, comment) => {
    setComments(prev => {
      const nextComments = {
        ...prev,
        [criterionId]: comment
      };
      if (!isEditMode) {
        saveEvaluationDraft(draftStorageKey, evaluations, nextComments);
      }
      return nextComments;
    });
  };

  // Переключение свернутости группы
  const toggleGroup = (groupKey) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [groupKey]: !prev[groupKey]
    }));
  };

  // Получение комментария сотрудника для критерия
  const getSelfComment = (criterion) => {
    const comments = employeeSelfReview?.comments || {};
    return comments[criterion.id]
      || comments[String(criterion.id)]
      || comments[criterion.title]
      || null;
  };

  // Показ окна подтверждения
  const handleSubmitClick = () => {
    if (!allCriteriaEvaluated) return;
    setShowConfirmation(true);
  };

  // Отмена подтверждения
  const handleCancelConfirm = () => {
    setShowConfirmation(false);
  };

  // Отправка оценки после подтверждения
  const handleConfirmSubmit = async () => {
    setShowConfirmation(false);
    await handleSubmit();
  };

  // Отправка оценки
  const handleSubmit = async () => {
    if (!employee?.id) {
      logger.error('Ошибка: сотрудник не выбран');
      return;
    }

    if (!allCriteriaEvaluated) {
      logger.error('Ошибка: не все критерии оценены');
      return;
    }

    try {
      setSubmitting(true);
      // Простое среднее арифметическое (без весов и коэффициентов)
      const finalScore = calculateFinalScore(evaluations, 1.0);
      
      const payload = {
        evaluator_id: user.id,
        subject_id: employee.id,
        final_score: parseFloat(finalScore),
        grades: evaluations,
        comments: comments
      };

      if (isEditMode && evaluatedDetails[employee.id]?.latest_evaluation_id) {
        // Обновление существующей оценки
        await apiClient.post(API_ENDPOINTS.UPDATE_EVALUATION, {
          ...payload,
          evaluation_id: evaluatedDetails[employee.id].latest_evaluation_id
        });
        setSubmitResult({ success: true, message: 'Оценка обновлена!', score: finalScore });
      } else {
        // Создание новой оценки
        await apiClient.post(API_ENDPOINTS.SUBMIT_EVALUATION, payload);
        setSubmitResult({ success: true, message: 'Оценка сохранена!', score: finalScore });
      }
      clearEvaluationDraft(draftStorageKey);
      setDraftRestored(false);
    } catch (error) {
      logger.error('Ошибка сохранения:', error);
      setSubmitResult({ success: false, message: 'Ошибка при сохранении оценки' });
    } finally {
      setSubmitting(false);
    }
  };

  // Закрытие с обновлением данных
  const handleFinalClose = () => {
    if (submitResult?.success) {
      onSuccess(); // Обновляем данные на дашборде
    }
    onClose();
  };

  // Рендер группы критериев
  const renderCriteriaGroup = (group) => {
    const criteriaList = groupedCriteria[group.key] || [];
    
    // Проверяем условие отображения группы (condition теперь boolean)
    if (group.condition !== undefined && !group.condition) return null;
    if (criteriaList.length === 0) return null;

    const isCollapsed = collapsedGroups[group.key];

    return (
      <div key={group.key} className={`rounded-xl border-2 ${group.borderColor} overflow-hidden mb-4`}>
        {/* Заголовок группы */}
        <button
          type="button"
          onClick={() => toggleGroup(group.key)}
          className={`w-full ${group.bgColor} px-4 py-3 flex items-center justify-between hover:opacity-90 transition-opacity`}
        >
          <div className="text-left">
            <h3 className="font-bold text-gray-900">{group.title}</h3>
            <p className="text-xs text-gray-600">{group.subtitle} • {criteriaList.length} критериев</p>
          </div>
          {isCollapsed ? (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          )}
        </button>

        {/* Критерии группы */}
        {!isCollapsed && (
          <div className="p-4 space-y-4 bg-white">
            {criteriaList.map((criterion) => (
              <CriterionSlider
                key={criterion.id}
                criterion={criterion}
                value={evaluations[criterion.id]}
                onChange={handleSliderChange}
                employeeSelfReview={employeeSelfReview}
                selfComment={getSelfComment(criterion)}
                managerComment={comments[criterion.id] || ''}
                onCommentChange={handleCommentChange}
                showCommentField={true}
              />
            ))}
          </div>
        )}
      </div>
    );
  };

  if (!isOpen || !employee) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-6 flex items-start justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold text-2xl backdrop-blur-md">
              {employee.full_name?.charAt(0) || 'U'}
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">{employee.full_name}</h2>
              <p className="text-indigo-100">{employee.job_title}</p>
            </div>
          </div>
          <button onClick={handleFinalClose} className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Info bar */}
        <div className="p-4 bg-indigo-50 border-b border-indigo-100 shrink-0 flex justify-between items-center">
          <p className="text-sm text-indigo-900">
            Категория: <span className="font-medium text-gray-700">{getWorkCategoryLabel(employee.work_category)}</span>
            {employee.is_project_participant && (
              <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                Участник проекта
              </span>
            )}
          </p>
          <div className="flex items-center gap-2">
            {draftRestored && !isEditMode && (
              <span className="text-xs bg-amber-100 text-amber-800 px-3 py-1 rounded-full font-medium border border-amber-200">
                Черновик восстановлен
              </span>
            )}
            {employeeSelfReview && (
              <span className="text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-bold border border-blue-200">
                ⭐ Самооценка: {employeeSelfReview.score}
              </span>
            )}
            {employeeSelfReviewStatus === 'missing' && (
              <span className="text-xs bg-slate-100 text-slate-600 px-3 py-1 rounded-full font-medium border border-slate-200">
                Самооценка ещё не отправлена
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto">
          {loadingExisting || loadingSelfReview ? (
            // Загрузка
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
              <span className="text-gray-500">Загрузка данных...</span>
            </div>
          ) : !submitResult ? (
            // Форма оценки с группировкой
            <>
              {visibleCriteria.length === 0 ? (
                <div className="text-center py-10 text-gray-500">
                  Нет активных критериев для категории "{getWorkCategoryLabel(employee.work_category)}".
                </div>
              ) : (
                <div>
                  {groupConfig.map(group => renderCriteriaGroup(group))}
                </div>
              )}
            </>
          ) : (
            // Результат отправки
            <div className="text-center py-12">
              <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
                submitResult.success ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {submitResult.success ? (
                  <CheckCircle className="w-10 h-10 text-green-600" />
                ) : (
                  <X className="w-10 h-10 text-red-600" />
                )}
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">{submitResult.message}</h3>
              {submitResult.success && (
                <p className="text-gray-600">
                  Итоговый балл: <span className="text-2xl font-bold text-indigo-600">{submitResult.score}</span>
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 shrink-0">
          {!submitResult ? (
            <>
              {/* Прогресс оценивания */}
              {visibleCriteria.length > 0 && (
                <div className="mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">
                      Оценено: {evaluatedCount} из {visibleCriteria.length}
                    </span>
                    {!allCriteriaEvaluated && (
                      <span className="text-xs text-amber-600 font-medium">
                        Осталось: {unevaluatedCriteria.length}
                      </span>
                    )}
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${
                        allCriteriaEvaluated ? 'bg-green-500' : 'bg-indigo-500'
                      }`}
                      style={{ width: `${visibleCriteria.length > 0 ? (evaluatedCount / visibleCriteria.length) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              )}
              
              <div className="flex gap-3">
                <button
                  onClick={handleFinalClose}
                  className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-white hover:shadow-sm transition-all"
                >
                  Отмена
                </button>
                <button
                  onClick={handleSubmitClick}
                  disabled={submitting || !allCriteriaEvaluated}
                  className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 ${
                    allCriteriaEvaluated
                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Сохранение...
                    </>
                  ) : allCriteriaEvaluated ? (
                    isEditMode ? 'Обновить оценку' : 'Сохранить оценку'
                  ) : (
                    `Оцените все критерии (${unevaluatedCriteria.length})`
                  )}
                </button>
              </div>
            </>
          ) : (
            <button
              onClick={handleFinalClose}
              className="w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors shadow-md"
            >
              Закрыть
            </button>
          )}
        </div>

        {/* Модальное окно подтверждения */}
        {showConfirmation && (
          <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4 z-[60]">
            <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col">
              {/* Header подтверждения */}
              <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">Подтверждение оценки</h3>
                    <p className="text-sm text-gray-500">Проверьте оценки для {employee?.full_name}</p>
                  </div>
                </div>
                <button 
                  onClick={handleCancelConfirm}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              {/* Список оценок */}
              <div className="p-6 overflow-y-auto flex-1">
                <div className="space-y-3">
                  {visibleCriteria.map((criterion) => {
                    const score = parseInt(evaluations[criterion.id], 10);
                    const zone = getScoreZone(score);
                    return (
                      <div key={criterion.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="text-sm font-medium text-gray-700 flex-1 mr-4 line-clamp-1">
                          {criterion.title}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${zone.text} ${zone.bg}`}>
                            {zone.label}
                          </span>
                          <span className="text-lg font-bold text-indigo-600 w-8 text-center">
                            {score}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Итоговый балл */}
                <div className="mt-6 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-indigo-800">Итоговый балл:</span>
                    <span className="text-2xl font-bold text-indigo-600">
                      {calculateFinalScore(evaluations, 1.0)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Footer подтверждения */}
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex gap-3">
                <button
                  onClick={handleCancelConfirm}
                  className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-white transition-all"
                >
                  Изменить
                </button>
                <button
                  onClick={handleConfirmSubmit}
                  className="flex-1 px-6 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 shadow-md transition-all flex justify-center items-center gap-2"
                >
                  <CheckCircle className="w-5 h-5" />
                  Подтвердить
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EvaluationModal;
