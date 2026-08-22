/**
 * AdminSettings - Страница управления критериями оценки
 * 
 * Назначение: Просмотр, создание, редактирование и удаление критериев оценки
 * Доступ: admin, c_level
 * 
 * Использует компоненты:
 * - CriteriaTable - таблица критериев
 * - LoadingSpinner - индикатор загрузки
 * 
 * Использует хуки:
 * - useCriteria - загрузка и управление критериями
 */

import React, { useState } from 'react';
import { ListPlus, Plus, User, Users, Shield, Trash2 } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

// Компоненты
import { LoadingSpinner, Toast, PeriodBanner } from '../components/common';
import CriteriaTable from '../components/admin/CriteriaTable';
import ClearTestEvaluationsModal from '../components/admin/ClearTestEvaluationsModal';

// Хуки
import { useCriteria } from '../hooks/useCriteria';

// Константы
import { TARGET_AUDIENCES } from '../config/constants';

// Начальное состояние формы для нового критерия
const getInitialFormState = (criterion = null) => {
  if (criterion) {
    return {
      ...criterion,
      level_0_desc: criterion.level_0_desc || '',
      level_1_desc: criterion.level_1_desc || '',
      level_2_desc: criterion.level_2_desc || '',
      level_3_desc: criterion.level_3_desc || '',
      level_4_desc: criterion.level_4_desc || '',
      level_5_desc: criterion.level_5_desc || '',
      level_6_desc: criterion.level_6_desc || '',
      level_7_desc: criterion.level_7_desc || '',
      level_8_desc: criterion.level_8_desc || '',
      level_9_desc: criterion.level_9_desc || '',
      level_10_desc: criterion.level_10_desc || '',
      selfassesment: criterion.selfassesment !== undefined ? criterion.selfassesment : true,
      for_manager: criterion.for_manager !== undefined ? criterion.for_manager : true,
      c_level_only: criterion.c_level_only !== undefined ? criterion.c_level_only : false
    };
  }
  
  return {
    title: '',
    description: '',
    target_audience: 'all',
    is_active: true,
    selfassesment: true,
    for_manager: true,
    c_level_only: false,
    level_0_desc: '',
    level_1_desc: '',
    level_2_desc: '',
    level_3_desc: '',
    level_4_desc: '',
    level_5_desc: '',
    level_6_desc: '',
    level_7_desc: '',
    level_8_desc: '',
    level_9_desc: '',
    level_10_desc: ''
  };
};

const AdminSettings = () => {
  // Хук для работы с критериями
  const { criteriaList, period, campaignActive, evaluationStarted, loading, saveCriterion, deleteCriterion } = useCriteria();
  
  // Состояние редактирования
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  
  // Состояние для очистки тестовых оценок
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [toast, setToast] = useState(null);

  // Начать редактирование критерия
  const handleEdit = (criterion) => {
    setEditingId(criterion.id);
    setEditForm(getInitialFormState(criterion));
  };

  // Добавить новый критерий
  const handleAddNew = () => {
    setEditingId('new');
    setEditForm(getInitialFormState());
  };

  // Сохранить критерий
  const handleSave = async () => {
    const result = await saveCriterion(editForm);
    if (result.success) {
      setEditingId(null);
    } else {
      alert(result.error);
    }
  };

  // Отменить редактирование
  const handleCancel = () => {
    setEditingId(null);
  };

  // Удалить критерий
  const handleDelete = async (id) => {
    if (!window.confirm("Вы уверены, что хотите удалить этот критерий? Это действие нельзя отменить.")) {
      return;
    }
    
    const result = await deleteCriterion(id);
    if (!result.success) {
      alert(result.error);
    }
  };

  // Очистить тестовые оценки
  const handleClearTestEvaluations = async () => {
    try {
      setIsClearing(true);
      const response = await apiClient.post(API_ENDPOINTS.ADMIN_CLEAR_TEST_EVALUATIONS);
      
      if (response.data?.success || response.status === 200) {
        setToast({
          type: 'success',
          message: 'Тестовые оценки успешно удалены'
        });
        setIsClearModalOpen(false);
      } else {
        throw new Error(response.data?.message || 'Ошибка при удалении оценок');
      }
    } catch (error) {
      logger.error('Ошибка очистки тестовых оценок:', error);
      setToast({
        type: 'error',
        message: error.userMessage || error.message || 'Не удалось удалить тестовые оценки'
      });
    } finally {
      setIsClearing(false);
    }
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка критериев..." />;
  }

  return (
    <div className="max-w-6xl mx-auto p-8 pb-20">
      {/* Header */}
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <ListPlus className="text-blue-600 w-8 h-8" />
            Критерии Оценки
          </h1>
          <p className="text-slate-500 mt-2">Добавляйте вопросы и назначайте их отделам.</p>
        </div>
        <button 
          onClick={handleAddNew}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" /> Добавить критерий
        </button>
      </div>

      <PeriodBanner
        period={period}
        campaignActive={campaignActive}
        emptyCopy="Нет активного периода — каталог можно менять."
        draftName={null}
      />
      {/* Каталог замораживается на СТАРТЕ оценки, не на активации (D-0822-1):
          в окне подготовки критерии ещё можно править. */}
      {evaluationStarted ? (
        <div className="mb-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-900 text-sm">
          Сохранение и удаление критериев заморожены: оценка в текущем периоде уже идёт (409).
        </div>
      ) : campaignActive && (
        <div className="mb-4 p-3 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-900 text-sm">
          Период активен, но оценка ещё не запущена — каталог можно менять. После запуска оценки правки будут заблокированы.
        </div>
      )}

      {/* Легенда */}
      <div className="mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
        <span className="text-xs font-bold text-slate-500 mr-4">Кто оценивает:</span>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-700 mr-2">
          <User className="w-3 h-3" /> Само — Самооценка
        </span>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-700 mr-2">
          <Users className="w-3 h-3" /> Мен — Менеджер
        </span>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-700">
          <Shield className="w-3 h-3" /> C-lvl — C-level / Admin
        </span>
      </div>

      {/* Кнопка очистки тестовых оценок */}
      <div className="mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Очистка тестовых данных</h3>
              <p className="text-sm text-gray-600">
                Удалить все тестовые оценки всех сотрудников
              </p>
            </div>
            <button
              onClick={() => setIsClearModalOpen(true)}
              disabled={isClearing}
              className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
            >
              <Trash2 className="w-5 h-5" />
              {isClearing ? 'Удаление...' : 'Очистить тестовые оценки'}
            </button>
          </div>
        </div>
      </div>

      {/* Таблица критериев */}
      <CriteriaTable
        criteria={criteriaList}
        audiences={TARGET_AUDIENCES}
        editingId={editingId}
        editForm={editForm}
        onEdit={handleEdit}
        onFormChange={setEditForm}
        onSave={handleSave}
        onCancel={handleCancel}
        onDelete={handleDelete}
      />

      {/* Модальное окно очистки тестовых оценок */}
      <ClearTestEvaluationsModal
        isOpen={isClearModalOpen && !isClearing}
        onConfirm={handleClearTestEvaluations}
        onCancel={() => !isClearing && setIsClearModalOpen(false)}
      />

      {/* Уведомления */}
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
};

export default AdminSettings;
