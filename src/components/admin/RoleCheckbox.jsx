/**
 * RoleCheckbox - Чекбокс для выбора ролей
 * 
 * Назначение: Стилизованный чекбокс с иконкой для выбора ролей оценщика
 * Используется в: CriteriaForm (AdminSettings)
 * 
 * Props:
 * - checked: boolean - состояние чекбокса
 * - onChange: function - колбэк при изменении
 * - icon: Component - иконка из lucide-react
 * - label: string - текст метки
 * - activeColor: string - цвет активного состояния (например, 'bg-blue-600')
 */

import React from 'react';
import { Check } from 'lucide-react';

const RoleCheckbox = ({ checked, onChange, icon: Icon, label, activeColor }) => {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      {/* Скрытый нативный чекбокс */}
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only"
      />
      
      {/* Кастомный чекбокс */}
      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
        checked ? `${activeColor} border-transparent` : 'bg-white border-slate-300'
      }`}>
        {checked && <Check className="w-3 h-3 text-white" />}
      </div>
      
      {/* Иконка роли */}
      <Icon className={`w-5 h-5 ${checked ? activeColor.replace('bg-', 'text-').replace('-600', '-600') : 'text-slate-400'}`} />
      
      {/* Текст метки */}
      <span className={`text-sm font-medium ${checked ? 'text-slate-700' : 'text-slate-400'}`}>
        {label}
      </span>
    </label>
  );
};

export default RoleCheckbox;

