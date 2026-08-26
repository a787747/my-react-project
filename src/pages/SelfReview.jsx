/**
 * SelfReview - Страница самооценки
 * 
 * Назначение: Заполнение самооценки пользователем
 * Доступ: Все авторизованные пользователи
 * 
 * Использует компоненты:
 * - SelfReviewStatusCard - карточка статуса
 * - SelfReviewModal - модальное окно с формой
 * - LoadingSpinner - индикатор загрузки
 * 
 * Использует хуки:
 * - useSelfReview - логика самооценки
 */

import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';

// Компоненты
import { LoadingSpinner, OutOfScopeNotice, CampaignNotStartedNotice, RatingGuide } from '../components/common';
import { SelfReviewStatusCard, SelfReviewModal } from '../components/self-review';

// Хуки
import { useSelfReview } from '../hooks/useSelfReview';
import { useTaskStatus } from '../context/TaskStatusContext';

const SelfReview = () => {
  // Контекст статусов задач для обновления сайдбара
  const {
    refreshTaskStatus,
    isOutOfScope,
    outOfScopeReason,
    actorScopeOverride,
    campaignActive,
    periodInPreparation,
    loading: loadingTaskStatus
  } = useTaskStatus();
  
  // Хук для работы с самооценкой
  const {
    user,
    loading,
    hasReview,
    reviewData,
    evaluatedCriteriaIds,
    criteria,
    newCriteria,
    grades,
    comments,
    submitting,
    draftRestored,
    setGrades,
    setComments,
    submitReview
  } = useSelfReview();

  // Состояние модального окна
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Admin и C-level не делают самооценку
  const isExemptFromReview = user?.role === 'c_level' || user?.role === 'admin';

  // Форматирование даты
  const formatDate = (dateString) => {
    try {
      if (!dateString) return 'Дата неизвестна';
      return new Date(dateString).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  // Отправка самооценки
  const handleSubmit = async () => {
    const result = await submitReview();
    
    if (result.success) {
      // Обновляем статусы задач в сайдбаре
      refreshTaskStatus();
      setIsModalOpen(false);
    } else {
      alert(result.error || 'Ошибка при сохранении');
    }
  };

  // Состояние загрузки
  if (loading || loadingTaskStatus) {
    return <LoadingSpinner text="Загрузка критериев..." />;
  }

  if (isOutOfScope) {
    return (
      <OutOfScopeNotice
        reason={outOfScopeReason}
        scopeOverride={actorScopeOverride}
      />
    );
  }

  // Кампания не идёт: период не активен, либо активен, но оценка не запущена
  // (D-0822-1). Сервер в этом окне отвечает 409 PERIOD_NOT_STARTED.
  if (!campaignActive) {
    return <CampaignNotStartedNotice inPreparation={periodInPreparation} />;
  }

  // Для Admin и C-level показываем сообщение, что самооценка не требуется
  if (isExemptFromReview) {
    const roleLabel = user?.role === 'admin' ? 'администраторов' : 'руководителей C-level';
    
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Самооценка</h1>
            <p className="text-gray-600">Оцените свою работу в текущем периоде</p>
          </div>

          {/* Информационная карточка для Admin/C-level */}
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-8 text-center">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold text-purple-900 mb-2">
              Самооценка не требуется
            </h3>
            <p className="text-purple-700">
              Для {roleLabel} самооценка не предусмотрена в системе оценки.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Критерии для отображения в модалке
  const criteriaToShow = hasReview ? newCriteria : criteria;

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Самооценка</h1>
          <p className="text-gray-600">Оцените свою работу в текущем периоде</p>
        </div>

        <div className="mb-6">
          <RatingGuide variant="employee" />
        </div>

        {/* Предупреждение */}
        <div className="bg-amber-50 border-l-4 border-amber-400 p-6 mb-6 rounded-r-xl shadow-sm">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-amber-900 mb-2">
                Важная информация
              </h3>
              <div className="space-y-3 text-amber-800 text-sm">
                <p>
                  Самооценка проводится <strong>ОДИН РАЗ</strong> и не подлежит пересмотру.
                </p>
                <p>
                  После сохранения вы не сможете изменить свои оценки.
                </p>
                <p>
                  Будьте честны и объективны при оценке своих результатов. Самооценка не влияет на материальную составляющую мотивации и нужна для планирования развития сотрудников.
                </p>
                <p className="font-semibold">
                  Явное завышение или занижение не будет добавлять вам никаких преимуществ.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Карточка статуса */}
        <SelfReviewStatusCard
          hasReview={hasReview}
          reviewData={reviewData}
          newCriteriaCount={newCriteria.length}
          totalCriteriaCount={criteria.length}
          evaluatedCount={evaluatedCriteriaIds.length}
          onStartReview={() => setIsModalOpen(true)}
          formatDate={formatDate}
        />
      </div>

      {/* Модальное окно */}
      <SelfReviewModal
        isOpen={isModalOpen}
        isUpdate={hasReview}
        userName={user?.full_name}
        criteria={criteriaToShow}
        grades={grades}
        comments={comments}
        submitting={submitting}
        draftRestored={draftRestored}
        onGradeChange={setGrades}
        onCommentChange={setComments}
        onSubmit={handleSubmit}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};

export default SelfReview;
