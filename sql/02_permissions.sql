-- =============================================================================
-- Seed: permissions
-- Safe to re-run (idempotent) — INSERT only if the row does not already exist.
-- Uses NOT EXISTS check on the unique key (category, resource, action).
-- Total: 85 permissions  |  SYSTEM=30, APPLICATION=55
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- SYSTEM module views (9)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'dashboard',  'view'),
    ('SYSTEM', 'workspaces', 'view'),
    ('SYSTEM', 'approvals',  'view'),
    ('SYSTEM', 'users',      'view'),
    ('SYSTEM', 'billing',    'view'),
    ('SYSTEM', 'referrals',  'view'),
    ('SYSTEM', 'roles',      'view'),
    ('SYSTEM', 'appearance', 'view'),
    ('SYSTEM', 'settings',   'view')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- SYSTEM workspaces (5)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'workspaces', 'read'),
    ('SYSTEM', 'workspaces', 'create'),
    ('SYSTEM', 'workspaces', 'update'),
    ('SYSTEM', 'workspaces', 'delete'),
    ('SYSTEM', 'workspaces', 'approve')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- SYSTEM billing (3)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'billing', 'read'),
    ('SYSTEM', 'billing', 'update'),
    ('SYSTEM', 'billing', 'subscription')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- SYSTEM referrals (1)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'referrals', 'read')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- SYSTEM roles (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'roles', 'read'),
    ('SYSTEM', 'roles', 'create'),
    ('SYSTEM', 'roles', 'update'),
    ('SYSTEM', 'roles', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- SYSTEM users (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'users', 'read'),
    ('SYSTEM', 'users', 'create'),
    ('SYSTEM', 'users', 'update'),
    ('SYSTEM', 'users', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- SYSTEM permissions (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('SYSTEM', 'permissions', 'read'),
    ('SYSTEM', 'permissions', 'create'),
    ('SYSTEM', 'permissions', 'update'),
    ('SYSTEM', 'permissions', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION module views (9)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'dashboard', 'view'),
    ('APPLICATION', 'pos',       'view'),
    ('APPLICATION', 'orders',    'view'),
    ('APPLICATION', 'catalog',   'view'),
    ('APPLICATION', 'locations', 'view'),
    ('APPLICATION', 'coupons',   'view'),
    ('APPLICATION', 'users',     'view'),
    ('APPLICATION', 'settings',  'view'),
    ('APPLICATION', 'persona',   'view')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION workspace (3)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'workspace', 'read'),
    ('APPLICATION', 'workspace', 'update'),
    ('APPLICATION', 'workspace', 'manage')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION organization (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'organization', 'read'),
    ('APPLICATION', 'organization', 'create'),
    ('APPLICATION', 'organization', 'update'),
    ('APPLICATION', 'organization', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION items (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'items', 'read'),
    ('APPLICATION', 'items', 'create'),
    ('APPLICATION', 'items', 'update'),
    ('APPLICATION', 'items', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION categories (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'categories', 'read'),
    ('APPLICATION', 'categories', 'create'),
    ('APPLICATION', 'categories', 'update'),
    ('APPLICATION', 'categories', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION areas (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'areas', 'read'),
    ('APPLICATION', 'areas', 'create'),
    ('APPLICATION', 'areas', 'update'),
    ('APPLICATION', 'areas', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION tables (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'tables', 'read'),
    ('APPLICATION', 'tables', 'create'),
    ('APPLICATION', 'tables', 'update'),
    ('APPLICATION', 'tables', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION reviews (5)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'reviews', 'read'),
    ('APPLICATION', 'reviews', 'create'),
    ('APPLICATION', 'reviews', 'update'),
    ('APPLICATION', 'reviews', 'delete'),
    ('APPLICATION', 'reviews', 'moderate')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION orders (6)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'orders', 'read'),
    ('APPLICATION', 'orders', 'create'),
    ('APPLICATION', 'orders', 'update'),
    ('APPLICATION', 'orders', 'delete'),
    ('APPLICATION', 'orders', 'status'),
    ('APPLICATION', 'orders', 'payment')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION status (1)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'status', 'update')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION users (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'users', 'read'),
    ('APPLICATION', 'users', 'create'),
    ('APPLICATION', 'users', 'update'),
    ('APPLICATION', 'users', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION dashboard (1)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'dashboard', 'read')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION coupons (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'coupons', 'read'),
    ('APPLICATION', 'coupons', 'create'),
    ('APPLICATION', 'coupons', 'update'),
    ('APPLICATION', 'coupons', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- APPLICATION persona (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at)
SELECT v.category, v.resource, v.action, true,
       (now() AT TIME ZONE 'Asia/Kolkata'),
       (now() AT TIME ZONE 'Asia/Kolkata')
FROM (VALUES
    ('APPLICATION', 'persona', 'read'),
    ('APPLICATION', 'persona', 'create'),
    ('APPLICATION', 'persona', 'update'),
    ('APPLICATION', 'persona', 'delete')
) AS v(category, resource, action)
WHERE NOT EXISTS (
    SELECT 1 FROM permissions p
    WHERE p.category = v.category
      AND p.resource  = v.resource
      AND p.action    = v.action
);

-- ---------------------------------------------------------------------------
-- Verification: count per category (expected: SYSTEM=30, APPLICATION=55, total=85)
-- ---------------------------------------------------------------------------
SELECT
    category,
    COUNT(*) AS permission_count
FROM permissions
GROUP BY category
ORDER BY category;

COMMIT;