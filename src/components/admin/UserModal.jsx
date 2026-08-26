/**
 * UserModal - Модальное окно создания/редактирования пользователя
 * 
 * Назначение: Форма для добавления нового или редактирования существующего сотрудника
 * Используется в: AdminUsers
 * 
 * Props:
 * - isOpen: boolean - открыто ли модальное окно
 * - user: object | null - редактируемый пользователь (null для создания нового)
 * - options: object - опции для селектов (departments, grades, managers)
 * - saving: boolean - статус сохранения
 * - currentUserRole: string - роль текущего пользователя (для ограничения ролей)
 * - onClose: function - колбэк закрытия
 * - onSave: function(formData) - колбэк сохранения
 */

import React, { useState, useEffect, useMemo } from 'react';
import { X, Save, Loader2, AlertCircle, History } from 'lucide-react';
import { isHR } from '../../utils/permissions';

// Начальное состояние формы
const initialFormState = {
  full_name: '',
  email: '',
  job_title: '',
  role: 'employee',
  work_category: 'general',
  department_id: '',
  grade_id: '',
  manager_id: '',
  join_date: ''
};

// Все доступные роли
const ALL_ROLES = [
  { value: 'employee', label: 'Employee' },
  { value: 'manager', label: 'Manager' },
  { value: 'hr', label: 'HR' },
  { value: 'admin', label: 'Admin' },
  { value: 'c_level', label: 'C-Level' }
];

// Привилегированные роли (недоступны для HR)
const PRIVILEGED_ROLES = ['hr', 'admin', 'c_level'];

const SCOPE_OUTCOME_TEXT = {
  closed_untouched: 'Закрытый период не изменён',
  no_participant_row: 'Нет строки участия — период не изменён',
  terminated_preserved: 'Увольнение имеет приоритет — период не изменён',
  manual_preserved: 'Ручное решение сохранено',
  not_recomputed: 'Дата приёма не менялась',
  refused_has_evaluations: 'Отказ: в периоде уже есть оценки',
  included_by_date: 'Включён в охват по исправленной дате',
  excluded_by_date: 'Исключён по правилу трёх месяцев',
  unchanged_in_scope: 'Остался в охвате',
  unchanged_out_of_scope: 'Остался вне охвата',
};

const UserModal = ({
  isOpen,
  user,
  options,
  saving,
  currentUserRole,
  canManageScope,
  onClose,
  onSave,
  onScopeChange,
  onLoadEvents,
}) => {
  const [formData, setFormData] = useState(initialFormState);
  const [formErrors, setFormErrors] = useState({});
  const [saveMessage, setSaveMessage] = useState(null);
  const [scopeResults, setScopeResults] = useState([]);
  const [periodScopes, setPeriodScopes] = useState([]);
  const [scopeError, setScopeError] = useState(null);
  const [events, setEvents] = useState([]);
  const [eventsError, setEventsError] = useState(null);
  
  // Фильтрация доступных ролей на основе роли текущего пользователя
  const availableRoles = useMemo(() => {
    // HR не может назначать привилегированные роли (hr, admin, c_level)
    if (isHR(currentUserRole)) {
      return ALL_ROLES.filter(role => !PRIVILEGED_ROLES.includes(role.value));
    }
    return ALL_ROLES;
  }, [currentUserRole]);

  // Заполняем форму данными пользователя при открытии
  useEffect(() => {
    if (isOpen) {
      if (user) {
        setFormData({
          full_name: user.full_name || '',
          email: user.email || '',
          job_title: user.job_title || '',
          role: user.role || 'employee',
          work_category: user.work_category || 'general',
          department_id: user.department_id || '',
          grade_id: user.grade_id || '',
          manager_id: user.manager_id || '',
          join_date: user.join_date || ''
        });
        setPeriodScopes(Array.isArray(user.period_scopes) ? user.period_scopes : []);
      } else {
        setFormData(initialFormState);
        setPeriodScopes([]);
      }
      setFormErrors({});
      setSaveMessage(null);
      setScopeResults([]);
      setScopeError(null);
      setEvents([]);
      setEventsError(null);
    }
  }, [isOpen, user]);

  const reloadEvents = async () => {
    if (!user?.id || !canManageScope || !onLoadEvents) return;
    const result = await onLoadEvents(user.id);
    if (result.success) {
      setEvents(result.data?.events || []);
      setEventsError(null);
    } else {
      setEventsError(result.error);
    }
  };

  useEffect(() => {
    if (isOpen && user?.id && canManageScope) {
      reloadEvents();
    }
    // reloadEvents intentionally depends on the current modal target.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, user?.id, canManageScope]);

  // Обработка Escape для закрытия
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Блокировка скролла
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Валидация формы
  const validateForm = () => {
    const errors = {};

    if (!formData.full_name.trim()) {
      errors.full_name = 'Введите ФИО';
    }

    if (!formData.email.trim()) {
      errors.email = 'Введите email';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Некорректный email';
    }

    // Проверка самоназначения менеджера
    if (user && formData.manager_id && String(user.id) === String(formData.manager_id)) {
      errors.manager_id = 'Сотрудник не может быть своим руководителем';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Отправка формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setSaveMessage(null);
    setScopeError(null);
    const result = await onSave(formData, user?.id);
    if (result?.success) {
      const outcomes = result.data?.scope_results || [];
      setScopeResults(outcomes);
      setSaveMessage(
        result.data?.card_event_id
          ? 'Карточка сохранена, изменение записано в журнал.'
          : 'Данные совпадают с текущей строкой; новая запись не потребовалась.'
      );
      setPeriodScopes((current) => current.map((period) => {
        const outcome = outcomes.find(
          (item) => Number(item.period_id) === Number(period.period_id)
        );
        if (!outcome || !outcome.desired_is_in_scope) {
          if (outcome?.outcome === 'excluded_by_date') {
            return {
              ...period,
              is_in_scope: false,
              exclusion_reason: outcome.desired_reason,
            };
          }
          return period;
        }
        if (outcome.outcome === 'included_by_date') {
          return { ...period, is_in_scope: true, exclusion_reason: null };
        }
        return period;
      }));
      await reloadEvents();
    } else if (result) {
      setScopeResults(result.data?.scope_results || result.data?.periods || []);
      setScopeError(result.error);
    }
  };

  const handleScopeToggle = async (period, participate) => {
    if (!user?.id || !onScopeChange) return;
    setScopeError(null);
    const result = await onScopeChange(user.id, period.period_id, participate);
    if (!result.success) {
      setScopeError(result.error);
      return;
    }
    setPeriodScopes((current) => current.map((item) => (
      Number(item.period_id) === Number(period.period_id)
        ? {
            ...item,
            is_in_scope: participate,
            exclusion_reason: participate ? null : 'excluded_by_admin',
            scope_override: participate ? 'included_by_admin' : 'excluded_by_admin',
          }
        : item
    )));
    setSaveMessage(
      `${period.period_name}: ${participate ? 'участие включено' : 'участие выключено'}; событие записано.`
    );
    await reloadEvents();
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div 
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          {/* Header */}
          <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0 z-10">
            <h2 id="modal-title" className="text-xl font-bold text-gray-900">
              {user ? 'Редактировать сотрудника' : 'Новый сотрудник'}
            </h2>
            <button 
              type="button" 
              onClick={onClose} 
              className="p-2 hover:bg-gray-100 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300"
              aria-label="Закрыть"
            >
              <X className="w-6 h-6 text-gray-400" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* ФИО */}
            <div className="col-span-2 md:col-span-1">
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-1">
                ФИО <span className="text-red-500">*</span>
              </label>
              <input 
                id="full_name"
                type="text" 
                className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all ${
                  formErrors.full_name ? 'border-red-300 bg-red-50' : 'border-gray-300'
                }`}
                value={formData.full_name} 
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              />
              {formErrors.full_name && (
                <p className="text-red-500 text-xs mt-1">{formErrors.full_name}</p>
              )}
            </div>
            
            {/* Email */}
            <div className="col-span-2 md:col-span-1">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email <span className="text-red-500">*</span>
              </label>
              <input 
                id="email"
                type="email" 
                className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all ${
                  formErrors.email ? 'border-red-300 bg-red-50' : 'border-gray-300'
                }`}
                value={formData.email} 
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
              {formErrors.email && (
                <p className="text-red-500 text-xs mt-1">{formErrors.email}</p>
              )}
            </div>

            {/* Должность */}
            <div className="col-span-2">
              <label htmlFor="job_title" className="block text-sm font-medium text-gray-700 mb-1">
                Должность
              </label>
              <input 
                id="job_title"
                type="text" 
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                value={formData.job_title} 
                onChange={(e) => setFormData({...formData, job_title: e.target.value})} 
              />
            </div>

            {/* Hire date is a money-affecting admin field (D-0826-4). Empty is
                a real value: it moves date-derived rows out with
                join_date_missing, unless a manual mark has precedence. */}
            {canManageScope && (
              <div className="col-span-2 md:col-span-1">
                <label htmlFor="join_date" className="block text-sm font-medium text-gray-700 mb-1">
                  Дата приёма
                </label>
                <input
                  id="join_date"
                  type="date"
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                  value={formData.join_date}
                  onChange={(e) => setFormData({ ...formData, join_date: e.target.value })}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Можно оставить пустой. После сохранения охват открытых периодов пересчитается.
                </p>
              </div>
            )}

            {/* Роль */}
            <div>
              <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1">
                Роль доступа
              </label>
              <select 
                id="role"
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white outline-none transition-all"
                value={formData.role} 
                onChange={(e) => setFormData({...formData, role: e.target.value})}
              >
                {availableRoles.map(role => (
                  <option key={role.value} value={role.value}>{role.label}</option>
                ))}
              </select>
              {/* Подсказка для HR о недоступных ролях */}
              {isHR(currentUserRole) && (
                <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Роли HR, Admin и C-Level назначаются только администратором
                </p>
              )}
            </div>
            
            {/* Категория */}
            <div>
              <label htmlFor="work_category" className="block text-sm font-medium text-gray-700 mb-1">
                Категория
              </label>
              <select 
                id="work_category"
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white outline-none transition-all"
                value={formData.work_category} 
                onChange={(e) => setFormData({...formData, work_category: e.target.value})}
              >
                <option value="general">General</option>
                <option value="project">Project</option>
                <option value="tender">Tender</option>
              </select>
            </div>

            {/* Отдел */}
            <div>
              <label htmlFor="department_id" className="block text-sm font-medium text-gray-700 mb-1">
                Отдел
              </label>
              <select 
                id="department_id"
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white outline-none transition-all"
                value={formData.department_id} 
                onChange={(e) => setFormData({...formData, department_id: e.target.value})}
              >
                <option value="">Без отдела</option>
                {options.departments.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            
            {/* Грейд */}
            <div>
              <label htmlFor="grade_id" className="block text-sm font-medium text-gray-700 mb-1">
                Грейд
              </label>
              <select 
                id="grade_id"
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white outline-none transition-all"
                value={formData.grade_id} 
                onChange={(e) => setFormData({...formData, grade_id: e.target.value})}
              >
                <option value="">Без грейда</option>
                {options.grades.map(g => (
                  <option key={g.id} value={g.id}>{g.code}</option>
                ))}
              </select>
            </div>

            {/* Руководитель */}
            <div className="col-span-2">
              <label htmlFor="manager_id" className="block text-sm font-medium text-gray-700 mb-1">
                Руководитель
              </label>
              <select 
                id="manager_id"
                className={`w-full p-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white outline-none transition-all ${
                  formErrors.manager_id ? 'border-red-300 bg-red-50' : 'border-gray-300'
                }`}
                value={formData.manager_id} 
                onChange={(e) => setFormData({...formData, manager_id: e.target.value})}
              >
                <option value="">Без руководителя</option>
                {options.managers.map(m => (
                  <option 
                    key={m.id} 
                    value={m.id}
                    disabled={user && user.id === m.id}
                  >
                    {m.name} {user && user.id === m.id ? '(это он сам)' : ''}
                  </option>
                ))}
              </select>
              {formErrors.manager_id && (
                <p className="text-red-500 text-xs mt-1">{formErrors.manager_id}</p>
              )}
            </div>

            {canManageScope && user && (
              <section className="col-span-2 border-t border-gray-200 pt-5" aria-labelledby="period-scope-title">
                <h3 id="period-scope-title" className="text-sm font-semibold text-gray-900">
                  Участвует в оценке
                </h3>
                <p className="text-xs text-gray-500 mt-1 mb-3">
                  Ручное решение имеет приоритет над датой приёма. Закрытые периоды и увольнение не меняются.
                </p>
                <div className="space-y-2">
                  {periodScopes.map((period) => {
                    const disabled = saving
                      || period.period_status === 'closed'
                      || period.period_type === 'annual'
                      || !period.has_period_row
                      || Boolean(user.terminated_at);
                    return (
                      <div
                        key={period.period_id}
                        className="flex items-center justify-between gap-4 rounded-lg border border-gray-200 p-3"
                      >
                        <div>
                          <p className="text-sm font-medium text-gray-900">{period.period_name}</p>
                          <p className="text-xs text-gray-500">
                            {period.start_date} — {period.end_date}
                            {period.period_status === 'closed' && ' · закрыт'}
                            {period.period_type === 'annual' && ' · годовой контейнер'}
                            {!period.has_period_row && ' · нет строки участия'}
                          </p>
                          {period.exclusion_reason && (
                            <p className="text-xs text-amber-700 mt-0.5">
                              Причина: {period.exclusion_reason}
                            </p>
                          )}
                        </div>
                        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                          <input
                            type="checkbox"
                            checked={period.is_in_scope === true}
                            disabled={disabled}
                            onChange={(e) => handleScopeToggle(period, e.target.checked)}
                            aria-label={`${period.period_name}: участвует в оценке`}
                            className="h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                          />
                          {period.is_in_scope === true ? 'Да' : 'Нет'}
                        </label>
                      </div>
                    );
                  })}
                  {periodScopes.length === 0 && (
                    <p className="text-sm text-gray-500">Периоды участия не найдены.</p>
                  )}
                </div>
              </section>
            )}

            {(saveMessage || scopeError) && (
              <div
                className={`col-span-2 rounded-lg border p-3 text-sm ${
                  scopeError
                    ? 'border-red-200 bg-red-50 text-red-800'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-800'
                }`}
                role={scopeError ? 'alert' : 'status'}
              >
                {scopeError || saveMessage}
              </div>
            )}

            {scopeResults.length > 0 && (
              <section className="col-span-2 rounded-lg border border-indigo-200 bg-indigo-50 p-3">
                <h3 className="text-sm font-semibold text-indigo-950">
                  Что произошло с охватом
                </h3>
                <ul className="mt-2 space-y-1 text-sm text-indigo-900">
                  {scopeResults.map((result) => (
                    <li key={result.period_id}>
                      <strong>{result.period_name}:</strong>{' '}
                      {SCOPE_OUTCOME_TEXT[result.outcome] || result.outcome}
                      {result.outcome === 'refused_has_evaluations' && (
                        <span>
                          {' '}— получено {result.evaluations_received || 0},
                          самооценок {result.self_reviews || 0},
                          поставлено другим {result.evaluations_given || 0},
                          корректировок {result.corrections_about || 0}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {canManageScope && user && (
              <section className="col-span-2 border-t border-gray-200 pt-5" aria-labelledby="employee-events-title">
                <h3 id="employee-events-title" className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                  <History className="w-4 h-4" />
                  Журнал изменений
                </h3>
                {eventsError && <p className="text-xs text-red-700 mt-2">{eventsError}</p>}
                {!eventsError && events.length === 0 && (
                  <p className="text-xs text-gray-500 mt-2">Записей пока нет.</p>
                )}
                <ul className="mt-2 max-h-40 overflow-y-auto space-y-2">
                  {events.map((event) => (
                    <li
                      key={`${event.source}-${event.event_id}`}
                      className="text-xs text-gray-700 border-l-2 border-gray-200 pl-2"
                    >
                      <span className="font-medium">{event.source}: {event.event_type}</span>
                      {' · '}
                      {event.occurred_at || 'время не указано'}
                      {' · actor '}
                      {event.actor_id}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 sticky bottom-0 rounded-b-2xl">
            <button 
              type="button" 
              onClick={onClose} 
              className="px-5 py-2.5 text-gray-700 font-medium hover:bg-gray-200 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300"
            >
              Отмена
            </button>
            <button 
              type="submit" 
              disabled={saving} 
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserModal;

