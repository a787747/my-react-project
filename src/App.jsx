/**
 * App.jsx - Главный компонент приложения
 * 
 * Назначение: Маршрутизация, авторизация и layout приложения
 * 
 * Роутинг:
 * - / - Dashboard (для авторизованных)
 * - /login - Страница входа
 * - /history - История оценок
 * - /profile - Профиль пользователя
 * - /self-review - Самооценка
 * - /analytics - Аналитика (admin, c_level)
 * - /admin/* - Админские страницы
 * 
 * Code Splitting:
 * - Login загружается сразу (нужен для входа)
 * - Остальные страницы загружаются лениво (React.lazy)
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { UserProvider, useUser } from './context/UserContext';
import { TaskStatusProvider } from './context/TaskStatusContext';
import { ToastProvider } from './context/ToastContext';
import Sidebar from './components/Sidebar';
import SessionExpiryWarning from './components/SessionExpiryWarning';
import { LoadingSpinner } from './components/common';
import { canAccessAdminPanel, canViewAnalytics, isManagerOrAbove, isHR } from './utils/permissions';

// Eager loading - страницы нужны сразу
import Login from './pages/Login';

// Lazy loading - страницы загружаются по требованию
const Register = lazy(() => import('./pages/Register'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const EvaluationHistory = lazy(() => import('./pages/EvaluationHistory'));
const Profile = lazy(() => import('./pages/Profile'));
const SelfReview = lazy(() => import('./pages/SelfReview'));
const Analytics = lazy(() => import('./pages/Analytics'));
const AdminUsers = lazy(() => import('./pages/AdminUsers'));
const AdminPeriods = lazy(() => import('./pages/AdminPeriods'));
const AdminSettings = lazy(() => import('./pages/AdminSettings'));
const AdminScoring = lazy(() => import('./pages/AdminScoring'));
const AdminAllEvaluations = lazy(() => import('./pages/AdminAllEvaluations'));
const AdminEvaluationsMatrix = lazy(() => import('./pages/AdminEvaluationsMatrix'));
const AdminFinalScores = lazy(() => import('./pages/AdminFinalScores'));
const BonusCalculation = lazy(() => import('./pages/BonusCalculation'));
const AdminAnnualRollup = lazy(() => import('./pages/AdminAnnualRollup'));
const ManagerEvaluation = lazy(() => import('./pages/ManagerEvaluation'));
const ManagerSubordinatesMatrix = lazy(() => import('./pages/ManagerSubordinatesMatrix'));
const Welcome = lazy(() => import('./pages/Welcome'));
const HRDashboard = lazy(() => import('./pages/HRDashboard'));
const TeamView = lazy(() => import('./pages/TeamView'));
const AdminScoreCalculator = lazy(() => import('./pages/AdminScoreCalculator'));

const ProtectedRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

/**
 * AdminRoute - Доступ только для admin, c_level, hr
 * Используется для страниц управления пользователями, периодами, настройками
 */
const AdminRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!canAccessAdminPanel(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
};

/**
 * ManagerRoute - Доступ для менеджеров и выше
 * Используется для страницы просмотра команды (/team)
 */
const ManagerRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!isManagerOrAbove(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
};

const HRRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!isHR(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
};

/**
 * ReportingRoute — company-wide results: admin + c_level only.
 * HR keeps /hr/dashboard. URL access to analytics / all-evaluations / matrix is denied.
 */
const ReportingRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!canViewAnalytics(user.role)) {
    return <Navigate to={isHR(user.role) ? '/hr/dashboard' : '/welcome'} replace />;
  }
  return children;
};

/**
 * Внутренний компонент приложения, использующий контекст пользователя
 */
function AppContent() {
  const { user, loading } = useUser();

  // Показываем загрузку пока проверяем авторизацию
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner text="Загрузка..." />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-surface-raised">
      {user && <Sidebar user={user} />}
      {user && <SessionExpiryWarning />}
      <div className={user ? 'lg:ml-64 flex-1 min-h-screen' : 'flex-1 min-h-screen'}>
        <Suspense fallback={<LoadingSpinner text="Загрузка страницы..." />}>
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to={user.role === 'hr' ? '/hr/dashboard' : '/welcome'} replace /> : <Login />}
          />
          <Route
            path="/register"
            element={user ? <Navigate to={user.role === 'hr' ? '/hr/dashboard' : '/welcome'} replace /> : <Register />}
          />
          <Route
            path="/reset-password"
            element={<ResetPassword />}
          />
          <Route
            path="/welcome"
            element={
              <ProtectedRoute user={user}>
                <Welcome />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute user={user}>
                <Navigate to="/welcome" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute user={user}>
                <Dashboard user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute user={user}>
                <EvaluationHistory user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute user={user}>
                <Profile user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/self-review"
            element={
              <ProtectedRoute user={user}>
                <SelfReview user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/manager-evaluation"
            element={
              <ProtectedRoute user={user}>
                <ManagerEvaluation user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/team-scores"
            element={
              <ProtectedRoute user={user}>
                <ManagerSubordinatesMatrix user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ReportingRoute user={user}>
                <Analytics />
              </ReportingRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <AdminRoute user={user}>
                <AdminUsers user={user} />
              </AdminRoute>
            }
          />
          <Route
            path="/team"
            element={
              <ManagerRoute user={user}>
                <TeamView user={user} />
              </ManagerRoute>
            }
          />
          <Route
            path="/admin/periods"
            element={
              <AdminRoute user={user}>
                <AdminPeriods user={user} />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/all-evaluations"
            element={
              <ReportingRoute user={user}>
                <AdminAllEvaluations />
              </ReportingRoute>
            }
          />
          <Route
            path="/admin/evaluations-matrix"
            element={
              <ReportingRoute user={user}>
                <AdminEvaluationsMatrix user={user} />
              </ReportingRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <AdminRoute user={user}>
                <AdminSettings />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/scoring"
            element={
              <AdminRoute user={user}>
                <AdminScoring />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/final-scores"
            element={
              <AdminRoute user={user}>
                <AdminFinalScores user={user} />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/bonus-calculation"
            element={
              <AdminRoute user={user}>
                <BonusCalculation user={user} />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/annual-rollup"
            element={
              <ReportingRoute user={user}>
                <AdminAnnualRollup />
              </ReportingRoute>
            }
          />
          <Route
            path="/hr/dashboard"
            element={
              <HRRoute user={user}>
                <HRDashboard />
              </HRRoute>
            }
          />
          <Route
            path="/admin/score-calculator"
            element={
              <AdminRoute user={user}>
                <AdminScoreCalculator />
              </AdminRoute>
            }
          />
        </Routes>
        </Suspense>
      </div>
    </div>
  );
}

/**
 * Главный компонент приложения с провайдерами
 */
function App() {
  return (
    <Router>
      <UserProvider>
        <TaskStatusProvider>
          <ToastProvider>
            <AppContent />
          </ToastProvider>
        </TaskStatusProvider>
      </UserProvider>
    </Router>
  );
}

export default App;
