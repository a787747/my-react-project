/**
 * CalculationCard - Карточка с детальной калькуляцией баллов сотрудника
 * 
 * Назначение: Отображение пошагового расчёта итогового балла
 * Используется в: AdminScoreCalculator
 * 
 * Props:
 * - calculation: Object - объект с данными калькуляции
 * - allCriteria: Array - общий список критериев для синхронизации между карточками
 * - onRemove: Function - callback для удаления карточки
 */

import React from 'react';
import { X, Award } from 'lucide-react';
import { getScoreZone } from '../../utils/evaluationUtils';

const CalculationCard = ({ calculation, allCriteria = [], onRemove }) => {
  if (!calculation) return null;

  const {
    full_name,
    department_name,
    grade_code,
    grade_coefficient,
    criteria,
    total_weighted_sum,
    final_score
  } = calculation;

  // Определяем зону итоговой оценки
  const scoreZone = getScoreZone(final_score);

  // Создаём карту критериев сотрудника для быстрого поиска
  const criteriaMap = {};
  criteria.forEach(c => {
    criteriaMap[c.criteria_id] = c;
  });

  // Группируем критерии по категориям
  const groupCriteria = (criteriaList) => {
    const groups = {
      general: { title: 'Общие критерии', items: [] },
      project: { title: 'Проектные критерии', items: [] },
      manager: { title: 'Критерии для менеджеров', items: [] },
      clevel: { title: 'C-Level критерии', items: [] }
    };

    criteriaList.forEach(crit => {
      if (crit.c_level_only) {
        groups.clevel.items.push(crit);
      } else if (crit.target_audience === 'managers_only') {
        groups.manager.items.push(crit);
      } else if (['project_participants', 'project', 'tender'].includes(crit.target_audience)) {
        groups.project.items.push(crit);
      } else {
        groups.general.items.push(crit);
      }
    });

    return Object.values(groups).filter(g => g.items.length > 0);
  };

  // Используем allCriteria если передан, иначе берём из calculation
  const criteriaToShow = allCriteria.length > 0 ? allCriteria : criteria;
  const groups = groupCriteria(criteriaToShow);

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden flex flex-col h-full text-xs">
      {/* Шапка карточки - компактная */}
      <div className="px-3 py-2 bg-gradient-to-r from-slate-50 to-gray-50 border-b border-gray-100">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-gray-900 text-sm truncate" title={full_name}>
              {full_name}
            </h3>
            <p className="text-[10px] text-gray-500 truncate">
              {department_name}
            </p>
          </div>
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors flex-shrink-0"
              title="Убрать"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        
        {/* Грейд */}
        <div className="mt-1.5 flex items-center gap-2 text-[10px]">
          <span className="inline-flex items-center px-1.5 py-0.5 bg-white rounded border border-gray-200">
            <Award className="w-2.5 h-2.5 text-amber-500 mr-1" />
            <span className="font-medium text-gray-700">{grade_code || '—'}</span>
          </span>
          <span className="text-gray-500">
            коэф: <span className="font-semibold text-gray-700">{grade_coefficient.toFixed(2)}</span>
          </span>
        </div>
      </div>

      {/* Критерии по группам */}
      <div className="flex-1 overflow-auto">
        {groups.map((group, groupIndex) => (
          <div key={groupIndex}>
            {/* Заголовок группы */}
            <div className="px-2 py-1 bg-gray-100 text-[9px] font-semibold text-gray-500 uppercase tracking-wide sticky top-0">
              {group.title}
            </div>
            
            {/* Критерии */}
            {group.items.map((crit) => {
              // Получаем данные критерия для этого сотрудника
              const empCrit = criteriaMap[crit.criteria_id];
              const hasScore = empCrit && empCrit.raw_score !== undefined;
              
              return (
                <div 
                  key={crit.criteria_id}
                  className="px-2 py-1.5 border-b border-gray-50 hover:bg-gray-50/50"
                >
                  {/* Название критерия */}
                  <div className="text-[10px] text-gray-600 leading-tight mb-0.5 line-clamp-2" title={crit.criteria_title}>
                    {crit.criteria_title}
                  </div>
                  
                  {/* Расчёт */}
                  {hasScore ? (
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-gray-400 font-mono">
                        {empCrit.raw_score.toFixed(1)}×{empCrit.score_coefficient.toFixed(1)}×{empCrit.weight.toFixed(1)}
                      </span>
                      <span className="font-bold text-gray-900">
                        = {empCrit.weighted_score.toFixed(2)}
                      </span>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-300 italic">
                      — нет оценки —
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Итоговый расчёт - компактный */}
      <div className="px-3 py-2 bg-gradient-to-r from-slate-50 to-gray-50 border-t border-gray-100">
        <div className="flex items-center justify-between text-[10px] text-gray-600 mb-1">
          <span>Σ баллов</span>
          <span className="font-semibold">{total_weighted_sum.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between text-[10px] text-gray-600 mb-2">
          <span>× коэф. грейда</span>
          <span className="font-mono text-gray-500">{total_weighted_sum.toFixed(2)} × {grade_coefficient.toFixed(2)}</span>
        </div>
        
        {/* Итоговый балл */}
        <div className={`p-2 rounded-lg border text-center ${scoreZone.bg} ${scoreZone.border}`}>
          <p className={`text-xl font-bold ${scoreZone.text}`}>
            {final_score.toFixed(2)}
          </p>
          <p className={`text-[9px] font-medium ${scoreZone.text}`}>
            {scoreZone.label}
          </p>
        </div>
      </div>
    </div>
  );
};

export default CalculationCard;
