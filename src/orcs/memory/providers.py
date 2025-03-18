from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Pattern
import os
import json
import pickle
import base64
import re
from datetime import datetime
import logging
import shutil

# Set up logger
logger = logging.getLogger("orcs.memory.providers")

class MemoryStorageProvider(ABC):
    """Abstract interface for memory storage providers
    
    This abstract class defines the operations that any storage provider
    must implement to be used with the memory system.
    """
    
    @abstractmethod
    def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a value with optional metadata
        
        Args:
            key: The key to store the value under
            value: The value to store
            metadata: Optional metadata about the value
        """
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Any:
        """Retrieve a value by key
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored value
            
        Raises:
            KeyError: If the key doesn't exist
        """
        pass
    
    @abstractmethod
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern
        
        Args:
            pattern: A glob pattern to match keys (default: "*" for all keys)
            
        Returns:
            A list of matching keys
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key-value pair
        
        Args:
            key: The key to delete
            
        Returns:
            True if deleted, False if key not found
        """
        pass
    
    @abstractmethod
    def has_key(self, key: str) -> bool:
        """Check if a key exists
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def store_binary(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store binary data
        
        Args:
            key: The key to store the data under
            data: The binary data to store
            metadata: Optional metadata about the data
        """
        pass
    
    @abstractmethod
    def retrieve_binary(self, key: str) -> bytes:
        """Retrieve binary data
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored binary data
            
        Raises:
            KeyError: If the key doesn't exist
        """
        pass
    
    def _glob_to_regex(self, pattern: str) -> Pattern:
        """Convert a glob pattern to a regex pattern
        
        Args:
            pattern: A glob pattern (e.g., "workflow:*:agent:*")
            
        Returns:
            A compiled regex pattern
        """
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern).replace('\\*', '.*').replace('\\?', '.')
        return re.compile(f"^{escaped}$")


class InMemoryStorageProvider(MemoryStorageProvider):
    """In-memory implementation of storage provider
    
    This provider stores all data in memory and is suitable for
    development, testing, and short-lived applications.
    """
    
    def __init__(self):
        """Initialize an in-memory storage provider"""
        logger.info("Initializing InMemoryStorageProvider")
        self.data = {}  # Main key-value store
        self.metadata = {}  # Metadata for keys
        self.binary_data = {}  # Binary data store
    
    def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a value with optional metadata
        
        Args:
            key: The key to store the value under
            value: The value to store
            metadata: Optional metadata about the value
        """
        logger.debug("Storing value for key '%s'", key)
        self.data[key] = value
        if metadata:
            self.metadata[key] = metadata
        elif key not in self.metadata:
            self.metadata[key] = {}
            
        # Add/update creation timestamp if not already present
        if "created_at" not in self.metadata[key]:
            self.metadata[key]["created_at"] = datetime.now().isoformat()
        
        # Always update last_modified timestamp
        self.metadata[key]["last_modified"] = datetime.now().isoformat()
    
    def retrieve(self, key: str) -> Any:
        """Retrieve a value by key
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored value
            
        Raises:
            KeyError: If the key doesn't exist
        """
        if key not in self.data:
            logger.warning("Key '%s' not found in memory", key)
            raise KeyError(f"Key '{key}' not found in memory")
            
        logger.debug("Retrieved value for key '%s'", key)
        
        # Update access metadata
        if key in self.metadata:
            self.metadata[key]["last_accessed"] = datetime.now().isoformat()
            self.metadata[key]["access_count"] = self.metadata[key].get("access_count", 0) + 1
            
        return self.data[key]
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern
        
        Args:
            pattern: A glob pattern to match keys (default: "*" for all keys)
            
        Returns:
            A list of matching keys
        """
        logger.debug("Listing keys with pattern '%s'", pattern)
        
        if pattern == "*":
            return list(self.data.keys())
            
        # Use regex for more complex patterns
        regex = self._glob_to_regex(pattern)
        return [key for key in self.data.keys() if regex.match(key)]
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair
        
        Args:
            key: The key to delete
            
        Returns:
            True if deleted, False if key not found
        """
        if key not in self.data:
            logger.warning("Cannot delete non-existent key '%s'", key)
            return False
            
        logger.debug("Deleting key '%s'", key)
        del self.data[key]
        if key in self.metadata:
            del self.metadata[key]
        if key in self.binary_data:
            del self.binary_data[key]
            
        return True
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        return key in self.data
    
    def store_binary(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store binary data
        
        Args:
            key: The key to store the data under
            data: The binary data to store
            metadata: Optional metadata about the data
        """
        logger.debug("Storing binary data for key '%s' (%d bytes)", key, len(data))
        self.binary_data[key] = data
        
        if metadata:
            self.metadata[key] = metadata
        elif key not in self.metadata:
            self.metadata[key] = {}
            
        # Add size to metadata
        self.metadata[key]["size_bytes"] = len(data)
        
        # Add/update timestamps
        if "created_at" not in self.metadata[key]:
            self.metadata[key]["created_at"] = datetime.now().isoformat()
        self.metadata[key]["last_modified"] = datetime.now().isoformat()
    
    def retrieve_binary(self, key: str) -> bytes:
        """Retrieve binary data
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored binary data
            
        Raises:
            KeyError: If the key doesn't exist
        """
        if key not in self.binary_data:
            logger.warning("Binary key '%s' not found in memory", key)
            raise KeyError(f"Binary key '{key}' not found in memory")
            
        logger.debug("Retrieved binary data for key '%s'", key)
        
        # Update access metadata
        if key in self.metadata:
            self.metadata[key]["last_accessed"] = datetime.now().isoformat()
            self.metadata[key]["access_count"] = self.metadata[key].get("access_count", 0) + 1
            
        return self.binary_data[key]
    
    def clear(self) -> None:
        """Clear all stored data
        
        This method removes all data, metadata, and binary data from the provider.
        """
        logger.info("Clearing all data from InMemoryStorageProvider")
        self.data.clear()
        self.metadata.clear()
        self.binary_data.clear()


class FileStorageProvider(MemoryStorageProvider):
    """File-based implementation of storage provider
    
    This provider persists all data to the filesystem, which makes
    it suitable for long-term storage that needs to survive restarts.
    """
    
    def __init__(self, storage_dir: str):
        """Initialize a file storage provider
        
        Args:
            storage_dir: Directory where data will be stored
        """
        self.storage_dir = os.path.abspath(storage_dir)
        self.data_dir = os.path.join(self.storage_dir, "data")
        self.binary_dir = os.path.join(self.storage_dir, "binary")
        self.metadata_file = os.path.join(self.storage_dir, "metadata.json")
        
        # Create directories if they don't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.binary_dir, exist_ok=True)
        
        # Load metadata if it exists
        self.metadata = self._load_metadata()
        
        logger.info("Initialized FileStorageProvider at '%s'", self.storage_dir)
        
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load metadata from file
        
        Returns:
            Dictionary of metadata indexed by key
        """
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error("Failed to load metadata: %s", str(e))
                return {}
        return {}
        
    def _save_metadata(self) -> None:
        """Save metadata to file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except IOError as e:
            logger.error("Failed to save metadata: %s", str(e))
    
    def _key_to_filename(self, key: str) -> str:
        """Convert a key to a valid filename
        
        Args:
            key: The key to convert
            
        Returns:
            A filename-safe representation of the key
        """
        # Replace characters that aren't allowed in filenames
        safe_key = key.replace(":", "_").replace("/", "_").replace("\\", "_")
        return safe_key
    
    def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a value with optional metadata
        
        Args:
            key: The key to store the value under
            value: The value to store
            metadata: Optional metadata about the value
        """
        filename = self._key_to_filename(key)
        filepath = os.path.join(self.data_dir, f"{filename}.pickle")
        
        try:
            # Serialize the value
            with open(filepath, 'wb') as f:
                pickle.dump(value, f)
                
            # Update metadata
            if key not in self.metadata:
                self.metadata[key] = {}
                self.metadata[key]["created_at"] = datetime.now().isoformat()
                
            self.metadata[key]["last_modified"] = datetime.now().isoformat()
            self.metadata[key]["filepath"] = filepath
            
            if metadata:
                self.metadata[key].update(metadata)
                
            self._save_metadata()
            logger.debug("Stored value for key '%s' at '%s'", key, filepath)
            
        except Exception as e:
            logger.error("Failed to store value for key '%s': %s", key, str(e))
            raise
    
    def retrieve(self, key: str) -> Any:
        """Retrieve a value by key
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored value
            
        Raises:
            KeyError: If the key doesn't exist
        """
        if key not in self.metadata or "filepath" not in self.metadata[key]:
            logger.warning("Key '%s' not found in storage", key)
            raise KeyError(f"Key '{key}' not found in storage")
            
        filepath = self.metadata[key]["filepath"]
        
        if not os.path.exists(filepath):
            logger.warning("File for key '%s' does not exist: %s", key, filepath)
            raise KeyError(f"File for key '{key}' does not exist: {filepath}")
            
        try:
            # Deserialize the value
            with open(filepath, 'rb') as f:
                value = pickle.load(f)
                
            # Update access metadata
            self.metadata[key]["last_accessed"] = datetime.now().isoformat()
            self.metadata[key]["access_count"] = self.metadata[key].get("access_count", 0) + 1
            self._save_metadata()
            
            logger.debug("Retrieved value for key '%s' from '%s'", key, filepath)
            return value
            
        except Exception as e:
            logger.error("Failed to retrieve value for key '%s': %s", key, str(e))
            raise KeyError(f"Failed to retrieve value for key '{key}': {str(e)}")
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern
        
        Args:
            pattern: A glob pattern to match keys (default: "*" for all keys)
            
        Returns:
            A list of matching keys
        """
        logger.debug("Listing keys with pattern '%s'", pattern)
        
        if pattern == "*":
            return list(self.metadata.keys())
            
        # Use regex for more complex patterns
        regex = self._glob_to_regex(pattern)
        return [key for key in self.metadata.keys() if regex.match(key)]
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair
        
        Args:
            key: The key to delete
            
        Returns:
            True if deleted, False if key not found
        """
        if key not in self.metadata:
            logger.warning("Cannot delete non-existent key '%s'", key)
            return False
            
        # Get file paths
        data_filepath = self.metadata[key].get("filepath", None)
        binary_filepath = self.metadata[key].get("binary_filepath", None)
        
        # Delete data file if it exists
        if data_filepath and os.path.exists(data_filepath):
            try:
                os.remove(data_filepath)
                logger.debug("Deleted data file for key '%s': %s", key, data_filepath)
            except OSError as e:
                logger.error("Failed to delete data file for key '%s': %s", key, str(e))
                
        # Delete binary file if it exists
        if binary_filepath and os.path.exists(binary_filepath):
            try:
                os.remove(binary_filepath)
                logger.debug("Deleted binary file for key '%s': %s", key, binary_filepath)
            except OSError as e:
                logger.error("Failed to delete binary file for key '%s': %s", key, str(e))
                
        # Remove from metadata
        del self.metadata[key]
        self._save_metadata()
        
        logger.debug("Deleted key '%s'", key)
        return True
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        return key in self.metadata
    
    def store_binary(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store binary data
        
        Args:
            key: The key to store the data under
            data: The binary data to store
            metadata: Optional metadata about the data
        """
        filename = self._key_to_filename(key)
        filepath = os.path.join(self.binary_dir, f"{filename}.bin")
        
        try:
            # Write binary data directly
            with open(filepath, 'wb') as f:
                f.write(data)
                
            # Update metadata
            if key not in self.metadata:
                self.metadata[key] = {}
                self.metadata[key]["created_at"] = datetime.now().isoformat()
                
            self.metadata[key]["last_modified"] = datetime.now().isoformat()
            self.metadata[key]["binary_filepath"] = filepath
            self.metadata[key]["size_bytes"] = len(data)
            
            if metadata:
                self.metadata[key].update(metadata)
                
            self._save_metadata()
            logger.debug("Stored binary data for key '%s' at '%s' (%d bytes)", 
                        key, filepath, len(data))
            
        except Exception as e:
            logger.error("Failed to store binary data for key '%s': %s", key, str(e))
            raise
    
    def retrieve_binary(self, key: str) -> bytes:
        """Retrieve binary data
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored binary data
            
        Raises:
            KeyError: If the key doesn't exist
        """
        if key not in self.metadata or "binary_filepath" not in self.metadata[key]:
            logger.warning("Binary key '%s' not found in storage", key)
            raise KeyError(f"Binary key '{key}' not found in storage")
            
        filepath = self.metadata[key]["binary_filepath"]
        
        if not os.path.exists(filepath):
            logger.warning("Binary file for key '%s' does not exist: %s", key, filepath)
            raise KeyError(f"Binary file for key '{key}' does not exist: {filepath}")
            
        try:
            # Read binary data directly
            with open(filepath, 'rb') as f:
                data = f.read()
                
            # Update access metadata
            self.metadata[key]["last_accessed"] = datetime.now().isoformat()
            self.metadata[key]["access_count"] = self.metadata[key].get("access_count", 0) + 1
            self._save_metadata()
            
            logger.debug("Retrieved binary data for key '%s' from '%s'", key, filepath)
            return data
            
        except Exception as e:
            logger.error("Failed to retrieve binary data for key '%s': %s", key, str(e))
            raise KeyError(f"Failed to retrieve binary data for key '{key}': {str(e)}")
            
    def clear(self) -> None:
        """Clear all stored data
        
        This method removes all data files, binary files, and metadata.
        """
        logger.warning("Clearing all data from FileStorageProvider at '%s'", self.storage_dir)
        
        try:
            # Remove data and binary directories
            shutil.rmtree(self.data_dir)
            shutil.rmtree(self.binary_dir)
            
            # Recreate empty directories
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(self.binary_dir, exist_ok=True)
            
            # Clear metadata
            self.metadata = {}
            self._save_metadata()
            
            logger.info("All data cleared from FileStorageProvider")
            
        except Exception as e:
            logger.error("Failed to clear data: %s", str(e))
            raise 