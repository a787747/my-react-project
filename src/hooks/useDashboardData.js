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

import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useDashboardData = (user) => {
  const [employees, setEmployees] = useState([]);
  const [criteria, setCriteria] = useState([]);
  const [evaluatedDetails, setEvaluatedDetails] = useState({});
  const [campaignActive, setCampaignActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;
      
      try {
        setLoading(true);
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
        setLoading(false);
      }
    };
    
    fetchData();
  }, [user]);

  return {
    employees,
    criteria,
    evaluatedDetails,
    campaignActive,
    loading,
    error,
    setEvaluatedDetails
  };
};
