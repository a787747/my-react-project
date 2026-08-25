/**
 * UserFilters - Панель фильтрации пользователей
 * 
 * Назначение: UI для фильтрации списка пользователей по разным критериям
 * Используется в: AdminUsers, TeamView
 * 
 * Props:
 * - searchInput: string - текущее значение поиска
 * - filters: object - текущие значения фильтров
 * - facets: object - варианты каждого контрола со счётчиками (useUserFilters)
 * - activeFilterCount: number - сколько контролов уведено от значения по умолчанию
 * - onSearchChange: function - колбэк изменения поиска
 * - onFilterChange: function(key, value) - колбэк изменения фильтра
 * - onReset: function - колбэк сброса фильтров
 *
 * Варианты выбора приходят из данных, а не из константы в разметке: опция
 * существует, только если её кто-то из популяции носит, и показывает число,
 * которое даст с учётом остальных активных фильтров. Поэтому «(0)» видно до
 * клика, а не после — прежняя строка молча отдавала пустой список.
 */

import React from 'react';
import { Search, Filter, X } from 'lucide-react';
import { ALL } from '../../utils/userFilters';

const SELECT_BASE =
  'w-full p-2 border rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 bg-white transition-all';
const SELECT_IDLE = 'border-gray-200 text-gray-900';
const SELECT_ACTIVE = 'border-indigo-400 ring-1 ring-indigo-200 text-indigo-900 font-medium';

const optionText = (option) =>
  option.orphan ? option.label : `${option.label} (${option.count})`;

const FilterSelect = ({ id, label, value, defaultValue, allLabel, options, onChange }) => {
  const isActive = value !== defaultValue;
  return (
    <select
      className={`${SELECT_BASE} ${isActive ? SELECT_ACTIVE : SELECT_IDLE}`}
      value={value}
      onChange={(e) => onChange(id, e.target.value)}
      aria-label={label}
      title={label}
    >
      {allLabel && <option value={ALL}>{allLabel}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {optionText(option)}
        </option>
      ))}
    </select>
  );
};

const UserFilters = ({ 
  searchInput, 
  filters, 
  facets,
  activeFilterCount = 0,
  onSearchChange, 
  onFilterChange, 
  onReset,
  // D-0825-11. Off by default, for the same reason UserTable's column is:
  // /team's payload cannot tell the states apart.
  showEvaluationState = false
}) => {
  const lists = facets || {};
  const searchActive = String(searchInput || '').trim() !== '';

  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 mb-6">
      {/* Заголовок */}
      <div className="flex items-center gap-2 mb-4 text-gray-700 font-medium">
        <Filter className="w-4 h-4" /> Фильтрация
        {activeFilterCount > 0 && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            активных: {activeFilterCount}
          </span>
        )}
      </div>
      
      {/* Сетка фильтров */}
      <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${showEvaluationState ? 'lg:grid-cols-8' : 'lg:grid-cols-7'}`}>
        {/* Поиск */}
        <div className="lg:col-span-1 relative">
          <Search className="absolute left-3 top-2.5 text-gray-400 w-4 h-4" />
          <input 
            type="text" 
            placeholder="Поиск..." 
            className={`w-full pl-9 p-2 border rounded-lg text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all ${
              searchActive ? 'border-indigo-400 ring-1 ring-indigo-200' : 'border-gray-200'
            }`}
            value={searchInput}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label="Поиск сотрудников"
            title="Поиск по имени и e-mail"
          />
        </div>

        {/* Роль */}
        <FilterSelect
          id="role"
          label="Фильтр по роли"
          value={filters.role}
          defaultValue={ALL}
          allLabel="Все роли"
          options={lists.role || []}
          onChange={onFilterChange}
        />

        {/* Отдел */}
        <FilterSelect
          id="department_id"
          label="Фильтр по отделу"
          value={filters.department_id}
          defaultValue={ALL}
          allLabel="Все отделы"
          options={lists.department_id || []}
          onChange={onFilterChange}
        />

        {/* Менеджер */}
        <FilterSelect
          id="manager_id"
          label="Фильтр по руководителю"
          value={filters.manager_id}
          defaultValue={ALL}
          allLabel="Все руководители"
          options={lists.manager_id || []}
          onChange={onFilterChange}
        />

        {/* Категория */}
        <FilterSelect
          id="work_category"
          label="Фильтр по категории"
          value={filters.work_category}
          defaultValue={ALL}
          allLabel="Все категории"
          options={lists.work_category || []}
          onChange={onFilterChange}
        />

        {/* Статус занятости — по умолчанию «Работают» (D-0825-7) */}
        <FilterSelect
          id="employment"
          label="Фильтр по статусу занятости"
          value={filters.employment}
          defaultValue="active"
          allLabel={null}
          options={lists.employment || []}
          onChange={onFilterChange}
        />

        {/* Оценка в периоде — D-0825-11. Показывается только там, где состояние
            вообще различимо: на /team payload маршрута не несёт строк участия,
            и список свёлся бы к одному пункту «нет активного периода». */}
        {showEvaluationState && (
          <FilterSelect
            id="evaluation_state"
            label="Фильтр по состоянию в оценке"
            value={filters.evaluation_state}
            defaultValue={ALL}
            allLabel="Любое состояние"
            options={lists.evaluation_state || []}
            onChange={onFilterChange}
          />
        )}

        {/* Кнопка сброса */}
        <button
          onClick={onReset}
          className="flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-dashed border-gray-300 hover:border-red-200 focus:outline-none focus:ring-2 focus:ring-red-200"
          aria-label="Сбросить фильтры"
          title="Сбросить всё: поиск пустой, все списки «Все», статус занятости — «Работают»"
        >
          <X className="w-4 h-4" /> Сброс
        </button>
      </div>
    </div>
  );
};

export default UserFilters;
