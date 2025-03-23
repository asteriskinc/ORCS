from typing import Any, Dict, List, Optional
import logging

from .system import MemorySystem
from ..system import AgentContext as LegacyAgentContext
from ..system import MemorySystem as LegacyMemorySystem

# Set up logger
logger = logging.getLogger("orcs.memory.v2.compatibility")

class LegacyCompatibleMemorySystem(LegacyMemorySystem):
    """Adapter for the new memory system to be compatible with legacy code
    
    This class provides an implementation of the old MemorySystem interface
    that delegates to the new MemorySystem implementation.
    """
    
    def __init__(self, new_memory_system: MemorySystem):
        """Initialize a legacy-compatible memory system
        
        Args:
            new_memory_system: The new MemorySystem implementation to delegate to
        """
        logger.info("Initializing LegacyCompatibleMemorySystem")
        self.new_memory = new_memory_system
        super().__init__()  # Initialize parent with default isolation
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information
        
        Args:
            key: The key to store the value under
            value: The value to store
            scope: The scope to store the data in (default: "global")
        """
        isolated_key = self._get_isolated_key(key)
        self.new_memory.store(isolated_key, value, scope)
        self.access_scopes[isolated_key] = scope  # Keep track for permissions
        logger.debug("Stored value for key '%s' in scope '%s'", key, scope)
    
    def retrieve(self, key: str, requesting_scope: str) -> Any:
        """Retrieve data if the requesting scope has access
        
        Args:
            key: The key to retrieve
            requesting_scope: The scope requesting access
            
        Returns:
            The stored value if accessible
            
        Raises:
            KeyError: If the key doesn't exist
            PermissionError: If the requesting scope doesn't have access
        """
        isolated_key = self._get_isolated_key(key)
        
        # First check if the key exists
        value = self.new_memory.retrieve(isolated_key, requesting_scope)
        if value is None:
            logger.warning("Key '%s' not found in memory", key)
            raise KeyError(f"Key '{key}' not found in memory")
        
        # Check if scope has access (for backward compatibility)
        target_scope = self.access_scopes.get(isolated_key)
        if target_scope is None:
            # If we don't have it in access_scopes, store it for future access checks
            self.access_scopes[isolated_key] = requesting_scope
            target_scope = requesting_scope
            
        if not self._has_access(requesting_scope, target_scope):
            logger.warning("Scope '%s' doesn't have access to data in scope '%s'", 
                          requesting_scope, target_scope)
            raise PermissionError(f"Scope '{requesting_scope}' doesn't have access to data in scope '{target_scope}'")
            
        logger.debug("Retrieved value for key '%s' from scope '%s' requested by scope '%s'", 
                    key, target_scope, requesting_scope)
        return value
    
    def list_keys(self, scope_pattern: str = "*") -> List[str]:
        """List all keys matching a scope pattern
        
        Args:
            scope_pattern: A pattern to match scopes (default: "*" for all scopes)
            
        Returns:
            A list of keys in matching scopes
        """
        # This is a bit tricky as the new system lists keys by pattern within a scope,
        # while the old one lists by scope pattern.
        # We'll need to gather keys from all scopes and filter.
        
        import re
        # Convert glob pattern to regex
        regex_pattern = "^" + scope_pattern.replace("*", ".*") + "$"
        pattern = re.compile(regex_pattern)
        
        # Get all unique scopes we know about
        scopes = set()
        for _, scope in self.access_scopes.items():
            scopes.add(scope)
            
        # For each matching scope, get the keys
        matching_keys = []
        for scope in scopes:
            if pattern.match(scope):
                # Get keys in this scope
                scope_keys = self.new_memory.list_keys("*", scope)
                
                # Strip isolation prefix if needed
                if self.isolation_provider:
                    prefix = self.isolation_provider.get_isolation_prefix()
                    prefix_len = len(prefix) + 1  # Plus 1 for the colon
                    scope_keys = [
                        key[prefix_len:] if key.startswith(f"{prefix}:") else key
                        for key in scope_keys
                    ]
                
                matching_keys.extend(scope_keys)
        
        logger.debug("Found %d keys matching scope pattern '%s'", len(matching_keys), scope_pattern)
        return matching_keys
    
    def create_agent_context(self, agent_id: str, workflow_id: str) -> 'CompatibleAgentContext':
        """Create a context object for an agent
        
        Args:
            agent_id: The ID of the agent
            workflow_id: The ID of the workflow
            
        Returns:
            A compatible AgentContext object
        """
        scope = f"workflow:{workflow_id}:agent:{agent_id}"
        logger.info("Creating compatible agent context for agent '%s' in workflow '%s' with scope '%s'", 
                   agent_id, workflow_id, scope)
        return CompatibleAgentContext(self, agent_id, workflow_id, scope)


class CompatibleAgentContext(LegacyAgentContext):
    """Compatibility wrapper for AgentContext
    
    Provides the old AgentContext interface with the new MemorySystem.
    """
    
    def __init__(self, memory_system: LegacyCompatibleMemorySystem, agent_id: str, 
                workflow_id: str, scope: str):
        """Initialize a compatible agent context
        
        Args:
            memory_system: The legacy-compatible memory system
            agent_id: The ID of the agent
            workflow_id: The ID of the workflow
            scope: The scope for this agent's memory
        """
        logger.debug("Initializing CompatibleAgentContext for agent '%s' in workflow '%s'", 
                    agent_id, workflow_id)
        self.memory = memory_system
        self.agent_id = agent_id
        self.workflow_id = workflow_id
        self.scope = scope 