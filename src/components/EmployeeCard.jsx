/**
 * EmployeeCard - Карточка сотрудника на дашборде
 * 
 * Назначение: Отображение информации о сотруднике с кнопкой оценки/редактирования
 * Используется в: Dashboard
 * 
 * Props:
 * - employee: object - данные сотрудника
 * - isEvaluated: boolean - оценен ли сотрудник (вами)
 * - lastScore: number - последний балл (ваша оценка)
 * - hasSelfReview: boolean - прошёл ли сотрудник самооценку
 * - selfReviewScore: number - балл самооценки
 * - hasEvaluatedManager: boolean - оценил ли сотрудник своего руководителя
 * - criteriaCounts: object - количество критериев по категориям {general, project, cLevel, total}
 * - showCLevel: boolean - показывать ли C-level критерии (для admin/c_level)
 * - onEvaluate: function(employee) - начать оценку
 * - onEdit: function(employee) - редактировать оценку
 * 
 * Accessibility:
 * - Семантическая разметка с article
 * - ARIA-labels для интерактивных элементов
 * - Focus-visible стили
 * - Достаточный цветовой контраст
 */

import React, { memo } from 'react';
import { Briefcase, Award, ChevronRight, Star, CheckCircle, Edit, UserCheck, XCircle, ClipboardList } from 'lucide-react';

const EmployeeCard = memo(({ employee, isEvaluated, lastScore, hasSelfReview, hasEvaluatedManager, criteriaCounts, showCLevel, onEvaluate, onEdit }) => {
  const displayName = employee.full_name || 'Неизвестный сотрудник';
  const initial = displayName.charAt(0).toUpperCase();
  
  return (
    <article 
      className="card-interactive p-6 flex flex-col"
      aria-labelledby={`employee-${employee.id}-name`}
    >
      {/* Header с аватаром и статусами */}
      <header className="flex items-start justify-between mb-4">
        {/* Аватар */}
        <div 
          className="w-14 h-14 bg-gradient-to-br from-brand-500 to-purple-600 rounded-2xl flex items-center justify-center text-white font-bold text-xl shadow-brand"
          role="img"
          aria-label={`Аватар ${displayName}`}
        >
          {initial}
        </div>
        
        {/* Статусы */}
        <div className="flex flex-col items-end gap-1.5">
          {/* Самооценка */}
          {hasSelfReview ? (
            <span 
              className="badge badge-success flex items-center gap-1"
              role="status"
              aria-label="Самооценка пройдена"
            >
              <CheckCircle className="w-3 h-3" aria-hidden="true" />
              <span>Самооценка ✓</span>
            </span>
          ) : (
            <span 
              className="badge bg-slate-100 text-slate-500 flex items-center gap-1"
              role="status"
              aria-label="Самооценка не пройдена"
            >
              <XCircle className="w-3 h-3" aria-hidden="true" />
              <span>Самооценка</span>
            </span>
          )}
          
          {/* Оценил руководителя */}
          {hasEvaluatedManager ? (
            <span 
              className="badge badge-info flex items-center gap-1"
              role="status"
              aria-label="Оценил руководителя"
            >
              <UserCheck className="w-3 h-3" aria-hidden="true" />
              <span>Оценил рук-ля ✓</span>
            </span>
          ) : (
            <span 
              className="badge bg-slate-100 text-slate-500 flex items-center gap-1"
              role="status"
              aria-label="Не оценил руководителя"
            >
              <UserCheck className="w-3 h-3" aria-hidden="true" />
              <span>Оценка рук-ля</span>
            </span>
          )}
          
          {/* Оценен вами */}
          {isEvaluated && (
            <div className="flex flex-col items-end gap-1 mt-1">
              <span 
                className="badge bg-purple-100 text-purple-700 flex items-center gap-1"
                role="status"
                aria-label="Сотрудник оценен вами"
              >
                <Star className="w-3 h-3" aria-hidden="true" />
                <span>Оценен вами</span>
              </span>
              {lastScore && (
                <span className="text-xs text-slate-600">
                  Балл: <span className="font-bold text-purple-600">{parseFloat(lastScore).toFixed(1)}</span>
                </span>
              )}
            </div>
          )}
        </div>
      </header>
      
      {/* Информация о сотруднике */}
      <div className="flex-1">
        <h3 
          id={`employee-${employee.id}-name`}
          className="text-lg font-semibold text-slate-900"
        >
          {displayName}
        </h3>
        <p className="text-slate-500 text-sm mb-4">{employee.job_title || 'Должность не указана'}</p>
        
        <dl className="space-y-2 mb-4">
          <div className="flex items-center text-sm text-slate-600">
            <dt className="sr-only">Отдел</dt>
            <Briefcase className="w-4 h-4 mr-2 text-slate-400" aria-hidden="true" />
            <dd>{employee.department_name || 'Отдел не указан'}</dd>
          </div>
          <div className="flex items-center text-sm text-slate-600">
            <dt className="sr-only">Грейд</dt>
            <Award className="w-4 h-4 mr-2 text-slate-400" aria-hidden="true" />
            <dd>Grade: {employee.grade_code || 'N/A'}</dd>
          </div>
        </dl>
        
        {/* Критерии оценки */}
        {criteriaCounts && (
          <div className="mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-600">
              <ClipboardList className="w-3.5 h-3.5" />
              <span>Критерии оценки:</span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {/* Общие критерии */}
              <span className={`px-2 py-1 rounded-full ${isEvaluated ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                Общие: {criteriaCounts.general} {isEvaluated && '✓'}
              </span>
              
              {/* Проектные критерии (только если есть) */}
              {criteriaCounts.project > 0 && (
                <span className={`px-2 py-1 rounded-full ${isEvaluated ? 'bg-green-100 text-green-700' : 'bg-purple-100 text-purple-700'}`}>
                  Проект: {criteriaCounts.project} {isEvaluated && '✓'}
                </span>
              )}
              
              {/* Критерии руководства (только для руководителей с подчинёнными) */}
              {criteriaCounts.management > 0 && (
                <span className={`px-2 py-1 rounded-full ${isEvaluated ? 'bg-green-100 text-green-700' : 'bg-indigo-100 text-indigo-700'}`}>
                  Руководство: {criteriaCounts.management} {isEvaluated && '✓'}
                </span>
              )}
              
              {/* C-level критерии (всегда показываем если есть) */}
              {criteriaCounts.cLevel > 0 && (
                <span className={`px-2 py-1 rounded-full ${
                  showCLevel && isEvaluated 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-orange-100 text-orange-700'
                }`}>
                  C-level: {criteriaCounts.cLevel} {showCLevel && isEvaluated && '✓'}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Кнопка действия */}
      <button 
        onClick={() => isEvaluated ? onEdit(employee) : onEvaluate(employee)}
        className={`
          w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl 
          font-semibold text-sm transition-all duration-200
          focus-visible:ring-2 focus-visible:ring-offset-2 active:scale-[0.98]
          ${isEvaluated 
            ? 'bg-success-600 hover:bg-success-700 text-white shadow-success focus-visible:ring-success-500' 
            : 'bg-brand-600 hover:bg-brand-700 text-white shadow-brand focus-visible:ring-brand-500'
          }
        `}
        aria-label={isEvaluated 
          ? `Редактировать оценку для ${displayName}` 
          : `Оценить сотрудника ${displayName}`
        }
      >
        {isEvaluated ? (
          <>
            <Edit className="w-4 h-4" aria-hidden="true" />
            <span>Редактировать</span>
          </>
        ) : (
          <>
            <Star className="w-4 h-4" aria-hidden="true" />
            <span>Оценить</span>
          </>
        )}
        <ChevronRight className="w-4 h-4" aria-hidden="true" />
      </button>
    </article>
  );
});

// Для React DevTools
EmployeeCard.displayName = 'EmployeeCard';

export default EmployeeCard;
