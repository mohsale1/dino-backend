from src.base.BaseService import BaseService
from src.repositories.OrderRepository import OrderRepository
from typing import Dict, Any
import random
import string
from datetime import datetime

class OrderService(BaseService):
    """Order service"""
    
    def __init__(self):
        repository = OrderRepository()
        super().__init__(repository)
    
    def generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"ORD-{timestamp}-{random_suffix}"
    
    def create_order(self, data: Dict[str, Any]) -> str:
        """Create new order"""
        # Generate order number
        data['order_number'] = self.generate_order_number()
        
        # Calculate total amount from items
        total_amount = sum(item.get('total_price', 0) for item in data.get('items', []))
        data['total_amount'] = total_amount
        
        # Set default status
        if 'status' not in data:
            data['status'] = 'pending'
        
        if 'payment_status' not in data:
            data['payment_status'] = 'unpaid'
        
        # Set order date
        data['order_date'] = datetime.utcnow()
        
        # Get workspace_id from organization
        from src.repositories.OrganizationRepository import OrganizationRepository
        org_repo = OrganizationRepository()
        organization = org_repo.get_by_id(data.get('organization_id'))
        
        if organization:
            data['workspace_id'] = organization.get('workspace_id')
        
        return self.create(data)
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status"""
        return self.update(order_id, {"status": status})
    
    def update_payment_status(self, order_id: str, payment_status: str) -> bool:
        """Update payment status"""
        return self.update(order_id, {"payment_status": payment_status})