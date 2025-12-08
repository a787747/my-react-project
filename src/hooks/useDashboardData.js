import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_ENDPOINTS } from '../config/api';

export const useDashboardData = (user) => {
  const [employees, setEmployees] = useState([]);
  const [criteria, setCriteria] = useState([]);
  const [evaluatedDetails, setEvaluatedDetails] = useState({});
  const [selfReviewsStatus, setSelfReviewsStatus] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;

      try {
        setLoading(true);

        const [employeesRes, criteriaRes] = await Promise.all([
          axios.get(API_ENDPOINTS.GET_EMPLOYEES, {
            params: { user_id: user.id, role: user.role }
          }),
          axios.get(API_ENDPOINTS.GET_CRITERIA)
        ]);

        console.log('📥 Employees API response:', employeesRes.data);
        console.log('📥 Criteria API response:', criteriaRes.data);

        const employeesData = Array.isArray(employeesRes.data) 
          ? employeesRes.data[0]?.data || [] 
          : employeesRes.data.data || [];

        const criteriaData = Array.isArray(criteriaRes.data)
          ? criteriaRes.data[0]?.data || []
          : criteriaRes.data.data || [];

        console.log('👥 RAW employeesRes.data:', employeesRes.data);
        console.log('👥 Parsed employeesData:', employeesData);

        setEmployees(employeesData);
        setCriteria(criteriaData);
        
        console.log('✅ Установлено сотрудников:', employeesData.length);

        // Загружаем evaluated details
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
        } catch (err) {
          console.log('Не удалось загрузить оценки:', err.message);
        }

        // Загружаем self reviews
        try {
          const selfReviewsRes = await axios.get(API_ENDPOINTS.CHECK_SELF_REVIEWS_STATUS);
          console.log('⭐ Self reviews API response:', selfReviewsRes.data);
          const selfReviews = selfReviewsRes.data.data || {};
          setSelfReviewsStatus(selfReviews);
          console.log('⭐ Parsed self reviews:', selfReviews);
        } catch (err) {
          console.log('Не удалось загрузить самооценки:', err.message);
        }

      } catch (error) {
        console.error('Ошибка загрузки данных:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  return {
    employees,
    criteria,
    evaluatedDetails,
    selfReviewsStatus,
    loading,
    setEvaluatedDetails
  };
};

