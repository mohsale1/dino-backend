-- =============================================================================
-- Superadmin user seed — dino-system
-- Assumes the SuperAdmin role already exists (run 02_seed_roles.sql first).
--
-- Plain-text password : 
-- Hash pipeline       : SHA-256(password) → base64-encode → bcrypt(rounds=12)
-- =============================================================================

BEGIN;

INSERT INTO users (
    user_type,
    email,
    first_name,
    last_name,
    password_hash,
    role_id,
    is_active,
    created_at,
    updated_at
)
SELECT
    0,
    'superadmin@dino.internal',
    'Super',
    'Admin',
    '$2b$12$fb3MAlzQw9PPNnx/Mv/BT.88qzd27BhiwUbVbvtyHO7UsQ8Sk8KB2',
    r.id,
    true,
    (now() AT TIME ZONE 'Asia/Kolkata'),
    (now() AT TIME ZONE 'Asia/Kolkata')
FROM roles r
WHERE r.name = 'SuperAdmin'
ON CONFLICT (email) DO NOTHING;

COMMIT;

-- =============================================================================
-- Verification
-- =============================================================================
SELECT
    u.id,
    u.email,
    u.user_type,
    u.is_active,
    r.name     AS role,
    u.created_at
FROM  users u
JOIN  roles r ON r.id = u.role_id
WHERE u.email = 'superadmin@dino.internal';