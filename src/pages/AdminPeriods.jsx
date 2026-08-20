/**
 * AdminPeriods - Страница управления периодами оценки и регистрацией
 * 
 * Назначение: Создание, активация и управление периодами оценки.
 *             Получение постоянной ссылки для регистрации сотрудников.
 * Доступ: admin, c_level
 * 
 * Функционал:
 * - Список всех периодов
 * - Создание нового периода
 * - Активация/деактивация периодов
 * - Получение постоянной invite-ссылки для регистрации
 */

import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { Calendar, Plus, CheckCircle, Circle, Loader2, Save, X, Link2, Copy, Check, UserPlus } from 'lucide-react';
import { API_ENDPOINTS, API_BASE_URL } from '../config/api';
import logger from '../utils/logger';

const AdminPeriods = ({ user }) => {
  const [periods, setPeriods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(null);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    start_date: '',
    end_date: ''
  });

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

  const handleActivate = async (periodId) => {
    const period = periods.find((item) => item.id === periodId);
    if (!period || period.status === 'closed') {
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
      alert('Не удалось активировать период');
    } finally {
      setActivating(null);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    
    try {
      setCreating(true);
      await apiClient.post(API_ENDPOINTS.PERIODS_CREATE, formData);
      setIsModalOpen(false);
      setFormData({ name: '', start_date: '', end_date: '' });
      await fetchPeriods();
    } catch (error) {
      logger.error('Ошибка создания:', error);
      alert('Не удалось создать период');
    } finally {
      setCreating(false);
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
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm font-medium"
        >
          <Plus className="w-5 h-5" />
          Создать период
        </button>
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
                {periods.map((period) => (
                  <tr 
                    key={period.id}
                    className={`hover:bg-gray-50 transition-colors ${
                      period.is_active ? 'bg-green-50/30' : ''
                    }`}
                  >
                    {/* Статус */}
                    <td className="px-6 py-4">
                      {period.is_active ? (
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-5 h-5 text-green-600" />
                          <span className="text-sm font-medium text-green-700">Активен</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Circle className="w-5 h-5 text-gray-400" />
                          <span className="text-sm text-gray-500">Неактивен</span>
                        </div>
                      )}
                    </td>

                    {/* Название */}
                    <td className="px-6 py-4">
                      <div className="font-semibold text-gray-900">{period.name}</div>
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
                        {period.in_scope_count != null
                          ? `${period.in_scope_count}${period.participant_count != null ? ` / ${period.participant_count}` : ''}`
                          : '—'}
                      </div>
                    </td>

                    {/* Действия */}
                    <td className="px-6 py-4 text-right">
                      {!period.is_active && period.status !== 'closed' && (
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
                      {period.is_active && (
                        <span className="px-4 py-2 bg-green-100 text-green-700 text-sm font-medium rounded-lg">
                          Текущий период
                        </span>
                      )}
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
                    placeholder="Q1 2025, Annual Review 2025, etc."
                    className="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
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

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Примечание:</strong> Новый период будет создан в неактивном состоянии.
                    Вы сможете активировать его позже.
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
    </div>
  );
};

export default AdminPeriods;
