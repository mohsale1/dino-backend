from src.base.BaseUser import BaseUser

class SystemUser(BaseUser):
    """System user model for system administrators"""
    
    def __init__(self):
        super().__init__()
        self.is_system: bool = False  # True for built-in users that cannot be deleted
