/**
 * Register - Страница регистрации с верификацией email
 * 
 * Назначение: Регистрация сотрудников по invite-токену с подтверждением email
 * Доступ: Публичный (по ссылке с токеном)
 * 
 * Процесс:
 * 1. Проверка invite-токена
 * 2. Ввод email → отправка кода верификации
 * 3. Ввод кода подтверждения
 * 4. Создание пароля → регистрация
 */

import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { 
  Lock, Mail, Loader2, CheckCircle, XCircle, UserPlus, 
  Eye, EyeOff, Send, ShieldCheck, ArrowRight, ArrowLeft,
  LogIn, AlertCircle, HelpCircle, UserX, KeyRound
} from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';
import logger from '../utils/logger';

// Шаги регистрации
const STEPS = {
  CHECKING_TOKEN: 'checking',
  INVALID_TOKEN: 'invalid',
  ALREADY_REGISTERED: 'already_registered',
  EMAIL_NOT_FOUND: 'email_not_found',
  EMAIL_INPUT: 'email',
  CODE_INPUT: 'code',
  PASSWORD_INPUT: 'password',
  SUCCESS: 'success'
};

/**
 * Валидация пароля - проверяет требования к надёжности
 * @param {string} password - пароль для проверки
 * @returns {string[]} - массив ошибок (пустой если пароль валидный)
 */
const validatePassword = (password) => {
  const errors = [];
  if (password.length < 8) {
    errors.push('минимум 8 символов');
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('хотя бы одна заглавная буква');
  }
  if (!/[a-z]/.test(password)) {
    errors.push('хотя бы одна строчная буква');
  }
  if (!/[0-9]/.test(password)) {
    errors.push('хотя бы одна цифра');
  }
  return errors;
};

/**
 * Рассчитывает надёжность пароля
 * @param {string} password - пароль
 * @returns {{ score: number, label: string, color: string }}
 */
const getPasswordStrength = (password) => {
  if (!password) return { score: 0, label: '', color: 'gray' };
  
  const errors = validatePassword(password);
  const score = 4 - errors.length;
  
  const strengthMap = [
    { label: 'Слабый', color: 'red' },
    { label: 'Слабый', color: 'red' },
    { label: 'Средний', color: 'amber' },
    { label: 'Хороший', color: 'emerald' },
    { label: 'Отличный', color: 'emerald' }
  ];
  
  return { score, ...strengthMap[score] };
};

const Register = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  // Состояния
  const [step, setStep] = useState(STEPS.CHECKING_TOKEN);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [formData, setFormData] = useState({
    email: '',
    verificationCode: '',
    password: '',
    confirmPassword: ''
  });

  const [userData, setUserData] = useState({
    fullName: '',
    email: ''
  });

  // Проверка токена при загрузке
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setStep(STEPS.INVALID_TOKEN);
        setError('Ссылка для регистрации недействительна. Отсутствует токен.');
        return;
      }

      try {
        const response = await apiClient.get(API_ENDPOINTS.VERIFY_INVITE, {
          params: { token }
        });

        if (response.data.valid) {
          setStep(STEPS.EMAIL_INPUT);
        } else {
          setStep(STEPS.INVALID_TOKEN);
          setError(response.data.message || 'Ссылка для регистрации недействительна или истекла.');
        }
      } catch (err) {
        logger.error('Token verification error:', err);
        setStep(STEPS.INVALID_TOKEN);
        setError('Ошибка проверки ссылки. Попробуйте позже.');
      }
    };

    verifyToken();
  }, [token]);

  // Отправка кода верификации
  const handleSendCode = async (e) => {
    e.preventDefault();
    
    if (!formData.email.toLowerCase().endsWith('@sedamedical.com')) {
      setError('Разрешены только email с доменом @sedamedical.com');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post(API_ENDPOINTS.SEND_VERIFICATION_CODE, {
        email: formData.email,
        token: token
      });

      if (response.data.success) {
        setUserData({
          fullName: (response.data.data.full_name || '').trim(),
          email: response.data.data.email
        });
        setStep(STEPS.CODE_INPUT);
      } else if (response.data.error_code === 'already_registered') {
        // Пользователь уже зарегистрирован - показываем специальный экран
        setUserData({
          fullName: (response.data.data?.full_name || '').trim(),
          email: response.data.data?.email || formData.email
        });
        setStep(STEPS.ALREADY_REGISTERED);
      } else if (response.data.error_code === 'email_not_found') {
        // Email не найден в системе - показываем специальный экран
        setUserData({
          fullName: '',
          email: response.data.data?.email || formData.email
        });
        setStep(STEPS.EMAIL_NOT_FOUND);
      } else if (response.data.error_code === 'resend_cooldown') {
        setError(response.data.message || 'Код уже отправлен. Подождите минуту перед повторной отправкой.');
      } else {
        setError(response.data.message || 'Ошибка отправки кода');
      }
    } catch (err) {
      logger.error('Send code error:', err);
      setError(err.response?.data?.message || 'Ошибка отправки кода. Проверьте email.');
    } finally {
      setLoading(false);
    }
  };

  // Проверка кода
  const handleVerifyCode = async (e) => {
    e.preventDefault();
    
    if (formData.verificationCode.length !== 6) {
      setError('Введите 6-значный код');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post(API_ENDPOINTS.VERIFY_CODE, {
        email: formData.email,
        code: formData.verificationCode
      });

      if (response.data.verified) {
        setStep(STEPS.PASSWORD_INPUT);
      } else {
        setError(response.data.message || 'Неверный код');
      }
    } catch (err) {
      logger.error('Verify code error:', err);
      setError(err.response?.data?.message || 'Ошибка проверки кода');
    } finally {
      setLoading(false);
    }
  };

  // Регистрация (создание пароля)
  const handleRegister = async (e) => {
    e.preventDefault();
    
    // Проверка надёжности пароля
    const passwordErrors = validatePassword(formData.password);
    if (passwordErrors.length > 0) {
      setError(`Пароль должен содержать: ${passwordErrors.join(', ')}`);
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post(API_ENDPOINTS.REGISTER, {
        token,
        email: formData.email,
        password: formData.password,
        verification_code: formData.verificationCode
      });

      if (response.data.success) {
        setStep(STEPS.SUCCESS);
        setTimeout(() => navigate('/login'), 3000);
      } else {
        setError(response.data.message || 'Ошибка регистрации');
      }
    } catch (err) {
      logger.error('Registration error:', err);
      setError(err.response?.data?.message || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  // Экран загрузки
  if (step === STEPS.CHECKING_TOKEN) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 text-center">
          <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-800">Проверка ссылки...</h2>
        </div>
      </div>
    );
  }

  // Невалидный токен или нет токена
  if (step === STEPS.INVALID_TOKEN) {
    const isNoToken = !token;
    
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
          {/* Header */}
          <div className={`${isNoToken ? 'bg-gradient-to-br from-emerald-600 to-teal-600' : 'bg-gradient-to-br from-red-500 to-rose-600'} p-6 text-center`}>
            <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-3">
              {isNoToken ? <UserPlus className="w-7 h-7 text-white" /> : <XCircle className="w-7 h-7 text-white" />}
            </div>
            <h1 className="text-xl font-bold text-white">
              {isNoToken ? 'Регистрация в системе' : 'Ссылка недействительна'}
            </h1>
            <p className={`${isNoToken ? 'text-emerald-100' : 'text-red-100'} text-sm mt-1`}>
              {isNoToken ? 'Как получить доступ' : 'Срок действия ссылки истёк'}
            </p>
          </div>

          {/* Content */}
          <div className="p-6">
            {isNoToken ? (
              <>
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

                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
                  <div className="flex items-start gap-3">
                    <HelpCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-amber-800 font-medium text-sm">Уже есть ссылка?</p>
                      <p className="text-amber-700 text-sm">Если у вас уже есть ссылка-приглашение, просто перейдите по ней для регистрации</p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="mb-6">
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
                  <p className="text-red-800 text-sm">{error}</p>
                </div>
                <p className="text-slate-600 text-sm text-center">
                  Обратитесь к HR-отделу для получения новой ссылки для регистрации
                </p>
              </div>
            )}

            <Link 
              to="/login" 
              className="block w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3 rounded-xl transition-all text-center"
            >
              <LogIn className="w-5 h-5 inline mr-2" />
              Перейти на страницу входа
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Аккаунт уже зарегистрирован
  if (step === STEPS.ALREADY_REGISTERED) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-br from-amber-500 to-orange-500 p-6 text-center">
            <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-3">
              <AlertCircle className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">Аккаунт уже существует</h1>
            <p className="text-amber-100 text-sm mt-1">
              Этот email уже зарегистрирован в системе
            </p>
          </div>

          {/* Content */}
          <div className="p-8">
            {userData.fullName && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center mb-6">
                <p className="text-amber-800 font-medium">{userData.fullName}</p>
                <p className="text-amber-600 text-sm">{userData.email || formData.email}</p>
              </div>
            )}

            <p className="text-gray-600 text-center mb-6">
              Этот аккаунт уже был зарегистрирован ранее. Вы можете войти в систему или сбросить пароль, если забыли его.
            </p>

            <div className="space-y-3">
              <Link 
                to="/login" 
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg flex justify-center items-center gap-2"
              >
                <LogIn className="w-5 h-5" />
                Войти в систему
              </Link>

              <button 
                onClick={() => {
                  setStep(STEPS.EMAIL_INPUT);
                  setFormData({ ...formData, email: '' });
                  setError('');
                }}
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 rounded-xl transition-all flex justify-center items-center gap-2"
              >
                Использовать другой email
              </button>

              <div className="bg-info-50 border border-info-200 rounded-xl p-4 mt-4">
                <div className="flex items-start gap-3">
                  <KeyRound className="w-5 h-5 text-info-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-info-800 font-medium text-sm">Забыли пароль?</p>
                    <p className="text-info-700 text-sm">
                      Обратитесь к HR-отделу (hr@sedamedical.com) для сброса пароля
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Email не найден в системе
  if (step === STEPS.EMAIL_NOT_FOUND) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-br from-red-500 to-rose-600 p-6 text-center">
            <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-3">
              <UserX className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">Email не найден</h1>
            <p className="text-red-100 text-sm mt-1">
              Этот email не зарегистрирован в системе
            </p>
          </div>

          {/* Content */}
          <div className="p-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center mb-6">
              <p className="text-red-800 font-medium font-mono text-sm">{userData.email || formData.email}</p>
            </div>

            <div className="space-y-4 mb-6">
              <div className="flex items-start gap-3 text-left">
                <div className="w-6 h-6 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <HelpCircle className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <p className="text-gray-700 font-medium text-sm">Проверьте правильность email</p>
                  <p className="text-gray-500 text-xs">Убедитесь, что вы правильно написали адрес электронной почты</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3 text-left">
                <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Mail className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <p className="text-gray-700 font-medium text-sm">Обратитесь в HR</p>
                  <p className="text-gray-500 text-xs">Если email правильный, попросите HR-отдел добавить вас в систему</p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <button 
                onClick={() => {
                  setStep(STEPS.EMAIL_INPUT);
                  setError('');
                }}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg flex justify-center items-center gap-2"
              >
                <ArrowLeft className="w-5 h-5" />
                Попробовать другой email
              </button>

              <Link 
                to="/login" 
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 rounded-xl transition-all flex justify-center items-center gap-2"
              >
                <LogIn className="w-5 h-5" />
                Перейти на страницу входа
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Успешная регистрация
  if (step === STEPS.SUCCESS) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Регистрация успешна!</h2>
          <p className="text-gray-500 mb-4">Добро пожаловать, {userData.fullName}!</p>
          <p className="text-sm text-gray-400">Перенаправление на страницу входа...</p>
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mx-auto mt-4" />
        </div>
      </div>
    );
  }

  // Индикатор прогресса
  const renderProgress = () => {
    const steps = [
      { id: STEPS.EMAIL_INPUT, label: 'Email', num: 1 },
      { id: STEPS.CODE_INPUT, label: 'Код', num: 2 },
      { id: STEPS.PASSWORD_INPUT, label: 'Пароль', num: 3 }
    ];
    const currentIdx = steps.findIndex(s => s.id === step);

    return (
      <div className="flex items-center justify-center gap-2 mb-6">
        {steps.map((s, idx) => (
          <React.Fragment key={s.id}>
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all ${
              idx <= currentIdx 
                ? 'bg-emerald-600 text-white' 
                : 'bg-gray-200 text-gray-500'
            }`}>
              {s.num}
            </div>
            {idx < steps.length - 1 && (
              <div className={`w-8 h-1 rounded ${
                idx < currentIdx ? 'bg-emerald-600' : 'bg-gray-200'
              }`} />
            )}
          </React.Fragment>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        
        {/* Header */}
        <div className="bg-gradient-to-br from-emerald-600 to-teal-600 p-6 text-center">
          <div className="w-14 h-14 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center mx-auto mb-3">
            {step === STEPS.EMAIL_INPUT && <Mail className="w-7 h-7 text-white" />}
            {step === STEPS.CODE_INPUT && <ShieldCheck className="w-7 h-7 text-white" />}
            {step === STEPS.PASSWORD_INPUT && <Lock className="w-7 h-7 text-white" />}
          </div>
          <h1 className="text-xl font-bold text-white">
            {step === STEPS.EMAIL_INPUT && 'Введите email'}
            {step === STEPS.CODE_INPUT && 'Подтверждение email'}
            {step === STEPS.PASSWORD_INPUT && 'Создание пароля'}
          </h1>
          <p className="text-emerald-100 text-sm mt-1">
            {step === STEPS.EMAIL_INPUT && 'Укажите ваш рабочий email'}
            {step === STEPS.CODE_INPUT && 'Введите код из письма'}
            {step === STEPS.PASSWORD_INPUT && 'Придумайте надёжный пароль'}
          </p>
        </div>

        {/* Progress */}
        <div className="px-8 pt-6">
          {renderProgress()}
        </div>

        {/* Form */}
        <div className="p-8 pt-2">
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm text-center font-medium border border-red-100 mb-4">
              {error}
            </div>
          )}

          {/* Step 1: Email */}
          {step === STEPS.EMAIL_INPUT && (
            <form onSubmit={handleSendCode} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Рабочий Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 text-gray-400 w-5 h-5" />
                  <input 
                    type="email" 
                    required
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                    placeholder="name@sedamedical.com"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </div>
                <p className="text-xs text-gray-400">Только @sedamedical.com</p>
              </div>

              <button 
                type="submit" 
                disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg flex justify-center items-center gap-2"
              >
                {loading ? <Loader2 className="animate-spin w-5 h-5" /> : (
                  <>
                    <Send className="w-5 h-5" />
                    Отправить код
                  </>
                )}
              </button>
            </form>
          )}

          {/* Step 2: Verification Code */}
          {step === STEPS.CODE_INPUT && (
            <form onSubmit={handleVerifyCode} className="space-y-4">
              {userData.fullName && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center mb-4">
                  <p className="text-emerald-800 font-medium">Здравствуйте, {userData.fullName}!</p>
                  <p className="text-emerald-600 text-sm">Код отправлен на {formData.email}</p>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Код подтверждения</label>
                <input 
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  required
                  className="w-full p-3 text-center text-2xl font-mono tracking-widest border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                  placeholder="000000"
                  value={formData.verificationCode}
                  onChange={(e) => setFormData({...formData, verificationCode: e.target.value.replace(/\D/g, '').slice(0, 6)})}
                />
              </div>

              <div className="flex gap-3">
                <button 
                  type="button"
                  onClick={() => {
                    setStep(STEPS.EMAIL_INPUT);
                    setError('');
                  }}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 rounded-xl transition-all flex justify-center items-center gap-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Назад
                </button>
                <button 
                  type="submit" 
                  disabled={loading || formData.verificationCode.length !== 6}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg flex justify-center items-center gap-2 disabled:opacity-50"
                >
                  {loading ? <Loader2 className="animate-spin w-5 h-5" /> : (
                    <>
                      Подтвердить
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <button 
                type="button"
                onClick={handleSendCode}
                disabled={loading}
                className="w-full text-emerald-600 hover:text-emerald-700 text-sm font-medium py-2"
              >
                Отправить код повторно
              </button>
            </form>
          )}

          {/* Step 3: Password */}
          {step === STEPS.PASSWORD_INPUT && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center mb-4">
                <p className="text-emerald-800 text-sm">
                  <CheckCircle className="w-4 h-4 inline mr-1" />
                  Email подтверждён: {formData.email}
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Пароль</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 text-gray-400 w-5 h-5" />
                  <input 
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={8}
                    className="w-full pl-10 pr-12 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                    placeholder="Минимум 8 символов, A-z, 0-9"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {/* Индикатор надёжности пароля */}
                {formData.password && (
                  <div className="mt-2">
                    <div className="flex gap-1 mb-1">
                      {[1, 2, 3, 4].map((level) => {
                        const strength = getPasswordStrength(formData.password);
                        const isActive = level <= strength.score;
                        return (
                          <div
                            key={level}
                            className={`h-1.5 flex-1 rounded-full transition-all ${
                              isActive
                                ? strength.color === 'red' ? 'bg-red-500'
                                : strength.color === 'amber' ? 'bg-amber-500'
                                : 'bg-emerald-500'
                                : 'bg-gray-200'
                            }`}
                          />
                        );
                      })}
                    </div>
                    <p className={`text-xs font-medium ${
                      getPasswordStrength(formData.password).color === 'red' ? 'text-red-600'
                      : getPasswordStrength(formData.password).color === 'amber' ? 'text-amber-600'
                      : 'text-emerald-600'
                    }`}>
                      {getPasswordStrength(formData.password).label}
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-gray-700">Подтверждение пароля</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 text-gray-400 w-5 h-5" />
                  <input 
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    className="w-full pl-10 pr-12 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none"
                    placeholder="Повторите пароль"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <button 
                type="submit" 
                disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg flex justify-center items-center gap-2"
              >
                {loading ? <Loader2 className="animate-spin w-5 h-5" /> : (
                  <>
                    <UserPlus className="w-5 h-5" />
                    Завершить регистрацию
                  </>
                )}
              </button>
            </form>
          )}

          {/* Link to login */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              Уже зарегистрированы?{' '}
              <Link to="/login" className="text-emerald-600 hover:text-emerald-700 font-medium">
                Войти
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
