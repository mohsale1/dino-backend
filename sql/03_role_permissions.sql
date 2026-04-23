-- =============================================================================
-- Seed: role_permissions
-- Assigns permissions to roles using name/category/resource/action lookups.
-- Safe to re-run (idempotent) — ON CONFLICT DO NOTHING.
-- No hardcoded IDs anywhere.
-- =============================================================================
--
-- Pattern per role:
--   WITH
--     r  AS (SELECT id FROM roles       WHERE name = '...')
--     p1 AS (SELECT id FROM permissions WHERE category = '...' AND resource = '...' AND action = '...')
--     ...
--   INSERT INTO role_permissions (role_id, permission_id)
--   SELECT r.id, p.id FROM r, (VALUES ...) AS p(id)
--   ON CONFLICT DO NOTHING;
--
-- Roles seeded:
--   APPLICATION roles (role_type = 1): Owner, Manager, User
--   SYSTEM      roles (role_type = 0): SuperAdmin, Admin, Operator
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. OWNER  (role_type = 1)
--    Module views : dashboard, pos, orders, catalog, locations,
--                   coupons, users, settings                          (8)
--    workspace    : read, update, manage                              (3)
--    organization : read, create, update, delete                      (4)
--    items        : read, create, update, delete                      (4)
--    categories   : read, create, update, delete                      (4)
--    areas        : read, create, update, delete                      (4)
--    tables       : read, create, update, delete                      (4)
--    reviews      : read, create, update, delete, moderate            (5)
--    orders       : read, create, update, delete, status, payment     (6)
--    status       : update                                            (1)
--    users        : read, create, update, delete                      (4)
--    dashboard    : read                                              (1)
--    coupons      : read, create, update, delete                      (4)
-- ---------------------------------------------------------------------------
WITH
    r AS (
        SELECT id FROM roles WHERE name = 'Owner'
    ),
    perms (category, resource, action) AS (
        VALUES
            -- module views
            ('APPLICATION', 'dashboard', 'view'),
            ('APPLICATION', 'pos',       'view'),
            ('APPLICATION', 'orders',    'view'),
            ('APPLICATION', 'catalog',   'view'),
            ('APPLICATION', 'locations', 'view'),
            ('APPLICATION', 'coupons',   'view'),
            ('APPLICATION', 'users',     'view'),
            ('APPLICATION', 'settings',  'view'),
            -- workspace
            ('APPLICATION', 'workspace', 'read'),
            ('APPLICATION', 'workspace', 'update'),
            ('APPLICATION', 'workspace', 'manage'),
            -- organization
            ('APPLICATION', 'organization', 'read'),
            ('APPLICATION', 'organization', 'create'),
            ('APPLICATION', 'organization', 'update'),
            ('APPLICATION', 'organization', 'delete'),
            -- items
            ('APPLICATION', 'items', 'read'),
            ('APPLICATION', 'items', 'create'),
            ('APPLICATION', 'items', 'update'),
            ('APPLICATION', 'items', 'delete'),
            -- categories
            ('APPLICATION', 'categories', 'read'),
            ('APPLICATION', 'categories', 'create'),
            ('APPLICATION', 'categories', 'update'),
            ('APPLICATION', 'categories', 'delete'),
            -- areas
            ('APPLICATION', 'areas', 'read'),
            ('APPLICATION', 'areas', 'create'),
            ('APPLICATION', 'areas', 'update'),
            ('APPLICATION', 'areas', 'delete'),
            -- tables
            ('APPLICATION', 'tables', 'read'),
            ('APPLICATION', 'tables', 'create'),
            ('APPLICATION', 'tables', 'update'),
            ('APPLICATION', 'tables', 'delete'),
            -- reviews
            ('APPLICATION', 'reviews', 'read'),
            ('APPLICATION', 'reviews', 'create'),
            ('APPLICATION', 'reviews', 'update'),
            ('APPLICATION', 'reviews', 'delete'),
            ('APPLICATION', 'reviews', 'moderate'),
            -- orders
            ('APPLICATION', 'orders', 'read'),
            ('APPLICATION', 'orders', 'create'),
            ('APPLICATION', 'orders', 'update'),
            ('APPLICATION', 'orders', 'delete'),
            ('APPLICATION', 'orders', 'status'),
            ('APPLICATION', 'orders', 'payment'),
            -- status
            ('APPLICATION', 'status', 'update'),
            -- users
            ('APPLICATION', 'users', 'read'),
            ('APPLICATION', 'users', 'create'),
            ('APPLICATION', 'users', 'update'),
            ('APPLICATION', 'users', 'delete'),
            -- dashboard
            ('APPLICATION', 'dashboard', 'read'),
            -- coupons
            ('APPLICATION', 'coupons', 'read'),
            ('APPLICATION', 'coupons', 'create'),
            ('APPLICATION', 'coupons', 'update'),
            ('APPLICATION', 'coupons', 'delete')
    ),
    resolved AS (
        SELECT p.id AS permission_id
        FROM   perms v
        JOIN   permissions p
               ON  p.category = v.category
               AND p.resource  = v.resource
               AND p.action    = v.action
    )
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, resolved.permission_id
FROM   r, resolved
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. MANAGER  (role_type = 1)
--    Module views : dashboard, pos, orders, catalog, locations,
--                   coupons, users  (NO settings/view)               (7)
--    workspace    : read                                              (1)
--    organization : read, update                                      (2)
--    items        : read, create, update, delete                      (4)
--    categories   : read, create, update, delete                      (4)
--    areas        : read, create, update, delete                      (4)
--    tables       : read, create, update, delete                      (4)
--    reviews      : read, create, update, moderate  (NO delete)       (4)
--    orders       : read, create, update, status, payment (NO delete) (5)
--    status       : update                                            (1)
--    users        : read, create  (NO update/delete)                  (2)
--    dashboard    : read                                              (1)
--    coupons      : read, create, update  (NO delete)                 (3)
-- ---------------------------------------------------------------------------
WITH
    r AS (
        SELECT id FROM roles WHERE name = 'Manager'
    ),
    perms (category, resource, action) AS (
        VALUES
            -- module views
            ('APPLICATION', 'dashboard', 'view'),
            ('APPLICATION', 'pos',       'view'),
            ('APPLICATION', 'orders',    'view'),
            ('APPLICATION', 'catalog',   'view'),
            ('APPLICATION', 'locations', 'view'),
            ('APPLICATION', 'coupons',   'view'),
            ('APPLICATION', 'users',     'view'),
            -- workspace
            ('APPLICATION', 'workspace', 'read'),
            -- organization
            ('APPLICATION', 'organization', 'read'),
            ('APPLICATION', 'organization', 'update'),
            -- items
            ('APPLICATION', 'items', 'read'),
            ('APPLICATION', 'items', 'create'),
            ('APPLICATION', 'items', 'update'),
            ('APPLICATION', 'items', 'delete'),
            -- categories
            ('APPLICATION', 'categories', 'read'),
            ('APPLICATION', 'categories', 'create'),
            ('APPLICATION', 'categories', 'update'),
            ('APPLICATION', 'categories', 'delete'),
            -- areas
            ('APPLICATION', 'areas', 'read'),
            ('APPLICATION', 'areas', 'create'),
            ('APPLICATION', 'areas', 'update'),
            ('APPLICATION', 'areas', 'delete'),
            -- tables
            ('APPLICATION', 'tables', 'read'),
            ('APPLICATION', 'tables', 'create'),
            ('APPLICATION', 'tables', 'update'),
            ('APPLICATION', 'tables', 'delete'),
            -- reviews (no delete)
            ('APPLICATION', 'reviews', 'read'),
            ('APPLICATION', 'reviews', 'create'),
            ('APPLICATION', 'reviews', 'update'),
            ('APPLICATION', 'reviews', 'moderate'),
            -- orders (no delete)
            ('APPLICATION', 'orders', 'read'),
            ('APPLICATION', 'orders', 'create'),
            ('APPLICATION', 'orders', 'update'),
            ('APPLICATION', 'orders', 'status'),
            ('APPLICATION', 'orders', 'payment'),
            -- status
            ('APPLICATION', 'status', 'update'),
            -- users (no update/delete)
            ('APPLICATION', 'users', 'read'),
            ('APPLICATION', 'users', 'create'),
            -- dashboard
            ('APPLICATION', 'dashboard', 'read'),
            -- coupons (no delete)
            ('APPLICATION', 'coupons', 'read'),
            ('APPLICATION', 'coupons', 'create'),
            ('APPLICATION', 'coupons', 'update')
    ),
    resolved AS (
        SELECT p.id AS permission_id
        FROM   perms v
        JOIN   permissions p
               ON  p.category = v.category
               AND p.resource  = v.resource
               AND p.action    = v.action
    )
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, resolved.permission_id
FROM   r, resolved
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. USER  (role_type = 1)
--    orders : view, read, create, status, payment                     (5)
-- ---------------------------------------------------------------------------
WITH
    r AS (
        SELECT id FROM roles WHERE name = 'User'
    ),
    perms (category, resource, action) AS (
        VALUES
            ('APPLICATION', 'orders', 'view'),
            ('APPLICATION', 'orders', 'read'),
            ('APPLICATION', 'orders', 'create'),
            ('APPLICATION', 'orders', 'status'),
            ('APPLICATION', 'orders', 'payment')
    ),
    resolved AS (
        SELECT p.id AS permission_id
        FROM   perms v
        JOIN   permissions p
               ON  p.category = v.category
               AND p.resource  = v.resource
               AND p.action    = v.action
    )
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, resolved.permission_id
FROM   r, resolved
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. SUPERADMIN  (role_type = 0)
--    Module views : dashboard, workspaces, users, roles,
--                   billing, registration, settings                   (7)
--    workspaces   : read, create, update, delete                      (4)
--    billing      : read, update, subscription                        (3)
--    registration : read, create, delete                              (3)
--    roles        : read, create, update, delete                      (4)
--    users        : read, create, update, delete                      (4)
--    permissions  : read, create, update, delete                      (4)
-- ---------------------------------------------------------------------------
WITH
    r AS (
        SELECT id FROM roles WHERE name = 'SuperAdmin'
    ),
    perms (category, resource, action) AS (
        VALUES
            -- module views
            ('SYSTEM', 'dashboard',    'view'),
            ('SYSTEM', 'workspaces',   'view'),
            ('SYSTEM', 'users',        'view'),
            ('SYSTEM', 'roles',        'view'),
            ('SYSTEM', 'billing',      'view'),
            ('SYSTEM', 'registration', 'view'),
            ('SYSTEM', 'settings',     'view'),
            -- workspaces
            ('SYSTEM', 'workspaces', 'read'),
            ('SYSTEM', 'workspaces', 'create'),
            ('SYSTEM', 'workspaces', 'update'),
            ('SYSTEM', 'workspaces', 'delete'),
            -- billing
            ('SYSTEM', 'billing', 'read'),
            ('SYSTEM', 'billing', 'update'),
            ('SYSTEM', 'billing', 'subscription'),
            -- registration
            ('SYSTEM', 'registration', 'read'),
            ('SYSTEM', 'registration', 'create'),
            ('SYSTEM', 'registration', 'delete'),
            -- roles
            ('SYSTEM', 'roles', 'read'),
            ('SYSTEM', 'roles', 'create'),
            ('SYSTEM', 'roles', 'update'),
            ('SYSTEM', 'roles', 'delete'),
            -- users
            ('SYSTEM', 'users', 'read'),
            ('SYSTEM', 'users', 'create'),
            ('SYSTEM', 'users', 'update'),
            ('SYSTEM', 'users', 'delete'),
            -- permissions
            ('SYSTEM', 'permissions', 'read'),
            ('SYSTEM', 'permissions', 'create'),
            ('SYSTEM', 'permissions', 'update'),
            ('SYSTEM', 'permissions', 'delete')
    ),
    resolved AS (
        SELECT p.id AS permission_id
        FROM   perms v
        JOIN   permissions p
               ON  p.category = v.category
               AND p.resource  = v.resource
               AND p.action    = v.action
    )
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, resolved.permission_id
FROM   r, resolved
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. ADMIN  (role_type = 0)
--    Module views : dashboard, workspaces, users, billing,
--                   registration, settings  (NO roles/view)           (6)
--    workspaces   : read, update  (NO create/delete)                  (2)
--    billing      : read, update, subscription                        (3)
--    registration : read, create, delete                              (3)
--    users        : read, create, update  (NO delete)                 (3)
--    permissions  : read                                              (1)
-- ---------------------------------------------------------------------------
WITH
    r AS (
        SELECT id FROM roles WHERE name = 'Admin'
    ),
    perms (category, resource, action) AS (
        VALUES
            -- module views (no roles/view)
            ('SYSTEM', 'dashboard',    'view'),
            ('SYSTEM', 'workspaces',   'view'),
            ('SYSTEM', 'users',        'view'),
            ('SYSTEM', 'billing',      'view'),
            ('SYSTEM', 'registration', 'view'),
            ('SYSTEM', 'settings',     'view'),
            -- workspaces (no create/delete)
            ('SYSTEM', 'workspaces', 'read'),
            ('SYSTEM', 'workspaces', 'update'),
            -- billing
            ('SYSTEM', 'billing', 'read'),
            ('SYSTEM', 'billing', 'update'),
            ('SYSTEM', 'billing', 'subscription'),
            -- registration
            ('SYSTEM', 'registration', 'read'),
            ('SYSTEM', 'registration', 'create'),
            ('SYSTEM', 'registration', 'delete'),
            -- users (no delete)
            ('SYSTEM', 'users', 'read'),
            ('SYSTEM', 'users', 'create'),
            ('SYSTEM', 'users', 'update'),
            -- permissions (read only)
            ('SYSTEM', 'permissions', 'read')
    ),
    resolved AS (
        SELECT p.id AS permission_id
        FROM   perms v
        JOIN   permissions p
               ON  p.category = v.category
               AND p.resource  = v.resource
               AND p.action    = v.action
    )
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, resolved.permission_id
FROM   r, resolved
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. OPERATOR  (role_type = 0)
--    Module views : dashboard, workspaces, users, billing,
--                   registration  (NO roles/view, NO settings/view)   (5)
--    workspaces   : read                                              (1)
--    billing      : read                                              (1)
--    registration : read                                              (1)
--    roles        : read                                              (1)
--    users        : read                                              (1)
--    permissions  : read                                              (1)
-- ---------------------------------------------------------------------------
WITH
    r AS (
        SELECT id FROM roles WHERE name = 'Operator'
    ),
    perms (category, resource, action) AS (
        VALUES
            -- module views (no roles/view, no settings/view)
            ('SYSTEM', 'dashboard',    'view'),
            ('SYSTEM', 'workspaces',   'view'),
            ('SYSTEM', 'users',        'view'),
            ('SYSTEM', 'billing',      'view'),
            ('SYSTEM', 'registration', 'view'),
            -- workspaces
            ('SYSTEM', 'workspaces', 'read'),
            -- billing
            ('SYSTEM', 'billing', 'read'),
            -- registration
            ('SYSTEM', 'registration', 'read'),
            -- roles
            ('SYSTEM', 'roles', 'read'),
            -- users
            ('SYSTEM', 'users', 'read'),
            -- permissions
            ('SYSTEM', 'permissions', 'read')
    ),
    resolved AS (
        SELECT p.id AS permission_id
        FROM   perms v
        JOIN   permissions p
               ON  p.category = v.category
               AND p.resource  = v.resource
               AND p.action    = v.action
    )
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, resolved.permission_id
FROM   r, resolved
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Verification: role name + permission count
-- ---------------------------------------------------------------------------
SELECT
    r.name                          AS role_name,
    COUNT(rp.permission_id)         AS permission_count
FROM       roles            r
LEFT JOIN  role_permissions rp ON rp.role_id = r.id
GROUP BY   r.name
ORDER BY   r.name;

COMMIT;
