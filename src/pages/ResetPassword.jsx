import React, { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertCircle, CheckCircle, KeyRound, Loader2 } from 'lucide-react';
import axios from 'axios';
import { API_ENDPOINTS } from '../config/api';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get('token') || '', [searchParams]);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!token) {
      setError('Ссылка для сброса пароля недействительна.');
      return;
    }
    if (password.length < 8) {
      setError('Пароль должен содержать минимум 8 символов.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Пароли не совпадают.');
      return;
    }

    try {
      setLoading(true);
      await axios.post(API_ENDPOINTS.RESET_PASSWORD, {
        token,
        password,
      });
      setSuccess(true);
      setPassword('');
      setConfirmPassword('');
    } catch (requestError) {
      setError(
        requestError.response?.data?.message
          || 'Ссылка недействительна или срок её действия истёк.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <section className="w-full max-w-md bg-white rounded-2xl border border-slate-200 p-8">
        <div className="w-14 h-14 bg-brand-100 text-brand-700 rounded-2xl flex items-center justify-center mb-6">
          <KeyRound className="w-7 h-7" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Новый пароль</h1>
        <p className="text-sm text-slate-500 mt-2 mb-6">
          Ссылка одноразовая и действует 30 минут.
        </p>

        {success ? (
          <div role="status" className="space-y-5">
            <div className="flex gap-3 p-4 rounded-xl bg-success-50 text-success-700">
              <CheckCircle className="w-5 h-5 shrink-0" aria-hidden="true" />
              <p className="text-sm">Пароль изменён. Все старые сессии завершены.</p>
            </div>
            <Link className="btn btn-lg w-full bg-brand-600 text-white" to="/login">
              Перейти ко входу
            </Link>
          </div>
        ) : (
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div role="alert" className="flex gap-3 p-4 rounded-xl bg-danger-50 text-danger-700">
                <AlertCircle className="w-5 h-5 shrink-0" aria-hidden="true" />
                <p className="text-sm">{error}</p>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="new-password">
                Новый пароль
              </label>
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="input w-full"
                required
                minLength={8}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2" htmlFor="confirm-password">
                Повторите пароль
              </label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="input w-full"
                required
                minLength={8}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !token}
              className="btn btn-lg w-full bg-brand-600 text-white disabled:opacity-60"
            >
              {loading && <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />}
              {loading ? 'Сохраняем...' : 'Сохранить пароль'}
            </button>
          </form>
        )}
      </section>
    </main>
  );
};

export default ResetPassword;
