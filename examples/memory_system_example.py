#!/usr/bin/env python
"""
Memory System Example

This example demonstrates the usage of the ORCS memory system,
showing different memory system implementations, content types,
and search capabilities.
"""

import os
import sys
import numpy as np
from typing import Any, Optional
from tempfile import TemporaryDirectory

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from orcs.memory import (
    # Core classes
    BasicMemorySystem,
    ScopedAccessMemorySystem,
    
    # Storage providers
    FileStorageProvider,
    
    # Storage-backed systems
    ScopedAccessStorageMemorySystem,
    
    # Content model
    MemoryContent,
    RichMemoryContent,
    EmbeddableMemoryContent,
    
    # Search capabilities
    SearchableMemorySystem,
    SimpleEmbeddingProvider,
    
    # Utility functions
    InMemoryStorageProvider
)

# Global variable to store the default memory system
_default_memory_system = None

def set_default_memory_system(memory_system):
    """Set the default memory system to use with utility functions.
    
    Args:
        memory_system: The memory system to set as default
    """
    global _default_memory_system
    _default_memory_system = memory_system

def get_default_memory_system():
    """Get the default memory system.
    
    Returns:
        The default memory system
    """
    global _default_memory_system
    if _default_memory_system is None:
        _default_memory_system = BasicMemorySystem()
    return _default_memory_system

def remember(context, key: str, value: Any, scope: Optional[str] = None, memory_system = None):
    """Store information in memory.
    
    Args:
        context: Agent context
        key: Key to store under
        value: Value to store
        scope: Optional memory scope (default is agent's scope)
        memory_system: Optional memory system to use (default: example system)
    """
    memory = memory_system or get_default_memory_system()
    effective_scope = context.agent_id if hasattr(context, "agent_id") else "default"
    if scope:
        effective_scope = scope
    
    memory.store(key, value, effective_scope)

def recall(context, key: str, scope: Optional[str] = None, memory_system = None):
    """Retrieve information from memory.
    
    Args:
        context: Agent context
        key: Key to retrieve
        scope: Optional memory scope (default is agent's scope)
        memory_system: Optional memory system to use (default: example system)
        
    Returns:
        The stored value or None if not found
    """
    memory = memory_system or get_default_memory_system()
    effective_scope = context.agent_id if hasattr(context, "agent_id") else "default"
    if scope:
        effective_scope = scope
    
    return memory.retrieve(key, effective_scope)

def demo_basic_memory():
    """Demonstrate basic memory operations"""
    print("\n=== Basic Memory Operations ===")
    
    # Create a basic memory system
    memory = BasicMemorySystem()
    
    # Store and retrieve simple values
    memory.store("greeting", "Hello, world!", "demo")
    value = memory.retrieve("greeting", "demo")
    print(f"Retrieved: {value}")
    
    # Test access controls
    memory.store("secret", "This is confidential", "agent1")
    
    # Different agent can't access
    value = memory.retrieve("secret", "agent2")
    print(f"Agent2 accessing Agent1's secret: {value}")
    
    # Parent scope can access child scope
    memory.store("child_data", "Child data", "parent:child")
    value = memory.retrieve("child_data", "parent")
    print(f"Parent accessing child data: {value}")

def demo_rich_content():
    """Demonstrate rich content with metadata"""
    print("\n=== Rich Memory Content ===")
    
    memory = BasicMemorySystem()
    
    # Create rich content
    content = RichMemoryContent(
        content="This is an important insight",
        importance=0.8,
        memory_type="insight",
        tags=["important", "demo"]
    )
    
    # Store and retrieve
    memory.store("insight1", content, "demo")
    retrieved = memory.retrieve("insight1", "demo")
    
    print(f"Content: {retrieved.content}")
    print(f"Importance: {retrieved.importance}")
    print(f"Type: {retrieved.memory_type}")
    print(f"Tags: {retrieved.tags}")
    
    # Tracking access
    retrieved.was_accessed()
    print(f"Access count: {retrieved.get_metadata('access_count')}")
    print(f"Last access: {retrieved.get_metadata('last_access_time')}")

def demo_persistent_storage():
    """Demonstrate persistent storage with file system"""
    print("\n=== Persistent Storage ===")
    
    # Create a temporary directory for storage
    with TemporaryDirectory() as temp_dir:
        print(f"Storage directory: {temp_dir}")
        
        # Create a file storage provider
        storage = FileStorageProvider(storage_dir=temp_dir)
        
        # Create a storage-backed memory system
        memory = ScopedAccessStorageMemorySystem(storage_provider=storage)
        
        # Store data
        memory.store("persistent", "This will be saved to disk", "demo")
        print("Data stored to disk")
        
        # Retrieve data
        value = memory.retrieve("persistent", "demo")
        print(f"Retrieved from disk: {value}")
        
        # Verify it was actually saved to disk
        files = os.listdir(temp_dir)
        print(f"Files in storage directory: {files}")

def demo_semantic_search():
    """Demonstrate semantic search capabilities"""
    print("\n=== Semantic Search ===")
    
    # Create a simple embedding provider
    embedder = SimpleEmbeddingProvider()
    
    # Create an in-memory storage provider
    storage = InMemoryStorageProvider()
    
    # Create a searchable memory system
    memory = SearchableMemorySystem(
        storage_provider=storage, 
        embedding_provider=embedder,
        default_access_scope="demo"
    )
    
    # Store embeddable content
    fact1 = EmbeddableMemoryContent(
        content="Python is a programming language created in the early 1990s.",
        memory_type="fact"
    )
    memory.store("fact1", fact1, "demo")
    print(f"Fact 1: Embedding present? {fact1.embedding is not None}")
    try:
        if fact1.embedding is not None:
            print(f"Embedding shape: {fact1.embedding.shape}")
    except AttributeError:
        print("Error accessing embedding attribute")
    
    # Explicitly embed content before storing
    fact2_text = "The capital of France is Paris."
    fact2 = EmbeddableMemoryContent(
        content=fact2_text,
        memory_type="fact"
    )
    fact2.embedding = embedder.embed(fact2_text)
    memory.store("fact2", fact2, "demo")
    
    fact3_text = "Machine learning is a subset of artificial intelligence."
    fact3 = EmbeddableMemoryContent(
        content=fact3_text,
        memory_type="fact"
    )
    fact3.embedding = embedder.embed(fact3_text)
    memory.store("fact3", fact3, "demo")
    
    # Search for related content
    print("Searching for 'programming':")
    results = memory.search("programming", "demo", threshold=0.1)
    for key, value, score in results:
        print(f"- {value.content} (score: {score:.3f})")
    
    print("\nSearching for 'artificial intelligence':")
    results = memory.search("artificial intelligence", "demo", threshold=0.1)
    for key, value, score in results:
        print(f"- {value.content} (score: {score:.3f})")
        
    # Print all stored keys to confirm content was stored
    print("\nStored keys:")
    keys = memory.list_keys("*", "demo")
    for key in keys:
        print(f"- {key}")

def demo_utility_functions():
    """Demonstrate utility functions for agent context"""
    print("\n=== Utility Functions ===")
    
    # Create a memory system and set as default
    memory = BasicMemorySystem()
    set_default_memory_system(memory)
    
    # Create a mock agent context
    class MockAgentContext:
        agent_id = "agent123"
        
    context = MockAgentContext()
    
    # Use utility functions
    remember(context, "agent_data", "This is some agent data")
    print("Stored data using remember()")
    
    data = recall(context, "agent_data")
    print(f"Retrieved data using recall(): {data}")
    
    # Search for data - direct method
    print("Search results:")
    if hasattr(memory, 'search'):
        results = memory.search("agent", "agent123")
        for key, value, score in results:
            print(f"- {value} (score: {score:.3f})")
    else:
        print("Search functionality not available on this memory system")

if __name__ == "__main__":
    demo_basic_memory()
    demo_rich_content()
    demo_persistent_storage()
    demo_semantic_search()
    demo_utility_functions()
    
    print("\n=== All Memory System Demos Completed Successfully ===")
    print("The new memory system provides core abstractions for:")
    print("- Basic memory operations with rich content and metadata")
    print("- Hierarchical access control with scoped memory")
    print("- Persistent storage with various storage providers")
    print("- Semantic search capabilities with custom embedding providers")
    print("- Utility functions for agent integration") 