/**
 * Profile - Страница профиля пользователя
 * 
 * Назначение: Отображение личного профиля с оценками и статистикой
 * Доступ: Все авторизованные пользователи
 * 
 * Использует компоненты:
 * - ProfileStats - карточки статистики
 * - ProfileChart - график динамики
 * - SelfEvaluationCard - карточка самооценки
 * - ProfileEvaluationsTable - таблица истории
 * - EvaluationDetailsModal - модальное окно деталей
 * - LoadingSpinner - индикатор загрузки
 * 
 * Использует хуки:
 * - useProfile - загрузка данных профиля
 * - useUser - получение данных пользователя из контекста
 */

import React, { useState } from 'react';
import { Award, Users, Crown } from 'lucide-react';

// Компоненты
import { LoadingSpinner } from '../components/common';
import { 
  ProfileStats, 
  ProfileChart, 
  SelfEvaluationCard, 
  ProfileEvaluationsTable,
  EvaluationDetailsModal
} from '../components/profile';

// Хуки
import { useProfile } from '../hooks/useProfile';
import { useUser } from '../context/UserContext';

// Константы
import { ADMIN_ROLES } from '../config/constants';

const Profile = () => {
  // Получаем пользователя из контекста
  const { user } = useUser();

  // Хук для работы с профилем
  const {
    profileData,
    loading,
    error,
    selfEvaluations,
    managerEvaluations,
    subordinateEvaluations,
    evaluationDetails,
    loadingDetails,
    fetchEvaluationDetails,
    clearDetails
  } = useProfile(user?.id);

  // Проверяем, является ли пользователь обычным сотрудником
  const isRegularEmployee = user && !ADMIN_ROLES.includes(user.role);

  // Состояние модального окна
  const [selectedEvaluation, setSelectedEvaluation] = useState(null);

  // Форматирование даты
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  // Открыть детали оценки
  const handleViewDetails = (evaluation) => {
    // Для обычных сотрудников показываем детали только для самооценок
    if (isRegularEmployee && !evaluation.is_self_evaluation) {
      return;
    }
    setSelectedEvaluation(evaluation);
    fetchEvaluationDetails(evaluation.evaluation_id);
  };

  // Закрыть модалку
  const handleCloseModal = () => {
    setSelectedEvaluation(null);
    clearDetails();
  };

  // Состояние загрузки
  if (loading) {
    return <LoadingSpinner text="Загрузка профиля..." />;
  }

  // Состояние ошибки
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-red-600">
          Ошибка загрузки данных. Попробуйте обновить страницу.
        </div>
      </div>
    );
  }

  // Нет данных
  if (!profileData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Нет данных профиля</div>
      </div>
    );
  }

  // Последняя самооценка
  const latestSelfEvaluation = selfEvaluations.length > 0 
    ? selfEvaluations[selfEvaluations.length - 1] 
    : null;

  // Если это обычный сотрудник, показываем упрощенный интерфейс
  if (isRegularEmployee) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Мой профиль</h1>
          <p className="text-gray-600">
            {user?.full_name} • {user?.job_title}
          </p>
        </div>

        {/* Карточка самооценки */}
        <SelfEvaluationCard
          selfEvaluation={latestSelfEvaluation}
          formatDate={formatDate}
          onViewDetails={handleViewDetails}
        />

        {/* История самооценок */}
        {selfEvaluations.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden mb-8">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-800">
                История самооценок
              </h2>
            </div>
            <ProfileEvaluationsTable
              evaluations={selfEvaluations}
              formatDate={formatDate}
              onViewDetails={handleViewDetails}
              hideManagerEvaluations={true}
            />
          </div>
        )}

        {/* Информация об оценках менеджера (без баллов) */}
        {managerEvaluations.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                <Users className="w-5 h-5 text-blue-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-800">
                Оценки от руководителя
              </h2>
            </div>
            <div className="space-y-3">
              {managerEvaluations.map((evaluation) => (
                <div
                  key={evaluation.evaluation_id}
                  className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200"
                >
                  <div>
                    <div className="font-semibold text-gray-800">
                      {evaluation.period_name}
                    </div>
                    <div className="text-sm text-gray-600">
                      Оценен руководителем: {evaluation.evaluator_name}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {formatDate(evaluation.updated_at)}
                    </div>
                  </div>
                  <div className="px-4 py-2 bg-green-100 text-green-700 rounded-lg font-semibold">
                    ✓ Оценено
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Информация об оценках от подчиненных (без баллов) */}
        {user?.has_subordinates && subordinateEvaluations.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
                <Crown className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-800">
                  Оценки от подчиненных
                </h2>
                <p className="text-sm text-gray-500">
                  Оценки качества управления от вашей команды
                </p>
              </div>
            </div>
            <div className="space-y-3">
              {subordinateEvaluations.map((evaluation) => (
                <div
                  key={evaluation.evaluation_id}
                  className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200"
                >
                  <div>
                    <div className="font-semibold text-gray-800">
                      {evaluation.period_name}
                    </div>
                    <div className="text-sm text-gray-600">
                      Оценен подчиненным: {evaluation.evaluator_name}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {formatDate(evaluation.updated_at)}
                    </div>
                  </div>
                  <div className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg font-semibold">
                    ✓ Оценено
                  </div>
                </div>
              ))}
            </div>
            {/* Количество оценок */}
            <div className="mt-4 pt-4 border-t border-purple-200">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Всего оценок от подчиненных:</span>
                <span className="text-xl font-bold text-purple-600">
                  {subordinateEvaluations.length}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Модальное окно деталей (только для самооценок) */}
        <EvaluationDetailsModal
          isOpen={!!selectedEvaluation && selectedEvaluation?.is_self_evaluation}
          evaluation={selectedEvaluation}
          details={evaluationDetails}
          loading={loadingDetails}
          formatDate={formatDate}
          onClose={handleCloseModal}
          hideManagerDetails={true}
        />
      </div>
    );
  }

  // Для Admin и C-level показываем полный интерфейс
  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Мой профиль</h1>
        <p className="text-gray-600">
          {user?.full_name} • {user?.job_title}
        </p>
      </div>

      {/* Карточка самооценки */}
      <SelfEvaluationCard
        selfEvaluation={latestSelfEvaluation}
        formatDate={formatDate}
        onViewDetails={handleViewDetails}
      />

      {/* Контент с оценками */}
      {profileData.has_evaluations ? (
        <>
          {/* Карточки статистики */}
          <ProfileStats 
            stats={profileData.stats} 
            formatDate={formatDate} 
          />

          {/* График динамики */}
          <ProfileChart evaluations={managerEvaluations} />

          {/* Оценки от подчиненных (без баллов - для менеджеров) */}
          {user?.has_subordinates && subordinateEvaluations.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
                  <Crown className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">
                    Оценки от подчиненных
                  </h2>
                  <p className="text-sm text-gray-500">
                    Оценки качества управления от вашей команды
                  </p>
                </div>
              </div>
              <div className="space-y-3">
                {subordinateEvaluations.map((evaluation) => (
                  <div
                    key={evaluation.evaluation_id}
                    className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200"
                  >
                    <div>
                      <div className="font-semibold text-gray-800">
                        {evaluation.period_name}
                      </div>
                      <div className="text-sm text-gray-600">
                        Оценен подчиненным: {evaluation.evaluator_name}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {formatDate(evaluation.updated_at)}
                      </div>
                    </div>
                    <div className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg font-semibold">
                      ✓ Оценено
                    </div>
                  </div>
                ))}
              </div>
              {/* Количество оценок */}
              <div className="mt-4 pt-4 border-t border-purple-200">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Всего оценок от подчиненных:</span>
                  <span className="text-xl font-bold text-purple-600">
                    {subordinateEvaluations.length}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Таблица истории */}
          <ProfileEvaluationsTable
            evaluations={profileData.evaluations}
            formatDate={formatDate}
            onViewDetails={handleViewDetails}
            showWeightedScore={ADMIN_ROLES.includes(user?.role)}
          />
        </>
      ) : (
        /* Нет оценок */
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Award className="w-24 h-24 text-gray-300 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Вы еще не были оценены
          </h2>
          <p className="text-gray-600">
            Как только ваш менеджер проведет оценку, результаты появятся здесь.
          </p>
        </div>
      )}

      {/* Модальное окно деталей */}
      <EvaluationDetailsModal
        isOpen={!!selectedEvaluation}
        evaluation={selectedEvaluation}
        details={evaluationDetails}
        loading={loadingDetails}
        formatDate={formatDate}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default Profile;
