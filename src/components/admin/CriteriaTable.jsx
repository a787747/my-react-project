/**
 * CriteriaTable - Таблица критериев оценки
 * 
 * Назначение: Отображение списка критериев с возможностью редактирования
 * Используется в: AdminSettings
 * 
 * Props:
 * - criteria: array - список критериев
 * - audiences: array - список аудиторий
 * - editingId: string | number | null - ID редактируемого критерия ('new' для нового)
 * - editForm: object - данные формы редактирования
 * - onEdit: function(criterion) - начать редактирование
 * - onFormChange: function(formData) - изменить форму
 * - onSave: function - сохранить
 * - onCancel: function - отменить
 * - onDelete: function(id) - удалить критерий
 */

import React from 'react';
import { Edit3, Trash2, Check, User, Users, Shield } from 'lucide-react';
import CriteriaForm from './CriteriaForm';

const CriteriaTable = ({ 
  criteria, 
  audiences, 
  editingId, 
  editForm, 
  onEdit, 
  onFormChange, 
  onSave, 
  onCancel, 
  onDelete 
}) => {
  
  // Отображение бейджей доступа
  const renderAccessBadges = (crit) => {
    const badges = [];
    
    if (crit.selfassesment) {
      badges.push(
        <span key="self" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-700">
          <User className="w-3 h-3" /> Само
        </span>
      );
    }
    if (crit.for_manager) {
      badges.push(
        <span key="mgr" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-700">
          <Users className="w-3 h-3" /> Мен
        </span>
      );
    }
    if (crit.c_level_only) {
      badges.push(
        <span key="clvl" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-700">
          <Shield className="w-3 h-3" /> C-lvl
        </span>
      );
    }
    
    if (badges.length === 0) {
      return <span className="text-xs text-slate-400">Нет доступа</span>;
    }
    
    return <div className="flex flex-wrap gap-1 justify-center">{badges}</div>;
  };

  // Получить название аудитории
  const getAudienceLabel = (audienceId) => {
    const audience = audiences.find(a => a.id === audienceId);
    return audience ? audience.label : audienceId;
  };

  // Получить стили бейджа аудитории
  const getAudienceBadgeClass = (audienceId) => {
    if (audienceId === 'all') return 'bg-slate-100 text-slate-600 border-slate-200';
    if (audienceId === 'project_participants' || audienceId === 'project') return 'bg-purple-100 text-purple-700 border-purple-200';
    return 'bg-blue-100 text-blue-700 border-blue-200';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <table className="w-full text-left border-collapse">
        <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-bold">
          <tr>
            <th className="p-4 border-b">Критерий / Вопрос</th>
            <th className="p-4 border-b w-48">Аудитория</th>
            <th className="p-4 border-b w-32 text-center">Статус</th>
            <th className="p-4 border-b w-44 text-center">Кто оценивает</th>
            <th className="p-4 border-b w-32 text-right">Действия</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {/* Форма создания нового критерия */}
          {editingId === 'new' && (
            <tr className="bg-blue-50">
              <CriteriaForm
                formData={editForm}
                audiences={audiences}
                isNew={true}
                onFormChange={onFormChange}
                onSave={onSave}
                onCancel={onCancel}
              />
            </tr>
          )}

          {/* Список критериев */}
          {criteria.map((crit) => (
            <tr key={crit.id} className={!crit.is_active ? 'opacity-50 bg-slate-50' : ''}>
              {/* Форма редактирования */}
              {editingId === crit.id ? (
                <CriteriaForm
                  formData={editForm}
                  audiences={audiences}
                  isNew={false}
                  onFormChange={onFormChange}
                  onSave={onSave}
                  onCancel={onCancel}
                />
              ) : (
                <>
                  {/* Название и описание */}
                  <td className="p-4">
                    <div className="font-bold text-slate-900">{crit.title}</div>
                    <div className="text-sm text-slate-500 mt-1">{crit.description}</div>
                  </td>
                  
                  {/* Аудитория */}
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs font-bold uppercase border ${getAudienceBadgeClass(crit.target_audience)}`}>
                      {getAudienceLabel(crit.target_audience)}
                    </span>
                  </td>
                  
                  {/* Статус */}
                  <td className="p-4 text-center">
                    {crit.is_active 
                      ? <span className="text-green-600 text-xs font-bold flex justify-center items-center gap-1"><Check className="w-3 h-3"/> Активен</span> 
                      : <span className="text-slate-400 text-xs font-bold">Отключен</span>
                    }
                  </td>
                  
                  {/* Кто оценивает */}
                  <td className="p-4 text-center">
                    {renderAccessBadges(crit)}
                  </td>
                  
                  {/* Действия */}
                  <td className="p-4 text-right flex justify-end gap-2">
                    <button 
                      onClick={() => onEdit(crit)} 
                      className="p-2 text-slate-400 hover:text-blue-600 transition-colors" 
                      title="Редактировать"
                    >
                      <Edit3 className="w-5 h-5" />
                    </button>
                    
                    <button 
                      onClick={() => onDelete(crit.id)} 
                      className="p-2 text-slate-400 hover:text-red-600 transition-colors hover:bg-red-50 rounded"
                      title="Удалить навсегда"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default CriteriaTable;

