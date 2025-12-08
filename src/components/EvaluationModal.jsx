import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Loader2, CheckCircle } from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';
import { calculateFinalScore, filterCriteriaByEmployee } from '../utils/evaluationUtils';
import SelfReviewBanner from './SelfReviewBanner';
import CriterionSlider from './CriterionSlider';

const EvaluationModal = ({ 
  isOpen, 
  employee, 
  criteria, 
  isEditMode, 
  evaluatedDetails,
  user,
  onClose,
  onSuccess 
}) => {
  const [evaluations, setEvaluations] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [employeeSelfReview, setEmployeeSelfReview] = useState(null);
  const [loadingSelfReview, setLoadingSelfReview] = useState(false);

  const filteredCriteria = filterCriteriaByEmployee(criteria, employee);

  useEffect(() => {
    if (!isOpen || !employee) return;

    const loadData = async () => {
      setEvaluations({});
      setSubmitResult(null);
      setLoadingSelfReview(true);
      setLoadingExisting(isEditMode);

      // Загружаем самооценку
      try {
        const response = await axios.get(API_ENDPOINTS.GET_EMPLOYEE_SELF_REVIEW, {
          params: { subject_id: employee.id }
        });
        setEmployeeSelfReview(response.data);
      } catch (error) {
        console.error('Ошибка загрузки самооценки:', error);
        setEmployeeSelfReview(null);
      } finally {
        setLoadingSelfReview(false);
      }

      // Загружаем существующую оценку в режиме редактирования
      if (isEditMode) {
        try {
          const evaluationDetail = evaluatedDetails[employee.id];
          if (evaluationDetail) {
            const response = await axios.get(API_ENDPOINTS.EVALUATION_DETAILS, {
              params: { evaluation_id: evaluationDetail.latest_evaluation_id }
            });

            const details = response.data;
            const existingScores = {};
            if (Array.isArray(details.scores)) {
              details.scores.forEach(score => {
                existingScores[score.criteria_title] = score.score_value;
              });
            }
            setEvaluations(existingScores);
          }
        } catch (error) {
          console.error('Ошибка загрузки оценки:', error);
        } finally {
          setLoadingExisting(false);
        }
      } else {
        // Если не в режиме редактирования, сразу устанавливаем loadingExisting в false
        setLoadingExisting(false);
      }
    };

    loadData();
  }, [isOpen, employee, isEditMode, evaluatedDetails]);

  const handleSliderChange = (criterionTitle, value) => {
    setEvaluations(prev => ({
      ...prev,
      [criterionTitle]: parseInt(value)
    }));
  };

  const handleSubmit = async () => {
    if (!employee || !employee.id) {
      console.error('Ошибка: сотрудник не выбран');
      return;
    }

    try {
      setSubmitting(true);

      const finalScore = calculateFinalScore(evaluations, employee.grade_coefficient || 1.0);

      if (isEditMode && evaluatedDetails[employee.id]?.latest_evaluation_id) {
        await axios.post(API_ENDPOINTS.UPDATE_EVALUATION, {
          evaluation_id: evaluatedDetails[employee.id].latest_evaluation_id,
          final_score: parseFloat(finalScore),
          grades: evaluations
        });
        setSubmitResult({ success: true, message: 'Оценка обновлена!', score: finalScore });
      } else {
        await axios.post(API_ENDPOINTS.SUBMIT_EVALUATION, {
          evaluator_id: user.id,
          subject_id: employee.id,
          final_score: parseFloat(finalScore),
          grades: evaluations
        });
        setSubmitResult({ success: true, message: 'Оценка сохранена!', score: finalScore });
      }

      // Вызываем onSuccess только при успешном сохранении
      onSuccess();
    } catch (error) {
      console.error('Ошибка сохранения:', error);
      setSubmitResult({ success: false, message: 'Ошибка при сохранении оценки' });
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !employee) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-6 flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold text-2xl">
              {employee.full_name?.charAt(0) || 'U'}
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">{employee.full_name}</h2>
              <p className="text-indigo-100">{employee.job_title}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Category info */}
        <div className="p-4 bg-indigo-50 border-b border-indigo-100">
          <p className="text-sm text-indigo-900">
            Категория: <span className="font-medium text-gray-700 capitalize">{employee.work_category}</span>
            {isEditMode && <span className="ml-2 text-green-600 font-medium">• Режим редактирования</span>}
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8 flex-1 overflow-y-auto">
          {loadingExisting ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              <span className="ml-3 text-gray-600">Загрузка существующей оценки...</span>
            </div>
          ) : !submitResult ? (
            <>
              <SelfReviewBanner employeeSelfReview={employeeSelfReview} />
              
              {filteredCriteria.length === 0 ? (
                <div className="text-center py-10 text-gray-500">
                  Нет активных критериев для категории "{employee.work_category}".
                </div>
              ) : (
                filteredCriteria.map((criterion) => (
                  <CriterionSlider
                    key={criterion.id}
                    criterion={criterion}
                    value={evaluations[criterion.title]}
                    onChange={handleSliderChange}
                    employeeSelfReview={employeeSelfReview}
                  />
                ))
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
                submitResult.success ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {submitResult.success ? (
                  <CheckCircle className="w-10 h-10 text-green-600" />
                ) : (
                  <X className="w-10 h-10 text-red-600" />
                )}
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">{submitResult.message}</h3>
              {submitResult.success && (
                <p className="text-gray-600">
                  Итоговый балл: <span className="text-2xl font-bold text-indigo-600">{submitResult.score}</span>
                </p>
              )}
              <button
                onClick={onClose}
                className="mt-6 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
              >
                Закрыть
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        {!submitResult && (
          <div className="p-6 border-t border-gray-200 bg-gray-50 flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-100 transition-colors"
            >
              Отмена
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting || Object.keys(evaluations).length === 0}
              className="flex-1 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Сохранение...
                </span>
              ) : isEditMode ? 'Обновить оценку' : 'Сохранить оценку'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EvaluationModal;

