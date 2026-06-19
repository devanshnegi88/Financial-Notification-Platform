-- Financial Notification Platform - Database Initialization
-- This script runs on first PostgreSQL startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE financial_notifications TO fnp_user;

-- Performance settings (applied at session level for migrations)
ALTER DATABASE financial_notifications SET timezone TO 'UTC';
ALTER DATABASE financial_notifications SET default_text_search_config TO 'english';
