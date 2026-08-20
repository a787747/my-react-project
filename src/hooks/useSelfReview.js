/**
 * useSelfReview - Хук для работы с самооценкой
 * 
 * Назначение: Загрузка критериев, проверка статуса и отправка самооценки
 * Используется в: SelfReview
 * 
 * Возвращает:
 * - loading: boolean - статус загрузки
 * - hasReview: boolean - есть ли уже самооценка
 * - reviewData: object - данные существующей самооценки
 * - criteria: array - все доступные критерии
 * - newCriteria: array - новые неоцененные критерии
 * - grades: object - текущие оценки
 * - submitting: boolean - статус отправки
 * - setGrades: function - установить оценки
 * - submitReview: function - отправить самооценку
 * - reload: function - перезагрузить данные
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { calculateWeightedScore } from '../utils/evaluationUtils';
import { useUser } from '../context/UserContext';
import logger from '../utils/logger';
import {
  clearEvaluationDraft,
  getEvaluationDraftKey,
  loadEvaluationDraft,
  saveEvaluationDraft
} from '../utils/evaluationDrafts';

export const useSelfReview = () => {
  const { user } = useUser();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasReview, setHasReview] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [evaluatedCriteriaIds, setEvaluatedCriteriaIds] = useState([]);
  const [criteria, setCriteria] = useState([]);
  const [newCriteria, setNewCriteria] = useState([]);
  const [grades, setGrades] = useState({});
  const [comments, setComments] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [criteriaWithCoefficients, setCriteriaWithCoefficients] = useState([]);
  const [draftRestored, setDraftRestored] = useState(false);

  const draftStorageKey = useMemo(
    () => getEvaluationDraftKey(user?.id, user?.id),
    [user?.id]
  );

  // Загрузка данных
  const loadData = useCallback(async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      setError(null);

      // 1. Проверяем есть ли уже самооценка
      const checkRes = await apiClient.get(`${API_ENDPOINTS.CHECK_SELF_REVIEWS}?user_id=${user.id}`);
      
      let evaluatedIds = [];
      if (checkRes.data.has_self_review) {
        setHasReview(true);
        setReviewData(checkRes.data);
        
        const rawIds = checkRes.data.evaluated_criteria_ids;
        
        // Логика парсинга ID
        if (Array.isArray(rawIds)) {
          evaluatedIds = rawIds.map(Number);
        } else if (typeof rawIds === 'string') {
          evaluatedIds = rawIds
            .replace(/[{}]/g, '')
            .split(',')
            .filter(Boolean)
            .map(Number);
        }
        
        evaluatedIds = evaluatedIds.filter(id => id && id > 0);
        setEvaluatedCriteriaIds(evaluatedIds);
      }

      // 2. Загружаем критерии
      const criteriaRes = await apiClient.get(API_ENDPOINTS.CRITERIA);
      const responseData = Array.isArray(criteriaRes.data) ? criteriaRes.data[0] : criteriaRes.data;
      const allCriteria = responseData?.data || [];

      // 2.5. Загружаем коэффициенты для расчета (асинхронно)
      if (API_ENDPOINTS.SCORE_COEFFICIENTS) {
        apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS)
          .then(response => {
            const data = response.data?.data || response.data || [];
            setCriteriaWithCoefficients(data);
          })
          .catch(error => {
            logger.warn('Не удалось загрузить коэффициенты:', error);
          });
      }

      // 3. Фильтруем критерии (активные + самооценка + аудитория)
      const filtered = allCriteria.filter(c => {
        const isActive = c.is_active === true || c.is_active === 'true';
        const isSelfAssessment = c.selfassesment === true || c.selfassesment === 'true';
        const isCLevelOnly = c.c_level_only === true || c.c_level_only === 'true';
        
        const audience = c.target_audience?.toLowerCase() || 'all';
        const category = user.work_category?.toLowerCase() || 'general';
        
        return isActive
          && isSelfAssessment
          && !isCLevelOnly
          && (audience === 'all' || audience === category);
      });

      setCriteria(filtered);

      // 4. Определяем новые критерии
      if (checkRes.data.has_self_review) {
        const unevaluated = filtered.filter(
          c => !evaluatedIds.includes(Number(c.id))
        );
        
        setNewCriteria(unevaluated);

        if (unevaluated.length === 0) {
          clearEvaluationDraft(draftStorageKey);
          setGrades({});
          setComments({});
          setDraftRestored(false);
        } else {
          const savedDraft = loadEvaluationDraft(draftStorageKey);
          setGrades(savedDraft?.evaluations || {});
          setComments(savedDraft?.comments || {});
          setDraftRestored(Boolean(savedDraft));
        }
      } else {
        // First self-review: resume a local draft after refresh or 401-relogin.
        setNewCriteria(filtered);
        const savedDraft = loadEvaluationDraft(draftStorageKey);
        setGrades(savedDraft?.evaluations || {});
        setComments(savedDraft?.comments || {});
        setDraftRestored(Boolean(savedDraft));
      }

    } catch (err) {
      logger.error('Error loading data:', err);
      // Используем userMessage от apiClient или стандартное сообщение
      const errorMessage = err.userMessage || err.message || 'Ошибка загрузки данных самооценки';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [user?.id, user?.work_category, draftStorageKey]);

  // Отправка самооценки
  const submitReview = useCallback(async () => {
    try {
      setSubmitting(true);
      const scores = Object.values(grades);
      
      if (scores.length === 0) {
        setSubmitting(false);
        return { success: false, error: 'Нет оценок для отправки' };
      }

      // Простое среднее (для отображения сотрудникам, 1-10)
      const simpleAverage = (scores.reduce((sum, s) => sum + s, 0) / scores.length).toFixed(2);

      // Взвешенный балл с коэффициентами (для Admin/C-level)
      const gradeCoef = user?.grade_coefficient || 1.0;
      const weightedScore = calculateWeightedScore(grades, criteriaWithCoefficients, gradeCoef);

      const payload = {
        user_id: user.id,
        final_score: parseFloat(simpleAverage),      // Простое среднее для сотрудников
        weighted_score: parseFloat(weightedScore),   // Взвешенный балл для Admin/C-level
        grades: grades,
        comments: comments,                          // Комментарии к каждому критерию
        is_update: hasReview
      };

      await apiClient.post(API_ENDPOINTS.SELF_REVIEW_SUBMIT, payload);

      clearEvaluationDraft(draftStorageKey);
      setDraftRestored(false);

      // Перезагружаем данные
      await loadData();
      
      return { success: true };
    } catch (err) {
      logger.error('Error submitting self-review:', err);
      // Используем userMessage от apiClient или стандартное сообщение
      const errorMessage = err.userMessage || err.message || 'Ошибка при сохранении самооценки';
      return { success: false, error: errorMessage };
    } finally {
      setSubmitting(false);
    }
  }, [grades, comments, hasReview, user, loadData, criteriaWithCoefficients, draftStorageKey]);

  // Изменение оценки
  const handleGradeChange = useCallback((criteriaId, value) => {
    setGrades(prev => {
      const nextGrades = {
        ...prev,
        [criteriaId]: parseInt(value)
      };
      saveEvaluationDraft(draftStorageKey, nextGrades, comments);
      return nextGrades;
    });
  }, [draftStorageKey, comments]);

  // Изменение комментария
  const handleCommentChange = useCallback((criteriaId, comment) => {
    setComments(prev => {
      const nextComments = {
        ...prev,
        [criteriaId]: comment
      };
      saveEvaluationDraft(draftStorageKey, grades, nextComments);
      return nextComments;
    });
  }, [draftStorageKey, grades]);

  // Загружаем при монтировании
  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    user,
    loading,
    error,
    hasReview,
    reviewData,
    evaluatedCriteriaIds,
    criteria,
    newCriteria,
    grades,
    comments,
    submitting,
    draftRestored,
    setGrades: handleGradeChange,
    setComments: handleCommentChange,
    submitReview,
    reload: loadData
  };
};

export default useSelfReview;

