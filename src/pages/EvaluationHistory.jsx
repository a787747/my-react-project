import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ClipboardList, User, Calendar, Award, TrendingUp, X, Loader2, Star } from 'lucide-react';

const API_HISTORY = 'http://92.51.45.147:5678/webhook/api/evaluation-history';
const API_DETAILS = 'http://92.51.45.147:5678/webhook/api/evaluation-details';

const EvaluationHistory = ({ user }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedEvaluation, setSelectedEvaluation] = useState(null);
  const [evaluationDetails, setEvaluationDetails] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      if (!user) return;

      try {
        setLoading(true);
        const response = await axios.get(API_HISTORY, {
          params: {
            evaluator_id: user.id
          }
        });

        const data = response.data.data || [];
        setHistory(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error('Ошибка загрузки истории:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [user]);

  const handleOpenDetails = async (evaluation) => {
    setSelectedEvaluation(evaluation);
    setIsModalOpen(true);
    setLoadingDetails(true);

    try {
      const response = await axios.get(API_DETAILS, {
        params: {
          evaluation_id: evaluation.id
        }
      });

      setEvaluationDetails(response.data);
    } catch (error) {
      console.error('Ошибка загрузки деталей:', error);
      alert('Не удалось загрузить детали оценки');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEvaluation(null);
    setEvaluationDetails(null);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <ClipboardList className="w-8 h-8 text-indigo-600" />
          <h1 className="text-3xl font-bold text-gray-900">История оценок</h1>
        </div>
        <p className="text-gray-500">
          Все оценки, которые вы провели
          <span className="ml-2 text-indigo-600 font-medium">
            (Всего: {history.length})
          </span>
        </p>
      </header>

      {/* История оценок */}
      {history.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <ClipboardList className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900">История пуста</h3>
          <p className="text-gray-500 mt-1">
            Вы еще не провели ни одной оценки
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {history.map((item) => (
            <div
              key={item.id}
              onClick={() => handleOpenDetails(item)}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-lg hover:border-indigo-200 transition-all cursor-pointer group"
            >
              {/* Header карточки */}
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-indigo-50 rounded-lg group-hover:bg-indigo-100 transition-colors">
                  <User className="w-6 h-6 text-indigo-600" />
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-indigo-600">
                    {parseFloat(item.final_score).toFixed(1)}
                  </div>
                  <div className="text-xs text-gray-500">балл</div>
                </div>
              </div>

              {/* Имя сотрудника */}
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                {item.evaluatee_name}
              </h3>
              <p className="text-sm text-gray-500 mb-4">{item.job_title}</p>

              {/* Детали */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center text-sm text-gray-600">
                  <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                  {formatDate(item.evaluation_date)}
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <Award className="w-4 h-4 mr-2 text-gray-400" />
                  {item.grade_name} • {item.department_name}
                </div>
              </div>

              {/* Период */}
              <div className="pt-4 border-t border-gray-100">
                <div className="flex items-center text-xs text-gray-500">
                  <Calendar className="w-3 h-3 mr-1" />
                  Период:
                  <span className="ml-1 font-medium text-indigo-600">
                    {item.period_name || 'Не указан'}
                  </span>
                </div>
              </div>

              {/* Hover эффект */}
              <div className="mt-4 text-sm text-indigo-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                Посмотреть детали →
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Модальное окно с деталями */}
      {isModalOpen && selectedEvaluation && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            
            {/* Header модалки */}
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white p-6 flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                  <User className="w-8 h-8" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold mb-1">
                    {selectedEvaluation.evaluatee_name}
                  </h2>
                  <p className="text-indigo-100 text-sm">{selectedEvaluation.job_title}</p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-indigo-200 mb-1">
                  {formatDate(selectedEvaluation.evaluation_date)}
                </div>
                <div className="flex items-center gap-2 text-sm text-indigo-100">
                  {selectedEvaluation.period_name && (
                    <>
                      <span>•</span>
                      <span className="text-indigo-600 font-medium">{selectedEvaluation.period_name}</span>
                    </>
                  )}
                </div>
              </div>
              <button 
                onClick={handleCloseModal}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-6 h-6 text-gray-400" />
              </button>
            </div>

            {/* Body модалки */}
            <div className="p-6">
              {loadingDetails ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
                </div>
              ) : evaluationDetails ? (
                <>
                  {/* Итоговый балл */}
                  <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-6 mb-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-600 mb-1">Итоговый балл</div>
                        <div className="text-4xl font-bold text-indigo-600">
                          {parseFloat(evaluationDetails.evaluation.final_score).toFixed(2)}
                        </div>
                      </div>
                      <div className="p-4 bg-white/50 rounded-full">
                        <Star className="w-12 h-12 text-indigo-600" />
                      </div>
                    </div>
                  </div>

                  {/* Информация о сотруднике */}
                  <div className="bg-gray-50 rounded-xl p-6 mb-6">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <User className="w-5 h-5 text-gray-600" />
                      Информация о сотруднике
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-gray-500">Должность</div>
                        <div className="font-medium text-gray-900">
                          {evaluationDetails.evaluation.job_title || 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Отдел</div>
                        <div className="font-medium text-gray-900">
                          {evaluationDetails.evaluation.department || 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Грейд</div>
                        <div className="font-medium text-gray-900">
                          {evaluationDetails.evaluation.grade || 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Категория работы</div>
                        <div className="font-medium text-gray-900 capitalize">
                          {evaluationDetails.evaluation.work_category || 'N/A'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Детализация по критериям */}
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-gray-600" />
                      Детализация по критериям
                    </h3>
                    {evaluationDetails.scores && evaluationDetails.scores.length > 0 ? (
                      <div className="space-y-4">
                        {evaluationDetails.scores.map((score, index) => (
                          <div 
                            key={index}
                            className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-200 transition-colors"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="font-medium text-gray-900 mb-1">
                                  {score.criteria_title}
                                </div>
                                {score.criteria_description && (
                                  <div className="text-sm text-gray-500 mb-2">
                                    {score.criteria_description}
                                  </div>
                                )}
                              </div>
                              <div className="ml-4">
                                <div className="text-2xl font-bold text-indigo-600">
                                  {score.score_value}
                                </div>
                                <div className="text-xs text-gray-500 text-right">из 10</div>
                              </div>
                            </div>
                            
                            <div className="mt-3">
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className="bg-indigo-600 h-2 rounded-full transition-all"
                                  style={{ width: `${(score.score_value / 10) * 100}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        Детальные оценки отсутствуют
                      </div>
                    )}
                  </div>

                  {/* Комментарии (если есть) */}
                  {(evaluationDetails.evaluation.general_comment || evaluationDetails.evaluation.private_comment) && (
                    <div className="mt-6 bg-amber-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-900 mb-3">Комментарии</h3>
                      
                      {evaluationDetails.evaluation.general_comment && (
                        <div className="mb-3">
                          <div className="text-sm text-gray-500 mb-1">Общий комментарий:</div>
                          <div className="text-gray-700">{evaluationDetails.evaluation.general_comment}</div>
                        </div>
                      )}
                      
                      {evaluationDetails.evaluation.private_comment && (
                        <div>
                          <div className="text-sm text-gray-500 mb-1">Приватный комментарий:</div>
                          <div className="text-gray-700">{evaluationDetails.evaluation.private_comment}</div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  Не удалось загрузить детали оценки
                </div>
              )}
            </div>

            {/* Footer модалки */}
            <div className="p-6 border-t border-gray-100 bg-gray-50 sticky bottom-0">
              <button
                onClick={handleCloseModal}
                className="w-full py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EvaluationHistory;