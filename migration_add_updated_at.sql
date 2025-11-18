-- Migration to add updated_at column to existing crew_execution_results table
-- Run this script manually in your Snowflake Native App instance

-- First, check if the column already exists
-- If you get an error "Column 'UPDATED_AT' does not exist", that's expected and good

-- Add the updated_at column to the existing table
ALTER TABLE app_data.crew_execution_results
ADD COLUMN updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP();

-- Update existing records to set updated_at = execution_timestamp
UPDATE app_data.crew_execution_results
SET updated_at = execution_timestamp
WHERE updated_at IS NULL;

-- Verify the migration
SELECT
    id,
    execution_timestamp,
    updated_at,
    status
FROM app_data.crew_execution_results
ORDER BY execution_timestamp DESC
LIMIT 5;
