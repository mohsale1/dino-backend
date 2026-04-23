-- =============================================================================
-- Seed: permissions
-- Safe to re-run (idempotent) — ON CONFLICT DO NOTHING
-- Total: 79 permissions
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- SYSTEM module view (7)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'dashboard', 'view', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'workspaces', 'view', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'users',      'view', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'roles',      'view', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'billing',    'view', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'registration','view',true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'settings',   'view', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM workspaces (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'workspaces', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'workspaces', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'workspaces', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'workspaces', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM billing (3)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'billing', 'read',         true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'billing', 'update',       true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'billing', 'subscription', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM registration (3)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'registration', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'registration', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'registration', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM roles (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'roles', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'roles', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'roles', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'roles', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM users (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'users', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'users', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'users', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'users', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SYSTEM permissions (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('SYSTEM', 'permissions', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'permissions', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'permissions', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('SYSTEM', 'permissions', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION module view (8)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'dashboard', 'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'pos',       'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'orders',    'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'catalog',   'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'locations', 'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'coupons',   'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'users',     'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'settings',  'view',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- APPLICATION workspace (3)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'workspace', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'workspace', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'workspace', 'manage', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION organization (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'organization', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'organization', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'organization', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'organization', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION items (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'items', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'items', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'items', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'items', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION categories (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'categories', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'categories', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'categories', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'categories', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION areas (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'areas', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'areas', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'areas', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'areas', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION tables (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'tables', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'tables', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'tables', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'tables', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION reviews (5)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'reviews', 'read',     true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'reviews', 'create',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'reviews', 'update',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'reviews', 'delete',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'reviews', 'moderate', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION orders (6)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'orders', 'read',    true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'orders', 'create',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'orders', 'update',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'orders', 'delete',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'orders', 'status',  true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'orders', 'payment', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION status (1)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'status', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION users (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'users', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'users', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'users', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'users', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION dashboard (1)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'dashboard', 'read', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- APPLICATION coupons (4)
-- ---------------------------------------------------------------------------
INSERT INTO permissions (category, resource, action, is_active, created_at, updated_at) VALUES
    ('APPLICATION', 'coupons', 'read',   true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'coupons', 'create', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'coupons', 'update', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata')),
    ('APPLICATION', 'coupons', 'delete', true, (now() AT TIME ZONE 'Asia/Kolkata'), (now() AT TIME ZONE 'Asia/Kolkata'))
ON CONFLICT (category, resource, action) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Verification: count per category (expected: SYSTEM=29, APPLICATION=50, total=79)
-- ---------------------------------------------------------------------------
SELECT
    category,
    COUNT(*) AS permission_count
FROM permissions
GROUP BY category
ORDER BY category;

COMMIT;
