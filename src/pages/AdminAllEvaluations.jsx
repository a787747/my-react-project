/**
 * AdminAllEvaluations - Страница всех оценок сотрудников
 * 
 * Назначение: Просмотр сводной информации по оценкам всех сотрудников
 * Доступ: admin, c_level
 * 
 * Использует компоненты:
 * - AllEvaluationsTable - таблица всех оценок
 * - AllEvaluationsDetailsModal - модальное окно деталей
 * - LoadingSpinner - индикатор загрузки
 * 
 * Использует хуки:
 * - useAllEvaluations - загрузка данных
 */

import React, { useState, useEffect } from 'react';
import { Users } from 'lucide-react';

// Компоненты
import { LoadingSpinner, PeriodBanner } from '../components/common';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import AllEvaluationsTable from '../components/admin/AllEvaluationsTable';
import AllEvaluationsDetailsModal from '../components/admin/AllEvaluationsDetailsModal';

// Хуки
import { useAllEvaluations } from '../hooks/useAllEvaluations';

const AdminAllEvaluations = () => {
  // Хук для работы с оценками
  const {
    employees,
    period,
    campaignActive,
    loading,
    detailsData,
    loadingDetails,
    fetchDetails,
    clearDetails
  } = useAllEvaluations();
  const [periodCatalog, setPeriodCatalog] = useState([]);

  useEffect(() => {
    apiClient.get(API_ENDPOINTS.PERIODS)
      .then((response) => setPeriodCatalog(response.data?.data || []))
      .catch(() => setPeriodCatalog([]));
  }, []);

  // Состояние модального окна
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [detailType, setDetailType] = useState('all');

  // Форматирование даты
  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  // Открыть детали с указанием типа
  const handleOpenDetails = (employee, type = 'all', evalId = null) => {
    setSelectedEmployee(employee);
    setDetailType(type);
    setIsModalOpen(true);
    fetchDetails(employee.id, type, evalId);
  };

  // Закрыть модалку
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
    setDetailType('all');
    clearDetails();
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка оценок..." />;
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Users className="w-8 h-8 text-indigo-600" />
          Все оценки сотрудников
        </h1>
        <p className="text-gray-500 mt-2">
          Полная таблица с самооценками, оценками от руководителей и оценками подчинённым.
          Нажмите на оценку для просмотра деталей.
        </p>
      </div>

      <PeriodBanner
        period={period}
        campaignActive={campaignActive}
        emptyCopy="Нет активного периода — таблица не смешивает строки."
        draftName={periodCatalog.find((item) => item.status === 'draft')?.name}
      />

      {/* Таблица */}
      <AllEvaluationsTable
        employees={employees}
        formatDate={formatDate}
        onViewDetails={handleOpenDetails}
      />

      {/* Модальное окно */}
      <AllEvaluationsDetailsModal
        isOpen={isModalOpen}
        employee={selectedEmployee}
        detailsData={detailsData}
        detailType={detailType}
        loading={loadingDetails}
        formatDate={formatDate}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default AdminAllEvaluations;
