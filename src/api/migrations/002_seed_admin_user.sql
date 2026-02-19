-- Jackdaw Sentry - Seed Admin User
-- For CI/automated/test environments ONLY. Interactive deployments use /setup.
-- The INSERT is guarded by the PostgreSQL GUC 'app.environment'; it will only
-- execute when that setting equals 'ci' or 'test'.  Production migrations
-- therefore skip this statement entirely.
--
-- To activate in CI, run before applying migrations:
--   SET app.environment = 'ci';
-- or pass via connection string: options='-c app.environment=ci'
--
-- The password hash is read from the GUC 'admin.password_hash' when available,
-- falling back to a well-known CI-only hash.  Production deployments MUST
-- provision admin credentials via the /setup wizard or secure secret management.

DO $$
BEGIN
    IF COALESCE(current_setting('app.environment', true), '') IN ('ci', 'test') THEN
        INSERT INTO users (username, email, password_hash, full_name, role, is_active, gdpr_consent_given)
        VALUES (
            'admin',
            'admin@jackdawsentry.local',
            COALESCE(
                NULLIF(current_setting('admin.password_hash', true), ''),
                '$2b$12$FUjNOehtqtKKSNDStEqMEe4Z2TuJsS.5PfRLqz7Enmph0fg5zcgza'
            ),
            'System Administrator',
            'admin',
            true,
            false
        )
        ON CONFLICT (username) DO NOTHING;
    END IF;
END
$$;
