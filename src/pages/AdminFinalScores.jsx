/**
 * AdminFinalScores - Страница матрицы итоговых баллов
 * 
 * Назначение: Сводная таблица итоговых баллов сотрудников с учетом весов и коэффициентов
 * Доступ: admin, c_level
 * 
 * Использует компоненты:
 * - FinalScoresMatrixTable - основная таблица
 * - MatrixFilters - панель фильтров
 * - EmployeeScoresModal - модальное окно просмотра всех оценок сотрудника
 * - LoadingSpinner - индикатор загрузки
 * 
 * Функционал:
 * - Отображение итоговых баллов всех сотрудников
 * - Суммы и средние значения
 * - Фильтрация и сортировка
 * - Экспорт данных (опционально)
 */

import React, { useState } from 'react';
import { Award, Download, RefreshCw, AlertTriangle } from 'lucide-react';

// Компоненты
import { LoadingSpinner } from '../components/common';
import MatrixFilters from '../components/admin/MatrixFilters';
import FinalScoresMatrixTable from '../components/admin/FinalScoresMatrixTable';
import EmployeeScoresModal from '../components/admin/EmployeeScoresModal';

// Хуки
import { useFinalScoresMatrix } from '../hooks/useFinalScoresMatrix';

const AdminFinalScores = () => {
  // Хук для работы с матрицей итоговых баллов
  const {
    employees,
    criteriaList,
    period,
    campaignActive,
    loading,
    error,
    filters,
    filterOptions,
    filteredEmployees,
    sorting,
    totals,
    activeFiltersCount,
    setFilters,
    clearFilters,
    setSorting,
    fetchData
  } = useFinalScoresMatrix();

  // Состояния модальных окон
  const [scoresModal, setScoresModal] = useState({ isOpen: false, employee: null });
  
  // Состояние панели фильтров
  const [showFilters, setShowFilters] = useState(true);

  // Клик по сотруднику - показать все оценки
  const handleEmployeeClick = (employee) => {
    setScoresModal({ isOpen: true, employee });
  };

  // Закрыть модалку
  const handleCloseModal = () => {
    setScoresModal({ isOpen: false, employee: null });
  };

  // Экспорт в CSV
  const handleExportCSV = () => {
    // Заголовки: Сотрудник, Отдел, Грейд, [критерии...], Сумма, Итог
    const headers = [
      'Сотрудник', 
      'Отдел', 
      'Грейд',
      'Коэф. грейда',
      // Состояние человека в периоде едет в файл: без него выгрузка не
      // отличает «не оценен» от «вне охвата», и таблица из нулей выглядит
      // как платёжная ведомость.
      'Берёт долю фонда',
      ...criteriaList.map(c => `${c.title} (вес ${c.weight})`),
      'Σ баллов',
      'Итог'
    ];
    
    const rows = filteredEmployees.map(emp => [
      emp.full_name,
      emp.department_name || '',
      emp.grade_code || '',
      emp.grade_coefficient?.toFixed(2) || '1.00',
      emp.takes_bonus_share === false
        ? (emp.is_in_scope === false ? 'нет — вне охвата' : 'нет — не оценивается никем')
        : 'да',
      // Пустая клетка там, где на экране прочерк: '0' сообщал бы, что человека
      // оценили нулём, а «н/п» и «ещё не оценен» — не ноль.
      ...criteriaList.map(c => {
        const score = emp.criteria_scores?.[c.id];
        return score === null || score === undefined ? '' : score.toFixed(2);
      }),
      emp.weighted_sum?.toFixed(2) || '0.00',
      emp.final_weighted_score?.toFixed(2) || '0.00'
    ]);
    
    const csvContent = [
      headers.join(';'),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(';'))
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `итоговые_баллы_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка итоговых баллов..." />;
  }

  // Ошибка загрузки: без весов, коэффициентов или матрицы таблица была бы
  // правдоподобной, но неверной — показываем ошибку, а не числа (BUG-030).
  if (error) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <div className="max-w-2xl mx-auto mt-12 bg-white rounded-xl shadow-sm border border-red-200 p-8 text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <h2 className="text-xl font-bold text-gray-900">Итоговые баллы не рассчитаны</h2>
          <p className="text-sm text-red-700 mt-3">{error}</p>
          <p className="text-sm text-gray-500 mt-2">
            Числа не показаны намеренно: без коэффициентов таблица выглядела бы
            правдоподобно, но была бы невзвешенной.
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
            <Award className="w-8 h-8 text-amber-500" />
            Итоговые баллы
          </h1>
          <p className="text-gray-500 mt-2">
            Матрица итоговых баллов сотрудников с учетом весов и коэффициентов
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
      <FinalScoresMatrixTable
        employees={filteredEmployees}
        criteriaList={criteriaList}
        sorting={sorting}
        totals={totals}
        onSort={setSorting}
        onEmployeeClick={handleEmployeeClick}
      />

      {/* Модальное окно просмотра всех оценок */}
      <EmployeeScoresModal
        isOpen={scoresModal.isOpen}
        employee={scoresModal.employee}
        period={period}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default AdminFinalScores;

