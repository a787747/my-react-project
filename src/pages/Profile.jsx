import React, { useState, useEffect } from 'react';
import { User, TrendingUp, Calendar, Award, Eye } from 'lucide-react';
import axios from 'axios';

const API_MY_PROFILE = 'http://92.51.45.147:5678/webhook/api/my-profile';
const API_EVALUATION_DETAILS = 'http://92.51.45.147:5678/webhook/api/evaluation-details';

const Profile = () => {
  const [user, setUser] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedEvaluation, setSelectedEvaluation] = useState(null);
  const [evaluationDetails, setEvaluationDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    setUser(userData);
    if (userData) {
      fetchProfileData(userData.id);
    }
  }, []);

  const fetchProfileData = async (userId) => {
    try {
      setLoading(true);
      setError(false);
      const response = await axios.get(`${API_MY_PROFILE}?user_id=${userId}`);
      setProfileData(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const fetchEvaluationDetails = async (evaluationId) => {
    try {
      setDetailsLoading(true);
      const response = await axios.get(`${API_EVALUATION_DETAILS}?evaluation_id=${evaluationId}`);
      setEvaluationDetails(response.data);
    } catch (error) {
      console.error('Error fetching evaluation details:', error);
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleViewDetails = (evaluation) => {
    setSelectedEvaluation(evaluation);
    fetchEvaluationDetails(evaluation.evaluation_id);
  };

  const closeModal = () => {
    setSelectedEvaluation(null);
    setEvaluationDetails(null);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Загрузка профиля...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-red-600">Ошибка загрузки данных. Попробуйте обновить страницу.</div>
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Нет данных профиля</div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Мой профиль</h1>
        <p className="text-gray-600">
          {user?.full_name} • {user?.job_title}
        </p>
      </div>

      {/* Stats Cards */}
      {profileData.has_evaluations ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Latest Score */}
            <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-blue-500">
              <div className="flex items-center justify-between mb-2">
                <Award className="w-8 h-8 text-blue-500" />
                <span className="text-sm text-gray-500">Последняя</span>
              </div>
              <div className="text-3xl font-bold text-gray-800">
                {profileData.stats.latest_score}
              </div>
              <div className="text-sm text-gray-600 mt-1">
                {profileData.stats.latest_period}
              </div>
            </div>

            {/* Average Score */}
            <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-green-500">
              <div className="flex items-center justify-between mb-2">
                <TrendingUp className="w-8 h-8 text-green-500" />
                <span className="text-sm text-gray-500">Средний балл</span>
              </div>
              <div className="text-3xl font-bold text-gray-800">
                {profileData.stats.average_score}
              </div>
              <div className="text-sm text-gray-600 mt-1">
                За все периоды
              </div>
            </div>

            {/* Total Evaluations */}
            <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-purple-500">
              <div className="flex items-center justify-between mb-2">
                <Calendar className="w-8 h-8 text-purple-500" />
                <span className="text-sm text-gray-500">Всего оценок</span>
              </div>
              <div className="text-3xl font-bold text-gray-800">
                {profileData.stats.total_evaluations}
              </div>
              <div className="text-sm text-gray-600 mt-1">
                Периодов оценки
              </div>
            </div>

            {/* Last Updated */}
            <div className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-orange-500">
              <div className="flex items-center justify-between mb-2">
                <User className="w-8 h-8 text-orange-500" />
                <span className="text-sm text-gray-500">Последнее обновление</span>
              </div>
              <div className="text-sm font-semibold text-gray-800 mt-2">
                {formatDate(profileData.stats.latest_date)}
              </div>
            </div>
          </div>

          {/* Chart (if 2+ evaluations) */}
          {profileData.evaluations.length >= 2 && (
            <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
              <h2 className="text-xl font-bold text-gray-800 mb-4">
                Динамика оценок
              </h2>
              <div className="h-64 flex items-end justify-around space-x-2">
                {profileData.evaluations.slice().reverse().map((evaluation, index) => {
                  const maxScore = 10;
                  const heightPercent = (parseFloat(evaluation.score) / maxScore) * 100;
                  
                  return (
                    <div key={index} className="flex flex-col items-center flex-1">
                      <div className="w-full bg-gray-200 rounded-t-lg relative" style={{ height: '200px' }}>
                        <div 
                          className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t-lg absolute bottom-0 flex items-center justify-center text-white font-bold transition-all duration-500"
                          style={{ height: `${heightPercent}%` }}
                        >
                          {evaluation.score}
                        </div>
                      </div>
                      <div className="text-xs text-gray-600 mt-2 text-center">
                        {evaluation.period_name}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* History Table */}
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-800">
                История оценок
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Период
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Оценка
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Оценил
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Дата
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {profileData.evaluations.map((evaluation) => (
                    <tr key={evaluation.evaluation_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                          {evaluation.period_name}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-2xl font-bold text-gray-900">
                          {evaluation.score}
                        </span>
                        <span className="text-sm text-gray-500 ml-1">/10</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {evaluation.evaluator_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {evaluation.evaluator_title}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {formatDate(evaluation.updated_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => handleViewDetails(evaluation)}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                          Детали
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* No Evaluations State */
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

      {/* Details Modal */}
      {selectedEvaluation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6 z-10">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-2xl font-bold text-gray-800">
                    Детали оценки
                  </h3>
                  <p className="text-gray-600 mt-1">
                    {selectedEvaluation.period_name} • {formatDate(selectedEvaluation.updated_at)}
                  </p>
                </div>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600 text-3xl leading-none"
                >
                  ×
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6">
              {detailsLoading ? (
                <div className="text-center py-8">
                  <div className="text-gray-600">Загрузка деталей...</div>
                </div>
              ) : evaluationDetails ? (
                <>
                  {/* Summary */}
                  <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 mb-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-gray-600 mb-1">Итоговая оценка</div>
                        <div className="text-4xl font-bold text-gray-800">
                          {evaluationDetails.evaluation.calculated_score}
                        </div>
                      </div>
                      <Award className="w-16 h-16 text-blue-500" />
                    </div>
                  </div>

                  {/* Criteria Breakdown */}
                  <div className="space-y-4">
                    <h4 className="text-lg font-bold text-gray-800 mb-4">
                      Оценка по критериям
                    </h4>
                    {evaluationDetails.scores.map((score, index) => (
                      <div key={index} className="border-b border-gray-200 pb-4">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-medium text-gray-800">
                            {score.criteria_title}
                          </span>
                          <span className="text-xl font-bold text-blue-600">
                            {score.score_value}/10
                          </span>
                        </div>
                        {/* Progress Bar */}
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
                            style={{ width: `${(score.score_value / 10) * 100}%` }}
                          />
                        </div>
                        {score.criteria_description && (
                          <p className="text-sm text-gray-600 mt-2">
                            {score.criteria_description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-red-600">
                  Ошибка загрузки деталей
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6">
              <button
                onClick={closeModal}
                className="w-full bg-gray-600 text-white py-3 rounded-lg hover:bg-gray-700 transition-colors font-medium"
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

export default Profile;