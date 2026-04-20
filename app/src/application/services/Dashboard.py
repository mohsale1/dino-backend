import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.OrderRepository import OrderRepository
from src.repositories.ItemRepository import ItemRepository
from src.repositories.TableRepository import TableRepository
from src.repositories.CategoryRepository import CategoryRepository
from src.repositories.PersonaRepository import PersonaRepository


class DashboardService:
    """Dashboard service to aggregate data from multiple sources"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.item_repo = ItemRepository(db)
        self.table_repo = TableRepository(db)
        self.category_repo = CategoryRepository(db)
        self.org_repo = PersonaRepository(db)

    # ---------------------------------------------------------------------------
    # Date parsing helper
    # ---------------------------------------------------------------------------

    def _parse_date(self, value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
        """
        Convert an Optional[str] ISO date/datetime to an Optional[datetime].

        Returns None if value is None or empty.
        When end_of_day=True the boundary is set to 23:59:59.999999 UTC only
        when the input string carries no time component (length <= 10), so that
        an explicit datetime string such as "2024-01-31T12:00:00" is never
        silently overwritten.
        """
        if not value:
            return None

        from datetime import date as date_type

        stripped = value.strip()
        value = stripped.replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            dt = datetime.combine(date_type.fromisoformat(value[:10]), datetime.min.time())

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Only apply end-of-day when the caller supplied a plain date (no time part).
        if end_of_day and len(stripped) <= 10:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        return dt

    async def get_venue_dashboard(
        self,
        workspace_id: str,
        persona_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard data for a venue"""
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date, end_of_day=True)

        # Use SQL COUNT queries for scalar totals — avoids loading every row into
        # memory just to call len() on the result list.
        from sqlalchemy import select, func
        from src.models.Item import Item
        from src.models.Table import Table

        orders, item_count, table_count = await asyncio.gather(
            self.order_repo.get_orders_for_analytics(workspace_id, persona_id, start_dt, end_dt),
            self.db.scalar(
                select(func.count()).where(Item.workspace_id == workspace_id, Item.is_active == True)  # noqa: E712
            ),
            self.db.scalar(
                select(func.count()).where(Table.workspace_id == workspace_id, Table.is_active == True)  # noqa: E712
            ),
        )

        # We still need the full item/table/category rows for the analytics and
        # status breakdowns that follow, but we fetch them only once and reuse.
        items, tables, categories = await asyncio.gather(
            self.item_repo.get_by_workspace(workspace_id),
            self.table_repo.get_by_workspace(workspace_id),
            self.category_repo.get_by_workspace(workspace_id),
        )

        stats = self._calculate_stats(orders, items, tables, categories)
        analytics = self._calculate_analytics(orders, items, categories)
        recent_activity = self._get_recent_activity(orders)
        table_statuses = self._get_table_statuses(tables)

        return {
            'success': True,
            'data': {
                'stats': stats,
                'analytics': analytics,
                'recent_activity': recent_activity,
                'table_statuses': table_statuses,
                'summary': {
                    'total_orders': len(orders),
                    'total_revenue': stats.get('total_revenue', 0),
                    'total_tables': table_count or 0,
                    'total_menu_items': item_count or 0,
                    'active_menu_items': len([i for i in items if i.get('is_available')]),
                    'todays_revenue': stats.get('todays_revenue', 0),
                    'todays_orders': stats.get('todays_orders', 0),
                    'avg_order_value': stats.get('avg_order_value', 0),
                    'table_occupancy_rate': stats.get('table_occupancy_rate', 0),
                    'occupied_tables': len([t for t in tables if t.get('status') == 'occupied']),
                    'pending_orders': len([o for o in orders if o.get('status') == 'pending']),
                    'preparing_orders': len([o for o in orders if o.get('status') == 'preparing']),
                    'ready_orders': len([o for o in orders if o.get('status') == 'ready']),
                    'active_orders': len([o for o in orders if o.get('status') in ['pending', 'preparing', 'ready']])
                }
            }
        }

    async def get_stats_only(
        self,
        workspace_id: str,
        persona_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get only the stats portion of the dashboard.

        Uses SQL COUNT queries for item/table/category totals — avoids loading
        every row into memory when only scalar counts are needed.
        """
        from sqlalchemy import select, func
        from src.models.Item import Item
        from src.models.Table import Table
        from src.models.Category import Category

        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date, end_of_day=True)

        (
            orders,
            total_categories,
            active_items,
            total_tables,
            occupied_tables,
        ) = await asyncio.gather(
            self.order_repo.get_orders_for_analytics(workspace_id, persona_id, start_dt, end_dt),
            self.db.scalar(
                select(func.count()).where(
                    Category.workspace_id == workspace_id,
                    Category.is_active == True,  # noqa: E712
                )
            ),
            self.db.scalar(
                select(func.count()).where(
                    Item.workspace_id == workspace_id,
                    Item.is_active == True,  # noqa: E712
                    Item.is_available == True,  # noqa: E712
                )
            ),
            self.db.scalar(
                select(func.count()).where(
                    Table.workspace_id == workspace_id,
                    Table.is_active == True,  # noqa: E712
                )
            ),
            self.db.scalar(
                select(func.count()).where(
                    Table.workspace_id == workspace_id,
                    Table.is_active == True,  # noqa: E712
                    Table.status == "occupied",
                )
            ),
        )

        total_categories = total_categories or 0
        active_items = active_items or 0
        total_tables = total_tables or 0
        occupied_tables = occupied_tables or 0

        # Revenue / order calculations (mirrors _calculate_stats logic).
        total_revenue = sum(
            order.get("total_amount", 0)
            for order in orders
            if order.get("status") != "cancelled"
        )

        today = datetime.now(timezone.utc).date()
        todays_orders: List[Dict[str, Any]] = []
        todays_revenue = 0.0

        for order in orders:
            if order.get("status") == "cancelled":
                continue
            order_date = self._get_order_date(order)
            if order_date is None:
                continue
            if order_date.date() == today:
                todays_orders.append(order)
                todays_revenue += order.get("total_amount", 0)

        non_cancelled = [o for o in orders if o.get("status") != "cancelled"]
        avg_order_value = total_revenue / len(non_cancelled) if non_cancelled else 0
        table_occupancy_rate = (occupied_tables / total_tables * 100) if total_tables else 0

        return {
            "total_revenue": round(total_revenue, 2),
            "todays_revenue": round(todays_revenue, 2),
            "todays_orders": len(todays_orders),
            "avg_order_value": round(avg_order_value, 2),
            "table_occupancy_rate": round(table_occupancy_rate, 2),
            "total_categories": total_categories,
            "active_items": active_items,
        }

    async def get_analytics_only(
        self,
        workspace_id: str,
        persona_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get only the analytics portion of the dashboard"""
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date, end_of_day=True)

        orders, items, categories = await asyncio.gather(
            self.order_repo.get_orders_for_analytics(workspace_id, persona_id, start_dt, end_dt),
            self.item_repo.get_by_workspace(workspace_id),
            self.category_repo.get_by_workspace(workspace_id),
        )
        return self._calculate_analytics(orders, items, categories)

    # ---------------------------------------------------------------------------
    # Private sync calculation methods — operate on already-fetched Python lists
    # ---------------------------------------------------------------------------

    def _calculate_stats(
        self,
        orders: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate dashboard statistics. Cancelled orders are excluded from revenue."""
        # Exclude cancelled orders from revenue totals
        total_revenue = sum(
            order.get('total_amount', 0)
            for order in orders
            if order.get('status') != 'cancelled'
        )

        today = datetime.now(timezone.utc).date()
        todays_orders: List[Dict[str, Any]] = []
        todays_revenue = 0.0

        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            order_date = self._get_order_date(order)
            if order_date is None:
                continue
            if order_date.date() == today:
                todays_orders.append(order)
                todays_revenue += order.get('total_amount', 0)

        # Average order value: denominator is non-cancelled orders only.
        non_cancelled = [o for o in orders if o.get('status') != 'cancelled']
        avg_order_value = total_revenue / len(non_cancelled) if non_cancelled else 0

        occupied_tables = len([t for t in tables if t.get('status') == 'occupied'])
        table_occupancy_rate = (occupied_tables / len(tables) * 100) if tables else 0

        return {
            'total_revenue': round(total_revenue, 2),
            'todays_revenue': round(todays_revenue, 2),
            'todays_orders': len(todays_orders),
            'avg_order_value': round(avg_order_value, 2),
            'table_occupancy_rate': round(table_occupancy_rate, 2),
            'total_categories': len(categories),
            'active_items': len([i for i in items if i.get('is_available', False)])
        }

    def _calculate_analytics(
        self,
        orders: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate analytics data"""
        return {
            'revenue_trend': self._calculate_revenue_trend(orders),
            'order_status_breakdown': self._calculate_order_status_breakdown(orders),
            'popular_items': self._calculate_popular_items(orders, items),
            'category_performance': self._calculate_category_performance(orders, items, categories),
            'payment_methods': self._calculate_payment_methods(orders),
            'peak_hours': self._calculate_peak_hours(orders)
        }

    def _calculate_revenue_trend(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate revenue trend for last 30 days (excludes cancelled orders).

        Pre-groups orders by date into a dict first so the inner lookup is O(1)
        per day rather than O(N) — overall complexity drops from O(30×N) to O(N).
        """
        today = datetime.now(timezone.utc).date()

        # Build a date-keyed dict: date -> {revenue, orders}
        by_date: Dict[Any, Dict[str, Any]] = {}
        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            order_date = self._get_order_date(order)
            if order_date is None:
                continue
            d = order_date.date()
            if d not in by_date:
                by_date[d] = {'revenue': 0.0, 'orders': 0}
            by_date[d]['revenue'] += order.get('total_amount', 0)
            by_date[d]['orders'] += 1

        trend = []
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            day = by_date.get(date, {'revenue': 0.0, 'orders': 0})
            trend.append({
                'date': date.isoformat(),
                'period': date.strftime('%b %d'),
                'revenue': round(day['revenue'], 2),
                'orders': day['orders']
            })

        return trend

    def _calculate_order_status_breakdown(self, orders: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate order status breakdown"""
        breakdown = {'pending': 0, 'preparing': 0, 'ready': 0, 'completed': 0, 'cancelled': 0}
        for order in orders:
            order_status = order.get('status', 'pending')
            if order_status in breakdown:
                breakdown[order_status] += 1
        return breakdown

    def _calculate_popular_items(
        self,
        orders: List[Dict[str, Any]],
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate popular items based on order data (excludes cancelled orders).

        TODO: replace with a SQL GROUP BY query on order_items joined to items
              so the aggregation happens in the database rather than in Python.

        Uses a pre-built item_stats dict (O(total order-lines)) instead of an
        O(N×M) nested loop.
        """
        item_lookup = {item.get('id'): item for item in items}
        item_stats: Dict[str, Dict[str, Any]] = {}

        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            for order_item in order.get('items', []):
                item_id = order_item.get('item_id')
                if item_id and item_id in item_lookup:
                    if item_id not in item_stats:
                        item_stats[item_id] = {'orders': 0, 'revenue': 0.0, 'quantity': 0}
                    item_stats[item_id]['orders'] += 1
                    item_stats[item_id]['quantity'] += order_item.get('quantity', 1)
                    item_stats[item_id]['revenue'] += order_item.get('total_price', 0)

        popular = []
        for item_id, stats in item_stats.items():
            item = item_lookup[item_id]
            popular.append({
                'id': item_id,
                'name': item.get('name', 'Unknown'),
                'category': item.get('category_name', 'Uncategorized'),
                'orders': stats['orders'],
                'revenue': round(stats['revenue'], 2),
                'quantity': stats['quantity'],
                'rating': item.get('rating', 4.0)
            })

        popular.sort(key=lambda x: x['revenue'], reverse=True)
        return popular[:10]

    def _calculate_category_performance(
        self,
        orders: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate category performance (excludes cancelled orders).

        TODO: replace with a SQL GROUP BY query on order_items joined to items
              and categories so the aggregation happens in the database.

        Uses pre-built lookup dicts (O(total order-lines)) instead of an
        O(N×M) nested loop.
        """
        category_lookup = {cat.get('id'): cat for cat in categories}
        item_to_category = {
            item.get('id'): item.get('category_id')
            for item in items
            if item.get('category_id')
        }

        category_stats: Dict[str, Dict[str, Any]] = {}
        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            for order_item in order.get('items', []):
                item_id = order_item.get('item_id')
                category_id = item_to_category.get(item_id)
                if category_id:
                    if category_id not in category_stats:
                        category_stats[category_id] = {'orders': 0, 'revenue': 0.0}
                    category_stats[category_id]['orders'] += 1
                    category_stats[category_id]['revenue'] += order_item.get('total_price', 0)

        total_revenue = sum(s['revenue'] for s in category_stats.values())
        performance = []
        for category_id, stats in category_stats.items():
            if category_id in category_lookup:
                category = category_lookup[category_id]
                percentage = (stats['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
                performance.append({
                    'category': category.get('name', 'Unknown'),
                    'orders': stats['orders'],
                    'revenue': round(stats['revenue'], 2),
                    'percentage': round(percentage, 1)
                })

        performance.sort(key=lambda x: x['revenue'], reverse=True)
        return performance

    def _calculate_payment_methods(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate payment methods distribution (excludes cancelled orders)"""
        methods: Dict[str, Dict[str, Any]] = {}
        total_revenue = 0.0

        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            method = order.get('payment_method', 'cash')
            amount = order.get('total_amount', 0)
            if method not in methods:
                methods[method] = {'count': 0, 'revenue': 0.0}
            methods[method]['count'] += 1
            methods[method]['revenue'] += amount
            total_revenue += amount

        payment_list = []
        for method, stats in methods.items():
            percentage = (stats['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            payment_list.append({
                'method': method.capitalize(),
                'count': stats['count'],
                'revenue': round(stats['revenue'], 2),
                'percentage': round(percentage, 1)
            })

        payment_list.sort(key=lambda x: x['revenue'], reverse=True)
        return payment_list

    def _calculate_peak_hours(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate peak hours based on order times (excludes cancelled orders).

        NOTE: Hours are currently in UTC. For accurate peak-hour reporting these
        should be converted to the venue's local timezone before bucketing.
        """
        hours: Dict[int, Dict[str, Any]] = {i: {'orders': 0, 'revenue': 0.0} for i in range(24)}

        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            order_date = self._get_order_date(order)
            if order_date is None:
                continue
            hours[order_date.hour]['orders'] += 1
            hours[order_date.hour]['revenue'] += order.get('total_amount', 0)

        peak_list = [
            {
                'hour': f'{hour:02d}:00',
                'orders': stats['orders'],
                'revenue': round(stats['revenue'], 2)
            }
            for hour, stats in hours.items()
            if stats['orders'] > 0
        ]

        peak_list.sort(key=lambda x: x['orders'], reverse=True)
        return peak_list[:12]

    def _get_recent_activity(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get recent order activity (top 10 most recent)"""
        sorted_orders = sorted(
            orders,
            key=lambda o: self._get_order_date(o) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        recent = []
        for order in sorted_orders[:10]:
            order_date = self._get_order_date(order)
            recent.append({
                'id': order.get('id'),
                'order_number': order.get('order_number'),
                'status': order.get('status', 'pending'),
                'subtotal': order.get('subtotal', 0),
                'tax_amount': order.get('tax_amount', 0),
                'discount_amount': order.get('discount_amount', 0),
                'total_amount': order.get('total_amount', 0),
                'table_number': order.get('table_number'),
                'venue_name': order.get('venue_name', ''),
                'createdAt': order_date.isoformat() if order_date is not None else None
            })

        return recent

    def _get_table_statuses(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get table statuses"""
        return [
            {
                'id': table.get('id'),
                'table_number': table.get('table_number'),
                'status': table.get('status', 'available'),
                'capacity': table.get('capacity'),
                'area_id': table.get('area_id'),
                'current_order_id': table.get('current_order_id'),
                'occupancy_time': table.get('occupancy_time')
            }
            for table in tables
        ]

    def _get_order_date(self, order: Dict[str, Any]) -> Optional[datetime]:
        """Get order date as a timezone-aware datetime object, or None if not present"""
        order_date = order.get('created_at') or order.get('order_date')

        if isinstance(order_date, str):
            order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
        elif not isinstance(order_date, datetime):
            return None

        if order_date.tzinfo is None:
            order_date = order_date.replace(tzinfo=timezone.utc)

        return order_date

