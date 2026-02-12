-- Jackdaw Sentry - Seed Admin User
-- Creates a default admin user for initial setup
-- Password: <REDACTED> (bcrypt hashed)
-- IMPORTANT: Change this password immediately after first login

INSERT INTO users (username, email, password_hash, full_name, role, is_active, gdpr_consent_given)
VALUES (
    'admin',
    'admin@jackdawsentry.local',
    '$2b$12$LJ3m4ys3Lz0QGqGZGK8xheYp8R1bFw0yP5nKzRGCVxEYJfMbHKXS2',
    'System Administrator',
    'admin',
    true,
    false
)
ON CONFLICT (username) DO NOTHING;
