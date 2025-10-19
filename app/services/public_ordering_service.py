"""

Public Ordering Service

Handles public order creation from QR code scans and customer-facing operations

"""

from typing import Dict, Any, Optional, List

from datetime import datetime, timedelta

from fastapi import HTTPException, status

import uuid



from app.core.logging_config import get_logger

from app.core.dependency_injection import get_repository_manager

from app.models.schemas import OrderStatus, PaymentStatus, OrderType



logger = get_logger(__name__)





class PublicOrderingService:

    """Service for handling public ordering operations"""

    

    def __init__(self):

        self.repo_manager = get_repository_manager()

    

    async def verify_qr_code_and_get_menu(self, qr_code: str) -> Dict[str, Any]:

        """

        Verify QR code and return venue menu with availability

        Enhanced with venue validation service

        """

        try:

            # Import validation service

            from app.services.venue_validation_service import venue_validation_service

            

            # Use the new validation service for QR code validation

            is_valid, validation_data = await venue_validation_service.validate_qr_code_access(qr_code)

            

            if not is_valid:

                # Handle different error types

                error_data = validation_data

                error_type = error_data.get('error_type', 'validation_failed')

                

                if error_type in ['venue_inactive', 'venue_not_operational']:

                    raise HTTPException(

                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

                        detail={

                            "error": "venue_not_accepting_orders",

                            "message": error_data.get('message', 'Venue is not accepting orders'),

                            "venue_name": error_data.get('venue_name'),

                            "show_error_page": True

                        }

                    )

                elif error_type == 'invalid_qr_code':

                    raise HTTPException(

                        status_code=status.HTTP_404_NOT_FOUND,

                        detail="Invalid QR code"

                    )

                else:

                    raise HTTPException(

                        status_code=status.HTTP_400_BAD_REQUEST,

                        detail=error_data.get('message', 'QR code validation failed')

                    )

            

            # Extract validated data

            venue_data = validation_data['venue']

            table_data = validation_data['table']

            venue_id = venue_data['id']

            

            # Get menu items for the venue

            menu_repo = self.repo_manager.get_repository('menu_item')

            menu_items = await menu_repo.query([

                ('venue_id', '==', venue_id),

                ('is_available', '==', True)

            ])

            

            # Organize menu items by category

            menu_by_category = {}

            for item in menu_items:

                category = item.get('category', 'Other')

                if category not in menu_by_category:

                    menu_by_category[category] = []

                menu_by_category[category].append({

                    'id': item['id'],

                    'name': item['name'],

                    'description': item.get('description', ''),

                    'base_price': item['base_price'],

                    'image_url': item.get('image_url'),

                    'is_vegetarian': item.get('is_vegetarian', False),

                    'is_vegan': item.get('is_vegan', False),

                    'allergens': item.get('allergens', []),

                    'preparation_time': item.get('preparation_time', 15)

                })

            

            return {

                'success': True,

                'venue': venue_data,

                'table': table_data,

                'menu': menu_by_category,

                'operating_status': await venue_validation_service.check_venue_operating_status(venue_id),

                'validation_timestamp': validation_data.get('validation_timestamp')

            }

            

        except HTTPException:

            raise

        except Exception as e:

            logger.error(f"Error verifying QR code {qr_code}: {e}")

            raise HTTPException(

                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

                detail="Failed to load menu"

            )

    

    async def check_venue_operating_status(self, venue_id: str) -> Dict[str, Any]:

        """

        Check if venue is currently open for orders

        """

        try:

            venue_repo = self.repo_manager.get_repository('venue')

            venue = await venue_repo.get_by_id(venue_id)

            

            if not venue:

                return {

                    'current_status': 'closed',

                    'is_open': False,

                    'message': 'Venue not found'

                }

            

            # For now, assume venue is open if active

            # In a real implementation, you'd check operating hours

            is_open = venue.get('is_active', False)

            

            return {

                'current_status': 'open' if is_open else 'closed',

                'is_open': is_open,

                'message': 'Venue is open for orders' if is_open else 'Venue is currently closed',

                'next_opening': None,  # Would be calculated based on operating hours

                'next_closing': None   # Would be calculated based on operating hours

            }

            

        except Exception as e:

            logger.error(f"Error checking venue status {venue_id}: {e}")

            return {

                'current_status': 'unknown',

                'is_open': False,

                'message': 'Unable to check venue status'

            }

    

    async def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:

        """

        Validate order before creation

        """

        try:

            venue_id = order_data.get('venue_id')

            items = order_data.get('items', [])

            

            if not venue_id:

                return {

                    'is_valid': False,

                    'errors': ['Venue ID is required']

                }

            

            if not items:

                return {

                    'is_valid': False,

                    'errors': ['Order must contain at least one item']

                }

            

            # Check venue status using validation service

            from app.services.venue_validation_service import venue_validation_service

            venue_status = await venue_validation_service.check_venue_operating_status(venue_id)

            if not venue_status['is_open']:

                return {

                    'is_valid': False,

                    'errors': [venue_status.get('message', 'Venue is currently closed for orders')]

                }

            

            # Validate menu items

            menu_repo = self.repo_manager.get_repository('menu_item')

            total_amount = 0.0

            estimated_prep_time = 0

            validated_items = []

            

            for item in items:

                menu_item_id = item.get('menu_item_id')

                quantity = item.get('quantity', 1)

                

                if not menu_item_id:

                    return {

                        'is_valid': False,

                        'errors': ['Menu item ID is required for all items']

                    }

                

                menu_item = await menu_repo.get_by_id(menu_item_id)

                if not menu_item:

                    return {

                        'is_valid': False,

                        'errors': [f'Menu item {menu_item_id} not found']

                    }

                

                if not menu_item.get('is_available', False):

                    return {

                        'is_valid': False,

                        'errors': [f'Menu item "{menu_item["name"]}" is not available']

                    }

                

                item_total = menu_item['base_price'] * quantity

                total_amount += item_total

                estimated_prep_time = max(estimated_prep_time, menu_item.get('preparation_time', 15))

                

                validated_items.append({

                    'menu_item_id': menu_item_id,

                    'name': menu_item['name'],

                    'quantity': quantity,

                    'unit_price': menu_item['base_price'],

                    'total_price': item_total

                })

            

            # Calculate tax and final total

            tax_rate = 0.18  # 18% GST

            tax_amount = total_amount * tax_rate

            final_total = total_amount + tax_amount

            

            return {

                'is_valid': True,

                'validated_items': validated_items,

                'subtotal': total_amount,

                'tax_amount': tax_amount,

                'total_amount': final_total,

                'estimated_preparation_time': estimated_prep_time,

                'venue_status': venue_status

            }

            

        except Exception as e:

            logger.error(f"Error validating order: {e}")

            return {

                'is_valid': False,

                'errors': ['Order validation failed']

            }

    

    async def create_public_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:

        """

        Create order from public interface

        """

        try:

            # Validate order first

            validation = await self.validate_order(order_data)

            if not validation['is_valid']:

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=f"Order validation failed: {', '.join(validation['errors'])}"

                )

            

            # Generate order ID and number

            order_id = str(uuid.uuid4())

            order_number = self._generate_order_number()

            

            # Create or update customer record

            customer_info = order_data.get('customer', {})

            customer_id = await self._handle_customer_record(customer_info)

            

            # Prepare order data

            order_record = {

                'id': order_id,

                'order_number': order_number,

                'venue_id': order_data['venue_id'],

                'table_id': order_data.get('table_id'),

                'customer_id': customer_id,

                'customer_name': customer_info.get('name', 'Guest'),

                'customer_phone': customer_info.get('phone'),

                'customer_email': customer_info.get('email'),

                'order_type': OrderType.DINE_IN.value,

                'status': OrderStatus.PENDING.value,

                'payment_status': PaymentStatus.PENDING.value,

                'items': validation['validated_items'],

                'subtotal': validation['subtotal'],

                'tax_amount': validation['tax_amount'],

                'total_amount': validation['total_amount'],

                'estimated_preparation_time': validation['estimated_preparation_time'],

                'special_instructions': order_data.get('special_instructions'),

                'created_at': datetime.utcnow(),

                'updated_at': datetime.utcnow()

            }

            

            # Save order to database

            order_repo = self.repo_manager.get_repository('order')

            try:

                created_order = await order_repo.create(order_record, doc_id=order_id)

                logger.info(f"Order successfully saved to database: {order_id}")

            except Exception as db_error:

                logger.error(f"Failed to save order to database: {db_error}")

                raise HTTPException(

                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

                    detail="Failed to save order to database"

                )

            

            # Update table status if applicable

            if order_data.get('table_id'):

                await self._update_table_status(order_data['table_id'], 'occupied')

            

            # Send WebSocket notification for new order

            await self._send_order_creation_notification(order_record)

            

            logger.info(f"Public order created: {order_id} for venue: {order_data['venue_id']}")

            

            return {

                'success': True,

                'order_id': order_id,

                'order_number': order_number,

                'total_amount': validation['total_amount'],

                'estimated_ready_time': datetime.utcnow() + timedelta(minutes=validation['estimated_preparation_time']),

                'status': OrderStatus.PENDING.value,

                'message': 'Order placed successfully! You will receive updates on your order status.'

            }

            

        except HTTPException:

            raise

        except Exception as e:

            logger.error(f"Error creating public order: {e}")

            raise HTTPException(

                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

                detail="Failed to create order"

            )

    

    async def _handle_customer_record(self, customer_info: Dict[str, Any]) -> str:

        """

        Create or update customer record

        """

        try:

            customer_repo = self.repo_manager.get_repository('customer')

            

            # Try to find existing customer by phone or email

            customer = None

            if customer_info.get('phone'):

                customers = await customer_repo.query([('phone', '==', customer_info['phone'])])

                if customers:

                    customer = customers[0]

            

            if not customer and customer_info.get('email'):

                customers = await customer_repo.query([('email', '==', customer_info['email'])])

                if customers:

                    customer = customers[0]

            

            if customer:

                # Update existing customer

                update_data = {

                    'name': customer_info.get('name', customer.get('name')),

                    'updated_at': datetime.utcnow()

                }

                await customer_repo.update(customer['id'], update_data)

                return customer['id']

            else:

                # Create new customer

                customer_id = str(uuid.uuid4())

                customer_data = {

                    'id': customer_id,

                    'name': customer_info.get('name', 'Guest'),

                    'phone': customer_info.get('phone'),

                    'email': customer_info.get('email'),

                    'created_at': datetime.utcnow(),

                    'updated_at': datetime.utcnow()

                }

                await customer_repo.create(customer_data, doc_id=customer_id)

                return customer_id

                

        except Exception as e:

            logger.error(f"Error handling customer record: {e}")

            # Return a guest customer ID if customer handling fails

            return "guest-customer"

    

    async def _update_table_status(self, table_id: str, status: str):

        """

        Update table status

        """

        try:

            table_repo = self.repo_manager.get_repository('table')

            await table_repo.update(table_id, {

                'status': status,

                'updated_at': datetime.utcnow()

            })

        except Exception as e:

            logger.error(f"Error updating table status: {e}")

            # Don't fail the order if table update fails

    

    def _generate_order_number(self) -> str:

        """

        Generate unique order number

        """

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")

        random_suffix = str(uuid.uuid4())[:6].upper()

        return f"PUB-{timestamp}-{random_suffix}"

    

    async def _send_order_creation_notification(self, order_data: Dict[str, Any]):

        """

        Send real-time notification when order is created via public interface

        """

        try:

            from app.core.websocket_manager import connection_manager

            

            # Get table number if available

            table_number = None

            table_id = order_data.get('table_id')

            if table_id:

                table_repo = self.repo_manager.get_repository('table')

                table = await table_repo.get_by_id(table_id)

                if table:

                    table_number = table.get('table_number')

            

            # Prepare order data with table number for notification

            notification_data = {

                **order_data,

                'table_number': table_number

            }

            

            # Send WebSocket notification to venue users

            await connection_manager.send_order_notification(notification_data, "order_created")

            

            logger.info(f"WebSocket notification sent for public order {order_data.get('order_number')} in venue {order_data.get('venue_id')}")

            

        except Exception as e:

            logger.error(f"Failed to send order creation notification for public order: {e}")

            # Don't fail the order creation if notification fails





# Singleton instance

public_ordering_service = PublicOrderingService()