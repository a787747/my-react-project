/**
 * ManagerEvaluation - Страница оценки менеджера подчиненными
 * 
 * Назначение: Позволяет сотрудникам оценить своего непосредственного руководителя
 * по критерию "Качество управления и развитие талантов"
 * 
 * Доступ: Все сотрудники, у которых есть менеджер
 * 
 * Использует хуки:
 * - useManagerEvaluation - загрузка данных и отправка оценки
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  User, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Star,
  Users,
  TrendingUp,
  Send,
  RefreshCw,
  Shield
} from 'lucide-react';
import { useManagerEvaluation } from '../hooks/useManagerEvaluation';
import { useTaskStatus } from '../context/TaskStatusContext';
import { OutOfScopeNotice } from '../components/common';
import CriterionSlider from '../components/CriterionSlider';
import { getScoreZone } from '../utils/evaluationUtils';
import { ADMIN_ROLES } from '../config/constants';
import {
  clearEvaluationDraft,
  getEvaluationDraftKey,
  loadEvaluationDraft,
  saveEvaluationDraft
} from '../utils/evaluationDrafts';

const ManagerEvaluation = ({ user }) => {
  // Контекст статусов задач для обновления сайдбара
  const {
    refreshTaskStatus,
    isOutOfScope,
    loading: loadingTaskStatus
  } = useTaskStatus();
  const {
    manager,
    hasManager,
    hasEvaluated,
    lastScore,
    criteria,
    loading,
    submitting,
    error,
    submitEvaluation,
    refreshData
  } = useManagerEvaluation(user);

  // Состояние формы
  const [evaluations, setEvaluations] = useState({});
  const [comments, setComments] = useState({});
  const [submitResult, setSubmitResult] = useState(null);
  const [draftRestored, setDraftRestored] = useState(false);

  const draftStorageKey = useMemo(
    () => getEvaluationDraftKey(user?.id, manager?.id),
    [user?.id, manager?.id]
  );

  useEffect(() => {
    if (loading || !draftStorageKey) return;

    if (hasEvaluated) {
      clearEvaluationDraft(draftStorageKey);
      setDraftRestored(false);
      return;
    }

    const savedDraft = loadEvaluationDraft(draftStorageKey);
    setEvaluations(savedDraft?.evaluations || {});
    setComments(savedDraft?.comments || {});
    setDraftRestored(Boolean(savedDraft));
  }, [loading, hasEvaluated, draftStorageKey]);

  // Обработчик изменения оценки
  const handleSliderChange = (criterionId, value) => {
    setEvaluations(prev => {
      const nextEvaluations = {
        ...prev,
        [criterionId]: parseInt(value)
      };
      saveEvaluationDraft(draftStorageKey, nextEvaluations, comments);
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
      saveEvaluationDraft(draftStorageKey, evaluations, nextComments);
      return nextComments;
    });
  };

  // Отправка оценки
  const handleSubmit = async () => {
    const result = await submitEvaluation(evaluations, comments);
    setSubmitResult(result);
    
    if (result.success) {
      // Обновляем статусы задач в сайдбаре
      refreshTaskStatus();
      
      // Сбрасываем форму
      clearEvaluationDraft(draftStorageKey);
      setDraftRestored(false);
      setEvaluations({});
      setComments({});
    }
  };

  // Проверка заполненности формы
  const isFormValid = criteria.length > 0 && 
    criteria.every(c => evaluations[c.id] !== undefined);

  // Состояние загрузки
  if (loading || loadingTaskStatus) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Загрузка данных...</p>
        </div>
      </div>
    );
  }

  if (isOutOfScope) {
    return <OutOfScopeNotice />;
  }

  // Если у пользователя нет менеджера
  if (!hasManager || !manager) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Users className="w-10 h-10 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              Руководитель не назначен
            </h2>
            <p className="text-gray-600 mb-6">
              В системе не указан ваш непосредственный руководитель. 
              Обратитесь к HR-отделу для уточнения информации.
            </p>
            <button
              onClick={refreshData}
              className="inline-flex items-center gap-2 px-4 py-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            >
              <RefreshCw className="w-5 h-5" />
              Обновить данные
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Проверка, является ли менеджер C-level или Admin (не оцениваются подчинёнными)
  const isManagerCLevel = ADMIN_ROLES.includes(manager?.role);

  // Получаем зону оценки для отображения
  const scoreZone = lastScore ? getScoreZone(parseFloat(lastScore)) : null;

  // Если менеджер C-level, показываем сообщение вместо формы
  if (hasManager && manager && isManagerCLevel) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          {/* Заголовок */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Оценка руководителя
            </h1>
            <p className="text-gray-600">
              Оцените качество управления вашего непосредственного руководителя
            </p>
          </div>

          {/* Сообщение о C-level менеджере */}
          <div className="bg-white rounded-xl shadow-sm border border-amber-200 p-12 text-center">
            <div className="w-20 h-20 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Shield className="w-10 h-10 text-amber-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Оценка недоступна
            </h2>
            <p className="text-gray-700 text-lg mb-2">
              Ваш непосредственный руководитель является менеджером уровня C-level.
            </p>
            <p className="text-gray-600 mb-6">
              C-level менеджеры не оцениваются подчиненными в рамках данной программы оценки.
            </p>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 max-w-2xl mx-auto">
              <p className="text-sm text-amber-800">
                Если у вас есть вопросы или предложения, пожалуйста, обратитесь к HR-отделу или 
                администратору системы.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        
        {/* Заголовок */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Оценка руководителя
          </h1>
          <p className="text-gray-600">
            Оцените качество управления вашего непосредственного руководителя
          </p>
        </div>

        {/* Карточка менеджера */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-start gap-6">
            {/* Аватар */}
            <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-3xl shadow-lg">
              {manager.full_name?.charAt(0) || 'M'}
            </div>
            
            {/* Информация */}
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-gray-900 mb-1">
                {manager.full_name}
              </h2>
              <p className="text-gray-600 mb-3">{manager.job_title}</p>
              
              <div className="flex flex-wrap gap-3">
                {manager.department_name && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                    <Users className="w-4 h-4" />
                    {manager.department_name}
                  </span>
                )}
                {manager.grade_code && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                    <TrendingUp className="w-4 h-4" />
                    Грейд: {manager.grade_code}
                  </span>
                )}
                {manager.has_subordinates && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                    <User className="w-4 h-4" />
                    Руководитель команды
                  </span>
                )}
              </div>
            </div>

            {/* Статус оценки */}
            <div className="text-right">
              {hasEvaluated ? (
                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl ${scoreZone?.bg || 'bg-green-100'} ${scoreZone?.text || 'text-green-700'}`}>
                  <CheckCircle className="w-5 h-5" />
                  <div>
                    <div className="font-medium">Оценено</div>
                    {lastScore && (
                      <div className="text-lg font-bold">{lastScore}</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-700 rounded-xl">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-medium">Ожидает оценки</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Ошибка */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Результат отправки */}
        {submitResult?.success && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6 text-center">
            <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
            <h3 className="text-xl font-bold text-green-900 mb-2">
              Оценка успешно сохранена!
            </h3>
            <p className="text-green-700">
              Итоговый балл: <span className="font-bold text-2xl">{submitResult.score}</span>
            </p>
          </div>
        )}

        {/* Форма оценки */}
        {(!hasEvaluated || submitResult?.success === false) && criteria.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            {/* Заголовок формы */}
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-6">
              <div className="flex items-center gap-3">
                <Star className="w-8 h-8" />
                <div>
                  <h3 className="text-xl font-bold">Критерии оценки</h3>
                  <p className="text-indigo-100 text-sm">
                    Оцените работу руководителя по каждому критерию
                  </p>
                  {draftRestored && (
                    <span className="inline-block mt-2 text-xs bg-amber-100 text-amber-800 px-3 py-1 rounded-full font-medium border border-amber-200">
                      Черновик восстановлен
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Критерии */}
            <div className="p-6 space-y-6">
              {criteria.map((criterion) => (
                <CriterionSlider
                  key={criterion.id}
                  criterion={criterion}
                  value={evaluations[criterion.id]}
                  onChange={handleSliderChange}
                  managerComment={comments[criterion.id] || ''}
                  onCommentChange={handleCommentChange}
                  showCommentField={true}
                />
              ))}
            </div>

            {/* Кнопка отправки */}
            <div className="p-6 border-t border-gray-200 bg-gray-50">
              <button
                onClick={handleSubmit}
                disabled={!isFormValid || submitting}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors shadow-lg shadow-indigo-200"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Сохранение...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Отправить оценку
                  </>
                )}
              </button>
              
              {!isFormValid && (
                <p className="text-center text-gray-500 text-sm mt-3">
                  Пожалуйста, оцените все критерии перед отправкой
                </p>
              )}
            </div>
          </div>
        )}

        {/* Если уже оценено */}
        {hasEvaluated && submitResult?.success !== false && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Вы уже оценили своего руководителя
            </h3>
            <p className="text-gray-600">
              Ваша оценка была успешно сохранена. 
              {lastScore && ` Текущий балл: ${lastScore}`}
            </p>
          </div>
        )}

        {/* Если нет критериев */}
        {criteria.length === 0 && !hasEvaluated && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
            <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Критерии оценки не настроены
            </h3>
            <p className="text-gray-600">
              Обратитесь к администратору для настройки критериев оценки руководителей.
            </p>
          </div>
        )}

      </div>
    </div>
  );
};

export default ManagerEvaluation;
