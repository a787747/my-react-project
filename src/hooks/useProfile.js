/**
 * useProfile - Хук для загрузки профиля пользователя
 * 
 * Назначение: Загрузка данных профиля и деталей оценок
 * Используется в: Profile
 * 
 * Параметры:
 * - userId: number - ID пользователя
 * 
 * Возвращает:
 * - profileData: object - данные профиля
 * - loading: boolean - статус загрузки
 * - error: boolean - ошибка загрузки
 * - evaluationDetails: object - детали выбранной оценки
 * - loadingDetails: boolean - загрузка деталей
 * - fetchEvaluationDetails: function(evaluationId) - загрузить детали
 * - clearDetails: function - очистить детали
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useProfile = (userId) => {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [criteria, setCriteria] = useState([]);
  
  const [evaluationDetails, setEvaluationDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Загрузка профиля
  const fetchProfileData = useCallback(async () => {
    if (!userId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Загружаем профиль и критерии параллельно
      const [profileResponse, criteriaResponse] = await Promise.all([
        apiClient.get(`${API_ENDPOINTS.MY_PROFILE}?user_id=${userId}`),
        apiClient.get(API_ENDPOINTS.CRITERIA).catch((err) => {
          logger.warn('Ошибка загрузки критериев:', err);
          return { data: [] };
        })
      ]);
      
      setProfileData(profileResponse.data);
      
      // Обрабатываем критерии (аналогично useSelfReview)
      const criteriaData = criteriaResponse.data;
      const responseData = Array.isArray(criteriaData) ? criteriaData[0] : criteriaData;
      const allCriteria = responseData?.data || [];
      
      setCriteria(Array.isArray(allCriteria) ? allCriteria : []);
    } catch (err) {
      logger.error('Error fetching profile:', err);
      // Используем userMessage от apiClient или стандартное сообщение
      const errorMessage = err.userMessage || err.message || 'Ошибка загрузки профиля';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Загрузка деталей оценки
  const fetchEvaluationDetails = useCallback(async (evaluationId) => {
    try {
      setLoadingDetails(true);
      const response = await apiClient.get(`${API_ENDPOINTS.EVALUATION_DETAILS}?evaluation_id=${evaluationId}`);
      setEvaluationDetails(response.data);
    } catch (err) {
      logger.error('Error fetching evaluation details:', err);
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  // Очистка деталей
  const clearDetails = useCallback(() => {
    setEvaluationDetails(null);
  }, []);

  // Загружаем профиль при монтировании
  useEffect(() => {
    fetchProfileData();
  }, [fetchProfileData]);

  // Разделяем оценки по типам
  const selfEvaluations = profileData?.evaluations?.filter(e => e.is_self_evaluation) || [];
  
  // Оценки от руководителя (evaluation_source = 'manager' или undefined)
  const managerEvaluations = profileData?.evaluations?.filter(e => 
    !e.is_self_evaluation && (e.evaluation_source === 'manager' || !e.evaluation_source)
  ) || [];
  
  // Оценки от подчиненных (evaluation_source = 'subordinate')
  const subordinateEvaluations = profileData?.evaluations?.filter(e => 
    !e.is_self_evaluation && e.evaluation_source === 'subordinate'
  ) || [];

  return {
    profileData,
    loading,
    error,
    criteria,
    selfEvaluations,
    managerEvaluations,
    subordinateEvaluations,
    evaluationDetails,
    loadingDetails,
    fetchEvaluationDetails,
    clearDetails
  };
};

export default useProfile;

