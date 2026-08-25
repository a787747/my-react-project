/**
 * UserFilters - Панель фильтрации пользователей
 * 
 * Назначение: UI для фильтрации списка пользователей по разным критериям
 * Используется в: AdminUsers
 * 
 * Props:
 * - searchInput: string - текущее значение поиска
 * - filters: object - текущие значения фильтров
 * - options: object - опции для селектов (departments, managers)
 * - onSearchChange: function - колбэк изменения поиска
 * - onFilterChange: function(key, value) - колбэк изменения фильтра
 * - onReset: function - колбэк сброса фильтров
 */

import React from 'react';
import { Search, Filter, X } from 'lucide-react';

const UserFilters = ({ 
  searchInput, 
  filters, 
  options, 
  onSearchChange, 
  onFilterChange, 
  onReset 
}) => {
  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 mb-6">
      {/* Заголовок */}
      <div className="flex items-center gap-2 mb-4 text-gray-700 font-medium">
        <Filter className="w-4 h-4" /> Фильтрация
      </div>
      
      {/* Сетка фильтров */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-4">
        {/* Поиск */}
        <div className="lg:col-span-1 relative">
          <Search className="absolute left-3 top-2.5 text-gray-400 w-4 h-4" />
          <input 
            type="text" 
            placeholder="Поиск..." 
            className="w-full pl-9 p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all"
            value={searchInput}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label="Поиск сотрудников"
          />
        </div>

        {/* Роль */}
        <select 
          className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white transition-all"
          value={filters.role}
          onChange={(e) => onFilterChange('role', e.target.value)}
          aria-label="Фильтр по роли"
        >
          <option value="all">Все роли</option>
          <option value="admin">Admin</option>
          <option value="c_level">C-Level</option>
          <option value="manager">Manager</option>
          <option value="employee">Employee</option>
        </select>

        {/* Отдел */}
        <select 
          className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white transition-all"
          value={filters.department_id}
          onChange={(e) => onFilterChange('department_id', e.target.value)}
          aria-label="Фильтр по отделу"
        >
          <option value="all">Все отделы</option>
          {options.departments.map(d => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>

        {/* Менеджер */}
        <select 
          className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white transition-all"
          value={filters.manager_id}
          onChange={(e) => onFilterChange('manager_id', e.target.value)}
          aria-label="Фильтр по руководителю"
        >
          <option value="all">Все руководители</option>
          {options.managers.map(m => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>

        {/* Категория */}
        <select 
          className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white transition-all"
          value={filters.work_category}
          onChange={(e) => onFilterChange('work_category', e.target.value)}
          aria-label="Фильтр по категории"
        >
          <option value="all">Все категории</option>
          <option value="general">General</option>
          <option value="project">Project</option>
          <option value="tender">Tender</option>
        </select>

        {/* Статус занятости — по умолчанию «Работают» (D-0825-7) */}
        <select
          className="w-full p-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white transition-all"
          value={filters.employment}
          onChange={(e) => onFilterChange('employment', e.target.value)}
          aria-label="Фильтр по статусу занятости"
        >
          <option value="active">Работают</option>
          <option value="terminated">Уволены</option>
          <option value="all">Все (вкл. уволенных)</option>
        </select>

        {/* Кнопка сброса */}
        <button
          onClick={onReset}
          className="flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-dashed border-gray-300 hover:border-red-200 focus:outline-none focus:ring-2 focus:ring-red-200"
          aria-label="Сбросить фильтры"
        >
          <X className="w-4 h-4" /> Сброс
        </button>
      </div>
    </div>
  );
};

export default UserFilters;

