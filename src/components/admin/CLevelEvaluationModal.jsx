/**
 * CLevelEvaluationModal - Модальное окно C-level оценки
 * 
 * Назначение: Форма для проведения C-level оценки сотрудника
 * Используется в: AdminEvaluationsMatrix
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - сотрудник для оценки
 * - submitting: boolean - статус отправки
 * - onClose: function - закрыть окно
 * - onSubmit: function(grades) - отправить оценку
 */

import React, { useState, useEffect } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { groupCriteria } from '../../utils/matrixUtils';

const CLevelEvaluationModal = ({ isOpen, employee, submitting, onClose, onSubmit }) => {
  const [grades, setGrades] = useState({});

  // Инициализация оценок при открытии
  useEffect(() => {
    if (isOpen && employee) {
      const cLevelCriteria = groupCriteria(employee.criteria).c_level;
      const initialGrades = {};
      
      cLevelCriteria.forEach(c => {
        initialGrades[c.criteria_id] = c.actor_c_level_score || 5;
      });
      
      setGrades(initialGrades);
    }
  }, [isOpen, employee]);

  if (!isOpen || !employee) return null;

  const cLevelCriteria = groupCriteria(employee.criteria).c_level;

  const handleSliderChange = (criteriaId, value) => {
    setGrades(prev => ({
      ...prev,
      [criteriaId]: parseInt(value)
    }));
  };

  const handleSubmit = () => {
    onSubmit(grades);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-600 to-red-600 text-white p-4 flex justify-between items-start shrink-0">
          <div>
            <h2 className="text-xl font-bold">
              {employee.actor_c_level_evaluation_id ? '👑 Изменить C-level оценку' : '👑 C-level оценка'}
            </h2>
            <p className="text-orange-100 text-sm">{employee.full_name}</p>
            {(employee.grade_code || employee.department_name) && (
              <p className="text-orange-200 text-xs">{employee.grade_code}{employee.department_name && ` • ${employee.department_name}`}</p>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-white/20 rounded-full transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 overflow-y-auto flex-1 min-h-0 space-y-4">
          {cLevelCriteria.map((criterion) => {
            const currentScore = grades[criterion.criteria_id] || 5;
            const levelDesc = criterion[`level_${currentScore}_desc`];
            
            return (
              <div key={criterion.criteria_id} className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                {/* Заголовок критерия */}
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1 pr-3">
                    <h3 className="text-base font-bold text-gray-900">{criterion.criteria_title}</h3>
                    {criterion.criteria_description && (
                      <p className="text-xs text-gray-500 mt-0.5">{criterion.criteria_description}</p>
                    )}
                  </div>
                  <span className="text-2xl font-bold text-orange-600">{currentScore}</span>
                </div>
                
                {/* Слайдер */}
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={currentScore}
                  onChange={(e) => handleSliderChange(criterion.criteria_id, e.target.value)}
                  className="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-orange-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1 px-0.5">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                    <span key={n} className={`w-3 text-center ${currentScore === n ? 'text-orange-600 font-bold' : ''}`}>
                      {n}
                    </span>
                  ))}
                </div>
                
                {/* Описание текущего уровня */}
                {levelDesc && (
                  <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded-lg">
                    <p className="text-xs text-orange-800">
                      <span className="font-semibold">Уровень {currentScore}:</span> {levelDesc}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-100 bg-gray-50 flex gap-3 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-white transition-colors text-sm"
          >
            Отмена
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 px-4 py-2.5 bg-orange-600 text-white rounded-xl font-medium hover:bg-orange-700 transition-colors flex items-center justify-center gap-2 text-sm"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Сохранение...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Сохранить
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CLevelEvaluationModal;

