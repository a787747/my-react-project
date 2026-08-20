/**
 * MatrixFilters - Панель фильтров для матрицы оценок
 * 
 * Назначение: UI для фильтрации матрицы оценок
 * Используется в: AdminEvaluationsMatrix
 * 
 * Props:
 * - filters: object - текущие значения фильтров
 * - filterOptions: object - опции для селектов
 * - activeFiltersCount: number - количество активных фильтров
 * - totalCount: number - общее количество сотрудников
 * - filteredCount: number - количество отфильтрованных
 * - isOpen: boolean - развернута ли панель
 * - onToggle: function - переключить панель
 * - onFilterChange: function(key, value) - изменить фильтр
 * - onClear: function - сбросить фильтры
 */

import React from 'react';
import { Filter, ChevronDown } from 'lucide-react';

const MatrixFilters = ({
  filters,
  filterOptions,
  activeFiltersCount,
  totalCount,
  filteredCount,
  isOpen,
  onToggle,
  onFilterChange,
  onClear
}) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 mb-4 overflow-hidden">
      {/* Заголовок */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-indigo-600" />
          <span className="font-medium text-gray-700">Фильтры</span>
          {activeFiltersCount > 0 && (
            <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-0.5 rounded-full">
              {activeFiltersCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            Показано: {filteredCount} из {totalCount}
          </span>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {/* Панель фильтров */}
      {isOpen && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 mt-4">
            {/* Отдел */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Отдел</label>
              <select
                value={filters.department}
                onChange={(e) => onFilterChange('department', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="">Все отделы</option>
                {filterOptions.departments.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            {/* Грейд */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Грейд</label>
              <select
                value={filters.grade}
                onChange={(e) => onFilterChange('grade', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="">Все грейды</option>
                {filterOptions.grades.map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>

            {/* Должность */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Должность</label>
              <select
                value={filters.jobTitle}
                onChange={(e) => onFilterChange('jobTitle', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="">Все должности</option>
                {filterOptions.jobTitles.map(j => (
                  <option key={j} value={j}>{j}</option>
                ))}
              </select>
            </div>

            {/* Участник проекта */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Участник проекта</label>
              <select
                value={filters.projectParticipant}
                onChange={(e) => onFilterChange('projectParticipant', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="">Все</option>
                <option value="yes">Да</option>
                <option value="no">Нет</option>
              </select>
            </div>

            {/* Кнопка сброса */}
            <div className="flex items-end">
              <button
                onClick={onClear}
                disabled={activeFiltersCount === 0}
                className="w-full px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Сбросить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MatrixFilters;

