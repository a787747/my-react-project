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
import { LoadingSpinner, OutOfScopeNotice } from '../components/common';
import { CriteriaOverview } from '../components/profile';
import { useProfile } from '../hooks/useProfile';
import { useUser } from '../context/UserContext';
import { useTaskStatus } from '../context/TaskStatusContext';

const Welcome = () => {
  const { user } = useUser();
  const { criteria, loading } = useProfile(user?.id);
  
  const { 
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

  if (loading || loadingTaskStatus) {
    return <LoadingSpinner text="Загрузка инструкций..." />;
  }

  if (isOutOfScope) {
    return <OutOfScopeNotice />;
  }

  return (
    <div className="min-h-screen bg-surface-raised p-4 lg:p-6">
      <div className="max-w-5xl mx-auto space-y-5">
        
        {/* Заголовок */}
        <div className="text-center py-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl shadow-brand mb-4">
            <BookOpen className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
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
              <h2 className="text-xl font-bold text-slate-900 mb-2">
                Обращение к сотрудникам
              </h2>
              <p className="text-slate-700 leading-relaxed mb-3">
                Система оценки производительности предназначена для объективного анализа вашей работы, 
                выявления сильных сторон и областей для развития. Мы стремимся создать прозрачную и 
                справедливую систему, которая поможет каждому сотруднику расти профессионально.
              </p>
              <p className="text-slate-700 leading-relaxed">
                Все данные оценок доступны только руководству компании (C-level менеджерам) для 
                обеспечения конфиденциальности и объективности процесса. Оценивается не разовое поведение сотрудника, а совокупность за период.
              </p>
            </div>
          </div>
        </div>

        {/* Блок отслеживания задач */}
        <div className="card p-5">
          <div className="text-center mb-4">
            <h2 className="text-lg font-bold text-slate-900 mb-1">Ваши задачи</h2>
            <p className="text-sm text-slate-500">Активный период оценки</p>
          </div>

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
        {hasSubordinates ? (
          <div className="card p-5">
            <div className="flex items-start gap-3 mb-5">
              <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900 mb-1">
                  Процесс оценки (для менеджеров с подчиненными)
                </h2>
                <p className="text-slate-600 text-sm">
                  Если у вас есть подчиненные, процесс оценки включает дополнительные этапы
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Шаг 1 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">1</div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Star className="w-4 h-4 text-warning-500" />
                    Самооценка и оценка вашего менеджера
                  </h3>
                  <p className="text-sm text-slate-700 mb-2">
                    Внимательно прочитайте критерии оценок. Сначала вы выполняете самооценку по установленным критериям. Затем вы оцениваете своего руководителя.
                  </p>
                  <div className="bg-warning-50 border border-warning-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-warning-900 mb-1">Важно: Анонимность оценки вами своего менеджера</p>
                        <p className="text-sm text-warning-800">
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
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Users className="w-4 h-4 text-purple-500" />
                    Оценка качества управления от подчиненных
                  </h3>
                  <p className="text-sm text-slate-700 mb-2">
                    Ваши подчиненные оценивают вас по критериям качества управления. Эта оценка также остается анонимной для вас.
                  </p>
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-2">
                    <div className="flex items-start gap-2">
                      <Shield className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-purple-800">
                        Оценки от подчиненных видят только C-level менеджеры для обеспечения конфиденциальности и объективности.
                      </p>
                    </div>
                  </div>
                  <div className="bg-brand-50 border border-brand-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <Award className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-brand-900 mb-1">Критерий для оценки руководителя</p>
                        <p className="text-sm text-brand-800">
                          Руководители (сотрудники, у которых есть прямые подчиненные) также будут оценены по критерию "Критерий для оценки руководителя". Оценка проводится каждым сотрудником отдела и непосредственным руководителем оцениваемого менеджера.
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
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <User className="w-4 h-4 text-success-500" />
                    Оценка ваших подчиненных
                  </h3>
                  <p className="text-sm text-slate-700 mb-2">
                    Вы оцениваете своих подчиненных по установленным критериям. Оценка вашего менеджера остается для вас недоступна, чтобы избежать искажения.
                  </p>
                  <div className="bg-info-50 border border-info-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-info-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-info-800">
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
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-brand-500" />
                    Оценка старшего менеджера (опционально)
                  </h3>
                  <p className="text-sm text-slate-700">
                    Старший менеджер может поставить вам свою оценку. В этом случае оценки вашего менеджера и старшего менеджера усредняются для получения финального результата.
                  </p>
                </div>
              </div>

              {/* Шаг 5 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-warning-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">5</div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-warning-500" />
                    Оценка C-level менеджеров
                  </h3>
                  <p className="text-sm text-slate-700">
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
                <h2 className="text-xl font-bold text-slate-900 mb-1">
                  Процесс оценки (для сотрудников без подчиненных)
                </h2>
                <p className="text-slate-600 text-sm">
                  Процесс оценки для обычных сотрудников включает следующие этапы
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Шаг 1 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">1</div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Star className="w-4 h-4 text-warning-500" />
                    Самооценка и оценка вашего менеджера
                  </h3>
                  <p className="text-sm text-slate-700 mb-2">
                    Внимательно прочитайте критерии оценок. Сначала вы выполняете самооценку по установленным критериям. Затем вы оцениваете своего руководителя.
                  </p>
                  <div className="bg-warning-50 border border-warning-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-warning-900 mb-1">Важно: Анонимность оценки вами своего менеджера</p>
                        <p className="text-sm text-warning-800">
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
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <User className="w-4 h-4 text-success-500" />
                    Оценка вашего менеджера
                  </h3>
                  <p className="text-sm text-slate-700 mb-2">
                    Ваш менеджер оценивает вас по установленным критериям. Оценка вашего менеджера остается для вас недоступна, чтобы избежать искажения.
                  </p>
                  <div className="bg-info-50 border border-info-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <EyeOff className="w-4 h-4 text-info-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-info-800">
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
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-brand-500" />
                    Оценка старшего менеджера (опционально)
                  </h3>
                  <p className="text-sm text-slate-700">
                    Старший менеджер может поставить вам свою оценку. В этом случае оценки вашего менеджера и старшего менеджера усредняются для получения финального результата.
                  </p>
                </div>
              </div>

              {/* Шаг 4 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-warning-500 text-white rounded-lg flex items-center justify-center font-bold text-sm">4</div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-warning-500" />
                    Оценка C-level менеджеров
                  </h3>
                  <p className="text-sm text-slate-700">
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
              <h2 className="text-xl font-bold text-slate-900 mb-2">Дополнительные критерии</h2>
              <p className="text-sm text-slate-700 leading-relaxed mb-3">
                Некоторые категории сотрудников будут оцениваться также и по дополнительным критериям. 
                Например, участники проектов могут иметь специальные проектные критерии, а сотрудники 
                определенных отделов - критерии, специфичные для их области деятельности.
              </p>
              {hasSubordinates && (
                <div className="bg-brand-50 border border-brand-200 rounded-lg p-3">
                  <p className="text-sm font-semibold text-brand-900 mb-1">Критерий для оценки руководителя</p>
                  <p className="text-sm text-brand-800">
                    Руководители (сотрудники, у которых есть прямые подчиненные) также будут оценены 
                    по критерию "Критерий для оценки руководителя". Оценка проводится каждым сотрудником 
                    отдела и непосредственным руководителем оцениваемого менеджера.
                  </p>
                </div>
              )}
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
          <h2 className="text-xl font-bold mb-2">Готовы начать?</h2>
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
