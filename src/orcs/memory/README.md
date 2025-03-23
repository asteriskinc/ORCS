# Memory System v2

## Overview

The Memory System v2 provides a flexible, extensible, and secure approach to memory management for ORCS agents. It offers hierarchical access controls, storage provider abstraction, and advanced memory features like rich content and semantic search.

## Core Design Principles

1. **Simplicity**: The core interfaces and abstractions are kept minimal.
2. **Extensibility**: The system is designed to be extended with additional functionality.
3. **Non-opinionated**: The system avoids enforcing specific implementation choices, letting you integrate it in your own way.
4. **Secure by default**: Access controls are integrated at the core level.

## Main Components

### Core Memory System

The foundation of the memory system:

- `MemorySystem`: The base interface for all memory systems
- `BasicMemorySystem`: A simple in-memory implementation
- `ScopedAccessMemorySystem`: Adds hierarchical access controls

### Storage Providers

Abstractions for different storage backends:

- `StorageProvider`: Base interface for storage providers
- `InMemoryStorageProvider`: Memory-only storage provider
- `FileStorageProvider`: File-based storage provider

### Storage-Backed Memory Systems

Combines memory systems with storage providers:

- `StorageBackedMemorySystem`: Basic persistent memory system
- `ScopedAccessStorageMemorySystem`: Adds hierarchical access controls to persistent storage

### Rich Memory Content

Structured content models with various capabilities:

- `MemoryContent`: Base class for structured memory content
- `RichMemoryContent`: Adds importance, tagging, and access tracking
- `EmbeddableMemoryContent`: Adds embedding support for semantic search

### Searchable Memory

Semantic search capabilities:

- `EmbeddingProvider`: Interface for embedding generators
- `SimpleEmbeddingProvider`: Basic embedding provider for testing
- `SearchableMemorySystem`: Memory system with semantic search capabilities

## Usage Examples

### Basic Usage

```python
from orcs.memory.v2 import BasicMemorySystem

# Create a memory system
memory = BasicMemorySystem()

# Store and retrieve data
memory.store("greeting", "Hello, world!", "agent1")
message = memory.retrieve("greeting", "agent1")
print(message)  # "Hello, world!"
```

### Using Rich Memory Content

```python
from orcs.memory.v2 import BasicMemorySystem, RichMemoryContent

# Create a memory system
memory = BasicMemorySystem()

# Create rich memory content
insight = RichMemoryContent(
    content="AI models work best with clear instructions",
    importance=0.8,
    memory_type="insight", 
    tags=["ai", "best_practices"]
)

# Store and retrieve
memory.store("key1", insight, "agent1")
retrieved = memory.retrieve("key1", "agent1")

# Access properties
print(retrieved.content)
print(retrieved.importance)
print(retrieved.tags)
```

### Using Searchable Memory

```python
from orcs.memory.v2 import (
    SearchableMemorySystem,
    SimpleEmbeddingProvider,
    InMemoryStorageProvider,
    RichMemoryContent
)

# Create providers and memory system
embedding_provider = SimpleEmbeddingProvider()
storage_provider = InMemoryStorageProvider()
memory = SearchableMemorySystem(
    storage_provider=storage_provider,
    embedding_provider=embedding_provider
)

# Store some memory items
memory.store(
    "insight1",
    RichMemoryContent(
        content="Python is a versatile programming language",
        importance=0.8,
        memory_type="insight",
        tags=["python", "programming"]
    ),
    "agent1"
)

memory.store(
    "insight2",
    RichMemoryContent(
        content="Neural networks require large datasets",
        importance=0.7,
        memory_type="insight",
        tags=["ai", "machine_learning"]
    ),
    "agent1"
)

# Search for related items
results = memory.search(
    query="programming languages", 
    scope="agent1",
    limit=5,
    threshold=0.5
)

# Display results
for key, value, score in results:
    print(f"{key}: {value.content} (score: {score:.2f})")
```

## Extending the Memory System

The Memory System v2 is deliberately minimalist, providing only core abstractions without additional utility functions or agent-specific tools. This design allows you to extend the system in ways that fit your specific needs.

For examples of how to build upon these core abstractions, see the `examples/` directory, which includes:

- Utility functions for working with memory content
- Helper functions for semantic search
- Templates for creating agent-specific tools

### Creating Custom Embedding Providers

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

### Creating Custom Storage Providers

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

## Migration from v1

For information on migrating from Memory System v1, please see the [Migration Guide](MIGRATION_GUIDE.md). 