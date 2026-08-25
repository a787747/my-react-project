/**
 * TeamView - Страница «Список команды» для менеджера
 *
 * Назначение: список прямых подчинённых с отметками о том, что уже сделано
 * Доступ: маршрут ManagerRoute (manager и выше); в меню пункт виден только у manager
 *
 * Источник данных — `GET /api/employees` (см. useTeamRoster). Охват считает
 * сервер: прямые подчинённые, только в охвате активного периода и только пока
 * кампания идёт. Уволенный сотрудник в ответе не появляется.
 *
 * Отличие от AdminUsers:
 * - только просмотр, без редактирования и без увольнения
 * - список приходит уже суженным сервером, а не строится обходом дерева
 * - показываются флаги выполнения, а не баллы: балл самооценки подчинённого
 *   менеджеру не принадлежит (D-0824-3), детали открываются по клику и
 *   запрашиваются отдельно, для одного человека
 *
 * Использует компоненты:
 * - UserTable - таблица (режим просмотра)
 * - UserFilters - панель фильтров
 * - LoadingSpinner - индикатор загрузки
 * - Pagination - пагинация
 * - SelfReviewDetailsModal - детали самооценки одного подчинённого
 *
 * Использует хуки:
 * - useTeamRoster - список команды
 * - useUserFilters - логика фильтрации
 */

import React, { useMemo, useState } from 'react';
import { Users, Info, Clock, AlertTriangle } from 'lucide-react';

// Компоненты
import { LoadingSpinner, Pagination } from '../components/common';
import { UserTable, UserFilters } from '../components/admin';
import SelfReviewDetailsModal from '../components/SelfReviewDetailsModal';

// Хуки
import { useTeamRoster } from '../hooks/useTeamRoster';
import { useUserFilters } from '../hooks/useUserFilters';

// Константы
import { UI_CONFIG } from '../config/constants';

const TeamView = ({ user }) => {
  const {
    employees,
    campaignActive,
    periodInPreparation,
    periodName,
    actorIsInScope,
    loading,
    error
  } = useTeamRoster(user);

  // Состояние для модального окна самооценки
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Приводим строки маршрута к форме, которую рисует UserTable.
  // `/api/employees` не отдаёт role, grade_name и manager_name: роль не нужна
  // для чтения собственной команды, грейд приходит как grade_code, а
  // руководитель у всех один и тот же — сам актор, по построению выборки
  // (`WHERE users.manager_id = actorId`).
  const teamRows = useMemo(
    () =>
      employees.map((employee) => ({
        ...employee,
        grade_name: employee.grade_code ?? null,
        manager_name: user?.full_name ?? null,
        self_review_done: employee.has_self_review === true,
        // «Оценка руководителя» на этой странице — это оценка, которую ставит
        // сам актор. Флаг покритериальный (D-0822-3): переклассификация
        // general->project снова открывает задачу и гасит галочку.
        manager_review_status: employee.evaluated_by_actor === true ? 'completed' : null
      })),
    [employees, user?.full_name]
  );

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
  } = useUserFilters(teamRows, UI_CONFIG.ITEMS_PER_PAGE);

  const selfReviewCount = useMemo(
    () => teamRows.filter((row) => row.self_review_done).length,
    [teamRows]
  );

  const evaluatedCount = useMemo(
    () => teamRows.filter((row) => row.manager_review_status === 'completed').length,
    [teamRows]
  );

  // Клик по строке открывает детали самооценки — модалка запрашивает их сама,
  // по одному человеку, маршрутом, который признаёт актора руководителем.
  const handleRowClick = (employee) => {
    if (!employee.self_review_done) return;
    setSelectedEmployee(employee);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
  };

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
            Список команды
          </h1>
          <p className="text-gray-500">
            Найдено: <span className="text-indigo-600 font-bold">{counts.found}</span>
            {teamRows.length > 0 && (
              <>
                <span className="ml-2">
                  | Самооценок: <span className="text-blue-600 font-bold">{selfReviewCount}</span>
                </span>
                <span className="ml-2">
                  | Оценено мной: <span className="text-green-600 font-bold">{evaluatedCount}</span>
                </span>
              </>
            )}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            Прямых подчинённых в охвате: {teamRows.length}
            {periodName ? ` · период: ${periodName}` : ''}
          </p>
        </div>
      </div>

      {/* Почему список пуст — это разные причины, и они требуют разных действий */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {!error && actorIsInScope === false && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <p className="text-amber-900 text-sm">
            Вы вне охвата текущего периода оценки, поэтому задач и списка команды здесь нет.
          </p>
        </div>
      )}

      {!error && actorIsInScope !== false && periodInPreparation && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <p className="text-blue-800 text-sm">
            {periodName ? `Период «${periodName}» открыт, но оценка ещё не запущена.` : 'Оценка ещё не запущена.'}
            {' '}Список команды появится, когда администратор её начнёт.
          </p>
        </div>
      )}

      {!error && actorIsInScope !== false && !periodInPreparation && !campaignActive && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <p className="text-blue-800 text-sm">
            Сейчас нет активного периода оценки, поэтому список команды пуст.
          </p>
        </div>
      )}

      {!error && campaignActive && teamRows.length === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <p className="text-blue-800 text-sm">
            У вас нет прямых подчинённых в охвате этого периода.
          </p>
        </div>
      )}

      {teamRows.length > 0 && (
        <>
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-blue-800 text-sm">
              <p>Здесь ваши прямые подчинённые в охвате текущего периода.</p>
              <p className="mt-1 text-blue-600">
                💡 <strong>Self</strong> — сотрудник сдал самооценку; нажмите на строку, чтобы открыть её.
              </p>
              <p className="mt-1 text-green-600">
                💡 <strong>Рук.</strong> — вы уже оценили этого сотрудника по всем применимым критериям.
              </p>
            </div>
          </div>

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

          {/* Таблица (режим только просмотр) */}
          <UserTable
            users={paginatedUsers}
            canEdit={false}
            onEdit={() => {}}
            onRowClick={handleRowClick}
            showSelfReviewScore={false}
            showThreeColumns={false}
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={handleSort}
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

      {/* Детали самооценки одного подчинённого */}
      <SelfReviewDetailsModal
        isOpen={isModalOpen}
        employee={selectedEmployee}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default TeamView;
