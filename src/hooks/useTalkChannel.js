import { useCallback, useEffect, useState } from 'react';

import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

const unwrap = (payload) => (Array.isArray(payload) ? payload[0] || {} : payload || {});

export const useTalkChannel = (user) => {
  const [wave, setWave] = useState(null);
  const [topics, setTopics] = useState([]);
  const [counterparts, setCounterparts] = useState([]);
  const [myResponse, setMyResponse] = useState(null);
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
      const response = await apiClient.get(API_ENDPOINTS.TALK_FORM);
      const body = unwrap(response.data);
      setWave(body.wave || null);
      setTopics(Array.isArray(body.topics) ? body.topics : []);
      setCounterparts(Array.isArray(body.counterparts) ? body.counterparts : []);
      setMyResponse(body.my_response || null);
    } catch (err) {
      logger.error('useTalkChannel: failed to load', err);
      const body = unwrap(err.response?.data);
      setError(body.message || err.userMessage || 'Не удалось загрузить страницу');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const save = useCallback(async (payload) => {
    try {
      setSaving(true);
      const response = await apiClient.post(API_ENDPOINTS.TALK_SAVE, payload);
      const body = unwrap(response.data);
      await refresh();
      return { ok: true, message: body.message || 'Ответ получен' };
    } catch (err) {
      const body = unwrap(err.response?.data);
      logger.error('useTalkChannel: failed to save', err);
      return { ok: false, message: body.message || err.userMessage || 'Не удалось сохранить ответ' };
    } finally {
      setSaving(false);
    }
  }, [refresh]);

  const withdraw = useCallback(async () => {
    try {
      setWithdrawing(true);
      const response = await apiClient.post(API_ENDPOINTS.TALK_WITHDRAW);
      const body = unwrap(response.data);
      await refresh();
      return { ok: true, message: body.message || 'Ответ снят' };
    } catch (err) {
      const body = unwrap(err.response?.data);
      logger.error('useTalkChannel: failed to withdraw', err);
      return { ok: false, message: body.message || err.userMessage || 'Не удалось снять ответ' };
    } finally {
      setWithdrawing(false);
    }
  }, [refresh]);

  return {
    wave,
    topics,
    counterparts,
    myResponse,
    loading,
    saving,
    withdrawing,
    error,
    save,
    withdraw,
    refresh,
  };
};

export default useTalkChannel;
