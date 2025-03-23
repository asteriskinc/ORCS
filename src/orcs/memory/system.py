from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional, Dict
import logging
import re

# Set up logger
logger = logging.getLogger("orcs.memory.system")

class MemorySystem(ABC):
    """Unified memory system interface for underlying storage and retrieval"""
    
    @abstractmethod
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information
        
        Args:
            key: The key to store data under
            value: The data to store
            scope: The scope to store the data in (default: "global")
        """
        pass
        
    @abstractmethod
    def retrieve(self, key: str, scope: str = "global") -> Any:
        """Retrieve data from specified scope
        
        Args:
            key: The key to retrieve
            scope: The scope to retrieve from (default: "global")
            
        Returns:
            The stored value, or None if not found
        """
        pass
        
    @abstractmethod
    def delete(self, key: str, scope: str = "global") -> bool:
        """Delete data from specified scope
        
        Args:
            key: The key to delete
            scope: The scope to delete from (default: "global")
            
        Returns:
            True if something was deleted, False otherwise
        """
        pass
        
    @abstractmethod
    def list_keys(self, pattern: str = "*", scope: str = "global") -> List[str]:
        """List keys matching a pattern in specified scope
        
        Args:
            pattern: Pattern to match keys against (default: "*" for all keys)
            scope: The scope to list keys from (default: "global")
            
        Returns:
            List of matching key names
        """
        pass
        
    @abstractmethod
    def search(self, query: str, scope: str = "global", limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Search for content semantically similar to the query
        
        Args:
            query: The search query
            scope: The scope to search in (default: "global")
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of (key, content, score) tuples
        """
        pass
        
    @abstractmethod
    def has_access(self, requesting_scope: str, target_scope: str) -> bool:
        """Check if a scope has access to data in another scope
        
        Access rules might include:
        - "global" scope is accessible by all
        - A scope has access to its own data
        - A parent scope has access to its children's data
          (e.g., "workflow:123" has access to "workflow:123:task:456")
        
        Args:
            requesting_scope: The scope requesting access
            target_scope: The scope being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        pass


class BasicMemorySystem(MemorySystem):
    """Simple in-memory implementation of the memory system"""
    
    def __init__(self):
        """Initialize an in-memory storage system"""
        logger.info("Initializing BasicMemorySystem")
        self.data = {}  # Dict[scope][key] = value
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information
        
        Args:
            key: The key to store data under
            value: The data to store
            scope: The scope to store the data in (default: "global")
        """
        if scope not in self.data:
            self.data[scope] = {}
        self.data[scope][key] = value
        logger.debug("Stored value at key '%s' in scope '%s'", key, scope)
        
    def retrieve(self, key: str, scope: str = "global") -> Any:
        """Retrieve data from specified scope
        
        Args:
            key: The key to retrieve
            scope: The scope to retrieve from (default: "global")
            
        Returns:
            The stored value, or None if not found
        """
        if scope not in self.data or key not in self.data[scope]:
            logger.debug("Key '%s' not found in scope '%s'", key, scope)
            return None
        logger.debug("Retrieved value from key '%s' in scope '%s'", key, scope)
        return self.data[scope][key]
        
    def delete(self, key: str, scope: str = "global") -> bool:
        """Delete data from specified scope
        
        Args:
            key: The key to delete
            scope: The scope to delete from (default: "global")
            
        Returns:
            True if something was deleted, False otherwise
        """
        if scope not in self.data or key not in self.data[scope]:
            logger.debug("Cannot delete: key '%s' not found in scope '%s'", key, scope)
            return False
        del self.data[scope][key]
        logger.debug("Deleted key '%s' from scope '%s'", key, scope)
        return True
        
    def list_keys(self, pattern: str = "*", scope: str = "global") -> List[str]:
        """List keys matching a pattern in specified scope
        
        Args:
            pattern: Pattern to match keys against (default: "*" for all keys)
            scope: The scope to list keys from (default: "global")
            
        Returns:
            List of matching key names
        """
        if scope not in self.data:
            logger.debug("No keys found in scope '%s'", scope)
            return []
            
        # Simple pattern matching - in a real implementation you'd use regex or glob
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
        
    def search(self, query: str, scope: str = "global", limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Basic search implementation that checks for keyword presence
        
        Args:
            query: The search query
            scope: The scope to search in (default: "global")
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of (key, content, score) tuples
        """
        if scope not in self.data:
            logger.debug("No data found in scope '%s' for search", scope)
            return []
            
        results = []
        query_lower = query.lower()
        for key, value in self.data[scope].items():
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
        
    def has_access(self, requesting_scope: str, target_scope: str) -> bool:
        """Check if a scope has access to data in another scope
        
        This basic implementation only allows access to:
        - The "global" scope (accessible by all)
        - The same scope (a scope can access its own data)
        
        Args:
            requesting_scope: The scope requesting access
            target_scope: The scope being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Global scope is accessible by all
        if target_scope == "global":
            return True
            
        # Same scope has access
        if requesting_scope == target_scope:
            return True
            
        # No hierarchical access in the basic implementation
        return False


class ScopedAccessMemorySystem(BasicMemorySystem):
    """Memory system with hierarchical scope access controls
    
    This extended memory system adds v1-style access control:
    - "global" scope is accessible by all
    - A scope has access to its own data
    - A parent scope has access to its children's data
    
    This is useful for maintaining hierarchical workflows where a higher-level
    scope (like a workflow) needs access to data in child scopes (like tasks).
    """
    
    def has_access(self, requesting_scope: str, target_scope: str) -> bool:
        """Check if a scope has access to data in another scope
        
        Access rules:
        - "global" scope is accessible by all
        - A scope has access to its own data
        - A parent scope has access to its children's data
          (e.g., "workflow:123" has access to "workflow:123:task:456")
        
        Args:
            requesting_scope: The scope requesting access
            target_scope: The scope being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Global scope is accessible by all
        if target_scope == "global":
            return True
            
        # Same scope has access
        if requesting_scope == target_scope:
            return True
            
        # Check if requesting_scope is a parent of target_scope
        has_access = target_scope.startswith(f"{requesting_scope}:")
        logger.debug("Access check: %s -> %s = %s", requesting_scope, target_scope, has_access)
        return has_access
    
    def retrieve(self, key: str, scope: str = "global") -> Any:
        """Retrieve data with hierarchical scope access controls
        
        This method first checks the specified scope directly.
        If not found and the scope is "global", it returns None.
        Otherwise, it checks child scopes that the requesting scope has access to.
        
        Args:
            key: The key to retrieve
            scope: The scope to retrieve from (default: "global")
            
        Returns:
            The stored value, or None if not found or not accessible
        """
        # First try direct access in the provided scope
        value = super().retrieve(key, scope)
        if value is not None:
            return value
            
        # If not in global scope, try to find in child scopes
        if scope != "global":
            # Look through all stored scopes for ones the requester can access
            for data_scope in self.data.keys():
                # Skip if we already checked this scope or don't have access
                if data_scope == scope or not self.has_access(scope, data_scope):
                    continue
                    
                if key in self.data[data_scope]:
                    logger.debug("Found key '%s' in child scope '%s' for requester '%s'", 
                                key, data_scope, scope)
                    return self.data[data_scope][key]
                    
        return None
    
    def list_keys(self, pattern: str = "*", scope: str = "global", include_child_scopes: bool = False) -> List[str]:
        """List keys matching a pattern in specified scope
        
        Args:
            pattern: Pattern to match keys against (default: "*" for all keys)
            scope: The scope to list keys from (default: "global")
            include_child_scopes: Whether to include keys from child scopes
            
        Returns:
            List of matching key names
        """
        # Get keys from the direct scope
        keys = super().list_keys(pattern, scope)
        
        # If not including child scopes, return just these keys
        if not include_child_scopes:
            return keys
            
        # Otherwise, collect keys from child scopes
        for data_scope in self.data.keys():
            # Skip if we already included this scope or don't have access
            if data_scope == scope or not self.has_access(scope, data_scope):
                continue
                
            # Get matching keys from this child scope
            child_keys = super().list_keys(pattern, data_scope)
            keys.extend(child_keys)
            
        # Return deduplicated keys
        return list(set(keys)) 