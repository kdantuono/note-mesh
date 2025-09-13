-- PostgreSQL initialization script for NoteMesh
-- This script runs when the database container starts for the first time

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full-text search extensions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For trigram matching (fuzzy search)
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- For accent-insensitive search

-- Create indexes for better performance
-- These will be managed by Alembic migrations, but we ensure extensions are available

-- Set default timezone
SET timezone = 'UTC';

-- Log that initialization is complete
DO $$
BEGIN
    RAISE NOTICE 'NoteMesh database initialized successfully with extensions: uuid-ossp, pg_trgm, unaccent';
END $$;