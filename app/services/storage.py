"""
Storage Service Interface
Provides a clean interface for file storage operations with multiple backend support
"""
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from fastapi import UploadFile
import os
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def upload_file(self, file: UploadFile, path: str) -> str:
        """Upload a file and return the URL"""
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def get_file_url(self, path: str) -> str:
        """Get the public URL for a file"""
        pass

class LocalStorageBackend(StorageBackend):
    """Local file system storage backend for development"""
    
    def __init__(self, upload_dir: str = "uploads", base_url: str = "http://localhost:8000/static"):
        self.upload_dir = upload_dir
        self.base_url = base_url.rstrip('/')
        
        # Create upload directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
    
    async def upload_file(self, file: UploadFile, path: str) -> str:
        """Upload file to local storage"""
        try:
            # Create directory structure
            full_path = os.path.join(self.upload_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save file
            with open(full_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Return public URL
            public_url = f"{self.base_url}/{path}"
            logger.info(f"Local upload: {file.filename} -> {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            raise
    
    async def delete_file(self, path: str) -> bool:
        """Delete file from local storage"""
        try:
            full_path = os.path.join(self.upload_dir, path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Local delete: {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Local delete failed: {e}")
            return False
    
    async def get_file_url(self, path: str) -> str:
        """Get local file URL"""
        return f"{self.base_url}/{path}"


class CloudStorageBackend(StorageBackend):
    """Google Cloud Storage backend for file uploads"""
    
    def __init__(self, bucket_name: str, base_url: Optional[str] = None):
        self.bucket_name = bucket_name
        self.base_url = base_url
        self._storage_client = None
        self._bucket = None
        logger.info(f"CloudStorageBackend initialized with bucket: {bucket_name}")
    
    def _get_storage_client(self):
        """Get or create Google Cloud Storage client"""
        if self._storage_client is None:
            try:
                from google.cloud import storage
                self._storage_client = storage.Client()
                logger.info("Google Cloud Storage client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._storage_client
    
    def _get_bucket(self):
        """Get or create bucket reference"""
        if self._bucket is None:
            try:
                client = self._get_storage_client()
                self._bucket = client.bucket(self.bucket_name)
                logger.info(f"GCS bucket reference created: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to get bucket reference: {e}")
                raise
        return self._bucket
    
    async def upload_file(self, file: UploadFile, path: str) -> str:
        """Upload file to Google Cloud Storage"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            
            # Read file content
            content = await file.read()
            
            # Upload to GCS
            blob.upload_from_string(
                content,
                content_type=file.content_type or 'application/octet-stream'
            )
            
            # Make the blob publicly accessible
            blob.make_public()
            
            # Get public URL
            public_url = blob.public_url
            
            logger.info(f"Successfully uploaded to GCS: {file.filename} -> {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"GCS upload failed for {file.filename}: {e}")
            raise
    
    async def delete_file(self, path: str) -> bool:
        """Delete file from Google Cloud Storage"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Successfully deleted from GCS: {path}")
                return True
            else:
                logger.warning(f"File not found in GCS: {path}")
                return False
                
        except Exception as e:
            logger.error(f"GCS delete failed for {path}: {e}")
            return False
    
    async def get_file_url(self, path: str) -> str:
        """Get public URL for a file in GCS"""
        return f"https://storage.googleapis.com/{self.bucket_name}/{path}"


class StorageService:
    """Main storage service that uses configurable backends"""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
    
    async def upload_image(self, file: UploadFile, category: str, entity_id: str, workspace_id: str = None, venue_id: str = None) -> str:
        """Upload an image file with optional workspace/venue folder structure"""
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise ValueError("File must be an image")
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename or "image.jpg")[1]
        filename = f"{timestamp}_{entity_id}{file_extension}"
        
        # Create path with workspace/venue structure if provided
        if workspace_id and venue_id:
            path = f"{workspace_id}/{venue_id}/{category}/{entity_id}/{filename}"
        elif workspace_id:
            path = f"{workspace_id}/{category}/{entity_id}/{filename}"
        else:
            path = f"{category}/{entity_id}/{filename}"
        
        # Upload file
        return await self.backend.upload_file(file, path)
    
    async def upload_menu_item_image(self, file: UploadFile, menu_item_id: str, venue_id: str) -> str:
        """Upload a menu item image to GCS with venue folder structure: bucket/VENUE_ID/filename"""
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise ValueError("File must be an image")
        
        # Generate unique filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename or "image.jpg")[1]
        filename = f"{menu_item_id}_{timestamp}{file_extension}"
        
        # Create path: VENUE_ID/filename
        path = f"{venue_id}/{filename}"
        
        # Upload file
        url = await self.backend.upload_file(file, path)
        logger.info(f"Menu item image uploaded: {filename} -> {url}")
        return url
    
    async def upload_document(self, file: UploadFile, category: str, entity_id: str) -> str:
        """Upload a document file"""
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename or "document.pdf")[1]
        filename = f"{timestamp}_{entity_id}{file_extension}"
        
        # Create path
        path = f"{category}/{entity_id}/{filename}"
        
        # Upload file
        return await self.backend.upload_file(file, path)
    
    async def delete_file(self, url: str) -> bool:
        """Delete a file by URL"""
        # Extract path from URL
        path = self._extract_path_from_url(url)
        if path:
            return await self.backend.delete_file(path)
        return False
    
    def _extract_path_from_url(self, url: str) -> Optional[str]:
        """Extract file path from URL"""
        # This is a simple implementation - might need adjustment based on backend
        if "/venues/" in url:
            return url.split("/venues/", 1)[1] if "/venues/" in url else None
        elif "/menu/" in url:
            return url.split("/menu/", 1)[1] if "/menu/" in url else None
        elif "/categories/" in url:
            return url.split("/categories/", 1)[1] if "/categories/" in url else None
        return None


# Global storage service instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance"""
    global _storage_service
    
    if _storage_service is None:
        # Initialize with appropriate backend based on environment
        from app.core.config import get_settings
        settings = get_settings()
        
        # Check if DINO_MENU_BUCKET is configured (for menu item uploads)
        bucket_name = getattr(settings, 'DINO_MENU_BUCKET', '')
        
        if bucket_name:
            # Use Google Cloud Storage for menu items
            backend = CloudStorageBackend(bucket_name)
            logger.info(f"Storage service initialized with GCS backend using bucket: {bucket_name}")
        else:
            # Fallback to local storage for development
            backend = LocalStorageBackend()
            logger.info("Storage service initialized with local backend (DINO_MENU_BUCKET not configured)")
        
        _storage_service = StorageService(backend)
    
    return _storage_service


def set_storage_service(service: StorageService):
    """Set the global storage service instance (for testing)"""
    global _storage_service
    _storage_service = service