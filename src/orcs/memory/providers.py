from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
import logging
import json
import os
import pickle

# Set up logger
logger = logging.getLogger("orcs.memory.providers")

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

    @abstractmethod
    def get_scope(self, key: str) -> str:
        """Get the scope of a specific key
        
        This method is used by hierarchical access control to determine
        parent-child relationships between scopes.
        
        Args:
            key: The key to get the scope for
            
        Returns:
            The scope of the key
            
        Raises:
            KeyError: If the key doesn't exist
            ValueError: If the scope can't be determined
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

    def get_scope(self, key: str) -> str:
        """Get the scope of a specific key
        
        Args:
            key: The key to get the scope for
            
        Returns:
            The scope of the key
            
        Raises:
            KeyError: If the key doesn't exist
            ValueError: If the scope can't be determined
        """
        # Search all scopes for the key
        for scope, scope_data in self.data.items():
            if key in scope_data:
                return scope
                
        raise KeyError(f"Key '{key}' not found in any scope")


class FileStorageProvider(StorageProvider):
    """File-based implementation of storage provider"""
    
    def __init__(self, storage_dir: str):
        """Initialize a file-based storage provider
        
        Args:
            storage_dir: The directory to store files in
        """
        logger.info("Initializing FileStorageProvider in '%s'", storage_dir)
        self.storage_dir = storage_dir
        self.index_file = os.path.join(storage_dir, "memory_index.json")
        self.index = self._load_index()
        
        # Create the storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
        
    def _load_index(self) -> Dict[str, Dict[str, str]]:
        """Load the index file
        
        Returns:
            The index data, mapping (scope, key) to file paths
        """
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Failed to load index file, creating new index")
                return {}
        return {}
        
    def _save_index(self) -> None:
        """Save the index file"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)
        
    def _get_file_path(self, key: str, scope: str) -> str:
        """Get the file path for a key in a scope
        
        Args:
            key: The key to get the path for
            scope: The scope the key is in
            
        Returns:
            The file path to use
        """
        # Use a deterministic filename based on scope and key
        import hashlib
        # Hash the scope and key to create a safe filename
        hash_str = hashlib.md5(f"{scope}:{key}".encode()).hexdigest()
        return os.path.join(self.storage_dir, f"{hash_str}.pickle")
        
    def save(self, key: str, value: Any, scope: str) -> None:
        """Save a value to a file
        
        Args:
            key: The key to save under
            value: The value to save
            scope: The scope to save in
        """
        file_path = self._get_file_path(key, scope)
        
        # Save the data
        with open(file_path, 'wb') as f:
            pickle.dump(value, f)
            
        # Update the index
        if scope not in self.index:
            self.index[scope] = {}
        self.index[scope][key] = file_path
        self._save_index()
        
        logger.debug("Saved value at key '%s' in scope '%s' to '%s'", 
                    key, scope, file_path)
        
    def load(self, key: str, scope: str) -> Any:
        """Load a value from a file
        
        Args:
            key: The key to load
            scope: The scope to load from
            
        Returns:
            The loaded value, or None if not found
        """
        if scope not in self.index or key not in self.index[scope]:
            logger.debug("Key '%s' not found in scope '%s'", key, scope)
            return None
            
        file_path = self.index[scope][key]
        if not os.path.exists(file_path):
            logger.warning("File for key '%s' in scope '%s' not found: '%s'", 
                          key, scope, file_path)
            return None
            
        try:
            with open(file_path, 'rb') as f:
                value = pickle.load(f)
            logger.debug("Loaded value from key '%s' in scope '%s' from '%s'", 
                        key, scope, file_path)
            return value
        except Exception as e:
            logger.error("Failed to load value from '%s': %s", file_path, str(e))
            return None
        
    def delete(self, key: str, scope: str) -> bool:
        """Delete a value from storage
        
        Args:
            key: The key to delete
            scope: The scope to delete from
            
        Returns:
            True if something was deleted, False otherwise
        """
        if scope not in self.index or key not in self.index[scope]:
            logger.debug("Cannot delete: key '%s' not found in scope '%s'", key, scope)
            return False
            
        file_path = self.index[scope][key]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error("Failed to delete file '%s': %s", file_path, str(e))
                
        # Update the index
        del self.index[scope][key]
        if not self.index[scope]:
            del self.index[scope]
        self._save_index()
        
        logger.debug("Deleted key '%s' from scope '%s'", key, scope)
        return True
        
    def list_keys(self, pattern: str, scope: str) -> List[str]:
        """List keys matching a pattern in a scope
        
        Args:
            pattern: The pattern to match against
            scope: The scope to list from
            
        Returns:
            List of matching keys
        """
        import re
        
        if scope not in self.index:
            logger.debug("No keys found in scope '%s'", scope)
            return []
            
        # Convert glob pattern to regex
        if pattern == "*":
            keys = list(self.index[scope].keys())
        else:
            regex_pattern = "^" + pattern.replace("*", ".*") + "$"
            regex = re.compile(regex_pattern)
            keys = [k for k in self.index[scope].keys() if regex.match(k)]
            
        logger.debug("Found %d keys matching pattern '%s' in scope '%s'", 
                    len(keys), pattern, scope)
        return keys
        
    def get_scope(self, key: str) -> str:
        """Get the scope of a specific key
        
        Args:
            key: The key to get the scope for
            
        Returns:
            The scope of the key
            
        Raises:
            KeyError: If the key doesn't exist
            ValueError: If the scope can't be determined
        """
        # Search all scopes for the key
        for scope, scope_data in self.index.items():
            if key in scope_data:
                return scope
                
        raise KeyError(f"Key '{key}' not found in any scope")

    def has_key(self, key: str, scope: str) -> bool:
        """Check if a key exists in a scope
        
        Args:
            key: The key to check
            scope: The scope to check in
            
        Returns:
            True if the key exists, False otherwise
        """
        has_key = scope in self.index and key in self.index[scope]
        logger.debug("Key '%s' %s in scope '%s'", 
                    key, "exists" if has_key else "does not exist", scope)
        return has_key 