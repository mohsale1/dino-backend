"""
QR Code Generator Utility
Handles QR code generation for tables and other entities.
"""

import hashlib
from datetime import datetime
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# QR CODE GENERATION
# =============================================================================

def generate_qr_code(venue_id: str, table_number: int, salt: Optional[str] = None) -> str:
    """
    Generate a unique QR code string for a table.

    Args:
        venue_id (str): Venue identifier
        table_number (int): Table number
        salt (Optional[str]): Optional salt for additional uniqueness

    Returns:
        str: Unique QR code string (16-character hex)
    """
    if salt is None:
        salt = datetime.utcnow().isoformat()

    # Create unique string
    unique_string = f"{venue_id}_{table_number}_{salt}"

    # Generate hash (first 16 hex characters of SHA256)
    qr_code = hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    logger.debug(f"Generated QR code for venue={venue_id}, table={table_number}: {qr_code}")
    return qr_code


def generate_qr_code_url(qr_code: str, base_url: str = "https://app.example.com") -> str:
    """
    Generate a full QR code URL.

    Args:
        qr_code (str): QR code string
        base_url (str): Base URL for the application (default: https://app.example.com)

    Returns:
        str: Full QR code URL
    """
    return f"{base_url}/scan/{qr_code}"


def validate_qr_code_format(qr_code: str) -> bool:
    """
    Validate QR code format.

    QR codes must be 16-character hexadecimal strings.

    Args:
        qr_code (str): QR code to validate

    Returns:
        bool: True if valid format, False otherwise
    """
    if not qr_code or len(qr_code) != 16:
        return False

    try:
        int(qr_code, 16)  # Ensure it's valid hex
        return True
    except ValueError:
        return False