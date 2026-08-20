const DRAFT_PREFIX = 'epe:evaluation-draft';
const DRAFT_VERSION = 1;
const DRAFT_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

export const getEvaluationDraftKey = (evaluatorId, subjectId) => {
  if (!evaluatorId || !subjectId) return null;
  return `${DRAFT_PREFIX}:${evaluatorId}:${subjectId}`;
};

export const loadEvaluationDraft = (key, storage = localStorage) => {
  if (!key) return null;

  try {
    const raw = storage.getItem(key);
    if (!raw) return null;

    const draft = JSON.parse(raw);
    const savedAt = Date.parse(draft.savedAt);
    const isExpired = !Number.isFinite(savedAt)
      || Date.now() - savedAt > DRAFT_MAX_AGE_MS;

    if (draft.version !== DRAFT_VERSION || isExpired) {
      storage.removeItem(key);
      return null;
    }

    return {
      evaluations: draft.evaluations || {},
      comments: draft.comments || {},
      savedAt: draft.savedAt,
    };
  } catch {
    storage.removeItem(key);
    return null;
  }
};

export const saveEvaluationDraft = (
  key,
  evaluations,
  comments,
  storage = localStorage,
) => {
  if (!key) return;

  storage.setItem(key, JSON.stringify({
    version: DRAFT_VERSION,
    savedAt: new Date().toISOString(),
    evaluations,
    comments,
  }));
};

export const clearEvaluationDraft = (key, storage = localStorage) => {
  if (key) storage.removeItem(key);
};
