"""
Firestore Database Configuration
"""

import firebase_admin
from google.cloud import firestore
from google.cloud.firestore import Client
from src.config.Settings import settings
from typing import Optional

_db: Optional[Client] = None


def initialize_firestore() -> Client:
    """Initialize Firestore connection using Application Default Credentials"""
    global _db
    
    if _db is not None:
        return _db
    
    try:
        print("🔥 Connecting to Firestore...")
        print(f"📊 Project ID: {settings.FIREBASE_PROJECT_ID}")
        print(f"📊 Database Name: {settings.FIREBASE_DATABASE_ID}")
        
        # Initialize Firebase Admin SDK
        try:
            firebase_admin.initialize_app(options={
                'projectId': settings.FIREBASE_PROJECT_ID,
            })
        except ValueError:
            # Already initialized
            pass
        
        # Connect to Firestore with database name
        database_name = settings.FIREBASE_DATABASE_ID if settings.FIREBASE_DATABASE_ID else "(default)"
        
        _db = firestore.Client(
            project=settings.FIREBASE_PROJECT_ID,
            database=database_name
        )
        
        print(f"✅ Firestore connected successfully!")
        return _db
        
    except Exception as e:
        print(f"❌ Error initializing Firestore: {str(e)}")
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
        except:
            pass
        _db = None
        print("Firestore connection closed")