/**
 * Экспорт всех админских компонентов
 * 
 * Использование:
 * import { UserTable, UserFilters, UserModal, CriteriaTable } from '../components/admin';
 */

// Компоненты для управления пользователями
export { default as UserTable } from './UserTable';
export { default as UserFilters } from './UserFilters';
export { default as UserModal } from './UserModal';
export { default as UserImportModal } from './UserImportModal';

// Компоненты для управления критериями
export { default as CriteriaTable } from './CriteriaTable';
export { default as CriteriaForm } from './CriteriaForm';
export { default as RoleCheckbox } from './RoleCheckbox';
export { default as LevelDescriptions } from './LevelDescriptions';

// Компоненты для матрицы оценок
export { default as MatrixFilters } from './MatrixFilters';
export { default as EvaluationsMatrixTable } from './EvaluationsMatrixTable';
export { default as CLevelEvaluationModal } from './CLevelEvaluationModal';

// Компоненты для всех оценок
export { default as AllEvaluationsTable } from './AllEvaluationsTable';
export { default as AllEvaluationsDetailsModal } from './AllEvaluationsDetailsModal';

// Компоненты для управления коэффициентами оценок
export { default as ScoringCoefficientsTable } from './ScoringCoefficientsTable';
export { default as CoefficientRow } from './CoefficientRow';

// Компоненты для итоговых баллов
export { default as FinalScoresMatrixTable } from './FinalScoresMatrixTable';

// Компоненты для калькуляции баллов
export { default as EmployeeSelector } from './EmployeeSelector';
export { default as CalculationCard } from './CalculationCard';
