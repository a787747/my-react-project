/**
 * ManagerEvaluationDetailsModal - Модальное окно просмотра оценок от менеджера
 * 
 * Назначение: Отображение всех оценок, которые сотрудник получил от своего руководителя
 * Используется в: TeamView
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - сотрудник
 * - onClose: function - закрыть окно
 */

import React, { useState, useEffect } from 'react';
import { X, User, Loader2, AlertCircle, TrendingUp, MessageSquare, Star, Crown } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { getScoreZone } from '../utils/evaluationUtils';
import logger from '../utils/logger';
import { isForbiddenError } from '../utils/errorHandler';

const ManagerEvaluationDetailsModal = ({ isOpen, employee, onClose }) => {
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
        // Загружаем оценки, которые сотрудник получил от менеджера
        const response = await apiClient.get(API_ENDPOINTS.ADMIN_EVALUATION_DETAILS_BY_USER, {
          params: { 
            user_id: employee.id,
            detail_type: 'received_from_manager'
          },
          signal
        });

        if (!signal.aborted) {
          const data = response.data?.data;
          // API возвращает manager_evaluations и c_level_evaluations для оценок от руководителей
          const hasManagerEvaluations = data?.manager_evaluations?.length > 0;
          const hasCLevelEvaluations = data?.c_level_evaluations?.length > 0;
          
          if (data && (hasManagerEvaluations || hasCLevelEvaluations)) {
            setEvaluationData(data);
          } else {
            setError('У сотрудника нет оценок от руководителя');
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
          logger.error('Ошибка загрузки оценок менеджера:', err);
          setError(isForbiddenError(err) || err.response?.status === 403
            ? 'Детали оценки доступны только администратору и C-level'
            : 'Не удалось загрузить данные оценки');
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

  // Группировка оценок по категориям
  const groupScores = (scores) => {
    const groups = {
      self: [],      // Основные критерии (для самооценки)
      general: [],   // Общие критерии
      project: [],   // Проектные критерии
      management: [], // Критерии управления
      c_level: []    // C-level критерии
    };

    (scores || []).forEach(score => {
      if (score.c_level_only) {
        groups.c_level.push(score);
      } else if (score.target_audience === 'project_participants') {
        groups.project.push(score);
      } else if (score.target_audience === 'managers_only') {
        groups.management.push(score);
      } else if (score.for_self || score.selfassesment) {
        groups.self.push(score);
      } else {
        groups.general.push(score);
      }
    });

    return groups;
  };

  // Рендер группы оценок
  const renderScoreGroup = (title, icon, scores) => {
    if (!scores || scores.length === 0) return null;

    return (
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          {icon}
          <h4 className="font-semibold text-gray-800">{title}</h4>
          <span className="text-xs text-gray-500">({scores.length})</span>
        </div>
        <div className="space-y-3">
          {scores.map((score, idx) => {
            const numericScore = parseFloat(score.score || score.manager_score);
            const zone = getScoreZone(numericScore);
            
            return (
              <div 
                key={score.criteria_id || idx}
                className={`p-4 rounded-xl border-2 ${zone?.border || 'border-gray-200'} ${zone?.bg || 'bg-gray-50'}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 pr-4">
                    <h5 className="font-medium text-gray-900">
                      {score.criteria_title || score.criterion_title || `Критерий ${score.criteria_id}`}
                    </h5>
                    {score.criteria_description && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                        {score.criteria_description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-2xl font-bold ${zone?.text || 'text-gray-700'}`}>
                      {numericScore ? numericScore.toFixed(1) : '-'}
                    </span>
                    <span className="text-sm text-gray-400">/10</span>
                  </div>
                </div>
                
                {/* Комментарий к оценке */}
                {score.comment && (
                  <div className="mt-3 pt-3 border-t border-gray-200 border-opacity-50">
                    <div className="flex items-start gap-2">
                      <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-gray-600 italic leading-relaxed whitespace-pre-wrap">
                        "{score.comment}"
                      </p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white p-6 flex items-start justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold text-2xl backdrop-blur-md">
              {initial}
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">{displayName}</h2>
              <p className="text-green-100">{employee.job_title || 'Должность не указана'}</p>
              {employee.manager_name && (
                <p className="text-green-200 text-sm mt-1">
                  <User className="w-3 h-3 inline mr-1" />
                  Руководитель: {employee.manager_name}
                </p>
              )}
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
              <Loader2 className="w-10 h-10 text-green-600 animate-spin" />
              <span className="text-gray-500">Загрузка оценок руководителя...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{error}</h3>
              <p className="text-gray-500">Руководитель ещё не провёл оценку этого сотрудника</p>
            </div>
          ) : evaluationData ? (
            <div className="space-y-6">
              {/* Отображаем оценки от менеджера */}
              {evaluationData.manager_evaluations?.map((evaluation, evalIndex) => (
                <div key={evaluation.evaluation_id || evalIndex} className="space-y-4">
                  {/* Информация об оценке */}
                  <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-xl">
                    <div className="flex items-center gap-3">
                      <TrendingUp className="w-6 h-6 text-green-600" />
                      <div>
                        <p className="text-sm text-green-700 font-medium">Оценка руководителя</p>
                        <p className="text-xs text-green-500 mt-0.5">
                          {evaluation.evaluator_name && `Оценщик: ${evaluation.evaluator_name}`}
                          {evaluation.updated_at && ` • ${formatDate(evaluation.updated_at)}`}
                        </p>
                      </div>
                    </div>
                    {evaluation.calculated_score && (
                      <div className="text-3xl font-bold text-green-700">
                        {parseFloat(evaluation.calculated_score).toFixed(1)}
                      </div>
                    )}
                  </div>

                  {/* Оценки по критериям */}
                  {evaluation.criteria && evaluation.criteria.length > 0 && (() => {
                    // Преобразуем criteria в формат для groupScores
                    const scores = evaluation.criteria.map(c => ({
                      criteria_id: c.criteria_id,
                      criteria_title: c.criteria_title,
                      score: c.score_value,
                      comment: c.comment,
                      for_self: c.selfassesment,
                      for_manager: true,
                      c_level_only: c.c_level_only,
                      target_audience: c.target_audience
                    }));
                    const grouped = groupScores(scores);
                    return (
                      <>
                        {renderScoreGroup(
                          'Основные критерии', 
                          <Star className="w-5 h-5 text-blue-500" />,
                          grouped.self,
                          'blue'
                        )}
                        {renderScoreGroup(
                          'Общие критерии', 
                          <TrendingUp className="w-5 h-5 text-green-500" />,
                          grouped.general,
                          'green'
                        )}
                        {renderScoreGroup(
                          'Проектные критерии', 
                          <User className="w-5 h-5 text-purple-500" />,
                          grouped.project,
                          'purple'
                        )}
                        {renderScoreGroup(
                          'Критерии управления', 
                          <User className="w-5 h-5 text-teal-500" />,
                          grouped.management,
                          'teal'
                        )}
                      </>
                    );
                  })()}
                </div>
              ))}

              {/* Отображаем оценки от C-level */}
              {evaluationData.c_level_evaluations?.map((evaluation, evalIndex) => (
                <div key={evaluation.evaluation_id || `clevel-${evalIndex}`} className="space-y-4">
                  {/* Информация об оценке C-level */}
                  <div className="flex items-center justify-between p-4 bg-orange-50 border border-orange-200 rounded-xl">
                    <div className="flex items-center gap-3">
                      <Crown className="w-6 h-6 text-orange-600" />
                      <div>
                        <p className="text-sm text-orange-700 font-medium">Оценка C-level</p>
                        <p className="text-xs text-orange-500 mt-0.5">
                          {evaluation.evaluator_name && `Оценщик: ${evaluation.evaluator_name}`}
                          {evaluation.updated_at && ` • ${formatDate(evaluation.updated_at)}`}
                        </p>
                      </div>
                    </div>
                    {evaluation.calculated_score && (
                      <div className="text-3xl font-bold text-orange-700">
                        {parseFloat(evaluation.calculated_score).toFixed(1)}
                      </div>
                    )}
                  </div>

                  {/* Оценки по критериям */}
                  {evaluation.criteria && evaluation.criteria.length > 0 && (() => {
                    const scores = evaluation.criteria.map(c => ({
                      criteria_id: c.criteria_id,
                      criteria_title: c.criteria_title,
                      score: c.score_value,
                      comment: c.comment,
                      c_level_only: c.c_level_only,
                      target_audience: c.target_audience
                    }));
                    return renderScoreGroup(
                      'C-level критерии', 
                      <Crown className="w-5 h-5 text-orange-500" />,
                      scores,
                      'orange'
                    );
                  })()}
                </div>
              ))}

              {/* Если нет детальных оценок */}
              {(!evaluationData.manager_evaluations?.length && !evaluationData.c_level_evaluations?.length) && (
                <div className="text-center py-6 text-gray-500">
                  <User className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p>Детальные оценки по критериям недоступны</p>
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

export default ManagerEvaluationDetailsModal;

