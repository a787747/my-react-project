/**
 * useTeamRoster - список подчинённых текущего пользователя
 *
 * Назначение: единственный источник «моей команды» для менеджера.
 * Используется в: TeamView
 *
 * Читает `GET /api/employees` — маршрут, охват которого сервер считает сам:
 * прямые подчинённые актора, только те, кто в охвате активного периода
 * (`evaluation_period_participants.is_in_scope = true`), и только пока кампания
 * идёт. Уволенный сотрудник получает `is_in_scope=false` c причиной
 * `terminated` (D-0825-7) и в ответе не появляется — фильтровать его на клиенте
 * не нужно и нечем: строка просто не приходит.
 *
 * До нажатия «Запустить оценку» (D-0822-1) `active_period` пуст, а `scoped`
 * присоединяет его через `JOIN active_period ap ON true`, поэтому список пуст
 * у всех. Это не ошибка, и страница обязана сказать об этом словами —
 * отсюда `campaignActive` / `periodInPreparation` / `periodName` в ответе.
 *
 * Раньше страница брала список из `GET /api/admin-users-data` (BUG-012) —
 * маршрута с guard `required_roles: ["admin"]`. Менеджер получал 403, список
 * оставался пустым, и «Список команды» в меню не работал ни разу.
 *
 * Возвращает:
 * - employees: массив прямых подчинённых (в охвате, кампания идёт)
 * - outOfScopeEmployees: прямые подчинённые, которые РАБОТАЮТ, но выведены из
 *   охвата этого периода (D-0825-11). Уволенных в этом массиве нет никогда —
 *   их сервер не отдаёт, и увольнение остаётся исчезновением.
 * - campaignActive / periodInPreparation / periodName: состояние периода
 * - actorIsInScope: false, если сам актор выведен из охвата
 * - loading / error
 */

import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

// n8n иногда отдаёт тело как объект, иногда как массив из одного элемента —
// та же защита, что в useDashboardData.
const unwrap = (payload) => (Array.isArray(payload) ? payload[0] || {} : payload || {});

export const useTeamRoster = (user) => {
  const [employees, setEmployees] = useState([]);
  // D-0825-11: employed people out of THIS period's scope. A separate array on
  // purpose — they are not tasks and must never reach the counters.
  const [outOfScopeEmployees, setOutOfScopeEmployees] = useState([]);
  const [campaignActive, setCampaignActive] = useState(false);
  const [periodInPreparation, setPeriodInPreparation] = useState(false);
  const [periodName, setPeriodName] = useState(null);
  const [actorIsInScope, setActorIsInScope] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTeam = useCallback(async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const res = await apiClient.get(API_ENDPOINTS.EMPLOYEES, {
        params: { user_id: user.id, role: user.role }
      });

      const body = unwrap(res.data);
      const rows = Array.isArray(body.data) ? body.data : [];

      setEmployees(rows.filter((row) => row.id !== user.id));
      const outOfScopeRows = Array.isArray(body.out_of_scope_data) ? body.out_of_scope_data : [];
      setOutOfScopeEmployees(outOfScopeRows.filter((row) => row.id !== user.id));
      setCampaignActive(body.campaign_active === true);
      setPeriodInPreparation(body.period_in_preparation === true);
      setPeriodName(body.period_name || null);
      setActorIsInScope(
        body.actor_is_in_scope === null || body.actor_is_in_scope === undefined
          ? null
          : body.actor_is_in_scope === true
      );
    } catch (err) {
      logger.error('Ошибка загрузки команды:', err);
      setEmployees([]);
      setOutOfScopeEmployees([]);
      setError(err.userMessage || 'Не удалось загрузить список команды');
    } finally {
      setLoading(false);
    }
  }, [user?.id, user?.role]);

  useEffect(() => {
    fetchTeam();
  }, [fetchTeam]);

  return {
    employees,
    outOfScopeEmployees,
    campaignActive,
    periodInPreparation,
    periodName,
    actorIsInScope,
    loading,
    error,
    refetch: fetchTeam
  };
};

export default useTeamRoster;
