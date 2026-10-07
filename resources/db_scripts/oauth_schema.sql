-- OAuth2 client-credentials schema (2026-09-22) - registers which
-- external callers may obtain a token from POST /oauth/token and call
-- POST /mcp. Own schema, not `hrb_emp_lms` (leave-management domain
-- data) or `public` - a bounded context for this server's own auth data,
-- same principle as hrb_chatbot_v2's `hrb_chatbot_v2_core` schema.
--
-- No FOREIGN KEY constraints, by the same real-world reasoning as that
-- sibling project's schema: this is a capstone/portfolio project, not a
-- production system with a data-integrity SLA that needs DB-enforced FKs.
--
-- Run as: psql -d <your POSTGRES_DB_NAME> -f oauth_schema.sql
-- (already applied to production's Neon database, 2026-10-07 - see
-- hrb_chatbot_v2's RAG-ROADMAP.md Phase 118)

CREATE SCHEMA IF NOT EXISTS hrb_lms_mcp_auth;

CREATE TABLE IF NOT EXISTS hrb_lms_mcp_auth.oauth_clients (
    id BIGSERIAL PRIMARY KEY,
    client_id TEXT NOT NULL UNIQUE,
    client_secret_hash TEXT NOT NULL,  -- SHA-256, not bcrypt - see this
                                        -- table's own note in hrb_chatbot_v2's
                                        -- RAG-ROADMAP.md Phase 53 for why
    client_name TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
