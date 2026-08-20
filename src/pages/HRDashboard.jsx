/**
 * HRDashboard - Страница HR дашборда
 * 
 * Назначение: Отображение статусов оценок всех сотрудников
 * Доступ: hr
 * 
 * Функционал:
 * - Таблица со статусами самооценок и оценок
 * - Фильтрация по статусам
 * - Статистика прогресса
 */

import React, { useState, useMemo } from 'react';
import { 
  Users, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  RefreshCw,
  Search,
  Filter,
  UserCheck,
  Star,
  UsersRound,
  TrendingUp
} from 'lucide-react';
import { LoadingSpinner, Pagination } from '../components/common';
import { useHRDashboard } from '../hooks/useHRDashboard';
import { UI_CONFIG } from '../config/constants';

// Компонент статус-бейджа
const StatusBadge = ({ status, text }) => {
  const styles = {
    success: 'bg-green-100 text-green-700 border-green-200',
    warning: 'bg-amber-100 text-amber-700 border-amber-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    neutral: 'bg-gray-100 text-gray-500 border-gray-200'
  };

  const icons = {
    success: <CheckCircle2 className="w-3.5 h-3.5" />,
    warning: <AlertCircle className="w-3.5 h-3.5" />,
    error: <XCircle className="w-3.5 h-3.5" />,
    neutral: <AlertCircle className="w-3.5 h-3.5" />
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
      {icons[status]}
      {text}
    </span>
  );
};

// Компонент карточки статистики
const StatCard = ({ icon: Icon, title, value, total, percent, color }) => {
  const colors = {
    green: 'from-green-500 to-emerald-600',
    blue: 'from-blue-500 to-indigo-600',
    purple: 'from-purple-500 to-violet-600',
    amber: 'from-amber-500 to-orange-600'
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${colors[color]} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <span className="text-2xl font-bold text-gray-900">{percent}%</span>
      </div>
      <h3 className="text-sm font-medium text-gray-600 mb-1">{title}</h3>
      <p className="text-xs text-gray-400">{value} из {total}</p>
      <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full bg-gradient-to-r ${colors[color]} rounded-full transition-all duration-500`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

const HRDashboard = () => {
  const { employees, loading, error, stats, refetch } = useHRDashboard();
  
  // Состояние фильтров
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // all, complete, incomplete
  const [currentPage, setCurrentPage] = useState(1);

  // Фильтрация сотрудников
  const filteredEmployees = useMemo(() => {
    let result = [...employees];

    // Поиск по имени или email
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(e => 
        e.full_name?.toLowerCase().includes(query) ||
        e.email?.toLowerCase().includes(query) ||
        e.job_title?.toLowerCase().includes(query)
      );
    }

    // Фильтр по статусу
    if (statusFilter === 'complete') {
      result = result.filter(e => {
        // C-level не делают самооценку
        const needsSelfReview = e.role !== 'c_level';
        if (needsSelfReview && !e.has_self_review) return false;
        if (e.manager_id && e.role !== 'c_level' && !e.evaluated_manager) return false;
        if ((e.has_subordinates || e.total_subordinates > 0) && !e.all_subordinates_evaluated) return false;
        return true;
      });
    } else if (statusFilter === 'incomplete') {
      result = result.filter(e => {
        // C-level не делают самооценку
        const needsSelfReview = e.role !== 'c_level';
        if (needsSelfReview && !e.has_self_review) return true;
        if (e.manager_id && e.role !== 'c_level' && !e.evaluated_manager) return true;
        if ((e.has_subordinates || e.total_subordinates > 0) && !e.all_subordinates_evaluated) return true;
        return false;
      });
    }

    return result;
  }, [employees, searchQuery, statusFilter]);

  // Пагинация
  const itemsPerPage = UI_CONFIG.ITEMS_PER_PAGE || 10;
  const totalPages = Math.ceil(filteredEmployees.length / itemsPerPage);
  const paginatedEmployees = filteredEmployees.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Сброс страницы при изменении фильтров
  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, statusFilter]);

  // Определение статуса сотрудника
  const getEmployeeStatus = (employee) => {
    const issues = [];
    
    // C-level не делают самооценку
    const needsSelfReview = employee.role !== 'c_level';
    
    if (needsSelfReview && !employee.has_self_review) {
      issues.push('Нет самооценки');
    }
    
    if (employee.manager_id && employee.role !== 'c_level' && !employee.evaluated_manager) {
      issues.push('Не оценил руководителя');
    }
    
    if ((employee.has_subordinates || employee.total_subordinates > 0) && !employee.all_subordinates_evaluated) {
      const remaining = employee.total_subordinates - employee.evaluated_subordinates;
      issues.push(`Не оценил ${remaining} подчин.`);
    }

    if (issues.length === 0) {
      return { status: 'success', text: 'Завершено' };
    } else if (issues.length === 1) {
      return { status: 'warning', text: issues[0] };
    } else {
      return { status: 'error', text: `${issues.length} задачи` };
    }
  };

  if (loading) {
    return <LoadingSpinner text="Загрузка статусов оценок..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8 flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Ошибка загрузки</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={refetch}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <RefreshCw className="w-4 h-4" />
            Повторить
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Заголовок */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-teal-600" />
              Статусы оценок
            </h1>
            <p className="text-gray-500 mt-1">
              Мониторинг прогресса оценок сотрудников
            </p>
          </div>
          <button
            onClick={refetch}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Обновить
          </button>
        </div>

        {/* Статистика */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard
              icon={Star}
              title="Самооценки"
              value={stats.withSelfReview}
              total={stats.shouldDoSelfReview}
              percent={stats.selfReviewPercent}
              color="green"
            />
            <StatCard
              icon={UserCheck}
              title="Оценили руководителя"
              value={stats.evaluatedManager}
              total={stats.shouldEvaluateManager}
              percent={stats.managerEvaluationPercent}
              color="blue"
            />
            <StatCard
              icon={UsersRound}
              title="Оценили подчинённых"
              value={stats.allSubordinatesEvaluated}
              total={stats.withSubordinates}
              percent={stats.subordinatesPercent}
              color="purple"
            />
            <StatCard
              icon={CheckCircle2}
              title="Полностью завершили"
              value={stats.fullyCompleted}
              total={stats.total}
              percent={stats.completionPercent}
              color="amber"
            />
          </div>
        )}

        {/* Фильтры */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Поиск */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Поиск по имени, email или должности..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            
            {/* Фильтр статуса */}
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
              >
                <option value="all">Все сотрудники</option>
                <option value="complete">Завершили оценки</option>
                <option value="incomplete">Не завершили</option>
              </select>
            </div>
          </div>
        </div>

        {/* Таблица */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Сотрудник
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Самооценка
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Оценка руководителя
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Оценка подчинённых
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Общий статус
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {paginatedEmployees.map((employee) => {
                  const overallStatus = getEmployeeStatus(employee);
                  const hasManager = employee.manager_id && employee.role !== 'c_level';
                  const hasSubordinates = employee.has_subordinates || employee.total_subordinates > 0;
                  const isCLevel = employee.role === 'c_level';
                  const needsSelfReview = !isCLevel;

                  return (
                    <tr key={employee.id} className="hover:bg-gray-50 transition-colors">
                      {/* Сотрудник */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-medium ${
                            isCLevel 
                              ? 'bg-gradient-to-br from-purple-500 to-violet-600' 
                              : 'bg-gradient-to-br from-indigo-500 to-purple-600'
                          }`}>
                            {employee.full_name?.charAt(0) || '?'}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-gray-900">{employee.full_name}</p>
                              {isCLevel && (
                                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                                  C-level
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-500">{employee.job_title || employee.email}</p>
                          </div>
                        </div>
                      </td>

                      {/* Самооценка */}
                      <td className="px-6 py-4 text-center">
                        {needsSelfReview ? (
                          employee.has_self_review ? (
                            <CheckCircle2 className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-400 mx-auto" />
                          )
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      {/* Оценка руководителя */}
                      <td className="px-6 py-4 text-center">
                        {hasManager ? (
                          employee.evaluated_manager ? (
                            <CheckCircle2 className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-400 mx-auto" />
                          )
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      {/* Оценка подчинённых */}
                      <td className="px-6 py-4 text-center">
                        {hasSubordinates ? (
                          employee.all_subordinates_evaluated ? (
                            <CheckCircle2 className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <div className="flex flex-col items-center gap-1">
                              <AlertCircle className="w-5 h-5 text-amber-500" />
                              <span className="text-xs text-gray-500">
                                {employee.evaluated_subordinates}/{employee.total_subordinates}
                              </span>
                            </div>
                          )
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      {/* Общий статус */}
                      <td className="px-6 py-4 text-center">
                        <StatusBadge status={overallStatus.status} text={overallStatus.text} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Пустое состояние */}
          {paginatedEmployees.length === 0 && (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-1">Нет результатов</h3>
              <p className="text-gray-500">Попробуйте изменить параметры поиска</p>
            </div>
          )}
        </div>

        {/* Пагинация */}
        {totalPages > 1 && (
          <div className="mt-6">
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={filteredEmployees.length}
              itemsPerPage={itemsPerPage}
              onPageChange={setCurrentPage}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default HRDashboard;

