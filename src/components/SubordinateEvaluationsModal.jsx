/**
 * SubordinateEvaluationsModal - Модальное окно просмотра оценок от подчинённых
 * 
 * Назначение: Отображение всех оценок, которые руководитель получил от своих подчинённых
 * Используется в: TeamView
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - сотрудник (руководитель)
 * - currentUser: object - текущий пользователь (для проверки прав)
 * - onClose: function - закрыть окно
 * 
 * Логика отображения:
 * - Обычные менеджеры видят только имена оценивших подчинённых
 * - Admin и C-level видят полные оценки с баллами
 */

import React, { useState, useEffect } from 'react';
import { X, User, Loader2, AlertCircle, MessageSquare, Star, Users, CheckCircle, Lock } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { getScoreZone } from '../utils/evaluationUtils';
import { ADMIN_ROLES } from '../config/constants';
import logger from '../utils/logger';
import { isForbiddenError } from '../utils/errorHandler';

const SubordinateEvaluationsModal = ({ isOpen, employee, currentUser, onClose }) => {
  // Проверяем, может ли текущий пользователь видеть детали оценок
  const canViewScores = currentUser && ADMIN_ROLES.includes(currentUser.role);
  const [loading, setLoading] = useState(true);
  const [evaluationData, setEvaluationData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !employee) return;

    const abortController = new AbortController();
    const signal = abortController.signal;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      setEvaluationData(null);

      try {
        // Загружаем оценки, которые сотрудник получил от подчинённых
        const response = await apiClient.get(API_ENDPOINTS.ADMIN_EVALUATION_DETAILS_BY_USER, {
          params: { 
            user_id: employee.id,
            detail_type: 'from_subordinates'
          },
          signal
        });

        if (!signal.aborted) {
          const data = response.data?.data;
          // API возвращает subordinate_evaluations для оценок от подчинённых
          const hasSubordinateEvaluations = data?.subordinate_evaluations?.length > 0;
          
          if (data && hasSubordinateEvaluations) {
            setEvaluationData(data);
          } else {
            setError('Нет оценок от подчинённых');
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
          logger.error('Ошибка загрузки оценок от подчинённых:', err);
          setError(isForbiddenError(err) || err.response?.status === 403
            ? 'Детали оценки доступны только администратору и C-level'
            : 'Не удалось загрузить данные оценок');
        }
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    };

    loadData();

    return () => {
      abortController.abort();
    };
  }, [isOpen, employee]);

  if (!isOpen || !employee) return null;

  // Форматирование даты
  const formatDate = (dateString) => {
    try {
      if (!dateString) return 'Дата неизвестна';
      return new Date(dateString).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const displayName = employee.full_name || 'Неизвестный сотрудник';
  const initial = displayName.charAt(0).toUpperCase();

  // Рендер оценки по критерию
  const renderCriterion = (criterion, idx) => {
    const numericScore = parseFloat(criterion.score_value);
    const zone = getScoreZone(numericScore, criterion);
    
    return (
      <div 
        key={criterion.criteria_id || idx}
        className={`p-4 rounded-xl border-2 ${zone?.border || 'border-gray-200'} ${zone?.bg || 'bg-gray-50'}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0 pr-4">
            <h5 className="font-medium text-gray-900">
              {criterion.criteria_title || `Критерий ${criterion.criteria_id}`}
            </h5>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-bold ${zone?.text || 'text-gray-700'}`}>
              {numericScore ? numericScore.toFixed(1) : '-'}
            </span>
            <span className="text-sm text-gray-400">/10</span>
          </div>
        </div>
        
        {/* Комментарий к оценке */}
        {criterion.comment && (
          <div className="mt-3 pt-3 border-t border-gray-200 border-opacity-50">
            <div className="flex items-start gap-2">
              <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-gray-600 italic leading-relaxed whitespace-pre-wrap">
                "{criterion.comment}"
              </p>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white p-6 flex items-start justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold text-2xl backdrop-blur-md">
              {initial}
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">{displayName}</h2>
              <p className="text-purple-100">{employee.job_title || 'Должность не указана'}</p>
              <p className="text-purple-200 text-sm mt-1">
                <Users className="w-3 h-3 inline mr-1" />
                Оценки от подчинённых
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
            aria-label="Закрыть"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-10 h-10 text-purple-600 animate-spin" />
              <span className="text-gray-500">Загрузка оценок от подчинённых...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{error}</h3>
              <p className="text-gray-500">Подчинённые ещё не провели оценку этого руководителя</p>
            </div>
          ) : evaluationData ? (
            <div className="space-y-6">
              {/* Информационное сообщение для обычных менеджеров */}
              {!canViewScores && (
                <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                  <Lock className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Вы видите список сотрудников, которые провели оценку.</p>
                    <p className="text-amber-600 mt-1">Детальные баллы доступны только руководству.</p>
                  </div>
                </div>
              )}

              {/* Отображаем оценки от подчинённых */}
              {evaluationData.subordinate_evaluations?.map((evaluation, evalIndex) => (
                <div key={evaluation.evaluation_id || evalIndex} className="space-y-4">
                  {/* Информация об оценке */}
                  <div className="flex items-center justify-between p-4 bg-purple-50 border border-purple-200 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-200 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-purple-700" />
                      </div>
                      <div>
                        <p className="text-sm text-purple-700 font-medium">
                          {evaluation.evaluator_name || 'Подчинённый'}
                        </p>
                        <p className="text-xs text-purple-500 mt-0.5">
                          {evaluation.updated_at && formatDate(evaluation.updated_at)}
                        </p>
                      </div>
                    </div>
                    {/* Показываем балл только для admin/c_level */}
                    {canViewScores && evaluation.calculated_score ? (
                      <div className="text-3xl font-bold text-purple-700">
                        {parseFloat(evaluation.calculated_score).toFixed(1)}
                      </div>
                    ) : (
                      <CheckCircle className="w-6 h-6 text-green-500" />
                    )}
                  </div>

                  {/* Оценки по критериям - только для admin/c_level */}
                  {canViewScores && evaluation.criteria && evaluation.criteria.length > 0 && (
                    <div className="space-y-3">
                      {evaluation.criteria.map((criterion, idx) => renderCriterion(criterion, idx))}
                    </div>
                  )}
                </div>
              ))}

              {/* Итого */}
              <div className="flex items-center justify-between p-4 bg-indigo-50 border border-indigo-200 rounded-xl">
                <div className="flex items-center gap-3">
                  <Star className="w-6 h-6 text-indigo-600 fill-current" />
                  <div>
                    <p className="text-sm text-indigo-700 font-medium">Всего оценок от подчинённых</p>
                  </div>
                </div>
                <div className="text-2xl font-bold text-indigo-700">
                  {evaluationData.subordinate_evaluations?.length || 0}
                </div>
              </div>

              {/* Если нет детальных оценок */}
              {(!evaluationData.subordinate_evaluations?.length) && (
                <div className="text-center py-6 text-gray-500">
                  <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p>Оценки от подчинённых недоступны</p>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 shrink-0">
          <button
            onClick={onClose}
            className="w-full px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-xl font-medium transition-colors shadow-md"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubordinateEvaluationsModal;

