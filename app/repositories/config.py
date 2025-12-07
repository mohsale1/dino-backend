"""
Config Repository
Handles database operations for system configuration
"""
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.config import Config
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConfigRepository(BaseRepository[Config]):
    """Repository for config management"""
    
    def __init__(self):
        super().__init__(collection_name="configs")
    
    async def get_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration by key (key is the document ID)
        
        Args:
            key: Configuration key (e.g., 'dino.registration.code')
        
        Returns:
            Config data if found, None otherwise
        """
        try:
            # Key is the document ID, so we can directly get it
            config = await self.get_by_id(key)
            
            if config:
                logger.info(f"Config found for key: {key}")
                return config
            
            logger.warning(f"Config not found for key: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting config by key {key}: {e}")
            raise
    
    async def get_value_by_key(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key
        
        Args:
            key: Configuration key
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        try:
            config = await self.get_by_key(key)
            if config:
                return config.get('value', default)
            return default
            
        except Exception as e:
            logger.error(f"Error getting config value for key {key}: {e}")
            return default
    
    async def set_value(self, key: str, value: Any) -> Dict[str, Any]:
        """
        Set or update configuration value
        
        Args:
            key: Configuration key (will be used as document ID)
            value: Configuration value
        
        Returns:
            Updated or created config data
        """
        try:
            # Check if config exists
            existing_config = await self.get_by_key(key)
            
            current_time = datetime.utcnow()
            
            if existing_config:
                # Update existing config
                update_data = {
                    'value': value,
                    'updated_at': current_time
                }
                
                await self.update(key, update_data)
                logger.info(f"Config updated for key: {key}")
                
                # Return updated config
                return await self.get_by_id(key)
            else:
                # Create new config with key as document ID
                config_data = {
                    'id': key,
                    'value': value,
                    'created_at': current_time,
                    'updated_at': current_time
                }
                
                created_config = await self.create(config_data, doc_id=key)
                logger.info(f"Config created for key: {key}")
                return created_config
                
        except Exception as e:
            logger.error(f"Error setting config value for key {key}: {e}")
            raise
    
    async def get_all_active(self) -> List[Dict[str, Any]]:
        """
        Get all configurations
        
        Returns:
            List of all configs
        """
        try:
            results = await self.get_all()
            logger.info(f"Retrieved {len(results)} configs")
            return results
            
        except Exception as e:
            logger.error(f"Error getting all configs: {e}")
            raise
    
    async def delete_by_key(self, key: str) -> bool:
        """
        Delete configuration by key
        
        Args:
            key: Configuration key (document ID)
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            config = await self.get_by_key(key)
            
            if not config:
                logger.warning(f"Config not found for deletion: {key}")
                return False
            
            await self.delete(key)
            logger.info(f"Config deleted: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting config by key {key}: {e}")
            raise
