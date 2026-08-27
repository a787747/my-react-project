/**
 * AdminPeerRecognition — чтение отметок «Отметить коллегу»
 * (brief PEER_RECOGNITION, 2026-08-27)
 *
 * Назначение: показать admin и c_level, кто кого отметил и что написал.
 * Доступ: ReportingRoute (admin + c_level). Сервер отказывает по роли: HR,
 * менеджер и обычный сотрудник получают 403 ROLE_FORBIDDEN на
 * GET /api/recognition/list — маршрут защищён guard'ом, а не тем, что пункт
 * меню кому-то не показан.
 *
 * Отмеченный человек своей отметки не видит, и его руководитель тоже: ни один
 * маршрут, кроме этого, отметок не отдаёт, а этот пускает только две роли.
 *
 * Чего на экране нет и не должно появиться: КОЛИЧЕСТВА отметок. Ни общего
 * числа, ни числа по человеку, ни бейджа, ни сортировки по частоте, ни
 * выгрузки со столбцом-счётчиком. Список идёт строго по времени, новые сверху.
 * Как только на экране появляется счётчик, это конкурс популярности — ровно то,
 * ради предотвращения чего вся конструкция и сделана.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { HeartHandshake, AlertCircle } from 'lucide-react';

import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { LoadingSpinner } from '../components/common';
import logger from '../utils/logger';

const unwrap = (payload) => (Array.isArray(payload) ? payload[0] || {} : payload || {});

const formatMoment = (value) => {
  if (!value) return '';
  // Сервер отдаёт «YYYY-MM-DDTHH:MM:SSZ» текстом, собранным в SQL (BUG-031).
  return String(value).replace('T', ' ').replace('Z', ' UTC');
};

const AdminPeerRecognition = () => {
  const [recognitions, setRecognitions] = useState([]);
  const [periodName, setPeriodName] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.get(API_ENDPOINTS.RECOGNITION_LIST);
      const body = unwrap(res.data);
      setRecognitions(Array.isArray(body.recognitions) ? body.recognitions : []);
      setPeriodName(body.period_name || null);
    } catch (err) {
      logger.error('AdminPeerRecognition: не удалось загрузить отметки', err);
      const body = unwrap(err.response?.data);
      // Отказ обязан назвать причину, а не оставить пустую страницу (BUG-042).
      setError(body.message || err.userMessage || 'Не удалось загрузить отметки');
      setRecognitions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center">
              <HeartHandshake className="w-5 h-5 text-brand-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Отметки коллег</h1>
          </div>
          <p className="text-gray-600 text-sm">
            Помощь, которую сотрудники отметили друг у друга{periodName ? ` за период ${periodName}` : ''}.
            Это не оценка и не рейтинг: отметки не считаются, ни на что не влияют и не входят ни в
            один расчёт. Отмеченный человек и его руководитель их не видят.
          </p>
        </div>

        {loading && <LoadingSpinner text="Загрузка..." />}

        {!loading && error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
            <p className="text-danger-800 text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && recognitions.length === 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-500 text-sm">
            Пока никто никого не отметил.
          </div>
        )}

        {!loading && !error && recognitions.length > 0 && (
          <div className="space-y-4">
            {recognitions.map((item) => (
              <article
                key={item.id}
                className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm"
              >
                <header className="mb-3 pb-3 border-b border-gray-100">
                  <div className="text-sm text-gray-900">
                    <strong>{item.author_name}</strong>
                    <span className="text-gray-500"> отметил(а) </span>
                    <strong>{item.nominee_name}</strong>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {[item.author_department, item.nominee_department].filter(Boolean).length > 0 && (
                      <span>
                        {item.author_department || '—'} → {item.nominee_department || '—'} ·{' '}
                      </span>
                    )}
                    {formatMoment(item.created_at)}
                    {item.updated_at && item.updated_at !== item.created_at
                      ? ` · изменено ${formatMoment(item.updated_at)}`
                      : ''}
                  </div>
                </header>
                <dl className="space-y-3 text-sm">
                  <div>
                    <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      В какой ситуации это было?
                    </dt>
                    <dd className="text-gray-800 whitespace-pre-wrap">{item.situation}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Что конкретно он или она сделал(а)?
                    </dt>
                    <dd className="text-gray-800 whitespace-pre-wrap">{item.action}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Что изменилось благодаря этому?
                    </dt>
                    <dd className="text-gray-800 whitespace-pre-wrap">{item.outcome}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPeerRecognition;
