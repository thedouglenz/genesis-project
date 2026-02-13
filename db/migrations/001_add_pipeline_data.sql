-- Run against genesis_solution as neondb_owner (table owner)
-- Adds pipeline_data column to store step summaries on assistant messages

ALTER TABLE messages ADD COLUMN IF NOT EXISTS pipeline_data JSONB;
