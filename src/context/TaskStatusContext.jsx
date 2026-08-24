/**
 * TaskStatusContext - Контекст для отслеживания статусов задач оценки
 * 
 * Назначение: Централизованное хранение и обновление статусов задач
 * Используется в: Sidebar, Welcome, SelfReview, ManagerEvaluation, Dashboard
 * 
 * Предоставляет:
 * - campaignActive: boolean - период активен И оценка запущена (D-0822-1)
 * - periodInPreparation: boolean - период активен, но оценка ещё не запущена
 * - hasSelfReview: boolean - выполнена ли самооценка
 * - hasEvaluatedManager: boolean - оценён ли руководитель
 * - hasEvaluatedAllSubordinates: boolean - оценены ли все подчинённые
 * - hasSubordinates: boolean - есть ли подчинённые
 * - hasManager: boolean - есть ли руководитель
 * - isManagerCLevel: boolean - является ли руководитель C-level
 * - loading: boolean - статус загрузки
 * - refreshTaskStatus: function - обновить все статусы
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useUser } from './UserContext';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { ADMIN_ROLES } from '../config/constants';
import logger from '../utils/logger';
import { extractPeriodMeta } from '../utils/periodNotice';

const TaskStatusContext = createContext(null);

export const TaskStatusProvider = ({ children }) => {
  const { user } = useUser();
  
  const [hasSelfReview, setHasSelfReview] = useState(false);
  const [hasEvaluatedManager, setHasEvaluatedManager] = useState(false);
  const [hasEvaluatedAllSubordinates, setHasEvaluatedAllSubordinates] = useState(false);
  const [hasSubordinates, setHasSubordinates] = useState(false);
  const [hasManager, setHasManager] = useState(false);
  const [isManagerCLevel, setIsManagerCLevel] = useState(false);
  const [isOutOfScope, setIsOutOfScope] = useState(false);
  const [campaignActive, setCampaignActive] = useState(false);
  const [periodInPreparation, setPeriodInPreparation] = useState(false);
  const [periodName, setPeriodName] = useState(null);
  const [periodStart, setPeriodStart] = useState(null);
  const [periodEnd, setPeriodEnd] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // C-level не нужна самооценка.
  // Задачи существуют только когда кампания идёт: период активен И оценка
  // запущена (D-0822-1). В окне подготовки сервер не отдаёт ни одного флага.
  const isCLevel = user?.role === 'c_level';
  const needsSelfReview = campaignActive && !isCLevel && !isOutOfScope;

  // Загрузка всех статусов
  const refreshTaskStatus = useCallback(async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);

      // Параллельно загружаем все данные для ускорения
      const [selfReviewRes, managerRes, employeesRes] = await Promise.all([
        apiClient.get(`${API_ENDPOINTS.CHECK_SELF_REVIEWS}?user_id=${user.id}`)
          .catch(() => ({ data: {} })),
        apiClient.get(API_ENDPOINTS.GET_MY_MANAGER, { params: { user_id: user.id } })
          .catch(() => ({ data: {} })),
        apiClient.get(API_ENDPOINTS.EMPLOYEES, { params: { user_id: user.id, role: user.role } })
          .catch(() => ({ data: {} }))
      ]);

      const employeesPayload = employeesRes.data || {};
      const campaignRunning = employeesPayload.campaign_active === true
        || employeesPayload[0]?.campaign_active === true;
      setCampaignActive(campaignRunning);
      setPeriodInPreparation(
        employeesPayload.period_in_preparation === true
        || employeesPayload[0]?.period_in_preparation === true
      );
      const periodMeta = extractPeriodMeta(employeesPayload);
      setPeriodName(periodMeta.periodName);
      setPeriodStart(periodMeta.startDate);
      setPeriodEnd(periodMeta.endDate);
      const actorOutOfScope = employeesPayload.actor_is_in_scope === false;
      setIsOutOfScope(actorOutOfScope);
      if (actorOutOfScope || !campaignRunning) {
        setHasSelfReview(false);
        setHasEvaluatedManager(false);
        setHasEvaluatedAllSubordinates(true);
        setHasSubordinates(false);
        setHasManager(false);
        setIsManagerCLevel(false);
        return;
      }

      // 1. Обрабатываем самооценку
      setHasSelfReview(selfReviewRes.data?.has_self_review || false);

      // 2. Обрабатываем менеджера
      const managerData = managerRes.data;
      if (managerData?.has_manager && managerData?.manager) {
        setHasManager(true);
        // C-level и Admin не оцениваются подчинёнными
        setIsManagerCLevel(ADMIN_ROLES.includes(managerData.manager.role));
        setHasEvaluatedManager(managerData.manager.has_evaluated_manager || false);
      } else {
        setHasManager(false);
        setIsManagerCLevel(false);
        setHasEvaluatedManager(false);
      }

      // 3. Обрабатываем подчинённых
      const employeesData = Array.isArray(employeesPayload)
        ? employeesPayload[0]?.data || []
        : employeesPayload.data || [];

      const subordinates = employeesData.filter(emp => emp.id !== user.id);
      const hasCampaignSubs = campaignRunning && subordinates.length > 0;
      setHasSubordinates(hasCampaignSubs);

      // Campaign task status uses in-scope subordinates only, not the org-tree flag.
      // evaluated_by_actor is per-criterion since D-0822-3: an evaluation that
      // no longer covers every currently-applicable criterion (after a
      // project/general switch) reopens the task here and on the dashboard.
      if (!campaignRunning || subordinates.length === 0) {
        setHasEvaluatedAllSubordinates(true);
      } else {
        const allEvaluated = subordinates.every(sub => sub.evaluated_by_actor === true);
        setHasEvaluatedAllSubordinates(allEvaluated);
      }

    } catch (error) {
      logger.error('Ошибка загрузки статусов задач:', error);
    } finally {
      setLoading(false);
    }
  }, [user?.id, user?.role]);

  // Загружаем при монтировании и смене пользователя
  useEffect(() => {
    refreshTaskStatus();
  }, [refreshTaskStatus]);

  const value = {
    campaignActive,
    periodInPreparation,
    periodName,
    periodStart,
    periodEnd,
    hasSelfReview,
    hasEvaluatedManager,
    hasEvaluatedAllSubordinates,
    hasSubordinates,
    hasManager,
    isManagerCLevel,
    isOutOfScope,
    isCLevel,
    needsSelfReview,
    loading,
    refreshTaskStatus
  };

  return (
    <TaskStatusContext.Provider value={value}>
      {children}
    </TaskStatusContext.Provider>
  );
};

export const useTaskStatus = () => {
  const context = useContext(TaskStatusContext);
  if (!context) {
    // Возвращаем дефолтные значения если контекст не найден
    return {
      campaignActive: false,
      periodInPreparation: false,
      periodName: null,
      periodStart: null,
      periodEnd: null,
      hasSelfReview: false,
      hasEvaluatedManager: false,
      hasEvaluatedAllSubordinates: false,
      hasSubordinates: false,
      hasManager: false,
      isManagerCLevel: false,
      isOutOfScope: false,
      isCLevel: false,
      needsSelfReview: false,
      loading: true,
      refreshTaskStatus: () => {}
    };
  }
  return context;
};

export default TaskStatusContext;

