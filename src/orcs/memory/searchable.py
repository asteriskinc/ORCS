from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import uuid
import numpy as np
from datetime import datetime

from .system import MemorySystem, AgentContext
from .content import MemoryContent, generate_memory_key
from .embeddings import (
    EmbeddingProvider, 
    create_default_embedding_provider, 
    cosine_similarity
)
from .providers import MemoryStorageProvider, InMemoryStorageProvider

# Set up logger
logger = logging.getLogger("orcs.memory.searchable")

class SearchableMemorySystem(MemorySystem):
    """Enhanced memory system with semantic search capabilities
    
    This extended memory system adds support for:
    - Rich content storage with metadata
    - Vector embeddings for semantic search
    - Multiple storage backend support
    """
    
    def __init__(self, 
                storage_provider: Optional[MemoryStorageProvider] = None,
                embedding_provider: Optional[EmbeddingProvider] = None,
                isolation_provider = None):
        """Initialize a searchable memory system
        
        Args:
            storage_provider: Provider for persistent storage (default: in-memory)
            embedding_provider: Provider for generating embeddings (default: mock/best available)
            isolation_provider: Provider for isolation between instances
        """
        super().__init__(isolation_provider)
        
        # Replace simple dict storage with provider-based storage
        self.storage_provider = storage_provider or InMemoryStorageProvider()
        self.embedding_provider = embedding_provider or create_default_embedding_provider()
        
        # Cache for embeddings to avoid regenerating
        self.embedding_cache = {}
        
        logger.info("Initialized SearchableMemorySystem with %s and %s", 
                   self.storage_provider.__class__.__name__,
                   self.embedding_provider.__class__.__name__)
        
    def store_content(self, key: str, content: MemoryContent, scope: str = "global") -> None:
        """Store rich content with metadata
        
        Args:
            key: The key to store the content under
            content: MemoryContent object to store
            scope: The scope to store the content in (default: "global")
        """
        isolated_key = self._get_isolated_key(key)
        
        # Generate embedding if content is string or has string content
        if content.embedding is None:
            content_text = self._get_embeddable_text(content)
            if content_text:
                try:
                    embedding = self.embedding_provider.embed(content_text)
                    content.embedding = embedding
                    self.embedding_cache[isolated_key] = embedding
                    logger.debug("Generated embedding for content with key '%s'", key)
                except Exception as e:
                    logger.error("Failed to generate embedding for key '%s': %s", key, str(e))
        
        # Store in provider
        self.storage_provider.store(isolated_key, content)
        self.access_scopes[isolated_key] = scope
        
        logger.debug("Stored content for key '%s' in scope '%s'", key, scope)
    
    def retrieve_content(self, key: str, requesting_scope: str) -> MemoryContent:
        """Retrieve content if the requesting scope has access
        
        Args:
            key: The key to retrieve
            requesting_scope: The scope requesting access
            
        Returns:
            The stored MemoryContent object
            
        Raises:
            KeyError: If the key doesn't exist
            PermissionError: If the requesting scope doesn't have access
            TypeError: If the stored value is not a MemoryContent object
        """
        isolated_key = self._get_isolated_key(key)
        
        # Check if key exists
        if not self.storage_provider.has_key(isolated_key):
            logger.warning("Key '%s' not found in memory", key)
            raise KeyError(f"Key '{key}' not found in memory")
        
        # Check access permission    
        target_scope = self.access_scopes.get(isolated_key)
        if target_scope is None:
            # If key exists in provider but not in scopes, add it with default scope
            logger.warning("Key '%s' found in storage but missing from access_scopes, "
                         "adding with global scope", key)
            self.access_scopes[isolated_key] = "global"
            target_scope = "global"
            
        if not self._has_access(requesting_scope, target_scope):
            logger.warning("Scope '%s' doesn't have access to data in scope '%s'", 
                           requesting_scope, target_scope)
            raise PermissionError(f"Scope '{requesting_scope}' doesn't have access to data in scope '{target_scope}'")
        
        # Retrieve from provider
        content = self.storage_provider.retrieve(isolated_key)
        
        # Type check
        if not isinstance(content, MemoryContent):
            logger.error("Retrieved value for key '%s' is not a MemoryContent object", key)
            raise TypeError(f"Retrieved value for key '{key}' is not a MemoryContent object")
        
        # Update access metadata
        content.was_accessed()
        
        logger.debug("Retrieved content for key '%s' from scope '%s' requested by scope '%s'", 
                     key, target_scope, requesting_scope)
        return content
    
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information (override parent for provider support)
        
        Args:
            key: The key to store the value under
            value: The value to store
            scope: The scope to store the data in (default: "global")
        """
        isolated_key = self._get_isolated_key(key)
        
        # Store in provider
        self.storage_provider.store(isolated_key, value)
        self.access_scopes[isolated_key] = scope
        
        logger.debug("Stored value for key '%s' in scope '%s'", key, scope)
    
    def retrieve(self, key: str, requesting_scope: str) -> Any:
        """Retrieve data if the requesting scope has access (override parent for provider support)
        
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
        
        # Check if key exists
        if not self.storage_provider.has_key(isolated_key):
            logger.warning("Key '%s' not found in memory", key)
            raise KeyError(f"Key '{key}' not found in memory")
        
        # Check access permission    
        target_scope = self.access_scopes.get(isolated_key)
        if target_scope is None:
            # If key exists in provider but not in scopes, add it with default scope
            logger.warning("Key '%s' found in storage but missing from access_scopes, "
                         "adding with global scope", key)
            self.access_scopes[isolated_key] = "global"
            target_scope = "global"
            
        if not self._has_access(requesting_scope, target_scope):
            logger.warning("Scope '%s' doesn't have access to data in scope '%s'", 
                           requesting_scope, target_scope)
            raise PermissionError(f"Scope '{requesting_scope}' doesn't have access to data in scope '{target_scope}'")
        
        # Retrieve from provider
        value = self.storage_provider.retrieve(isolated_key)
        
        logger.debug("Retrieved value for key '%s' from scope '%s' requested by scope '%s'", 
                     key, target_scope, requesting_scope)
        return value
    
    def list_keys(self, scope_pattern: str = "*") -> List[str]:
        """List all keys matching a scope pattern (override parent for provider support)
        
        Args:
            scope_pattern: A pattern to match scopes (default: "*" for all scopes)
            
        Returns:
            A list of keys in matching scopes
        """
        logger.debug("Listing keys with scope pattern '%s'", scope_pattern)
        
        # First get all matching scopes
        if scope_pattern == "*":
            matching_scopes = list(set(self.access_scopes.values()))
        else:
            # Convert glob pattern to regex
            import re
            regex_pattern = "^" + scope_pattern.replace("*", ".*") + "$"
            pattern = re.compile(regex_pattern)
            
            # Find matching scopes
            matching_scopes = []
            for scope in set(self.access_scopes.values()):
                if pattern.match(scope):
                    matching_scopes.append(scope)
        
        # Then get all keys in those scopes
        matching_keys = []
        for isolated_key, scope in self.access_scopes.items():
            if scope in matching_scopes:
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
    
    def search(self, query: str, requesting_scope: str, limit: int = 5, 
              min_similarity: float = 0.5) -> List[Tuple[MemoryContent, float]]:
        """Search for content semantically similar to the query
        
        Args:
            query: The search query
            requesting_scope: The scope requesting access
            limit: Maximum number of results (default: 5)
            min_similarity: Minimum similarity score to include in results
            
        Returns:
            List of (content, similarity) tuples, sorted by similarity (highest first)
        """
        logger.debug("Searching for '%s' in scope '%s' (limit: %d)", 
                    query, requesting_scope, limit)
        
        # Generate query embedding
        try:
            query_embedding = self.embedding_provider.embed(query)
        except Exception as e:
            logger.error("Failed to generate embedding for query: %s", str(e))
            return []
        
        # Get all keys the scope has access to
        accessible_keys = self._get_accessible_keys(requesting_scope)
        
        # Calculate similarity for each key that has an embedding
        similarities = []
        for key in accessible_keys:
            try:
                # First check embedding cache
                if key in self.embedding_cache:
                    embedding = self.embedding_cache[key]
                    similarity = cosine_similarity(query_embedding, embedding)
                    similarities.append((key, similarity))
                    continue
                    
                # Otherwise try to retrieve content and check embedding
                content = self.storage_provider.retrieve(key)
                if isinstance(content, MemoryContent) and content.embedding is not None:
                    similarity = cosine_similarity(query_embedding, content.embedding)
                    # Cache the embedding for future searches
                    self.embedding_cache[key] = content.embedding
                    similarities.append((key, similarity))
                    continue
                    
                # If it's a MemoryContent but has no embedding, try to generate one
                if isinstance(content, MemoryContent):
                    content_text = self._get_embeddable_text(content)
                    if content_text:
                        try:
                            embedding = self.embedding_provider.embed(content_text)
                            content.embedding = embedding
                            self.embedding_cache[key] = embedding
                            self.storage_provider.store(key, content)  # Update stored content
                            similarity = cosine_similarity(query_embedding, embedding)
                            similarities.append((key, similarity))
                        except Exception as e:
                            logger.error("Failed to generate embedding for key '%s': %s", 
                                       key, str(e))
            except Exception as e:
                logger.error("Error processing key '%s' during search: %s", key, str(e))
                continue
        
        # Sort by similarity (highest first) and filter by minimum similarity
        similarities = [(k, s) for k, s in similarities if s >= min_similarity]
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        top_keys = [key for key, _ in similarities[:limit]]
        
        # Retrieve content for each key
        results = []
        for key, similarity in similarities[:limit]:
            try:
                content = self.storage_provider.retrieve(key)
                if isinstance(content, MemoryContent):
                    # Update access metadata
                    content.was_accessed()
                    results.append((content, similarity))
                else:
                    logger.warning("Key '%s' does not contain MemoryContent", key)
            except Exception as e:
                logger.error("Error retrieving key '%s': %s", key, str(e))
        
        logger.info("Found %d results for query '%s'", len(results), query)
        return results
    
    def _get_accessible_keys(self, requesting_scope: str) -> List[str]:
        """Get all keys that a scope has access to
        
        Args:
            requesting_scope: The scope requesting access
            
        Returns:
            List of accessible keys
        """
        accessible_keys = []
        for key, scope in self.access_scopes.items():
            if self._has_access(requesting_scope, scope):
                accessible_keys.append(key)
        return accessible_keys
        
    def _get_embeddable_text(self, content: MemoryContent) -> Optional[str]:
        """Extract text that can be embedded from a MemoryContent object
        
        Args:
            content: The MemoryContent object
            
        Returns:
            String representation suitable for embedding, or None if not embeddable
        """
        if isinstance(content.content, str):
            return content.content
        elif hasattr(content.content, '__str__'):
            # Try to convert to string if it has a string representation
            return str(content.content)
        return None
    
    def create_agent_context(self, agent_id: str, workflow_id: str) -> 'SearchableAgentContext':
        """Create a context object for an agent
        
        Args:
            agent_id: The ID of the agent
            workflow_id: The ID of the workflow
            
        Returns:
            A SearchableAgentContext object
        """
        scope = f"workflow:{workflow_id}:agent:{agent_id}"
        logger.info("Creating searchable agent context for agent '%s' in workflow '%s' with scope '%s'", 
                   agent_id, workflow_id, scope)
        return SearchableAgentContext(self, agent_id, workflow_id, scope)


class SearchableAgentContext(AgentContext):
    """Enhanced context object for agents to interact with searchable memory"""
    
    def __init__(self, memory_system: SearchableMemorySystem, agent_id: str, 
                workflow_id: str, scope: str):
        """Initialize a searchable agent context
        
        Args:
            memory_system: The searchable memory system to use
            agent_id: The ID of the agent
            workflow_id: The ID of the workflow
            scope: The scope for this agent's memory
        """
        super().__init__(memory_system, agent_id, workflow_id, scope)
        
    @property
    def searchable_memory(self) -> SearchableMemorySystem:
        """Get the searchable memory system
        
        Returns:
            The searchable memory system
        """
        return self.memory
    
    def remember_insight(self, 
                        insight: str, 
                        importance: float = 0.5, 
                        tags: Optional[List[str]] = None, 
                        sub_scope: Optional[str] = None) -> str:
        """Store an important insight in memory
        
        Args:
            insight: The insight text
            importance: Importance score (0.0 to 1.0)
            tags: Optional tags for better retrieval
            sub_scope: Optional sub-scope within the agent's scope
            
        Returns:
            The key under which the insight was stored
        """
        memory_key = generate_memory_key("insight")
        
        content = MemoryContent(
            content=insight,
            importance=importance,
            memory_type="insight",
            tags=tags or [],
            metadata={
                "agent_id": self.agent_id,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if sub_scope:
            full_scope = f"{self.scope}:{sub_scope}"
        else:
            full_scope = self.scope
            
        self.searchable_memory.store_content(memory_key, content, full_scope)
        
        logger.debug("Agent '%s' stored insight with key '%s' (importance: %.2f)", 
                    self.agent_id, memory_key, importance)
        
        return memory_key
    
    def remember_fact(self, 
                     fact: str, 
                     importance: float = 0.5, 
                     tags: Optional[List[str]] = None, 
                     sub_scope: Optional[str] = None) -> str:
        """Store a factual knowledge in memory
        
        Args:
            fact: The factual information
            importance: Importance score (0.0 to 1.0)
            tags: Optional tags for better retrieval
            sub_scope: Optional sub-scope within the agent's scope
            
        Returns:
            The key under which the fact was stored
        """
        memory_key = generate_memory_key("fact")
        
        content = MemoryContent(
            content=fact,
            importance=importance,
            memory_type="fact",
            tags=tags or [],
            metadata={
                "agent_id": self.agent_id,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if sub_scope:
            full_scope = f"{self.scope}:{sub_scope}"
        else:
            full_scope = self.scope
            
        self.searchable_memory.store_content(memory_key, content, full_scope)
        
        logger.debug("Agent '%s' stored fact with key '%s' (importance: %.2f)", 
                    self.agent_id, memory_key, importance)
        
        return memory_key
    
    def remember_for_agent(self, 
                          target_agent_id: str, 
                          content_text: str,
                          memory_type: str = "shared",
                          importance: float = 0.5, 
                          tags: Optional[List[str]] = None) -> str:
        """Store memory specifically for another agent
        
        Args:
            target_agent_id: ID of the agent this memory is for
            content_text: The content to share
            memory_type: Type of memory ("shared", "insight", "fact", etc.)
            importance: Importance score (0.0 to 1.0)
            tags: Optional tags for better retrieval
            
        Returns:
            The key under which the memory was stored
        """
        memory_key = generate_memory_key(memory_type)
        
        content = MemoryContent(
            content=content_text,
            importance=importance,
            memory_type=memory_type,
            tags=tags or [],
            metadata={
                "source_agent_id": self.agent_id,
                "target_agent_id": target_agent_id,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Store in a shared scope that the target agent can access
        target_scope = f"workflow:{self.workflow_id}:agent:{target_agent_id}:shared"
        self.searchable_memory.store_content(memory_key, content, target_scope)
        
        logger.debug("Agent '%s' stored memory for agent '%s' with key '%s'", 
                    self.agent_id, target_agent_id, memory_key)
        
        return memory_key
    
    def search_memory(self, 
                     query: str, 
                     limit: int = 5, 
                     min_similarity: float = 0.5,
                     include_global: bool = True) -> List[Tuple[MemoryContent, float]]:
        """Search for content semantically similar to the query
        
        Args:
            query: The search query
            limit: Maximum number of results
            min_similarity: Minimum similarity score to include
            include_global: Whether to include global memories
            
        Returns:
            List of (content, similarity) tuples, sorted by similarity
        """
        # First search in agent's own scope
        results = self.searchable_memory.search(
            query=query, 
            requesting_scope=self.scope,
            limit=limit,
            min_similarity=min_similarity
        )
        
        # If including global and we haven't hit the limit, search global scope too
        if include_global and len(results) < limit:
            global_results = self.searchable_memory.search(
                query=query,
                requesting_scope="global",
                limit=limit - len(results),
                min_similarity=min_similarity
            )
            
            # Combine results
            all_results = results + global_results
            
            # Sort by similarity
            all_results.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to requested number
            results = all_results[:limit]
            
        logger.debug("Agent '%s' searched for '%s' and found %d results", 
                    self.agent_id, query, len(results))
            
        return results
    
    def get_relevant_context(self, query: str, limit: int = 5) -> str:
        """Get relevant context from memory as a formatted string
        
        Args:
            query: The context query
            limit: Maximum number of memories to include
            
        Returns:
            Formatted string with relevant memories
        """
        results = self.search_memory(query, limit=limit)
        
        if not results:
            return "No relevant context found in memory."
            
        # Format results
        context_parts = []
        for content, similarity in results:
            memory_type = content.memory_type.upper()
            importance = content.importance
            context_parts.append(f"[{memory_type}] (Relevance: {similarity:.2f}, Importance: {importance:.2f})")
            context_parts.append(content.content)
            context_parts.append("")  # Empty line between entries
            
        logger.debug("Agent '%s' retrieved %d relevant context items for query '%s'", 
                    self.agent_id, len(results), query)
            
        return "\n".join(context_parts) 