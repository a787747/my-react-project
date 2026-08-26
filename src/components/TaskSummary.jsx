import React from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Info, Shield, Star, Users } from 'lucide-react';
import CampaignNotStartedNotice from './common/CampaignNotStartedNotice';

const TASKS = {
  self: {
    label: 'Самооценка',
    to: '/self-review',
    icon: Star,
  },
  subordinates: {
    label: 'Сотрудники',
    to: '/dashboard',
    icon: Users,
  },
  manager: {
    label: 'Руководитель',
    to: '/manager-evaluation',
    icon: Shield,
  },
};

const TaskLink = ({ task, done }) => {
  const Icon = task.icon;

  return (
    <Link
      to={task.to}
      aria-label={`${task.label}: ${done ? 'выполнено' : 'перейти к задаче'}`}
      className={`flex flex-col items-center p-4 rounded-xl transition-all min-w-[110px] focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
        done
          ? 'bg-success-50 border border-success-200 hover:bg-success-100'
          : 'bg-slate-50 border border-slate-200 hover:bg-brand-50 hover:border-brand-300'
      }`}
    >
      <div className={`relative w-12 h-12 rounded-xl flex items-center justify-center mb-2 ${
        done ? 'bg-success-500 shadow-success' : 'bg-slate-200'
      }`}>
        <Icon className={`w-6 h-6 ${done ? 'text-white' : 'text-slate-500'}`} />
        {done && (
          <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full flex items-center justify-center shadow">
            <CheckCircle2 className="w-3 h-3 text-success-500" />
          </div>
        )}
      </div>
      <span className={`text-sm font-medium ${done ? 'text-success-700' : 'text-slate-700'}`}>
        {task.label}
      </span>
      <span className={`text-xs ${done ? 'text-success-600' : 'text-brand-600'}`}>
        {done ? 'Выполнено' : 'Открыть'}
      </span>
    </Link>
  );
};

const TaskSummary = ({
  campaignActive,
  periodInPreparation,
  needsSelfReview,
  hasSelfReview,
  hasSubordinates,
  hasEvaluatedAllSubordinates,
  hasManager,
  isManagerCLevel,
  hasEvaluatedManager,
  isOutOfScope = false,
}) => (
  <div className="card p-5" data-testid="task-summary">
    <div className="text-center mb-4">
      <h2 className="text-lg md:text-lg font-bold text-slate-900 mb-1 leading-normal">Ваши задачи</h2>
      <p className="text-sm text-slate-500">
        {campaignActive ? 'Активный период оценки' : 'Оценка не идёт'}
      </p>
    </div>

    {!campaignActive && (
      <CampaignNotStartedNotice inPreparation={periodInPreparation} embedded />
    )}

    {campaignActive && isOutOfScope && (
      <p className="text-sm text-slate-600 text-center">
        Задач нет: вы не участвуете в текущем периоде оценки.
      </p>
    )}

    {campaignActive && !isOutOfScope && (
      <div className="flex flex-wrap justify-center gap-3">
        {needsSelfReview && <TaskLink task={TASKS.self} done={hasSelfReview} />}
        {hasSubordinates && (
          <TaskLink task={TASKS.subordinates} done={hasEvaluatedAllSubordinates} />
        )}
        {hasManager && !isManagerCLevel && (
          <TaskLink task={TASKS.manager} done={hasEvaluatedManager} />
        )}
      </div>
    )}

    {campaignActive && !isOutOfScope && hasManager && isManagerCLevel && (
      <div className="mt-3 p-2 bg-warning-50 border border-warning-200 rounded-lg text-center">
        <p className="text-xs text-warning-700 flex items-center justify-center gap-1.5">
          <Info className="w-3.5 h-3.5" />
          C-level менеджеры не оцениваются подчиненными
        </p>
      </div>
    )}
  </div>
);

export default TaskSummary;
