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
import { User } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import { useTaskStatus } from '../context/TaskStatusContext';
import EmployeeCard from '../components/EmployeeCard';
import OutOfScopeTeamSection from '../components/common/OutOfScopeTeamSection';
import EvaluationModal from '../components/EvaluationModal';
import { Skeleton } from '../components/common';
import { ADMIN_ROLES } from '../config/constants';
import logger from '../utils/logger';

const Dashboard = ({ user }) => {
  // Контекст статусов задач для обновления сайдбара
  const { refreshTaskStatus } = useTaskStatus();
  const {
    employees,
    outOfScopeEmployees,
    criteria,
    evaluatedDetails,
    campaignActive,
    loading,
    refetch
  } = useDashboardData(user);

  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [additiveCriteriaIds, setAdditiveCriteriaIds] = useState(null);

  // Мемоизированные колбэки для предотвращения ненужных ре-рендеров EmployeeCard
  const handleOpenEvaluation = useCallback((employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(false);
    setAdditiveCriteriaIds(null);
    setIsModalOpen(true);
  }, []);

  const handleOpenEdit = useCallback((employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(true);
    setAdditiveCriteriaIds(null);
    setIsModalOpen(true);
  }, []);

  // Дооценка: оценка уже существует, но после смены классификации появились
  // новые применимые критерии. Форма покажет ТОЛЬКО недостающие; сервер
  // добавит их к существующей оценке (additive path, D-0822-3).
  const handleOpenAdditive = useCallback((employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(false);
    setAdditiveCriteriaIds(
      Array.isArray(employee.missing_criteria_ids) ? employee.missing_criteria_ids : []
    );
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
    setAdditiveCriteriaIds(null);
  }, []);

  const handleEvaluationSuccess = useCallback(async () => {
    try {
      // Флаг evaluated_by_actor и missing_criteria_ids живут на строках
      // /api/employees — перечитываем их, а не только check-evaluated.
      await refetch();
      // Обновляем статусы задач в сайдбаре
      refreshTaskStatus();
    } catch (error) {
      logger.error('Ошибка обновления данных:', error);
    }
  }, [refetch, refreshTaskStatus]);

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

  const criteriaTitleById = (id) => criteria.find(c => Number(c.id) === Number(id))?.title || `Критерий ${id}`;

  const processedSubordinates = employees
    .filter(emp => emp.id !== user.id)
    .map(emp => {
      const criteriaCounts = getCriteriaCounts(emp);
      // evaluated_by_actor стал по-критериальным (D-0822-3): true только когда
      // оценка существует И покрывает все применимые сейчас критерии. Наличие
      // строки в check-evaluated больше не означает «оценен».
      const isEvaluated = emp.evaluated_by_actor === true;
      const hasExistingEvaluation = !!evaluatedDetails[emp.id];
      const missingIds = Array.isArray(emp.missing_criteria_ids) ? emp.missing_criteria_ids : [];
      return {
        ...emp,
        isEvaluated,
        hasExistingEvaluation,
        needsAdditional: hasExistingEvaluation && !isEvaluated && missingIds.length > 0,
        missingCriteriaTitles: missingIds.map(criteriaTitleById),
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
                needsAdditional={emp.needsAdditional}
                missingCriteriaTitles={emp.missingCriteriaTitles}
                lastScore={emp.lastScore}
                hasSelfReview={emp.hasSelfReview}
                hasEvaluatedManager={emp.hasEvaluatedManager}
                criteriaCounts={emp.criteriaCounts}
                showCLevel={emp.showCLevel}
                onEvaluate={handleOpenEvaluation}
                onEdit={handleOpenEdit}
                onEvaluateMissing={handleOpenAdditive}
              />
            ))}
          </div>
        )}

        {/* D-0825-11: работающие подчинённые вне охвата этого периода.
            Отдельным блоком под карточками: это не задачи, кнопки «Оценить»
            у них нет, и ни один счётчик выше их не считает. Уволенные сюда не
            попадают — увольнение остаётся исчезновением (D-0825-7). */}
        <OutOfScopeTeamSection employees={outOfScopeEmployees} className="mt-6" />
      </div>

      <EvaluationModal
        isOpen={isModalOpen}
        employee={selectedEmployee}
        criteria={criteria}
        isEditMode={isEditMode}
        additiveCriteriaIds={additiveCriteriaIds}
        evaluatedDetails={evaluatedDetails}
        user={user}
        onClose={handleCloseModal}
        onSuccess={handleEvaluationSuccess}
      />
    </div>
  );
};

export default Dashboard;