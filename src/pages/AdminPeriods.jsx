/**
 * AdminPeriods - Страница управления периодами оценки и регистрацией
 *
 * Назначение: Создание, активация, переименование, закрытие периодов,
 *             привязка периодов к контейнерам (Annual → H1/H2).
 *             Получение постоянной ссылки для регистрации сотрудников.
 * Доступ: admin, c_level, hr (просмотр); действия — только admin.
 *         Переименование, привязка, активация и закрытие рисуются только
 *         админу (сервер и так отвечает 403): необратимую кнопку не показывают
 *         тому, кому её нажимать нельзя.
 *
 * Контейнер = период с дочерними периодами. Контейнеры не активируются
 * (кнопки нет; API отвечает 422) и не закрываются — закрываются их дочерние
 * периоды. Закрытие периода фиксирует результаты (period_results) навсегда.
 *
 * Три состояния листового периода (D-0822-1):
 *   Неактивен (draft) → Активен, подготовка (оценка не запущена)
 *   → Идёт оценка (запущена) → Закрыт.
 * «Запустить оценку» необратима так же, как активация и закрытие: маршрута,
 * который снимает отметку, нет — откат только SQL на хосте.
 */

import React, { useState, useEffect, useMemo } from 'react';
import apiClient from '../api/client';
import {
  Calendar, Plus, CheckCircle, Circle, Loader2, Save, X, Link2, Copy, Check,
  UserPlus, Pencil, FolderTree, Lock, CornerDownRight, Layers, Hourglass, PlayCircle
} from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';
import handleApiError from '../utils/errorHandler';
import logger from '../utils/logger';
import { isAdmin } from '../utils/permissions';

const isContainer = (period) => Number(period?.child_count) > 0;

/** Оценка запущена — второй шлюз (D-0822-1). */
const isStarted = (period) => Boolean(period?.evaluation_started_at);

/** Родителем может стать период верхнего уровня без оценок и не активный. */
const canBeParent = (period, childId = null) =>
  period &&
  period.id !== childId &&
  !period.parent_period_id &&
  !period.has_evaluations &&
  period.status !== 'active';

/** Плоский список → дерево: контейнер, под ним дети (по возрастанию дат). */
const orderPeriods = (periods) => {
  const byParent = new Map();
  periods.forEach((p) => {
    if (p.parent_period_id) {
      const list = byParent.get(p.parent_period_id) || [];
      list.push(p);
      byParent.set(p.parent_period_id, list);
    }
  });
  const ordered = [];
  const seen = new Set();
  periods.forEach((p) => {
    if (p.parent_period_id) return;
    ordered.push({ ...p, depth: 0 });
    seen.add(p.id);
    (byParent.get(p.id) || [])
      .slice()
      .sort((a, b) => String(a.start_date).localeCompare(String(b.start_date)))
      .forEach((child) => {
        ordered.push({ ...child, depth: 1 });
        seen.add(child.id);
      });
  });
  // Дети с отсутствующим родителем (не должно случаться) — в конец, видимыми.
  periods.forEach((p) => {
    if (!seen.has(p.id)) ordered.push({ ...p, depth: 0 });
  });
  return ordered;
};

const AdminPeriods = ({ user }) => {
  // Просмотр — admin, c_level, hr; изменения — только admin (API 403 остальным).
  const canManage = isAdmin(user?.role);

  const [periods, setPeriods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(null);
  const [starting, setStarting] = useState(null);
  const [closing, setClosing] = useState(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    start_date: '',
    end_date: '',
    period_type: 'half_year',
    parent_period_id: ''
  });

  // Rename modal
  const [renameModal, setRenameModal] = useState({ open: false, period: null, name: '' });
  const [renaming, setRenaming] = useState(false);

  // Reparent modal
  const [reparentModal, setReparentModal] = useState({ open: false, period: null, parentId: '' });
  const [reparenting, setReparenting] = useState(false);

  // Close modal: закрытие необратимо, поэтому подтверждение — ввод названия
  const [closeModal, setCloseModal] = useState({ open: false, period: null, typed: '' });

  // Invite token states
  const [generatingInvite, setGeneratingInvite] = useState(false);
  const [inviteLink, setInviteLink] = useState(null);
  const [copied, setCopied] = useState(false);
  const [inviteError, setInviteError] = useState('');

  useEffect(() => {
    fetchPeriods();
  }, []);

  const fetchPeriods = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(API_ENDPOINTS.PERIODS);
      const data = response.data.data || [];
      setPeriods(data);
    } catch (error) {
      logger.error('Ошибка загрузки периодов:', error);
    } finally {
      setLoading(false);
    }
  };

  const orderedPeriods = useMemo(() => orderPeriods(periods), [periods]);
  const eligibleParents = useMemo(
    () => periods.filter((p) => canBeParent(p)),
    [periods]
  );

  const handleActivate = async (periodId) => {
    const period = periods.find((item) => item.id === periodId);
    if (!period || period.status === 'closed' || isContainer(period)) {
      return;
    }

    if (!window.confirm('Активировать этот период? Текущий активный период будет деактивирован.')) {
      return;
    }

    try {
      setActivating(periodId);
      await apiClient.post(API_ENDPOINTS.PERIODS_ACTIVATE, {
        period_id: periodId
      });
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка активации:', error);
      alert(handleApiError(error));
    } finally {
      setActivating(null);
    }
  };

  /**
   * Запуск оценки — необратим. Отдельное подтверждение, потому что именно
   * этот шаг открывает задачи сотрудникам и замораживает каталог критериев.
   */
  const handleStartEvaluation = async (periodId) => {
    const period = periods.find((item) => item.id === periodId);
    if (!period || !period.is_active || period.status !== 'active'
        || isContainer(period) || isStarted(period)) {
      return;
    }

    if (!window.confirm(
      'Запустить оценку в этом периоде?\n\n'
      + 'Сотрудники сразу увидят задачи и смогут отправлять оценки. '
      + 'Каталог критериев будет заморожен. Отменить запуск нельзя.'
    )) {
      return;
    }

    try {
      setStarting(periodId);
      const response = await apiClient.post(API_ENDPOINTS.PERIODS_START_EVALUATION, {
        period_id: periodId
      });
      const body = response.data || {};
      if (body.already_started) {
        alert(body.message || 'Оценка в этом периоде уже запущена.');
      }
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка запуска оценки:', error);
      alert(handleApiError(error));
    } finally {
      setStarting(null);
    }
  };

  const openCloseModal = (periodId) => {
    const period = periods.find((item) => item.id === periodId);
    if (!period || !period.is_active || isContainer(period)) {
      return;
    }
    setCloseModal({ open: true, period, typed: '' });
  };

  /**
   * Закрытие необратимо: маршрута на переоткрытие нет, period_results никто
   * не переписывает, активация закрытого периода отвечает 422. Единственное
   * восстановление — восстановление базы, поэтому подтверждение — набранное
   * от руки название периода, а не один клик.
   */
  const handleClose = async (e) => {
    e.preventDefault();
    const period = closeModal.period;
    if (!period || closeModal.typed.trim() !== period.name) {
      return;
    }
    const periodId = period.id;
    try {
      setClosing(periodId);
      const response = await apiClient.post(API_ENDPOINTS.PERIODS_CLOSE, { period_id: periodId });
      const body = response.data || {};
      alert(
        body.already_closed
          ? body.message
          : `Период закрыт. Сохранено результатов: ${body.results_stored} (в охвате: ${body.in_scope}, без данных: ${body.no_data}).`
      );
      setCloseModal({ open: false, period: null, typed: '' });
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка закрытия периода:', error);
      alert(handleApiError(error));
    } finally {
      setClosing(null);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();

    try {
      setCreating(true);
      const payload = {
        name: formData.name,
        start_date: formData.start_date,
        end_date: formData.end_date,
        period_type: formData.period_type
      };
      if (formData.parent_period_id) {
        payload.parent_period_id = Number(formData.parent_period_id);
      }
      await apiClient.post(API_ENDPOINTS.PERIODS_CREATE, payload);
      setIsModalOpen(false);
      setFormData({ name: '', start_date: '', end_date: '', period_type: 'half_year', parent_period_id: '' });
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка создания:', error);
      alert(handleApiError(error));
    } finally {
      setCreating(false);
    }
  };

  const handleRename = async (e) => {
    e.preventDefault();
    if (!renameModal.period) return;
    try {
      setRenaming(true);
      await apiClient.post(API_ENDPOINTS.PERIODS_RENAME, {
        period_id: renameModal.period.id,
        name: renameModal.name
      });
      setRenameModal({ open: false, period: null, name: '' });
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка переименования:', error);
      alert(handleApiError(error));
    } finally {
      setRenaming(false);
    }
  };

  const handleReparent = async (e) => {
    e.preventDefault();
    const period = reparentModal.period;
    if (!period) return;
    // Отвязка закрытого периода с сохранёнными результатами не трогает
    // period_results, но выводит их из среднего и суммы контейнера —
    // годовые числа человека изменятся молча, если не сказать об этом.
    const isDetach = !reparentModal.parentId;
    if (isDetach && period.parent_period_id && period.has_results) {
      const parentName = periods.find((item) => item.id === period.parent_period_id)?.name;
      if (!window.confirm(
        `Отвязать «${period.name}» от контейнера${parentName ? ` «${parentName}»` : ''}?\n\n` +
        'У этого периода есть сохранённые результаты. Сами результаты останутся ' +
        'нетронутыми, но они перестанут учитываться в годовой сводке: годовой ' +
        'рейтинг (среднее) и годовой индекс (сумма) участников изменятся.'
      )) {
        return;
      }
    }
    try {
      setReparenting(true);
      await apiClient.post(API_ENDPOINTS.PERIODS_REPARENT, {
        period_id: period.id,
        parent_period_id: reparentModal.parentId ? Number(reparentModal.parentId) : null
      });
      setReparentModal({ open: false, period: null, parentId: '' });
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка привязки:', error);
      alert(handleApiError(error));
    } finally {
      setReparenting(false);
    }
  };

  // Генерация invite токена
  const handleGenerateInvite = async () => {
    if (!user?.id) {
      setInviteError('Ошибка: пользователь не авторизован');
      return;
    }

    try {
      setGeneratingInvite(true);
      setInviteError('');
      setInviteLink(null);

      // Получаем текущий URL для frontend
      const frontendUrl = window.location.origin;

      const response = await apiClient.post(API_ENDPOINTS.CREATE_INVITE, {
        admin_id: user.id,
        frontend_url: frontendUrl
      });

      if (response.data.success) {
        setInviteLink(response.data.data.registration_link);
      } else {
        setInviteError(response.data.message || 'Ошибка получения ссылки');
      }
    } catch (error) {
      logger.error('Ошибка получения invite:', error);
      setInviteError(error.response?.data?.message || 'Не удалось получить ссылку для регистрации');
    } finally {
      setGeneratingInvite(false);
    }
  };

  // Копирование ссылки
  const handleCopyLink = async () => {
    if (!inviteLink) return;

    try {
      await navigator.clipboard.writeText(inviteLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      logger.error('Ошибка копирования:', error);
      // Fallback для старых браузеров
      const textArea = document.createElement('textarea');
      textArea.value = inviteLink;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const renderStatus = (period) => {
    if (isContainer(period)) {
      return (
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-500" />
          <span className="text-sm font-medium text-indigo-600">Контейнер</span>
        </div>
      );
    }
    if (period.is_active) {
      // Активен, но оценка не запущена — окно подготовки (D-0822-1).
      if (!isStarted(period)) {
        return (
          <div className="flex items-center gap-2">
            <Hourglass className="w-5 h-5 text-amber-500" />
            <div>
              <span className="text-sm font-medium text-amber-700">Активен · подготовка</span>
              <p className="text-xs text-amber-600">Оценка не запущена — сотрудники не видят задач</p>
            </div>
          </div>
        );
      }
      return (
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <div>
            <span className="text-sm font-medium text-green-700">Идёт оценка</span>
            <p className="text-xs text-green-600">Запущена {formatDate(period.evaluation_started_at)}</p>
          </div>
        </div>
      );
    }
    if (period.status === 'closed') {
      return (
        <div className="flex items-center gap-2">
          <Lock className="w-5 h-5 text-gray-500" />
          <span className="text-sm text-gray-600">
            Закрыт{period.has_results ? ' · результаты сохранены' : ''}
          </span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2">
        <Circle className="w-5 h-5 text-gray-400" />
        <span className="text-sm text-gray-500">Неактивен</span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Calendar className="w-8 h-8 text-indigo-600" />
            Периоды оценки
          </h1>
          <p className="text-gray-500 mt-2">
            Управление циклами оценки эффективности
          </p>
        </div>
        {canManage && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm font-medium"
          >
            <Plus className="w-5 h-5" />
            Создать период
          </button>
        )}
      </div>

      {/* Карточка генерации ссылки для регистрации */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-8">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <UserPlus className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Регистрация сотрудников</h2>
              <p className="text-sm text-gray-500">
                Получите постоянную ссылку для регистрации и отправьте её сотрудникам
              </p>
            </div>
          </div>
          <button
            onClick={handleGenerateInvite}
            disabled={generatingInvite}
            className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-sm font-medium disabled:opacity-50"
          >
            {generatingInvite ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Загрузка...
              </>
            ) : (
              <>
                <Link2 className="w-4 h-4" />
                Получить ссылку
              </>
            )}
          </button>
        </div>

        {/* Ошибка */}
        {inviteError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {inviteError}
          </div>
        )}

        {/* Сгенерированная ссылка */}
        {inviteLink && (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
            <p className="text-sm font-medium text-emerald-800 mb-2">
              Постоянная ссылка для регистрации:
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={inviteLink}
                className="flex-1 p-2.5 bg-white border border-emerald-300 rounded-lg text-sm text-gray-700 font-mono"
              />
              <button
                onClick={handleCopyLink}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
                  copied
                    ? 'bg-green-600 text-white'
                    : 'bg-white border border-emerald-300 text-emerald-700 hover:bg-emerald-100'
                }`}
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    Скопировано
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    Копировать
                  </>
                )}
              </button>
            </div>
            <p className="text-xs text-emerald-600 mt-2">
              Отправьте эту ссылку на <strong>all@sedamedical.com</strong>.
              Сотрудники смогут зарегистрироваться только если их email уже есть в системе.
            </p>
          </div>
        )}
      </div>

      {/* Список периодов */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {periods.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            <Calendar className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p>Нет созданных периодов оценки</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Статус</th>
                  <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Название</th>
                  <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Начало</th>
                  <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">Окончание</th>
                  <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase">В охвате</th>
                  <th className="px-6 py-4 text-xs font-semibold text-gray-500 uppercase text-right">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {orderedPeriods.map((period) => (
                  <tr
                    key={period.id}
                    className={`hover:bg-gray-50 transition-colors ${
                      period.is_active ? 'bg-green-50/30' : ''
                    } ${isContainer(period) ? 'bg-indigo-50/30' : ''}`}
                  >
                    {/* Статус */}
                    <td className="px-6 py-4">
                      {renderStatus(period)}
                    </td>

                    {/* Название */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {period.depth > 0 && (
                          <CornerDownRight className="w-4 h-4 text-gray-300 shrink-0" />
                        )}
                        <div>
                          <div className="font-semibold text-gray-900">{period.name}</div>
                          {isContainer(period) && (
                            <div className="text-xs text-indigo-500">
                              дочерних периодов: {period.child_count}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Даты */}
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600">{formatDate(period.start_date)}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600">{formatDate(period.end_date)}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-700">
                        {isContainer(period)
                          ? '—'
                          : period.in_scope_count != null
                            ? `${period.in_scope_count}${period.participant_count != null ? ` / ${period.participant_count}` : ''}`
                            : '—'}
                      </div>
                    </td>

                    {/* Действия */}
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2 flex-wrap">
                        {/* Действия рисуются только админу: сервер и так отвечает
                            403, но необратимую кнопку не показывают тому, кому
                            её нажимать нельзя (M1). */}
                        {canManage && (
                          <button
                            onClick={() => setRenameModal({ open: true, period, name: period.name })}
                            className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                            title="Переименовать"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                        )}

                        {canManage && !isContainer(period) && (
                          <button
                            onClick={() => setReparentModal({
                              open: true,
                              period,
                              parentId: period.parent_period_id ? String(period.parent_period_id) : ''
                            })}
                            className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                            title="Привязать к контейнеру / отвязать"
                          >
                            <FolderTree className="w-4 h-4" />
                          </button>
                        )}

                        {/* Контейнеры не активируются: кнопки нет (D-0821-1) */}
                        {canManage && !period.is_active && period.status !== 'closed' && !isContainer(period) && (
                          <button
                            onClick={() => handleActivate(period.id)}
                            disabled={activating === period.id}
                            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                          >
                            {activating === period.id ? (
                              <span className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Активация...
                              </span>
                            ) : (
                              'Активировать'
                            )}
                          </button>
                        )}

                        {/* Второй шлюз: показывается только админу и только
                            активному незапущенному листовому периоду (D-0822-1) */}
                        {canManage && period.is_active && period.status === 'active'
                          && !isContainer(period) && !isStarted(period) && (
                          <button
                            onClick={() => handleStartEvaluation(period.id)}
                            disabled={starting === period.id}
                            className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                            title="Открыть оценку сотрудникам. Необратимо."
                          >
                            {starting === period.id ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Запуск...
                              </>
                            ) : (
                              <>
                                <PlayCircle className="w-4 h-4" />
                                Запустить оценку
                              </>
                            )}
                          </button>
                        )}

                        {period.is_active && !isContainer(period) && (
                          <>
                            <span className={`px-4 py-2 text-sm font-medium rounded-lg ${
                              isStarted(period)
                                ? 'bg-green-100 text-green-700'
                                : 'bg-amber-100 text-amber-700'
                            }`}>
                              {isStarted(period) ? 'Текущий период' : 'Подготовка'}
                            </span>
                            {canManage && (
                            <button
                              onClick={() => openCloseModal(period.id)}
                              disabled={closing === period.id}
                              className="px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 transition-colors disabled:opacity-50"
                              title="Рассчитать и сохранить результаты, закрыть период"
                            >
                              {closing === period.id ? (
                                <span className="flex items-center gap-2">
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  Закрытие...
                                </span>
                              ) : (
                                'Закрыть период'
                              )}
                            </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Модалка создания периода */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
            <form onSubmit={handleCreate}>
              {/* Header */}
              <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">Создать период оценки</h2>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-6 h-6 text-gray-400" />
                </button>
              </div>

              {/* Body */}
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Название периода
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="H2-2026, Annual 2026, etc."
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Тип периода
                  </label>
                  <select
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.period_type}
                    onChange={(e) => setFormData({ ...formData, period_type: e.target.value })}
                  >
                    <option value="half_year">Полугодовой</option>
                    <option value="annual">Годовой</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Дата начала
                  </label>
                  <input
                    type="date"
                    required
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Дата окончания
                  </label>
                  <input
                    type="date"
                    required
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  />
                </div>

                {eligibleParents.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Родительский период (контейнер)
                    </label>
                    <select
                      className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                      value={formData.parent_period_id}
                      onChange={(e) => setFormData({ ...formData, parent_period_id: e.target.value })}
                    >
                      <option value="">— без контейнера —</option>
                      {eligibleParents.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-400 mt-1">
                      Даты нового периода должны лежать внутри дат контейнера.
                    </p>
                  </div>
                )}

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Примечание:</strong> Новый период будет создан в неактивном состоянии.
                    Вы сможете активировать его позже. Контейнер (период с дочерними периодами)
                    активировать нельзя — он служит для годовой сводки.
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md disabled:opacity-50"
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Создание...
                    </>
                  ) : (
                    <>
                      <Save className="w-5 h-5" />
                      Создать
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Модалка переименования */}
      {renameModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <form onSubmit={handleRename}>
              <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">Переименовать период</h2>
                <button
                  type="button"
                  onClick={() => setRenameModal({ open: false, period: null, name: '' })}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-6 h-6 text-gray-400" />
                </button>
              </div>
              <div className="p-6 space-y-3">
                <label className="block text-sm font-medium text-gray-700">
                  Новое название
                </label>
                <input
                  type="text"
                  required
                  maxLength={100}
                  autoFocus
                  className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={renameModal.name}
                  onChange={(e) => setRenameModal({ ...renameModal, name: e.target.value })}
                />
                <p className="text-xs text-gray-400">
                  Название — только подпись: расчёты, охват и права привязаны к идентификатору периода.
                </p>
              </div>
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setRenameModal({ open: false, period: null, name: '' })}
                  className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={renaming || !renameModal.name.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md disabled:opacity-50"
                >
                  {renaming ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                  Сохранить
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Модалка закрытия периода — подтверждение вводом названия.
          Закрытие необратимо (нет маршрута переоткрытия, period_results никем
          не переписывается), поэтому обычного confirm здесь недостаточно. */}
      {closeModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <form onSubmit={handleClose}>
              <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <Lock className="w-5 h-5 text-red-600" />
                  Закрыть период
                </h2>
                <button
                  type="button"
                  onClick={() => setCloseModal({ open: false, period: null, typed: '' })}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-6 h-6 text-gray-400" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
                  Результаты всех участников — рейтинги по источникам, итоговая оценка
                  и бонусный индекс — будут рассчитаны и сохранены навсегда. Период
                  станет закрытым. <strong>Действие необратимо:</strong> переоткрыть
                  период нельзя, сохранённые результаты не пересчитываются.
                </div>
                <label className="block text-sm font-medium text-gray-700">
                  Введите название периода, чтобы подтвердить:
                  <span className="ml-1 font-mono font-semibold text-gray-900">
                    {closeModal.period?.name}
                  </span>
                </label>
                <input
                  type="text"
                  autoFocus
                  autoComplete="off"
                  placeholder={closeModal.period?.name}
                  className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 outline-none font-mono"
                  value={closeModal.typed}
                  onChange={(e) => setCloseModal({ ...closeModal, typed: e.target.value })}
                />
              </div>
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setCloseModal({ open: false, period: null, typed: '' })}
                  className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={
                    closing === closeModal.period?.id ||
                    closeModal.typed.trim() !== closeModal.period?.name
                  }
                  className="flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {closing === closeModal.period?.id
                    ? <Loader2 className="w-5 h-5 animate-spin" />
                    : <Lock className="w-5 h-5" />}
                  Закрыть период навсегда
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Модалка привязки к контейнеру */}
      {reparentModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <form onSubmit={handleReparent}>
              <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">
                  Контейнер для «{reparentModal.period?.name}»
                </h2>
                <button
                  type="button"
                  onClick={() => setReparentModal({ open: false, period: null, parentId: '' })}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-6 h-6 text-gray-400" />
                </button>
              </div>
              <div className="p-6 space-y-3">
                <label className="block text-sm font-medium text-gray-700">
                  Родительский период
                </label>
                <select
                  className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={reparentModal.parentId}
                  onChange={(e) => setReparentModal({ ...reparentModal, parentId: e.target.value })}
                >
                  <option value="">— без контейнера (отвязать) —</option>
                  {periods
                    .filter((p) => canBeParent(p, reparentModal.period?.id))
                    .map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                </select>
                <p className="text-xs text-gray-400">
                  Контейнер — отчётная конструкция для годовой сводки; привязка и отвязка безопасны.
                  Родителем может быть только период без оценок; даты дочернего периода должны лежать
                  внутри дат контейнера.
                </p>
              </div>
              <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setReparentModal({ open: false, period: null, parentId: '' })}
                  className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={reparenting}
                  className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md disabled:opacity-50"
                >
                  {reparenting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                  Сохранить
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPeriods;
