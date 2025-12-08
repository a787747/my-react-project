import React from 'react';
import { CheckCircle } from 'lucide-react';

const SelfReviewBanner = ({ employeeSelfReview }) => {
  if (!employeeSelfReview?.has_self_review) return null;

  return (
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
  );
};

export default SelfReviewBanner;

