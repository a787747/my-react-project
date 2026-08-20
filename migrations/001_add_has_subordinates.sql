-- Migration: Add has_subordinates field to users table
-- Description: Adds a boolean field to track if a user has direct subordinates (is a manager)
-- Date: 2024-12

-- Step 1: Add the column
ALTER TABLE performance_db.users 
ADD COLUMN IF NOT EXISTS has_subordinates BOOLEAN DEFAULT false NOT NULL;

-- Step 2: Update the field based on existing manager_id relationships
-- A user has_subordinates = true if at least one other user has them as manager_id
UPDATE performance_db.users u
SET has_subordinates = EXISTS (
    SELECT 1 FROM performance_db.users sub 
    WHERE sub.manager_id = u.id
);

-- Step 3: Create a trigger function to automatically update has_subordinates when manager_id changes
CREATE OR REPLACE FUNCTION performance_db.update_has_subordinates()
RETURNS TRIGGER AS $$
BEGIN
    -- If manager_id changed, update both old and new manager
    IF TG_OP = 'UPDATE' AND OLD.manager_id IS DISTINCT FROM NEW.manager_id THEN
        -- Update old manager (if existed)
        IF OLD.manager_id IS NOT NULL THEN
            UPDATE performance_db.users
            SET has_subordinates = EXISTS (
                SELECT 1 FROM performance_db.users sub 
                WHERE sub.manager_id = OLD.manager_id
            )
            WHERE id = OLD.manager_id;
        END IF;
        
        -- Update new manager (if exists)
        IF NEW.manager_id IS NOT NULL THEN
            UPDATE performance_db.users
            SET has_subordinates = true
            WHERE id = NEW.manager_id;
        END IF;
    END IF;
    
    -- If inserting with a manager_id
    IF TG_OP = 'INSERT' AND NEW.manager_id IS NOT NULL THEN
        UPDATE performance_db.users
        SET has_subordinates = true
        WHERE id = NEW.manager_id;
    END IF;
    
    -- If deleting and had a manager
    IF TG_OP = 'DELETE' AND OLD.manager_id IS NOT NULL THEN
        UPDATE performance_db.users
        SET has_subordinates = EXISTS (
            SELECT 1 FROM performance_db.users sub 
            WHERE sub.manager_id = OLD.manager_id
        )
        WHERE id = OLD.manager_id;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create the trigger
DROP TRIGGER IF EXISTS trg_update_has_subordinates ON performance_db.users;
CREATE TRIGGER trg_update_has_subordinates
AFTER INSERT OR UPDATE OF manager_id OR DELETE ON performance_db.users
FOR EACH ROW
EXECUTE FUNCTION performance_db.update_has_subordinates();

-- Verification query (optional, for manual check)
-- SELECT id, full_name, has_subordinates, 
--        (SELECT COUNT(*) FROM performance_db.users WHERE manager_id = u.id) as actual_subordinates
-- FROM performance_db.users u
-- ORDER BY has_subordinates DESC, id;

