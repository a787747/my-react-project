/**
 * useDashboardData - Хук для загрузки данных дашборда
 * 
 * Назначение: Загрузка списка сотрудников, критериев и статусов оценок
 * Используется в: Dashboard
 * 
 * Параметры:
 * - user: object - текущий пользователь
 * 
 * Возвращает:
 * - employees: массив подчиненных
 * - criteria: массив критериев
 * - evaluatedDetails: статусы оценок
 * - selfReviewsStatus: статусы самооценок
 * - loading: статус загрузки
 * - error: сообщение об ошибке (или null)
 * - setEvaluatedDetails: обновить статусы
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useDashboardData = (user) => {
  const [employees, setEmployees] = useState([]);
  // D-0825-11: employed, out of this period's scope, never a task.
  const [outOfScopeEmployees, setOutOfScopeEmployees] = useState([]);
  const [criteria, setCriteria] = useState([]);
  const [evaluatedDetails, setEvaluatedDetails] = useState({});
  const [campaignActive, setCampaignActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async ({ silent = false } = {}) => {
      if (!user) return;

      try {
        if (!silent) setLoading(true);
        setError(null);
        
        // Completion flags come from the actor-scoped employees route.
        const [employeesRes, criteriaRes, evaluatedRes] = await Promise.all([
          apiClient.get(API_ENDPOINTS.EMPLOYEES, {
            params: { user_id: user.id, role: user.role }
          }),
          apiClient.get(API_ENDPOINTS.CRITERIA),
          apiClient.get(API_ENDPOINTS.CHECK_EVALUATED, {
            params: { evaluator_id: user.id }
          }).catch(() => ({ data: {} }))
        ]);
        
        // Обрабатываем employees
        const employeesPayload = employeesRes.data || {};
        const employeesData = Array.isArray(employeesPayload)
          ? employeesPayload[0]?.data || []
          : employeesPayload.data || [];
        setEmployees(employeesData);
        const outOfScopeData = Array.isArray(employeesPayload)
          ? employeesPayload[0]?.out_of_scope_data || []
          : employeesPayload.out_of_scope_data || [];
        setOutOfScopeEmployees(Array.isArray(outOfScopeData) ? outOfScopeData : []);
        setCampaignActive(
          employeesPayload.campaign_active === true
          || employeesPayload[0]?.campaign_active === true
        );
        
        // Обрабатываем criteria
        const criteriaData = Array.isArray(criteriaRes.data)
          ? criteriaRes.data[0]?.data || []
          : criteriaRes.data.data || [];
        setCriteria(criteriaData);
        
        // Обрабатываем evaluated details
        if (evaluatedRes.data?.details && Array.isArray(evaluatedRes.data.details)) {
          const evaluatedMap = {};
          evaluatedRes.data.details.forEach(item => {
            evaluatedMap[item.subject_id] = {
              latest_evaluation_id: item.latest_evaluation_id,
              last_score: item.last_score
            };
          });
          setEvaluatedDetails(evaluatedMap);
        } else {
          setEvaluatedDetails({});
        }
        
      } catch (err) {
        logger.error('Ошибка загрузки данных:', err);
        const errorMessage = err.userMessage || err.message || 'Ошибка загрузки данных';
        setError(errorMessage);
      } finally {
        if (!silent) setLoading(false);
      }
  }, [user]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    employees,
    outOfScopeEmployees,
    criteria,
    evaluatedDetails,
    campaignActive,
    loading,
    error,
    setEvaluatedDetails,
    // Silent refetch after a submit/additive write: the per-criterion
    // evaluated_by_actor flag and missing_criteria_ids live on the employees
    // rows, so the rows themselves must be refreshed, not only evaluatedDetails.
    refetch: () => fetchData({ silent: true })
  };
};
