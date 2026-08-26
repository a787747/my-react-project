/**
 * useAllEvaluations - Хук для загрузки всех оценок (админ)
 * 
 * Назначение: Загрузка списка всех сотрудников с оценками и деталей
 * Используется в: AdminAllEvaluations
 * 
 * Возвращает:
 * - employees: array - список сотрудников
 * - loading: boolean - статус загрузки
 * - detailsData: object - детали выбранного сотрудника
 * - loadingDetails: boolean - загрузка деталей
 * - fetchDetails: function(userId, type, evalId) - загрузить детали
 * - clearDetails: function - очистить детали
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useAllEvaluations = () => {
  const [employees, setEmployees] = useState([]);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [detailsData, setDetailsData] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Загрузка списка
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(API_ENDPOINTS.ADMIN_ALL_EVALUATIONS);
      setEmployees(response.data.data || []);
      setPeriod(response.data.period || null);
      setCampaignActive(Boolean(response.data.campaign_active));
    } catch (err) {
      logger.error('Ошибка загрузки:', err);
      // Отказ или сбой обязан дойти до экрана: пустой список без причины
      // неотличим от «оценок ещё нет».
      setError(err.userMessage || 'Не удалось загрузить оценки');
    } finally {
      setLoading(false);
    }
  }, []);

  // Загрузка деталей по пользователю
  // type: 'all' | 'self' | 'received_from_manager' | 'gave_to_manager' | 'gave_to_subordinates'
  const fetchDetails = useCallback(async (userId, type = 'all', evalId = null) => {
    try {
      setLoadingDetails(true);
      setDetailsData(null);
      
      const params = { 
        user_id: userId,
        detail_type: type
      };
      
      if (evalId) {
        params.evaluation_id = evalId;
      }
      
      const response = await apiClient.get(API_ENDPOINTS.ADMIN_EVALUATION_DETAILS_BY_USER, {
        params
      });
      
      setDetailsData(response.data.data);
    } catch (error) {
      logger.error('Ошибка загрузки деталей:', error);
      setDetailsData(null);
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  // Очистка деталей
  const clearDetails = useCallback(() => {
    setDetailsData(null);
  }, []);

  // Загружаем при монтировании
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    employees,
    period,
    campaignActive,
    loading,
    error,
    detailsData,
    loadingDetails,
    fetchDetails,
    clearDetails,
    reload: fetchData
  };
};

export default useAllEvaluations;
