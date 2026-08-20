/**
 * useEvaluationHistory - Хук для загрузки истории оценок
 * 
 * Назначение: Загрузка истории оценок, проведенных текущим пользователем
 * Используется в: EvaluationHistory
 * 
 * Параметры:
 * - userId: number - ID пользователя (оценщика)
 * 
 * Возвращает:
 * - history: array - список проведенных оценок
 * - loading: boolean - статус загрузки
 * - evaluationDetails: object - детали выбранной оценки
 * - loadingDetails: boolean - загрузка деталей
 * - fetchDetails: function(evaluationId) - загрузить детали
 * - clearDetails: function - очистить детали
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useEvaluationHistory = (userId) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [evaluationDetails, setEvaluationDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Загрузка истории
  const fetchHistory = useCallback(async () => {
    if (!userId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get(API_ENDPOINTS.EVALUATION_HISTORY, {
        params: { evaluator_id: userId }
      });

      // Универсальная обработка ответа
      let data = [];
      if (response.data && Array.isArray(response.data.data)) {
        data = response.data.data;
      } else if (Array.isArray(response.data)) {
        data = response.data;
      }

      setHistory(data);
    } catch (err) {
      logger.error('Ошибка загрузки истории:', err);
      // Используем userMessage от apiClient или стандартное сообщение
      const errorMessage = err.userMessage || err.message || 'Ошибка загрузки истории оценок';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Загрузка деталей оценки
  const fetchDetails = useCallback(async (evaluationId) => {
    try {
      setLoadingDetails(true);
      const response = await apiClient.get(API_ENDPOINTS.EVALUATION_DETAILS, {
        params: { evaluation_id: evaluationId }
      });
      
      // Обрабатываем разные форматы ответа
      let details = response.data;
      
      // Если ответ имеет структуру { status, evaluation, scores }
      if (response.data && response.data.status === 'success') {
        details = {
          evaluation: response.data.evaluation,
          scores: response.data.scores || []
        };
      }
      // Если данные вложены в data
      else if (response.data && response.data.data) {
        details = response.data.data;
      }
      
      setEvaluationDetails(details);
    } catch (error) {
      logger.error('Ошибка загрузки деталей:', error);
      setEvaluationDetails(null);
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  // Очистка деталей
  const clearDetails = useCallback(() => {
    setEvaluationDetails(null);
  }, []);

  // Загружаем при монтировании
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return {
    history,
    loading,
    error,
    evaluationDetails,
    loadingDetails,
    fetchDetails,
    clearDetails
  };
};

export default useEvaluationHistory;

