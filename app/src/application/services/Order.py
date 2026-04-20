from src.base.BaseService import BaseService
from src.repositories.OrderRepository import OrderRepository
from typing import Dict, Any, Optional
import random
import string
from datetime import datetime, timezone

class OrderService(BaseService):
    """Order service"""

    def __init__(self):
        repository = OrderRepository()
        super().__init__(repository)

    def generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"ORD-{timestamp}-{random_suffix}"

    def create_order(self, data: Dict[str, Any]) -> str:
        """Create new order and return the new order ID"""
        # Generate order number
        data['order_number'] = self.generate_order_number()

        # Only calculate total_amount from items if caller has not already provided it
        if 'total_amount' not in data:
            data['total_amount'] = sum(item.get('total_price', 0) for item in data.get('items', []))

        # Set default status
        if 'status' not in data:
            data['status'] = 'pending'

        if 'payment_status' not in data:
            data['payment_status'] = 'unpaid'

        # Set order date
        data['order_date'] = datetime.now(timezone.utc)

        # Resolve workspace_id from organization when not already supplied
        organization_id = data.get('organization_id')
        if organization_id and 'workspace_id' not in data:
            from src.repositories.OrganizationRepository import OrganizationRepository
            org_repo = OrganizationRepository()
            organization = org_repo.get_by_id(organization_id)
            if organization:
                data['workspace_id'] = organization.get('workspace_id')

        created = self.create(data)
        return created['id']


    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status"""
        return self.update(order_id, {"status": status})

    def update_payment_status(self, order_id: str, payment_status: str) -> bool:
        """Update payment status"""
        return self.update(order_id, {"payment_status": payment_status})

    def get_statistics(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Return aggregated order statistics for the given filters.

        Supported filter keys (all optional except at least one scoping key):
          workspace_id, organization_id, start_date, end_date

        Date values may be ISO-format strings or datetime objects.
        """
        # Work on a copy so the caller's dict is never mutated
        filters = dict(filters)

        # Separate date-range filters from Firestore equality filters
        start_date = filters.pop('start_date', None)
        end_date = filters.pop('end_date', None)

        # Parse date boundaries when provided as strings
        def _parse_dt(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            try:
                dt = datetime.fromisoformat(str(value))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None

        start_dt = _parse_dt(start_date)
        end_dt = _parse_dt(end_date)

        # Fetch all orders matching the equality filters
        orders = self.get_all(filters=filters if filters else None)

        # Apply date-range filter in memory
        if start_dt or end_dt:
            def _in_range(order: Dict[str, Any]) -> bool:
                created = order.get('created_at') or order.get('order_date')
                if created is None:
                    return False
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except ValueError:
                        return False
                if not isinstance(created, datetime):
                    return False
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if start_dt and created < start_dt:
                    return False
                if end_dt and created > end_dt:
                    return False
                return True

            orders = [o for o in orders if _in_range(o)]

        # Compute today's boundaries (UTC)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        total_orders = len(orders)
        total_revenue = 0.0
        orders_by_status: Dict[str, int] = {}
        today_orders = 0
        today_revenue = 0.0

        for order in orders:
            order_status = order.get('status', 'unknown')
            orders_by_status[order_status] = orders_by_status.get(order_status, 0) + 1

            # Resolve the order timestamp once for reuse below
            created = order.get('created_at') or order.get('order_date')
            if created is not None:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except ValueError:
                        created = None
                if isinstance(created, datetime):
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)

            # Exclude cancelled orders from all revenue calculations
            if order_status != 'cancelled':
                amount = float(order.get('total_amount') or 0)
                total_revenue += amount

                if created is not None and isinstance(created, datetime):
                    if today_start <= created <= today_end:
                        today_orders += 1
                        today_revenue += amount
            else:
                # Still count today's cancelled orders in today_orders for status tracking
                if created is not None and isinstance(created, datetime):
                    if today_start <= created <= today_end:
                        today_orders += 1

        avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0.0

        return {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "orders_by_status": orders_by_status,
            "avg_order_value": round(avg_order_value, 2),
            "today_orders": today_orders,
            "today_revenue": round(today_revenue, 2),
        }