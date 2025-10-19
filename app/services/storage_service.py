"""
Storage Service Interface
Provides a clean interface for file storage operations with multiple backend support
"""
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from fastapi import UploadFile
import os
from datetime import datetime

from app.core.logging_config import get_logger

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


class MockStorageBackend(StorageBackend):
    """Mock storage backend for development and testing"""
    
    def __init__(self, base_url: str = "https://storage.example.com"):
        self.base_url = base_url.rstrip('/')
    
    async def upload_file(self, file: UploadFile, path: str) -> str:
        """Mock file upload - returns a mock URL"""
        # In a real implementation, this would upload to cloud storage
        mock_url = f"{self.base_url}/{path}"
        logger.info(f"Mock upload: {file.filename} -> {mock_url}")
        return mock_url
    
    async def delete_file(self, path: str) -> bool:
        """Mock file deletion"""
        logger.info(f"Mock delete: {path}")
        return True
    
    async def get_file_url(self, path: str) -> str:
        """Get mock file URL"""
        return f"{self.base_url}/{path}"


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
    """Cloud storage backend (Google Cloud Storage, AWS S3, etc.)"""
    
    def __init__(self, bucket_name: str, base_url: Optional[str] = None):
        self.bucket_name = bucket_name
        self.base_url = base_url
        # TODO: Initialize cloud storage client (GCS, S3, etc.)
        logger.warning("CloudStorageBackend not fully implemented - using mock behavior")
    
    async def upload_file(self, file: UploadFile, path: str) -> str:
        """Upload file to cloud storage"""
        # TODO: Implement actual cloud storage upload
        mock_url = f"https://{self.bucket_name}.storage.googleapis.com/{path}"
        logger.info(f"Cloud upload (mock): {file.filename} -> {mock_url}")
        return mock_url
    
    async def delete_file(self, path: str) -> bool:
        """Delete file from cloud storage"""
        # TODO: Implement actual cloud storage deletion
        logger.info(f"Cloud delete (mock): {path}")
        return True
    
    async def get_file_url(self, path: str) -> str:
        """Get cloud file URL"""
        return f"https://{self.bucket_name}.storage.googleapis.com/{path}"


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
    
    async def upload_menu_item_image(self, file: UploadFile, menu_item_id: str, workspace_id: str, venue_id: str) -> str:
        """Upload a menu item image with workspace/venue folder structure"""
        return await self.upload_image(file, "menu_items", menu_item_id, workspace_id, venue_id)
    
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
        
        storage_backend = getattr(settings, 'STORAGE_BACKEND', 'mock')
        
        if storage_backend == 'local':
            backend = LocalStorageBackend()
        elif storage_backend == 'cloud':
            bucket_name = getattr(settings, 'STORAGE_BUCKET', 'dino-uploads')
            backend = CloudStorageBackend(bucket_name)
        else:
            # Default to mock for development
            backend = MockStorageBackend()
        
        _storage_service = StorageService(backend)
        logger.info(f"Storage service initialized with {storage_backend} backend")
    
    return _storage_service


def set_storage_service(service: StorageService):
    """Set the global storage service instance (for testing)"""
    global _storage_service
    _storage_service = service