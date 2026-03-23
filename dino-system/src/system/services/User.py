from src.base.BaseService import BaseService
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository
from src.core.Security import get_password_hash
from typing import Dict, Any, List, Optional, Tuple

class SystemUserService(BaseService):
    def __init__(self):
        repository = UserRepository('system_users')
        super().__init__(repository)
        self.role_repo = RoleRepository()
    def create_system_user(self, user_data):
        if 'password' in user_data:
            user_data['password_hash'] = get_password_hash(user_data.pop('password'))
        user_data['is_active'] = user_data.get('is_active', True)
        user_data['is_deleted'] = False
        return self.repository.create_system_user(user_data)
    def get_user_with_role(self, user_id):
        user = self.get_by_id(user_id)
        if not user:
            return None
        if user.get('role_id'):
            role = self.role_repo.get_by_id(user['role_id'])
            if role:
                user['role'] = {'id': role['id'], 'name': role['name'], 'role_type': role.get('role_type', 0)}
        user.pop('password_hash', None)
        return user
    def get_all_users(self, include_deleted=False):
        return self.get_all(include_deleted=include_deleted)
    def update_user(self, user_id, data):
        if 'password' in data:
            data['password_hash'] = get_password_hash(data.pop('password'))
        return self.update(user_id, data)
    def soft_delete_user(self, user_id):
        return self.soft_delete(user_id)
    def restore_user(self, user_id):
        return self.restore(user_id)
    def get_paginated_users(self, page=1, page_size=10, include_deleted=False, order_by='created_at', order_direction='desc'):
        items, total, total_pages = self.get_paginated(page=page, page_size=page_size, include_deleted=include_deleted, order_by=order_by, order_direction=order_direction)
        sanitized = []
        for user in items:
            u = dict(user)
            u.pop('password_hash', None)
            if u.get('role_id'):
                role = self.role_repo.get_by_id(u['role_id'])
                if role:
                    u['role'] = {'id': role['id'], 'name': role['name']}
            sanitized.append(u)
        return sanitized, total, total_pages
    def email_exists(self, email):
        return bool(self.repository.get_all(filters={'email': email}))
    def validate_system_role(self, role_id):
        role = self.role_repo.get_by_id(role_id)
        if not role:
            return False
        return role.get('role_type') == 0
    def get_users_by_role(self, role_id):
        return self.repository.get_all(filters={'role_id': role_id})