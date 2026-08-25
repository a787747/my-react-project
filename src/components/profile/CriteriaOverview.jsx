/**
 * CriteriaOverview - Обзор критериев оценки
 * 
 * Назначение: Отображение критериев по категориям (самооценка, менеджер, C-level)
 * Используется в: Profile
 * 
 * Props:
 * - criteria: array - все критерии
 * - user: object - текущий пользователь
 */

import React, { useMemo, useState } from 'react';
import { CheckCircle, Circle, Star, User, Shield, Users, ChevronDown, ChevronUp, Wrench } from 'lucide-react';

// Компонент для отображения одного критерия с описаниями уровней
const CriterionItem = ({ criterion, showLevelDescriptions = true }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Получаем все описания уровней от 1 до 10
  const levelDescriptions = [];
  for (let i = 1; i <= 10; i++) {
    const desc = criterion[`level_${i}_desc`];
    if (desc) {
      levelDescriptions.push({ level: i, description: desc });
    }
  }

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
      <div className="flex items-start gap-3 p-3">
        <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="text-base font-semibold text-gray-900 mb-1 leading-normal">
            {criterion.title}
          </div>
          {criterion.description && (
            <div className="text-sm text-gray-600 mb-2 leading-normal">
              {criterion.description}
            </div>
          )}
          {showLevelDescriptions && levelDescriptions.length > 0 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-2 text-sm leading-normal text-blue-600 hover:text-blue-700 font-medium mt-2 transition-colors"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Скрыть описания уровней
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Показать описания уровней (1-10)
                </>
              )}
            </button>
          )}
        </div>
      </div>
      
      {/* Описания уровней */}
      {showLevelDescriptions && isExpanded && levelDescriptions.length > 0 && (
        <div className="px-3 pb-3 pt-0 border-t border-gray-200 mt-2">
          <div className="space-y-2 mt-3">
            {levelDescriptions.map(({ level, description }) => (
              <div
                key={level}
                className="flex gap-3 p-2 bg-white rounded border border-gray-100"
              >
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                  <span className="text-xs font-bold text-blue-700">{level}</span>
                </div>
                <div className="flex-1 text-sm text-gray-700 leading-normal">
                  {description}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const CriteriaOverview = ({ criteria, user }) => {
  const upwardCriterionTitle = useMemo(() => {
    const row = Array.isArray(criteria)
      ? criteria.find((criterion) => Number(criterion.id) === 2)
      : null;
    return row?.title || 'Качество управления и развитие команды';
  }, [criteria]);

  // Разделяем критерии по категориям
  const categorizedCriteria = useMemo(() => {
    if (!criteria || !Array.isArray(criteria) || criteria.length === 0) {
      return {
        selfAssessment: [],
        manager: [],
        cLevel: [],
        management: [],
        projectParticipants: []
      };
    }

    const selfAssessment = [];
    const manager = [];
    const cLevel = [];
    const management = [];
    const projectParticipants = [];

    criteria.forEach(criterion => {
      // Проверка активности (поддерживаем разные форматы: boolean, string, number)
      const isActive = criterion.is_active === true || 
                       criterion.is_active === 'true' || 
                       criterion.is_active === 1 ||
                       criterion.is_active === '1';
      if (!isActive) return;

      // Проверка целевой аудитории
      const audience = (criterion.target_audience?.toLowerCase() || 'all').trim();
      const category = (user?.work_category?.toLowerCase() || 'general').trim();
      
      // Критерии только для менеджеров (managers_only)
      if (audience === 'managers_only') {
        // Показываем только если пользователь является менеджером (has_subordinates)
        if (user?.has_subordinates) {
          management.push(criterion);
        }
        return; // Не добавляем в другие категории
      }
      
      // Критерии для участников проектов (project_participants)
      if (audience === 'project_participants') {
        const isProjectParticipant = user?.is_project_participant === true || 
                                      user?.is_project_participant === 'true' || 
                                      user?.is_project_participant === 1 ||
                                      user?.is_project_participant === '1';
        if (isProjectParticipant) {
          projectParticipants.push(criterion);
        }
        return; // Не добавляем в другие категории
      }
      
      // Проверка соответствия аудитории
      const matchesAudience = audience === 'all' || audience === category;

      if (!matchesAudience) return;

      // Критерии для самооценки (поддерживаем разные форматы)
      const isSelfAssessment = criterion.selfassesment === true || 
                                 criterion.selfassesment === 'true' || 
                                 criterion.selfassesment === 1 ||
                                 criterion.selfassesment === '1';
      if (isSelfAssessment) {
        selfAssessment.push(criterion);
        // Критерии самооценки также используются менеджером
        manager.push(criterion);
      }

      // Дополнительные критерии для менеджера (не selfassesment и не c_level_only)
      const isCLevelOnly = criterion.c_level_only === true || 
                           criterion.c_level_only === 'true' || 
                           criterion.c_level_only === 1 ||
                           criterion.c_level_only === '1';
      const isForManager = criterion.for_manager === true || 
                           criterion.for_manager === 'true' || 
                           criterion.for_manager === 1 ||
                           criterion.for_manager === '1' ||
                           criterion.for_manager === undefined; // Если поле не задано, считаем что для менеджера
      
      // Добавляем дополнительные критерии для менеджера (которые не входят в самооценку)
      if (!isSelfAssessment && !isCLevelOnly && isForManager) {
        manager.push(criterion);
      }

      // Критерии для C-level
      if (isCLevelOnly) {
        cLevel.push(criterion);
      }
    });

    // Убираем дубликаты из критериев менеджера (на случай если критерий был добавлен дважды)
    const uniqueManagerCriteria = manager.filter((criterion, index, self) => 
      index === self.findIndex((c) => c.id === criterion.id)
    );

    return {
      selfAssessment,
      manager: uniqueManagerCriteria,
      cLevel,
      management,
      projectParticipants
    };
  }, [criteria, user]);

  const renderCriteriaList = (criteriaList, Icon, title, description, showLevelDescriptions = true) => {
    if (criteriaList.length === 0) {
      return (
        <div className="bg-white rounded-xl shadow-sm p-6 border-2 border-gray-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
              <Icon className="w-6 h-6 text-gray-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg md:text-lg font-bold text-gray-800 mb-1 leading-normal">{title}</h3>
              <p className="text-sm text-gray-600 mb-3 leading-normal">{description}</p>
              <p className="text-sm text-gray-500 italic leading-normal">Нет критериев для отображения</p>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-white rounded-xl shadow-sm p-6 border-2 border-blue-200">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
            <Icon className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg md:text-lg font-bold text-gray-800 mb-1 leading-normal">{title}</h3>
            <p className="text-sm text-gray-600 leading-normal">{description}</p>
          </div>
        </div>
        <div className="space-y-3">
          {criteriaList.map((criterion) => (
            <CriterionItem key={criterion.id} criterion={criterion} showLevelDescriptions={showLevelDescriptions} />
          ))}
        </div>
      </div>
    );
  };

  // Проверяем, есть ли хотя бы одна категория с критериями
  const hasAnyCriteria = categorizedCriteria.selfAssessment.length > 0 ||
    categorizedCriteria.manager.length > 0 ||
    categorizedCriteria.cLevel.length > 0 ||
    categorizedCriteria.management.length > 0 ||
    categorizedCriteria.projectParticipants.length > 0;

  return (
    <div className="space-y-6 mb-8">
      <div className="mb-6">
        <h2 className="text-2xl md:text-2xl font-bold text-gray-800 mb-2 leading-normal">
          Критерии оценки
        </h2>
        <p className="text-sm text-gray-600 leading-normal">
          Ниже представлены критерии, по которым вы оцениваетесь в системе
        </p>
      </div>

      {/* Если нет критериев вообще */}
      {!hasAnyCriteria && criteria && criteria.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
          <p className="text-yellow-800">
            <strong>Внимание:</strong> Критерии загружены, но не найдено активных критериев, соответствующих вашей категории работы.
          </p>
          <p className="text-sm text-yellow-700 mt-2">
            Всего загружено критериев: {criteria.length}
          </p>
        </div>
      )}

      {/* Если критерии не загружены */}
      {(!criteria || criteria.length === 0) && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
          <p className="text-gray-600">
            Критерии оценки загружаются...
          </p>
        </div>
      )}

      {/* Критерии для самооценки */}
      {renderCriteriaList(
        categorizedCriteria.selfAssessment,
        Star,
        'Критерии для самооценки',
        'Эти критерии вы используете для самостоятельной оценки своей работы'
      )}

      {/* Критерии для менеджера */}
      {renderCriteriaList(
        categorizedCriteria.manager,
        User,
        'Критерии для оценки менеджером',
        'Менеджер оценивает вас по тем же критериям по которым вы оценили себя самостоятельно и также по дополнительным критериям'
      )}

      {/* Критерии для C-level */}
      {renderCriteriaList(
        categorizedCriteria.cLevel,
        Shield,
        'Критерии для оценки C-level',
        'По этим критериям вас оценивает руководство компании',
        false
      )}

      {/* Критерии управления (для менеджеров) */}
      {user?.has_subordinates && renderCriteriaList(
        categorizedCriteria.management,
        Users,
        'Критерии качества управления',
        `По этим критериям вас оценивают ваши подчиненные и руководство. Руководители (сотрудники, у которых есть прямые подчиненные) также будут оценены по критерию «${upwardCriterionTitle}». Оценка проводится каждым сотрудником отдела и непосредственным руководителем оцениваемого менеджера.`
      )}

      {/* Критерии для участников проектов (полевые работы) */}
      {categorizedCriteria.projectParticipants.length > 0 && renderCriteriaList(
        categorizedCriteria.projectParticipants,
        Wrench,
        'Критерии для участников проектов',
        'Только для сотрудников, напрямую работавших в полях за пределами офиса при установке оборудования. По этим критериям вас оценивает руководитель проекта.'
      )}
    </div>
  );
};

export default CriteriaOverview;

