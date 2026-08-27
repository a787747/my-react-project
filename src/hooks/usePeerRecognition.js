/**
 * usePeerRecognition — данные страницы «Отметить коллегу»
 *
 * Назначение: единственный источник данных для PeerRecognition.
 * Используется в: pages/PeerRecognition
 *
 * Читает `GET /api/recognition/form` — один запрос на всю страницу. Сервер
 * возвращает период, собственную отметку автора (если она есть) и два списка:
 * `colleagues` — кого отметить можно, `blocked` — кого нельзя, с причиной
 * словами. Списки строит сервер, а не клиент: те же три отказа (себя, своего
 * руководителя, своего подчинённого) и уволенные проверяются заново в
 * `POST /api/recognition/save`, поэтому прямой вызов маршрута с чужим
 * `nominee_id` отказывает ровно так же, как экран. Снятие — `POST
 * /api/recognition/withdraw` — удаляет собственную строку автора; чужую
 * сервер отказывает, закрытый период тоже.
 *
 * Чего здесь нет и не должно появиться: любого счётчика отметок. Ни общего
 * числа, ни числа по человеку, ни сортировки по частоте. Маршрут их не отдаёт,
 * и вычислять их на клиенте нельзя — это ровно то, что превратило бы страницу
 * в рейтинг популярности.
 *
 * Возвращает:
 * - period: { id, name, start_date, end_date } | null (null = открытого периода нет)
 * - colleagues: [{ id, full_name, job_title, department_name }]
 * - blocked: то же + { blocked_reason, message }
 * - myNomination: { id, nominee_id, nominee_name, situation, action, outcome, updated_at } | null
 * - loading / error / saving / withdrawing
 * - save(payload) / withdraw({ recognitionId }) / refresh()
 */

import { useCallback, useEffect, useState } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

// n8n иногда отдаёт тело как объект, иногда как массив из одного элемента —
// та же защита, что в useTeamRoster / useDashboardData.
const unwrap = (payload) => (Array.isArray(payload) ? payload[0] || {} : payload || {});

export const usePeerRecognition = (user) => {
  const [period, setPeriod] = useState(null);
  const [colleagues, setColleagues] = useState([]);
  const [blocked, setBlocked] = useState([]);
  const [myNomination, setMyNomination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.get(API_ENDPOINTS.RECOGNITION_FORM);
      const body = unwrap(res.data);
      setPeriod(body.period || null);
      setColleagues(Array.isArray(body.colleagues) ? body.colleagues : []);
      setBlocked(Array.isArray(body.blocked) ? body.blocked : []);
      setMyNomination(body.my_nomination || null);
    } catch (err) {
      logger.error('usePeerRecognition: не удалось загрузить страницу', err);
      // Экран обязан назвать причину, а не остаться пустым (BUG-042).
      setError(err.userMessage || 'Не удалось загрузить страницу');
      setColleagues([]);
      setBlocked([]);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  /**
   * Сохранить или заменить отметку. Возвращает { ok, message } —
   * страница показывает сообщение сервера, а не своё собственное: отказ
   * «своего руководителя отметить нельзя» написан владельцем и живёт на
   * сервере в одном экземпляре.
   */
  const save = useCallback(async ({ nomineeId, situation, action, outcome }) => {
    try {
      setSaving(true);
      const res = await apiClient.post(API_ENDPOINTS.RECOGNITION_SAVE, {
        nominee_id: nomineeId,
        situation,
        action,
        outcome
      });
      const body = unwrap(res.data);
      await refresh();
      return { ok: true, message: body.message || 'Отметка сохранена' };
    } catch (err) {
      const body = unwrap(err.response?.data);
      logger.error('usePeerRecognition: не удалось сохранить отметку', err);
      return {
        ok: false,
        message: body.message || err.userMessage || 'Не удалось сохранить отметку'
      };
    } finally {
      setSaving(false);
    }
  }, [refresh]);

  /**
   * Снять собственную отметку. Сервер удаляет строку по identity из токена
   * и по id отметки; чужую отметку отказывает, закрытый период — тоже.
   */
  const withdraw = useCallback(async ({ recognitionId }) => {
    try {
      setWithdrawing(true);
      const res = await apiClient.post(API_ENDPOINTS.RECOGNITION_WITHDRAW, {
        recognition_id: recognitionId
      });
      const body = unwrap(res.data);
      await refresh();
      return { ok: true, message: body.message || 'Отметка снята' };
    } catch (err) {
      const body = unwrap(err.response?.data);
      logger.error('usePeerRecognition: не удалось снять отметку', err);
      return {
        ok: false,
        message: body.message || err.userMessage || 'Не удалось снять отметку'
      };
    } finally {
      setWithdrawing(false);
    }
  }, [refresh]);

  return {
    period,
    colleagues,
    blocked,
    myNomination,
    loading,
    saving,
    withdrawing,
    error,
    save,
    withdraw,
    refresh
  };
};

export default usePeerRecognition;
