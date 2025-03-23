"""ORCS Memory System

This module provides memory capabilities for ORCS agents and workflows,
enabling storage, retrieval, and semantic search of information.
"""

# Core memory system
from .system import (
    MemorySystem,
    BasicMemorySystem,
    ScopedAccessMemorySystem
)

# Storage providers
from .providers import (
    StorageProvider,
    InMemoryStorageProvider,
    FileStorageProvider
)

# Storage-backed memory systems
from .storage_memory import (
    StorageBackedMemorySystem,
    ScopedAccessStorageMemorySystem
)

# Memory content model
from .content import (
    MemoryContent,
    RichMemoryContent,
    EmbeddableMemoryContent
)

# Searchable memory
from .searchable import (
    EmbeddingProvider,
    SimpleEmbeddingProvider,
    SearchableMemorySystem,
    cosine_similarity
)

# Memory utility functions
from .tools import (
    get_default_memory_system,
    set_default_memory_system,
    remember,
    recall,
    recall_with_error_handling,
    forget,
    list_memories,
    list_keys_by_scope_pattern,
    create_workspace,
    workspace_write,
    workspace_read,
    workspace_search
)

__all__ = [
    # Core memory system
    'MemorySystem',
    'BasicMemorySystem',
    'ScopedAccessMemorySystem',
    
    # Storage providers
    'StorageProvider',
    'InMemoryStorageProvider',
    'FileStorageProvider',
    
    # Enhanced memory systems
    'StorageBackedMemorySystem',
    'ScopedAccessStorageMemorySystem',
    
    # Memory content model
    'MemoryContent',
    'RichMemoryContent',
    'EmbeddableMemoryContent',
    
    # Searchable memory
    'EmbeddingProvider',
    'SimpleEmbeddingProvider',
    'SearchableMemorySystem',
    'cosine_similarity',
    
    # Memory utility functions
    'get_default_memory_system',
    'set_default_memory_system',
    
    # Basic memory functions
    'remember',
    'recall',
    'recall_with_error_handling',
    'forget',
    'list_memories',
    'list_keys_by_scope_pattern',
    'create_workspace',
    'workspace_write',
    'workspace_read',
    'workspace_search'
]
