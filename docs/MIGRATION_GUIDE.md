# Memory System Evolution and Migration Guide

> **Note**: This document is for historical reference. The v1 memory system has been fully replaced by the improved implementation described here.

## Core Differences

### Architectural Changes

- **Minimalist Core**: The memory system provides only core abstractions without utility functions or agent tools
- **Access Controls**: Access is now enforced by the memory system rather than being optional
- **Storage Abstraction**: The concept of a storage provider is now separate from the memory system
- **Simplified Core**: The core interfaces are smaller and more focused
- **Modular Design**: Features like rich memory content and embedding are now optional extensions

### API Changes

| Legacy API | Current API | Notes |
|-----------------|-----------------|-------|
| `MemorySystem.get(key, scope)` | `MemorySystem.retrieve(key, scope)` | Method renamed |
| `MemorySystem.set(key, value, scope)` | `MemorySystem.store(key, value, scope)` | Method renamed |
| `MemorySystem.remove(key, scope)` | `MemorySystem.delete(key, scope)` | Method renamed |
| No equivalent | `MemorySystem.has_access(scope, target_scope)` | New method for access control |
| `MemorySystem.get_keys(scope, pattern)` | `MemorySystem.list_keys(pattern, scope)` | Parameter order changed |
| Monolithic `MemoryContent` class | `RichMemoryContent` class | Similar functionality, improved design |
| Legacy `SearchableMemorySystem` | Improved `SearchableMemorySystem` | Core functionality preserved, improved design |

## Core Memory System

The memory system has a cleaner interface:

```python
# Basic example
from orcs.memory import BasicMemorySystem
memory = BasicMemorySystem()
memory.store("key", "value", "agent1")
value = memory.retrieve("key", "agent1")  # Returns None if not found
```

## Persistent Storage

For persistent storage with file-based backend:

```python
from orcs.memory import (
    ScopedAccessStorageMemorySystem,
    FileStorageProvider
)
storage = FileStorageProvider(storage_dir="./memory_data")
memory = ScopedAccessStorageMemorySystem(storage)
```

## Using Memory Content

For structured memory content:

```python
from orcs.memory import (
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

## Searchable Memory

For semantic search capabilities:

```python
from orcs.memory import (
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

## Creating Utility Functions

The memory system is deliberately minimalist, providing only core abstractions. You can create your own utility functions:

```python
# Example utility functions
from orcs.memory import RichMemoryContent
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

## Agent Tools Integration

For agent tool functions, you can create your own based on the core abstractions:

```python
# Create your own agent tools
from your_project.memory_tools import remember_insight, remember_fact
from orcs.memory import get_default_memory_system
```

## Advanced Topics

### Custom Embedding Providers

To implement a custom embedding provider:

```python
from orcs.memory import EmbeddingProvider
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

To implement a custom storage provider:

```python
from orcs.memory import StorageProvider
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