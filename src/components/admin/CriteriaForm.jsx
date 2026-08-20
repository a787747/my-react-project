/**
 * CriteriaForm - Форма редактирования/создания критерия
 * 
 * Назначение: Полная форма для редактирования критерия оценки
 * Используется в: AdminSettings (внутри таблицы критериев)
 * 
 * Props:
 * - formData: object - данные формы
 * - audiences: array - список аудиторий
 * - isNew: boolean - создание нового критерия
 * - onFormChange: function(formData) - колбэк изменения формы
 * - onSave: function - колбэк сохранения
 * - onCancel: function - колбэк отмены
 */

import React, { useState } from 'react';
import { ToggleLeft, ToggleRight, Check, User, Users, Shield } from 'lucide-react';
import RoleCheckbox from './RoleCheckbox';
import LevelDescriptions from './LevelDescriptions';

const CriteriaForm = ({ 
  formData, 
  audiences, 
  isNew, 
  onFormChange, 
  onSave, 
  onCancel 
}) => {
  const [showLevelDescriptions, setShowLevelDescriptions] = useState(false);

  // Обработчик изменения поля формы
  const handleChange = (field, value) => {
    onFormChange({ ...formData, [field]: value });
  };

  return (
    <td className="p-4" colSpan="5">
      {/* Название */}
      <input 
        className="w-full p-2 border rounded mb-2 font-bold" 
        placeholder="Название критерия"
        value={formData.title || ''}
        onChange={e => handleChange('title', e.target.value)}
      />
      
      {/* Описание */}
      <textarea 
        className="w-full p-2 border rounded text-sm mb-3" 
        placeholder="Описание (подсказка)"
        rows="2"
        value={formData.description || ''}
        onChange={e => handleChange('description', e.target.value)}
      />

      {/* Аудитория и статус */}
      <div className="flex gap-4 mb-4 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-bold text-slate-600 mb-1">Аудитория</label>
          <select 
            className="w-full p-2 border rounded"
            value={formData.target_audience || 'all'}
            onChange={e => handleChange('target_audience', e.target.value)}
          >
            {audiences.map(a => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
        </div>
        
        {/* Переключатель активности */}
        <div className="flex items-end">
          <button 
            type="button"
            onClick={() => handleChange('is_active', !formData.is_active)}
            className="flex items-center gap-2 text-sm"
          >
            {formData.is_active 
              ? <ToggleRight className="text-green-600 w-8 h-8"/> 
              : <ToggleLeft className="text-slate-400 w-8 h-8"/>
            }
            <span className="font-bold">{formData.is_active ? 'Активен' : 'Отключен'}</span>
          </button>
        </div>
      </div>

      {/* Чекбоксы ролей */}
      <div className="mb-4 p-3 bg-white rounded border border-slate-200">
        <label className="block text-xs font-bold text-slate-600 mb-3">
          Кто может оценивать по этому критерию:
        </label>
        <div className="flex gap-6 flex-wrap">
          <RoleCheckbox
            checked={formData.selfassesment}
            onChange={() => handleChange('selfassesment', !formData.selfassesment)}
            icon={User}
            label="Самооценка"
            activeColor="bg-blue-600"
          />
          <RoleCheckbox
            checked={formData.for_manager}
            onChange={() => handleChange('for_manager', !formData.for_manager)}
            icon={Users}
            label="Менеджер"
            activeColor="bg-green-600"
          />
          <RoleCheckbox
            checked={formData.c_level_only}
            onChange={() => handleChange('c_level_only', !formData.c_level_only)}
            icon={Shield}
            label="C-level / Admin"
            activeColor="bg-purple-600"
          />
        </div>
        <p className="text-xs text-slate-500 mt-2">
          C-level и Admin всегда видят все критерии. Этот флаг добавляет критерии, доступные только им.
        </p>
      </div>

      {/* Описания уровней */}
      <LevelDescriptions
        formData={formData}
        onChange={handleChange}
        isOpen={showLevelDescriptions}
        onToggle={() => setShowLevelDescriptions(!showLevelDescriptions)}
      />

      {/* Кнопки действий */}
      <div className="mt-4 flex justify-end gap-2">
        <button 
          type="button"
          onClick={onCancel} 
          className="bg-slate-200 text-slate-700 px-4 py-2 rounded hover:bg-slate-300 font-bold"
        >
          Отмена
        </button>
        <button 
          type="button"
          onClick={onSave} 
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 font-bold flex items-center gap-2"
        >
          <Check className="w-4 h-4"/> Сохранить
        </button>
      </div>
    </td>
  );
};

export default CriteriaForm;

