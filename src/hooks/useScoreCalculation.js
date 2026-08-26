/**
 * useScoreCalculation - Хук для калькуляции итоговых баллов сотрудников
 * 
 * Назначение: Загрузка данных для детальной калькуляции баллов с учетом
 * весов критериев, коэффициентов оценок и коэффициентов грейдов
 * 
 * Используется в: AdminScoreCalculator
 * 
 * Возвращает:
 * - employees: список сотрудников с базовой информацией
 * - criteriaWithCoefficients: критерии с весами и коэффициентами
 * - grades: массив грейдов с коэффициентами
 * - loading: статус загрузки
 * - error: ошибка
 * - getEmployeeCalculation: функция для получения детальной калькуляции сотрудника
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { getCLevelChannel } from '../utils/matrixUtils';
import logger from '../utils/logger';

/**
 * Получить финальную оценку по критерию (с учетом mid-level и C-level корректировок)
 * Логика: для c_level_only критериев - c_level_score (СРЕДНЕЕ по всем C-level,
 *         D-0826-1; число оценщиков приходит рядом как `c_level_count`)
 *         для остальных: среднее из (manager_score, mid_level_correction?, c_level_correction?)
 */
const getCriterionFinalScore = (criterion) => {
  const { manager_score, mid_level_correction, c_level_correction, c_level_only } = criterion;

  // Для C-level критериев
  if (c_level_only) {
    return getCLevelChannel(criterion).score;
  }

  // Если нет оценки менеджера
  if (manager_score === null || manager_score === undefined) {
    return null;
  }
  
  // Собираем все оценки для усреднения
  const scores = [manager_score];
  
  if (mid_level_correction !== null && mid_level_correction !== undefined) {
    scores.push(mid_level_correction);
  }
  
  if (c_level_correction !== null && c_level_correction !== undefined) {
    scores.push(c_level_correction);
  }
  
  const sum = scores.reduce((acc, s) => acc + s, 0);
  return sum / scores.length;
};

export const useScoreCalculation = () => {
  const [employees, setEmployees] = useState([]);
  const [matrixData, setMatrixData] = useState([]);
  const [criteriaWithCoefficients, setCriteriaWithCoefficients] = useState([]);
  const [grades, setGrades] = useState([]);
  const [gradesMap, setGradesMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);

  // Загрузка всех данных
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Загружаем данные параллельно:
      // 1. Матрицу оценок (содержит сотрудников и их оценки)
      // 2. Коэффициенты критериев
      // 3. Данные пользователей с грейдами
      // allSettled, а не all с молчаливыми catch: пустой набор коэффициентов
      // неотличим от правды и давал невзвешенный расчёт без ошибки (BUG-042).
      const [matrixResult, coefficientsResult, usersDataResult] = await Promise.allSettled([
        apiClient.get(API_ENDPOINTS.ADMIN_EVALUATIONS_MATRIX),
        apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS),
        apiClient.get(API_ENDPOINTS.ADMIN_USERS_DATA)
      ]);

      const failures = [];
      if (matrixResult.status === 'rejected') {
        logger.error('Матрица оценок не загружена:', matrixResult.reason);
        failures.push('Матрица оценок не загружена — расчёт невозможен');
      }
      if (coefficientsResult.status === 'rejected') {
        logger.error('Коэффициенты критериев не загружены:', coefficientsResult.reason);
        failures.push('Коэффициенты не загружены — расчёт невозможен');
      }
      if (usersDataResult.status === 'rejected') {
        logger.error('Коэффициенты грейдов не загружены:', usersDataResult.reason);
        failures.push('Коэффициенты грейдов не загружены — расчёт невозможен');
      }
      if (failures.length > 0) {
        setMatrixData([]);
        setEmployees([]);
        setCriteriaWithCoefficients([]);
        setGrades([]);
        setGradesMap({});
        setPeriod(null);
        setCampaignActive(false);
        setError(failures.join(' · '));
        return;
      }

      const matrixResponse = matrixResult.value;
      const coefficientsResponse = coefficientsResult.value;
      const usersDataResponse = usersDataResult.value;

      const rawEmployees = matrixResponse.data.data || [];
      setPeriod(matrixResponse.data.period || null);
      setCampaignActive(Boolean(matrixResponse.data.campaign_active));
      const coefficients = coefficientsResponse.data?.data || coefficientsResponse.data || [];
      const gradesData = usersDataResponse.data?.options?.grades || [];
      
      // Сохраняем матрицу данных
      setMatrixData(rawEmployees);
      
      // Формируем список сотрудников для селектора
      // API возвращает поле "id" (u.id в SQL)
      const employeesList = rawEmployees.map(emp => ({
        id: emp.id,
        full_name: emp.full_name,
        department_name: emp.department_name,
        grade_code: emp.grade_code || emp.grade,
        job_title: emp.job_title
      }));
      
      setEmployees(employeesList);
      
      // Нормализуем коэффициенты критериев
      const normalizedCoefficients = (Array.isArray(coefficients) ? coefficients : []).map(crit => ({
        ...crit,
        weight: parseFloat(crit.weight) || 1.0,
        score_coefficients: normalizeScoreCoefficients(crit.score_coefficients)
      }));
      setCriteriaWithCoefficients(normalizedCoefficients);
      
      // Создаем карту грейдов
      const gradesMapData = {};
      gradesData.forEach(g => {
        gradesMapData[g.code] = parseFloat(g.coefficient) || 1.0;
      });
      setGradesMap(gradesMapData);
      setGrades(gradesData);
      
      logger.log('Score Calculation data loaded:', {
        employees: employeesList.length,
        criteria: normalizedCoefficients.length,
        grades: gradesData.length
      });
      
    } catch (err) {
      logger.error('Ошибка загрузки данных калькуляции:', err);
      setError('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, []);

  // Нормализация коэффициентов - убедиться что есть все уровни 1-10
  const normalizeScoreCoefficients = (coefficients) => {
    const normalized = {};
    for (let i = 1; i <= 10; i++) {
      normalized[i] = coefficients && coefficients[i] !== undefined 
        ? parseFloat(coefficients[i]) 
        : 1.0;
    }
    return normalized;
  };

  /**
   * Получить детальную калькуляцию для сотрудника
   * @param {number} employeeId - ID сотрудника
   * @returns {Object} объект с детальной калькуляцией
   */
  const getEmployeeCalculation = useCallback((employeeId) => {
    // Находим данные сотрудника из матрицы по id
    const empData = matrixData.find(e => e.id === employeeId);
    if (!empData) {
      logger.warn('Employee not found in matrixData:', employeeId);
      return null;
    }
    
    const gradeCode = empData.grade_code || empData.grade;
    const gradeCoefficient = gradesMap[gradeCode] || 1.0;
    
    // Рассчитываем детали по каждому критерию
    const criteriaDetails = [];
    let totalWeightedSum = 0;
    let totalWeight = 0;
    
    // Создаем карту коэффициентов для быстрого доступа (как в useFinalScoresMatrix)
    const coefficientsMap = {};
    criteriaWithCoefficients.forEach(c => {
      coefficientsMap[c.id] = c;
    });
    
    if (empData.criteria && Array.isArray(empData.criteria)) {
      empData.criteria.forEach(crit => {
        const rawScore = getCriterionFinalScore(crit);
        if (rawScore === null) return;
        
        // Используем ту же логику что в useFinalScoresMatrix.calculateCriterionScore
        const criteriaCoefs = coefficientsMap[crit.criteria_id];
        let weight = 1.0;
        let scoreCoefficient = 1.0;
        let weightedScore = rawScore;
        
        if (criteriaCoefs) {
          weight = criteriaCoefs.weight || 1.0;
          const scoreLevel = Math.round(rawScore);
          const clampedLevel = Math.max(0, Math.min(10, scoreLevel)); // 0-10 как в useFinalScoresMatrix
          scoreCoefficient = criteriaCoefs.score_coefficients?.[clampedLevel] ?? 1.0;
          
          // Формула: оценка × коэффициент_оценки × вес_критерия
          weightedScore = rawScore * scoreCoefficient * weight;
        }
        
        criteriaDetails.push({
          criteria_id: crit.criteria_id,
          criteria_title: crit.criteria_title,
          target_audience: crit.target_audience || 'all',
          c_level_only: crit.c_level_only || false,
          raw_score: rawScore,
          score_coefficient: scoreCoefficient,
          weight: weight,
          weighted_score: weightedScore
        });
        
        totalWeightedSum += weightedScore;
        totalWeight += weight;
      });
    }
    
    // Сортировка критериев: сначала общие, потом проектные, потом для менеджеров, потом c_level
    const sortedCriteria = [...criteriaDetails].sort((a, b) => {
      const orderMap = {
        'all': 1,
        'project_participants': 2,
        'project': 3,
        'tender': 4,
        'managers_only': 5
      };
      
      // c_level_only критерии в конце
      if (a.c_level_only && !b.c_level_only) return 1;
      if (!a.c_level_only && b.c_level_only) return -1;
      
      const orderA = orderMap[a.target_audience] || 10;
      const orderB = orderMap[b.target_audience] || 10;
      
      return orderA - orderB;
    });
    
    // Итоговый расчёт: Σ взвешенных × коэфф. грейда (как в useFinalScoresMatrix)
    // НЕ делим на сумму весов!
    const finalScore = totalWeightedSum * gradeCoefficient;
    
    return {
      employee_id: employeeId,
      full_name: empData.full_name,
      department_name: empData.department_name,
      job_title: empData.job_title,
      grade_code: gradeCode,
      grade_coefficient: gradeCoefficient,
      criteria: sortedCriteria,              // Отсортированные критерии
      total_weighted_sum: totalWeightedSum,  // Σ(оценка × коэф × вес)
      total_weight: totalWeight,             // Σ весов (для информации)
      final_score: finalScore                // totalWeightedSum × gradeCoefficient
    };
  }, [matrixData, criteriaWithCoefficients, gradesMap]);

  // Загружаем данные при монтировании
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    employees,
    criteriaWithCoefficients,
    grades,
    gradesMap,
    loading,
    error,
    period,
    campaignActive,
    fetchData,
    getEmployeeCalculation
  };
};

export default useScoreCalculation;

