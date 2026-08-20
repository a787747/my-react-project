-- Migration: Add evaluation_source field to evaluations table
-- Description: Adds a field to distinguish between evaluation types (manager, subordinate, self)
-- Date: 2024-12

-- Step 1: Add the evaluation_source column
ALTER TABLE performance_db.evaluations 
ADD COLUMN IF NOT EXISTS evaluation_source VARCHAR(20) DEFAULT 'manager';

-- Step 2: Update existing records based on is_self_evaluation flag
UPDATE performance_db.evaluations
SET evaluation_source = CASE 
    WHEN is_self_evaluation = true THEN 'self'
    ELSE 'manager'
END
WHERE evaluation_source IS NULL OR evaluation_source = 'manager';

-- Step 3: Drop the old unique index and create a new one that includes evaluation_source
-- This allows the same evaluator to evaluate the same subject with different sources
DROP INDEX IF EXISTS performance_db.idx_evaluations_unique_pair;

-- Create new unique index that considers evaluation_source
CREATE UNIQUE INDEX idx_evaluations_unique_pair_with_source 
ON performance_db.evaluations (subject_id, evaluator_id, evaluation_source) 
WHERE is_self_evaluation = false;

-- Keep a separate unique index for self-evaluations
CREATE UNIQUE INDEX IF NOT EXISTS idx_evaluations_self_unique 
ON performance_db.evaluations (subject_id, period_id) 
WHERE is_self_evaluation = true;

-- Add comment for documentation
COMMENT ON COLUMN performance_db.evaluations.evaluation_source IS 
'Type of evaluation: manager (от руководителя), subordinate (от подчиненного), self (самооценка)';

