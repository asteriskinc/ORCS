# Migrating from Memory v1 to v2

This guide helps you migrate from the original ORCS memory system (v1) to the enhanced v2 memory system.

## Core Differences Between v1 and v2

### Simplified Interface

The v2 memory system has a cleaner, more consistent interface:

- **Abstract Base Class**: Clearly defined `MemorySystem` ABC with required methods
- **Simplified Retrieval**: Returns `None` for missing keys instead of raising exceptions
- **Delete Operations**: Added explicit `delete` method
- **Search Integration**: Search functionality is part of the base interface
- **Scope-Based Operations**: All operations include scope parameter (v1 mixed direct and scoped access)
- **Access Control**: Standard `has_access` method for scope permissions

### Agent-Facing Tools vs AgentContext

In v1, agents interact with memory through an `AgentContext` object. In v2, they use functional tools:

```python
# V1 approach
agent_context = memory_system.create_agent_context(agent_id, workflow_id)
agent_context.store("key", "value")
value = agent_context.retrieve("key")

# V2 approach
from orcs.memory.v2 import remember, recall
remember(context, "key", "value")
value = recall(context, "key")
```

## Migration Guides

### Basic Usage

```python
# V1 approach
from orcs.memory import MemorySystem
memory = MemorySystem()
memory.store("key", "value", "scope:123")
value = memory.retrieve("key", "scope:123")  # Raises KeyError if not found

# V2 approach
from orcs.memory.v2 import BasicMemorySystem
memory = BasicMemorySystem()
memory.store("key", "value", "scope:123")
value = memory.retrieve("key", "scope:123")  # Returns None if not found
```

### For Hierarchical Access Control

If you need v1's hierarchical access control (parent scopes can access child scopes):

```python
# V1 approach
memory = MemorySystem()
memory.store("key", "value", "workflow:123:task:456")
value = memory.retrieve("key", "workflow:123")  # Parent can access child data

# V2 approach with ScopedAccessMemorySystem
from orcs.memory.v2 import ScopedAccessMemorySystem
memory = ScopedAccessMemorySystem()
memory.store("key", "value", "workflow:123:task:456")
value = memory.retrieve("key", "workflow:123")  # Same hierarchical access

# For storage-backed hierarchical access
from orcs.memory.v2 import ScopedAccessStorageMemorySystem, FileStorageProvider
storage = FileStorageProvider("./memory")
memory = ScopedAccessStorageMemorySystem(storage_provider=storage)
```

### For Custom Access Control Rules

If you need custom access control rules:

```python
from orcs.memory.v2 import BasicMemorySystem

class CustomAccessMemorySystem(BasicMemorySystem):
    def has_access(self, requesting_scope: str, target_scope: str) -> bool:
        # Implement your custom access rules here
        # For example, add role-based access control
        if requesting_scope.startswith("admin:"):
            return True  # Admins can access anything
        return super().has_access(requesting_scope, target_scope)
```

### For Exception-Based Error Handling

If you prefer v1's exception-based approach:

```python
# V1 approach
try:
    value = memory.retrieve("key", "scope:123")
except KeyError:
    # Handle missing key
    
# V2 approach with utility
from orcs.memory.v2 import recall_with_error_handling
try:
    value = recall_with_error_handling("key", "scope:123", raise_if_missing=True)
except KeyError:
    # Handle missing key
```

### For Cross-Scope Key Listing

If you need v1's ability to list keys across multiple scopes:

```python
# V1 approach
keys = memory.list_keys("workflow:123*")  # Lists keys in workflow:123 and all sub-scopes

# V2 approach with utility
from orcs.memory.v2 import list_keys_by_scope_pattern
scope_keys = list_keys_by_scope_pattern("workflow:123*")
# Returns dict mapping scope names to lists of keys

# Using ScopedAccessMemorySystem directly (recommended)
memory = ScopedAccessMemorySystem()
keys = memory.list_keys("*", "workflow:123", include_child_scopes=True)
```

### For Complete Legacy Compatibility

If you need full backward compatibility:

```python
from orcs.memory.v2 import BasicMemorySystem, LegacyCompatibleMemorySystem

# Create v2 memory system
v2_memory = BasicMemorySystem()

# Wrap it in legacy compatibility layer
legacy_memory = LegacyCompatibleMemorySystem(v2_memory)

# Use with v1 API
legacy_memory.store("key", "value")
value = legacy_memory.retrieve("key", "requesting_scope")
```

## Feature Comparison

| Feature | v1 | v2 | Migration Notes |
|---------|----|----|----------------|
| Basic storage/retrieval | ✅ | ✅ | Direct equivalents |
| Hierarchical scopes | ✅ | ✅ | Use `ScopedAccessMemorySystem` |
| Exception-based errors | ✅ | ⚠️ | Use `recall_with_error_handling` |
| Cross-scope key listing | ✅ | ⚠️ | Use class with `include_child_scopes=True` |
| Delete operations | ❌ | ✅ | New in v2 |
| Built-in search | ❌ | ✅ | Part of base interface in v2 |
| Storage providers | ✅ | ✅ | Enhanced in v2 |
| Agent tools | ❌ | ✅ | New function-based interface |
| Workspaces | ❌ | ✅ | New in v2 |
| Access control | ✅ | ✅ | Standard `has_access` method |

## Setting as Default

To make v2 the default memory system, set it globally:

```python
from orcs.memory.v2 import set_default_memory_system, ScopedAccessMemorySystem

# Create your preferred memory system
memory = ScopedAccessMemorySystem()

# Set as global default
set_default_memory_system(memory)

# All memory tools will now use this instance
``` 