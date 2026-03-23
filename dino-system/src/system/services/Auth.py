from src.base.BaseAuth import BaseAuth
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository
from src.config.Settings import settings

class SystemAuthService(BaseAuth):
    """System authentication service"""
    
    def __init__(self):
        user_repo = UserRepository("system_users")
        role_repo = RoleRepository()
        super().__init__(user_repo, role_repo)
    
    def login(self, email: str, password: str):
        """Login system user"""
        user = self.authenticate_user(email, password)
        
        if not user:
            return None
        
        # Get user with role
        user_with_role = self.get_user_with_role(user['id'])
        
        # If JWT is disabled, return user without tokens
        if not settings.ENABLE_JWT:
            return {
                "access_token": None,
                "refresh_token": None,
                "token_type": "none",
                "user": user_with_role,
                "jwt_enabled": False
            }
        
        # Create tokens with user_type
        token_data = {
            "sub": user['id'],
            "email": user['email'],
            "user_type": "system"
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_with_role,
            "jwt_enabled": True
        }