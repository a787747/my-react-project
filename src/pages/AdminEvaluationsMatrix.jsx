/**
 * AdminEvaluationsMatrix - Страница матрицы оценок
 * 
 * Назначение: Сводная таблица всех оценок сотрудников по всем критериям
 * Доступ: admin, c_level
 * 
 * Использует компоненты:
 * - EvaluationsMatrixTable - основная таблица
 * - MatrixFilters - панель фильтров
 * - CLevelEvaluationModal - модальное окно C-level оценки
 * - EmployeeScoresModal - модальное окно просмотра всех оценок сотрудника
 * - ScoreDetailModal - модальное окно просмотра одной оценки
 * - LoadingSpinner - индикатор загрузки
 * 
 * Логика кликов:
 * - Имя сотрудника → просмотр всех оценок
 * - C-level зона → оценка/переоценка
 * - Ячейка с оценкой → просмотр детальной оценки
 */

import React, { useState, useEffect } from 'react';
import { Users, Download, FileSpreadsheet, AlertCircle } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { canReceiveCLevel } from '../utils/matrixUtils';

// Компоненты
import { LoadingSpinner } from '../components/common';
import MatrixFilters from '../components/admin/MatrixFilters';
import EvaluationsMatrixTable from '../components/admin/EvaluationsMatrixTable';
import CLevelEvaluationModal from '../components/admin/CLevelEvaluationModal';
import EmployeeScoresModal from '../components/admin/EmployeeScoresModal';
import ScoreDetailModal from '../components/admin/ScoreDetailModal';

// Хуки
import { useEvaluationsMatrix } from '../hooks/useEvaluationsMatrix';

// Утилиты
import { exportMatrixToExcel } from '../utils/excelExport';

const AdminEvaluationsMatrix = ({ user }) => {
  // Хук для работы с матрицей
  const {
    employees,
    period,
    campaignActive,
    loading,
    filters,
    filterOptions,
    filteredEmployees,
    sorting,
    activeFiltersCount,
    setFilters,
    clearFilters,
    setSorting,
    submitCLevelEvaluation,
    submitScoreCorrection
  } = useEvaluationsMatrix();

  const [periodCatalog, setPeriodCatalog] = useState([]);

  useEffect(() => {
    apiClient.get(API_ENDPOINTS.PERIODS)
      .then((response) => setPeriodCatalog(response.data?.data || []))
      .catch(() => setPeriodCatalog([]));
  }, []);

  // Состояния модальных окон
  const [cLevelModal, setCLevelModal] = useState({ isOpen: false, employee: null });
  const [scoresModal, setScoresModal] = useState({ isOpen: false, employee: null });
  const [detailModal, setDetailModal] = useState({ isOpen: false, employee: null, criterion: null, group: null });
  
  const [submitting, setSubmitting] = useState(false);
  
  // Состояние панели фильтров
  const [showFilters, setShowFilters] = useState(true);
  
  // Состояние экспорта
  const [exporting, setExporting] = useState(false);

  // Экспорт в Excel
  const handleExportToExcel = async () => {
    try {
      setExporting(true);
      
      // Экспортируем отфильтрованные данные
      const dataToExport = filteredEmployees.length > 0 ? filteredEmployees : employees;
      
      const filename = exportMatrixToExcel(dataToExport, 'matrix_ocenok');
      
      // Показываем уведомление
      alert(`Файл "${filename}" успешно сохранён!`);
    } catch (error) {
      console.error('Ошибка экспорта:', error);
      alert('Ошибка при экспорте данных');
    } finally {
      setExporting(false);
    }
  };

  // Клик по имени сотрудника - показать все оценки
  const handleEmployeeNameClick = (employee) => {
    setScoresModal({ isOpen: true, employee });
  };

  // Клик по C-level зоне - открыть модалку оценки
  const handleCLevelZoneClick = (employee) => {
    if (!canReceiveCLevel(employee, period)) return;
    setCLevelModal({ isOpen: true, employee });
  };

  // Клик по ячейке с оценкой - показать детали
  const handleScoreClick = (employee, criterion, group) => {
    setDetailModal({ isOpen: true, employee, criterion, group });
  };

  // Закрыть модалку C-level
  const handleCloseCLevelModal = () => {
    setCLevelModal({ isOpen: false, employee: null });
  };

  // Закрыть модалку всех оценок
  const handleCloseScoresModal = () => {
    setScoresModal({ isOpen: false, employee: null });
  };

  // Закрыть модалку деталей оценки
  const handleCloseDetailModal = () => {
    setDetailModal({ isOpen: false, employee: null, criterion: null, group: null });
  };

  // Отправить C-level оценку
  const handleSubmitCLevelEvaluation = async (grades) => {
    if (!cLevelModal.employee) return;

    setSubmitting(true);
    const result = await submitCLevelEvaluation(
      user.id,
      cLevelModal.employee.id,
      grades,
      cLevelModal.employee.actor_c_level_evaluation_id
    );
    setSubmitting(false);

    if (result.success) {
      alert('C-level оценка сохранена!');
      handleCloseCLevelModal();
    } else {
      alert(result.error || 'Ошибка при сохранении оценки');
    }
  };

  // Переход из просмотра всех оценок к C-level оценке
  const handleCLevelFromScores = (employee) => {
    setCLevelModal({ isOpen: true, employee });
  };

  // Отправка корректировки оценки
  const handleScoreCorrection = async (employeeId, criteriaId, score, correctionLevel = 'c_level') => {
    const result = await submitScoreCorrection(user.id, employeeId, criteriaId, score, correctionLevel);
    if (result.success) {
      // Обновляем criterion в текущем modals state чтобы показать новую корректировку
      const correctionField = correctionLevel === 'c_level' ? 'c_level_correction' : 'mid_level_correction';
      setDetailModal(prev => ({
        ...prev,
        criterion: {
          ...prev.criterion,
          [correctionField]: score
        }
      }));
    } else {
      throw new Error(result.error);
    }
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка матрицы оценок..." />;
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-indigo-600" />
            Матрица оценок
          </h1>
          <p className="text-gray-500 mt-2">
            Все ячейки — из одного периода. По умолчанию это активный период.
          </p>
        </div>
        
        {/* Кнопка экспорта */}
        <button
          onClick={handleExportToExcel}
          disabled={exporting || employees.length === 0}
          className="inline-flex items-center gap-2 px-5 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-xl shadow-sm transition-colors"
        >
          {exporting ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Экспорт...</span>
            </>
          ) : (
            <>
              <FileSpreadsheet className="w-5 h-5" />
              <span>Выгрузить в Excel</span>
            </>
          )}
        </button>
      </div>
      
      {period ? (
        <div className={`mb-4 p-3 rounded-lg border text-sm ${
          campaignActive
            ? 'bg-indigo-50 border-indigo-200 text-indigo-800'
            : 'bg-amber-50 border-amber-200 text-amber-800'
        }`}>
          Период: <strong>{period.name}</strong>
          {period.status === 'active' && period.is_active ? ' — активен' : ` — ${period.status}`}
          {!campaignActive && ' · запись C-level и корректировок доступна только в активном периоде'}
        </div>
      ) : (
        <div className="mb-4 p-4 rounded-lg border border-amber-200 bg-amber-50 text-amber-900">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Нет активного периода — матрица не смешивает строки.</p>
              <p className="text-sm mt-1">
                {periodCatalog.find((item) => item.status === 'draft')
                  ? `${periodCatalog.find((item) => item.status === 'draft').name} сейчас черновик. Ячейки появятся после активации.`
                  : 'Активируйте период, чтобы увидеть оценки этого цикла.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Информация об экспорте */}
      {filteredEmployees.length !== employees.length && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2 text-sm text-blue-700">
          <Download className="w-4 h-4" />
          <span>
            При экспорте будут выгружены <strong>{filteredEmployees.length}</strong> из {employees.length} сотрудников (с учётом фильтров)
          </span>
        </div>
      )}

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
      <EvaluationsMatrixTable
        employees={filteredEmployees}
        period={period}
        sorting={sorting}
        onSort={setSorting}
        onEmployeeNameClick={handleEmployeeNameClick}
        onCLevelZoneClick={handleCLevelZoneClick}
        onScoreClick={handleScoreClick}
      />

      {/* Модальное окно C-level оценки */}
      <CLevelEvaluationModal
        isOpen={cLevelModal.isOpen}
        employee={cLevelModal.employee}
        submitting={submitting}
        onClose={handleCloseCLevelModal}
        onSubmit={handleSubmitCLevelEvaluation}
      />

      {/* Модальное окно просмотра всех оценок */}
      <EmployeeScoresModal
        isOpen={scoresModal.isOpen}
        employee={scoresModal.employee}
        period={period}
        onClose={handleCloseScoresModal}
        onCLevelClick={canReceiveCLevel(scoresModal.employee, period) ? handleCLevelFromScores : undefined}
      />

      {/* Модальное окно детальной оценки */}
      <ScoreDetailModal
        isOpen={detailModal.isOpen}
        employee={detailModal.employee}
        criterion={detailModal.criterion}
        group={detailModal.group}
        user={user}
        onClose={handleCloseDetailModal}
        onCorrectionSubmit={handleScoreCorrection}
      />
    </div>
  );
};

export default AdminEvaluationsMatrix;
