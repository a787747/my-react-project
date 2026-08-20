/**
 * AdminScoreCalculator - Страница детальной калькуляции итоговых баллов
 * 
 * Назначение: Выбор сотрудников и отображение пошагового расчёта их итоговых баллов
 * Доступ: admin только
 * 
 * Функционал:
 * - Мультиселект сотрудников для сравнения
 * - Детальная калькуляция по формуле с коэффициентами
 * - Сравнение сотрудников бок о бок
 * - Экспорт в CSV
 */

import React, { useState, useMemo } from 'react';
import { Calculator, Download, RefreshCw, Play, Users, AlertCircle } from 'lucide-react';

// Компоненты
import { LoadingSpinner } from '../components/common';
import { EmployeeSelector, CalculationCard } from '../components/admin';

// Хуки
import { useScoreCalculation } from '../hooks/useScoreCalculation';

const AdminScoreCalculator = () => {
  // Хук для данных калькуляции
  const {
    employees,
    loading,
    error,
    period,
    campaignActive,
    fetchData,
    getEmployeeCalculation
  } = useScoreCalculation();

  // Выбранные сотрудники (массив ID)
  const [selectedIds, setSelectedIds] = useState([]);
  
  // Показывать ли результаты калькуляции
  const [showCalculations, setShowCalculations] = useState(false);

  // Рассчитанные данные калькуляций для выбранных сотрудников
  const calculations = useMemo(() => {
    if (!showCalculations) return [];
    return selectedIds
      .map(id => getEmployeeCalculation(id))
      .filter(Boolean);
  }, [selectedIds, showCalculations, getEmployeeCalculation]);

  // Собираем все уникальные критерии из всех калькуляций для синхронизации
  const allCriteria = useMemo(() => {
    if (calculations.length === 0) return [];
    
    // Собираем все критерии из всех сотрудников
    const criteriaMap = new Map();
    calculations.forEach(calc => {
      calc.criteria.forEach(crit => {
        if (!criteriaMap.has(crit.criteria_id)) {
          criteriaMap.set(crit.criteria_id, crit);
        }
      });
    });
    
    // Сортируем: сначала общие, потом проектные, потом менеджерские, потом c-level
    const sortedCriteria = Array.from(criteriaMap.values()).sort((a, b) => {
      const orderMap = {
        'all': 1,
        'project_participants': 2,
        'project': 3,
        'tender': 4,
        'managers_only': 5
      };
      
      // c_level_only критерии в конце
      if (a.c_level_only && !b.c_level_only) return 1;
      if (!a.c_level_only && b.c_level_only) return -1;
      
      const orderA = orderMap[a.target_audience] || 10;
      const orderB = orderMap[b.target_audience] || 10;
      
      if (orderA !== orderB) return orderA - orderB;
      
      // При одинаковой категории сортируем по названию
      return (a.criteria_title || '').localeCompare(b.criteria_title || '');
    });
    
    return sortedCriteria;
  }, [calculations]);

  // Показать калькуляцию
  const handleShowCalculation = () => {
    setShowCalculations(true);
  };

  // Убрать сотрудника из сравнения
  const handleRemoveFromCalculation = (employeeId) => {
    setSelectedIds(prev => prev.filter(id => id !== employeeId));
  };

  // Сброс
  const handleReset = () => {
    setSelectedIds([]);
    setShowCalculations(false);
  };

  // Экспорт в CSV
  const handleExportCSV = () => {
    if (calculations.length === 0) return;

    // Формируем заголовки на основе всех критериев
    const criteriaHeaders = allCriteria.map(c => c.criteria_title);
    const headers = [
      'Сотрудник',
      'Отдел',
      'Должность',
      'Грейд',
      'Коэф. грейда',
      ...criteriaHeaders.flatMap(title => [
        `${title} (расчёт)`
      ]),
      'Σ взвешенных',
      'Итоговый балл'
    ];

    // Формируем строки данных
    const rows = calculations.map(calc => {
      // Создаём карту критериев сотрудника
      const criteriaMap = {};
      calc.criteria.forEach(c => {
        criteriaMap[c.criteria_id] = c;
      });

      // Данные по критериям (в порядке allCriteria)
      const criteriaData = allCriteria.map(crit => {
        const empCrit = criteriaMap[crit.criteria_id];
        if (empCrit) {
          return `${empCrit.raw_score.toFixed(1)}×${empCrit.score_coefficient.toFixed(1)}×${empCrit.weight.toFixed(1)}=${empCrit.weighted_score.toFixed(2)}`;
        }
        return '—';
      });

      return [
        calc.full_name,
        calc.department_name || '',
        calc.job_title || '',
        calc.grade_code || '',
        calc.grade_coefficient.toFixed(2),
        ...criteriaData,
        calc.total_weighted_sum.toFixed(2),
        calc.final_score.toFixed(2)
      ];
    });

    // Формируем CSV
    const csvContent = [
      headers.join(';'),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(';'))
    ].join('\n');

    // Скачиваем файл
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `калькуляция_баллов_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка данных..." />;
  }

  // Ошибка
  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-700 font-medium">{error}</p>
          <button
            onClick={fetchData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6 flex flex-col lg:flex-row justify-between items-start gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Calculator className="w-8 h-8 text-indigo-500" />
            Калькуляция баллов
          </h1>
          <p className="text-gray-500 mt-2">
            Детальный расчёт итоговых баллов с учётом весов и коэффициентов
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {period
              ? `Период: ${period.name}${campaignActive ? ' — активен' : ` — ${period.status}`}`
              : 'Нет активного периода — числа не смешиваются между циклами.'}
          </p>
        </div>

        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors flex items-center gap-2"
            title="Обновить данные"
          >
            <RefreshCw className="w-4 h-4" />
            Обновить
          </button>
          {calculations.length > 0 && (
            <button
              onClick={handleExportCSV}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Экспорт CSV
            </button>
          )}
        </div>
      </div>

      {/* Панель выбора сотрудников */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-end">
          {/* Селектор сотрудников */}
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Выберите сотрудников для калькуляции
            </label>
            <EmployeeSelector
              employees={employees}
              selected={selectedIds}
              onChange={(ids) => {
                setSelectedIds(ids);
                if (showCalculations) setShowCalculations(false);
              }}
              placeholder="Найти сотрудника по имени, отделу или грейду..."
            />
          </div>

          {/* Кнопки действий */}
          <div className="flex gap-2 flex-shrink-0">
            {selectedIds.length > 0 && (
              <button
                onClick={handleReset}
                className="px-4 py-2.5 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 transition-colors font-medium"
              >
                Сбросить
              </button>
            )}
            <button
              onClick={handleShowCalculation}
              disabled={selectedIds.length === 0}
              className={`
                px-5 py-2.5 rounded-xl font-semibold flex items-center gap-2 transition-all
                ${selectedIds.length > 0
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }
              `}
            >
              <Play className="w-4 h-4" />
              Показать калькуляцию
            </button>
          </div>
        </div>

        {/* Подсказка */}
        {selectedIds.length === 0 && (
          <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
            <Users className="w-4 h-4" />
            <span>Выберите одного или нескольких сотрудников для сравнения калькуляций</span>
          </div>
        )}
      </div>

      {/* Формула расчёта */}
      {showCalculations && calculations.length > 0 && (
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-100 p-4 mb-6">
          <p className="text-sm font-medium text-indigo-800">
            Формула расчёта итогового балла:
          </p>
          <p className="text-sm text-indigo-700 mt-1 font-mono bg-white/50 px-3 py-2 rounded-lg inline-block">
            Σ(оценка × коэфф_оценки × вес_критерия) × коэфф_грейда
          </p>
        </div>
      )}

      {/* Карточки калькуляций */}
      {showCalculations && calculations.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {calculations.map(calc => (
            <CalculationCard
              key={calc.employee_id}
              calculation={calc}
              allCriteria={allCriteria}
              onRemove={() => handleRemoveFromCalculation(calc.employee_id)}
            />
          ))}
        </div>
      )}

      {/* Пустое состояние после показа */}
      {showCalculations && calculations.length === 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
          <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Нет данных для отображения</p>
          <p className="text-sm text-gray-400 mt-1">Возможно, у выбранных сотрудников нет оценок за активный период</p>
        </div>
      )}
    </div>
  );
};

export default AdminScoreCalculator;

