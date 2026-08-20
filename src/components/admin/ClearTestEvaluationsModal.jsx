/**
 * ClearTestEvaluationsModal - Модальное окно подтверждения очистки тестовых оценок
 * 
 * Назначение: Подтверждение удаления всех тестовых оценок с таймером обратного отсчета
 * Используется в: AdminSettings
 * 
 * Props:
 * - isOpen: boolean - открыто ли окно
 * - onConfirm: function - подтверждение действия
 * - onCancel: function - отмена действия
 */

import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, Trash2, Clock } from 'lucide-react';

const ClearTestEvaluationsModal = ({ isOpen, onConfirm, onCancel }) => {
  const [countdown, setCountdown] = useState(10);
  const [canConfirm, setCanConfirm] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      // Сброс при закрытии
      setCountdown(10);
      setCanConfirm(false);
      return;
    }

    // Запускаем таймер только когда модалка открыта
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          setCanConfirm(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (canConfirm) {
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full">
        {/* Header */}
        <div className="bg-red-50 border-b border-red-200 p-6 rounded-t-2xl">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Очистка тестовых оценок
                </h2>
                <p className="text-sm text-red-600 mt-1">
                  Внимание! Это действие необратимо
                </p>
              </div>
            </div>
            <button
              onClick={onCancel}
              className="p-2 hover:bg-red-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="mb-6">
            <p className="text-gray-700 mb-4">
              Вы собираетесь удалить <strong>все тестовые оценки всех сотрудников</strong>.
            </p>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-yellow-800">
                <strong>Это действие:</strong>
              </p>
              <ul className="list-disc list-inside text-sm text-yellow-800 mt-2 space-y-1">
                <li>Удалит все тестовые оценки из системы</li>
                <li>Не может быть отменено</li>
                <li>Затронет всех сотрудников</li>
              </ul>
            </div>

            {/* Таймер */}
            <div className="flex items-center justify-center gap-3 mb-4">
              <Clock className="w-5 h-5 text-gray-500" />
              <div className="text-center">
                {countdown > 0 ? (
                  <>
                    <div className="text-3xl font-bold text-red-600">
                      {countdown}
                    </div>
                    <div className="text-sm text-gray-500">
                      секунд до разблокировки
                    </div>
                  </>
                ) : (
                  <>
                    <div className="text-lg font-semibold text-green-600">
                      Готово к подтверждению
                    </div>
                    <div className="text-sm text-gray-500">
                      Вы можете подтвердить действие
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Вопрос подтверждения */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-sm font-medium text-gray-700 mb-2">
              Вы уверены, что хотите продолжить?
            </p>
            <p className="text-xs text-gray-500">
              Нажмите кнопку подтверждения ниже, чтобы удалить все тестовые оценки.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-2xl flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors"
          >
            Отмена
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm}
            className={`flex-1 py-3 font-medium rounded-lg transition-all flex items-center justify-center gap-2 ${
              canConfirm
                ? 'bg-red-600 hover:bg-red-700 text-white shadow-md hover:shadow-lg'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Trash2 className="w-5 h-5" />
            {canConfirm ? 'Подтвердить удаление' : `Подождите ${countdown}с`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClearTestEvaluationsModal;





