from typing import Any, List, Tuple, Optional, Dict
import logging

from .system import MemorySystem
from .providers import StorageProvider, InMemoryStorageProvider

# Set up logger
logger = logging.getLogger("orcs.memory.v2.storage_memory")

class StorageBackedMemorySystem(MemorySystem):
    """Memory system backed by a storage provider
    
    This implementation delegates storage operations to a provider,
    allowing for different storage backends.
    """
    
    def __init__(self, storage_provider: Optional[StorageProvider] = None):
        """Initialize a storage-backed memory system
        
        Args:
            storage_provider: Provider for persistent storage (default: in-memory)
        """
        logger.info("Initializing StorageBackedMemorySystem")
        self.storage_provider = storage_provider or InMemoryStorageProvider()
        logger.info("Using storage provider: %s", self.storage_provider.__class__.__name__)
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information
        
        Args:
            key: The key to store data under
            value: The data to store
            scope: The scope to store the data in (default: "global")
        """
        self.storage_provider.save(key, value, scope)
        logger.debug("Stored value at key '%s' in scope '%s'", key, scope)
        
    def retrieve(self, key: str, scope: str = "global") -> Any:
        """Retrieve data from specified scope
        
        Args:
            key: The key to retrieve
            scope: The scope to retrieve from (default: "global")
            
        Returns:
            The stored value, or None if not found
        """
        value = self.storage_provider.load(key, scope)
        if value is None:
            logger.debug("Key '%s' not found in scope '%s'", key, scope)
        else:
            logger.debug("Retrieved value from key '%s' in scope '%s'", key, scope)
        return value
        
    def delete(self, key: str, scope: str = "global") -> bool:
        """Delete data from specified scope
        
        Args:
            key: The key to delete
            scope: The scope to delete from (default: "global")
            
        Returns:
            True if something was deleted, False otherwise
        """
        result = self.storage_provider.delete(key, scope)
        if result:
            logger.debug("Deleted key '%s' from scope '%s'", key, scope)
        else:
            logger.debug("Cannot delete: key '%s' not found in scope '%s'", key, scope)
        return result
        
    def list_keys(self, pattern: str = "*", scope: str = "global") -> List[str]:
        """List keys matching a pattern in specified scope
        
        Args:
            pattern: Pattern to match keys against (default: "*" for all keys)
            scope: The scope to list keys from (default: "global")
            
        Returns:
            List of matching key names
        """
        keys = self.storage_provider.list_keys(pattern, scope)
        logger.debug("Found %d keys matching pattern '%s' in scope '%s'", 
                    len(keys), pattern, scope)
        return keys
        
    def search(self, query: str, scope: str = "global", limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Basic search implementation that checks for keyword presence
        
        This implementation is not optimized for semantic search.
        Consider using a specialized implementation for semantic search.
        
        Args:
            query: The search query
            scope: The scope to search in (default: "global")
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of (key, content, score) tuples
        """
        # Get all keys in the scope
        keys = self.list_keys("*", scope)
        if not keys:
            logger.debug("No data found in scope '%s' for search", scope)
            return []
            
        # Load values for the keys
        results = []
        query_lower = query.lower()
        
        for key in keys:
            value = self.retrieve(key, scope)
            if value is None:
                continue
                
            # Convert value to string if possible for simple text matching
            try:
                value_str = str(value) if not isinstance(value, (bytes, bytearray)) else ""
            except:
                value_str = ""
                
            # Check if query appears in key or value
            key_match = query_lower in key.lower()
            value_match = query_lower in value_str.lower()
            
            if key_match or value_match:
                # Simple relevance score based on exact matches
                if query_lower == key.lower() or query_lower == value_str.lower():
                    score = 1.0  # Exact match
                elif key.lower().startswith(query_lower) or value_str.lower().startswith(query_lower):
                    score = 0.9  # Starts with match
                else:
                    score = 0.7  # Contains match
                
                results.append((key, value, score))
                
        # Sort by score (highest first) and limit results
        results.sort(key=lambda x: x[2], reverse=True)
        logger.debug("Found %d matches for query '%s' in scope '%s'", 
                    len(results[:limit]), query, scope)
        return results[:limit] 