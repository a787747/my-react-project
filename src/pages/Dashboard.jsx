import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { User, Briefcase, Award, ChevronRight, Star, X, Loader2, CheckCircle, Edit } from 'lucide-react';

// URL API endpoints
const API_GET_EMPLOYEES = 'http://92.51.45.147:5678/webhook/api/employees'; 
const API_GET_CRITERIA = 'http://92.51.45.147:5678/webhook/api/criteria';
const API_SUBMIT_EVALUATION = 'http://92.51.45.147:5678/webhook/api/submit-evaluation-v3';
const API_UPDATE_EVALUATION = 'http://92.51.45.147:5678/webhook/api/update-evaluation';
const API_CHECK_EVALUATED = 'http://92.51.45.147:5678/webhook/api/check-evaluated';
const API_EVALUATION_DETAILS = 'http://92.51.45.147:5678/webhook/api/evaluation-details';
const API_GET_EMPLOYEE_SELF_REVIEW = 'http://92.51.45.147:5678/webhook/api/employee-self-review';
const API_CHECK_SELF_REVIEWS_STATUS = 'http://92.51.45.147:5678/webhook/api/check-self-reviews';

const Dashboard = ({ user }) => {
  const [employees, setEmployees] = useState([]);
  const [criteria, setCriteria] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [evaluatedDetails, setEvaluatedDetails] = useState({});
  const [selfReviewsStatus, setSelfReviewsStatus] = useState({});

  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingEvaluationId, setEditingEvaluationId] = useState(null);
  const [employeeSelfReview, setEmployeeSelfReview] = useState(null);
  const [loadingSelfReview, setLoadingSelfReview] = useState(false);
  
  const [evaluations, setEvaluations] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [loadingExisting, setLoadingExisting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;

      try {
        setLoading(true);

        // Загружаем данные независимо друг от друга
        const employeesRes = await axios.get(API_GET_EMPLOYEES, {
          params: {
            user_id: user.id,
            role: user.role
          }
        });
        console.log('📥 Employees API response:', employeesRes.data);

        const criteriaRes = await axios.get(API_GET_CRITERIA);
        console.log('📥 Criteria API response:', criteriaRes.data);

        // Эти два могут упасть - обрабатываем отдельно
        let evaluatedRes = null;
        let selfReviewsRes = null;

        try {
          evaluatedRes = await axios.get(API_CHECK_EVALUATED, {
            params: {
              evaluator_id: user.id
            }
          });
        } catch (err) {
          console.log('Не удалось загрузить оценки:', err.message);
        }

        try {
          selfReviewsRes = await axios.get(API_CHECK_SELF_REVIEWS_STATUS);
          console.log('⭐ Self reviews API response:', selfReviewsRes.data);
        } catch (err) {
          console.log('Не удалось загрузить самооценки:', err.message);
        }

        const employeesData = Array.isArray(employeesRes.data) 
          ? employeesRes.data[0]?.data || [] 
          : employeesRes.data.data || [];

        console.log('👥 RAW employeesRes.data:', employeesRes.data);
        console.log('👥 Parsed employeesData:', employeesData);

        const criteriaData = Array.isArray(criteriaRes.data)
          ? criteriaRes.data[0]?.data || []
          : criteriaRes.data.data || [];

        setEmployees(employeesData);
        setCriteria(criteriaData);
        
        console.log('✅ Установлено сотрудников:', employeesData.length);

        if (evaluatedRes) {
          const evaluatedData = evaluatedRes.data.details || [];
          const evaluatedMap = {};
          evaluatedData.forEach(item => {
            evaluatedMap[item.subject_id] = {
              latest_evaluation_id: item.latest_evaluation_id,
              last_score: item.last_score
            };
          });
          setEvaluatedDetails(evaluatedMap);
        }

        if (selfReviewsRes) {
          const selfReviews = selfReviewsRes.data.data || {};
          setSelfReviewsStatus(selfReviews);
          console.log('⭐ Parsed self reviews:', selfReviews);
        }

      } catch (error) {
        console.error('Ошибка загрузки данных:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  const loadEmployeeSelfReview = async (employeeId) => {
    try {
      setLoadingSelfReview(true);
      const response = await axios.get(API_GET_EMPLOYEE_SELF_REVIEW, {
        params: { subject_id: employeeId }
      });
      setEmployeeSelfReview(response.data);
    } catch (error) {
      console.error('Ошибка загрузки самооценки:', error);
      setEmployeeSelfReview(null);
    } finally {
      setLoadingSelfReview(false);
    }
  };

  const handleOpenEvaluation = async (employee) => {
    setSelectedEmployee(employee);
    setEvaluations({});
    setSubmitResult(null);
    setIsEditMode(false);
    setEditingEvaluationId(null);
    setIsModalOpen(true);
    await loadEmployeeSelfReview(employee.id);
  };

  const handleOpenEdit = async (employee) => {
    setSelectedEmployee(employee);
    setSubmitResult(null);
    setIsEditMode(true);
    setIsModalOpen(true);
    setLoadingExisting(true);
    await loadEmployeeSelfReview(employee.id);

    try {
      const evaluationDetail = evaluatedDetails[employee.id];
      if (!evaluationDetail) return;

      const response = await axios.get(API_EVALUATION_DETAILS, {
        params: {
          evaluation_id: evaluationDetail.latest_evaluation_id
        }
      });

      const details = response.data;
      setEditingEvaluationId(details.evaluation.evaluation_id);

      const existingScores = {};
      details.scores.forEach(score => {
        existingScores[score.criteria_title] = score.score_value;
      });
      setEvaluations(existingScores);

    } catch (error) {
      console.error('Ошибка загрузки оценки:', error);
    } finally {
      setLoadingExisting(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
    setEvaluations({});
    setSubmitResult(null);
    setIsEditMode(false);
    setEditingEvaluationId(null);
    setEmployeeSelfReview(null);
  };

  const handleSliderChange = (criterionTitle, value) => {
    setEvaluations(prev => ({
      ...prev,
      [criterionTitle]: parseInt(value)
    }));
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);

      const scores = Object.values(evaluations);
      const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
      const gradeCoef = selectedEmployee.grade_coefficient || 1.0;
      const finalScore = (average * gradeCoef).toFixed(2);

      if (isEditMode && editingEvaluationId) {
        await axios.post(API_UPDATE_EVALUATION, {
          evaluation_id: editingEvaluationId,
          final_score: parseFloat(finalScore),
          grades: evaluations
        });
        setSubmitResult({ success: true, message: 'Оценка обновлена!', score: finalScore });
      } else {
        const response = await axios.post(API_SUBMIT_EVALUATION, {
          evaluator_id: user.id,
          subject_id: selectedEmployee.id,
          final_score: parseFloat(finalScore),
          grades: evaluations
        });
        setSubmitResult({ success: true, message: 'Оценка сохранена!', score: finalScore });
      }

      const evaluatedRes = await axios.get(API_CHECK_EVALUATED, {
        params: { evaluator_id: user.id }
      });
      const evaluatedData = evaluatedRes.data.details || [];
      const evaluatedMap = {};
      evaluatedData.forEach(item => {
        evaluatedMap[item.subject_id] = {
          latest_evaluation_id: item.latest_evaluation_id,
          last_score: item.last_score
        };
      });
      setEvaluatedDetails(evaluatedMap);

    } catch (error) {
      console.error('Ошибка сохранения:', error);
      setSubmitResult({ success: false, message: 'Ошибка при сохранении оценки' });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  const filteredCriteria = selectedEmployee
    ? criteria.filter(c => {
        const isActive = c.is_active === true;
        const audience = c.target_audience?.toLowerCase() || 'all';
        const category = selectedEmployee.work_category?.toLowerCase() || 'general';
        return isActive && (audience === 'all' || audience === category);
      })
    : [];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Моя команда</h1>
          <p className="text-gray-600">Сотрудники в вашем подчинении</p>
        </div>

        {employees.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <User className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Команда не найдена</h3>
            <p className="text-gray-600">У вас нет прямых подчиненных для оценки.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {employees.map((emp) => {
              const isEvaluated = evaluatedDetails[emp.id];
              const lastScore = isEvaluated?.last_score;
              const hasSelfReview = selfReviewsStatus[emp.id]?.has_self_review;
              const selfReviewScore = selfReviewsStatus[emp.id]?.score;
              
              console.log(`👤 ${emp.full_name} (id=${emp.id}):`, {
                hasSelfReview,
                selfReviewScore,
                statusObject: selfReviewsStatus[emp.id]
              });

              return (
                <div
                  key={emp.id}
                  className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg transition-all"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-2xl">
                      {emp.full_name?.charAt(0) || 'U'}
                    </div>
                    
                    <div className="flex flex-col items-end gap-2">
                      {hasSelfReview && (
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700 flex items-center gap-1">
                          <Star className="w-3 h-3" />
                          Самооценка {parseFloat(selfReviewScore).toFixed(1)}
                        </span>
                      )}
                      
                      {isEvaluated && (
                        <div className="flex flex-col items-end gap-1">
                          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Оценен
                          </span>
                          {lastScore && (
                            <span className="text-xs text-gray-600">
                              Балл: <span className="font-bold text-green-600">{parseFloat(lastScore).toFixed(1)}</span>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <h3 className="text-lg font-semibold text-gray-900">{emp.full_name}</h3>
                  <p className="text-gray-500 text-sm mb-4">{emp.job_title}</p>
                  
                  <div className="space-y-2 mb-6">
                    <div className="flex items-center text-sm text-gray-600">
                      <Briefcase className="w-4 h-4 mr-2" />
                      {emp.department_name || 'No Dept'}
                    </div>
                    <div className="flex items-center text-sm text-gray-600">
                      <Award className="w-4 h-4 mr-2" />
                      Grade: {emp.grade_code || 'N/A'}
                    </div>
                  </div>

                  <button 
                    onClick={() => isEvaluated ? handleOpenEdit(emp) : handleOpenEvaluation(emp)}
                    className={`w-full flex items-center justify-center space-x-2 py-2.5 rounded-lg transition-all font-medium ${
                      isEvaluated 
                        ? 'bg-green-600 hover:bg-green-700 text-white' 
                        : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                    }`}
                  >
                    {isEvaluated ? (
                      <>
                        <Edit className="w-4 h-4" />
                        <span>Редактировать</span>
                      </>
                    ) : (
                      <>
                        <Star className="w-4 h-4" />
                        <span>Оценить</span>
                      </>
                    )}
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {isModalOpen && selectedEmployee && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-6 flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold text-2xl">
                  {selectedEmployee.full_name?.charAt(0) || 'U'}
                </div>
                <div>
                  <h2 className="text-2xl font-bold mb-1">{selectedEmployee.full_name}</h2>
                  <p className="text-indigo-100">{selectedEmployee.job_title}</p>
                </div>
              </div>
              <button onClick={handleCloseModal} className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-4 bg-indigo-50 border-b border-indigo-100">
              <p className="text-sm text-indigo-900">
                Категория: <span className="font-medium text-gray-700 capitalize">{selectedEmployee.work_category}</span>
                {isEditMode && <span className="ml-2 text-green-600 font-medium">• Режим редактирования</span>}
              </p>
            </div>

            <div className="p-6 space-y-8 flex-1 overflow-y-auto">
              {loadingExisting ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
                  <span className="ml-3 text-gray-600">Загрузка существующей оценки...</span>
                </div>
              ) : !submitResult ? (
                <>
                  {employeeSelfReview?.has_self_review && (
                    <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-4 mb-6">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="w-6 h-6 text-blue-600 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-blue-900 font-semibold">Сотрудник провел самооценку</p>
                          <p className="text-sm text-blue-700">
                            Общий балл самооценки: <span className="font-bold">{employeeSelfReview.total_score}</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {filteredCriteria.length === 0 ? (
                    <div className="text-center py-10 text-gray-500">
                      Нет активных критериев для категории "{selectedEmployee.work_category}".
                    </div>
                  ) : (
                    filteredCriteria.map((criterion) => (
                      <div key={criterion.id} className="space-y-3">
                        <div className="flex justify-between items-end">
                          <label className="text-base font-medium text-gray-800">
                            {criterion.title}
                          </label>
                          <span className="text-2xl font-bold text-indigo-600 w-12 text-right">
                            {evaluations[criterion.title] ?? 0}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">{criterion.description}</p>
                        
                        <input
                          type="range"
                          min="0"
                          max="10"
                          step="1"
                          value={evaluations[criterion.title] ?? 0}
                          onChange={(e) => handleSliderChange(criterion.title, e.target.value)}
                          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 hover:accent-indigo-700"
                        />
                        <div className="flex justify-between text-xs text-gray-400 font-medium">
                          <span>Плохо (0)</span>
                          <span>Отлично (10)</span>
                        </div>
                        
                        {employeeSelfReview?.has_self_review && employeeSelfReview.scores[criterion.id] !== undefined && (
                          <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-blue-900 font-medium flex items-center gap-2">
                                <Star className="w-4 h-4 text-blue-600" />
                                Самооценка сотрудника:
                              </span>
                              <span className="text-lg font-bold text-blue-600">
                                {employeeSelfReview.scores[criterion.id]}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
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
                    onClick={handleCloseModal}
                    className="mt-6 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
                  >
                    Закрыть
                  </button>
                </div>
              )}
            </div>

            {!submitResult && (
              <div className="p-6 border-t border-gray-200 bg-gray-50 flex gap-3">
                <button
                  onClick={handleCloseModal}
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
      )}
    </div>
  );
};

export default Dashboard;
