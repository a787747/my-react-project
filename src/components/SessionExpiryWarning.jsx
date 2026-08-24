import React, { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { getTokenExpiryMs } from '../utils/tokenExpiry';

const WARNING_WINDOW_MS = 15 * 60 * 1000;

const SessionExpiryWarning = () => {
  const [remainingMs, setRemainingMs] = useState(null);

  useEffect(() => {
    const updateRemaining = () => {
      const expiryMs = getTokenExpiryMs(localStorage.getItem('token'));
      setRemainingMs(expiryMs ? expiryMs - Date.now() : null);
    };

    updateRemaining();
    const timer = window.setInterval(updateRemaining, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  if (
    remainingMs === null
    || remainingMs <= 0
    || remainingMs > WARNING_WINDOW_MS
  ) {
    return null;
  }

  const minutes = Math.max(1, Math.ceil(remainingMs / 60_000));

  return (
    <div
      role="status"
      className="fixed top-4 right-4 z-[100] max-w-sm rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900"
    >
      <div className="flex items-start gap-3">
        <Clock className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-sm">
          Сессия завершится примерно через {minutes} мин. Завершите форму;
          незавершённая оценка сохранится в этом браузере и истечёт через 7 дней.
        </p>
      </div>
    </div>
  );
};

export default SessionExpiryWarning;
