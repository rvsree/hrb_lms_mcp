-- Sample OAuth2 client for hrb_chatbot_v2. Run after oauth_schema.sql.
-- client_secret_hash below is a PLACEHOLDER - the real row (with a real
-- generated secret's SHA-256 hash) was inserted directly, not via this
-- file, 2026-09-22 - the plaintext secret is only ever handed to the
-- client once, at provisioning time (hrb_chatbot_v2's own .env), never
-- checked into either repo. Re-run this file with a real hash if you
-- need to reprovision from scratch.

INSERT INTO hrb_lms_mcp_auth.oauth_clients (client_id, client_secret_hash, client_name, scopes) VALUES
    ('hrb-chatbot-v2', 'REPLACE_WITH_REAL_SHA256_HASH', 'hrb_chatbot_v2 calling hrb_lms_mcp',
        ARRAY['mcp:get_leave_balance', 'mcp:get_leave_history'])
ON CONFLICT (client_id) DO NOTHING;
