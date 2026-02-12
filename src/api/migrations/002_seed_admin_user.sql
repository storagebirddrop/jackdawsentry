-- Jackdaw Sentry - Seed Admin User
-- Creates a default admin user for initial setup
-- Default password: admin (bcrypt hashed)
-- IMPORTANT: Change this password immediately after first login

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
