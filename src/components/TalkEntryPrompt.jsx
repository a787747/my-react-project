import React from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle } from 'lucide-react';

import { TALK_COPY } from '../content/talkCopy';
import { useTalkChannel } from '../hooks/useTalkChannel';

const TalkEntryPrompt = ({ user, compact = false, className = '' }) => {
  const { wave, myResponse, loading, error } = useTalkChannel(user);

  if (loading || error || !wave?.is_open || myResponse) return null;

  return (
    <div className={`bg-brand-50 border border-brand-200 rounded-xl ${compact ? 'p-4' : 'p-5'} ${className}`}>
      <div className="flex items-start gap-3">
        <MessageCircle className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h2 className="font-bold text-brand-900">{TALK_COPY.title}</h2>
          <p className="text-sm text-brand-800 mt-1">{TALK_COPY.question}</p>
          {wave.deadline_text && (
            <p className="text-xs text-brand-700 mt-1">Ответить можно до {wave.deadline_text}.</p>
          )}
          <Link
            to="/talk"
            className="inline-flex mt-3 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700"
          >
            Ответить
          </Link>
        </div>
      </div>
    </div>
  );
};

export default TalkEntryPrompt;
