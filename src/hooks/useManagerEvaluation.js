/**
 * useManagerEvaluation - Хук для работы с оценкой менеджера подчиненными
 * 
 * Назначение: Загрузка информации о менеджере пользователя, 
 *             загрузка критериев для оценки менеджера,
 *             отправка оценки менеджера подчиненным
 * Используется в: ManagerEvaluation
 * 
 * Параметры:
 * - user: object - текущий пользователь
 * 
 * Возвращает:
 * - manager: object | null - информация о менеджере
 * - hasManager: boolean - есть ли менеджер у пользователя
 * - hasEvaluated: boolean - оценивал ли пользователь менеджера
 * - criteria: array - критерии для оценки менеджера
 * - loading: boolean - статус загрузки
 * - submitting: boolean - статус отправки
 * - error: string | null - ошибка
 * - submitEvaluation: function - отправка оценки
 * - refreshData: function - обновление данных
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useManagerEvaluation = (user) => {
  const [manager, setManager] = useState(null);
  const [hasManager, setHasManager] = useState(false);
  const [hasEvaluated, setHasEvaluated] = useState(false);
  const [lastScore, setLastScore] = useState(null);
  const [previousScores, setPreviousScores] = useState({}); // Предыдущие оценки по критериям
  const [previousComments, setPreviousComments] = useState({}); // Предыдущие комментарии
  const [criteria, setCriteria] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Загрузка данных о менеджере
  const fetchManagerData = useCallback(async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Получаем информацию о менеджере
      const managerResponse = await apiClient.get(API_ENDPOINTS.GET_MY_MANAGER, {
        params: { user_id: user.id }
      });

      const managerData = managerResponse.data;
      
      if (managerData?.has_manager && managerData?.manager) {
        setManager(managerData.manager);
        setHasManager(true);
        setHasEvaluated(managerData.manager.has_evaluated_manager || false);
        setLastScore(managerData.manager.last_evaluation_score || null);
        
        // Преобразуем предыдущие оценки в удобный формат
        const scores = {};
        const comments = {};
        const prevScores = managerData.manager.previous_scores || [];
        
        // DEBUG: логируем данные для отладки
        console.log('[useManagerEvaluation] previous_scores from API:', prevScores);
        
        prevScores.forEach(item => {
          if (item.criteria_id) {
            scores[item.criteria_id] = item.score_value;
            if (item.comment) {
              comments[item.criteria_id] = item.comment;
            }
          }
        });
        
        console.log('[useManagerEvaluation] Parsed scores:', scores);
        console.log('[useManagerEvaluation] Parsed comments:', comments);
        
        setPreviousScores(scores);
        setPreviousComments(comments);
      } else {
        setManager(null);
        setHasManager(false);
        setHasEvaluated(false);
        setLastScore(null);
        setPreviousScores({});
        setPreviousComments({});
      }

      // Получаем критерии для оценки менеджера
      const criteriaResponse = await apiClient.get(API_ENDPOINTS.CRITERIA);
      const allCriteria = criteriaResponse.data?.data || criteriaResponse.data || [];
      
      // Фильтруем только критерий для оценки менеджеров
      const managementCriteria = allCriteria.filter(c => {
        const isCLevelOnly = c.c_level_only === true || c.c_level_only === 'true';
        return c.is_active
          && c.target_audience === 'managers_only'
          && !isCLevelOnly;
      });
      
      setCriteria(managementCriteria);

    } catch (err) {
      logger.error('Ошибка загрузки данных о менеджере:', err);
      setError('Не удалось загрузить данные о менеджере');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  // Отправка оценки менеджера
  const submitEvaluation = useCallback(async (evaluations, comments = {}) => {
    if (!manager?.id || !user?.id) {
      return { success: false, error: 'Нет данных для оценки' };
    }

    try {
      setSubmitting(true);
      setError(null);

      // Рассчитываем средний балл
      const scores = Object.values(evaluations);
      const averageScore = scores.length > 0 
        ? scores.reduce((sum, score) => sum + score, 0) / scores.length 
        : 0;

      const payload = {
        evaluator_id: user.id,
        subject_id: manager.id,
        final_score: parseFloat(averageScore.toFixed(2)),
        grades: evaluations,
        comments: comments,
        evaluation_source: 'subordinate'  // Важно: указываем источник оценки
      };

      await apiClient.post(API_ENDPOINTS.SUBMIT_EVALUATION, payload);

      // Обновляем состояние
      setHasEvaluated(true);
      setLastScore(averageScore.toFixed(2));

      return { success: true, score: averageScore.toFixed(2) };

    } catch (err) {
      logger.error('Ошибка отправки оценки менеджера:', err);
      const errorMessage = err.response?.data?.message || 'Ошибка при сохранении оценки';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setSubmitting(false);
    }
  }, [manager?.id, user?.id]);

  // Загружаем данные при монтировании
  useEffect(() => {
    fetchManagerData();
  }, [fetchManagerData]);

  return {
    manager,
    hasManager,
    hasEvaluated,
    lastScore,
    previousScores,
    previousComments,
    criteria,
    loading,
    submitting,
    error,
    submitEvaluation,
    refreshData: fetchManagerData
  };
};

export default useManagerEvaluation;

