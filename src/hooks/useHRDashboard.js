/**
 * useHRDashboard - Хук для получения статусов оценок сотрудников
 * 
 * Назначение: Загрузка данных о статусах самооценок и оценок для HR дашборда
 * Используется в: HRDashboard
 * 
 * Возвращает:
 * - employees: массив сотрудников со статусами оценок
 * - loading: статус загрузки
 * - error: ошибка загрузки
 * - stats: общая статистика
 * - refetch: функция перезагрузки данных
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useHRDashboard = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Загрузка данных
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const res = await apiClient.get(API_ENDPOINTS.HR_EVALUATION_STATUS);
      const data = res.data;
      
      if (data.success) {
        setEmployees(data.employees || []);
      } else {
        setError('Не удалось загрузить данные');
      }
    } catch (err) {
      logger.error('Ошибка загрузки статусов оценок:', err);
      setError('Не удалось загрузить статусы оценок');
    } finally {
      setLoading(false);
    }
  }, []);

  // Вычисляем статистику
  const stats = useMemo(() => {
    if (!employees.length) return null;

    const total = employees.length;
    
    // C-level не делают самооценку, поэтому считаем только тех, кто должен
    const shouldDoSelfReview = employees.filter(e => e.role !== 'c_level');
    const withSelfReview = shouldDoSelfReview.filter(e => e.has_self_review).length;
    
    // Сотрудники, которые должны оценить руководителя (не c-level и имеют менеджера)
    const shouldEvaluateManager = employees.filter(e => e.manager_id && e.role !== 'c_level');
    const evaluatedManager = shouldEvaluateManager.filter(e => e.evaluated_manager).length;
    
    // Сотрудники с подчинёнными
    const withSubordinates = employees.filter(e => e.has_subordinates || e.total_subordinates > 0);
    const allSubordinatesEvaluated = withSubordinates.filter(e => e.all_subordinates_evaluated).length;

    // Полностью завершившие все оценки
    const fullyCompleted = employees.filter(e => {
      // C-level не делают самооценку
      const needsSelfReview = e.role !== 'c_level';
      
      // Если нужна самооценка и её нет - не завершено
      if (needsSelfReview && !e.has_self_review) return false;
      
      // Если есть менеджер и не C-level - должен оценить руководителя
      if (e.manager_id && e.role !== 'c_level' && !e.evaluated_manager) return false;
      
      // Если есть подчинённые - должен оценить всех
      if ((e.has_subordinates || e.total_subordinates > 0) && !e.all_subordinates_evaluated) return false;
      
      return true;
    }).length;

    return {
      total,
      withSelfReview,
      shouldDoSelfReview: shouldDoSelfReview.length,
      selfReviewPercent: shouldDoSelfReview.length > 0 
        ? Math.round((withSelfReview / shouldDoSelfReview.length) * 100) 
        : 100,
      shouldEvaluateManager: shouldEvaluateManager.length,
      evaluatedManager,
      managerEvaluationPercent: shouldEvaluateManager.length > 0 
        ? Math.round((evaluatedManager / shouldEvaluateManager.length) * 100) 
        : 100,
      withSubordinates: withSubordinates.length,
      allSubordinatesEvaluated,
      subordinatesPercent: withSubordinates.length > 0 
        ? Math.round((allSubordinatesEvaluated / withSubordinates.length) * 100) 
        : 100,
      fullyCompleted,
      completionPercent: Math.round((fullyCompleted / total) * 100)
    };
  }, [employees]);

  // Загружаем данные при монтировании
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    employees,
    loading,
    error,
    stats,
    refetch: fetchData
  };
};

export default useHRDashboard;

