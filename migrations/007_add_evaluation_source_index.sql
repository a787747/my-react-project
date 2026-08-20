-- Migration: Add unique index for evaluation_source
-- Purpose: Allow separate evaluations from different sources (manager, subordinate, etc.)

-- Step 1: Drop old index if exists
DROP INDEX IF EXISTS performance_db.idx_evaluations_unique_pair;

-- Step 2: Create new unique index including evaluation_source
-- This allows one evaluation per (subject_id, evaluator_id, evaluation_source) combination
CREATE UNIQUE INDEX idx_evaluations_unique_pair_source 
ON performance_db.evaluations (subject_id, evaluator_id, evaluation_source) 
WHERE is_self_evaluation = false;

-- Step 3: Keep a separate index for self evaluations
CREATE UNIQUE INDEX IF NOT EXISTS idx_evaluations_self_unique 
ON performance_db.evaluations (subject_id, period_id) 
WHERE is_self_evaluation = true;





