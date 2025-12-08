import React from 'react';
import { Star } from 'lucide-react';

const CriterionSlider = ({ criterion, value, onChange, employeeSelfReview }) => {
  const selfReviewScore = employeeSelfReview?.has_self_review 
    ? employeeSelfReview.scores[criterion.id] 
    : undefined;

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-end">
        <label className="text-base font-medium text-gray-800">
          {criterion.title}
        </label>
        <span className="text-2xl font-bold text-indigo-600 w-12 text-right">
          {value ?? 0}
        </span>
      </div>
      <p className="text-sm text-gray-500">{criterion.description}</p>
      
      <input
        type="range"
        min="0"
        max="10"
        step="1"
        value={value ?? 0}
        onChange={(e) => onChange(criterion.title, e.target.value)}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 hover:accent-indigo-700"
      />
      <div className="flex justify-between text-xs text-gray-400 font-medium">
        <span>Плохо (0)</span>
        <span>Отлично (10)</span>
      </div>
      
      {selfReviewScore !== undefined && (
        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-900 font-medium flex items-center gap-2">
              <Star className="w-4 h-4 text-blue-600" />
              Самооценка сотрудника:
            </span>
            <span className="text-lg font-bold text-blue-600">
              {selfReviewScore}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CriterionSlider;

