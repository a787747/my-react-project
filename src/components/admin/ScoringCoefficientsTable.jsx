/**
 * ScoringCoefficientsTable - Таблица с коэффициентами для всех критериев
 * 
 * Назначение: Отображение и редактирование весов и коэффициентов критериев
 * Используется в: AdminScoring
 * 
 * Props:
 * - criteria: array - список критериев с коэффициентами
 * - onWeightChange: function(criteriaId, weight) - изменение веса
 * - onCoefficientChange: function(criteriaId, level, coefficient) - изменение коэффициента
 */

import React, { useState } from 'react';
import { Calculator, Info, ChevronDown, ChevronUp } from 'lucide-react';
import CoefficientRow from './CoefficientRow';

const ScoringCoefficientsTable = ({ 
  criteria, 
  onWeightChange, 
  onCoefficientChange 
}) => {
  // Состояние для развернутых строк
  const [expandedRows, setExpandedRows] = useState({});
  const [showFormula, setShowFormula] = useState(false);

  // Переключить развернутость строки
  const toggleRow = (id) => {
    setExpandedRows(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Развернуть/свернуть все
  const toggleAll = () => {
    const allExpanded = criteria.every(c => expandedRows[c.id]);
    const newState = {};
    criteria.forEach(c => {
      newState[c.id] = !allExpanded;
    });
    setExpandedRows(newState);
  };

  const allExpanded = criteria.length > 0 && criteria.every(c => expandedRows[c.id]);

  return (
    <div>
      {/* Информация о формуле */}
      <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
        <button 
          className="w-full flex items-center justify-between text-left"
          onClick={() => setShowFormula(!showFormula)}
        >
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-blue-900">Формула расчета итогового балла</span>
          </div>
          {showFormula ? <ChevronUp className="w-5 h-5 text-blue-600" /> : <ChevronDown className="w-5 h-5 text-blue-600" />}
        </button>
        
        {showFormula && (
          <div className="mt-4 pt-4 border-t border-blue-200">
            <div className="bg-white p-4 rounded-lg border border-blue-100 font-mono text-sm">
              <p className="text-slate-700 mb-2">
                <strong>Итоговый балл</strong> = (Σ(оценка × коэффициент_оценки × вес_критерия) / Σ(весов)) × коэффициент_грейда
              </p>
            </div>
            <div className="mt-3 text-sm text-blue-800">
              <p className="flex items-start gap-2 mb-1">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Оценка</strong> — значение от 1 до 10, выставленное оценщиком</span>
              </p>
              <p className="flex items-start gap-2 mb-1">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Коэффициент оценки</strong> — множитель для конкретного уровня оценки (настраивается ниже)</span>
              </p>
              <p className="flex items-start gap-2 mb-1">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Вес критерия</strong> — важность критерия относительно других</span>
              </p>
              <p className="flex items-start gap-2">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Коэффициент грейда</strong> — множитель, зависящий от грейда сотрудника</span>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Кнопка развернуть/свернуть все */}
      <div className="flex justify-end mb-4">
        <button
          onClick={toggleAll}
          className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"
        >
          {allExpanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Свернуть все
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Развернуть все
            </>
          )}
        </button>
      </div>

      {/* Список критериев */}
      <div className="space-y-1">
        {criteria.map(criterion => (
          <CoefficientRow
            key={criterion.id}
            criterion={criterion}
            onWeightChange={onWeightChange}
            onCoefficientChange={onCoefficientChange}
            isExpanded={!!expandedRows[criterion.id]}
            onToggleExpand={() => toggleRow(criterion.id)}
          />
        ))}
      </div>

      {/* Пустое состояние */}
      {criteria.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          <Calculator className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Нет активных критериев для настройки</p>
        </div>
      )}
    </div>
  );
};

export default ScoringCoefficientsTable;

