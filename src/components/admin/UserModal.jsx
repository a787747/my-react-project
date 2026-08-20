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
import { X, Save, Loader2, AlertCircle } from 'lucide-react';
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
  manager_id: ''
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

const UserModal = ({ isOpen, user, options, saving, currentUserRole, onClose, onSave }) => {
  const [formData, setFormData] = useState(initialFormState);
  const [formErrors, setFormErrors] = useState({});
  
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
          manager_id: user.manager_id || ''
        });
      } else {
        setFormData(initialFormState);
      }
      setFormErrors({});
    }
  }, [isOpen, user]);

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

    await onSave(formData, user?.id);
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

