from src.base.BaseUser import BaseUser
from typing import List

class ApplicationUser(BaseUser):
    """Application user model for workspace users"""
    
    def __init__(self):
        super().__init__()
        self.workspace_ids: List[str] = []  # User can be part of multiple workspaces
        self.default_workspace_id: str = ""  # Default workspace when user logs in