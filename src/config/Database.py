"""
Firestore Database Configuration
"""

import logging

import firebase_admin
from google.cloud import firestore
from google.cloud.firestore import Client
from typing import Optional

from src.config.Settings import settings

logger = logging.getLogger(__name__)

_db: Optional[Client] = None


def initialize_firestore() -> Client:
    """Initialize Firestore connection using Application Default Credentials"""
    global _db

    if _db is not None:
        return _db

    try:
        logger.info("Connecting to Firestore...")
        logger.info(f"Project ID: {settings.FIREBASE_PROJECT_ID}")
        logger.info(f"Database Name: {settings.FIREBASE_DATABASE_ID}")

        # Initialize Firebase Admin SDK
        try:
            firebase_admin.initialize_app(options={
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
        except ValueError:
            # Already initialized
            pass

        # Connect to Firestore with database name
        database_name = settings.FIREBASE_DATABASE_ID if settings.FIREBASE_DATABASE_ID else "(default)"

        _db = firestore.Client(
            project=settings.FIREBASE_PROJECT_ID,
            database=database_name,
        )

        logger.info("Firestore connected successfully.")
        return _db

    except Exception as e:
        logger.error(f"Error initializing Firestore: {e}")
        raise


def get_firestore_client() -> Client:
    """Get Firestore client instance"""
    global _db

    if _db is None:
        _db = initialize_firestore()

    return _db


def close_firestore():
    """Close Firestore connection"""
    global _db

    if _db is not None:
        try:
            firebase_admin.delete_app(firebase_admin.get_app())
        except Exception as e:
            logger.warning(f"Error closing Firebase app: {e}")
        _db = None
        logger.info("Firestore connection closed.")
