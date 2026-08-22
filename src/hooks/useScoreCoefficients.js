/**
 * useScoreCoefficients - Хук для управления коэффициентами оценок и грейдов
 * 
 * Назначение: Загрузка и сохранение коэффициентов оценок для критериев и грейдов
 * Используется в: AdminScoring
 * 
 * Возвращает:
 * - criteriaWithCoefficients: массив критериев с весами и коэффициентами
 * - grades: массив грейдов с коэффициентами
 * - loading: статус загрузки
 * - saving: статус сохранения
 * - error: ошибка (если есть)
 * - hasChanges: есть ли несохраненные изменения
 * - fetchCoefficients: функция перезагрузки данных
 * - saveAll: функция сохранения всех изменений
 * - updateWeight: обновить вес критерия
 * - updateCoefficient: обновить коэффициент оценки
 * - updateGradeCoefficient: обновить коэффициент грейда
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

export const useScoreCoefficients = () => {
  const [criteriaWithCoefficients, setCriteriaWithCoefficients] = useState([]);
  const [grades, setGrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Загрузка всех данных
  const fetchCoefficients = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Загружаем коэффициенты критериев и грейды параллельно.
      // Грейды берём из ADMIN_USERS_DATA (там они в options.grades).
      // Ни один из двух запросов не подменяется пустым ответом: пустая таблица
      // грейдов неотличима от «все коэффициенты 1.0» — это шаблон BUG-030.
      const [coefficientsSettled, usersDataSettled] = await Promise.allSettled([
        apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS),
        apiClient.get(API_ENDPOINTS.ADMIN_USERS_DATA)
      ]);

      if (coefficientsSettled.status === 'rejected' || usersDataSettled.status === 'rejected') {
        const failures = [];
        if (coefficientsSettled.status === 'rejected') {
          logger.error('Ошибка загрузки коэффициентов критериев:', coefficientsSettled.reason);
          failures.push('Коэффициенты критериев не загружены');
        }
        if (usersDataSettled.status === 'rejected') {
          logger.error('Ошибка загрузки грейдов:', usersDataSettled.reason);
          failures.push('Коэффициенты грейдов не загружены');
        }
        setCriteriaWithCoefficients([]);
        setGrades([]);
        setHasChanges(false);
        setError(`${failures.join('. ')} — редактирование невозможно.`);
        return;
      }

      const coefficientsRes = coefficientsSettled.value;
      const usersDataRes = usersDataSettled.value;

      // Обработка коэффициентов критериев
      const rawData = coefficientsRes.data;
      let list = [];
      if (rawData && rawData.data && Array.isArray(rawData.data)) {
        list = rawData.data;
      } else if (Array.isArray(rawData)) {
        list = rawData;
      }
      
      const normalizedList = list.map(crit => ({
        ...crit,
        weight: parseFloat(crit.weight) || 1.0,
        score_coefficients: normalizeCoefficients(crit.score_coefficients)
      }));
      
      setCriteriaWithCoefficients(normalizedList);
      
      // Обработка грейдов из ADMIN_USERS_DATA
      const gradesData = usersDataRes.data?.options?.grades || [];
      logger.log("Loaded grades:", gradesData);
      
      setGrades(gradesData.map(g => ({
        ...g,
        coefficient: parseFloat(g.coefficient) || 1.0
      })));
      
      setHasChanges(false);
    } catch (err) {
      logger.error("Ошибка загрузки:", err);
      setError('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, []);

  // Нормализация коэффициентов - убедиться что есть все уровни 1-10
  const normalizeCoefficients = (coefficients) => {
    const normalized = {};
    for (let i = 1; i <= 10; i++) {
      normalized[i] = coefficients && coefficients[i] !== undefined 
        ? parseFloat(coefficients[i]) 
        : 1.0;
    }
    return normalized;
  };

  // Обновить критерий локально
  const updateCriterion = useCallback((criteriaId, updates) => {
    setCriteriaWithCoefficients(prev => 
      prev.map(crit => {
        if (crit.id === criteriaId) {
          return { ...crit, ...updates };
        }
        return crit;
      })
    );
    setHasChanges(true);
  }, []);

  // Обновить коэффициент для конкретного уровня оценки
  const updateCoefficient = useCallback((criteriaId, scoreLevel, coefficient) => {
    setCriteriaWithCoefficients(prev =>
      prev.map(crit => {
        if (crit.id === criteriaId) {
          return {
            ...crit,
            score_coefficients: {
              ...crit.score_coefficients,
              [scoreLevel]: parseFloat(coefficient) || 1.0
            }
          };
        }
        return crit;
      })
    );
    setHasChanges(true);
  }, []);

  // Обновить вес критерия
  const updateWeight = useCallback((criteriaId, weight) => {
    setCriteriaWithCoefficients(prev =>
      prev.map(crit => {
        if (crit.id === criteriaId) {
          return { ...crit, weight: parseFloat(weight) || 1.0 };
        }
        return crit;
      })
    );
    setHasChanges(true);
  }, []);

  // Обновить коэффициент грейда
  const updateGradeCoefficient = useCallback((gradeId, coefficient) => {
    setGrades(prev =>
      prev.map(grade => {
        if (grade.id === gradeId) {
          return { ...grade, coefficient: parseFloat(coefficient) || 1.0 };
        }
        return grade;
      })
    );
    setHasChanges(true);
  }, []);

  // Сохранить все изменения (критерии + грейды)
  const saveAll = useCallback(async () => {
    try {
      setSaving(true);
      setError(null);
      
      let criteriaSuccess = false;
      let gradesSuccess = false;
      
      // Сохраняем коэффициенты критериев
      try {
        await apiClient.post(API_ENDPOINTS.SCORE_COEFFICIENTS, {
          criteria: criteriaWithCoefficients.map(crit => ({
            id: crit.id,
            weight: crit.weight,
            score_coefficients: crit.score_coefficients
          }))
        });
        criteriaSuccess = true;
      } catch (err) {
        logger.error("Ошибка сохранения критериев:", err);
      }
      
      // Сохраняем грейды отдельно
      try {
        await apiClient.post(API_ENDPOINTS.UPDATE_ADMIN_DATA, {
          grades: grades.map(g => ({
            id: g.id,
            coefficient: g.coefficient
          }))
        });
        gradesSuccess = true;
      } catch (err) {
        logger.error("Ошибка сохранения грейдов:", err);
        if (err.response?.status === 409) {
          return {
            success: false,
            error: err.response?.data?.message || 'Коэффициенты грейдов заморожены, пока период активен',
          };
        }
      }
      
      if (criteriaSuccess && gradesSuccess) {
        setHasChanges(false);
        return { success: true };
      } else if (criteriaSuccess) {
        setHasChanges(false);
        return { success: true, warning: 'Коэффициенты критериев сохранены. Грейды не удалось сохранить (проверьте n8n workflow).' };
      } else {
        setError('Ошибка сохранения');
        return { success: false, error: 'Ошибка сохранения' };
      }
    } catch (err) {
      logger.error("Ошибка сохранения:", err);
      setError('Ошибка сохранения');
      return { success: false, error: 'Ошибка сохранения' };
    } finally {
      setSaving(false);
    }
  }, [criteriaWithCoefficients, grades]);

  // Для обратной совместимости
  const saveCoefficients = saveAll;

  // Сброс изменений
  const resetChanges = useCallback(() => {
    fetchCoefficients();
  }, [fetchCoefficients]);

  // Загружаем данные при монтировании
  useEffect(() => {
    fetchCoefficients();
  }, [fetchCoefficients]);

  return {
    criteriaWithCoefficients,
    grades,
    loading,
    saving,
    error,
    hasChanges,
    fetchCoefficients,
    saveCoefficients,
    saveAll,
    updateCriterion,
    updateCoefficient,
    updateWeight,
    updateGradeCoefficient,
    resetChanges
  };
};

export default useScoreCoefficients;

