import React from 'react';
import { Briefcase, Award, ChevronRight, Star, CheckCircle, Edit } from 'lucide-react';

const EmployeeCard = ({ employee, isEvaluated, lastScore, hasSelfReview, selfReviewScore, onEvaluate, onEdit }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg transition-all">
      <div className="flex items-start justify-between mb-4">
        <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-2xl">
          {employee.full_name?.charAt(0) || 'U'}
        </div>
        
        <div className="flex flex-col items-end gap-2">
          {hasSelfReview && selfReviewScore != null && (
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
      
      <h3 className="text-lg font-semibold text-gray-900">{employee.full_name}</h3>
      <p className="text-gray-500 text-sm mb-4">{employee.job_title}</p>
      
      <div className="space-y-2 mb-6">
        <div className="flex items-center text-sm text-gray-600">
          <Briefcase className="w-4 h-4 mr-2" />
          {employee.department_name || 'No Dept'}
        </div>
        <div className="flex items-center text-sm text-gray-600">
          <Award className="w-4 h-4 mr-2" />
          Grade: {employee.grade_code || 'N/A'}
        </div>
      </div>

      <button 
        onClick={() => isEvaluated ? onEdit(employee) : onEvaluate(employee)}
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
};

export default EmployeeCard;

