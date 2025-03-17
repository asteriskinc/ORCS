from typing import Any, Dict, List, Optional
import re
import logging

# Set up logger
logger = logging.getLogger("orcs.memory.system")

class MemorySystem:
    """Unified memory system with access controls and scoping"""
    
    def __init__(self, isolation_provider=None):
        logger.info("Initializing MemorySystem%s", 
                    " with isolation provider" if isolation_provider else "")
        self.data: Dict[str, Any] = {}  # Key-value store
        self.access_scopes: Dict[str, str] = {}  # Maps keys to their access scopes
        self.isolation_provider = isolation_provider
        
    def _get_isolated_key(self, key: str) -> str:
        """Get key with isolation prefix if provider exists
        
        Args:
            key: The original key
            
        Returns:
            Key with isolation prefix if provider exists, original key otherwise
        """
        if not self.isolation_provider:
            return key
            
        isolation_prefix = self.isolation_provider.get_isolation_prefix()
        isolated_key = f"{isolation_prefix}:{key}"
        logger.debug("Mapped key '%s' to isolated key '%s'", key, isolated_key)
        return isolated_key
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information
        
        Args:
            key: The key to store the value under
            value: The value to store
            scope: The scope to store the data in (default: "global")
        """
        isolated_key = self._get_isolated_key(key)
        self.data[isolated_key] = value
        self.access_scopes[isolated_key] = scope
        logger.debug("Stored value for key '%s' in scope '%s'", key, scope)
        
    def retrieve(self, key: str, requesting_scope: str) -> Any:
        """Retrieve data if the requesting scope has access
        
        Args:
            key: The key to retrieve
            requesting_scope: The scope requesting access
            
        Returns:
            The stored value if accessible, None otherwise
            
        Raises:
            KeyError: If the key doesn't exist
            PermissionError: If the requesting scope doesn't have access
        """
        isolated_key = self._get_isolated_key(key)
        if isolated_key not in self.data:
            logger.warning("Key '%s' not found in memory", key)
            raise KeyError(f"Key '{key}' not found in memory")
            
        target_scope = self.access_scopes[isolated_key]
        if not self._has_access(requesting_scope, target_scope):
            logger.warning("Scope '%s' doesn't have access to data in scope '%s'", 
                           requesting_scope, target_scope)
            raise PermissionError(f"Scope '{requesting_scope}' doesn't have access to data in scope '{target_scope}'")
            
        logger.debug("Retrieved value for key '%s' from scope '%s' requested by scope '%s'", 
                     key, target_scope, requesting_scope)
        return self.data[isolated_key]
        
    def list_keys(self, scope_pattern: str = "*") -> List[str]:
        """List all keys matching a scope pattern
        
        Args:
            scope_pattern: A pattern to match scopes (default: "*" for all scopes)
            
        Returns:
            A list of keys in matching scopes
        """
        logger.debug("Listing keys with scope pattern '%s'", scope_pattern)
        # Convert glob pattern to regex
        regex_pattern = "^" + scope_pattern.replace("*", ".*") + "$"
        pattern = re.compile(regex_pattern)
        
        matching_keys = []
        for isolated_key, scope in self.access_scopes.items():
            if pattern.match(scope):
                # If using isolation, strip the isolation prefix before returning keys
                if self.isolation_provider:
                    prefix = self.isolation_provider.get_isolation_prefix()
                    if isolated_key.startswith(f"{prefix}:"):
                        # Return the original key without the isolation prefix
                        original_key = isolated_key[len(prefix)+1:]
                        matching_keys.append(original_key)
                else:
                    matching_keys.append(isolated_key)
        
        logger.debug("Found %d keys matching scope pattern '%s'", len(matching_keys), scope_pattern)
        return matching_keys
        
    def _has_access(self, requesting_scope: str, target_scope: str) -> bool:
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
        
    def create_agent_context(self, agent_id: str, workflow_id: str) -> 'AgentContext':
        """Create a context object for an agent
        
        Args:
            agent_id: The ID of the agent
            workflow_id: The ID of the workflow
            
        Returns:
            An AgentContext object
        """
        scope = f"workflow:{workflow_id}:agent:{agent_id}"
        logger.info("Creating agent context for agent '%s' in workflow '%s' with scope '%s'", 
                   agent_id, workflow_id, scope)
        return AgentContext(self, agent_id, workflow_id, scope)


class AgentContext:
    """Context object for agents to interact with memory"""
    
    def __init__(self, memory_system: MemorySystem, agent_id: str, 
                workflow_id: str, scope: str):
        """Initialize an agent context
        
        Args:
            memory_system: The memory system to use
            agent_id: The ID of the agent
            workflow_id: The ID of the workflow
            scope: The scope for this agent's memory
        """
        logger.debug("Initializing AgentContext for agent '%s' in workflow '%s'", 
                    agent_id, workflow_id)
        self.memory = memory_system
        self.agent_id = agent_id
        self.workflow_id = workflow_id
        self.scope = scope
        
    def store(self, key: str, value: Any, sub_scope: Optional[str] = None) -> None:
        """Store data in agent's scope
        
        Args:
            key: The key to store the value under
            value: The value to store
            sub_scope: Optional sub-scope within the agent's scope
        """
        if sub_scope:
            full_scope = f"{self.scope}:{sub_scope}"
        else:
            full_scope = self.scope
        
        logger.debug("Agent '%s' storing key '%s'%s", 
                    self.agent_id, key, f" in sub-scope '{sub_scope}'" if sub_scope else "")
        self.memory.store(key, value, full_scope)
        
    def retrieve(self, key: str) -> Any:
        """Retrieve data accessible to the agent
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored value
            
        Raises:
            KeyError: If the key doesn't exist
            PermissionError: If the agent doesn't have access
        """
        logger.debug("Agent '%s' retrieving key '%s'", self.agent_id, key)
        return self.memory.retrieve(key, self.scope)
        
    def retrieve_global(self, key: str) -> Any:
        """Retrieve global data
        
        Args:
            key: The key to retrieve
            
        Returns:
            The stored global value
            
        Raises:
            KeyError: If the key doesn't exist
        """
        logger.debug("Agent '%s' retrieving global key '%s'", self.agent_id, key)
        try:
            return self.memory.retrieve(key, "global")
        except PermissionError:
            # This shouldn't happen for global data, but just in case
            logger.warning("Global key '%s' not accessible to agent '%s'", key, self.agent_id)
            raise KeyError(f"Global key '{key}' not accessible")
            
    def list_keys(self, include_global: bool = True) -> List[str]:
        """List keys accessible to this agent
        
        Args:
            include_global: Whether to include global keys
            
        Returns:
            A list of accessible keys
        """
        logger.debug("Agent '%s' listing keys (include_global=%s)", self.agent_id, include_global)
        # Get keys in agent's scope
        agent_keys = self.memory.list_keys(self.scope)
        
        if include_global:
            # Get global keys
            global_keys = self.memory.list_keys("global")
            # Combine and remove duplicates
            return list(set(agent_keys + global_keys))
        
        return agent_keys 