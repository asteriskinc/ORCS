"""Example utilities for working with structured memory content.

This module demonstrates how to create utility functions for working with
MemoryContent objects in a memory system implementation.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime
import uuid

from orcs.memory import (
    MemorySystem,
    MemoryContent, 
    RichMemoryContent, 
    EmbeddableMemoryContent
)

# Set up logger
logger = logging.getLogger("orcs.memory.examples.content_utilities")

def generate_memory_key(prefix: str = "") -> str:
    """Generate a unique key for memory content.
    
    Args:
        prefix: Optional prefix for the key
        
    Returns:
        A unique key string
    """
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}"
    else:
        return f"memory_{timestamp}_{unique_id}"

def store_memory_content(
    key: str,
    content: Union[MemoryContent, RichMemoryContent, EmbeddableMemoryContent],
    scope: str,
    memory_system: MemorySystem
) -> str:
    """Store memory content in the memory system
    
    Args:
        key: The key to store under
        content: The memory content to store
        scope: The scope to store in
        memory_system: Memory system to use
        
    Returns:
        The key that was used
    """
    memory_system.store(key, content, scope)
    logger.debug("Stored memory content at key '%s' in scope '%s'", key, scope)
    return key

def retrieve_memory_content(
    key: str,
    scope: str,
    memory_system: MemorySystem
) -> Optional[Union[MemoryContent, RichMemoryContent, EmbeddableMemoryContent]]:
    """Retrieve memory content from the memory system
    
    Args:
        key: The key to retrieve
        scope: The scope to retrieve from
        memory_system: Memory system to use
        
    Returns:
        The memory content, or None if not found or not a MemoryContent object
    """
    value = memory_system.retrieve(key, scope)
    
    # Check if it's a memory content object
    if value is None:
        return None
        
    if not isinstance(value, MemoryContent):
        logger.warning("Retrieved value is not a MemoryContent object")
        return None
        
    # Update access metadata if it's a RichMemoryContent
    if isinstance(value, RichMemoryContent):
        value.was_accessed()
        # Re-store to save the updated access metadata
        memory_system.store(key, value, scope)
        
    return value

def create_insight(content: str, importance: float = 0.7, tags: Optional[List[str]] = None) -> RichMemoryContent:
    """Create a memory content object for an insight
    
    Args:
        content: The insight text
        importance: Importance score (0.0 to 1.0)
        tags: Optional tags for the insight
        
    Returns:
        RichMemoryContent object
    """
    return RichMemoryContent(
        content=content,
        importance=importance,
        memory_type="insight",
        tags=tags or ["insight"]
    )

def create_fact(content: str, importance: float = 0.5, tags: Optional[List[str]] = None) -> RichMemoryContent:
    """Create a memory content object for a factual observation
    
    Args:
        content: The fact text
        importance: Importance score (0.0 to 1.0)
        tags: Optional tags for the fact
        
    Returns:
        RichMemoryContent object
    """
    return RichMemoryContent(
        content=content,
        importance=importance,
        memory_type="fact",
        tags=tags or ["fact"]
    )

def remember_content(
    content: str,
    content_type: str = "general",
    importance: float = 0.5,
    tags: Optional[List[str]] = None,
    key: Optional[str] = None,
    scope: str = "default",
    memory_system: MemorySystem = None
) -> str:
    """Store rich content in memory
    
    Args:
        content: The content to remember
        content_type: Type of content ("general", "insight", "fact", etc.)
        importance: Importance score (0.0 to 1.0)
        tags: Optional list of tags for retrieval
        key: Optional key to use (auto-generated if not provided)
        scope: Scope to store the memory in
        memory_system: Memory system to use
        
    Returns:
        The key that was used
    """
    if memory_system is None:
        raise ValueError("memory_system must be provided")
    
    # Create memory content object
    memory_content = RichMemoryContent(
        content=content,
        importance=importance,
        memory_type=content_type,
        tags=tags or [content_type]
    )
    
    # Generate key if not provided
    if key is None:
        key = generate_memory_key(content_type)
    
    # Store in memory
    store_memory_content(key, memory_content, scope, memory_system)
    
    logger.info("Stored %s with importance %.2f under key '%s'", 
               content_type, importance, key)
    return key 