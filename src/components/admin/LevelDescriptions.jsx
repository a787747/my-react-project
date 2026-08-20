/**
 * LevelDescriptions - Секция описаний уровней оценки
 * 
 * Назначение: Редактирование описаний для каждого уровня оценки (1-10)
 * Используется в: CriteriaForm (AdminSettings)
 * 
 * Props:
 * - formData: object - данные формы с полями level_0_desc ... level_10_desc
 * - onChange: function(fieldName, value) - колбэк изменения поля
 * - isOpen: boolean - развернута ли секция
 * - onToggle: function - колбэк переключения
 */

import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const LevelDescriptions = ({ formData, onChange, isOpen, onToggle }) => {
  // Массив уровней от 1 до 10
  const levels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  return (
    <div className="border-t pt-3">
      {/* Кнопка раскрытия/скрытия */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 bg-slate-100 rounded hover:bg-slate-200 transition-colors"
      >
        <span className="font-bold text-slate-700">📊 Описания уровней оценки (1-10)</span>
        {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
      </button>

      {/* Поля описаний */}
      {isOpen && (
        <div className="mt-3 grid grid-cols-1 gap-2 bg-slate-50 p-4 rounded">
          {levels.map(level => (
            <div key={level} className="flex items-center gap-2">
              <label className="w-24 text-sm font-bold text-slate-700 shrink-0">
                Уровень {level}:
              </label>
              <input
                type="text"
                className="flex-1 p-2 border rounded text-sm"
                placeholder={`Описание для оценки ${level}`}
                value={formData[`level_${level}_desc`] || ''}
                onChange={e => onChange(`level_${level}_desc`, e.target.value)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LevelDescriptions;

