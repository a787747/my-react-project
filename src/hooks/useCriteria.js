/**
 * useCriteria - Хук для управления критериями оценки
 * 
 * Назначение: Загрузка, сохранение и удаление критериев оценки
 * Используется в: AdminSettings
 * 
 * Возвращает:
 * - criteriaList: массив критериев
 * - evaluationStarted: оценка запущена — сохранение и удаление вернут 409
 * - loading: статус загрузки
 * - fetchCriteria: функция перезагрузки
 * - saveCriterion: функция сохранения критерия
 * - deleteCriterion: функция удаления критерия
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useCriteria = () => {
  const [criteriaList, setCriteriaList] = useState([]);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);
  // Каталог замораживается на СТАРТЕ оценки, не на активации (D-0822-1).
  const [evaluationStarted, setEvaluationStarted] = useState(false);
  const [loading, setLoading] = useState(true);

  // Загрузка критериев
  const fetchCriteria = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.post(API_ENDPOINTS.MANAGE_CRITERIA, { action: 'get' });
      const rawData = response.data;
      
      let list = [];
      if (rawData && rawData.data && Array.isArray(rawData.data)) {
        list = rawData.data;
      } else if (Array.isArray(rawData)) {
        list = rawData;
      }
      
      setCriteriaList(list);
      setPeriod(rawData?.period || null);
      setCampaignActive(Boolean(rawData?.campaign_active));
      setEvaluationStarted(Boolean(rawData?.evaluation_started));
    } catch (error) {
      logger.error("Ошибка загрузки критериев:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Сохранение критерия (создание или обновление)
  const saveCriterion = useCallback(async (criterionData) => {
    try {
      await apiClient.post(API_ENDPOINTS.MANAGE_CRITERIA, {
        action: 'save',
        criteria: criterionData
      });
      await fetchCriteria();
      return { success: true };
    } catch (error) {
      logger.error("Ошибка сохранения:", error);
      const status = error.response?.status;
      const serverMessage = error.response?.data?.message;
      if (status === 409) {
        return { success: false, error: serverMessage || 'Критерии заморожены: оценка в текущем периоде уже идёт' };
      }
      return { success: false, error: 'Ошибка сохранения' };
    }
  }, [fetchCriteria]);

  // Удаление критерия
  const deleteCriterion = useCallback(async (id) => {
    try {
      await apiClient.post(API_ENDPOINTS.MANAGE_CRITERIA, {
        action: 'delete',
        criteria: { id }
      });
      await fetchCriteria();
      return { success: true };
    } catch (error) {
      logger.error("Ошибка удаления:", error);
      return { 
        success: false, 
        error: 'Не удалось удалить. Возможно, критерий уже используется в оценках.' 
      };
    }
  }, [fetchCriteria]);

  // Загружаем данные при монтировании
  useEffect(() => {
    fetchCriteria();
  }, [fetchCriteria]);

  return {
    criteriaList,
    period,
    campaignActive,
    evaluationStarted,
    loading,
    fetchCriteria,
    saveCriterion,
    deleteCriterion
  };
};

export default useCriteria;

