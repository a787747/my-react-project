/**
 * useFinalScoresMatrix - Хук для работы с матрицей итоговых баллов
 * 
 * Назначение: Загрузка данных матрицы оценок, расчет взвешенных баллов по критериям
 * с учетом весов и коэффициентов, фильтрация и сортировка
 * 
 * Используется в: AdminFinalScores
 * 
 * Возвращает:
 * - employees: массив сотрудников с рассчитанными баллами
 * - criteriaList: список критериев с весами
 * - loading: статус загрузки
 * - error: текст ошибки загрузки; пока он не null, чисел на экране быть не должно
 * - filters: текущие фильтры
 * - filterOptions: опции для фильтров
 * - filteredEmployees: отфильтрованный и отсортированный список
 * - sorting: текущая сортировка { field, direction }
 * - totals: итоговые суммы по всем сотрудникам и критериям
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import {
  buildSharedCriteriaList,
  extractFilterOptions,
  filterEmployees,
  takesBonusShare,
} from '../utils/matrixUtils';
import logger from '../utils/logger';

const initialFilters = {
  department: '',
  grade: '',
  jobTitle: '',
  projectParticipant: ''
};

const initialSorting = {
  field: 'final_weighted_score',
  direction: 'desc'
};

/**
 * Веса, коэффициенты уровней и коэффициенты грейдов — часть формулы бонуса,
 * а не оформление. Если любой из трёх запросов не удался, экран обязан
 * показать ошибку: молчаливый дефолт нарисовал бы правдоподобную, но
 * невзвешенную таблицу денег (BUG-030).
 */
const LOAD_ERRORS = {
  matrix: 'Матрица оценок не загружена — расчёт невозможен',
  coefficients: 'Коэффициенты не загружены — расчёт невозможен',
  grades: 'Коэффициенты грейдов не загружены — расчёт невозможен'
};

/**
 * Получить финальную оценку по критерию (с учетом mid-level и C-level корректировок)
 * Логика: для c_level_only критериев - c_level_score
 *         для остальных: среднее из (manager_score, mid_level_correction?, c_level_correction?)
 */
const getCriterionFinalScore = (criterion) => {
  const { manager_score, mid_level_correction, c_level_correction, c_level_score, c_level_only } = criterion;
  
  // Для C-level критериев
  if (c_level_only) {
    return c_level_score ?? null;
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

/**
 * Рассчитать взвешенный балл по критерию
 * Формула: оценка × коэффициент_оценки × вес_критерия
 */
const calculateCriterionScore = (score, criteriaId, coefficientsMap) => {
  if (score === null || score === undefined) return null;
  
  const criteriaCoefs = coefficientsMap[criteriaId];
  if (!criteriaCoefs) {
    // Если нет коэффициентов, просто умножаем на вес (дефолт 1.0)
    return score;
  }
  
  const weight = criteriaCoefs.weight || 1.0;
  const scoreLevel = Math.round(score);
  const clampedLevel = Math.max(0, Math.min(10, scoreLevel));
  const scoreCoef = criteriaCoefs.score_coefficients?.[clampedLevel] ?? 1.0;
  
  return score * scoreCoef * weight;
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
    } else if (sorting.field === 'final_weighted_score') {
      valueA = a.final_weighted_score ?? -1;
      valueB = b.final_weighted_score ?? -1;
    } else if (sorting.field === 'weighted_sum') {
      valueA = a.weighted_sum ?? -1;
      valueB = b.weighted_sum ?? -1;
    } else if (sorting.field.startsWith('criteria_')) {
      const criteriaId = parseInt(sorting.field.replace('criteria_', ''));
      valueA = a.criteria_scores?.[criteriaId] ?? -1;
      valueB = b.criteria_scores?.[criteriaId] ?? -1;
    } else {
      return 0;
    }

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

export const useFinalScoresMatrix = () => {
  const [employees, setEmployees] = useState([]);
  const [criteriaList, setCriteriaList] = useState([]);
  const [period, setPeriod] = useState(null);
  const [campaignActive, setCampaignActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const [sorting, setSortingState] = useState(initialSorting);

  // Загрузка данных
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Загружаем матрицу оценок, коэффициенты критериев и грейды параллельно.
      // allSettled, а не all: нужен точный список того, что не загрузилось.
      const [matrixResult, coefficientsResult, usersDataResult] = await Promise.allSettled([
        apiClient.get(API_ENDPOINTS.ADMIN_EVALUATIONS_MATRIX),
        apiClient.get(API_ENDPOINTS.SCORE_COEFFICIENTS),
        apiClient.get(API_ENDPOINTS.ADMIN_USERS_DATA)
      ]);
      
      // Ни один из трёх запросов не имеет безопасного значения по умолчанию:
      // отсутствие коэффициентов даёт невзвешенные баллы, отсутствие грейдов —
      // коэффициент грейда 1.00 для всех. Обе подмены неотличимы от правды.
      const failures = [];
      if (matrixResult.status === 'rejected') {
        logger.error('Матрица оценок не загружена:', matrixResult.reason);
        failures.push(LOAD_ERRORS.matrix);
      }
      if (coefficientsResult.status === 'rejected') {
        logger.error('Коэффициенты критериев не загружены:', coefficientsResult.reason);
        failures.push(LOAD_ERRORS.coefficients);
      }
      if (usersDataResult.status === 'rejected') {
        logger.error('Коэффициенты грейдов не загружены:', usersDataResult.reason);
        failures.push(LOAD_ERRORS.grades);
      }
      if (failures.length > 0) {
        setEmployees([]);
        setCriteriaList([]);
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
      
      // Создаем карту коэффициентов критериев для быстрого доступа
      const coefficientsMap = {};
      coefficients.forEach(c => {
        coefficientsMap[c.id] = c;
      });
      
      // Создаем карту коэффициентов грейдов по коду грейда
      const gradesMap = {};
      gradesData.forEach(g => {
        gradesMap[g.code] = parseFloat(g.coefficient) || 1.0;
      });
      logger.log('Grades map:', gradesMap);
      
      // Колонки — объединение критериев ВСЕХ строк (BUG-051, вторая половина).
      // Раньше заголовок брался из rawEmployees[0], а сервер отдаёт каждой
      // строке только применимые ей критерии: снять «участник проекта» с
      // первого по алфавиту человека — и проектные колонки исчезали у всех,
      // при том что weightedSum продолжал их считать.
      const criteriaFromData = buildSharedCriteriaList(rawEmployees).map(c => ({
        id: c.criteria_id,
        title: c.criteria_title,
        weight: coefficientsMap[c.criteria_id]?.weight || 1.0,
        score_coefficients: coefficientsMap[c.criteria_id]?.score_coefficients || {}
      }));
      setCriteriaList(criteriaFromData);
      
      // Рассчитываем баллы для каждого сотрудника
      const employeesWithScores = rawEmployees.map(emp => {
        const criteriaScores = {};    // Взвешенные баллы по критериям
        const criteriaRawScores = {}; // Сырые 1–10 — только для окраски и подсказок
        const criteriaById = {};      // Применимые критерии этой строки
        let weightedSum = 0;          // Сумма взвешенных баллов
        
        if (emp.criteria && Array.isArray(emp.criteria)) {
          emp.criteria.forEach(crit => {
            criteriaById[crit.criteria_id] = crit;
            const rawScore = getCriterionFinalScore(crit);
            if (rawScore !== null) {
              const weightedScore = calculateCriterionScore(
                rawScore, 
                crit.criteria_id, 
                coefficientsMap
              );
              criteriaScores[crit.criteria_id] = weightedScore;
              criteriaRawScores[crit.criteria_id] = rawScore;
              weightedSum += weightedScore || 0;
            }
          });
        }
        
        // Коэффициент грейда по коду грейда сотрудника. Подстановка 1.0 при
        // отсутствующем грейде остаётся (иначе строка исчезнет из расчёта
        // молча), но теперь она ПОМЕЧЕНА: экран, который отказывается рисовать
        // числа при упавшем справочнике грейдов (BUG-030), не имеет права
        // тихо подставлять множитель одному человеку.
        const gradeCode = emp.grade_code || emp.grade;
        const gradeCoefficient = gradesMap[gradeCode] || 1.0;
        const gradeResolved = Boolean(gradeCode) && gradesMap[gradeCode] !== undefined;
        const finalWeightedScore = weightedSum * gradeCoefficient;
        
        return {
          ...emp,
          criteria_scores: criteriaScores,
          criteria_raw_scores: criteriaRawScores,
          criteria_by_id: criteriaById,
          weighted_sum: weightedSum,
          final_weighted_score: finalWeightedScore,
          grade_coefficient: gradeCoefficient,
          grade_resolved: gradeResolved,
          takes_bonus_share: takesBonusShare(emp)
        };
      });
      
      setEmployees(employeesWithScores);
    } catch (err) {
      logger.error('Ошибка загрузки:', err);
      setEmployees([]);
      setCriteriaList([]);
      setPeriod(null);
      setCampaignActive(false);
      setError(LOAD_ERRORS.matrix);
    } finally {
      setLoading(false);
    }
  }, []);

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

  // Итоговые суммы.
  //
  // ИТОГО и «средний итог» считаются ТОЛЬКО по людям, которые берут долю фонда
  // этого периода (D-0825-14): выведенные из охвата и те, кого не оценивает
  // никто, остаются видимыми строками — это диагностический экран, а не
  // платёжная ведомость, — но в сумму и в среднее не входят. До 2026-08-25 они
  // входили, и «Сотрудников: 88» читалось как размер премиального пула, при
  // том что охват периода в тот момент был 84.
  const totals = useMemo(() => {
    const criteriaSums = {};
    criteriaList.forEach(c => {
      criteriaSums[c.id] = 0;
    });
    
    let totalWeightedSum = 0;
    let totalWeightedScore = 0;
    let poolCount = 0;
    
    filteredEmployees.forEach(emp => {
      if (emp.takes_bonus_share === false) return;
      poolCount += 1;
      Object.entries(emp.criteria_scores || {}).forEach(([criteriaId, score]) => {
        if (criteriaSums[criteriaId] !== undefined && score !== null) {
          criteriaSums[criteriaId] += score;
        }
      });
      
      totalWeightedSum += emp.weighted_sum || 0;
      totalWeightedScore += emp.final_weighted_score || 0;
    });
    
    const employeesCount = filteredEmployees.length;
    
    return {
      employeesCount,
      poolCount,
      excludedCount: employeesCount - poolCount,
      criteriaSums,
      totalWeightedSum,
      totalWeightedScore,
      averageWeightedScore: poolCount > 0 
        ? (totalWeightedScore / poolCount).toFixed(2)
        : '0.00'
    };
  }, [filteredEmployees, criteriaList]);

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
        if (prev.direction === 'desc') {
          return { field, direction: 'asc' };
        } else {
          return initialSorting;
        }
      }
      return { field, direction: 'desc' };
    });
  }, []);

  // Количество активных фильтров
  const activeFiltersCount = useMemo(() => {
    return Object.values(filters).filter(v => v !== '').length;
  }, [filters]);

  return {
    employees,
    criteriaList,
    period,
    campaignActive,
    loading,
    error,
    filters,
    filterOptions,
    filteredEmployees,
    sorting,
    totals,
    activeFiltersCount,
    setFilters: handleFilterChange,
    clearFilters,
    setSorting,
    fetchData
  };
};

export default useFinalScoresMatrix;

