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

import React, { useState, useMemo } from 'react';
import { Users, Plus, Info, Upload, UserMinus, UserCheck, AlertCircle } from 'lucide-react';

// Компоненты
import { Toast, LoadingSpinner, Pagination } from '../components/common';
import { UserTable, UserFilters, UserModal, UserImportModal, EmploymentStatusModal } from '../components/admin';

// Хуки
import { useUsers } from '../hooks/useUsers';
import { useUserFilters } from '../hooks/useUserFilters';

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

const AdminUsers = ({ user }) => {
  // Admin, C-level и HR видят весь список (ROLE_ACCESS_HR_CLEVEL, 2026-08-26).
  // Редактирует только admin: каждый маршрут записи отвечает 403 остальным
  // ролям, поэтому кнопки для них не рисуются вовсе — скрытая кнопка не защита,
  // но видимая кнопка, которую сервер откажет, — ложное обещание.
  const isFullAccess = ['admin', 'c_level', 'hr'].includes(user?.role);
  const isAdminUser = user?.role === 'admin';
  const canEdit = isAdminUser;

  // Хук для работы с пользователями
  const {
    users,
    options,
    loading,
    error,
    saving,
    fetchData,
    saveUser,
    changePeriodScope,
    getEmployeeEvents,
    terminateUser,
    reinstateUser,
    importUsers
  } = useUsers();

  // Evaluation-status circles were removed (BUG-034): no admin-allowed
  // route returns the subject-centric metrics the column claimed to show.
  // GET /api/check-self-review is single-subject; GET /api/hr/evaluation-status
  // is allowed for admin but answers evaluator-task flags, not received scores,
  // and uses different field names than this page mapped.

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

  // Хук для фильтрации
  const {
    filters,
    searchInput,
    currentPage,
    filteredUsers,
    paginatedUsers,
    totalPages,
    facets,
    counts,
    activeFilterCount,
    setSearchInput,
    handleFilterChange,
    resetFilters,
    setCurrentPage,
    sortField,
    sortDirection,
    handleSort
  } = useUserFilters(visibleUsers, UI_CONFIG.ITEMS_PER_PAGE);

  // Состояние модального окна
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Состояние модального окна импорта
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Состояние окна увольнения / восстановления (D-0825-7)
  const [employmentTarget, setEmploymentTarget] = useState(null);
  const [employmentMode, setEmploymentMode] = useState('terminate');
  const [employmentError, setEmploymentError] = useState(null);

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
    const scrollY = window.scrollY;
    const result = await saveUser(formData, existingUserId);
    
    if (result.success) {
      if (!existingUserId) {
        showToast('Сотрудник успешно добавлен', 'success');
      }
      // Keep an edited card open: the per-period recompute result and the
      // append-only event must be visible instead of disappearing into a toast.
      if (!existingUserId) handleCloseModal();
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo(0, scrollY);
        });
      });
    } else if (!existingUserId) {
      showToast(result.error || 'Ошибка при сохранении', 'error');
    }
    return result;
  };

  const handleScopeChange = async (targetUserId, periodId, participate) => {
    return changePeriodScope(targetUserId, periodId, participate);
  };

  // Увольнение / восстановление (D-0825-7).
  // Ошибка сервера (например «есть прямые подчинённые») остаётся в окне, а не
  // уходит в toast: она объясняет, что именно нужно сделать до повтора.
  const handleOpenEmployment = (targetUser, mode) => {
    if (!canEdit) return;
    setEmploymentTarget(targetUser);
    setEmploymentMode(mode);
    setEmploymentError(null);
  };

  const handleCloseEmployment = () => {
    setEmploymentTarget(null);
    setEmploymentError(null);
  };

  const handleConfirmEmployment = async ({ terminationDate, note }) => {
    if (!employmentTarget) return;
    const scrollY = window.scrollY;
    const result = employmentMode === 'terminate'
      ? await terminateUser(employmentTarget.id, terminationDate, note)
      : await reinstateUser(employmentTarget.id, note);

    if (result.success) {
      showToast(
        employmentMode === 'terminate'
          ? `${employmentTarget.full_name}: увольнение отмечено`
          : `${employmentTarget.full_name}: сотрудник восстановлен`,
        'success'
      );
      handleCloseEmployment();
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo(0, scrollY);
        });
      });
    } else {
      setEmploymentError(result.error || 'Не удалось изменить статус');
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

  // Список не загрузился — говорим почему, а не рисуем пустую таблицу.
  // До 2026-08-26 отказ сервера (403 для hr/c_level) молча превращался в
  // «Найдено: 0» — тот же проглоченный отказ, что был на /team (BUG-012).
  if (error) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <div className="max-w-xl mx-auto mt-16 bg-white border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <p className="text-gray-900 font-semibold mb-1">Список сотрудников не загружен</p>
          <p className="text-red-700 text-sm mb-4">{error}</p>
          <button
            onClick={() => fetchData()}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
          >
            Повторить
          </button>
        </div>
      </div>
    );
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
          {/* Каждое число — над названной популяцией. «Найдено» считается по
              отфильтрованному списку, строка ниже — по всей видимой популяции;
              раньше они стояли рядом без подписи и противоречили друг другу
              (например «Работают: 88 … Найдено: 89» при фильтре «Все»). */}
          <p className="text-gray-500">
            Найдено: <span className="text-indigo-600 font-bold">{counts.found}</span>
            {counts.foundTerminated > 0 && (
              <span className="text-gray-500">
                {' '}— из них уволенных:{' '}
                <span className="text-red-600 font-semibold">{counts.foundTerminated}</span>
              </span>
            )}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {isFullAccess ? 'Всего в базе' : 'Подчинённых'}: {counts.total}
            {' · '}работают {counts.active}
            {' · '}уволены {counts.terminated}
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
        facets={facets}
        activeFilterCount={activeFilterCount}
        onSearchChange={setSearchInput}
        onFilterChange={handleFilterChange}
        onReset={resetFilters}
        showEvaluationState
      />

      {/* Статус занятости убирает людей, которые подходят под все остальные
          фильтры. Без этой строки поиск по уволенному человеку отвечает
          «Сотрудники не найдены» и не говорит, почему. */}
      {counts.hiddenTerminated > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-6 flex flex-wrap items-center gap-2 text-sm text-amber-900">
          <UserMinus className="w-4 h-4 flex-shrink-0" />
          <span>
            Скрыто уволенных: <strong>{counts.hiddenTerminated}</strong> — они подходят под остальные фильтры.
          </span>
          <button
            onClick={() => handleFilterChange('employment', 'all')}
            className="underline underline-offset-2 font-medium hover:text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-300 rounded"
          >
            Показать всех
          </button>
        </div>
      )}
      {counts.hiddenActive > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-6 flex flex-wrap items-center gap-2 text-sm text-amber-900">
          <UserCheck className="w-4 h-4 flex-shrink-0" />
          <span>
            Скрыто работающих: <strong>{counts.hiddenActive}</strong> — они подходят под остальные фильтры.
          </span>
          <button
            onClick={() => handleFilterChange('employment', 'all')}
            className="underline underline-offset-2 font-medium hover:text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-300 rounded"
          >
            Показать всех
          </button>
        </div>
      )}

      {/* Таблица пользователей */}
      <UserTable
        users={paginatedUsers}
        canEdit={canEdit}
        onEdit={handleOpenModal}
        showEvaluationStatus={false}
        showEvaluationState
        sortField={sortField}
        sortDirection={sortDirection}
        onSort={handleSort}
        onEmploymentChange={canEdit ? handleOpenEmployment : undefined}
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
        canManageScope={isAdminUser}
        onClose={handleCloseModal}
        onSave={handleSave}
        onScopeChange={handleScopeChange}
        onLoadEvents={getEmployeeEvents}
      />

      {/* Увольнение / восстановление */}
      <EmploymentStatusModal
        isOpen={Boolean(employmentTarget) && canEdit}
        mode={employmentMode}
        user={employmentTarget}
        saving={saving}
        error={employmentError}
        onClose={handleCloseEmployment}
        onConfirm={handleConfirmEmployment}
      />

      {/* Модальное окно импорта/экспорта */}
      <UserImportModal
        isOpen={isImportModalOpen && canEdit}
        options={options}
        users={users}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImport}
      />
    </div>
  );
};

export default AdminUsers;
