import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, MessageCircle } from 'lucide-react';

import apiClient from '../api/client';
import { LoadingSpinner } from '../components/common';
import { API_ENDPOINTS } from '../config/api';
import { TALK_COPY } from '../content/talkCopy';
import logger from '../utils/logger';

const unwrap = (payload) => (Array.isArray(payload) ? payload[0] || {} : payload || {});

const counterpartText = (item) => {
  if (item.counterpart_mode === 'help_choose') {
    return TALK_COPY.specialCounterparts.help_choose;
  }
  if (item.counterpart_mode === 'all_leadership') {
    return TALK_COPY.specialCounterparts.all_leadership;
  }
  return (item.counterparts || []).map((person) => person.full_name).join(', ') || '—';
};

const AdminTalkChannel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(API_ENDPOINTS.TALK_LIST);
      setData(unwrap(response.data));
    } catch (err) {
      logger.error('AdminTalkChannel: failed to load', err);
      const body = unwrap(err.response?.data);
      setError(body.message || err.userMessage || 'Не удалось загрузить ответы');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingSpinner text="Загрузка..." />;

  const counts = data?.counts || {};
  const cards = [
    ['Всё в порядке', counts.all_good],
    ['Тема без встречи', counts.topic_only],
    ['Нужен разговор', counts.conversation],
    ['Зарегистрированы, не ответили', counts.registered_unanswered],
    ['Никогда не регистрировались', counts.never_registered],
  ];

  return (
    <div className="min-h-screen bg-surface-raised p-4 lg:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-brand-100 flex items-center justify-center">
            <MessageCircle className="w-6 h-6 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Поговорить с руководством — ответы</h1>
            <p className="text-sm text-slate-500">
              Работающих сотрудников: {counts.employed ?? '—'}
            </p>
          </div>
        </header>

        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4 flex gap-3">
            <AlertCircle className="w-5 h-5 text-danger-600 shrink-0" />
            <p className="text-danger-800">{error}</p>
          </div>
        )}

        {!error && (
          <>
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {cards.map(([label, value]) => (
                <div key={label} className="card p-4">
                  <div className="text-2xl font-bold text-slate-900">{value ?? 0}</div>
                  <div className="text-xs text-slate-500 mt-1">{label}</div>
                </div>
              ))}
            </section>

            <section className="card p-5">
              <h2 className="text-lg font-bold text-slate-900 mb-4">Темы</h2>
              <div className="space-y-2">
                {(data?.topics || []).map((topic) => (
                  <div key={topic.topic_key} className="flex justify-between gap-4 text-sm border-b py-2">
                    <span>{topic.label}</span>
                    <strong>{topic.response_count}</strong>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-3">
              <h2 className="text-lg font-bold text-slate-900">Ответы</h2>
              {(data?.responses || []).length === 0 && (
                <div className="card p-8 text-center text-slate-500">Ответов пока нет.</div>
              )}
              {(data?.responses || []).map((item) => (
                <article key={item.responder_id} className="card p-5">
                  <header className="flex justify-between gap-4 border-b pb-3 mb-3">
                    <div>
                      <strong>{item.responder_name}</strong>
                      <div className="text-sm text-slate-600">{item.answer_label}</div>
                    </div>
                    <time className="text-xs text-slate-400">{item.updated_at}</time>
                  </header>
                  {item.topic_label && (
                    <p className="text-sm mb-2"><strong>Тема:</strong> {item.topic_label}</p>
                  )}
                  {item.answer_key === 'conversation' && (
                    <dl className="text-sm space-y-2">
                      <div><dt className="font-semibold inline">С кем: </dt><dd className="inline">{counterpartText(item)}</dd></div>
                      <div><dt className="font-semibold inline">Срочность: </dt><dd className="inline">{item.urgency_label}</dd></div>
                      <div><dt className="font-semibold inline">Групповой формат: </dt><dd className="inline">{item.group_readiness_label}</dd></div>
                    </dl>
                  )}
                </article>
              ))}
            </section>
          </>
        )}
      </div>
    </div>
  );
};

export default AdminTalkChannel;
