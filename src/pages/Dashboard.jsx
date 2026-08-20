/**
 * Dashboard - Главная страница (дашборд)
 * 
 * Назначение: Отображение списка подчиненных для оценки
 * Доступ: manager, admin, c_level
 * 
 * Функционал:
 * - Список сотрудников с карточками
 * - Модальное окно для проведения оценки
 * - Отображение статусов самооценок и оценок менеджера
 */

import React, { useState, useCallback } from 'react';
import apiClient from '../api/client';
import { User } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import { useTaskStatus } from '../context/TaskStatusContext';
import EmployeeCard from '../components/EmployeeCard';
import EvaluationModal from '../components/EvaluationModal';
import { Skeleton } from '../components/common';
import { API_ENDPOINTS } from '../config/api';
import { ADMIN_ROLES } from '../config/constants';
import logger from '../utils/logger';

const Dashboard = ({ user }) => {
  // Контекст статусов задач для обновления сайдбара
  const { refreshTaskStatus } = useTaskStatus();
  const {
    employees,
    criteria,
    evaluatedDetails,
    campaignActive,
    loading,
    setEvaluatedDetails
  } = useDashboardData(user);

  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);

  // Мемоизированные колбэки для предотвращения ненужных ре-рендеров EmployeeCard
  const handleOpenEvaluation = useCallback((employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(false);
    setIsModalOpen(true);
  }, []);

  const handleOpenEdit = useCallback((employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(true);
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
  }, []);

  const handleEvaluationSuccess = useCallback(async () => {
    try {
      const evaluatedRes = await apiClient.get(API_ENDPOINTS.CHECK_EVALUATED, {
        params: { evaluator_id: user.id }
      });
      const evaluatedData = evaluatedRes.data.details || [];
      const evaluatedMap = {};
      evaluatedData.forEach(item => {
        evaluatedMap[item.subject_id] = {
          latest_evaluation_id: item.latest_evaluation_id,
          last_score: item.last_score
        };
      });
      setEvaluatedDetails(evaluatedMap);
      
      // Обновляем статусы задач в сайдбаре
      refreshTaskStatus();
    } catch (error) {
      logger.error('Ошибка обновления данных:', error);
    }
  }, [user.id, setEvaluatedDetails, refreshTaskStatus]);

  // Функция для подсчёта критериев по категориям для сотрудника
  const getCriteriaCounts = useCallback((employee) => {
    // Фильтруем критерии для данного сотрудника (без учёта роли для подсчёта)
    const activeCriteria = criteria.filter(c => c.is_active === true || c.is_active === 'true');
    
    // Группируем критерии
    const generalCriteria = activeCriteria.filter(c => 
      !c.c_level_only && 
      c.target_audience !== 'project_participants' && 
      c.target_audience !== 'managers_only' &&
      c.for_manager // только критерии для оценки менеджером
    );
    
    // Проектные критерии (только для участников проектов)
    const projectCriteria = employee.is_project_participant 
      ? activeCriteria.filter(c => 
          !c.c_level_only && 
          c.target_audience === 'project_participants'
        )
      : [];
    
    // C-level критерии (всегда считаем для отображения)
    const cLevelCriteria = activeCriteria.filter(c => c.c_level_only);
    
    // Критерии руководства (только для сотрудников с подчинёнными - managers_only)
    const managementCriteria = employee.has_subordinates
      ? activeCriteria.filter(c => 
          !c.c_level_only && 
          c.target_audience === 'managers_only'
        )
      : [];
    
    return {
      general: generalCriteria.length,
      project: projectCriteria.length,
      cLevel: cLevelCriteria.length,
      management: managementCriteria.length,
      total: generalCriteria.length + projectCriteria.length + cLevelCriteria.length + managementCriteria.length
    };
  }, [criteria]);

  const processedSubordinates = employees
    .filter(emp => emp.id !== user.id)
    .map(emp => {
      const criteriaCounts = getCriteriaCounts(emp);
      return {
        ...emp,
        isEvaluated: emp.evaluated_by_actor === true || !!evaluatedDetails[emp.id],
        lastScore: evaluatedDetails[emp.id]?.last_score,
        hasSelfReview: emp.has_self_review === true,
        hasEvaluatedManager: emp.has_evaluated_manager === true,
        criteriaCounts,
        showCLevel: ADMIN_ROLES.includes(user.role)
      };
    });

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-raised p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <Skeleton.Title width="w-48" className="mb-3" />
            <Skeleton.Text width="w-64" />
          </div>
          <Skeleton.EmployeeGrid count={6} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-raised p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Моя команда</h1>
          <p className="text-slate-600">Сотрудники в вашем подчинении</p>
        </div>

        {processedSubordinates.length === 0 ? (
          <div className="card p-12 text-center">
            <User className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-2">
              {campaignActive ? 'Нет сотрудников в этой кампании' : 'Кампания ещё не открыта'}
            </h3>
            <p className="text-slate-600">
              {campaignActive
                ? 'В активном периоде нет подчинённых в охвате оценки.'
                : 'Список для оценки появится, когда HR откроет период.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {processedSubordinates.map((emp) => (
              <EmployeeCard
                key={emp.id}
                employee={emp}
                isEvaluated={emp.isEvaluated}
                lastScore={emp.lastScore}
                hasSelfReview={emp.hasSelfReview}
                hasEvaluatedManager={emp.hasEvaluatedManager}
                criteriaCounts={emp.criteriaCounts}
                showCLevel={emp.showCLevel}
                onEvaluate={handleOpenEvaluation}
                onEdit={handleOpenEdit}
              />
            ))}
          </div>
        )}
      </div>

      <EvaluationModal
        isOpen={isModalOpen}
        employee={selectedEmployee}
        criteria={criteria}
        isEditMode={isEditMode}
        evaluatedDetails={evaluatedDetails}
        user={user}
        onClose={handleCloseModal}
        onSuccess={handleEvaluationSuccess}
      />
    </div>
  );
};

export default Dashboard;