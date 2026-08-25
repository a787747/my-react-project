/**
 * BonusCalculation - Страница калькуляции бонусов
 * 
 * Назначение: распределение премиального фонда между людьми, которые берут
 * его долю, пропорционально индексу распределения премии.
 * Доступ: только admin (CoefficientRoute, D-0822-2). Прежняя строка «admin,
 * c_level» в этом комментарии маршруту не соответствовала.
 *
 * Как считается (D-0825-14, §4 HANDOVER):
 *   индекс_i  = взвешенная сумма БЕЗ деления на сумму весов × коэф. грейда
 *               (формула 3 — это НЕ рейтинг 1–10 и он с ним не сходится)
 *   доля_i    = индекс_i / Σиндекс
 *   сумма_i   = доля_i × бюджет,   и Σсумма_i = бюджет ТОЧНО
 *
 * До 2026-08-25 введённый бюджет делился на Σиндекс, ЦЕЛОЧИСЛЕННО округлялся
 * и превращался в «стоимость балла», которой затем умножали каждый индекс.
 * Итог не сходился с бюджетом (расхождение росло с числом людей), а бюджет
 * меньше половины Σиндекс округлял стоимость балла в ноль и обнулял всю
 * таблицу, оставив в поле бюджета введённую сумму.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Coins, Download, RefreshCw, DollarSign, Calculator, ChevronUp, ChevronDown, Building2, Briefcase, TrendingUp, AlertTriangle } from 'lucide-react';

// Компоненты
import { LoadingSpinner } from '../components/common';
import MatrixFilters from '../components/admin/MatrixFilters';

// Хуки
import { useFinalScoresMatrix } from '../hooks/useFinalScoresMatrix';
import { distributeBudget, parseHumanNumber } from '../utils/matrixUtils';

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

// Разбор числа, введённого человеком, живёт в matrixUtils: локальная версия
// возвращала 3 для «3.000.000» (parseFloat останавливается на второй точке) и
// заменяла только первую запятую. Ru-locale администратор, набравший бюджет
// точками, получал бюджет в три маната и таблицу нулей.
const parseFormattedNumber = parseHumanNumber;

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

  // D-0825-14. Список фонда — это люди, которые берут его долю: в охвате
  // периода И оцениваемые хоть кем-нибудь. Правило, не список идентификаторов,
  // поэтому список поддерживает себя сам: оба поля владелец меняет в
  // «Сотрудниках», охват меняют маршруты периода.
  //
  // `takes_bonus_share` считает `takesBonusShare` в matrixUtils. Сегодня на
  // живой базе правило убирает 14 строк из 88: шестерых, кого не оценивает
  // никто (2, 18, 21, 40, 47, 61 — из них id 2 маршрут матрицы и так не
  // отдаёт), и девять человек вне охвата H1.
  const poolEligible = useMemo(
    () => filteredEmployees.filter(emp => emp.takes_bonus_share !== false),
    [filteredEmployees],
  );
  const notInPool = useMemo(
    () => filteredEmployees.filter(emp => emp.takes_bonus_share === false),
    [filteredEmployees],
  );

  // Фильтрация по грейду A
  const employeesAfterGradeFilter = useMemo(() => {
    if (includeGradeA) {
      return poolEligible;
    }
    // Исключаем сотрудников с грейдом A (проверяем на точное совпадение "A")
    return poolEligible.filter(emp => {
      const gradeCode = emp.grade_code || emp.grade || '';
      return gradeCode.toUpperCase() !== 'A';
    });
  }, [poolEligible, includeGradeA]);

  // Общая сумма всех баллов (отфильтрованных сотрудников)
  const totalPoints = useMemo(() => {
    return employeesAfterGradeFilter.reduce((sum, emp) => sum + (emp.final_weighted_score || 0), 0);
  }, [employeesAfterGradeFilter]);

  // Бюджет и стоимость балла — два взгляда на одно и то же, и ни один из них
  // больше не округляется до целого. Что бы ни ввели, распределяемая сумма —
  // `budget`, а `pointValue` — производное, для чтения.
  const calculatedValues = useMemo(() => {
    const budget = parseFormattedNumber(totalBudget);
    const point = parseFormattedNumber(pointValue);

    if (lastEdited === 'budget' && budget > 0) {
      return {
        budget,
        pointValue: totalPoints > 0 ? budget / totalPoints : 0,
        source: 'budget',
      };
    }
    if (lastEdited === 'point' && point > 0) {
      return { budget: point * totalPoints, pointValue: point, source: 'point' };
    }
    return { budget: budget || 0, pointValue: point || 0, source: null };
  }, [totalBudget, pointValue, totalPoints, lastEdited]);

  // Суммы. Метод наибольших остатков: доли пропорциональны индексу, а сумма
  // выведенных на экран сумм равна бюджету до копейки. Простое умножение на
  // стоимость балла этого не даёт — на 80 строках расхождение доходит до 0.40,
  // и экран показывал бы «Итого бонусов», не равное введённому бюджету.
  const bonusByEmployee = useMemo(
    () => distributeBudget(
      employeesAfterGradeFilter.map(emp => ({ key: emp.id, index: emp.final_weighted_score || 0 })),
      calculatedValues.budget,
    ),
    [employeesAfterGradeFilter, calculatedValues.budget],
  );

  const employeesWithBonuses = useMemo(() => {
    return employeesAfterGradeFilter.map(emp => ({
      ...emp,
      bonus: bonusByEmployee.get(emp.id) ?? 0,
      share: totalPoints > 0 ? (emp.final_weighted_score || 0) / totalPoints : 0,
    }));
  }, [employeesAfterGradeFilter, bonusByEmployee, totalPoints]);

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
      'Доля фонда, %',
      'Бонус (TMT)'
    ];
    
    const rows = sortedEmployees.map(emp => [
      emp.full_name,
      emp.department_name || '',
      emp.grade_code || '',
      emp.final_weighted_score?.toFixed(2) || '0.00',
      (emp.share * 100).toFixed(4),
      emp.bonus?.toFixed(2) || '0.00'
    ]);
    
    // Добавляем итоговую строку
    rows.push([
      'ИТОГО',
      '',
      '',
      totalPoints.toFixed(2),
      totalPoints > 0 ? '100.0000' : '0.0000',
      totalBonuses.toFixed(2)
    ]);
    
    // Провенанс. Без этих трёх строк файл нулей, выгруженный до ввода бюджета,
    // выглядит как готовая платёжная ведомость: на экране в этот момент честно
    // стоит подсказка, а в файле — только нули.
    const provenance = [
      ['Период', period?.name || 'не определён', '', '', '', ''],
      ['Бюджет (TMT)', calculatedValues.budget ? calculatedValues.budget.toFixed(2) : '0.00', '', '', '', ''],
      ['Стоимость балла (TMT)', calculatedValues.pointValue ? calculatedValues.pointValue.toFixed(6) : '0.000000', '', '', '', ''],
      ['Не берут долю фонда', String(notInPool.length), '', '', '', ''],
      ['', '', '', '', '', ''],
    ];
    
    const csvContent = [
      ...provenance.map(row => row.map(cell => `"${cell}"`).join(';')),
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
                data-testid="budget-input"
                className="w-full pl-10 pr-12 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-lg font-semibold"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">TMT</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Сумма распределяется между {sortedEmployees.length} чел. пропорционально итоговому
              баллу; сумма всех начислений равна введённому бюджету.
            </p>
            {calculatedValues.budget > 0 && totalPoints <= 0 && (
              <p className="text-xs text-amber-700 font-semibold mt-2" data-testid="budget-no-points">
                Распределять пока не из чего: сумма итоговых баллов равна нулю — в этом периоде
                ещё нет ни одной оценки. Бюджет сохранён в поле, начисления появятся вместе
                с оценками.
              </p>
            )}
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
              Или введите стоимость балла — бюджет рассчитается автоматически. Значение больше
              не округляется до целого: округление обнуляло всю таблицу, когда бюджет был меньше
              половины суммы баллов.
            </p>
          </div>

          {/* Статистика */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-4 text-white shadow-lg">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">В фонде:</span>
                <span className="font-bold text-lg">{sortedEmployees.length}</span>
              </div>
              {notInPool.length > 0 && (
                <div className="flex justify-between items-center">
                  <span
                    className="text-slate-400 text-sm"
                    title="Вне охвата периода или не оценивается никем — доли фонда не берут"
                  >
                    Не берут долю:
                  </span>
                  <span className="font-bold text-lg text-slate-300" data-testid="not-in-pool-count">
                    {notInPool.length}
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Сумма баллов:</span>
                <span className="font-bold text-lg text-amber-400">{formatNumber(totalPoints, 2)}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-slate-700">
                <span className="text-slate-400 text-sm">Итого бонусов:</span>
                <span
                  className="font-bold text-lg text-emerald-400"
                  data-testid="total-bonuses"
                >
                  {formatCurrency(totalBonuses)}
                </span>
              </div>
              {calculatedValues.budget > 0 && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Сходится с бюджетом:</span>
                  <span
                    className={Math.abs(totalBonuses - calculatedValues.budget) < 0.005
                      ? 'text-emerald-400 font-semibold'
                      : 'text-red-400 font-semibold'}
                    data-testid="budget-reconciliation"
                  >
                    {Math.abs(totalBonuses - calculatedValues.budget) < 0.005
                      ? 'да, до копейки'
                      : `нет, расхождение ${formatCurrency(totalBonuses - calculatedValues.budget)}`}
                  </span>
                </div>
              )}
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
                <th
                  className="text-center px-4 py-4 text-sm font-semibold text-gray-600"
                  title="Доля = итоговый балл / сумма итоговых баллов"
                >
                  Доля фонда
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
                  <td className="px-4 py-4 text-center text-sm text-gray-600" data-testid="share-cell">
                    {totalPoints > 0 ? `${(emp.share * 100).toFixed(2)} %` : '—'}
                  </td>
                  <td className="px-4 py-4 text-center">
                    {calculatedValues.budget > 0 && totalPoints > 0 ? (
                      <span
                        className="inline-flex items-center px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 font-bold text-lg border border-amber-200"
                        data-testid="bonus-cell"
                      >
                        {formatCurrency(emp.bonus)}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">
                        {calculatedValues.budget > 0
                          ? 'Нет оценок — распределять нечего'
                          : 'Введите бюджет или стоимость балла'}
                      </span>
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
                <td className="px-4 py-4 text-center text-sm text-gray-600">
                  {totalPoints > 0 ? '100.00 %' : '—'}
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

      {/* Кто НЕ берёт долю фонда, поимённо (D-0825-14). Список исключённых
          обязан быть виден: иначе правило работает молча, и понять, почему
          доля соседа выросла, нельзя ниоткуда. */}
      {notInPool.length > 0 && (
        <div
          className="mt-6 bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
          data-testid="not-in-pool-list"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            Не берут долю фонда: {notInPool.length}
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            Правило одно — «нет результата оценки в этом периоде, значит нет доли фонда». Никаких
            списков идентификаторов: состав меняется сам, когда меняется охват периода или
            пометка «подлежит оценке» в «Сотрудниках».
          </p>
          <ul className="space-y-2 list-none">
            {notInPool.map(emp => (
              <li
                key={emp.id}
                className="flex flex-wrap items-center gap-2 text-sm border-b border-gray-50 pb-2 last:border-0"
                data-testid="not-in-pool-row"
              >
                <span className="font-medium text-gray-900">{emp.full_name}</span>
                {emp.job_title && <span className="text-gray-500">· {emp.job_title}</span>}
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-amber-50 text-amber-800 border-amber-200">
                  {emp.is_in_scope === false
                    ? 'вне охвата периода'
                    : 'не оценивается никем'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default BonusCalculation;

