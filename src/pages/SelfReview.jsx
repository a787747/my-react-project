import { useState, useEffect } from 'react';
import { User, Star, CheckCircle } from 'lucide-react';
import axios from 'axios';

const API_GET_CRITERIA = 'http://92.51.45.147:5678/webhook/api/criteria';
const API_SUBMIT_SELF_REVIEW = 'http://92.51.45.147:5678/webhook/api/submit-self-review';
const API_CHECK_SELF_REVIEW = 'http://92.51.45.147:5678/webhook/api/check-self-review';

// Функция для получения цвета зоны
const getScoreZone = (score) => {
  if (score <= 3) return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'Зона риска' };
  if (score <= 6) return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', label: 'Зона нормы' };
  if (score <= 8) return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', label: 'Зона роста' };
  return { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', label: 'Зона исключительности' };
};

// Функция для получения описания уровня из критерия
const getLevelDescription = (criterion, level) => {
  const fieldName = `level_${level}_desc`;
  return criterion[fieldName] || `Оценка ${level} из 10`;
};

const SelfReview = () => {
  const user = JSON.parse(localStorage.getItem('user'));
  const [criteria, setCriteria] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasReview, setHasReview] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [grades, setGrades] = useState({});
  const [generalComment, setGeneralComment] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Проверяем есть ли уже самооценка
      const checkRes = await axios.get(`${API_CHECK_SELF_REVIEW}?user_id=${user.id}`);
      
      if (checkRes.data.has_self_review) {
        setHasReview(true);
        setReviewData(checkRes.data);
      }

      // Загружаем критерии
      const criteriaRes = await axios.get(API_GET_CRITERIA);
      console.log('📥 RAW response:', criteriaRes.data);
      
      // n8n возвращает массив [{success: true, data: [...]}]
      const responseData = Array.isArray(criteriaRes.data) ? criteriaRes.data[0] : criteriaRes.data;
      console.log('📦 Parsed responseData:', responseData);
      const allCriteria = responseData?.data || [];
      console.log('📋 Всего критериев:', allCriteria.length, allCriteria);

      // Фильтруем критерии по категории сотрудника
      const filtered = allCriteria.filter(c => {
        const isActive = c.is_active === true;
        const audience = c.target_audience?.toLowerCase() || 'all';
        const category = user.work_category?.toLowerCase() || 'general';
        return isActive && (audience === 'all' || audience === category);
      });

      setCriteria(filtered);

      // Инициализируем оценки
      const initialGrades = {};
      filtered.forEach(c => {
        initialGrades[c.id] = 5;
      });
      setGrades(initialGrades);

    } catch (error) {
      console.error('Error loading data:', error);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const handleSliderChange = (criteriaId, value) => {
    setGrades(prev => ({
      ...prev,
      [criteriaId]: parseInt(value)
    }));
  };

  const handleSubmit = async () => {
    try {
      // Считаем средний балл
      const scores = Object.values(grades);
      const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;

      // Применяем коэффициент грейда
      const gradeCoef = user.grade_coefficient || 1.0;
      const finalScore = (average * gradeCoef).toFixed(2);

      const payload = {
        user_id: user.id,
        final_score: parseFloat(finalScore),
        grades: grades,
        general_comment: generalComment,
        private_comment: ''
      };

      await axios.post(API_SUBMIT_SELF_REVIEW, payload);

      alert('Самооценка сохранена успешно!');
      setIsModalOpen(false);
      loadData(); // Обновляем данные
    } catch (error) {
      console.error('Error submitting self-review:', error);
      alert('Ошибка при сохранении самооценки');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Самооценка</h1>
          <p className="text-gray-600">Оцените свою работу в текущем периоде</p>
        </div>

        {/* Status Card */}
        {hasReview ? (
          <div className="bg-green-50 border-2 border-green-200 rounded-xl p-6 mb-6">
            <div className="flex items-start gap-4">
              <CheckCircle className="w-8 h-8 text-green-600 flex-shrink-0 mt-1" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-green-900 mb-2">
                  Вы уже оценили себя в этом периоде
                </h3>
                <div className="space-y-1 text-green-700">
                  <p>Оценка: <span className="font-bold text-xl">{reviewData.score}</span></p>
                  <p className="text-sm">
                    Дата: {new Date(reviewData.date).toLocaleDateString('ru-RU')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                <User className="w-8 h-8 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900">{user.full_name}</h3>
                <p className="text-gray-600">{user.job_title || 'Сотрудник'}</p>
              </div>
            </div>

            <button
              onClick={() => setIsModalOpen(true)}
              className="w-full mt-4 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all flex items-center justify-center gap-2"
            >
              <Star className="w-5 h-5" />
              Оценить себя
            </button>
          </div>
        )}

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
          <h3 className="font-semibold text-blue-900 mb-2">💡 Как это работает?</h3>
          <ul className="space-y-2 text-blue-800 text-sm">
            <li>• Оцените себя по каждому критерию от 0 до 10</li>
            <li>• Ваша оценка будет видна вашему менеджеру</li>
            <li>• Менеджер сможет сравнить вашу оценку со своей</li>
            <li>• Это поможет лучше понять ожидания и результаты</li>
          </ul>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 rounded-t-2xl">
              <h2 className="text-2xl font-bold mb-2">Самооценка</h2>
              <p className="text-blue-100">{user.full_name}</p>
            </div>

            <div className="p-6 space-y-6">
              {criteria.map((criterion) => (
                <div key={criterion.id} className="border-b border-gray-200 pb-6 last:border-0">
                  <div className="mb-3">
                    <h3 className="font-semibold text-gray-900 mb-1">{criterion.title}</h3>
                    {criterion.description && (
                      <p className="text-sm text-gray-600">{criterion.description}</p>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-4 mb-4">
                    <input
                      type="range"
                      min="0"
                      max="10"
                      value={grades[criterion.id] ?? 5}
                      onChange={(e) => handleSliderChange(criterion.id, e.target.value)}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                    />
                    <div className="w-16 text-center">
                      <span className="text-2xl font-bold text-blue-600">
                        {grades[criterion.id] ?? 5}
                      </span>
                      <span className="text-gray-400 text-sm">/10</span>
                    </div>
                  </div>

                  {/* Динамическое описание уровня */}
                  {(() => {
                    const currentScore = grades[criterion.id] ?? 5;
                    const zone = getScoreZone(currentScore);
                    return (
                      <div className={`${zone.bg} ${zone.border} border rounded-lg p-4 transition-all`}>
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0">
                            <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${zone.text} bg-white`}>
                              {zone.label}
                            </span>
                          </div>
                          <p className={`text-sm ${zone.text} leading-relaxed`}>
                            {getLevelDescription(criterion, currentScore)}
                          </p>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ))}

              {/* Comment */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Общий комментарий (необязательно)
                </label>
                <textarea
                  value={generalComment}
                  onChange={(e) => setGeneralComment(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows="3"
                  placeholder="Что бы вы хотели отметить о своей работе?"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                >
                  Отмена
                </button>
                <button
                  onClick={handleSubmit}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all"
                >
                  Сохранить оценку
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SelfReview;