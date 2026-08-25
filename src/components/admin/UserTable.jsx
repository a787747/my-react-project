/**
 * UserTable - Таблица со списком пользователей
 * 
 * Назначение: Отображение списка пользователей в табличном виде
 * Используется в: AdminUsers, TeamView
 * 
 * Props:
 * - users: array - список пользователей для отображения
 * - canEdit: boolean - может ли пользователь редактировать
 * - onEdit: function(user) - колбэк при клике на редактирование
 * - selfReviewsStatus: object - статусы самооценок (опционально)
 * - onRowClick: function(user) - колбэк при клике на строку (опционально)
 * - onManagerEvaluationClick: function(user) - колбэк при клике на оценку от руководителя (опционально)
 * - onSubordinateEvaluationClick: function(user) - колбэк при клике на оценки от сотрудников (опционально)
 * - showSelfReviewScore: boolean - показывать ли балл самооценки (опционально)
 * - showThreeColumns: boolean - показывать ли 3 колонки статусов (Self, Сотрудники, Manager)
 * - showEvaluationStatus: boolean - колонка кружков; AdminUsers hides it (BUG-034)
 * - sortField / sortDirection / onSort: клиентская сортировка (опционально; без onSort заголовки статичны)
 * - onEmploymentChange: function(user, 'terminate'|'reinstate') - увольнение/восстановление (D-0825-7).
 *   Без него кнопка не рендерится: страницы, кроме AdminUsers, это не показывают.
 */

import React from 'react';
import { Pencil, Mail, Users, CheckCircle, Circle, Clock, Crown, Star, Eye, UserCheck, UserMinus, ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react';

const SortIcon = ({ field, sortField, sortDirection }) => {
  if (sortField !== field) {
    return <ArrowUpDown className="w-3 h-3 text-gray-300" />;
  }
  return sortDirection === 'asc'
    ? <ChevronUp className="w-3 h-3 text-indigo-600" />
    : <ChevronDown className="w-3 h-3 text-indigo-600" />;
};

const SortButton = ({ field, label, sortField, sortDirection, onSort, title }) => {
  const active = sortField === field;
  const next = active && sortDirection === 'asc' ? 'по убыванию' : 'по возрастанию';
  return (
    <button
      type="button"
      title={title}
      aria-label={`Сортировать: ${label}, ${next}`}
      onClick={() => onSort(field)}
      className={`inline-flex items-center gap-1 uppercase hover:text-indigo-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 rounded ${
        active ? 'text-indigo-600' : 'text-gray-500'
      }`}
    >
      {label}
      <SortIcon field={field} sortField={sortField} sortDirection={sortDirection} />
    </button>
  );
};

const UserTable = ({ 
  users, 
  canEdit, 
  onEdit, 
  selfReviewsStatus = {}, 
  onRowClick, 
  onManagerEvaluationClick, 
  onSubordinateEvaluationClick,
  showSelfReviewScore = false,
  showThreeColumns = false,
  showEvaluationStatus = true,
  sortField = null,
  sortDirection = 'asc',
  onSort,
  onEmploymentChange
}) => {
  const sortable = typeof onSort === 'function';
  const canChangeEmployment = typeof onEmploymentChange === 'function';
  
  // Получение данных самооценки для пользователя
  const getSelfReviewData = (userId) => {
    return selfReviewsStatus[userId] || null;
  };

  // Рендер иконки статуса оценки
  const renderStatusIcon = (status, isManager = false) => {
    if (isManager) {
      // Для оценки менеджера: 'completed', 'draft', null
      if (status === 'completed') {
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      }
      if (status === 'draft') {
        return <Clock className="w-4 h-4 text-orange-400" />;
      }
      return <Circle className="w-4 h-4 text-gray-200" />;
    } else {
      // Для самооценки (boolean)
      if (status) {
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      }
      return <Circle className="w-4 h-4 text-gray-200" />;
    }
  };

  // Рендер статуса самооценки с баллом
  const renderSelfReviewStatus = (user) => {
    const selfReviewData = getSelfReviewData(user.id);
    const hasSelfReview = selfReviewData?.has_self_review || user.self_review_done;
    const score = selfReviewData?.score;

    return (
      <div title="Самооценка" className="flex flex-col items-center min-h-[52px] justify-start pt-1">
        {hasSelfReview ? (
          <>
            <div className="flex items-center gap-0.5">
              <CheckCircle className="w-4 h-4 text-green-500" />
              {showSelfReviewScore && score != null && (
                <span className="text-xs font-bold text-blue-600">{parseFloat(score).toFixed(1)}</span>
              )}
            </div>
            <span className="text-[9px] text-gray-400 mt-0.5">Self</span>
            {showSelfReviewScore && onRowClick ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRowClick(user);
                }}
                className="text-[9px] text-blue-600 hover:text-blue-800 flex items-center gap-0.5 transition-colors"
                title="Посмотреть детали самооценки"
              >
                <Eye className="w-3 h-3" />
                <span>Детали</span>
              </button>
            ) : (
              <div className="h-4"></div>
            )}
          </>
        ) : (
          <>
            <Circle className="w-4 h-4 text-gray-200" />
            <span className="text-[9px] text-gray-400 mt-0.5">Self</span>
            <div className="h-4"></div>
          </>
        )}
      </div>
    );
  };

  // Получение класса бейджа роли
  const getRoleBadgeClass = (role) => {
    switch (role) {
      case 'admin':
        return 'bg-red-50 text-red-700 border-red-100';
      case 'c_level':
        return 'bg-purple-50 text-purple-700 border-purple-100';
      case 'manager':
        return 'bg-blue-50 text-blue-700 border-blue-100';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-100';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                {sortable ? (
                  <div className="flex flex-col items-start gap-0.5">
                    <SortButton field="name" label="Сотрудник" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                    <SortButton field="registered" label="Рег." title="Статус регистрации" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                  </div>
                ) : (
                  'Сотрудник'
                )}
              </th>
              <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                {sortable ? (
                  <div className="flex flex-col items-start gap-0.5">
                    <SortButton field="role" label="Роль" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                    <SortButton field="category" label="Категория" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                  </div>
                ) : (
                  'Роль / Категория'
                )}
              </th>
              <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                {sortable ? (
                  <div className="flex flex-col items-start gap-0.5">
                    <SortButton field="department" label="Отдел" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                    <SortButton field="grade" label="Грейд" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                  </div>
                ) : (
                  'Отдел / Грейд'
                )}
              </th>
              <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                {sortable ? (
                  <SortButton field="manager" label="Менеджер" sortField={sortField} sortDirection={sortDirection} onSort={onSort} />
                ) : (
                  'Менеджер'
                )}
              </th>
              {showEvaluationStatus && (
                <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase text-center">
                  {showThreeColumns ? 'Статусы оценок' : 'Статус (Само. / Рук.)'}
                </th>
              )}
              {canEdit && <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase text-right">Действия</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users.length > 0 ? (
              users.map((user) => (
                <tr
                  key={user.id}
                  className={`hover:bg-gray-50 transition-colors ${onRowClick ? 'cursor-pointer' : ''} ${
                    user.terminated_at ? 'bg-gray-50/70 text-gray-500' : ''
                  }`}
                  onClick={onRowClick ? () => onRowClick(user) : undefined}
                >
                  {/* Сотрудник */}
                  <td className="px-4 py-2">
                    <div className="flex items-center">
                      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 text-sm font-bold mr-2.5 flex-shrink-0">
                        {user.full_name?.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-sm text-gray-900 truncate">{user.full_name}</div>
                        <div className="text-xs text-gray-500 flex items-center gap-1.5 min-w-0">
                          <Mail className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{user.email}</span>
                          {user.is_registered != null && (
                            <span className={`inline-flex shrink-0 items-center px-1.5 py-0 rounded text-[10px] font-medium border ${
                              user.is_registered
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-gray-50 text-gray-500 border-gray-200'
                            }`}>
                              {user.is_registered ? 'Зарегистрирован' : 'Не зарегистрирован'}
                            </span>
                          )}
                          {user.terminated_at && (
                            <span
                              title="Уволен: вне списков, задач и расчёта премии. Оценки в базе сохранены."
                              className="inline-flex shrink-0 items-center gap-1 px-1.5 py-0 rounded text-[10px] font-semibold border bg-red-50 text-red-700 border-red-200"
                            >
                              <UserMinus className="w-3 h-3" />
                              Уволен{user.termination_date ? ` ${user.termination_date}` : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                  
                  {/* Роль / Категория */}
                  <td className="px-4 py-2">
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-1.5">
                        {/* Роль есть не во всех источниках: /api/employees её не
                            отдаёт, потому что для чтения собственной команды она
                            не нужна. Пустой бейдж рисовать нечего. */}
                        {user.role && (
                          <span className={`inline-flex w-fit items-center px-2 py-0 rounded text-xs font-medium capitalize border ${getRoleBadgeClass(user.role)}`}>
                            {user.role === 'c_level' ? 'C-Level' : user.role}
                          </span>
                        )}
                        {user.has_subordinates && (
                          <span 
                            title="Руководитель (есть подчиненные)"
                            className="inline-flex items-center px-1.5 py-0 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200"
                          >
                            <Crown className="w-3 h-3" />
                          </span>
                        )}
                      </div>
                      <span className="text-sm text-gray-600 capitalize">{user.work_category}</span>
                    </div>
                  </td>
                  
                  {/* Отдел / Грейд */}
                  <td className="px-4 py-2">
                    <div className="text-sm text-gray-900 font-medium">{user.department_name || '-'}</div>
                    <div className="text-xs text-gray-500">
                      Grade: <span className="font-medium text-gray-700">{user.grade_name || 'N/A'}</span>
                    </div>
                  </td>
                  
                  {/* Менеджер */}
                  <td className="px-4 py-2 text-sm text-gray-600">
                    {user.manager_name ? (
                      <div className="flex items-center gap-1.5">
                        <Users className="w-4 h-4 text-gray-400 flex-shrink-0" /> 
                        <span className="truncate">{user.manager_name}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 italic text-xs">Не назначен</span>
                    )}
                  </td>
                  
                  {/* Статусы — omitted on AdminUsers: no admin-allowed route returns these metrics */}
                  {showEvaluationStatus && (
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-center gap-2">
                      {/* Колонка 1: Самооценка - фиксированная ширина */}
                      <div className="w-14 flex flex-col items-center">
                        {renderSelfReviewStatus(user)}
                      </div>
                      
                      {/* Колонка 2: Оценки от сотрудников (только если showThreeColumns) */}
                      {showThreeColumns && (
                        <>
                          <div className="h-10 w-px bg-gray-200 flex-shrink-0"></div>
                          <div 
                            title={user.has_subordinates 
                              ? `Оценки от сотрудников: ${user.subordinate_evaluations_count || 0}` 
                              : 'Нет подчинённых'}
                            className={`w-14 flex flex-col items-center min-h-[52px] justify-start pt-1 ${
                              onSubordinateEvaluationClick && user.subordinate_evaluations_count > 0
                                ? 'cursor-pointer hover:bg-purple-50 rounded-lg transition-colors' 
                                : ''
                            }`}
                            onClick={(e) => {
                              if (onSubordinateEvaluationClick && user.subordinate_evaluations_count > 0) {
                                e.stopPropagation();
                                onSubordinateEvaluationClick(user);
                              }
                            }}
                          >
                            {user.has_subordinates ? (
                              user.subordinate_evaluations_count > 0 ? (
                                <div className="flex items-center gap-0.5">
                                  <CheckCircle className="w-4 h-4 text-purple-500" />
                                  <span className="text-xs font-bold text-purple-600">
                                    {user.subordinate_evaluations_count}
                                  </span>
                                </div>
                              ) : (
                                <Circle className="w-4 h-4 text-gray-200" />
                              )
                            ) : (
                              <span className="text-gray-300 text-sm">—</span>
                            )}
                            <span className="text-[9px] text-gray-400 mt-0.5">Сотр.</span>
                            {user.subordinate_evaluations_count > 0 && onSubordinateEvaluationClick ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSubordinateEvaluationClick(user);
                                }}
                                className="text-[9px] text-purple-600 hover:text-purple-800 flex items-center gap-0.5 transition-colors"
                                title="Посмотреть оценки от сотрудников"
                              >
                                <Eye className="w-3 h-3" />
                                <span>Детали</span>
                              </button>
                            ) : (
                              <div className="h-4"></div>
                            )}
                          </div>
                        </>
                      )}
                      
                      {/* Колонка 3: Оценка от руководителя - фиксированная ширина */}
                      <div className="h-10 w-px bg-gray-200 flex-shrink-0"></div>
                      <div 
                        title={`Оценка руководителя: ${user.manager_review_status === 'completed' ? 'Есть' : 'Нет'}`} 
                        className={`w-14 flex flex-col items-center min-h-[52px] justify-start pt-1 ${
                          onManagerEvaluationClick && user.manager_review_status === 'completed' 
                            ? 'cursor-pointer hover:bg-green-50 rounded-lg transition-colors' 
                            : ''
                        }`}
                        onClick={(e) => {
                          if (onManagerEvaluationClick && user.manager_review_status === 'completed') {
                            e.stopPropagation();
                            onManagerEvaluationClick(user);
                          }
                        }}
                      >
                        {renderStatusIcon(user.manager_review_status, true)}
                        <span className="text-[9px] text-gray-400 mt-0.5">Рук.</span>
                        {user.manager_review_status === 'completed' && onManagerEvaluationClick ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onManagerEvaluationClick(user);
                            }}
                            className="text-[9px] text-green-600 hover:text-green-800 flex items-center gap-0.5 transition-colors"
                            title="Посмотреть оценку от руководителя"
                          >
                            <Eye className="w-3 h-3" />
                            <span>Детали</span>
                          </button>
                        ) : (
                          <div className="h-4"></div>
                        )}
                      </div>
                    </div>
                  </td>
                  )}
                  
                  {/* Действия */}
                  {canEdit && (
                    <td className="px-4 py-2 text-right">
                      <div className="flex items-center justify-end gap-0.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onEdit(user);
                          }}
                          className="text-gray-400 hover:text-indigo-600 p-1.5 rounded-lg hover:bg-indigo-50 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-200"
                          aria-label={`Редактировать ${user.full_name}`}
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        {canChangeEmployment && (
                          user.terminated_at ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onEmploymentChange(user, 'reinstate');
                              }}
                              className="text-gray-400 hover:text-emerald-600 p-1.5 rounded-lg hover:bg-emerald-50 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-200"
                              aria-label={`Восстановить ${user.full_name}`}
                              title="Восстановить сотрудника"
                            >
                              <UserCheck className="w-4 h-4" />
                            </button>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onEmploymentChange(user, 'terminate');
                              }}
                              className="text-gray-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-200"
                              aria-label={`Отметить увольнение: ${user.full_name}`}
                              title="Отметить увольнение"
                            >
                              <UserMinus className="w-4 h-4" />
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={(canEdit ? 5 : 4) + (showEvaluationStatus ? 1 : 0)} className="text-center py-10 text-gray-500">
                  Сотрудники не найдены.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UserTable;

