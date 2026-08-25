/**
 * SelfReviewDetailsModal - Модальное окно просмотра самооценки сотрудника
 * 
 * Назначение: Отображение деталей самооценки с комментариями (только просмотр)
 * Используется в: TeamView
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - employee: object - сотрудник
 * - onClose: function - закрыть окно
 */

import React, { useState, useEffect } from 'react';
import { X, Star, MessageSquare, Loader2, AlertCircle, User } from 'lucide-react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../config/api';
import { getScoreZone } from '../utils/evaluationUtils';
import logger from '../utils/logger';

const SelfReviewDetailsModal = ({ isOpen, employee, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [selfReviewData, setSelfReviewData] = useState(null);
  const [criteria, setCriteria] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !employee) return;

    const abortController = new AbortController();
    const signal = abortController.signal;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      setSelfReviewData(null);

      try {
        // Загружаем параллельно самооценку и критерии
        const [selfReviewRes, criteriaRes] = await Promise.all([
          apiClient.get(API_ENDPOINTS.CHECK_SELF_REVIEWS, {
            params: { user_id: employee.id },
            signal
          }),
          apiClient.get(API_ENDPOINTS.CRITERIA, { signal })
        ]);

        if (!signal.aborted) {
          if (selfReviewRes.data?.has_self_review) {
            setSelfReviewData(selfReviewRes.data);
          } else {
            setError('У сотрудника нет самооценки');
          }

          // Обработка критериев
          const criteriaData = Array.isArray(criteriaRes.data)
            ? criteriaRes.data[0]?.data || []
            : criteriaRes.data.data || [];
          setCriteria(criteriaData);
        }
      } catch (err) {
        if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
          logger.error('Ошибка загрузки самооценки:', err);
          setError('Не удалось загрузить данные самооценки');
        }
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    };

    loadData();

    return () => {
      abortController.abort();
    };
  }, [isOpen, employee]);

  if (!isOpen || !employee) return null;

  // Находим критерий по ID
  const getCriterionById = (id) => criteria.find(c => c.id === id || c.id === Number(id));

  // Получаем название критерия
  const getCriterionTitle = (key) => {
    const criterion = getCriterionById(key);
    return criterion?.title || `Критерий ${key}`;
  };

  // Форматирование даты
  const formatDate = (dateString) => {
    try {
      if (!dateString) return 'Дата неизвестна';
      return new Date(dateString).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const displayName = employee.full_name || 'Неизвестный сотрудник';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 flex items-start justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold text-2xl backdrop-blur-md">
              {initial}
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">{displayName}</h2>
              <p className="text-blue-100">{employee.job_title || 'Должность не указана'}</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
            aria-label="Закрыть"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
              <span className="text-gray-500">Загрузка самооценки...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{error}</h3>
              <p className="text-gray-500">Сотрудник ещё не заполнил самооценку</p>
            </div>
          ) : selfReviewData ? (
            <div className="space-y-6">
              {/* Общий балл и дата */}
              <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <div className="flex items-center gap-3">
                  <Star className="w-6 h-6 text-blue-600 fill-current" />
                  <div>
                    <p className="text-sm text-blue-700 font-medium">Общий балл самооценки</p>
                    {selfReviewData.created_at && (
                      <p className="text-xs text-blue-500 mt-0.5">
                        Заполнено: {formatDate(selfReviewData.created_at)}
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-3xl font-bold text-blue-700">
                  {parseFloat(selfReviewData.score).toFixed(1)}
                </div>
              </div>


              {/* Оценки по критериям */}
              {selfReviewData.grades && Object.keys(selfReviewData.grades).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Оценки по критериям</h3>
                  <div className="space-y-3">
                    {Object.entries(selfReviewData.grades).map(([criterionKey, score]) => {
                      const numericScore = parseInt(score, 10);
                      const criterion = getCriterionById(criterionKey);
                      const zone = getScoreZone(numericScore, criterion || criterionKey);
                      
                      // Получаем комментарий для этого критерия
                      const comment = selfReviewData.comments?.[criterionKey];
                      
                      return (
                        <div 
                          key={criterionKey}
                          className={`p-4 rounded-xl border-2 ${zone?.border || 'border-gray-200'} ${zone?.bg || 'bg-gray-50'}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0 pr-4">
                              <h4 className="font-medium text-gray-900">
                                {getCriterionTitle(criterionKey)}
                              </h4>
                              {criterion?.description && (
                                <p className="text-xs text-gray-500 mt-1 line-clamp-1">
                                  {criterion.description}
                                </p>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-2xl font-bold ${zone?.text || 'text-gray-700'}`}>
                                {numericScore}
                              </span>
                              <span className="text-sm text-gray-400">/10</span>
                            </div>
                          </div>
                          
                          {/* Комментарий к критерию */}
                          {comment && (
                            <div className="mt-3 pt-3 border-t border-gray-200 border-opacity-50">
                              <div className="flex items-start gap-2">
                                <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-gray-600 italic leading-relaxed whitespace-pre-wrap">
                                  "{comment}"
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Если нет детальных оценок */}
              {(!selfReviewData.grades || Object.keys(selfReviewData.grades).length === 0) && (
                <div className="text-center py-6 text-gray-500">
                  <User className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p>Детальные оценки по критериям недоступны</p>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 shrink-0">
          <button
            onClick={onClose}
            className="w-full px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-xl font-medium transition-colors shadow-md"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

export default SelfReviewDetailsModal;

