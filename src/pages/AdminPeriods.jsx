import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar, Plus, CheckCircle, Circle, Loader2, Save, X } from 'lucide-react';

const API_GET_PERIODS = 'http://92.51.45.147:5678/webhook/api/periods';
const API_CREATE_PERIOD = 'http://92.51.45.147:5678/webhook/api/periods/create';
const API_ACTIVATE_PERIOD = 'http://92.51.45.147:5678/webhook/api/periods/activate';

const AdminPeriods = () => {
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

  useEffect(() => {
    fetchPeriods();
  }, []);

  const fetchPeriods = async () => {
    try {
      setLoading(true);
      const response = await axios.get(API_GET_PERIODS);
      const data = response.data.data || [];
      setPeriods(data);
    } catch (error) {
      console.error('Ошибка загрузки периодов:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (periodId) => {
    if (!window.confirm('Активировать этот период? Текущий активный период будет деактивирован.')) {
      return;
    }

    try {
      setActivating(periodId);
      await axios.post(API_ACTIVATE_PERIOD, {
        period_id: periodId
      });
      await fetchPeriods();
    } catch (error) {
      console.error('Ошибка активации:', error);
      alert('Не удалось активировать период');
    } finally {
      setActivating(null);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    
    try {
      setCreating(true);
      await axios.post(API_CREATE_PERIOD, formData);
      setIsModalOpen(false);
      setFormData({ name: '', start_date: '', end_date: '' });
      await fetchPeriods();
    } catch (error) {
      console.error('Ошибка создания:', error);
      alert('Не удалось создать период');
    } finally {
      setCreating(false);
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

                    {/* Действия */}
                    <td className="px-6 py-4 text-right">
                      {!period.is_active && (
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
