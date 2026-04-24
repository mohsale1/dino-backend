-- =============================================================================
-- Seed: roles
-- Safe to re-run (idempotent) — INSERT only if the role name does not exist.
-- Uses NOT EXISTS check on the unique key (name).
-- Total: 6 roles  |  role_type: 0 = System, 1 = Application
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- APPLICATION roles (role_type = 1)
-- ---------------------------------------------------------------------------
INSERT INTO roles (name, description, role_type, is_active, created_at, updated_at)
SELECT v.name, v.description, v.role_type, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    (
        'Owner',
        'Full access to all application modules including workspace management, '
        'organization switching, user administration, catalog, locations, orders, '
        'POS, personas and analytics.',
        1
    ),
    (
        'Manager',
        'Full application access except persona module management. Can only read '
        'their own persona, cannot view or manage the personas module.',
        1
    ),
    (
        'User',
        'Restricted to the orders module only. Can view orders and update order status.',
        1
    )
) AS v(name, description, role_type)
WHERE NOT EXISTS (
    SELECT 1 FROM roles r WHERE r.name = v.name
);

-- ---------------------------------------------------------------------------
-- SYSTEM roles (role_type = 0)
-- ---------------------------------------------------------------------------
INSERT INTO roles (name, description, role_type, is_active, created_at, updated_at)
SELECT v.name, v.description, v.role_type, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    (
        'SuperAdmin',
        'Unrestricted access to the entire system including user management, billing, '
        'workspace management, and role and permission management.',
        0
    ),
    (
        'Admin',
        'Read-only access across all system modules. Can approve workspace requests. '
        'Cannot create, update or delete any resource.',
        0
    ),
    (
        'Operator',
        'Read-only access to workspaces and billing modules only.',
        0
    )
) AS v(name, description, role_type)
WHERE NOT EXISTS (
    SELECT 1 FROM roles r WHERE r.name = v.name
);

-- ---------------------------------------------------------------------------
-- Verification: all 6 roles grouped by type
-- (expected: role_type 0 = 3 rows, role_type 1 = 3 rows, total = 6)
-- ---------------------------------------------------------------------------
SELECT
    role_type,
    CASE role_type
        WHEN 0 THEN 'System'
        WHEN 1 THEN 'Application'
        ELSE 'Unknown'
    END                  AS type_label,
    COUNT(*)             AS role_count,
    array_agg(name ORDER BY name) AS role_names
FROM roles
GROUP BY role_type
ORDER BY role_type;

COMMIT;
