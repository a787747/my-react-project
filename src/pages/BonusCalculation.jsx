/**
 * BonusCalculation - Страница калькуляции бонусов
 * 
 * Назначение: Расчет бонусов сотрудников на основе итоговых оценок
 * Доступ: admin, c_level
 * 
 * Функционал:
 * - Отображение итоговых баллов сотрудников (упрощённая версия без критериев)
 * - Два связанных поля: общий бюджет и сумма одного балла
 * - Автоматический расчет бонуса для каждого сотрудника
 * - Фильтрация и сортировка
 * - Экспорт данных
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Coins, Download, RefreshCw, DollarSign, Calculator, ChevronUp, ChevronDown, Building2, Briefcase, TrendingUp, AlertTriangle } from 'lucide-react';

// Компоненты
import { LoadingSpinner } from '../components/common';
import MatrixFilters from '../components/admin/MatrixFilters';

// Хуки
import { useFinalScoresMatrix } from '../hooks/useFinalScoresMatrix';

// Форматирование числа с разделителями тысяч
const formatNumber = (num, decimals = 2) => {
  if (num === null || num === undefined || isNaN(num)) return '0';
  return num.toLocaleString('ru-RU', { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  });
};

// Форматирование валюты
const formatCurrency = (num) => {
  if (num === null || num === undefined || isNaN(num)) return '0 TMT';
  return num.toLocaleString('ru-RU', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  }) + ' TMT';
};

// Парсинг числа из строки с разделителями
const parseFormattedNumber = (str) => {
  if (!str) return 0;
  // Убираем все пробелы и заменяем запятую на точку
  const cleaned = str.toString().replace(/\s/g, '').replace(',', '.');
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
};

// Округление до целого числа
const roundToInt = (num) => {
  return Math.round(num);
};

const BonusCalculation = () => {
  // Хук для работы с матрицей итоговых баллов
  const {
    employees,
    period,
    campaignActive,
    loading,
    error,
    filters,
    filterOptions,
    filteredEmployees,
    activeFiltersCount,
    setFilters,
    clearFilters,
    fetchData
  } = useFinalScoresMatrix();

  // Состояния для расчета бонусов
  const [totalBudget, setTotalBudget] = useState('');
  const [pointValue, setPointValue] = useState('');
  const [lastEdited, setLastEdited] = useState(null); // 'budget' или 'point'
  
  // Состояние панели фильтров
  const [showFilters, setShowFilters] = useState(true);
  
  // Исключить сотрудников с грейдом A (по умолчанию включены)
  const [includeGradeA, setIncludeGradeA] = useState(true);

  // Локальная сортировка (переопределяем для добавления сортировки по бонусу)
  const [localSorting, setLocalSorting] = useState({ field: 'final_weighted_score', direction: 'desc' });

  // Фильтрация по грейду A
  const employeesAfterGradeFilter = useMemo(() => {
    if (includeGradeA) {
      return filteredEmployees;
    }
    // Исключаем сотрудников с грейдом A (проверяем на точное совпадение "A")
    return filteredEmployees.filter(emp => {
      const gradeCode = emp.grade_code || emp.grade || '';
      return gradeCode.toUpperCase() !== 'A';
    });
  }, [filteredEmployees, includeGradeA]);

  // Общая сумма всех баллов (отфильтрованных сотрудников)
  const totalPoints = useMemo(() => {
    return employeesAfterGradeFilter.reduce((sum, emp) => sum + (emp.final_weighted_score || 0), 0);
  }, [employeesAfterGradeFilter]);

  // Рассчитанные значения
  const calculatedValues = useMemo(() => {
    const budget = parseFormattedNumber(totalBudget);
    const point = parseFormattedNumber(pointValue);

    if (lastEdited === 'budget' && budget > 0 && totalPoints > 0) {
      // Бюджет введён - считаем стоимость балла и округляем до целого
      const rawPointValue = budget / totalPoints;
      const roundedPointValue = roundToInt(rawPointValue);
      return {
        budget: budget,
        pointValue: roundedPointValue
      };
    } else if (lastEdited === 'point' && point > 0) {
      // Стоимость балла введена - округляем до целого и считаем бюджет
      const roundedPoint = roundToInt(point);
      return {
        budget: roundedPoint * totalPoints,
        pointValue: roundedPoint
      };
    }

    return {
      budget: budget || 0,
      pointValue: point || 0
    };
  }, [totalBudget, pointValue, totalPoints, lastEdited]);

  // Сотрудники с расчитанными бонусами
  const employeesWithBonuses = useMemo(() => {
    return employeesAfterGradeFilter.map(emp => ({
      ...emp,
      bonus: (emp.final_weighted_score || 0) * calculatedValues.pointValue
    }));
  }, [employeesAfterGradeFilter, calculatedValues.pointValue]);

  // Сортировка
  const sortedEmployees = useMemo(() => {
    const sorted = [...employeesWithBonuses].sort((a, b) => {
      let valueA, valueB;

      if (localSorting.field === 'full_name') {
        valueA = a.full_name?.toLowerCase() || '';
        valueB = b.full_name?.toLowerCase() || '';
        const result = valueA.localeCompare(valueB);
        return localSorting.direction === 'asc' ? result : -result;
      } else if (localSorting.field === 'department_name') {
        valueA = a.department_name?.toLowerCase() || '';
        valueB = b.department_name?.toLowerCase() || '';
        const result = valueA.localeCompare(valueB);
        return localSorting.direction === 'asc' ? result : -result;
      } else if (localSorting.field === 'final_weighted_score') {
        valueA = a.final_weighted_score ?? -1;
        valueB = b.final_weighted_score ?? -1;
      } else if (localSorting.field === 'bonus') {
        valueA = a.bonus ?? -1;
        valueB = b.bonus ?? -1;
      } else {
        return 0;
      }

      const result = (valueA || 0) - (valueB || 0);
      return localSorting.direction === 'asc' ? result : -result;
    });

    return sorted;
  }, [employeesWithBonuses, localSorting]);

  // Обработчик изменения бюджета
  const handleBudgetChange = (e) => {
    setTotalBudget(e.target.value);
    setLastEdited('budget');
  };

  // Обработчик изменения стоимости балла
  const handlePointValueChange = (e) => {
    setPointValue(e.target.value);
    setLastEdited('point');
  };

  // Обработчик сортировки
  const handleSort = useCallback((field) => {
    setLocalSorting(prev => {
      if (prev.field === field) {
        if (prev.direction === 'desc') {
          return { field, direction: 'asc' };
        } else {
          return { field: 'final_weighted_score', direction: 'desc' };
        }
      }
      return { field, direction: 'desc' };
    });
  }, []);

  // Иконка сортировки
  const getSortIcon = (field) => {
    if (localSorting.field !== field) return null;
    return localSorting.direction === 'desc' ? 
      <ChevronDown className="w-4 h-4" /> : 
      <ChevronUp className="w-4 h-4" />;
  };

  // Общая сумма бонусов
  const totalBonuses = useMemo(() => {
    return sortedEmployees.reduce((sum, emp) => sum + (emp.bonus || 0), 0);
  }, [sortedEmployees]);

  // Экспорт в CSV
  const handleExportCSV = () => {
    const headers = [
      'Сотрудник', 
      'Отдел', 
      'Грейд',
      'Итоговый балл',
      'Бонус (TMT)'
    ];
    
    const rows = sortedEmployees.map(emp => [
      emp.full_name,
      emp.department_name || '',
      emp.grade_code || '',
      emp.final_weighted_score?.toFixed(2) || '0.00',
      emp.bonus?.toFixed(2) || '0.00'
    ]);
    
    // Добавляем итоговую строку
    rows.push([
      'ИТОГО',
      '',
      '',
      totalPoints.toFixed(2),
      totalBonuses.toFixed(2)
    ]);
    
    const csvContent = [
      headers.join(';'),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(';'))
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `бонусы_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка данных..." />;
  }

  // Ошибка загрузки: бонусный индекс без весов и коэффициентов — это
  // невзвешенное распределение денег. Показываем ошибку, а не числа (BUG-030).
  if (error) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <div className="max-w-2xl mx-auto mt-12 bg-white rounded-xl shadow-sm border border-red-200 p-8 text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <h2 className="text-xl font-bold text-gray-900">Бонусы не рассчитаны</h2>
          <p className="text-sm text-red-700 mt-3">{error}</p>
          <p className="text-sm text-gray-500 mt-2">
            Распределять бюджет по этим данным нельзя: без коэффициентов баллы
            были бы невзвешенными, а таблица выглядела бы нормальной.
          </p>
          <button
            onClick={fetchData}
            className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Повторить загрузку
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Coins className="w-8 h-8 text-amber-500" />
            Калькуляция бонусов
          </h1>
          <p className="text-gray-500 mt-2">
            Расчет бонусов сотрудников на основе итоговых оценок
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {period
              ? `Период: ${period.name}${campaignActive ? ' — активен' : ` — ${period.status}`}`
              : 'Нет активного периода — числа не смешиваются между циклами.'}
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors flex items-center gap-2"
            title="Обновить данные"
          >
            <RefreshCw className="w-4 h-4" />
            Обновить
          </button>
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Экспорт CSV
          </button>
        </div>
      </div>

      {/* Панель расчета бонусов */}
      <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl p-6 mb-6 border border-amber-200 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Calculator className="w-5 h-5 text-amber-600" />
          <h2 className="text-lg font-semibold text-amber-900">Параметры расчёта</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Общий бюджет */}
          <div className="bg-white rounded-xl p-4 shadow-sm border border-amber-100">
            <label className="block text-sm font-medium text-gray-600 mb-2">
              Общий бюджет бонусов
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-500" />
              <input
                type="text"
                value={lastEdited === 'point' && calculatedValues.budget > 0 
                  ? formatNumber(calculatedValues.budget, 2) 
                  : totalBudget}
                onChange={handleBudgetChange}
                placeholder="3 000 000"
                className="w-full pl-10 pr-12 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-lg font-semibold"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">TMT</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Введите сумму — стоимость балла рассчитается автоматически
            </p>
          </div>

          {/* Стоимость одного балла */}
          <div className="bg-white rounded-xl p-4 shadow-sm border border-amber-100">
            <label className="block text-sm font-medium text-gray-600 mb-2">
              Стоимость одного балла
            </label>
            <div className="relative">
              <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-emerald-500" />
              <input
                type="text"
                value={lastEdited === 'budget' && calculatedValues.pointValue > 0 
                  ? formatNumber(calculatedValues.pointValue, 2) 
                  : pointValue}
                onChange={handlePointValueChange}
                placeholder="150.00"
                className="w-full pl-10 pr-12 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-lg font-semibold"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">TMT</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Или введите стоимость балла — бюджет рассчитается автоматически
            </p>
          </div>

          {/* Статистика */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-4 text-white shadow-lg">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Сотрудников:</span>
                <span className="font-bold text-lg">{sortedEmployees.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Сумма баллов:</span>
                <span className="font-bold text-lg text-amber-400">{formatNumber(totalPoints, 2)}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-slate-700">
                <span className="text-slate-400 text-sm">Итого бонусов:</span>
                <span className="font-bold text-lg text-emerald-400">{formatCurrency(totalBonuses)}</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Переключатель грейда A */}
        <div className="mt-4 pt-4 border-t border-amber-200">
          <label className="flex items-center gap-3 cursor-pointer group">
            <button
              type="button"
              onClick={() => setIncludeGradeA(!includeGradeA)}
              className={`relative w-14 h-7 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 ${
                includeGradeA ? 'bg-emerald-500' : 'bg-slate-300'
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white shadow-md transform transition-transform duration-200 ${
                  includeGradeA ? 'translate-x-7' : 'translate-x-0'
                }`}
              />
            </button>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-amber-900 group-hover:text-amber-700 transition-colors">
                Учитывать грейд A
              </span>
              <span className="text-xs text-amber-600">
                {includeGradeA 
                  ? 'Сотрудники с грейдом A включены в расчёт' 
                  : 'Сотрудники с грейдом A исключены из расчёта'}
              </span>
            </div>
          </label>
        </div>
      </div>

      {/* Фильтры */}
      <MatrixFilters
        filters={filters}
        filterOptions={filterOptions}
        activeFiltersCount={activeFiltersCount}
        totalCount={employees.length}
        filteredCount={filteredEmployees.length}
        isOpen={showFilters}
        onToggle={() => setShowFilters(!showFilters)}
        onFilterChange={setFilters}
        onClear={clearFilters}
      />

      {/* Таблица */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">
                  <button
                    onClick={() => handleSort('full_name')}
                    className="flex items-center gap-1 hover:text-gray-900 transition-colors"
                  >
                    Сотрудник
                    {getSortIcon('full_name')}
                  </button>
                </th>
                <th className="text-left px-4 py-4 text-sm font-semibold text-gray-600">
                  <button
                    onClick={() => handleSort('department_name')}
                    className="flex items-center gap-1 hover:text-gray-900 transition-colors"
                  >
                    <Building2 className="w-4 h-4 mr-1" />
                    Отдел
                    {getSortIcon('department_name')}
                  </button>
                </th>
                <th className="text-center px-4 py-4 text-sm font-semibold text-gray-600">
                  <Briefcase className="w-4 h-4 inline mr-1" />
                  Грейд
                </th>
                <th className="text-center px-4 py-4 text-sm font-semibold text-gray-600">
                  <button
                    onClick={() => handleSort('final_weighted_score')}
                    className="flex items-center gap-1 hover:text-gray-900 transition-colors mx-auto"
                  >
                    Итоговый балл
                    {getSortIcon('final_weighted_score')}
                  </button>
                </th>
                <th className="text-center px-4 py-4 text-sm font-semibold text-gray-600">
                  <button
                    onClick={() => handleSort('bonus')}
                    className="flex items-center gap-1 hover:text-gray-900 transition-colors mx-auto"
                  >
                    <Coins className="w-4 h-4 mr-1 text-amber-500" />
                    Бонус
                    {getSortIcon('bonus')}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedEmployees.map((emp, index) => (
                <tr 
                  key={emp.id || index} 
                  className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{emp.full_name}</div>
                    {emp.job_title && (
                      <div className="text-sm text-gray-500">{emp.job_title}</div>
                    )}
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-600">
                    {emp.department_name || '—'}
                  </td>
                  <td className="px-4 py-4 text-center">
                    {emp.grade_code ? (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 text-sm font-medium">
                        {emp.grade_code}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-100 text-slate-800 font-bold text-lg">
                      {formatNumber(emp.final_weighted_score || 0, 2)}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    {calculatedValues.pointValue > 0 ? (
                      <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 font-bold text-lg border border-amber-200">
                        {formatCurrency(emp.bonus)}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">Введите бюджет или стоимость балла</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            {/* Итоговая строка */}
            <tfoot>
              <tr className="bg-gradient-to-r from-slate-100 to-slate-50 border-t-2 border-slate-200">
                <td colSpan="3" className="px-6 py-4 font-bold text-gray-700 text-right">
                  ИТОГО ({sortedEmployees.length} сотрудников):
                </td>
                <td className="px-4 py-4 text-center">
                  <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-700 text-white font-bold text-lg">
                    {formatNumber(totalPoints, 2)}
                  </span>
                </td>
                <td className="px-4 py-4 text-center">
                  <span className="inline-flex items-center px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold text-lg shadow-lg">
                    {formatCurrency(totalBonuses)}
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* Пустое состояние */}
        {sortedEmployees.length === 0 && (
          <div className="text-center py-16">
            <Coins className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">Нет данных</h3>
            <p className="text-gray-500">
              Не найдено сотрудников с итоговыми оценками
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BonusCalculation;

