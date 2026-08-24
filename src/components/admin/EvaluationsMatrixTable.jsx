/**
 * EvaluationsMatrixTable - Таблица матрицы оценок
 * 
 * Назначение: Отображение сводной таблицы оценок всех сотрудников по критериям
 * Используется в: AdminEvaluationsMatrix
 * 
 * Props:
 * - employees: array - список сотрудников с оценками
 * - sorting: object { field, direction } - текущая сортировка
 * - onSort: function(field) - изменить сортировку
 * - onEmployeeNameClick: function(employee) - клик по имени сотрудника
 * - onCLevelZoneClick: function(employee) - клик по C-level зоне
 * - onScoreClick: function(employee, criterion, group) - клик по ячейке с оценкой
 */

import React from 'react';
import { Star, Eye, Edit2, AlertTriangle, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import { buildSharedCriteriaGroups, getCriterionFinalScore, getCriterionCorrections, canReceiveCLevel, formatCorrectionTooltip } from '../../utils/matrixUtils';

const EvaluationsMatrixTable = ({ 
  employees, 
  period,
  sorting,
  onSort,
  onEmployeeNameClick, 
  onCLevelZoneClick, 
  onScoreClick 
}) => {
  
  // Заголовок — объединение критериев всех строк: сервер отдаёт каждой строке
  // только применимые ей критерии, одна строка заголовок не определяет (BUG-051)
  const headerGroups = buildSharedCriteriaGroups(employees);

  const getFinalScore = (criterion) => {
    const raw = getCriterionFinalScore(criterion);
    if (raw === null || raw === undefined) return null;
    return Number(raw).toFixed(1);
  };

  const hasCorrection = (criterion) => getCriterionCorrections(criterion).hasAny;

  // Получить иконку сортировки
  const getSortIcon = (field) => {
    if (!sorting || sorting.field !== field) {
      return <ArrowUpDown className="w-3 h-3 text-gray-300" />;
    }
    if (sorting.direction === 'asc') {
      return <ArrowUp className="w-3 h-3 text-indigo-600" />;
    }
    return <ArrowDown className="w-3 h-3 text-indigo-600" />;
  };

  // Обработчик клика по ячейке с оценкой
  const handleScoreClick = (e, employee, criterion, group) => {
    e.stopPropagation();
    if (onScoreClick) {
      onScoreClick(employee, criterion, group);
    }
  };

  // Обработчик клика по C-level зоне
  const handleCLevelClick = (e, employee) => {
    e.stopPropagation();
    if (onCLevelZoneClick) {
      onCLevelZoneClick(employee);
    }
  };

  // Обработчик клика по имени сотрудника
  const handleNameClick = (e, employee) => {
    e.stopPropagation();
    if (onEmployeeNameClick) {
      onEmployeeNameClick(employee);
    }
  };

  // BUG-051: строка выравнивается по колонкам заголовка. Критерий, которого у
  // сотрудника нет (сервер его не отдал — неприменим), занимает свою колонку
  // заглушкой; пропуск <td> сдвигал все последующие ячейки под чужие заголовки.
  const renderMissingCell = (group, employee, criterion, borderClass, label = '—') => (
    <td
      key={`${group}-${employee.id}-${criterion.criteria_id}`}
      className={`px-2 py-3 text-center border-l ${borderClass}`}
    >
      <span className="text-gray-200 text-xs">{label}</span>
    </td>
  );

  // Рендер ячейки с оценкой (с учётом корректировки)
  const renderScoreCell = (employee, criterion, group, borderClass) => {
    const managerScore = criterion.manager_score;
    const hasCorrectionApplied = hasCorrection(criterion);
    const finalScore = getFinalScore(criterion);
    const hasScore = managerScore !== null && managerScore !== undefined;

    let bgClass = 'bg-green-100';
    let textClass = 'text-green-700';
    
    if (hasCorrectionApplied) {
      bgClass = 'bg-amber-100';
      textClass = 'text-amber-700';
    }
    
    return (
      <td 
        key={`${group}-${employee.id}-${criterion.criteria_id}`} 
        className={`px-2 py-3 text-center border-l ${borderClass}`}
      >
        {hasScore ? (
          <button
            onClick={(e) => handleScoreClick(e, employee, criterion, group)}
            className={`inline-flex items-center justify-center w-8 h-8 ${bgClass} ${textClass} rounded-full font-bold text-xs hover:ring-2 hover:ring-offset-1 hover:ring-indigo-400 transition-all cursor-pointer group relative`}
            title={hasCorrectionApplied ? formatCorrectionTooltip(criterion) : 'Нажмите для просмотра'}
          >
            {hasCorrectionApplied ? finalScore : managerScore}
            {hasCorrectionApplied && (
              <AlertTriangle className="w-3 h-3 absolute -top-1 -right-1 text-amber-600 bg-white rounded-full" />
            )}
            <Eye className="w-3 h-3 absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100 text-indigo-600 bg-white rounded-full" />
          </button>
        ) : (
          <span className="text-gray-300 text-xs">-</span>
        )}
      </td>
    );
  };

  // Рендер ячейки self
  const renderSelfCell = (employee, criterion) => {
    const hasCorrectionApplied = hasCorrection(criterion);
    const finalScore = getFinalScore(criterion);

    return (
      <td 
        key={`self-${employee.id}-${criterion.criteria_id}`} 
        className="px-1 py-2 text-center border-l border-blue-50"
      >
        <button
          onClick={(e) => handleScoreClick(e, employee, criterion, 'self')}
          className="flex flex-col items-center justify-center hover:bg-blue-50 rounded-lg p-1 transition-colors group cursor-pointer"
          title={hasCorrectionApplied ? formatCorrectionTooltip(criterion) : 'Нажмите для просмотра'}
        >
          <div className="flex items-center gap-1">
            <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-[10px] ${
              criterion.self_score ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-400'
            }`}>
              {criterion.self_score || '-'}
            </span>
            <span className="text-gray-300 text-[10px]">/</span>
            <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-[10px] relative ${
              hasCorrectionApplied 
                ? 'bg-amber-100 text-amber-700' 
                : criterion.manager_score 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-gray-100 text-gray-400'
            }`}>
              {hasCorrectionApplied ? finalScore : (criterion.manager_score || '-')}
              {hasCorrectionApplied && (
                <AlertTriangle className="w-2.5 h-2.5 absolute -top-0.5 -right-0.5 text-amber-600" />
              )}
            </span>
          </div>
        </button>
      </td>
    );
  };

  // Рендер ячейки проектных критериев
  const renderProjectCell = (employee, criterion) => {
    if (!employee.is_project_participant) {
      return (
        <td key={`proj-${employee.id}-${criterion.criteria_id}`} className="px-2 py-3 text-center border-l border-purple-50">
          <span className="text-gray-200 text-xs">N/A</span>
        </td>
      );
    }

    const hasCorrectionApplied = hasCorrection(criterion);
    const finalScore = getFinalScore(criterion);
    const hasScore = !!criterion.manager_score;

    return (
      <td key={`proj-${employee.id}-${criterion.criteria_id}`} className="px-2 py-3 text-center border-l border-purple-50">
        {hasScore ? (
          <button
            onClick={(e) => handleScoreClick(e, employee, criterion, 'project')}
            className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-xs hover:ring-2 hover:ring-offset-1 hover:ring-indigo-400 transition-all cursor-pointer group relative ${
              hasCorrectionApplied 
                ? 'bg-amber-100 text-amber-700' 
                : 'bg-purple-100 text-purple-700'
            }`}
            title={hasCorrectionApplied ? formatCorrectionTooltip(criterion) : 'Нажмите для просмотра'}
          >
            {hasCorrectionApplied ? finalScore : criterion.manager_score}
            {hasCorrectionApplied && (
              <AlertTriangle className="w-3 h-3 absolute -top-1 -right-1 text-amber-600 bg-white rounded-full" />
            )}
            <Eye className="w-3 h-3 absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100 text-indigo-600 bg-white rounded-full" />
          </button>
        ) : (
          <span className="text-gray-300 text-xs">-</span>
        )}
      </td>
    );
  };

  // Рендер ячейки оценки руководителя (managers_only)
  // Показывает: среднее от подчинённых / оценка начальника
  const renderManagementCell = (employee, criterion) => {
    // Если сотрудник не является руководителем - показываем N/A
    if (!employee.has_subordinates) {
      return (
        <td key={`mgmt-${employee.id}-${criterion.criteria_id}`} className="px-2 py-3 text-center border-l border-teal-50">
          <span className="text-gray-200 text-xs">N/A</span>
        </td>
      );
    }

    const subordinateAvg = criterion.subordinate_avg_score;
    const subordinateCount = criterion.subordinate_count;
    const bossScore = criterion.boss_score;
    const hasSubordinateScore = subordinateAvg !== null && subordinateAvg !== undefined;
    const hasBossScore = bossScore !== null && bossScore !== undefined;

    // Формируем tooltip
    let tooltipText = '';
    if (hasSubordinateScore) {
      tooltipText += `Среднее от подчинённых (${subordinateCount}): ${subordinateAvg}`;
    }
    if (hasBossScore) {
      tooltipText += tooltipText ? `, Оценка начальника: ${bossScore}` : `Оценка начальника: ${bossScore}`;
    }
    if (!tooltipText) {
      tooltipText = 'Нет оценок';
    }

    return (
      <td key={`mgmt-${employee.id}-${criterion.criteria_id}`} className="px-2 py-3 text-center border-l border-teal-50">
        <button
          onClick={(e) => handleScoreClick(e, employee, criterion, 'management')}
          className="flex items-center justify-center gap-1 hover:bg-teal-50 rounded-lg p-1 transition-colors group cursor-pointer"
          title={tooltipText}
        >
          {/* Среднее от подчинённых */}
          <span className={`inline-flex items-center justify-center min-w-[24px] h-6 px-1 rounded-full font-bold text-[10px] ${
            hasSubordinateScore ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-400'
          }`}>
            {hasSubordinateScore ? subordinateAvg : '-'}
          </span>
          
          <span className="text-gray-300 text-[10px]">/</span>
          
          {/* Оценка начальника */}
          <span className={`inline-flex items-center justify-center min-w-[24px] h-6 px-1 rounded-full font-bold text-[10px] ${
            hasBossScore ? 'bg-cyan-100 text-cyan-700' : 'bg-gray-100 text-gray-400'
          }`}>
            {hasBossScore ? bossScore : '-'}
          </span>
          
          <Eye className="w-3 h-3 text-gray-300 group-hover:text-teal-500 opacity-0 group-hover:opacity-100 transition-all ml-1" />
        </button>
      </td>
    );
  };

  // Рендер сортируемого заголовка критерия
  const renderSortableHeader = (criterion, borderClass) => {
    const field = `criteria_${criterion.criteria_id}`;
    const isActive = sorting?.field === field;
    
    return (
      <th 
        key={`header-${criterion.criteria_id}`} 
        className={`px-2 py-2 text-[10px] text-center border-l ${borderClass} max-w-[100px] cursor-pointer hover:bg-gray-100 transition-colors ${isActive ? 'bg-indigo-50' : ''}`}
        onClick={() => onSort && onSort(field)}
        title={`Сортировать по "${criterion.criteria_title}"`}
      >
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-gray-600 truncate w-full">{criterion.criteria_title}</span>
          {getSortIcon(field)}
        </div>
      </th>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-sm">
          {/* Заголовок с группами */}
          <thead className="bg-gray-50 border-b-2 border-gray-200">
            <tr>
              <th className="px-4 py-3 text-xs font-bold text-gray-700 uppercase sticky left-0 bg-gray-50 z-10">
                Сотрудник
              </th>
              
              {headerGroups.self.length > 0 && (
                <th colSpan={headerGroups.self.length} className="px-4 py-3 text-xs font-bold text-center bg-blue-100 text-blue-800 uppercase border-x-2 border-blue-200">
                  ⭐ Само / 👔 Рук.
                </th>
              )}
              
              {headerGroups.general.length > 0 && (
                <th colSpan={headerGroups.general.length} className="px-4 py-3 text-xs font-bold text-center bg-green-100 text-green-800 uppercase border-x-2 border-green-200">
                  📋 Общие
                </th>
              )}
              
              {headerGroups.project.length > 0 && (
                <th colSpan={headerGroups.project.length} className="px-4 py-3 text-xs font-bold text-center bg-purple-100 text-purple-800 uppercase border-x-2 border-purple-200">
                  🎯 Проектные
                </th>
              )}
              
              {headerGroups.management.length > 0 && (
                <th colSpan={headerGroups.management.length} className="px-4 py-3 text-xs font-bold text-center bg-teal-100 text-teal-800 uppercase border-x-2 border-teal-200">
                  👥 Как руководитель (подч./нач.)
                </th>
              )}
              
              {headerGroups.c_level.length > 0 && (
                <th colSpan={headerGroups.c_level.length} className="px-4 py-3 text-xs font-bold text-center bg-orange-100 text-orange-800 uppercase border-x-2 border-orange-200">
                  👑 C-level
                </th>
              )}
            </tr>
            
            {/* Названия критериев с сортировкой */}
            <tr className="bg-gray-50 border-b border-gray-200">
              {/* Сортировка по имени/отделу */}
              <th className="px-2 py-2 sticky left-0 bg-gray-50 z-10">
                <div className="flex gap-1">
                  <button
                    onClick={() => onSort && onSort('full_name')}
                    className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors ${
                      sorting?.field === 'full_name' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'
                    }`}
                    title="Сортировать по имени"
                  >
                    Имя {getSortIcon('full_name')}
                  </button>
                  <button
                    onClick={() => onSort && onSort('department_name')}
                    className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors ${
                      sorting?.field === 'department_name' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'
                    }`}
                    title="Сортировать по отделу"
                  >
                    Отдел {getSortIcon('department_name')}
                  </button>
                </div>
              </th>
              
              {headerGroups.self.map(c => renderSortableHeader(c, 'border-blue-100'))}
              {headerGroups.general.map(c => renderSortableHeader(c, 'border-green-100'))}
              {headerGroups.project.map(c => renderSortableHeader(c, 'border-purple-100'))}
              {headerGroups.management.map(c => renderSortableHeader(c, 'border-teal-100'))}
              {headerGroups.c_level.map(c => renderSortableHeader(c, 'border-orange-100'))}
            </tr>
          </thead>
          
          {/* Тело таблицы */}
          <tbody>
            {employees.length === 0 ? (
              <tr>
                <td colSpan="100" className="px-4 py-8 text-center text-gray-500">
                  Нет сотрудников по выбранным фильтрам
                </td>
              </tr>
            ) : (
              employees.map((emp) => {
                // Ячейки строки ищутся по criteria_id заголовка; объекты
                // заголовка несут данные ЧУЖОЙ строки и в ячейки не попадают.
                const rowCriteria = new Map(
                  (emp.criteria || []).map(c => [c.criteria_id, c])
                );

                return (
                  <tr 
                    key={emp.id}
                    className="hover:bg-gray-50 transition-colors border-b border-gray-100"
                  >
                    {/* Сотрудник */}
                    <td className="px-4 py-3 sticky left-0 bg-white z-10">
                      <button
                        onClick={(e) => handleNameClick(e, emp)}
                        className="flex items-center gap-2 text-left hover:bg-indigo-50 rounded-lg p-1 -m-1 transition-colors group w-full"
                        title="Показать все оценки сотрудника"
                      >
                        <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-bold text-xs group-hover:bg-indigo-200 transition-colors">
                          {emp.full_name?.charAt(0)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-gray-900 text-xs truncate group-hover:text-indigo-700 transition-colors">
                            {emp.full_name}
                          </div>
                          <div className="text-[10px] text-gray-500 truncate">
                            {emp.department_name && <span className="text-purple-600">{emp.department_name} • </span>}
                            {emp.job_title}
                            {emp.grade_code && <span className="ml-1 text-indigo-600">• {emp.grade_code}</span>}
                          </div>
                        </div>
                        <Eye className="w-4 h-4 text-gray-300 group-hover:text-indigo-500 opacity-0 group-hover:opacity-100 transition-all" />
                      </button>
                    </td>
                    
                    {/* Самооценка + Оценка менеджера */}
                    {headerGroups.self.map(hc => {
                      const c = rowCriteria.get(hc.criteria_id);
                      return c
                        ? renderSelfCell(emp, c)
                        : renderMissingCell('self', emp, hc, 'border-blue-50');
                    })}

                    {/* Общие */}
                    {headerGroups.general.map(hc => {
                      const c = rowCriteria.get(hc.criteria_id);
                      return c
                        ? renderScoreCell(emp, c, 'general', 'border-green-50')
                        : renderMissingCell('general', emp, hc, 'border-green-50');
                    })}

                    {/* Проектные: неприменимый критерий = N/A в СВОЕЙ колонке */}
                    {headerGroups.project.map(hc => {
                      const c = rowCriteria.get(hc.criteria_id);
                      return c
                        ? renderProjectCell(emp, c)
                        : renderMissingCell('proj', emp, hc, 'border-purple-50', 'N/A');
                    })}

                    {/* Оценка руководителя */}
                    {headerGroups.management.map(hc => {
                      const c = rowCriteria.get(hc.criteria_id);
                      return c
                        ? renderManagementCell(emp, c)
                        : renderMissingCell('mgmt', emp, hc, 'border-teal-50', 'N/A');
                    })}

                    {/* C-level */}
                    {headerGroups.c_level.map((hc, idx) => {
                      const c = rowCriteria.get(hc.criteria_id);
                      if (!c) {
                        return renderMissingCell('clvl', emp, hc, 'border-orange-50');
                      }
                      const writable = canReceiveCLevel(emp, period);
                      const actorScore = c.actor_c_level_score ?? null;
                      const displayed = actorScore ?? c.c_level_score;
                      const isEdit = Boolean(emp.actor_c_level_evaluation_id);
                      return (
                      <td 
                        key={`clvl-${emp.id}-${c.criteria_id}`} 
                        className={`px-2 py-3 text-center border-l border-orange-50 ${idx === 0 ? 'border-l-2 border-l-orange-200' : ''}`}
                      >
                        {writable ? (
                        <button
                          onClick={(e) => handleCLevelClick(e, emp)}
                          className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-xs transition-all cursor-pointer group relative ${
                            displayed
                              ? 'bg-orange-100 text-orange-700 hover:bg-orange-200 hover:ring-2 hover:ring-offset-1 hover:ring-orange-400' 
                              : 'bg-orange-50 text-orange-400 hover:bg-orange-100 border-2 border-dashed border-orange-300'
                          }`}
                          title={isEdit ? 'Изменить C-level оценку' : 'Добавить C-level оценку'}
                        >
                          {displayed ? (
                            <>
                              {displayed}
                              <Edit2 className="w-3 h-3 absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 text-orange-600 bg-white rounded-full" />
                            </>
                          ) : (
                            <Star className="w-4 h-4" />
                          )}
                        </button>
                        ) : (
                          <span
                            className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-xs ${
                              displayed ? 'bg-gray-100 text-gray-500' : 'text-gray-300'
                            }`}
                            title="C-level оценка недоступна для этого сотрудника в выбранном периоде"
                          >
                            {displayed || '-'}
                          </span>
                        )}
                      </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      
      {/* Легенда */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-green-100 rounded-full"></div>
            <span>Оценка менеджера</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-amber-100 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-2.5 h-2.5 text-amber-600" />
            </div>
            <span>С корректировкой</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-teal-100 rounded-full"></div>
            <span>/</span>
            <div className="w-4 h-4 bg-cyan-100 rounded-full"></div>
            <span>Ср. от подчинённых / Оценка начальника</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-orange-100 rounded-full"></div>
            <span>C-level</span>
          </div>
        </div>
        
        {sorting && sorting.field !== 'full_name' && (
          <div className="text-xs text-gray-500">
            Сортировка: <span className="font-medium text-indigo-600">
              {sorting.field === 'department_name' ? 'Отдел' : 
               sorting.field === 'grade_code' ? 'Грейд' :
               sorting.field.startsWith('criteria_') ? 'Критерий' : sorting.field}
            </span>
            {sorting.direction === 'asc' ? ' ↑' : ' ↓'}
          </div>
        )}
      </div>
    </div>
  );
};

export default EvaluationsMatrixTable;
