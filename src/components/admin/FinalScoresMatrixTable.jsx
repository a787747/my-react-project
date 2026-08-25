/**
 * FinalScoresMatrixTable - Таблица итоговых баллов сотрудников
 * 
 * Назначение: Отображение взвешенных баллов по критериям с учетом весов и коэффициентов
 * Используется в: AdminFinalScores
 * 
 * Props:
 * - employees: array - список сотрудников с рассчитанными баллами
 * - criteriaList: array - список критериев с весами
 * - sorting: object { field, direction } - текущая сортировка
 * - totals: object - итоговые суммы
 * - onSort: function(field) - изменить сортировку
 * - onEmployeeClick: function(employee) - клик по сотруднику
 */

import React from 'react';
import { ArrowUp, ArrowDown, ArrowUpDown, Trophy, TrendingUp, User, Calculator } from 'lucide-react';
import { getScoreZone } from '../../utils/evaluationUtils';
import { formatCorrectionTooltip, getCriterionCorrections } from '../../utils/matrixUtils';

const FinalScoresMatrixTable = ({ 
  employees, 
  criteriaList = [],
  sorting,
  totals,
  onSort,
  onEmployeeClick
}) => {
  
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

  // Цвет ячейки по СЫРОЙ оценке 1–10, а не по взвешенному произведению.
  // Зоны в evaluationUtils описаны для шкалы 1–10; критерий 14 с нормой 2 после
  // умножения на вес 1.50 попадал в полосу «сверх роли», а критерий 12 при
  // оценке 7 — в «зону исключительности». Раскрашен был вес, не человек.
  const getScoreColor = (rawScore, criterion) => {
    if (rawScore === null || rawScore === undefined || rawScore === 0) return 'text-gray-300';
    const zone = getScoreZone(rawScore, criterion);
    return zone.text;
  };

  // Итог — это ИНДЕКС распределения премии (§4 HANDOVER, формула 3): взвешенная
  // сумма БЕЗ деления на сумму весов, × коэффициент грейда. Он не ограничен
  // сверху и не является оценкой 1–10, поэтому пороги 3/5/7 на нём не значили
  // ничего: A-грейд с шестёрками по всем критериям давал 35.68 и красился в
  // зелёный ровно так же, как M3 с 356.76. Одна нейтральная плашка, число само
  // за себя; сравнивать людей между собой — задача сортировки, а не цвета.
  const getFinalScoreColor = (score) => {
    const val = parseFloat(score);
    if (!Number.isFinite(val) || val === 0) return 'bg-gray-200 text-gray-600';
    return 'bg-indigo-600 text-white';
  };

  // Получить позицию в рейтинге (медаль)
  const getRankBadge = (index) => {
    if (index === 0) return <Trophy className="w-5 h-5 text-yellow-500" />;
    if (index === 1) return <Trophy className="w-5 h-5 text-gray-400" />;
    if (index === 2) return <Trophy className="w-5 h-5 text-amber-600" />;
    return <span className="text-sm text-gray-400 font-medium">{index + 1}</span>;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Итоговая статистика */}
      <div className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-indigo-100">
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-lg p-3 shadow-sm border border-indigo-100">
            <div className="flex items-center gap-2 mb-1">
              <User className="w-4 h-4 text-indigo-500" />
              <span className="text-xs text-gray-500">Сотрудников</span>
            </div>
            <span className="text-2xl font-bold text-indigo-600">{totals.employeesCount}</span>
            {totals.excludedCount > 0 && (
              <div className="text-[10px] text-amber-700 mt-0.5">
                в фонде {totals.poolCount}, вне фонда {totals.excludedCount}
              </div>
            )}
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm border border-green-100">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-green-500" />
              <span className="text-xs text-gray-500">Сумма баллов</span>
            </div>
            <span className="text-2xl font-bold text-green-600">{totals.totalWeightedSum?.toFixed(2) || '0.00'}</span>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm border border-purple-100">
            <div className="flex items-center gap-2 mb-1">
              <Calculator className="w-4 h-4 text-purple-500" />
              <span className="text-xs text-gray-500">Сумма с коэф. грейда</span>
            </div>
            <span className="text-2xl font-bold text-purple-600">{totals.totalWeightedScore?.toFixed(2) || '0.00'}</span>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm border border-amber-100">
            <div className="flex items-center gap-2 mb-1">
              <Trophy className="w-4 h-4 text-amber-500" />
              <span className="text-xs text-gray-500" title="Среднее по людям, которые берут долю фонда">
                Средний итог{totals.excludedCount > 0 ? ` (по ${totals.poolCount})` : ''}
              </span>
            </div>
            <span className="text-2xl font-bold text-amber-600">{totals.averageWeightedScore}</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-sm">
          <thead className="bg-gray-50">
            {/* Строка с весами критериев */}
            <tr className="border-b border-gray-200">
              <th className="px-4 py-2 text-[10px] text-gray-400 uppercase sticky left-0 w-14 min-w-[3.5rem] max-w-[3.5rem] bg-gray-50 z-20">#</th>
              <th className="px-4 py-2 text-[10px] text-gray-400 uppercase sticky left-14 bg-gray-50 z-10">Сотрудник</th>
              
              {criteriaList.map(c => (
                <th 
                  key={`weight-${c.id}`} 
                  className="px-2 py-2 text-center border-x border-gray-100"
                >
                  <span className="text-[10px] text-gray-400 font-normal">
                    вес: {c.weight?.toFixed(1) || '1.0'}
                  </span>
                </th>
              ))}
              
              <th className="px-3 py-2 text-center border-x border-indigo-200 bg-indigo-50"></th>
              <th className="px-3 py-2 text-center border-x border-emerald-200 bg-emerald-50"></th>
            </tr>
            
            {/* Заголовки критериев */}
            <tr className="border-b-2 border-gray-300">
              <th 
                className="px-4 py-3 text-xs font-bold text-gray-700 uppercase sticky left-0 w-14 min-w-[3.5rem] max-w-[3.5rem] bg-gray-50 z-20 cursor-pointer hover:bg-gray-100"
                onClick={() => onSort && onSort('full_name')}
              >
                <div className="flex items-center gap-1">
                  # {getSortIcon('full_name')}
                </div>
              </th>
              <th className="px-4 py-3 text-xs font-bold text-gray-700 uppercase sticky left-14 bg-gray-50 z-10">
                Сотрудник
              </th>
              
              {criteriaList.map(c => (
                <th 
                  key={`header-${c.id}`} 
                  className="px-2 py-3 text-[10px] text-center border-x border-gray-100 max-w-[80px] cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => onSort && onSort(`criteria_${c.id}`)}
                  title={`${c.title} (вес: ${c.weight || 1.0})`}
                >
                  <div className="truncate font-semibold text-gray-700">{c.title}</div>
                  <div className="mt-0.5">{getSortIcon(`criteria_${c.id}`)}</div>
                </th>
              ))}
              
              <th className="px-3 py-3 text-xs font-bold text-center bg-indigo-100 text-indigo-800 uppercase border-x border-indigo-200">
                <button
                  onClick={() => onSort && onSort('weighted_sum')}
                  className="flex items-center justify-center gap-1 w-full hover:text-indigo-600 transition-colors"
                  title="Сумма взвешенных баллов"
                >
                  Σ баллов
                  {getSortIcon('weighted_sum')}
                </button>
              </th>
              <th className="px-3 py-3 text-xs font-bold text-center bg-emerald-100 text-emerald-800 uppercase border-x border-emerald-200">
                <button
                  onClick={() => onSort && onSort('final_weighted_score')}
                  className="flex items-center justify-center gap-1 w-full hover:text-emerald-600 transition-colors"
                  title="Итог с коэф. грейда"
                >
                  Итог
                  {getSortIcon('final_weighted_score')}
                </button>
              </th>
            </tr>
          </thead>
          
          <tbody>
            {employees.length === 0 ? (
              <tr>
                <td colSpan={criteriaList.length + 4} className="px-4 py-8 text-center text-gray-500">
                  Нет сотрудников по выбранным фильтрам
                </td>
              </tr>
            ) : (
              employees.map((emp, index) => (
                <tr 
                  key={emp.id}
                  className="hover:bg-gray-50 transition-colors border-b border-gray-100"
                >
                  {/* Позиция в рейтинге */}
                  <td className="px-4 py-3 sticky left-0 w-14 min-w-[3.5rem] max-w-[3.5rem] bg-white z-20 text-center">
                    {getRankBadge(index)}
                  </td>
                  
                  {/* Сотрудник */}
                  <td className="px-3 py-3 sticky left-14 bg-white z-10">
                    <button
                      onClick={() => onEmployeeClick && onEmployeeClick(emp)}
                      className="flex items-center gap-2 text-left hover:bg-indigo-50 rounded-lg p-1 -m-1 transition-colors group w-full"
                      title="Показать детали"
                    >
                      <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-bold text-sm group-hover:bg-indigo-200 transition-colors">
                        {emp.full_name?.charAt(0)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-gray-900 text-sm truncate group-hover:text-indigo-700 transition-colors max-w-[140px]">
                          {emp.full_name}
                        </div>
                        <div className="text-[10px] text-gray-500 truncate max-w-[140px]">
                          {emp.department_name && <span className="text-purple-600">{emp.department_name}</span>}
                          {emp.grade_code ? (
                            <span className="ml-1 text-indigo-600">
                              • {emp.grade_code} (×{emp.grade_coefficient?.toFixed(2) || '1.00'})
                            </span>
                          ) : (
                            <span
                              className="ml-1 text-orange-600 font-semibold"
                              title="Грейд не задан — в расчёте подставлен множитель 1.00. Это дефект карточки, а не решение."
                            >
                              • без грейда (×1.00)
                            </span>
                          )}
                        </div>
                        {emp.takes_bonus_share === false && (
                          <div
                            className="text-[10px] font-semibold text-amber-700"
                            data-testid="no-bonus-share"
                            title={
                              emp.is_in_scope === false
                                ? 'Вне охвата этого периода: доли премиального фонда не берёт, в ИТОГО и в средний не входит.'
                                : 'Этого человека не оценивает никто: доли премиального фонда не берёт, в ИТОГО и в средний не входит.'
                            }
                          >
                            {emp.is_in_scope === false ? 'вне охвата периода' : 'не оценивается никем'}
                          </div>
                        )}
                      </div>
                    </button>
                  </td>
                  
                  {/* Баллы по критериям.
                      Три разных состояния, которые до 2026-08-25 рисовались
                      одним прочерком: критерий к человеку не применяется,
                      применяется но ещё не оценен, оценен. */}
                  {criteriaList.map(c => {
                    const criterionScore = emp.criteria_scores?.[c.id];
                    const rawScore = emp.criteria_raw_scores?.[c.id];
                    const applicable = Boolean(emp.criteria_by_id?.[c.id]);
                    const corrections = applicable
                      ? getCriterionCorrections(emp.criteria_by_id[c.id])
                      : { hasAny: false };
                    const scored = criterionScore !== null && criterionScore !== undefined;
                    return (
                      <td 
                        key={`score-${emp.id}-${c.id}`} 
                        className={`px-2 py-3 text-center border-x border-gray-50 ${applicable ? '' : 'bg-gray-50'}`}
                        title={
                          !applicable
                            ? `«${c.title}» не применяется к этому сотруднику`
                            : scored
                              ? [
                                // formatCorrectionTooltip knows the manager path
                                // only; a c_level_only cell has no manager score
                                // and would otherwise open with a bare « · ».
                                formatCorrectionTooltip(emp.criteria_by_id[c.id]),
                                `${rawScore?.toFixed(2)} × коэф. × вес ${c.weight?.toFixed(2)} = ${criterionScore.toFixed(2)}`,
                              ].filter(Boolean).join(' · ')
                              : `«${c.title}» ещё не оценен`
                        }
                      >
                        {!applicable ? (
                          <span className="text-[10px] text-gray-400">н/п</span>
                        ) : (
                          <span className={`font-bold text-sm ${getScoreColor(rawScore, c)}`}>
                            {scored ? criterionScore.toFixed(2) : '-'}
                            {corrections.hasAny && (
                              <sup className="ml-0.5 text-[10px] text-amber-600" title="Есть корректировка">*</sup>
                            )}
                          </span>
                        )}
                      </td>
                    );
                  })}
                  
                  {/* Сумма взвешенных баллов */}
                  <td className="px-3 py-3 text-center border-x border-indigo-100 bg-indigo-50">
                    <span className="font-bold text-indigo-700 text-base">
                      {emp.weighted_sum?.toFixed(2) || '0.00'}
                    </span>
                  </td>
                  
                  {/* Итоговый балл с коэф. грейда */}
                  <td className="px-3 py-3 text-center border-x border-emerald-100">
                    <span className={`inline-flex items-center justify-center px-3 py-1.5 rounded-lg font-bold text-base ${getFinalScoreColor(emp.final_weighted_score)}`}>
                      {emp.final_weighted_score?.toFixed(2) || '0.00'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
          
          {/* Итоги */}
          {employees.length > 0 && (
            <tfoot className="bg-gray-100 border-t-2 border-gray-300">
              <tr className="font-bold">
                <td className="px-4 py-4 sticky left-0 w-14 min-w-[3.5rem] max-w-[3.5rem] bg-gray-100 z-20"></td>
                <td className="px-3 py-4 sticky left-14 bg-gray-100 z-10 text-gray-700 text-sm">
                  ИТОГО ({totals.poolCount} чел. в фонде
                  {totals.excludedCount > 0 ? `, ${totals.excludedCount} вне` : ''})
                </td>
                
                {/* Суммы по критериям */}
                {criteriaList.map(c => (
                  <td 
                    key={`sum-${c.id}`} 
                    className="px-2 py-4 text-center border-x border-gray-200 bg-gray-50"
                  >
                    <span className="text-gray-600 text-sm">
                      {totals.criteriaSums?.[c.id]?.toFixed(1) || '-'}
                    </span>
                  </td>
                ))}
                
                {/* Общая сумма баллов */}
                <td className="px-3 py-4 text-center border-x border-indigo-200 bg-indigo-100">
                  <span className="text-indigo-800 text-lg">
                    {totals.totalWeightedSum?.toFixed(2) || '0.00'}
                  </span>
                </td>
                
                {/* Общая сумма с коэф. грейда */}
                <td className="px-3 py-4 text-center border-x border-emerald-200 bg-emerald-100">
                  <span className="text-emerald-800 text-lg">
                    {totals.totalWeightedScore?.toFixed(2) || '0.00'}
                  </span>
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      
      {/* Легенда */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
        <div className="text-xs text-gray-500">
          <p className="mb-1">
            <strong>Балл по критерию</strong> = оценка × коэффициент_оценки × вес_критерия
          </p>
          <p className="mb-1">
            <strong>Σ баллов</strong> = сумма всех баллов по критериям
          </p>
          <p>
            <strong className="text-emerald-600">Итог</strong> = Σ баллов × коэффициент_грейда
          </p>
        </div>
      </div>
    </div>
  );
};

export default FinalScoresMatrixTable;

