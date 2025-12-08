import React, { useState } from 'react';
import axios from 'axios';
import { User, Loader2 } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import EmployeeCard from '../components/EmployeeCard';
import EvaluationModal from '../components/EvaluationModal';
import { API_ENDPOINTS } from '../config/api';

const Dashboard = ({ user }) => {
  const {
    employees,
    criteria,
    evaluatedDetails,
    selfReviewsStatus,
    loading,
    setEvaluatedDetails
  } = useDashboardData(user);

  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);

  const handleOpenEvaluation = (employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(false);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (employee) => {
    setSelectedEmployee(employee);
    setIsEditMode(true);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedEmployee(null);
  };

  const handleEvaluationSuccess = async () => {
    // Обновляем данные об оцененных сотрудниках
    try {
      const evaluatedRes = await axios.get(API_ENDPOINTS.CHECK_EVALUATED, {
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
      console.error('Ошибка обновления данных:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

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

              return (
                <EmployeeCard
                  key={emp.id}
                  employee={emp}
                  isEvaluated={!!isEvaluated}
                  lastScore={lastScore}
                  hasSelfReview={hasSelfReview}
                  selfReviewScore={selfReviewScore}
                  onEvaluate={handleOpenEvaluation}
                  onEdit={handleOpenEdit}
                />
              );
            })}
          </div>
        )}
      </div>

      <EvaluationModal
        isOpen={isModalOpen}
        employee={selectedEmployee}
        criteria={criteria}
        isEditMode={isEditMode}
        evaluatedDetails={evaluatedDetails}
        user={user}
        onClose={handleCloseModal}
        onSuccess={handleEvaluationSuccess}
      />
    </div>
  );
};

export default Dashboard;
