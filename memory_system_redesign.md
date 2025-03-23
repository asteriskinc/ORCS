# Memory System Redesign Proposal

## Current Issues

1. **Inconsistent Memory Infrastructure**: Currently, `MemorySystem` has a base interface, while `SearchableMemorySystem` extends it with additional methods. This creates API inconsistency when these systems need to be used interchangeably.

2. **Complex Interface**: The `SearchableMemorySystem` offers valuable features (embeddings, search, storage) but with a complex, inconsistent interface.

3. **Multiple AgentContext Implementations**: Having different `AgentContext` and `SearchableAgentContext` implementations creates confusion and requires type checking.

4. **Fragmented Memory Tools**: Multiple memory-related tools scattered across the codebase lead to redundancy and unclear responsibilities for LLM agents.

5. **Dictionary API vs MemoryContent**: Parallel APIs for storing primitive values and structured content create confusion.

6. **Provider Implementation**: Storage providers are only fully utilized in the SearchableMemorySystem.

7. **Hooks Implementation**: Current hooks in orcs/agent/infrastructure use the memory system for what is essentially telemetry.

8. **Limited Memory Timeframes**: No clear distinction between short-term (task-level), medium-term (workflow-level), and long-term (persistent) memory.

## Proposed Solution: Two-Layer Architecture

Our solution proposes a clear separation between:

1. **Core Memory Infrastructure (Layer 1)**: The underlying systems (MemorySystem) that provide storage, retrieval, and search capabilities.
2. **Agent-Facing Memory Tools (Layer 2)**: The agent-facing tools that provide a simple, consistent interface for LLM agents to interact with memory.

### Layer 1: Core Memory Infrastructure

#### 1.1. Memory System Abstract Base Class

```python
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional

class MemorySystem(ABC):
    """Unified memory system interface for underlying storage and retrieval"""
    
    @abstractmethod
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information"""
        pass
        
    @abstractmethod
    def retrieve(self, key: str, scope: str = "global") -> Any:
        """Retrieve data from specified scope"""
        pass
        
    @abstractmethod
    def delete(self, key: str, scope: str = "global") -> bool:
        """Delete data from specified scope"""
        pass
        
    @abstractmethod
    def list_keys(self, pattern: str = "*", scope: str = "global") -> List[str]:
        """List keys matching a pattern in specified scope"""
        pass
        
    @abstractmethod
    def search(self, query: str, scope: str = "global", limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Search for content semantically similar to the query
        Returns list of (key, content, score) tuples
        """
        pass
```

#### 1.2. Basic Memory System Implementation

```python
class BasicMemorySystem(MemorySystem):
    """Simple in-memory implementation of the memory system"""
    
    def __init__(self):
        self.data = {}  # Dict[scope][key] = value
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        if scope not in self.data:
            self.data[scope] = {}
        self.data[scope][key] = value
        
    def retrieve(self, key: str, scope: str = "global") -> Any:
        if scope not in self.data or key not in self.data[scope]:
            return None
        return self.data[scope][key]
        
    def delete(self, key: str, scope: str = "global") -> bool:
        if scope not in self.data or key not in self.data[scope]:
            return False
        del self.data[scope][key]
        return True
        
    def list_keys(self, pattern: str = "*", scope: str = "global") -> List[str]:
        if scope not in self.data:
            return []
        # Simple pattern matching - in a real implementation you'd use regex or glob
        if pattern == "*":
            return list(self.data[scope].keys())
        return [k for k in self.data[scope].keys() if pattern in k]
        
    def search(self, query: str, scope: str = "global", limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Simple implementation that just checks for keyword presence"""
        if scope not in self.data:
            return []
            
        results = []
        for key, value in self.data[scope].items():
            # Convert value to string if possible for simple text matching
            value_str = str(value) if not isinstance(value, (bytes, bytearray)) else ""
            if query.lower() in value_str.lower() or query.lower() in key.lower():
                # Simple relevance score - 1.0 if exact match, less otherwise
                score = 1.0 if query.lower() == value_str.lower() else 0.7
                results.append((key, value, score))
                
        return sorted(results, key=lambda x: x[2], reverse=True)[:limit]
```

#### 1.3. Storage Provider Interface (Optional Extension)

```python
class StorageProvider(ABC):
    """Abstract interface for memory storage providers"""
    
    @abstractmethod
    def save(self, key: str, value: Any, scope: str) -> None:
        """Save a value with its scope"""
        pass
    
    @abstractmethod
    def load(self, key: str, scope: str) -> Any:
        """Load a value by key from a scope"""
        pass
    
    @abstractmethod
    def delete(self, key: str, scope: str) -> bool:
        """Delete a key-value pair from a scope"""
        pass
    
    @abstractmethod
    def list_keys(self, pattern: str, scope: str) -> List[str]:
        """List keys matching a pattern in a scope"""
        pass
```

#### 1.4. Workspace Abstraction (Higher-level Feature)

```python
class Workspace:
    """Higher-level abstraction for collaborative memory spaces"""
    
    def __init__(self, memory_system: MemorySystem, workspace_id: str):
        self.memory = memory_system
        self.workspace_id = workspace_id
        self.scope = f"workspace:{workspace_id}"
        
    def write(self, key: str, value: Any) -> None:
        """Write data to workspace"""
        self.memory.store(key, value, scope=self.scope)
        
    def read(self, key: str) -> Any:
        """Read data from workspace"""
        return self.memory.retrieve(key, scope=self.scope)
        
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List all keys in this workspace matching pattern"""
        return self.memory.list_keys(pattern, scope=self.scope)
        
    def search(self, query: str, limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Search for content in this workspace"""
        return self.memory.search(query, scope=self.scope, limit=limit)
```

#### 1.5. Multi-Tenant Support (Optional)

```python
class MultiTenantMemorySystem(MemorySystem):
    """Memory system with tenant isolation"""
    
    def __init__(self, base_memory_system: MemorySystem):
        self.base_memory = base_memory_system
        
    def get_tenant_isolated_scope(self, tenant_id: str, scope: str) -> str:
        """Get tenant-isolated scope"""
        return f"tenant:{tenant_id}:{scope}"
        
    def store(self, key: str, value: Any, scope: str = "global", tenant_id: str = None) -> None:
        """Store with optional tenant isolation"""
        effective_scope = self.get_tenant_isolated_scope(tenant_id, scope) if tenant_id else scope
        self.base_memory.store(key, value, effective_scope)
        
    def retrieve(self, key: str, scope: str = "global", tenant_id: str = None) -> Any:
        """Retrieve with optional tenant isolation"""
        effective_scope = self.get_tenant_isolated_scope(tenant_id, scope) if tenant_id else scope
        return self.base_memory.retrieve(key, effective_scope)
        
    def delete(self, key: str, scope: str = "global", tenant_id: str = None) -> bool:
        """Delete with optional tenant isolation"""
        effective_scope = self.get_tenant_isolated_scope(tenant_id, scope) if tenant_id else scope
        return self.base_memory.delete(key, effective_scope)
        
    def list_keys(self, pattern: str = "*", scope: str = "global", tenant_id: str = None) -> List[str]:
        """List keys with optional tenant isolation"""
        effective_scope = self.get_tenant_isolated_scope(tenant_id, scope) if tenant_id else scope
        return self.base_memory.list_keys(pattern, effective_scope)
        
    def search(self, query: str, scope: str = "global", limit: int = 5, tenant_id: str = None) -> List[Tuple[str, Any, float]]:
        """Search with optional tenant isolation"""
        effective_scope = self.get_tenant_isolated_scope(tenant_id, scope) if tenant_id else scope
        return self.base_memory.search(query, effective_scope, limit)
```

### Layer 2: Agent-Facing Memory Tools

#### 2.1. Core Memory Tools for Agents

```python
from agents import function_tool
import uuid
from datetime import datetime

def get_default_memory_system() -> MemorySystem:
    """Get the default memory system instance
    
    This function should be implemented by the application to return
    the appropriate memory system instance. This allows for dependency
    injection without forcing a specific pattern.
    """
    # This is just an example - applications would implement this
    # based on their preferred dependency injection approach
    return BasicMemorySystem()  # Or however the application manages this

def get_agent_scope(context) -> str:
    """Calculate the appropriate scope for the current agent
    
    This is a helper function that applications can implement based on
    their own conventions for agent and workflow identification.
    """
    agent_id = getattr(context, "agent_id", "unknown_agent")
    workflow_id = getattr(context, "workflow_id", "unknown_workflow")
    return f"workflow:{workflow_id}:agent:{agent_id}"

@function_tool
def remember(context, key: str, value: Any, scope: str = None):
    """Store information in memory
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        key: The key to store the information under
        value: The information to remember
        scope: Optional memory scope (default is agent's scope)
    
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    memory_system.store(key, value, effective_scope)
    return f"Stored '{key}' in scope '{effective_scope}'"

@function_tool
def recall(context, key: str, scope: str = None):
    """Retrieve information from memory
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        key: The key to retrieve
        scope: Optional memory scope (default is agent's scope)
    
    Returns:
        The retrieved information, or a message if not found
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    value = memory_system.retrieve(key, effective_scope)
    
    if value is not None:
        return f"Found: {value}"
    return f"No information found for '{key}' in scope '{effective_scope}'"

@function_tool
def search_memory(context, query: str, scope: str = None, limit: int = 5):
    """Search for information in memory
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        query: What to search for
        scope: Optional memory scope (default is agent's scope)
        limit: Maximum number of results to return
    
    Returns:
        Formatted string with search results
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    results = memory_system.search(query, effective_scope, limit)
    
    if not results:
        return f"No relevant information found for '{query}' in scope '{effective_scope}'"
        
    formatted_results = []
    for key, value, score in results:
        formatted_results.append(f"Key: {key} (Relevance: {score:.2f})")
        formatted_results.append(f"{value}")
        formatted_results.append("")
    
    return "\n".join(formatted_results)

@function_tool
def create_workspace(context, workspace_id: str = None):
    """Create a new workspace for collaboration
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        workspace_id: Optional ID for the workspace (auto-generated if not provided)
    
    Returns:
        Confirmation message with workspace ID
    """
    workspace_id = workspace_id or f"workspace_{uuid.uuid4().hex[:8]}"
    
    # We don't actually need to create anything - workspaces are virtual
    # and constructed on-demand when written to
    
    return f"Created workspace '{workspace_id}'"

@function_tool
def workspace_write(context, workspace_id: str, key: str, value: Any):
    """Write to a collaborative workspace
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        workspace_id: The ID of the workspace
        key: The key to store the information under
        value: The information to store
    
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    scope = f"workspace:{workspace_id}"
    
    memory_system.store(key, value, scope)
    return f"Stored '{key}' in workspace '{workspace_id}'"

@function_tool
def workspace_read(context, workspace_id: str, key: str):
    """Read from a collaborative workspace
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        workspace_id: The ID of the workspace
        key: The key to retrieve
    
    Returns:
        The retrieved information, or a message if not found
    """
    memory_system = get_default_memory_system()
    scope = f"workspace:{workspace_id}"
    
    value = memory_system.retrieve(key, scope)
    
    if value is not None:
        return f"Found in workspace '{workspace_id}': {value}"
    return f"No information found for '{key}' in workspace '{workspace_id}'"

@function_tool
def workspace_search(context, workspace_id: str, query: str, limit: int = 5):
    """Search in a collaborative workspace
    
    This function can be used directly or as a foundation for building
    specialized memory tools.
    
    Args:
        context: The run context
        workspace_id: The ID of the workspace
        query: What to search for
        limit: Maximum number of results to return
    
    Returns:
        Formatted string with search results
    """
    memory_system = get_default_memory_system()
    scope = f"workspace:{workspace_id}"
    
    results = memory_system.search(query, scope, limit)
    
    if not results:
        return f"No relevant information found for '{query}' in workspace '{workspace_id}'"
        
    formatted_results = []
    for key, value, score in results:
        formatted_results.append(f"Key: {key} (Relevance: {score:.2f})")
        formatted_results.append(f"{value}")
        formatted_results.append("")
    
    return "\n".join(formatted_results)
```

#### 2.2. Memory Tool Collection

```python
def get_memory_tools():
    """Get the collection of memory tools for agents"""
    return [
        remember,
        recall,
        search_memory,
        create_workspace,
        workspace_write,
        workspace_read,
        workspace_search
    ]
```

#### 2.3. Building Specialized Tools

```python
@function_tool
def remember_user_preference(context, preference_name: str, preference_value: str):
    """Remember a user preference
    
    A specialized memory tool that stores user preferences
    
    Args:
        context: The run context
        preference_name: The name of the preference
        preference_value: The value of the preference
    
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    
    # Extract user ID from context (implementation depends on your context structure)
    user_id = getattr(context, "user_id", "user123")
    
    # Use specialized key format and scope
    key = f"preference:{preference_name}"
    scope = f"user:{user_id}"
    
    # Add metadata
    value = {
        "value": preference_value,
        "updated_at": datetime.now().isoformat(),
        "updated_by": getattr(context, "agent_id", "unknown_agent")
    }
    
    memory_system.store(key, value, scope)
    return f"Stored preference '{preference_name}' for user"
```

### Examples of Using Memory API

#### Basic Memory Usage

```python
# Using the memory system directly
memory_system = get_default_memory_system()
memory_system.store("key1", "value1", "scope:example")
value = memory_system.retrieve("key1", "scope:example")

# Using the agent tools
await remember(context, "user_preference", "dark_mode")
result = await recall(context, "user_preference")
results = await search_memory(context, "user preferences", limit=3)
```

#### Workspace Collaboration

```python
# Create a workspace
workspace_id = await create_workspace(context)

# Write to workspace
await workspace_write(context, workspace_id, "task_status", {"completed": 2, "remaining": 3})

# Read from workspace
status = await workspace_read(context, workspace_id, "task_status")

# Search workspace
results = await workspace_search(context, workspace_id, "status", limit=5)
```

#### Multi-Tenant Usage

```python
# In a multi-tenant application:
multi_tenant_memory = MultiTenantMemorySystem(BasicMemorySystem())

# Store tenant-specific data
multi_tenant_memory.store(
    key="config", 
    value={"theme": "dark", "notifications": True},
    scope="user_settings",
    tenant_id="tenant123"
)

# Retrieve tenant-specific data
config = multi_tenant_memory.retrieve(
    key="config",
    scope="user_settings",
    tenant_id="tenant123"
)
```

## Implementation Strategy

1. Implement the core MemorySystem interface with a simple in-memory implementation
2. Implement utility functions for scope generation and memory system access
3. Implement the base memory tools (remember, recall, search_memory)
4. Add workspace abstractions and related tools
5. Implement optional extensions (multi-tenant support) as needed
6. Create specialized tools for specific use cases

## Example: Building a SearchableMemorySystem

To illustrate the flexibility of the new design, here's how we could implement a feature-rich `SearchableMemorySystem` similar to our current implementation, but built on the new cleaner architecture:

```python
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from abc import ABC, abstractmethod
import uuid

# Embedding Provider interface
class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers"""
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for the provided text"""
        pass

# Simple implementation using a vector storage
class SearchableMemorySystem(MemorySystem):
    """Implementation with embedding-based search capabilities"""
    
    def __init__(self, embedding_provider: EmbeddingProvider, storage_provider: Optional[StorageProvider] = None):
        self.data = {}  # Dict[scope][key] = value
        self.embeddings = {}  # Dict[scope][key] = embedding_vector
        self.embedding_provider = embedding_provider
        self.storage_provider = storage_provider
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store with embedding generation"""
        # Initialize scope if needed
        if scope not in self.data:
            self.data[scope] = {}
            self.embeddings[scope] = {}
            
        # Store the value
        self.data[scope][key] = value
        
        # Generate and store embedding
        text_to_embed = self._get_text_for_embedding(value)
        if text_to_embed:
            self.embeddings[scope][key] = self.embedding_provider.get_embedding(text_to_embed)
            
        # Persist to storage provider if available
        if self.storage_provider:
            self.storage_provider.save(key, value, scope)
    
    def retrieve(self, key: str, scope: str = "global") -> Any:
        """Retrieve with fallback to storage provider"""
        # Check in-memory cache first
        if scope in self.data and key in self.data[scope]:
            return self.data[scope][key]
            
        # Fall back to storage provider if available
        if self.storage_provider:
            value = self.storage_provider.load(key, scope)
            if value is not None:
                # Cache the value for future retrieval
                if scope not in self.data:
                    self.data[scope] = {}
                self.data[scope][key] = value
                return value
                
        return None
        
    def delete(self, key: str, scope: str = "global") -> bool:
        """Delete with removal of embeddings"""
        success = False
        
        # Remove from in-memory storage
        if scope in self.data and key in self.data[scope]:
            del self.data[scope][key]
            success = True
            
        # Remove from embeddings
        if scope in self.embeddings and key in self.embeddings[scope]:
            del self.embeddings[scope][key]
            
        # Remove from storage provider if available
        if self.storage_provider:
            if self.storage_provider.delete(key, scope):
                success = True
                
        return success
        
    def list_keys(self, pattern: str = "*", scope: str = "global") -> List[str]:
        """List keys with provider fallback"""
        keys = []
        
        # Get keys from in-memory storage
        if scope in self.data:
            if pattern == "*":
                keys = list(self.data[scope].keys())
            else:
                keys = [k for k in self.data[scope].keys() if pattern in k]
        
        # Get additional keys from storage provider if available
        if self.storage_provider:
            provider_keys = self.storage_provider.list_keys(pattern, scope)
            # Combine and deduplicate keys
            keys = list(set(keys + provider_keys))
            
        return keys
        
    def search(self, query: str, scope: str = "global", limit: int = 5) -> List[Tuple[str, Any, float]]:
        """Semantic search using embeddings"""
        if not query or scope not in self.embeddings or not self.embeddings[scope]:
            return []
            
        # Generate embedding for the query
        query_embedding = self.embedding_provider.get_embedding(query)
        
        # Calculate similarity scores
        results = []
        for key, embedding in self.embeddings[scope].items():
            similarity = self._calculate_similarity(query_embedding, embedding)
            value = self.retrieve(key, scope)
            results.append((key, value, similarity))
            
        # Sort by similarity (highest first) and limit results
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]
    
    def _get_text_for_embedding(self, value: Any) -> Optional[str]:
        """Extract text to embed from a value"""
        if isinstance(value, str):
            return value
        elif isinstance(value, dict) and "content" in value:
            # Handle MemoryContent-like objects
            if isinstance(value["content"], str):
                return value["content"]
            else:
                return str(value["content"])
        else:
            try:
                return str(value)
            except:
                return None
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
```

### Using SearchableMemorySystem with OpenAI Embeddings

```python
from openai import OpenAI

# OpenAI Embedding Provider
class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str = "text-embedding-3-small"):
        self.client = OpenAI()
        self.model = model
    
    def get_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

# Optional Redis Storage Provider
class RedisStorageProvider(StorageProvider):
    def __init__(self, redis_client, prefix: str = "memory"):
        self.redis = redis_client
        self.prefix = prefix
    
    def _get_key(self, key: str, scope: str) -> str:
        return f"{self.prefix}:{scope}:{key}"
    
    def save(self, key: str, value: Any, scope: str) -> None:
        import json
        redis_key = self._get_key(key, scope)
        # Serialize the value
        serialized = json.dumps(value)
        self.redis.set(redis_key, serialized)
    
    def load(self, key: str, scope: str) -> Any:
        import json
        redis_key = self._get_key(key, scope)
        value = self.redis.get(redis_key)
        if value:
            return json.loads(value)
        return None
    
    def delete(self, key: str, scope: str) -> bool:
        redis_key = self._get_key(key, scope)
        return bool(self.redis.delete(redis_key))
    
    def list_keys(self, pattern: str, scope: str) -> List[str]:
        search_pattern = self._get_key(f"*{pattern}*", scope)
        # Remove prefix from returned keys
        prefix_len = len(f"{self.prefix}:{scope}:")
        keys = self.redis.keys(search_pattern)
        return [k[prefix_len:].decode('utf-8') if isinstance(k, bytes) else k[prefix_len:] for k in keys]

# Creating and using a SearchableMemorySystem
def create_searchable_memory_system():
    # Create the embedding provider
    embedding_provider = OpenAIEmbeddingProvider()
    
    # Optionally create a storage provider
    # redis_client = redis.Redis(host='localhost', port=6379, db=0)
    # storage_provider = RedisStorageProvider(redis_client)
    
    # Create the memory system
    memory_system = SearchableMemorySystem(
        embedding_provider=embedding_provider,
        # storage_provider=storage_provider  # Uncomment to use Redis storage
    )
    
    return memory_system

# Example usage
searchable_memory = create_searchable_memory_system()

# Store some memories
searchable_memory.store(
    key="fact_1",
    value="The Earth completes one full rotation around its axis every 24 hours.",
    scope="science"
)

searchable_memory.store(
    key="fact_2",
    value="Jupiter is the largest planet in our solar system.",
    scope="science"
)

searchable_memory.store(
    key="fact_3",
    value="The Milky Way galaxy contains billions of stars.",
    scope="science"
)

# Search for memories
results = searchable_memory.search("planets in solar system", scope="science")
for key, value, score in results:
    print(f"{key}: {value} (similarity: {score:.2f})")
```

This example demonstrates how the new architecture enables us to:
1. Recreate our current SearchableMemorySystem functionality
2. Integrate with external services (OpenAI)
3. Support persistent storage (Redis)
4. Maintain clean separation of concerns

All while providing a consistent interface that conforms to the core `MemorySystem` contract.

## Benefits

1. **Minimal Core API**: Clean, simple interface focused on the essentials (key, value, scope)
2. **Non-Opinionated Infrastructure**: Flexible approach that works with any dependency injection pattern
3. **Composable Architecture**: Base functionality with optional extensions for specialized needs
4. **Scope-Based Organization**: All operations use scopes as the fundamental organizing principle
5. **Simple Tool Building**: Easy to extend base tools for specialized requirements
6. **Multi-Tenant Ready**: Built-in support for tenant isolation
7. **Workspace Abstraction**: First-class support for collaboration spaces
8. **Progressive Complexity**: Simple for basic usage, powerful for advanced scenarios