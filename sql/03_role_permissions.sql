-- =============================================================================
-- Seed: role_permissions
-- Assigns permissions to roles using name/category/resource/action lookups.
-- Safe to re-run (idempotent) — INSERT only if the (role_id, permission_id)
-- pair does not already exist. Uses NOT EXISTS on the composite PK.
-- No hardcoded IDs anywhere.
-- =============================================================================
--
-- Roles seeded:
--   SYSTEM      roles (role_type = 0): SuperAdmin, Admin, Operator
--   APPLICATION roles (role_type = 1): Owner, Manager, User
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. SUPERADMIN  (role_type = 0)
--    Module views : dashboard, workspaces, approvals, users, billing,
--                   referrals, roles, appearance, settings                (9)
--    workspaces   : read, create, update, delete, approve                 (5)
--    billing      : read, update, subscription                            (3)
--    referrals    : read                                                   (1)
--    roles        : read, create, update, delete                          (4)
--    users        : read, create, update, delete                          (4)
--    permissions  : read, create, update, delete                          (4)
--    Total        : 9 views + 21 functional = 30
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN (VALUES
    -- module views (9)
    ('SYSTEM', 'dashboard',  'view'),
    ('SYSTEM', 'workspaces', 'view'),
    ('SYSTEM', 'approvals',  'view'),
    ('SYSTEM', 'users',      'view'),
    ('SYSTEM', 'billing',    'view'),
    ('SYSTEM', 'referrals',  'view'),
    ('SYSTEM', 'roles',      'view'),
    ('SYSTEM', 'appearance', 'view'),
    ('SYSTEM', 'settings',   'view'),
    -- workspaces
    ('SYSTEM', 'workspaces', 'read'),
    ('SYSTEM', 'workspaces', 'create'),
    ('SYSTEM', 'workspaces', 'update'),
    ('SYSTEM', 'workspaces', 'delete'),
    ('SYSTEM', 'workspaces', 'approve'),
    -- billing
    ('SYSTEM', 'billing', 'read'),
    ('SYSTEM', 'billing', 'update'),
    ('SYSTEM', 'billing', 'subscription'),
    -- referrals
    ('SYSTEM', 'referrals', 'read'),
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
) AS v(category, resource, action)
JOIN permissions p ON p.category = v.category
                  AND p.resource  = v.resource
                  AND p.action    = v.action
WHERE r.name = 'SuperAdmin'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id       = r.id
        AND rp.permission_id = p.id
  );

-- ---------------------------------------------------------------------------
-- 2. ADMIN  (role_type = 0)  — read-only across all system modules + approve
--    Module views : dashboard, workspaces, approvals, users, billing,
--                   referrals, roles, appearance, settings                (9)
--    workspaces   : read, approve                                          (2)
--    billing      : read                                                   (1)
--    referrals    : read                                                   (1)
--    roles        : read                                                   (1)
--    users        : read                                                   (1)
--    permissions  : read                                                   (1)
--    Total        : 9 views + 7 functional = 16
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN (VALUES
    -- module views (9)
    ('SYSTEM', 'dashboard',  'view'),
    ('SYSTEM', 'workspaces', 'view'),
    ('SYSTEM', 'approvals',  'view'),
    ('SYSTEM', 'users',      'view'),
    ('SYSTEM', 'billing',    'view'),
    ('SYSTEM', 'referrals',  'view'),
    ('SYSTEM', 'roles',      'view'),
    ('SYSTEM', 'appearance', 'view'),
    ('SYSTEM', 'settings',   'view'),
    -- workspaces
    ('SYSTEM', 'workspaces', 'read'),
    ('SYSTEM', 'workspaces', 'approve'),
    -- billing (read only)
    ('SYSTEM', 'billing', 'read'),
    -- referrals (read only)
    ('SYSTEM', 'referrals', 'read'),
    -- roles (read only)
    ('SYSTEM', 'roles', 'read'),
    -- users (read only)
    ('SYSTEM', 'users', 'read'),
    -- permissions (read only)
    ('SYSTEM', 'permissions', 'read')
) AS v(category, resource, action)
JOIN permissions p ON p.category = v.category
                  AND p.resource  = v.resource
                  AND p.action    = v.action
WHERE r.name = 'Admin'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id       = r.id
        AND rp.permission_id = p.id
  );

-- ---------------------------------------------------------------------------
-- 3. OPERATOR  (role_type = 0)
--    Module views : workspaces, billing                                    (2)
--    workspaces   : read                                                   (1)
--    billing      : read                                                   (1)
--    Total        : 2 views + 2 functional = 4
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN (VALUES
    -- module views (2)
    ('SYSTEM', 'workspaces', 'view'),
    ('SYSTEM', 'billing',    'view'),
    -- workspaces
    ('SYSTEM', 'workspaces', 'read'),
    -- billing
    ('SYSTEM', 'billing', 'read')
) AS v(category, resource, action)
JOIN permissions p ON p.category = v.category
                  AND p.resource  = v.resource
                  AND p.action    = v.action
WHERE r.name = 'Operator'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id       = r.id
        AND rp.permission_id = p.id
  );

-- ---------------------------------------------------------------------------
-- 4. OWNER  (role_type = 1)
--    Module views : dashboard, pos, orders, catalog, locations,
--                   coupons, users, settings, persona                     (9)
--    workspace    : read, update, manage                                   (3)
--    organization : read, create, update, delete                           (4)
--    items        : read, create, update, delete                           (4)
--    categories   : read, create, update, delete                           (4)
--    areas        : read, create, update, delete                           (4)
--    tables       : read, create, update, delete                           (4)
--    reviews      : read, create, update, delete, moderate                 (5)
--    orders       : read, create, update, delete, status, payment          (6)
--    status       : update                                                 (1)
--    users        : read, create, update, delete                           (4)
--    dashboard    : read                                                   (1)
--    coupons      : read, create, update, delete                           (4)
--    persona      : read, create, update, delete                           (4)
--    Total        : 9 views + 48 functional = 57
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN (VALUES
    -- module views (9)
    ('APPLICATION', 'dashboard', 'view'),
    ('APPLICATION', 'pos',       'view'),
    ('APPLICATION', 'orders',    'view'),
    ('APPLICATION', 'catalog',   'view'),
    ('APPLICATION', 'locations', 'view'),
    ('APPLICATION', 'coupons',   'view'),
    ('APPLICATION', 'users',     'view'),
    ('APPLICATION', 'settings',  'view'),
    ('APPLICATION', 'persona',   'view'),
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
    ('APPLICATION', 'coupons', 'delete'),
    -- persona
    ('APPLICATION', 'persona', 'read'),
    ('APPLICATION', 'persona', 'create'),
    ('APPLICATION', 'persona', 'update'),
    ('APPLICATION', 'persona', 'delete')
) AS v(category, resource, action)
JOIN permissions p ON p.category = v.category
                  AND p.resource  = v.resource
                  AND p.action    = v.action
WHERE r.name = 'Owner'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id       = r.id
        AND rp.permission_id = p.id
  );

-- ---------------------------------------------------------------------------
-- 5. MANAGER  (role_type = 1)
--    Module views : dashboard, pos, orders, catalog, locations,
--                   coupons, users, settings                              (8)  (NO persona view)
--    workspace    : read, update, manage                                   (3)
--    organization : read, create, update, delete                           (4)
--    items        : read, create, update, delete                           (4)
--    categories   : read, create, update, delete                           (4)
--    areas        : read, create, update, delete                           (4)
--    tables       : read, create, update, delete                           (4)
--    reviews      : read, create, update, delete, moderate                 (5)
--    orders       : read, create, update, delete, status, payment          (6)
--    status       : update                                                 (1)
--    users        : read, create, update, delete                           (4)
--    dashboard    : read                                                   (1)
--    coupons      : read, create, update, delete                           (4)
--    persona      : read                                                   (1)  (read only — no view, no create/update/delete)
--    Total        : 8 views + 45 functional = 53
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN (VALUES
    -- module views (8)
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
    ('APPLICATION', 'coupons', 'delete'),
    -- persona (read only)
    ('APPLICATION', 'persona', 'read')
) AS v(category, resource, action)
JOIN permissions p ON p.category = v.category
                  AND p.resource  = v.resource
                  AND p.action    = v.action
WHERE r.name = 'Manager'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id       = r.id
        AND rp.permission_id = p.id
  );

-- ---------------------------------------------------------------------------
-- 6. USER  (role_type = 1)
--    Module views : orders                                                 (1)
--    orders       : status                                                 (1)
--    Total        : 1 view + 1 functional = 2
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN (VALUES
    -- module views (1)
    ('APPLICATION', 'orders', 'view'),
    -- orders
    ('APPLICATION', 'orders', 'status')
) AS v(category, resource, action)
JOIN permissions p ON p.category = v.category
                  AND p.resource  = v.resource
                  AND p.action    = v.action
WHERE r.name = 'User'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id       = r.id
        AND rp.permission_id = p.id
  );

-- ---------------------------------------------------------------------------
-- Verification: role name + permission count
--   Expected:
--   SuperAdmin : 30  (9 views + 21 functional)
--   Admin      : 16  (9 views + 7 functional)
--   Operator   : 4   (2 views + 2 functional)
--   Owner      : 57  (9 views + 48 functional)
--   Manager    : 53  (8 views + 45 functional)
--   User       : 2   (1 view  + 1 functional)
-- ---------------------------------------------------------------------------
SELECT
    r.name                  AS role_name,
    COUNT(rp.permission_id) AS permission_count
FROM       roles            r
LEFT JOIN  role_permissions rp ON rp.role_id = r.id
GROUP BY   r.name
ORDER BY   r.name;

COMMIT;
