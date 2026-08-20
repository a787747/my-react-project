/**
 * Login - Страница авторизации
 * 
 * Назначение: Вход в систему по email и паролю
 * Доступ: Публичный
 * 
 * Функционал:
 * - Форма входа
 * - Сохранение пользователя в localStorage
 * - Редирект на главную после успешного входа
 * 
 * Accessibility:
 * - Семантическая разметка с form и labels
 * - ARIA-атрибуты для ошибок
 * - Focus management
 * - Правильные autocomplete атрибуты
 */

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Lock, Mail, Loader2, AlertCircle, HelpCircle, X, UserPlus, KeyRound } from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showForgotPasswordModal, setShowForgotPasswordModal] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState('');
  const [resetError, setResetError] = useState('');
  const emailInputRef = useRef(null);
  const errorRef = useRef(null);
  
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  // Focus на email при загрузке
  useEffect(() => {
    emailInputRef.current?.focus();
  }, []);

  // Focus на ошибку при появлении
  useEffect(() => {
    if (error) {
      errorRef.current?.focus();
    }
  }, [error]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(API_ENDPOINTS.LOGIN, formData);
      
      if (response.data.success) {
        // Сохраняем пользователя в LocalStorage
        localStorage.setItem('user', JSON.stringify(response.data.user));
        localStorage.setItem('token', response.data.token);
        
        // Перенаправляем на главную (один редирект без мерцания)
        window.location.href = '/';
      } else {
        setError(response.data.message || 'Ошибка входа');
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.message || 'Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const openPasswordReset = () => {
    setResetEmail(formData.email);
    setResetMessage('');
    setResetError('');
    setShowForgotPasswordModal(true);
  };

  const handlePasswordResetRequest = async (event) => {
    event.preventDefault();
    setResetMessage('');
    setResetError('');

    try {
      setResetLoading(true);
      await axios.post(API_ENDPOINTS.REQUEST_PASSWORD_RESET, {
        email: resetEmail.trim().toLowerCase()
      });
      setResetMessage(
        'Если такой аккаунт существует, ссылка для сброса отправлена на рабочую почту.'
      );
    } catch {
      setResetError('Не удалось отправить запрос. Попробуйте ещё раз позже.');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-sidebar-bg flex items-center justify-center p-4">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-900/20 via-transparent to-transparent" />
      
      <main className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-scale-in">
        
        {/* Header */}
        <header className="bg-gradient-to-br from-brand-600 to-brand-700 p-8 text-center">
          <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <span className="text-white text-3xl font-bold">E</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Evaluation Portal</h1>
          <p className="text-brand-100 text-sm mt-1">Войдите в систему для продолжения</p>
        </header>

        {/* Form */}
        <div className="p-8">
          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            {/* Error message */}
            {error && (
              <div 
                ref={errorRef}
                role="alert"
                aria-live="assertive"
                tabIndex={-1}
                className="flex items-start gap-3 p-4 bg-danger-50 text-danger-700 rounded-xl border border-danger-200 animate-slide-down"
              >
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <span className="text-sm font-medium">{error}</span>
              </div>
            )}

            {/* Email field */}
            <div className="space-y-2">
              <label 
                htmlFor="email" 
                className="label"
              >
                Email
              </label>
              <div className="relative">
                <Mail 
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 pointer-events-none" 
                  aria-hidden="true" 
                />
                <input 
                  ref={emailInputRef}
                  id="email"
                  name="email"
                  type="email" 
                  required
                  autoComplete="email"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck="false"
                  className="input pl-11"
                  placeholder="name@company.com"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  aria-describedby={error ? 'login-error' : undefined}
                />
              </div>
            </div>

            {/* Password field */}
            <div className="space-y-2">
              <label 
                htmlFor="password" 
                className="label"
              >
                Пароль
              </label>
              <div className="relative">
                <Lock 
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 pointer-events-none" 
                  aria-hidden="true" 
                />
                <input 
                  id="password"
                  name="password"
                  type="password" 
                  required
                  autoComplete="current-password"
                  className="input pl-11"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  aria-describedby={error ? 'login-error' : undefined}
                />
              </div>
            </div>

            {/* Forgot password link */}
            <div className="text-right">
              <button
                type="button"
                onClick={openPasswordReset}
                className="text-sm text-slate-500 hover:text-brand-600 transition-colors"
              >
                Забыли пароль?
              </button>
            </div>

            {/* Submit button */}
            <button 
              type="submit" 
              disabled={loading}
              className="btn btn-lg w-full bg-sidebar-bg hover:bg-slate-800 text-white shadow-xl disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin w-5 h-5" aria-hidden="true" />
                  <span>Вход...</span>
                </>
              ) : (
                'Войти'
              )}
            </button>
          </form>

          {/* Registration link */}
          <p className="text-center text-sm text-slate-500 mt-6">
            Нет аккаунта?{' '}
            <button 
              onClick={() => setShowRegisterModal(true)}
              className="text-brand-600 hover:text-brand-700 font-medium"
            >
              Зарегистрироваться
            </button>
          </p>
        </div>
      </main>

      {/* Register Modal */}
      {showRegisterModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 animate-fade-in"
          onClick={() => setShowRegisterModal(false)}
        >
          <div 
            className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="bg-gradient-to-br from-emerald-600 to-teal-600 p-6 text-center relative">
              <button 
                onClick={() => setShowRegisterModal(false)}
                className="absolute right-4 top-4 text-white/80 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-3">
                <UserPlus className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white">Регистрация в системе</h2>
              <p className="text-emerald-100 text-sm mt-1">Как получить доступ</p>
            </div>

            {/* Content */}
            <div className="p-6">
              <div className="space-y-4 mb-6">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-600 font-bold text-sm">1</span>
                  </div>
                  <div>
                    <p className="text-slate-800 font-medium">Обратитесь к HR-отделу</p>
                    <p className="text-slate-500 text-sm">Попросите HR добавить вас в систему и выслать ссылку для регистрации</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-600 font-bold text-sm">2</span>
                  </div>
                  <div>
                    <p className="text-slate-800 font-medium">Получите ссылку-приглашение</p>
                    <p className="text-slate-500 text-sm">Ссылка придёт на вашу рабочую почту @sedamedical.com</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-600 font-bold text-sm">3</span>
                  </div>
                  <div>
                    <p className="text-slate-800 font-medium">Завершите регистрацию</p>
                    <p className="text-slate-500 text-sm">Перейдите по ссылке, подтвердите email и создайте пароль</p>
                  </div>
                </div>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-amber-800 font-medium text-sm">Уже есть ссылка?</p>
                    <p className="text-amber-700 text-sm">Если у вас уже есть ссылка-приглашение, просто перейдите по ней для регистрации</p>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => setShowRegisterModal(false)}
                className="w-full mt-6 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium py-3 rounded-xl transition-colors"
              >
                Понятно
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Forgot Password Modal */}
      {showForgotPasswordModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 animate-fade-in"
          onClick={() => setShowForgotPasswordModal(false)}
        >
          <div 
            className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="bg-gradient-to-br from-brand-600 to-brand-700 p-6 text-center relative">
              <button 
                onClick={() => setShowForgotPasswordModal(false)}
                className="absolute right-4 top-4 text-white/80 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-3">
                <KeyRound className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white">Забыли пароль?</h2>
              <p className="text-brand-100 text-sm mt-1">Как восстановить доступ</p>
            </div>

            {/* Content */}
            <div className="p-6">
              <form className="space-y-4" onSubmit={handlePasswordResetRequest}>
                {resetMessage && (
                  <div role="status" className="bg-success-50 text-success-700 rounded-xl p-4 text-sm">
                    {resetMessage}
                  </div>
                )}
                {resetError && (
                  <div role="alert" className="bg-danger-50 text-danger-700 rounded-xl p-4 text-sm">
                    {resetError}
                  </div>
                )}
                <div>
                  <label htmlFor="reset-email" className="block text-sm font-medium text-slate-700 mb-2">
                    Рабочий email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" aria-hidden="true" />
                    <input
                      id="reset-email"
                      type="email"
                      autoComplete="email"
                      value={resetEmail}
                      onChange={(event) => setResetEmail(event.target.value)}
                      className="w-full pl-11 pr-4 py-3 border border-slate-200 rounded-xl"
                      placeholder="name@sedamedical.com"
                      required
                    />
                  </div>
                </div>
                <p className="text-xs text-slate-500">
                  Ссылка одноразовая и действует 30 минут. Ответ одинаков для существующих и неизвестных адресов.
                </p>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="btn btn-lg w-full bg-brand-600 text-white disabled:opacity-60"
                >
                  {resetLoading && <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />}
                  {resetLoading ? 'Отправляем...' : 'Отправить ссылку'}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Login;
