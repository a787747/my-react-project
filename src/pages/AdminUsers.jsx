/**
 * AdminUsers - Страница управления пользователями
 * 
 * Назначение: Просмотр списка сотрудников, фильтрация, добавление и редактирование
 * Доступ: admin, c_level, hr (редактирование и все пользователи)
 *         остальные - только просмотр своих подчинённых
 * 
 * Использует компоненты:
 * - UserTable - таблица пользователей
 * - UserFilters - панель фильтров
 * - UserModal - модальное окно создания/редактирования
 * - Toast - уведомления
 * - LoadingSpinner - индикатор загрузки
 * - Pagination - пагинация
 * 
 * Использует хуки:
 * - useUsers - загрузка и сохранение пользователей
 * - useUserFilters - логика фильтрации
 */

import React, { useState, useMemo, useEffect } from 'react';
import { Users, Plus, Info, Upload } from 'lucide-react';

// Компоненты
import { Toast, LoadingSpinner, Pagination } from '../components/common';
import { UserTable, UserFilters, UserModal, UserImportModal } from '../components/admin';
import SelfReviewDetailsModal from '../components/SelfReviewDetailsModal';
import ManagerEvaluationDetailsModal from '../components/ManagerEvaluationDetailsModal';
import SubordinateEvaluationsModal from '../components/SubordinateEvaluationsModal';

// API
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';

// Хуки
import { useUsers } from '../hooks/useUsers';
import { useUserFilters } from '../hooks/useUserFilters';

// Утилиты
import logger from '../utils/logger';

// Константы
import { UI_CONFIG } from '../config/constants';
import { canViewAnalytics } from '../utils/permissions';

/**
 * Рекурсивно находит всех подчинённых пользователя
 * @param {number} managerId - ID менеджера
 * @param {array} allUsers - все пользователи
 * @param {Set} visited - уже посещённые ID (для защиты от циклов)
 * @returns {array} - массив подчинённых
 */
const getAllSubordinates = (managerId, allUsers, visited = new Set()) => {
  if (visited.has(managerId)) return [];
  visited.add(managerId);
  
  const directSubordinates = allUsers.filter(u => u.manager_id === managerId);
  let allSubordinates = [...directSubordinates];
  
  // Рекурсивно добавляем подчинённых подчинённых
  directSubordinates.forEach(sub => {
    const nested = getAllSubordinates(sub.id, allUsers, visited);
    allSubordinates = [...allSubordinates, ...nested];
  });
  
  return allSubordinates;
};

const AdminUsers = ({ user }) => {
  // Проверка прав доступа - Admin, C-level, HR видят всех и могут редактировать
  const isFullAccess = ['admin', 'c_level', 'hr'].includes(user?.role);
  const canEdit = isFullAccess;
  const canOpenDossier = canViewAnalytics(user?.role);

  // Хук для работы с пользователями
  const { 
    users, 
    options, 
    loading, 
    saving, 
    saveUser,
    importUsers
  } = useUsers();

  // Состояние для статусов оценок
  const [selfReviewsStatus, setSelfReviewsStatus] = useState({});
  const [evaluationStatuses, setEvaluationStatuses] = useState({});

  // Состояние для модальных окон оценок
  const [selectedEmployeeForSelfReview, setSelectedEmployeeForSelfReview] = useState(null);
  const [isSelfReviewModalOpen, setIsSelfReviewModalOpen] = useState(false);
  const [selectedEmployeeForManager, setSelectedEmployeeForManager] = useState(null);
  const [isManagerModalOpen, setIsManagerModalOpen] = useState(false);
  const [selectedEmployeeForSubordinates, setSelectedEmployeeForSubordinates] = useState(null);
  const [isSubordinatesModalOpen, setIsSubordinatesModalOpen] = useState(false);

  // Загрузка статусов оценок
  useEffect(() => {
    const loadStatuses = async () => {
      if (users.length === 0) return;

      try {
        setLoadingStatuses(true);
        
        const [selfReviewsRes, hrStatusRes] = await Promise.all([
          apiClient.get(API_ENDPOINTS.CHECK_SELF_REVIEWS).catch(() => ({ data: {} })),
          apiClient.get(API_ENDPOINTS.HR_EVALUATION_STATUS).catch(() => ({ data: { employees: [] } }))
        ]);
        
        // Обрабатываем самооценки
        const selfReviews = selfReviewsRes.data?.data || {};
        setSelfReviewsStatus(selfReviews);
        
        // Обрабатываем HR статусы
        const hrEmployees = hrStatusRes.data?.employees || [];
        const statusMap = {};
        hrEmployees.forEach(emp => {
          statusMap[emp.id] = {
            was_evaluated_by_manager: emp.was_evaluated_by_manager,
            subordinate_evaluations_received: emp.subordinate_evaluations_received || 0
          };
        });
        setEvaluationStatuses(statusMap);
      } catch (err) {
        logger.error('Ошибка загрузки статусов оценок:', err);
      } finally {
        setLoadingStatuses(false);
      }
    };

    loadStatuses();
  }, [users.length]);

  // Обработчики для модальных окон
  const handleSelfReviewClick = (employee) => {
    // Открываем только если есть самооценка
    const selfReviewData = selfReviewsStatus[employee.id];
    if (selfReviewData?.has_self_review || employee.self_review_done) {
      setSelectedEmployeeForSelfReview(employee);
      setIsSelfReviewModalOpen(true);
    }
  };

  const handleManagerEvaluationClick = (employee) => {
    setSelectedEmployeeForManager(employee);
    setIsManagerModalOpen(true);
  };

  const handleSubordinateEvaluationClick = (employee) => {
    setSelectedEmployeeForSubordinates(employee);
    setIsSubordinatesModalOpen(true);
  };

  // Фильтрация пользователей на основе роли
  const visibleUsers = useMemo(() => {
    if (isFullAccess) {
      return users;
    }
    // Для остальных - показываем подчинённых и их подчинённых
    const subordinates = getAllSubordinates(user?.id, users);
    
    // Если нет подчинённых - показываем самого себя
    if (subordinates.length === 0) {
      const currentUser = users.find(u => u.id === user?.id);
      return currentUser ? [currentUser] : [];
    }
    
    return subordinates;
  }, [users, user?.id, isFullAccess]);

  // Добавляем статусы оценок к пользователям
  const usersWithStatus = useMemo(() => {
    return visibleUsers.map(u => ({
      ...u,
      manager_review_status: evaluationStatuses[u.id]?.was_evaluated_by_manager ? 'completed' : null,
      subordinate_evaluations_count: evaluationStatuses[u.id]?.subordinate_evaluations_received || 0
    }));
  }, [visibleUsers, evaluationStatuses]);

  // Хук для фильтрации (работает с usersWithStatus)
  const {
    filters,
    searchInput,
    currentPage,
    filteredUsers,
    paginatedUsers,
    totalPages,
    setSearchInput,
    handleFilterChange,
    resetFilters,
    setCurrentPage
  } = useUserFilters(usersWithStatus, UI_CONFIG.ITEMS_PER_PAGE);

  // Состояние модального окна
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Состояние модального окна импорта
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Состояние уведомлений
  const [toast, setToast] = useState(null);

  // Показать уведомление
  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  // Открытие модального окна
  const handleOpenModal = (targetUser = null) => {
    if (!canEdit) return;
    setCurrentUser(targetUser);
    setIsModalOpen(true);
  };

  // Закрытие модального окна
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setCurrentUser(null);
  };

  // Сохранение пользователя
  const handleSave = async (formData, existingUserId) => {
    const result = await saveUser(formData, existingUserId);
    
    if (result.success) {
      showToast(
        existingUserId ? 'Сотрудник успешно обновлен' : 'Сотрудник успешно добавлен',
        'success'
      );
      handleCloseModal();
    } else {
      showToast(result.error || 'Ошибка при сохранении', 'error');
    }
  };

  // Импорт пользователей из файла
  const handleImport = async (usersData) => {
    const result = await importUsers(usersData);
    
    if (result.success) {
      showToast(`Успешно импортировано ${result.count} сотрудников`, 'success');
    } else {
      showToast(result.error || 'Ошибка при импорте', 'error');
      throw new Error(result.error);
    }
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка данных..." />;
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Toast уведомления */}
      {toast && (
        <Toast 
          message={toast.message} 
          type={toast.type} 
          onClose={() => setToast(null)} 
        />
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-indigo-600" />
            {isFullAccess ? 'Сотрудники' : 'Моя команда'}
          </h1>
          <p className="text-gray-500">
            {isFullAccess 
              ? `Всего: ${users.length} | Найдено: `
              : `Подчинённых: ${visibleUsers.length} | Найдено: `
            }
            <span className="text-indigo-600 font-bold">{filteredUsers.length}</span>
          </p>
        </div>
        
        {canEdit && (
          <div className="flex gap-3">
            <button 
              onClick={() => setIsImportModalOpen(true)}
              className="flex items-center gap-2 bg-white text-indigo-600 border border-indigo-200 px-5 py-2.5 rounded-lg hover:bg-indigo-50 transition-colors font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              aria-label="Импорт/Экспорт Excel"
            >
              <Upload className="w-5 h-5" /> Excel
            </button>
            <button 
              onClick={() => handleOpenModal()}
              className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              aria-label="Добавить нового сотрудника"
            >
              <Plus className="w-5 h-5" /> Добавить
            </button>
          </div>
        )}
      </div>

      {/* Информационное сообщение для обычных пользователей */}
      {!isFullAccess && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <p className="text-blue-800 text-sm">
            {visibleUsers.length === 1 && visibleUsers[0]?.id === user?.id
              ? 'У вас нет подчинённых, поэтому здесь отображается только ваш профиль.'
              : 'Здесь отображаются ваши прямые подчинённые и их подчинённые. Для просмотра полного списка сотрудников обратитесь к HR или администратору.'
            }
          </p>
        </div>
      )}

      {/* Панель фильтров */}
      <UserFilters
        searchInput={searchInput}
        filters={filters}
        options={options}
        onSearchChange={setSearchInput}
        onFilterChange={handleFilterChange}
        onReset={resetFilters}
      />

      {/* Таблица пользователей */}
      <UserTable
        users={paginatedUsers}
        canEdit={canEdit}
        onEdit={handleOpenModal}
        selfReviewsStatus={selfReviewsStatus}
        onRowClick={handleSelfReviewClick}
        onManagerEvaluationClick={canOpenDossier ? handleManagerEvaluationClick : undefined}
        onSubordinateEvaluationClick={canOpenDossier ? handleSubordinateEvaluationClick : undefined}
        showSelfReviewScore={true}
        showThreeColumns={true}
      />

      {/* Пагинация */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalItems={filteredUsers.length}
        itemsPerPage={UI_CONFIG.ITEMS_PER_PAGE}
        onPageChange={setCurrentPage}
      />

      {/* Модальное окно редактирования */}
      <UserModal
        isOpen={isModalOpen && canEdit}
        user={currentUser}
        options={options}
        saving={saving}
        currentUserRole={user?.role}
        onClose={handleCloseModal}
        onSave={handleSave}
      />

      {/* Модальное окно импорта/экспорта */}
      <UserImportModal
        isOpen={isImportModalOpen && canEdit}
        options={options}
        users={users}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImport}
      />

      {/* Модальное окно деталей самооценки */}
      <SelfReviewDetailsModal
        isOpen={isSelfReviewModalOpen}
        employee={selectedEmployeeForSelfReview}
        onClose={() => {
          setIsSelfReviewModalOpen(false);
          setSelectedEmployeeForSelfReview(null);
        }}
      />

      {/* Модальное окно оценок от руководителя */}
      <ManagerEvaluationDetailsModal
        isOpen={isManagerModalOpen}
        employee={selectedEmployeeForManager}
        onClose={() => {
          setIsManagerModalOpen(false);
          setSelectedEmployeeForManager(null);
        }}
      />

      {/* Модальное окно оценок от подчинённых */}
      <SubordinateEvaluationsModal
        isOpen={isSubordinatesModalOpen}
        employee={selectedEmployeeForSubordinates}
        currentUser={user}
        onClose={() => {
          setIsSubordinatesModalOpen(false);
          setSelectedEmployeeForSubordinates(null);
        }}
      />
    </div>
  );
};

export default AdminUsers;
