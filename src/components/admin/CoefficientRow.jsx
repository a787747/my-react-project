/**
 * CoefficientRow - Строка редактирования коэффициентов для одного критерия
 * 
 * Назначение: UI компонент для редактирования веса критерия и коэффициентов оценок (1-10)
 * Используется в: ScoringCoefficientsTable
 * 
 * Props:
 * - criterion: object - критерий с весом и коэффициентами
 * - onWeightChange: function(criteriaId, weight) - изменение веса
 * - onCoefficientChange: function(criteriaId, level, coefficient) - изменение коэффициента
 * - isExpanded: boolean - развернута ли строка
 * - onToggleExpand: function - переключить развернутость
 */

import React from 'react';
import { ChevronDown, ChevronRight, Scale, Sliders } from 'lucide-react';

const CoefficientRow = ({ 
  criterion, 
  onWeightChange, 
  onCoefficientChange,
  isExpanded,
  onToggleExpand
}) => {
  const { id, title, weight, score_coefficients } = criterion;

  // Получить цвет для уровня оценки
  const getLevelColor = (level) => {
    if (level <= 3) return 'bg-red-50 border-red-200 text-red-700';
    if (level <= 6) return 'bg-amber-50 border-amber-200 text-amber-700';
    if (level <= 8) return 'bg-green-50 border-green-200 text-green-700';
    return 'bg-purple-50 border-purple-200 text-purple-700';
  };

  return (
    <div className="border border-slate-200 rounded-lg mb-3 bg-white overflow-hidden">
      {/* Заголовок строки */}
      <div 
        className="flex items-center gap-4 p-4 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={onToggleExpand}
      >
        <button className="text-slate-400 hover:text-slate-600">
          {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </button>
        
        <div className="flex-1">
          <h3 className="font-semibold text-slate-900">{title}</h3>
        </div>
        
        {/* Вес критерия */}
        <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
          <Scale className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-500">Вес:</span>
          <input
            type="number"
            value={weight}
            onChange={e => onWeightChange(id, e.target.value)}
            className="w-20 px-2 py-1 border border-slate-200 rounded text-center font-medium"
            step="0.1"
            min="0.1"
          />
        </div>
      </div>

      {/* Развернутое содержимое с коэффициентами */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-slate-100">
          <div className="pt-4">
            <div className="flex items-center gap-2 mb-3 text-sm text-slate-500">
              <Sliders className="w-4 h-4" />
              <span>Коэффициенты для каждого уровня оценки (1-10):</span>
            </div>
            
            {/* Сетка коэффициентов */}
            <div className="grid grid-cols-10 gap-2">
              {Array.from({ length: 10 }, (_, i) => i + 1).map((level) => (
                <div key={level} className="flex flex-col items-center">
                  <span className={`text-xs font-bold mb-1 px-2 py-0.5 rounded ${getLevelColor(level)}`}>
                    {level}
                  </span>
                  <input
                    type="number"
                    value={score_coefficients[level] || 1.0}
                    onChange={e => onCoefficientChange(id, level, e.target.value)}
                    className="w-full px-1 py-1.5 border border-slate-200 rounded text-center text-sm font-medium hover:border-blue-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                    step="0.1"
                    min="0"
                  />
                </div>
              ))}
            </div>
            
            {/* Подсказка */}
            <p className="mt-3 text-xs text-slate-400">
              Коэффициент умножается на оценку при расчете итогового балла. 
              Значение 1.0 означает, что оценка учитывается как есть.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default CoefficientRow;

