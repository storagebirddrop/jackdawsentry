-- Jackdaw Sentry - Seed Admin User
-- For CI/automated environments only. Interactive deployments use /setup.
-- No plaintext credentials are stored in source control. The bcrypt hash below
-- is a placeholder for CI pipelines. Production deployments MUST provision admin
-- credentials via the /setup wizard or secure secret management (vault/ENV).
-- Rotate this hash immediately if used outside ephemeral test environments.

INSERT INTO users (username, email, password_hash, full_name, role, is_active, gdpr_consent_given)
VALUES (
    'admin',
    'admin@jackdawsentry.local',
    '$2b$12$FUjNOehtqtKKSNDStEqMEe4Z2TuJsS.5PfRLqz7Enmph0fg5zcgza',
    'System Administrator',
    'admin',
    true,
    false
)
ON CONFLICT (username) DO NOTHING;
