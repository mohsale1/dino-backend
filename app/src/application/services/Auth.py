from src.base.BaseAuth import BaseAuth
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.OrganizationRepository import OrganizationRepository
from src.core.Security import get_password_hash
from datetime import datetime, timezone
from typing import Dict, Any

class ApplicationAuthService(BaseAuth):
    """Application authentication service"""

    def __init__(self):
        user_repo = UserRepository("application_users")
        role_repo = RoleRepository()
        super().__init__(user_repo, role_repo)
        # Store repositories as instance variables for easy access
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.workspace_repo = WorkspaceRepository()
        self.organization_repo = OrganizationRepository()
        self.system_user_repo = UserRepository("system_users")

    def login(self, email: str, password: str):
        """Login application user"""
        user = self.authenticate_user(email, password)

        if not user:
            return None

        # Create tokens with user_type
        token_data = {
            "sub": user['id'],
            "email": user['email'],
            "user_type": "application"
        }

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        # Get user with role
        user_with_role = self.get_user_with_role(user['id'])

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_with_role
        }

    def signup(self, referral_code: str, workspace_data: Dict[str, Any], organization_data: Dict[str, Any], admin_data: Dict[str, Any], billing_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Complete signup process: create workspace, organization, and admin user.
        Validates referral code and tracks who onboarded the workspace.
        Performs compensating deletes on partial failure to avoid orphaned records.
        """
        created_workspace = None
        created_organization = None

        try:
            # 1. Validate referral code (4-digit system user ID)
            if not referral_code or not referral_code.isdigit() or len(referral_code) != 4:
                raise ValueError("Invalid referral code. Must be a 4-digit number.")

            # Check if system user exists with this ID
            referred_by_user = self.system_user_repo.get_by_id(referral_code)
            if not referred_by_user:
                raise ValueError(f"Invalid referral code '{referral_code}'. User not found.")

            if not referred_by_user.get('is_active', False):
                raise ValueError(f"Referral code '{referral_code}' is inactive. Please contact support.")

            referred_by = referral_code

            # 2. Check if admin email already exists
            existing_user = self.user_repo.get_by_email(admin_data['email'])
            if existing_user:
                raise ValueError(f"User with email {admin_data['email']} already exists")

            # 3. Get or create Owner role for application users
            owner_role = self.role_repo.get_by_name_and_type("Owner", 1)
            if not owner_role:
                now = datetime.now(timezone.utc)
                owner_role_data = {
                    "name": "Owner",
                    "role_type": 1,  # Application role
                    "description": "Workspace owner with full access to all resources",
                    "permissions": ["workspace:*"],
                    "is_system": True,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now
                }
                owner_role = self.role_repo.create(owner_role_data)

            # 4. Create workspace
            now = datetime.now(timezone.utc)
            workspace = {
                "name": workspace_data['name'],
                "description": workspace_data.get('description'),
                "owner_id": "",  # Updated after admin user creation
                "organization_ids": [],  # Updated after organization creation
                "referred_by": referred_by,
                "created_at": now,
                "updated_at": now,
                "is_active": True
            }

            if billing_data:
                workspace.update({
                    "billing_name": billing_data.get('billing_name'),
                    "billing_email": billing_data.get('billing_email'),
                    "billing_phone": billing_data.get('billing_phone'),
                    "billing_address": billing_data.get('billing_address'),
                    "billing_city": billing_data.get('billing_city'),
                    "billing_state": billing_data.get('billing_state'),
                    "billing_postal_code": billing_data.get('billing_postal_code'),
                    "billing_country": billing_data.get('billing_country'),
                    "subscription_plan": "Free",
                    "subscription_status": "Active",
                    "next_billing_date": None
                })

            created_workspace = self.workspace_repo.create(workspace)
            workspace_id = created_workspace['id']

            # 5. Create organization — rollback workspace on failure
            try:
                now = datetime.now(timezone.utc)
                organization = {
                    "name": organization_data['name'],
                    "description": organization_data.get('description'),
                    "workspace_id": workspace_id,
                    "address": organization_data.get('address'),
                    "city": organization_data.get('city'),
                    "state": organization_data.get('state'),
                    "country": organization_data.get('country'),
                    "postal_code": organization_data.get('postal_code'),
                    "phone": organization_data.get('phone'),
                    "email": organization_data.get('email'),
                    "organization_type": organization_data.get('organization_type', 0),
                    "order_type": organization_data.get('order_type', 0),
                    "settings": {
                        "enable_qr_ordering": True,
                        "enable_counter_ordering": True,
                        "allow_order_type_switch": True,
                        "default_order_type": organization_data.get('order_type', 0),
                        "qr_code_prefix": "",
                        "table_qr_enabled": True,
                        "auto_print_orders": False,
                        "require_customer_details": False,
                        "industry_specific_attributes": {}
                    },
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True
                }
                created_organization = self.organization_repo.create(organization)
            except Exception:
                self.workspace_repo.delete(workspace_id)
                raise

            organization_id = created_organization['id']

            # 6. Create owner user — rollback workspace and organization on failure
            try:
                now = datetime.now(timezone.utc)
                owner_user = {
                    "email": admin_data['email'],
                    "password_hash": get_password_hash(admin_data['password']),
                    "first_name": admin_data['first_name'],
                    "last_name": admin_data['last_name'],
                    "phone": admin_data.get('phone'),
                    "role_id": owner_role['id'],
                    "workspace_id": workspace_id,
                    "organization_id": organization_id,
                    "created_at": now,
                    "updated_at": now,
                    "is_active": True
                }
                created_owner = self.user_repo.create(owner_user)
            except Exception:
                self.organization_repo.delete(organization_id)
                self.workspace_repo.delete(workspace_id)
                raise

            # 7. Update workspace with owner_id and organization list
            self.workspace_repo.update(workspace_id, {
                "owner_id": created_owner['id'],
                "organization_ids": [organization_id]
            })
            created_workspace['owner_id'] = created_owner['id']
            created_workspace['organization_ids'] = [organization_id]

            # 8. Remove sensitive data from response
            created_owner.pop('password_hash', None)

            return {
                "workspace": created_workspace,
                "organization": created_organization,
                "admin_user": created_owner
            }

        except Exception:
            raise