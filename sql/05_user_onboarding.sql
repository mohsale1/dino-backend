-- ============================================================
-- DINO ONBOARDING SCRIPT
-- Email    : admin@dino-demo.com
-- Password : Admin@1234
-- ============================================================

BEGIN;

-- 1. Role
INSERT INTO roles (name, description, role_type, is_active, created_at, updated_at)
VALUES ('Owner', 'Workspace owner with full access', 1, true, now(), now())
ON CONFLICT (name) DO NOTHING;

-- 2. Workspace
INSERT INTO workspaces (name, description, owner_id, is_active, is_verified, created_at, updated_at)
VALUES ('Dino Demo Restaurant', 'Demo workspace for testing', NULL, true, true, now(), now());

-- 3. Workspace Billing
INSERT INTO workspace_billing (workspace_id, plan, plan_status, created_at, updated_at)
VALUES (
    (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant'),
    'free', 'active', now(), now()
);

-- 4. Persona
INSERT INTO personas (
    name, description, workspace_id,
    persona_type, order_type,
    address, city, state, country, postal_code,
    phone, email,
    is_open, is_deactivated, is_active,
    created_at, updated_at
)
VALUES (
    'Main Branch', 'Primary outlet',
    (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant'),
    0, 0,
    '123 Food Street', 'Hyderabad', 'Telangana', 'India', '500001',
    '8121137113', 'branch@dino-demo.com',
    true, false, true,
    now(), now()
);

-- 5. Link workspace <-> persona
INSERT INTO workspace_personas (workspace_id, persona_id)
VALUES (
    (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant'),
    (SELECT id FROM personas WHERE name = 'Main Branch'
        AND workspace_id = (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant'))
)
ON CONFLICT DO NOTHING;

-- 6. Admin User
INSERT INTO users (
    user_type, email, password_hash,
    first_name, last_name, phone,
    role_id, workspace_id,
    is_active, created_at, updated_at
)
VALUES (
    1,
    'admin@dino-demo.com',
    '$2b$12$1K8SAT5HsKsfIUFmkzwgAukW8d/qS/GAjT7hJasTX9JABG4F6ksxy',
    'Demo', 'Admin', '8121137113',
    (SELECT id FROM roles WHERE name = 'Owner' AND role_type = 1),
    (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant'),
    true, now(), now()
);

-- 7. Back-fill workspace owner_id
UPDATE workspaces
SET owner_id = (SELECT id FROM users WHERE email = 'admin@dino-demo.com')
WHERE name = 'Dino Demo Restaurant';

COMMIT;


BEGIN;



-- Fix the id column to auto-generate
ALTER TABLE workspace_requests 
ALTER COLUMN id SET DEFAULT nextval(pg_get_serial_sequence('workspace_requests', 'id'));

-- Step 1: Create a sequence
CREATE SEQUENCE IF NOT EXISTS workspace_requests_id_seq
    START WITH 1 INCREMENT BY 1;

-- Step 2: Set it as the default for id
ALTER TABLE workspace_requests 
    ALTER COLUMN id SET DEFAULT nextval('workspace_requests_id_seq');

-- Step 3: Now insert
INSERT INTO workspace_requests (
    email, user_id, workspace_id,
    status, is_active,
    created_at, updated_at
)
SELECT
    'admin@dino-demo.com',
    u.id,
    w.id,
    'pending',
    true,
    now(), now()
FROM users u, workspaces w
WHERE u.email = 'admin@dino-demo.com'
  AND w.name  = 'Dino Demo Restaurant';

-- 9. Billing Detail (GST / legal info)
INSERT INTO billing_details (
    workspace_id,
    legal_name, trade_name,
    billing_email, billing_phone,
    address_line1, city, state, country, postal_code,
    created_at, updated_at
)
VALUES (
    (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant'),
    'Dino Demo Pvt Ltd', 'Dino Demo Restaurant',
    'billing@dino-demo.com', '8121137113',
    '123 Food Street', 'Hyderabad', 'Telangana', 'India', '500001',
    now(), now()
) ON CONFLICT (workspace_id) DO NOTHING;

-- 10. Update workspace_billing with full billing info
UPDATE workspace_billing
SET
    billing_name    = 'Dino Demo Restaurant',
    billing_email   = 'billing@dino-demo.com',
    billing_phone   = '8121137113',
    billing_address = '123 Food Street',
    billing_city    = 'Hyderabad',
    billing_state   = 'Telangana',
    billing_country = 'India',
    billing_postal_code = '500001',
    billing_cycle   = 'monthly',
    updated_at      = now()
WHERE workspace_id = (SELECT id FROM workspaces WHERE name = 'Dino Demo Restaurant');

COMMIT;

-- ============================================================
-- FULL VERIFY
-- ============================================================
SELECT
    u.id            AS user_id,
    u.email,
    u.first_name || ' ' || u.last_name AS full_name,
    u.is_active     AS user_active,
    r.name          AS role,
    w.id            AS workspace_id,
    w.name          AS workspace,
    w.is_active     AS workspace_active,
    wb.plan,
    wb.plan_status,
    wr.status       AS request_status,
    bd.legal_name,
    p.name          AS persona
FROM users u
JOIN roles              r  ON r.id  = u.role_id
JOIN workspaces         w  ON w.id  = u.workspace_id
JOIN workspace_billing  wb ON wb.workspace_id = w.id
LEFT JOIN workspace_requests wr ON wr.workspace_id = w.id AND wr.is_active = true
LEFT JOIN billing_details    bd ON bd.workspace_id = w.id
JOIN workspace_personas wp ON wp.workspace_id = w.id
JOIN personas           p  ON p.id = wp.persona_id
WHERE u.email = 'admin@dino-demo.com';

