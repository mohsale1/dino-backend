-- =============================================================================
-- Seed: roles
-- Safe to re-run (idempotent) — ON CONFLICT (name) DO NOTHING
-- Total: 6 roles  |  role_type: 0 = System, 1 = Application
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- APPLICATION roles (role_type = 1)
-- ---------------------------------------------------------------------------

INSERT INTO roles (name, description, role_type, is_active, created_at, updated_at) VALUES

    (
        'Owner',
        'Full access to all application modules including workspace management, '
        'organization switching, user administration, catalog, locations, orders, '
        'POS, and analytics.',
        1, true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')
    ),

    (
        'Manager',
        'Broad access to all operational modules. Cannot manage workspace settings, '
        'delete users, or delete catalog and coupon records.',
        1, true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')
    ),

    (
        'User',
        'Restricted to the orders module only. Can create, view, update order status, '
        'and process payments.',
        1, true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')
    )

ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM roles (role_type = 0)
-- ---------------------------------------------------------------------------

INSERT INTO roles (name, description, role_type, is_active, created_at, updated_at) VALUES

    (
        'SuperAdmin',
        'Unrestricted access to the entire system including user management, billing, '
        'registration codes, and role and permission management.',
        0, true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')
    ),

    (
        'Admin',
        'Access to most system modules. Cannot delete workspaces, manage roles, '
        'or manage permissions.',
        0, true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')
    ),

    (
        'Operator',
        'Read-only access across all system resources. Cannot create, update, '
        'or delete any entity.',
        0, true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')
    )

ON CONFLICT (name) DO NOTHING;

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
