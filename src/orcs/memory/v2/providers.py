from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
import logging
import json

# Set up logger
logger = logging.getLogger("orcs.memory.v2.providers")

class StorageProvider(ABC):
    """Abstract interface for memory storage providers"""
    
    @abstractmethod
    def save(self, key: str, value: Any, scope: str) -> None:
        """Save a value with its scope
        
        Args:
            key: The key to save under
            value: The value to save
            scope: The scope to save in
        """
        pass
    
    @abstractmethod
    def load(self, key: str, scope: str) -> Any:
        """Load a value by key from a scope
        
        Args:
            key: The key to load
            scope: The scope to load from
            
        Returns:
            The loaded value, or None if not found
        """
        pass
    
    @abstractmethod
    def delete(self, key: str, scope: str) -> bool:
        """Delete a key-value pair from a scope
        
        Args:
            key: The key to delete
            scope: The scope to delete from
            
        Returns:
            True if something was deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def list_keys(self, pattern: str, scope: str) -> List[str]:
        """List keys matching a pattern in a scope
        
        Args:
            pattern: Pattern to match keys against
            scope: The scope to list keys from
            
        Returns:
            List of matching key names
        """
        pass
    
    @abstractmethod
    def has_key(self, key: str, scope: str) -> bool:
        """Check if a key exists in a scope
        
        Args:
            key: The key to check
            scope: The scope to check in
            
        Returns:
            True if the key exists, False otherwise
        """
        pass


class InMemoryStorageProvider(StorageProvider):
    """Simple in-memory implementation of the storage provider"""
    
    def __init__(self):
        """Initialize an in-memory storage provider"""
        logger.info("Initializing InMemoryStorageProvider")
        self.data = {}  # Dict[scope][key] = value
    
    def save(self, key: str, value: Any, scope: str) -> None:
        """Save a value with its scope
        
        Args:
            key: The key to save under
            value: The value to save
            scope: The scope to save in
        """
        if scope not in self.data:
            self.data[scope] = {}
        self.data[scope][key] = value
        logger.debug("Saved value at key '%s' in scope '%s'", key, scope)
    
    def load(self, key: str, scope: str) -> Any:
        """Load a value by key from a scope
        
        Args:
            key: The key to load
            scope: The scope to load from
            
        Returns:
            The loaded value, or None if not found
        """
        if scope not in self.data or key not in self.data[scope]:
            logger.debug("Key '%s' not found in scope '%s'", key, scope)
            return None
        logger.debug("Loaded value from key '%s' in scope '%s'", key, scope)
        return self.data[scope][key]
    
    def delete(self, key: str, scope: str) -> bool:
        """Delete a key-value pair from a scope
        
        Args:
            key: The key to delete
            scope: The scope to delete from
            
        Returns:
            True if something was deleted, False otherwise
        """
        if scope not in self.data or key not in self.data[scope]:
            logger.debug("Cannot delete: key '%s' not found in scope '%s'", key, scope)
            return False
        del self.data[scope][key]
        logger.debug("Deleted key '%s' from scope '%s'", key, scope)
        return True
    
    def list_keys(self, pattern: str, scope: str) -> List[str]:
        """List keys matching a pattern in a scope
        
        Args:
            pattern: Pattern to match keys against
            scope: The scope to list keys from
            
        Returns:
            List of matching key names
        """
        import re
        
        if scope not in self.data:
            logger.debug("No keys found in scope '%s'", scope)
            return []
            
        # Simple pattern matching using regex
        if pattern == "*":
            keys = list(self.data[scope].keys())
        else:
            # Convert glob pattern to regex
            regex_pattern = "^" + pattern.replace("*", ".*") + "$"
            regex = re.compile(regex_pattern)
            keys = [k for k in self.data[scope].keys() if regex.match(k)]
            
        logger.debug("Found %d keys matching pattern '%s' in scope '%s'", 
                    len(keys), pattern, scope)
        return keys
    
    def has_key(self, key: str, scope: str) -> bool:
        """Check if a key exists in a scope
        
        Args:
            key: The key to check
            scope: The scope to check in
            
        Returns:
            True if the key exists, False otherwise
        """
        has_key = scope in self.data and key in self.data[scope]
        logger.debug("Key '%s' %s in scope '%s'", 
                    key, "exists" if has_key else "does not exist", scope)
        return has_key


class FileStorageProvider(StorageProvider):
    """File-based implementation of the storage provider
    
    Stores data in JSON files organized by scope.
    """
    
    def __init__(self, base_path: str):
        """Initialize a file-based storage provider
        
        Args:
            base_path: Base directory for storing files
        """
        import os
        self.base_path = base_path
        logger.info("Initializing FileStorageProvider at %s", base_path)
        
        # Ensure base directory exists
        os.makedirs(base_path, exist_ok=True)
        
        # Cache for loaded scopes
        self.cache = {}
    
    def _get_scope_path(self, scope: str) -> str:
        """Get the file path for a scope
        
        Args:
            scope: The scope to get the path for
            
        Returns:
            The file path for the scope
        """
        import os
        # Replace characters that are not allowed in filenames
        safe_scope = scope.replace(":", "_").replace("/", "_")
        return os.path.join(self.base_path, f"{safe_scope}.json")
    
    def _load_scope(self, scope: str) -> Dict[str, Any]:
        """Load a scope from disk
        
        Args:
            scope: The scope to load
            
        Returns:
            The loaded scope data
        """
        import os
        
        # Check if already in cache
        if scope in self.cache:
            return self.cache[scope]
            
        # Get the file path
        scope_path = self._get_scope_path(scope)
        
        # If file doesn't exist, return empty dict
        if not os.path.exists(scope_path):
            self.cache[scope] = {}
            return {}
            
        # Load from file
        try:
            with open(scope_path, 'r') as f:
                scope_data = json.load(f)
                self.cache[scope] = scope_data
                logger.debug("Loaded scope '%s' from disk", scope)
                return scope_data
        except Exception as e:
            logger.error("Error loading scope '%s' from disk: %s", scope, str(e))
            self.cache[scope] = {}
            return {}
    
    def _save_scope(self, scope: str) -> None:
        """Save a scope to disk
        
        Args:
            scope: The scope to save
        """
        # Get the file path
        scope_path = self._get_scope_path(scope)
        
        # Save to file
        try:
            with open(scope_path, 'w') as f:
                json.dump(self.cache[scope], f, indent=2)
                logger.debug("Saved scope '%s' to disk", scope)
        except Exception as e:
            logger.error("Error saving scope '%s' to disk: %s", scope, str(e))
    
    def save(self, key: str, value: Any, scope: str) -> None:
        """Save a value with its scope
        
        Args:
            key: The key to save under
            value: The value to save
            scope: The scope to save in
        """
        # Load scope if not in cache
        if scope not in self.cache:
            self._load_scope(scope)
            
        # Update cache
        if scope not in self.cache:
            self.cache[scope] = {}
        self.cache[scope][key] = value
        
        # Save to disk
        self._save_scope(scope)
        logger.debug("Saved value at key '%s' in scope '%s'", key, scope)
    
    def load(self, key: str, scope: str) -> Any:
        """Load a value by key from a scope
        
        Args:
            key: The key to load
            scope: The scope to load from
            
        Returns:
            The loaded value, or None if not found
        """
        # Load scope if not in cache
        if scope not in self.cache:
            self._load_scope(scope)
            
        # Check if key exists
        if scope not in self.cache or key not in self.cache[scope]:
            logger.debug("Key '%s' not found in scope '%s'", key, scope)
            return None
            
        logger.debug("Loaded value from key '%s' in scope '%s'", key, scope)
        return self.cache[scope][key]
    
    def delete(self, key: str, scope: str) -> bool:
        """Delete a key-value pair from a scope
        
        Args:
            key: The key to delete
            scope: The scope to delete from
            
        Returns:
            True if something was deleted, False otherwise
        """
        # Load scope if not in cache
        if scope not in self.cache:
            self._load_scope(scope)
            
        # Check if key exists
        if scope not in self.cache or key not in self.cache[scope]:
            logger.debug("Cannot delete: key '%s' not found in scope '%s'", key, scope)
            return False
            
        # Delete from cache
        del self.cache[scope][key]
        
        # Save to disk
        self._save_scope(scope)
        logger.debug("Deleted key '%s' from scope '%s'", key, scope)
        return True
    
    def list_keys(self, pattern: str, scope: str) -> List[str]:
        """List keys matching a pattern in a scope
        
        Args:
            pattern: Pattern to match keys against
            scope: The scope to list keys from
            
        Returns:
            List of matching key names
        """
        import re
        
        # Load scope if not in cache
        if scope not in self.cache:
            self._load_scope(scope)
            
        if scope not in self.cache:
            logger.debug("No keys found in scope '%s'", scope)
            return []
            
        # Simple pattern matching using regex
        if pattern == "*":
            keys = list(self.cache[scope].keys())
        else:
            # Convert glob pattern to regex
            regex_pattern = "^" + pattern.replace("*", ".*") + "$"
            regex = re.compile(regex_pattern)
            keys = [k for k in self.cache[scope].keys() if regex.match(k)]
            
        logger.debug("Found %d keys matching pattern '%s' in scope '%s'", 
                    len(keys), pattern, scope)
        return keys
    
    def has_key(self, key: str, scope: str) -> bool:
        """Check if a key exists in a scope
        
        Args:
            key: The key to check
            scope: The scope to check in
            
        Returns:
            True if the key exists, False otherwise
        """
        # Load scope if not in cache
        if scope not in self.cache:
            self._load_scope(scope)
            
        has_key = scope in self.cache and key in self.cache[scope]
        logger.debug("Key '%s' %s in scope '%s'", 
                    key, "exists" if has_key else "does not exist", scope)
        return has_key 