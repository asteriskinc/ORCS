"""ORCS Memory System

This module provides memory capabilities for ORCS agents and workflows,
enabling storage, retrieval, and semantic search of information.
"""

# Base memory system
from .system import MemorySystem, AgentContext

# Enhanced memory with search capabilities
from .searchable import SearchableMemorySystem, SearchableAgentContext

# Rich memory content model
from .content import MemoryContent, generate_memory_key

# Storage providers
from .providers import (
    MemoryStorageProvider,
    InMemoryStorageProvider,
    FileStorageProvider
)

# Embedding providers
from .embeddings import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    cosine_similarity,
    create_default_embedding_provider
)

# Check if optional providers are available
from .embeddings import OPENAI_AVAILABLE, SENTENCE_TRANSFORMERS_AVAILABLE

# Conditionally expose optional providers
if OPENAI_AVAILABLE:
    from .embeddings import OpenAIEmbeddingProvider

if SENTENCE_TRANSFORMERS_AVAILABLE:
    from .embeddings import HuggingFaceEmbeddingProvider

# Re-export v2 components as "memory"
from .v2 import (
    get_default_memory_system,
    set_default_memory_system,
    get_memory_tools
)

# Explicitly export the old components for backward compatibility
__all__ = [
    # Legacy components (v1)
    'MemorySystem',
    'AgentContext',
    'SearchableMemorySystem', 
    'SearchableAgentContext',
    'MemoryContent',
    'generate_memory_key',
    
    # New components (v2)
    'get_default_memory_system',
    'set_default_memory_system',
    'get_memory_tools',
    
    # Storage providers
    "MemoryStorageProvider",
    "InMemoryStorageProvider",
    "FileStorageProvider",
    
    # Embedding providers
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "cosine_similarity",
    "create_default_embedding_provider",
    
    # Feature flags
    "OPENAI_AVAILABLE",
    "SENTENCE_TRANSFORMERS_AVAILABLE"
]

# Conditionally add optional providers to __all__
if OPENAI_AVAILABLE:
    __all__.append("OpenAIEmbeddingProvider")

if SENTENCE_TRANSFORMERS_AVAILABLE:
    __all__.append("HuggingFaceEmbeddingProvider")
