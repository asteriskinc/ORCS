# Migration Guide: Memory System v1 to v2

This guide provides instructions for migrating from Memory System v1 to v2. It covers the core differences, migration strategies, and specific guidance for porting features from v1 to v2.

## Core Differences

### Architectural Changes

- **Minimalist Core**: v2 provides only core abstractions without utility functions or agent tools
- **Access Controls**: Access is now enforced by the memory system rather than being optional
- **Storage Abstraction**: The concept of a storage provider is now separate from the memory system
- **Simplified Core**: The core interfaces are smaller and more focused
- **Modular Design**: Features like rich memory content and embedding are now optional extensions

### API Changes

| Memory System v1 | Memory System v2 | Notes |
|-----------------|-----------------|-------|
| `MemorySystem.get(key, scope)` | `MemorySystem.retrieve(key, scope)` | Method renamed |
| `MemorySystem.set(key, value, scope)` | `MemorySystem.store(key, value, scope)` | Method renamed |
| `MemorySystem.remove(key, scope)` | `MemorySystem.delete(key, scope)` | Method renamed |
| No equivalent | `MemorySystem.has_access(scope, target_scope)` | New method for access control |
| `MemorySystem.get_keys(scope, pattern)` | `MemorySystem.list_keys(pattern, scope)` | Parameter order changed |
| `MemoryContent` class | `RichMemoryContent` class | Similar functionality, improved design |
| `SearchableMemorySystem` | `SearchableMemorySystem` (new implementation) | Core functionality preserved, improved design |

## Migration Strategies

### Basic Memory Usage

For basic memory usage, the migration is straightforward:

```python
# v1
from orcs.memory import MemorySystem
memory = MemorySystem()
memory.set("key", "value", "agent1")
value = memory.get("key", "agent1")

# v2
from orcs.memory.v2 import BasicMemorySystem
memory = BasicMemorySystem()
memory.store("key", "value", "agent1")
value = memory.retrieve("key", "agent1")
```

### Persistent Storage

For persistent storage with file-based backend:

```python
# v1
from orcs.memory import MemorySystem
memory = MemorySystem(persistent=True, memory_dir="./memory_data")

# v2
from orcs.memory.v2 import (
    ScopedAccessStorageMemorySystem,
    FileStorageProvider
)
storage = FileStorageProvider(storage_dir="./memory_data")
memory = ScopedAccessStorageMemorySystem(storage)
```

### Using MemoryContent

For structured memory content:

```python
# v1
from orcs.memory import MemorySystem, MemoryContent
memory = MemorySystem()
content = MemoryContent(
    content="Important insight",
    importance=0.8,
    type="insight",
    tags=["important"]
)
memory.set("insight1", content, "agent1")

# v2
from orcs.memory.v2 import (
    BasicMemorySystem,
    RichMemoryContent
)
memory = BasicMemorySystem()
content = RichMemoryContent(
    content="Important insight",
    importance=0.8,
    memory_type="insight",
    tags=["important"]
)
memory.store("insight1", content, "agent1")
```

### Searchable Memory

For semantic search capabilities:

```python
# v1 
from orcs.memory import SearchableMemorySystem
memory = SearchableMemorySystem(
    embedding_provider="simple", 
    persistent=True
)
memory.set("insight1", "Python is useful", "agent1")
results = memory.search("programming language", "agent1")

# v2
from orcs.memory.v2 import (
    SearchableMemorySystem,
    SimpleEmbeddingProvider,
    FileStorageProvider,
    RichMemoryContent
)
storage = FileStorageProvider(storage_dir="./memory_data")
embedder = SimpleEmbeddingProvider()
memory = SearchableMemorySystem(
    storage_provider=storage,
    embedding_provider=embedder
)

memory.store(
    "insight1", 
    RichMemoryContent(
        content="Python is useful",
        memory_type="insight"
    ), 
    "agent1"
)
results = memory.search("programming language", "agent1")
```

### Creating Utility Functions

In v2, we recommend creating your own utility functions for common operations:

```python
# Example utility functions for v2
from orcs.memory.v2 import RichMemoryContent
import uuid
from datetime import datetime

def generate_memory_key(prefix: str = "") -> str:
    """Generate a unique key for memory content."""
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}"
    else:
        return f"memory_{timestamp}_{unique_id}"

def create_insight(content: str, importance: float = 0.7) -> RichMemoryContent:
    """Create a memory content object for an insight."""
    return RichMemoryContent(
        content=content,
        importance=importance,
        memory_type="insight",
        tags=["insight"]
    )

def remember_insight(memory, content: str, scope: str) -> str:
    """Store an insight in memory with automatic key generation."""
    key = generate_memory_key("insight")
    memory.store(key, create_insight(content), scope)
    return key
```

See the `examples/` directory for more extensive utility functions that can be adapted to your needs.

### Agent Tools Migration

For agent tool functions, you'll need to create your own based on the v2 core abstractions:

```python
# v1
from orcs.agent.memory_tools import remember_insight, remember_fact
from orcs.memory import get_default_memory_system

# v2
# Create your own agent tools (see examples directory)
from your_project.memory_tools import remember_insight, remember_fact
from orcs.memory.v2 import get_default_memory_system
```

## Compatibility Layer

For easier migration, v2 provides a compatibility layer that implements the v1 API:

```python
from orcs.memory.v2 import (
    LegacyCompatibleMemorySystem,
    FileStorageProvider
)

# Create a v2 memory system that has v1 API compatibility
storage = FileStorageProvider(storage_dir="./memory_data")
memory = LegacyCompatibleMemorySystem(storage)

# Can use with v1 method names
memory.set("key", "value", "agent1")
value = memory.get("key", "agent1")
```

## Feature Comparison

| Feature | v1 | v2 | Notes |
|---------|----|----|-------|
| Basic memory operations | ✅ | ✅ | Core functionality preserved |
| Persistent storage | ✅ | ✅ | Improved with storage provider abstraction |
| Access controls | ✅ | ✅ | Now integrated at the core level |
| Structured memory content | ✅ | ✅ | Improved with modular design |
| Embedding/semantic search | ✅ | ✅ | More flexible implementation |
| Agent memory tools | ✅ | ❌ | Now your responsibility to implement |
| Utility functions | ✅ | ❌ | Now your responsibility to implement |
| Workspace utilities | ✅ | ✅ | Preserved with the same functionality |

## Advanced Migration Topics

### Custom Embedding Providers

To implement a custom embedding provider in v2:

```python
from orcs.memory.v2 import EmbeddingProvider
import numpy as np

class MyEmbeddingProvider(EmbeddingProvider):
    def embed(self, text: str) -> np.ndarray:
        # Your embedding logic here
        return np.array([...])
    
    def get_dimension(self) -> int:
        return 768  # Example dimension
    
    def get_name(self) -> str:
        return "MyEmbeddingProvider"
```

### Custom Storage Providers

To implement a custom storage provider in v2:

```python
from orcs.memory.v2 import StorageProvider
from typing import Dict, Any, List, Optional

class MyStorageProvider(StorageProvider):
    def save(self, key: str, value: Any, scope: str) -> None:
        # Your save logic
        pass
    
    def load(self, key: str) -> Optional[Any]:
        # Your load logic
        pass
    
    def delete(self, key: str) -> None:
        # Your delete logic
        pass
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        # Your key listing logic
        pass
    
    def get_scope(self, key: str) -> Optional[str]:
        # Your scope retrieval logic
        pass
```

## Conclusion

Memory System v2 provides a more flexible, extensible, and secure foundation for agent memory, but with a more minimalist approach that gives you greater freedom to implement patterns that match your specific needs. By following this guide, you should be able to transition your code from v1 to v2. 