/**
 * TeamView - Страница просмотра команды для менеджеров
 * 
 * Назначение: Просмотр списка подчинённых с информацией о самооценках
 * Доступ: manager
 * 
 * Отличие от AdminUsers:
 * - Только просмотр (нет кнопок редактирования)
 * - Показывает только прямых подчинённых и их подчинённых
 * - Отображает баллы самооценок
 * - Возможность просмотра деталей самооценки с комментариями
 * 
 * Использует компоненты:
 * - UserTable - таблица пользователей (режим просмотра)
 * - UserFilters - панель фильтров
 * - LoadingSpinner - индикатор загрузки
 * - Pagination - пагинация
 * - SelfReviewDetailsModal - модальное окно деталей самооценки
 * 
 * Использует хуки:
 * - useUsers - загрузка пользователей
 * - useUserFilters - логика фильтрации
 */

import React, { useMemo, useState, useEffect } from 'react';
import { Users, Info, Star } from 'lucide-react';

// Компоненты
import { LoadingSpinner, Pagination } from '../components/common';
import { UserTable, UserFilters } from '../components/admin';
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

const TeamView = ({ user }) => {
  // Хук для работы с пользователями
  const { 
    users, 
    loading
  } = useUsers();

  // Состояние для самооценок подчинённых
  const [selfReviewsStatus, setSelfReviewsStatus] = useState({});
  
  // Состояние для статусов оценок от менеджера
  const [evaluationStatuses, setEvaluationStatuses] = useState({});

  // Состояние для модального окна самооценки
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Состояние для модального окна оценки менеджера
  const [selectedEmployeeForManager, setSelectedEmployeeForManager] = useState(null);
  const [isManagerModalOpen, setIsManagerModalOpen] = useState(false);

  // Фильтрация пользователей - показываем только подчинённых
  const visibleUsers = useMemo(() => {
    const subordinates = getAllSubordinates(user?.id, users);
    
    // Если нет подчинённых - показываем пустой список
    if (subordinates.length === 0) {
      return [];
    }
    
    return subordinates;
  }, [users, user?.id]);

  // Загрузка статусов самооценок и оценок от менеджера
  useEffect(() => {
    const loadStatuses = async () => {
      if (visibleUsers.length === 0) return;

      try {
        setLoadingSelfReviews(true);
        
        // Загружаем параллельно статусы самооценок и HR статусы оценок
        const [selfReviewsRes, hrStatusRes] = await Promise.all([
          apiClient.get(API_ENDPOINTS.CHECK_SELF_REVIEWS).catch(() => ({ data: {} })),
          apiClient.get(API_ENDPOINTS.HR_EVALUATION_STATUS).catch(() => ({ data: { employees: [] } }))
        ]);
        
        // Обрабатываем самооценки
        const selfReviews = selfReviewsRes.data?.data || {};
        setSelfReviewsStatus(selfReviews);
        
        // Обрабатываем HR статусы (was_evaluated_by_manager, subordinate_evaluations_received)
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
        logger.error('Ошибка загрузки статусов:', err);
      } finally {
        setLoadingSelfReviews(false);
      }
    };

    loadStatuses();
  }, [visibleUsers.length]);

  // Обработчик клика на строку для просмотра самооценки
  const handleRowClick = (employee) => {
    const selfReviewData = selfReviewsStatus[employee.id];
    if (selfReviewData?.has_self_review || employee.self_review_done) {
      setSelectedEmployee(employee);
      setIsModalOpen(true);
    }
  };

  // Закрытие модального окна самооценки
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
  };

  // Обработчик клика на оценку от руководителя
  const handleManagerEvaluationClick = (employee) => {
    setSelectedEmployeeForManager(employee);
    setIsManagerModalOpen(true);
  };

  // Закрытие модального окна оценки от руководителя
  const handleCloseManagerModal = () => {
    setIsManagerModalOpen(false);
    setSelectedEmployeeForManager(null);
  };

  // Состояние для модального окна оценок от сотрудников
  const [selectedEmployeeForSubordinates, setSelectedEmployeeForSubordinates] = useState(null);
  const [isSubordinatesModalOpen, setIsSubordinatesModalOpen] = useState(false);

  // Обработчик клика на оценки от сотрудников
  const handleSubordinateEvaluationClick = (employee) => {
    setSelectedEmployeeForSubordinates(employee);
    setIsSubordinatesModalOpen(true);
  };

  // Закрытие модального окна оценок от сотрудников
  const handleCloseSubordinatesModal = () => {
    setIsSubordinatesModalOpen(false);
    setSelectedEmployeeForSubordinates(null);
  };

  // Добавляем статусы оценок к пользователям
  const usersWithStatus = useMemo(() => {
    return visibleUsers.map(u => ({
      ...u,
      // Оценён ли руководителем
      manager_review_status: evaluationStatuses[u.id]?.was_evaluated_by_manager ? 'completed' : null,
      // Сколько подчинённых оценили этого сотрудника (актуально для руководителей)
      subordinate_evaluations_count: evaluationStatuses[u.id]?.subordinate_evaluations_received || 0
    }));
  }, [visibleUsers, evaluationStatuses]);

  // Хук для фильтрации
  const {
    filters,
    searchInput,
    currentPage,
    filteredUsers,
    paginatedUsers,
    totalPages,
    facets,
    activeFilterCount,
    setSearchInput,
    handleFilterChange,
    resetFilters,
    setCurrentPage
  } = useUserFilters(usersWithStatus, UI_CONFIG.ITEMS_PER_PAGE);

  // Подсчёт сотрудников с самооценкой
  const selfReviewCount = useMemo(() => {
    return usersWithStatus.filter(u => 
      selfReviewsStatus[u.id]?.has_self_review || u.self_review_done
    ).length;
  }, [usersWithStatus, selfReviewsStatus]);
  
  // Подсчёт оценённых руководителем сотрудников
  const managerEvaluatedCount = useMemo(() => {
    return usersWithStatus.filter(u => u.manager_review_status === 'completed').length;
  }, [usersWithStatus]);

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка данных..." />;
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-indigo-600" />
            Моя команда
          </h1>
          <p className="text-gray-500">
            Подчинённых: {usersWithStatus.length} | Найдено:{' '}
            <span className="text-indigo-600 font-bold">{filteredUsers.length}</span>
            {selfReviewCount > 0 && (
              <span className="ml-2">
                | <Star className="w-4 h-4 inline-block text-blue-500" /> Самооценок:{' '}
                <span className="text-blue-600 font-bold">{selfReviewCount}</span>
              </span>
            )}
            {managerEvaluatedCount > 0 && (
              <span className="ml-2">
                | Оценено:{' '}
                <span className="text-green-600 font-bold">{managerEvaluatedCount}</span>
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Информационное сообщение */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-blue-800 text-sm">
          {usersWithStatus.length === 0 ? (
            <p>У вас нет подчинённых в системе.</p>
          ) : (
            <>
              <p>Здесь отображаются ваши прямые подчинённые и их подчинённые.</p>
              <p className="mt-1 text-blue-600">
                💡 <strong>Self</strong> — самооценка сотрудника
              </p>
              <p className="mt-1 text-purple-600">
                💡 <strong>Сотр.</strong> — оценки от подчинённых (для руководителей)
              </p>
              <p className="mt-1 text-green-600">
                💡 <strong>Рук.</strong> — оценка от руководителя
              </p>
            </>
          )}
        </div>
      </div>

      {usersWithStatus.length > 0 && (
        <>
          {/* Панель фильтров */}
          <UserFilters
            searchInput={searchInput}
            filters={filters}
            facets={facets}
            activeFilterCount={activeFilterCount}
            onSearchChange={setSearchInput}
            onFilterChange={handleFilterChange}
            onReset={resetFilters}
          />

          {/* Таблица пользователей (режим только просмотр) */}
          <UserTable
            users={paginatedUsers}
            canEdit={false}
            onEdit={() => {}}
            selfReviewsStatus={selfReviewsStatus}
            onRowClick={handleRowClick}
            onManagerEvaluationClick={undefined}
            onSubordinateEvaluationClick={undefined}
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
        </>
      )}

      {/* Модальное окно деталей самооценки */}
      <SelfReviewDetailsModal
        isOpen={isModalOpen}
        employee={selectedEmployee}
        onClose={handleCloseModal}
      />

      {/* Модальное окно оценок от руководителя */}
      <ManagerEvaluationDetailsModal
        isOpen={isManagerModalOpen}
        employee={selectedEmployeeForManager}
        onClose={handleCloseManagerModal}
      />

      {/* Модальное окно оценок от подчинённых */}
      <SubordinateEvaluationsModal
        isOpen={isSubordinatesModalOpen}
        employee={selectedEmployeeForSubordinates}
        currentUser={user}
        onClose={handleCloseSubordinatesModal}
      />
    </div>
  );
};

export default TeamView;

