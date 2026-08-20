/**
 * EvaluationHistory - Страница истории проведенных оценок
 * 
 * Назначение: Отображение списка всех оценок, которые провел текущий пользователь
 * Доступ: manager, admin, c_level
 * 
 * Использует компоненты:
 * - EvaluationHistoryCard - карточка оценки
 * - EvaluationHistoryModal - модальное окно деталей
 * - LoadingSpinner - индикатор загрузки
 * - EmptyState - пустое состояние
 * 
 * Использует хуки:
 * - useEvaluationHistory - загрузка истории
 */

import React, { useState, useEffect, useMemo } from 'react';
import { ClipboardList, Users, UserCheck, Crown } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

// Компоненты
import { LoadingSpinner, EmptyState } from '../components/common';
import EvaluationHistoryCard from '../components/evaluation/EvaluationHistoryCard';
import EvaluationHistoryModal from '../components/evaluation/EvaluationHistoryModal';

// Хуки
import { useEvaluationHistory } from '../hooks/useEvaluationHistory';

const EvaluationHistory = ({ user }) => {
  // Хук для работы с историей
  const {
    history,
    loading,
    evaluationDetails,
    loadingDetails,
    fetchDetails,
    clearDetails
  } = useEvaluationHistory(user?.id);

  // Состояние для проверки подчиненных
  const [hasSubordinates, setHasSubordinates] = useState(false);
  const [loadingSubordinates, setLoadingSubordinates] = useState(true);

  // Разделяем историю на оценки подчиненных и оценки руководителя
  const { subordinateEvaluations, managerEvaluations, totalEvaluations } = useMemo(() => {
    const subordinate = [];
    const manager = [];
    
    // Фильтруем только валидные записи с обязательными полями для отображения
    const validHistory = history.filter(item => {
      if (!item || !item.id) {
        return false;
      }
      
      // Проверяем, что evaluatee_name существует и не пустое
      const hasValidName = item.evaluatee_name && 
                           typeof item.evaluatee_name === 'string' && 
                           item.evaluatee_name.trim() !== '';
      
      // Проверяем, что evaluation_date существует
      const hasValidDate = item.evaluation_date && 
                          (item.evaluation_date !== null && 
                           item.evaluation_date !== '');
      
      // Для оценок руководителя (evaluation_source === 'subordinate')
      if (item.evaluation_source === 'subordinate') {
        // Должно быть хотя бы имя или дата
        return hasValidName || hasValidDate;
      }
      
      // Для оценок подчиненных (обычные оценки)
      // Должно быть и имя, и дата для корректного отображения
      const isValid = hasValidName && hasValidDate;
      
      // Логируем невалидные записи для отладки (можно удалить после исправления)
      if (!isValid && history.length > 0) {
        logger.warn('Отфильтрована невалидная запись оценки:', {
          id: item.id,
          evaluatee_name: item.evaluatee_name,
          evaluation_date: item.evaluation_date,
          evaluation_source: item.evaluation_source
        });
      }
      
      return isValid;
    });
    
    validHistory.forEach(item => {
      if (item.evaluation_source === 'subordinate') {
        manager.push(item); // Оценки, которые я дал своему руководителю
      } else {
        subordinate.push(item); // Оценки, которые я дал подчиненным
      }
    });
    
    // Подсчитываем общее количество отображаемых оценок
    const total = subordinate.length + manager.length;
    
    return { 
      subordinateEvaluations: subordinate, 
      managerEvaluations: manager,
      totalEvaluations: total
    };
  }, [history]);

  // Состояние модального окна
  const [selectedEvaluation, setSelectedEvaluation] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Проверка наличия подчиненных
  useEffect(() => {
    const checkSubordinates = async () => {
      if (!user) {
        setLoadingSubordinates(false);
        return;
      }

      try {
        setLoadingSubordinates(true);
        const response = await apiClient.get(API_ENDPOINTS.EMPLOYEES, {
          params: { user_id: user.id, role: user.role }
        });
        
        const employeesData = Array.isArray(response.data) 
          ? response.data[0]?.data || [] 
          : response.data.data || [];
        
        // Фильтруем: убираем самого себя из списка
        const subordinates = employeesData.filter(emp => emp.id !== user.id);
        setHasSubordinates(subordinates.length > 0);
      } catch (error) {
        logger.error('Ошибка проверки подчиненных:', error);
        setHasSubordinates(false);
      } finally {
        setLoadingSubordinates(false);
      }
    };

    checkSubordinates();
  }, [user]);

  // Форматирование даты
  const formatDate = (dateString) => {
    if (!dateString) return 'Дата неизвестна';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Открыть детали
  const handleOpenDetails = (evaluation) => {
    setSelectedEvaluation(evaluation);
    setIsModalOpen(true);
    fetchDetails(evaluation.id);
  };

  // Закрыть модалку
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEvaluation(null);
    clearDetails();
  };

  // Состояние загрузки
  if (loading || loadingSubordinates) {
    return <LoadingSpinner text="Загрузка истории оценок..." />;
  }

  // Если нет ни подчиненных, ни оценок руководителя - показываем сообщение
  const hasAnyEvaluations = totalEvaluations > 0;
  if (!hasSubordinates && !hasAnyEvaluations) {
    return (
      <div className="p-8 bg-gray-50 min-h-screen">
        <header className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <ClipboardList className="w-8 h-8 text-indigo-600" />
            <h1 className="text-3xl font-bold text-gray-900">Мои оценки</h1>
          </div>
        </header>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Оценок пока нет
          </h3>
          <p className="text-gray-600">
            Здесь будут ваши оценки, когда вы их проведете.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <ClipboardList className="w-8 h-8 text-indigo-600" />
          <h1 className="text-3xl font-bold text-gray-900">Мои оценки</h1>
        </div>
        <p className="text-gray-500">
          Все оценки, которые вы провели
          <span className="ml-2 text-indigo-600 font-medium">
            (Всего: {totalEvaluations})
          </span>
        </p>
      </header>

      {/* Оценки руководителя (если есть) */}
      {managerEvaluations.length > 0 && (
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <Crown className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Оценки руководителя</h2>
              <p className="text-sm text-gray-500">
                Оценки, которые вы дали своему руководителю ({managerEvaluations.length})
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {managerEvaluations.map((item) => (
              <EvaluationHistoryCard
                key={item.id}
                evaluation={item}
                formatDate={formatDate}
                onClick={() => handleOpenDetails(item)}
                variant="manager"
              />
            ))}
          </div>
        </div>
      )}

      {/* История оценок подчиненных */}
      {hasSubordinates && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
              <Users className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Оценки подчиненных</h2>
              <p className="text-sm text-gray-500">
                Оценки, которые вы дали своим подчиненным ({subordinateEvaluations.length})
              </p>
            </div>
          </div>
          
          {subordinateEvaluations.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Оценок подчиненных пока нет
              </h3>
              <p className="text-gray-600">
                Здесь будут оценки ваших подчиненных, когда вы их оцените.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {subordinateEvaluations.map((item) => (
                <EvaluationHistoryCard
                  key={item.id}
                  evaluation={item}
                  formatDate={formatDate}
                  onClick={() => handleOpenDetails(item)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Модальное окно */}
      <EvaluationHistoryModal
        isOpen={isModalOpen}
        evaluation={selectedEvaluation}
        details={evaluationDetails}
        loading={loadingDetails}
        formatDate={formatDate}
        onClose={handleCloseModal}
      />
    </div>
  );
};

export default EvaluationHistory;
