"""
Application Initialization Module

Handles automatic initialization of critical system resources on startup:
  - SuperAdmin role
  - SuperAdmin user
  - Homepage info (singleton row)

The top-level entry point is initialize_application(db), which is called
from Main.py lifespan with an injected AsyncSession.
"""

import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.Settings import settings
from src.core.Security import get_password_hash
from src.models.HomePageInfo import HomePageInfo
from src.models.Role import Role
from src.models.SystemUser import SystemUser
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SuperAdmin role
# ---------------------------------------------------------------------------

async def _initialize_superadmin_role(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Ensure the SuperAdmin role (name='SuperAdmin', role_type=0) exists.
    Creates it if absent and returns the role dict.
    """
    logger.info("Initializing SuperAdmin role...")

    role_repo = RoleRepository(db)

    existing = await role_repo.get_by_name_and_type("SuperAdmin", 0)
    if existing:
        logger.info(f"SuperAdmin role already exists (ID: {existing.get('id')})")
        return existing

    logger.info("Creating SuperAdmin role...")
    created = await role_repo.create({
        "name": "SuperAdmin",
        "role_type": 0,
        "description": (
            "Unrestricted access to the entire system — all APIs, all modules, "
            "all administrative operations including user password management, "
            "billing, registration codes, and role/permission management."
        ),
    })
    logger.info(f"SuperAdmin role created successfully (ID: {created.get('id')})")
    return created


# ---------------------------------------------------------------------------
# SuperAdmin user
# ---------------------------------------------------------------------------

async def _generate_system_user_id(db: AsyncSession) -> str:
    """
    Generate a unique 4-digit numeric system-user ID (range 1000–9999).

    Strategy: pick a random ID in [1000, 9999] and attempt an INSERT.
    Retry up to 10 times on conflict. Raises RuntimeError if all attempts fail
    (extremely unlikely given ~9000 available slots).
    """
    user_repo = UserRepository(db)

    for attempt in range(10):
        candidate = str(random.randint(1000, 9999))
        existing = await user_repo.get_by_id(candidate)
        if existing is None:
            return candidate
        logger.debug(
            f"System user ID {candidate!r} already taken, retrying "
            f"(attempt {attempt + 1}/10)..."
        )

    raise RuntimeError(
        "Failed to generate a unique system user ID after 10 attempts. "
        "The ID space (1000–9999) may be exhausted."
    )


async def _initialize_superadmin_user(
    db: AsyncSession, superadmin_role: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Ensure the default SuperAdmin user exists.
    Creates it if absent; updates the role assignment if it has drifted.
    """
    logger.info("Initializing SuperAdmin user...")

    superadmin_email = settings.SUPERADMIN_EMAIL
    superadmin_role_id = superadmin_role.get("id")

    if not superadmin_role_id:
        logger.error("SuperAdmin role ID not found — skipping user creation")
        return None

    user_repo = UserRepository(db)

    existing = await user_repo.get_by_email(superadmin_email)
    if existing:
        logger.info(f"SuperAdmin user already exists (Email: {superadmin_email})")

        if existing.get("role_id") != superadmin_role_id:
            logger.info("Updating existing user's role to SuperAdmin")
            await user_repo.update(existing.get("id"), {"role_id": superadmin_role_id})
            logger.info("User role updated to SuperAdmin")

        return existing

    # Hash password
    try:
        password_hash = get_password_hash(settings.SUPERADMIN_PASSWORD)
    except Exception as exc:
        logger.error(f"Failed to hash SuperAdmin password: {exc}")
        raise

    # Generate a unique 4-digit ID
    user_id = await _generate_system_user_id(db)

    logger.info("Creating SuperAdmin user...")
    created = await user_repo.create({
        "id": user_id,
        "email": superadmin_email,
        "password_hash": password_hash,
        "role_id": superadmin_role_id,
        "first_name": "Super",
        "last_name": "Admin",
        "is_active": True,
    })

    logger.info("=" * 70)
    logger.info("SuperAdmin user created successfully!")
    logger.info("=" * 70)
    logger.info(f"  User ID : {created.get('id')}")
    logger.info(f"  Email   : {superadmin_email}")
    logger.info(f"  Role    : SuperAdmin")
    logger.info("=" * 70)
    logger.info("You can now login with:")
    logger.info(f"  Email   : {superadmin_email}")
    logger.info("  Password: [set via SUPERADMIN_PASSWORD environment variable]")
    logger.info("=" * 70)

    return created


# ---------------------------------------------------------------------------
# Homepage info (singleton row, auto-generated UUID)
# ---------------------------------------------------------------------------

async def _initialize_homepage_info(db: AsyncSession) -> None:
    """
    Ensure the singleton home_page_info row exists.
    Inserts default content if the table is empty.
    """
    logger.info("Initializing homepage information...")

    count_stmt = select(func.count()).select_from(HomePageInfo)
    existing_count: int = (await db.execute(count_stmt)).scalar_one()

    if existing_count > 0:
        logger.info("Homepage information already exists")
        return

    logger.info("Creating default homepage information...")

    now_iso = datetime.now(timezone.utc).isoformat()

    default_stats = [
        {
            "title": "Active Businesses",
            "value": "50",
            "number": 50,
            "suffix": "+",
            "label": "Active Businesses",
            "icon": "business",
        },
        {
            "title": "Orders Processed",
            "value": "10000",
            "number": 10000,
            "suffix": "+",
            "label": "Orders Processed",
            "icon": "shopping_cart",
        },
        {
            "title": "Customer Satisfaction",
            "value": "98",
            "number": 98,
            "suffix": "%",
            "label": "Customer Satisfaction",
            "icon": "sentiment_satisfied",
        },
        {
            "title": "Uptime",
            "value": "99.9",
            "number": 99.9,
            "suffix": "%",
            "label": "Uptime",
            "icon": "cloud_done",
        },
    ]

    default_testimonials = [
        {
            "name": "Rajesh Kumar",
            "role": "Owner",
            "restaurant": "Spice Garden Restaurant",
            "location": "Mumbai, Maharashtra",
            "rating": 5,
            "comment": (
                "Dino transformed our restaurant operations completely. Orders are faster, "
                "more accurate, and our customers love the digital menu experience. "
                "Highly recommended!"
            ),
            "avatar": "RK",
            "created_at": now_iso,
        },
        {
            "name": "Priya Sharma",
            "role": "Manager",
            "restaurant": "Cafe Coffee Day",
            "location": "Bangalore, Karnataka",
            "rating": 5,
            "comment": (
                "The analytics dashboard gives us incredible insights into our business. "
                "We've increased our revenue by 30% since implementing Dino. Best decision ever!"
            ),
            "avatar": "PS",
            "created_at": now_iso,
        },
        {
            "name": "Amit Patel",
            "role": "Owner",
            "restaurant": "Gujarat Bhavan",
            "location": "Ahmedabad, Gujarat",
            "rating": 5,
            "comment": (
                "Managing multiple outlets was a challenge until we found Dino. "
                "Now everything is centralized and efficient. Our staff loves how easy it is to use."
            ),
            "avatar": "AP",
            "created_at": now_iso,
        },
        {
            "name": "Sneha Reddy",
            "role": "Co-founder",
            "restaurant": "South Indian Delights",
            "location": "Hyderabad, Telangana",
            "rating": 5,
            "comment": (
                "The QR code ordering system is a game-changer! Our customers can browse the menu "
                "and place orders seamlessly. Customer satisfaction has gone up significantly."
            ),
            "avatar": "SR",
            "created_at": now_iso,
        },
        {
            "name": "Vikram Singh",
            "role": "Owner",
            "restaurant": "Punjabi Tadka",
            "location": "Chandigarh, Punjab",
            "rating": 5,
            "comment": (
                "Dino helped us go digital without any hassle. The support team is amazing and "
                "the platform is very user-friendly. Our business has grown 40% in just 6 months!"
            ),
            "avatar": "VS",
            "created_at": now_iso,
        },
        {
            "name": "Meera Iyer",
            "role": "Manager",
            "restaurant": "Saravana Bhavan",
            "location": "Chennai, Tamil Nadu",
            "rating": 5,
            "comment": (
                "Real-time order tracking and inventory management features are outstanding. "
                "We can now serve more customers efficiently and reduce wastage significantly."
            ),
            "avatar": "MI",
            "created_at": now_iso,
        },
    ]

    default_contact = {
        "email": "contact@dino.restaurant",
        "phone": "+1 (555) 123-4567",
        "address": "123 Restaurant Street",
        "city": "San Francisco",
        "state": "CA",
        "country": "United States",
        "postal_code": "94102",
    }

    homepage = HomePageInfo(
        stats=default_stats,
        testimonials=default_testimonials,
        contact=default_contact,
    )
    db.add(homepage)

    logger.info("Homepage information created successfully")


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

async def initialize(db: AsyncSession) -> None:
    """
    Run all startup initialization steps using the provided AsyncSession.

    Role + user initialization runs inside a single transaction so that a
    partial failure (e.g. user creation fails after role creation) is fully
    rolled back. Homepage initialization runs in its own transaction.

    Errors are logged and abort the application startup.
    """
    logger.info("Starting application initialization...")

    try:
        # --- Role + user: single atomic transaction --------------------------
        async with db.begin():
            superadmin_role = await _initialize_superadmin_role(db)

            if settings.CREATE_DEFAULT_SUPERADMIN and superadmin_role:
                await _initialize_superadmin_user(db, superadmin_role)

        # --- Homepage info: separate transaction ------------------------------
        async with db.begin():
            await _initialize_homepage_info(db)

        logger.info("Application initialization completed successfully")

    except Exception as exc:
        logger.error(f"Application initialization failed: {exc}", exc_info=True)
        raise


async def initialize_application(db: AsyncSession) -> None:
    """
    Public entry point called from Main.py lifespan.

    Args:
        db: An AsyncSession provided by the lifespan context.
    """
    await initialize(db)
