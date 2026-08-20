/**
 * useEvaluationsMatrix - Хук для работы с матрицей оценок
 * 
 * Назначение: Загрузка данных матрицы, фильтрация, сортировка и отправка C-level оценок
 * Используется в: AdminEvaluationsMatrix
 * 
 * Возвращает:
 * - employees: массив сотрудников с оценками
 * - loading: статус загрузки
 * - filters: текущие фильтры
 * - filterOptions: опции для фильтров
 * - filteredEmployees: отфильтрованный и отсортированный список
 * - sorting: текущая сортировка { field, direction }
 * - setSorting: установить сортировку
 * - setFilters: установить фильтры
 * - clearFilters: сбросить фильтры
 * - submitCLevelEvaluation: отправить C-level оценку
 * - fetchData: перезагрузить данные
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { extractFilterOptions, filterEmployees, getCriterionFinalScore, cLevelWritePath } from '../utils/matrixUtils';
import logger from '../utils/logger';

const initialFilters = {
  department: '',
  grade: '',
  jobTitle: '',
  projectParticipant: ''
};

const initialSorting = {
  field: 'full_name', // full_name, department_name, или criteria_id
  direction: 'asc'    // asc или desc
};

/**
 * Сортировка сотрудников
 */
const sortEmployees = (employees, sorting) => {
  if (!sorting || !sorting.field) return employees;

  const sorted = [...employees].sort((a, b) => {
    let valueA, valueB;

    if (sorting.field === 'full_name') {
      valueA = a.full_name?.toLowerCase() || '';
      valueB = b.full_name?.toLowerCase() || '';
    } else if (sorting.field === 'department_name') {
      valueA = a.department_name?.toLowerCase() || '';
      valueB = b.department_name?.toLowerCase() || '';
    } else if (sorting.field === 'grade_code') {
      valueA = a.grade_code?.toLowerCase() || '';
      valueB = b.grade_code?.toLowerCase() || '';
    } else if (sorting.field.startsWith('criteria_')) {
      // Сортировка по конкретному критерию
      const criteriaId = parseInt(sorting.field.replace('criteria_', ''));
      const criterionA = a.criteria?.find(c => c.criteria_id === criteriaId);
      const criterionB = b.criteria?.find(c => c.criteria_id === criteriaId);
      
      valueA = criterionA ? getCriterionFinalScore(criterionA) : null;
      valueB = criterionB ? getCriterionFinalScore(criterionB) : null;
      
      // null значения в конец
      if (valueA === null && valueB === null) return 0;
      if (valueA === null) return 1;
      if (valueB === null) return -1;
    } else {
      return 0;
    }

    // Сравнение
    if (typeof valueA === 'string') {
      const result = valueA.localeCompare(valueB);
      return sorting.direction === 'asc' ? result : -result;
    } else {
      const result = (valueA || 0) - (valueB || 0);
      return sorting.direction === 'asc' ? result : -result;
    }
  });

  return sorted;
};

export const useEvaluationsMatrix = (periodId = null) => {
  const [employees, setEmployees] = useState([]);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState(initialFilters);
  const [sorting, setSortingState] = useState(initialSorting);

  // Загрузка данных
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(API_ENDPOINTS.ADMIN_EVALUATIONS_MATRIX, {
        params: periodId ? { period_id: periodId } : undefined
      });
      const body = response.data || {};
      setEmployees(body.data || []);
      setPeriod(body.period || null);
      setCampaignActive(Boolean(body.campaign_active));
    } catch (error) {
      logger.error('Ошибка загрузки:', error);
    } finally {
      setLoading(false);
    }
  }, [periodId]);

  // Загружаем при монтировании
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Уникальные значения для фильтров
  const filterOptions = useMemo(() => {
    return extractFilterOptions(employees);
  }, [employees]);

  // Отфильтрованный и отсортированный список
  const filteredEmployees = useMemo(() => {
    const filtered = filterEmployees(employees, filters);
    return sortEmployees(filtered, sorting);
  }, [employees, filters, sorting]);

  // Изменить один фильтр
  const handleFilterChange = useCallback((key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  // Сбросить фильтры
  const clearFilters = useCallback(() => {
    setFilters(initialFilters);
  }, []);

  // Установить сортировку
  const setSorting = useCallback((field) => {
    setSortingState(prev => {
      if (prev.field === field) {
        // Переключаем направление или сбрасываем
        if (prev.direction === 'asc') {
          return { field, direction: 'desc' };
        } else {
          return initialSorting; // Сброс к дефолту
        }
      }
      return { field, direction: 'asc' };
    });
  }, []);

  // Сбросить сортировку
  const clearSorting = useCallback(() => {
    setSortingState(initialSorting);
  }, []);

  // Количество активных фильтров
  const activeFiltersCount = useMemo(() => {
    return Object.values(filters).filter(v => v !== '').length;
  }, [filters]);

  // C-level: new row → submit-evaluation; existing actor row → update-evaluation.
  const submitCLevelEvaluation = useCallback(async (evaluatorId, subjectId, grades, evaluationId = null) => {
    try {
      const scores = Object.values(grades);
      const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
      const finalScore = average.toFixed(2);

      const payload = {
        evaluator_id: evaluatorId,
        subject_id: subjectId,
        final_score: parseFloat(finalScore),
        grades: grades,
        evaluation_source: 'c_level_direct'
      };

      if (cLevelWritePath(evaluationId) === 'update') {
        await apiClient.post(API_ENDPOINTS.UPDATE_EVALUATION, {
          ...payload,
          evaluation_id: evaluationId
        });
      } else {
        await apiClient.post(API_ENDPOINTS.SUBMIT_EVALUATION, payload);
      }
      await fetchData();
      
      return { success: true };
    } catch (error) {
      logger.error('Ошибка сохранения:', error);
      const status = error.response?.status;
      const apiError = error.response?.data?.error || error.response?.data?.message;
      return {
        success: false,
        error: status === 409
          ? 'Эта оценка уже есть. Откройте её снова — сохранится через изменение, не через повторную отправку.'
          : (apiError || 'Ошибка при сохранении оценки')
      };
    }
  }, [fetchData]);

  // Отправка корректировки оценки (mid_level или c_level)
  const submitScoreCorrection = useCallback(async (evaluatorId, subjectId, criteriaId, score, correctionLevel = null) => {
    try {
      const payload = {
        evaluator_id: evaluatorId,
        subject_id: subjectId,
        criteria_id: criteriaId,
        correction_score: score
      };
      
      // Добавляем уровень корректировки если указан
      if (correctionLevel) {
        payload.correction_level = correctionLevel;
      }

      await apiClient.post(API_ENDPOINTS.ADMIN_SCORE_CORRECTION, payload);
      await fetchData(); // Перезагружаем данные
      
      return { success: true };
    } catch (error) {
      logger.error('Ошибка сохранения корректировки:', error);
      return { success: false, error: 'Ошибка при сохранении корректировки' };
    }
  }, [fetchData]);

  return {
    employees,
    period,
    campaignActive,
    loading,
    filters,
    filterOptions,
    filteredEmployees,
    sorting,
    activeFiltersCount,
    setFilters: handleFilterChange,
    clearFilters,
    setSorting,
    clearSorting,
    submitCLevelEvaluation,
    submitScoreCorrection,
    fetchData
  };
};

export default useEvaluationsMatrix;
