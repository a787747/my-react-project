/**
 * AllEvaluationsTable - Таблица всех оценок сотрудников
 * 
 * Назначение: Сводная таблица с самооценками, оценками менеджеров и данными оценщиков
 * Используется в: AdminAllEvaluations
 * 
 * Props:
 * - employees: array - список сотрудников
 * - formatDate: function - функция форматирования даты
 * - onViewDetails: function(employee, type) - открыть детали по типу
 */

import React, { useState, useMemo } from 'react';
import { Eye, Star, UserCheck, Users, ChevronDown, ChevronUp, ArrowUpDown, Search, UserMinus } from 'lucide-react';

// Иконка сортировки - вынесена за пределы компонента
const SortIcon = ({ field, sortField, sortDirection }) => {
  if (sortField !== field) {
    return <ArrowUpDown className="w-3 h-3 text-gray-300" />;
  }
  return sortDirection === 'asc' 
    ? <ChevronUp className="w-3 h-3 text-indigo-600" />
    : <ChevronDown className="w-3 h-3 text-indigo-600" />;
};

const AllEvaluationsTable = ({ employees, formatDate, onViewDetails }) => {
  const [sortField, setSortField] = useState('full_name');
  const [sortDirection, setSortDirection] = useState('asc');
  const [searchQuery, setSearchQuery] = useState('');

  // Сортировка
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Фильтрация и сортировка
  const filteredAndSortedEmployees = useMemo(() => {
    let result = [...employees];
    
    // Фильтр по поиску
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(emp => 
        emp.full_name?.toLowerCase().includes(query) ||
        emp.department_name?.toLowerCase().includes(query) ||
        emp.job_title?.toLowerCase().includes(query)
      );
    }
    
    // Сортировка
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      // Числовые поля
      if (['self_score', 'manager_score', 'gave_to_manager_score', 'from_subordinates_score', 'subordinates_evaluated'].includes(sortField)) {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      } else {
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
      }
      
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return result;
  }, [employees, searchQuery, sortField, sortDirection]);

  // Рендер кликабельной ячейки с оценкой
  const renderScoreCell = (employee, score, date, type, colorClass, evalId) => {
    if (!score) {
      return <div className="text-center text-gray-300 text-sm">—</div>;
    }

    return (
      <button
        onClick={() => onViewDetails(employee, type, evalId)}
        className={`flex flex-col items-center p-2 rounded-lg hover:ring-2 hover:ring-offset-1 hover:ring-indigo-400 transition-all cursor-pointer group w-full`}
        title="Нажмите для просмотра деталей"
      >
        <div className={`text-2xl font-bold ${colorClass}`}>{score}</div>
        <div className="text-[10px] text-gray-400 group-hover:text-indigo-600">
          {formatDate(date)}
        </div>
        <Eye className="w-3 h-3 text-gray-300 group-hover:text-indigo-500 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
      </button>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Поиск */}
      <div className="p-4 border-b border-gray-100">
        <div className="relative max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Поиск по имени, отделу, должности..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
          />
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Найдено: {filteredAndSortedEmployees.length} из {employees.length} сотрудников
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('full_name')}
              >
                <div className="flex items-center gap-1">
                  Сотрудник
                  <SortIcon field="full_name" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('department_name')}
              >
                <div className="flex items-center gap-1">
                  Отдел
                  <SortIcon field="department_name" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('self_score')}
              >
                <div className="flex items-center justify-center gap-1">
                  <Star className="w-3 h-3 text-blue-500" />
                  Самооценка
                  <SortIcon field="self_score" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('manager_score')}
              >
                <div className="flex items-center justify-center gap-1">
                  <UserCheck className="w-3 h-3 text-green-500" />
                  От руководителя
                  <SortIcon field="manager_score" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('gave_to_manager_score')}
              >
                <div className="flex items-center justify-center gap-1">
                  <UserCheck className="w-3 h-3 text-teal-500" />
                  Оценил рук-ля
                  <SortIcon field="gave_to_manager_score" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('from_subordinates_score')}
              >
                <div className="flex items-center justify-center gap-1">
                  <UserMinus className="w-3 h-3 text-orange-500" />
                  От подчинённых
                  <SortIcon field="from_subordinates_score" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('subordinates_evaluated')}
              >
                <div className="flex items-center justify-center gap-1">
                  <Users className="w-3 h-3 text-purple-500" />
                  Оценил подч.
                  <SortIcon field="subordinates_evaluated" sortField={sortField} sortDirection={sortDirection} />
                </div>
              </th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center">
                Все
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filteredAndSortedEmployees.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                  Сотрудники не найдены
                </td>
              </tr>
            ) : (
              filteredAndSortedEmployees.map((emp) => (
                <tr key={emp.id} className="hover:bg-gray-50 transition-colors">
                  {/* Сотрудник */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                        {emp.full_name?.charAt(0)}
                      </div>
                      <div>
                        <div className="font-semibold text-gray-900 text-sm">{emp.full_name}</div>
                        <div className="text-xs text-gray-500">{emp.job_title}</div>
                        {emp.has_subordinates && (
                          <span className="inline-flex items-center gap-1 text-[10px] text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded-full mt-0.5">
                            <Users className="w-2.5 h-2.5" />
                            Руководитель
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Отдел */}
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600">{emp.department_name || '—'}</span>
                  </td>

                  {/* Самооценка */}
                  <td className="px-2 py-2">
                    {renderScoreCell(
                      emp, 
                      emp.self_score, 
                      emp.self_date, 
                      'self', 
                      'text-blue-600',
                      emp.self_eval_id
                    )}
                  </td>

                  {/* Оценка от руководителя */}
                  <td className="px-2 py-2">
                    {renderScoreCell(
                      emp, 
                      emp.manager_score, 
                      emp.manager_date, 
                      'received_from_manager', 
                      'text-green-600',
                      emp.manager_eval_id
                    )}
                  </td>

                  {/* Оценка, данная руководителю */}
                  <td className="px-2 py-2">
                    {emp.manager_id ? (
                      emp.gave_to_manager_score ? (
                        <button
                          onClick={() => onViewDetails(emp, 'gave_to_manager', emp.gave_to_manager_eval_id)}
                          className="flex flex-col items-center p-2 rounded-lg hover:ring-2 hover:ring-offset-1 hover:ring-teal-400 transition-all cursor-pointer group w-full"
                          title={`Оценка для ${emp.evaluated_manager_name || emp.manager_name}`}
                        >
                          <div className="text-2xl font-bold text-teal-600">{emp.gave_to_manager_score}</div>
                          <div className="text-[10px] text-gray-400 group-hover:text-teal-600 truncate max-w-[80px]">
                            → {emp.evaluated_manager_name || emp.manager_name}
                          </div>
                          <Eye className="w-3 h-3 text-gray-300 group-hover:text-teal-500 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                      ) : (
                        <div className="text-center">
                          <div className="text-gray-300 text-sm">—</div>
                          <div className="text-[10px] text-gray-400 truncate max-w-[80px]">
                            → {emp.manager_name}
                          </div>
                        </div>
                      )
                    ) : (
                      <div className="text-center text-gray-200 text-xs">Нет рук-ля</div>
                    )}
                  </td>

                  {/* Оценка ОТ подчинённых (средняя оценка, которую подчинённые поставили этому руководителю) */}
                  <td className="px-2 py-2">
                    {emp.has_subordinates ? (
                      emp.from_subordinates_score ? (
                        <button
                          onClick={() => onViewDetails(emp, 'from_subordinates')}
                          className="flex flex-col items-center p-2 rounded-lg hover:ring-2 hover:ring-offset-1 hover:ring-orange-400 transition-all cursor-pointer group w-full"
                          title={`Средняя оценка от ${emp.from_subordinates_count} подчинённых`}
                        >
                          <div className="text-2xl font-bold text-orange-600">{emp.from_subordinates_score}</div>
                          <div className="text-[10px] text-gray-400 group-hover:text-orange-600">
                            от {emp.from_subordinates_count} чел.
                          </div>
                          <Eye className="w-3 h-3 text-gray-300 group-hover:text-orange-500 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                      ) : (
                        <div className="text-center">
                          <div className="text-gray-300 text-sm">—</div>
                          <div className="text-[10px] text-gray-400">не оценили</div>
                        </div>
                      )
                    ) : (
                      <div className="text-center text-gray-200 text-xs">—</div>
                    )}
                  </td>

                  {/* Сколько подчинённых оценил этот руководитель */}
                  <td className="px-2 py-2">
                    {emp.has_subordinates ? (
                      <button
                        onClick={() => onViewDetails(emp, 'gave_to_subordinates')}
                        className="flex flex-col items-center p-2 rounded-lg hover:ring-2 hover:ring-offset-1 hover:ring-purple-400 transition-all cursor-pointer group w-full"
                        title="Оценки, данные подчинённым"
                      >
                        <div className="text-lg font-bold text-purple-600">
                          {emp.subordinates_evaluated || 0}/{emp.subordinates_total || 0}
                        </div>
                        <div className="text-[10px] text-gray-400 group-hover:text-purple-600">
                          оценено
                        </div>
                        <Eye className="w-3 h-3 text-gray-300 group-hover:text-purple-500 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                    ) : (
                      <div className="text-center text-gray-200 text-xs">—</div>
                    )}
                  </td>

                  {/* Все детали */}
                  <td className="px-4 py-3 text-center">
                    <button 
                      onClick={() => onViewDetails(emp, 'all')}
                      className="p-2 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-lg transition-colors"
                      title="Посмотреть все оценки"
                    >
                      <Eye className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Легенда */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Star className="w-3 h-3 text-blue-500" />
          <span>Самооценка</span>
        </div>
        <div className="flex items-center gap-1.5">
          <UserCheck className="w-3 h-3 text-green-500" />
          <span>От руководителя</span>
        </div>
        <div className="flex items-center gap-1.5">
          <UserCheck className="w-3 h-3 text-teal-500" />
          <span>Поставил рук-лю</span>
        </div>
        <div className="flex items-center gap-1.5">
          <UserMinus className="w-3 h-3 text-orange-500" />
          <span>Ср. от подчинённых</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="w-3 h-3 text-purple-500" />
          <span>Оценил подчинённых</span>
        </div>
      </div>
    </div>
  );
};

export default AllEvaluationsTable;
