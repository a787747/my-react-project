/**
 * Welcome - Приветственная страница с инструкциями
 * 
 * Назначение: Инструкции для сотрудников о том, как работает система оценки
 * Доступ: Все авторизованные пользователи
 */

import React from 'react';
import { 
  BookOpen, 
  Users, 
  User, 
  Shield, 
  Star, 
  CheckCircle, 
  EyeOff,
  Award,
  Info,
  CheckCircle2
} from 'lucide-react';
import { LoadingSpinner, OutOfScopeNotice, CampaignNotStartedNotice, PeriodNotice, RatingGuide } from '../components/common';
import { CriteriaOverview } from '../components/profile';
import { useProfile } from '../hooks/useProfile';
import { useUser } from '../context/UserContext';
import { useTaskStatus } from '../context/TaskStatusContext';
import { buildPeriodNotice } from '../utils/periodNotice';

const Welcome = () => {
  const { user } = useUser();
  const { criteria, loading } = useProfile(user?.id);
  
  const { 
    campaignActive,
    periodInPreparation,
    periodName,
    periodStart,
    periodEnd,
    hasSelfReview, 
    hasEvaluatedManager, 
    hasEvaluatedAllSubordinates, 
    hasSubordinates, 
    hasManager, 
    isManagerCLevel,
    needsSelfReview,
    isOutOfScope,
    loading: loadingTaskStatus 
  } = useTaskStatus();

  const periodNotice = buildPeriodNotice({
    campaignActive,
    periodInPreparation,
    periodName,
    startDate: periodStart,
    endDate: periodEnd,
  });
  const showManagerTrack = Boolean(user?.has_subordinates);

  if (loading || loadingTaskStatus) {
    return <LoadingSpinner text="Загрузка инструкций..." />;
  }

  if (isOutOfScope) {
    return (
      <div className="min-h-screen bg-surface-raised p-4 lg:p-6">
        <div className="max-w-5xl mx-auto space-y-5">
          <PeriodNotice notice={periodNotice} />
          <OutOfScopeNotice embedded />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-raised p-4 lg:p-6">
      <div className="max-w-5xl mx-auto space-y-5">
        
        {/* Заголовок */}
        <div className="text-center py-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl shadow-brand mb-4">
            <BookOpen className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl md:text-3xl font-bold text-slate-900 mb-2 leading-normal">
            Добро пожаловать в систему оценки!
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Эта страница поможет вам понять, как работает система оценки производительности в нашей компании
          </p>
        </div>

        {/* Обращение к сотрудникам */}
        <div className="card p-5 border-l-4 border-l-brand-500">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-brand-100 rounded-xl flex items-center justify-center flex-shrink-0">
              <Info className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <h2 className="text-xl md:text-xl font-bold text-slate-900 mb-2 leading-normal">
                Обращение к сотрудникам
              </h2>
              <p className="text-sm text-slate-700 leading-normal mb-3">
                Система оценки производительности предназначена для объективного анализа вашей работы, 
                выявления сильных сторон и областей для развития. Мы стремимся создать прозрачную и 
                справедливую систему, которая поможет каждому сотруднику расти профессионально.
              </p>
              <p className="text-sm text-slate-700 leading-normal">
                Все данные оценок доступны только руководству компании (C-level менеджерам) для 
                обеспечения конфиденциальности и объективности процесса. Оценивается не разовое поведение сотрудника, а совокупность за период.
              </p>
            </div>
          </div>
        </div>

        <PeriodNotice notice={periodNotice} />

        {/* Блок отслеживания задач.
            Задачи существуют только когда кампания идёт: период активен И
            оценка запущена (D-0822-1). В окне подготовки — объяснение, а не
            мёртвые карточки. */}
        <div className="card p-5">
          <div className="text-center mb-4">
            <h2 className="text-lg md:text-lg font-bold text-slate-900 mb-1 leading-normal">Ваши задачи</h2>
            <p className="text-sm text-slate-500">
              {campaignActive ? 'Активный период оценки' : 'Оценка не идёт'}
            </p>
          </div>

          {!campaignActive && (
            <CampaignNotStartedNotice inPreparation={periodInPreparation} embedded />
          )}

          <div className="flex flex-wrap justify-center gap-3">
            {/* Самооценка */}
            {needsSelfReview && (
              <div className={`flex flex-col items-center p-4 rounded-xl transition-all min-w-[110px] ${
                hasSelfReview 
                  ? 'bg-success-50 border border-success-200' 
                  : 'bg-slate-50 border border-slate-200'
              }`}>
                <div className={`relative w-12 h-12 rounded-xl flex items-center justify-center mb-2 ${
                  hasSelfReview ? 'bg-success-500 shadow-success' : 'bg-slate-200'
                }`}>
                  <Star className={`w-6 h-6 ${hasSelfReview ? 'text-white' : 'text-slate-400'}`} />
                  {hasSelfReview && (
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full flex items-center justify-center shadow">
                      <CheckCircle2 className="w-3 h-3 text-success-500" />
                    </div>
                  )}
                </div>
                <span className={`text-sm font-medium ${hasSelfReview ? 'text-success-700' : 'text-slate-600'}`}>
                  Самооценка
                </span>
                {hasSelfReview && <span className="text-xs text-success-600">Выполнено</span>}
              </div>
            )}

            {/* Оценка подчиненных */}
            {hasSubordinates && (
              <div className={`flex flex-col items-center p-4 rounded-xl transition-all min-w-[110px] ${
                hasEvaluatedAllSubordinates 
                  ? 'bg-success-50 border border-success-200' 
                  : 'bg-slate-50 border border-slate-200'
              }`}>
                <div className={`relative w-12 h-12 rounded-xl flex items-center justify-center mb-2 ${
                  hasEvaluatedAllSubordinates ? 'bg-success-500 shadow-success' : 'bg-slate-200'
                }`}>
                  <Users className={`w-6 h-6 ${hasEvaluatedAllSubordinates ? 'text-white' : 'text-slate-400'}`} />
                  {hasEvaluatedAllSubordinates && (
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full flex items-center justify-center shadow">
                      <CheckCircle2 className="w-3 h-3 text-success-500" />
                    </div>
                  )}
                </div>
                <span className={`text-sm font-medium ${hasEvaluatedAllSubordinates ? 'text-success-700' : 'text-slate-600'}`}>
                  Сотрудники
                </span>
                {hasEvaluatedAllSubordinates && <span className="text-xs text-success-600">Выполнено</span>}
              </div>
            )}

            {/* Оценка руководителя */}
            {hasManager && !isManagerCLevel && (
              <div className={`flex flex-col items-center p-4 rounded-xl transition-all min-w-[110px] ${
                hasEvaluatedManager 
                  ? 'bg-success-50 border border-success-200' 
                  : 'bg-slate-50 border border-slate-200'
              }`}>
                <div className={`relative w-12 h-12 rounded-xl flex items-center justify-center mb-2 ${
                  hasEvaluatedManager ? 'bg-success-500 shadow-success' : 'bg-slate-200'
                }`}>
                  <Shield className={`w-6 h-6 ${hasEvaluatedManager ? 'text-white' : 'text-slate-400'}`} />
                  {hasEvaluatedManager && (
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full flex items-center justify-center shadow">
                      <CheckCircle2 className="w-3 h-3 text-success-500" />
                    </div>
                  )}
                </div>
                <span className={`text-sm font-medium ${hasEvaluatedManager ? 'text-success-700' : 'text-slate-600'}`}>
                  Руководитель
                </span>
                {hasEvaluatedManager && <span className="text-xs text-success-600">Выполнено</span>}
              </div>
            )}

            {/* C-level info */}
            {hasManager && isManagerCLevel && (
              <div className="flex flex-col items-center p-4 rounded-xl bg-warning-50 border border-warning-200 min-w-[110px]">
                <div className="relative w-12 h-12 rounded-xl flex items-center justify-center mb-2 bg-warning-200">
                  <Shield className="w-6 h-6 text-warning-600" />
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-warning-500 rounded-full flex items-center justify-center shadow">
                    <Info className="w-2.5 h-2.5 text-white" />
                  </div>
                </div>
                <span className="text-sm font-medium text-warning-700">Руководитель</span>
                <span className="text-xs text-warning-600">C-level</span>
              </div>
            )}
          </div>

          {hasManager && isManagerCLevel && (
            <div className="mt-3 p-2 bg-warning-50 border border-warning-200 rounded-lg text-center">
              <p className="text-xs text-warning-700">C-level менеджеры не оцениваются подчиненными</p>
            </div>
          )}
        </div>

        {/* Процесс оценки - для менеджеров с подчиненными */}
        {showManagerTrack ? (
          <div className="card p-5">
            <div className="flex items-start gap-3 mb-5">
              <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-xl md:text-xl font-bold text-slate-900 mb-1 leading-normal">
                  Процесс оценки (для менеджеров с подчиненными)
                </h2>
                <p className="text-slate-600 text-sm leading-normal">
                  Если у вас есть подчиненные, процесс оценки включает дополнительные этапы
                </p>
              </div>
            </div>

            <div className="mb-5">
              <RatingGuide variant="full" />
            </div>

            <div className="space-y-4">
              {/* Шаг 1 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">1</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Star className="w-4 h-4 text-warning-500" />
                    Самооценка и оценка вашего менеджера
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal mb-2">
                    Внимательно прочитайте критерии оценок. Сначала вы выполняете самооценку по установленным критериям. Затем вы оцениваете своего руководителя.
                  </p>
                  <div className="bg-warning-50 border border-warning-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-warning-900 mb-1 leading-normal">Важно: Анонимность оценки вами своего менеджера</p>
                        <p className="text-sm text-warning-800 leading-normal">
                          Оценка вашего менеджера остается <strong>анонимной</strong> - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Шаг 2 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-purple-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">2</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Users className="w-4 h-4 text-purple-500" />
                    Оценка качества управления от подчиненных
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal mb-2">
                    Ваши подчиненные оценивают вас по критериям качества управления. Эта оценка также остается анонимной для вас.
                  </p>
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-2">
                    <div className="flex items-start gap-2">
                      <Shield className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-purple-800 leading-normal">
                        Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.
                      </p>
                    </div>
                  </div>
                  <div className="bg-brand-50 border border-brand-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <Award className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-brand-900 mb-1 leading-normal">Качество управления и развитие команды</p>
                        <p className="text-sm text-brand-800 leading-normal">
                          Руководители (сотрудники, у которых есть прямые подчиненные) также будут оценены по критерию «Качество управления и развитие команды». Оценка проводится каждым сотрудником отдела и непосредственным руководителем оцениваемого менеджера.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Шаг 3 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-success-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">3</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <User className="w-4 h-4 text-success-500" />
                    Оценка ваших подчиненных
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal mb-2">
                    Вы оцениваете своих подчиненных по установленным критериям. Оценка вашего менеджера остается для вас недоступна, чтобы избежать искажения.
                  </p>
                  <div className="bg-info-50 border border-info-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-info-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-info-800 leading-normal">
                        Оценка вашего менеджера недоступна вам, чтобы обеспечить независимость и объективность ваших оценок подчиненных.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Шаг 4 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">4</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Shield className="w-4 h-4 text-brand-500" />
                    Оценка старшего менеджера (опционально)
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal">
                    Старший менеджер может поставить вам свою оценку. В этом случае оценки вашего менеджера и старшего менеджера усредняются для получения финального результата.
                  </p>
                </div>
              </div>

              {/* Шаг 5 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-warning-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">5</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Shield className="w-4 h-4 text-warning-500" />
                    Оценка C-level менеджеров
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal">
                    C-level менеджеры оценивают вас по специальным критериям, доступным только для руководства компании.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Процесс оценки - для сотрудников без подчиненных */
          <div className="card p-5">
            <div className="flex items-start gap-3 mb-5">
              <div className="w-10 h-10 bg-success-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-success-600" />
              </div>
              <div>
                <h2 className="text-xl md:text-xl font-bold text-slate-900 mb-1 leading-normal">
                  Процесс оценки (для сотрудников без подчиненных)
                </h2>
                <p className="text-slate-600 text-sm leading-normal">
                  Процесс оценки для обычных сотрудников включает следующие этапы
                </p>
              </div>
            </div>

            <div className="mb-5">
              <RatingGuide variant="employee" />
            </div>

            <div className="space-y-4">
              {/* Шаг 1 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">1</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Star className="w-4 h-4 text-warning-500" />
                    Самооценка и оценка вашего менеджера
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal mb-2">
                    Внимательно прочитайте критерии оценок. Сначала вы выполняете самооценку по установленным критериям. Затем вы оцениваете своего руководителя.
                  </p>
                  <div className="bg-warning-50 border border-warning-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-warning-900 mb-1 leading-normal">Важно: Анонимность оценки вами своего менеджера</p>
                        <p className="text-sm text-warning-800 leading-normal">
                          Оценка вашего менеджера остается <strong>анонимной</strong> - он не видит конкретные баллы и комментарии, чтобы избежать искажения оценок и обеспечить объективность процесса. Все данные видят только C-level менеджеры.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Шаг 2 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-success-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">2</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <User className="w-4 h-4 text-success-500" />
                    Оценка вашего менеджера
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal mb-2">
                    Ваш менеджер оценивает вас по установленным критериям. Оценка вашего менеджера остается для вас недоступна, чтобы избежать искажения.
                  </p>
                  <div className="bg-info-50 border border-info-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-info-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-info-800 leading-normal">
                        Оценка вашего менеджера недоступна вам, чтобы обеспечить независимость и объективность процесса оценки.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Шаг 3 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">3</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Shield className="w-4 h-4 text-brand-500" />
                    Оценка старшего менеджера (опционально)
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal">
                    Старший менеджер может поставить вам свою оценку. В этом случае оценки вашего менеджера и старшего менеджера усредняются для получения финального результата.
                  </p>
                </div>
              </div>

              {/* Шаг 4 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-warning-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">4</div>
                <div className="flex-1">
                  <h3 className="text-base md:text-base font-semibold text-slate-900 mb-1 leading-normal flex items-center gap-2">
                    <Shield className="w-4 h-4 text-warning-500" />
                    Оценка C-level менеджеров
                  </h3>
                  <p className="text-sm text-slate-700 leading-normal">
                    C-level менеджеры оценивают вас по специальным критериям, доступным только для руководства компании.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Дополнительные критерии */}
        <div className="card p-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-brand-100 rounded-xl flex items-center justify-center flex-shrink-0">
              <Award className="w-5 h-5 text-brand-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl md:text-xl font-bold text-slate-900 mb-2 leading-normal">Дополнительные критерии</h2>
              <p className="text-sm text-slate-700 leading-normal mb-3">
                Эти два критерия учитываются у сотрудников, чей вклад в проектную деятельность не ограничивался рутинной работой.
              </p>
              <div className="space-y-3">
                <div className="bg-brand-50 border border-brand-200 rounded-lg p-3">
                  <p className="text-base font-semibold text-brand-900 mb-1 leading-normal">Взаимодействие и надежность в проекте</p>
                  <p className="text-sm text-brand-800 leading-normal">
                    Оценка работы в проектных командах (в т.ч. на объектах). Оценивается вклад в общий результат, а не только выполнение своей функции. Ключевые факторы: взаимовыручка (например, помочь на монтаже), предвосхищение проблем, предложение решений, качественная передача информации смежникам и конструктивное поведение в стрессовых условиях (командировки, стройка). Оцениваются только участники проектов.
                  </p>
                </div>
                <div className="bg-brand-50 border border-brand-200 rounded-lg p-3">
                  <p className="text-base font-semibold text-brand-900 mb-1 leading-normal">Объем проектной работы и загрузка</p>
                  <p className="text-sm text-brand-800 leading-normal">
                    Количественная оценка вклада. Учитывает фактический объем выполненных задач и долю рабочего времени, занятую проектом (в том числе время на объектах). Позволяет дифференцировать сотрудников с полной проектной загрузкой (в том числе длительные командировки) от консультантов и временных участников.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Критерии оценки */}
        <div className="card p-5">
          <CriteriaOverview criteria={criteria} user={user} />
        </div>

        {/* Заключение */}
        <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-2xl p-6 text-white text-center">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-90" />
          <h2 className="text-xl md:text-xl font-bold mb-2 leading-normal">Готовы начать?</h2>
          <p className="text-brand-100 max-w-2xl mx-auto">
            Перейдите в раздел "Самооценка" для начала процесса оценки или в "Мой Профиль" 
            для просмотра ваших текущих результатов.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Welcome;
