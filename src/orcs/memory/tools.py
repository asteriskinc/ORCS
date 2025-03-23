"""Utility functions for memory management.

This module provides convenience functions for common memory operations
that build on top of the core memory system abstractions.
"""

from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import logging
import os
import json

from .system import MemorySystem, BasicMemorySystem
from .storage_memory import StorageBackedMemorySystem

# Set up logger
logger = logging.getLogger("orcs.memory.tools")

# Default memory system instance for simple usage
default_memory_system = BasicMemorySystem()

def get_default_memory_system() -> MemorySystem:
    """Get the default memory system instance
    
    This is a convenience function for code that wants to work with
    the default memory system instance
    
    Returns:
        The default memory system instance
    """
    global default_memory_system
    return default_memory_system

def set_default_memory_system(memory_system: MemorySystem) -> None:
    """Set the default memory system instance
    
    Args:
        memory_system: The memory system to use as default
    """
    global default_memory_system
    default_memory_system = memory_system
    logger.info("Default memory system set to %s", memory_system.__class__.__name__)

# Helper function for extracting scope from context
def _get_scope_from_context(context, scope: Optional[str] = None) -> str:
    """Extract scope from context or use provided scope
    
    Args:
        context: Agent context object
        scope: Optional explicit scope
        
    Returns:
        Effective scope to use
    """
    if scope is not None:
        return scope
    
    # Try to get scope from context
    if hasattr(context, "agent_id"):
        return context.agent_id
    elif hasattr(context, "scope"):
        return context.scope
    
    # Fallback
    return "default"

def remember(context, key: str, value: Any, scope: Optional[str] = None) -> str:
    """Store information in memory
    
    Args:
        context: Agent context
        key: Key to store under
        value: Value to store
        scope: Optional memory scope (default is agent's scope)
        
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    effective_scope = _get_scope_from_context(context, scope)
    
    memory_system.store(key, value, effective_scope)
    
    return f"Stored '{key}' in memory"

def recall(context, key: str, scope: Optional[str] = None) -> Any:
    """Retrieve information from memory
    
    Args:
        context: Agent context
        key: Key to retrieve
        scope: Optional memory scope (default is agent's scope)
        
    Returns:
        The stored value or None if not found
    """
    memory_system = get_default_memory_system()
    effective_scope = _get_scope_from_context(context, scope)
    
    value = memory_system.retrieve(key, effective_scope)
    return value

def recall_with_error_handling(key: str, scope: str, memory_system: Optional[MemorySystem] = None,
                              error_handler: Optional[Callable[[Exception], Any]] = None) -> Any:
    """Retrieve information from memory with custom error handling
    
    This utility function provides v1-style error handling on top of v2's memory system.
    
    Args:
        key: Key to retrieve
        scope: Scope to retrieve from
        memory_system: The memory system to use (default: global default)
        error_handler: Optional function to handle errors
        
    Returns:
        The retrieved value or None/error handler result if not found
    """
    try:
        memory = memory_system or get_default_memory_system()
        value = memory.retrieve(key, scope)
        return value
    except Exception as e:
        if error_handler:
            return error_handler(e)
        return None

def forget(context, key: str, scope: Optional[str] = None) -> bool:
    """Remove information from memory
    
    Args:
        context: Agent context
        key: Key to remove
        scope: Optional memory scope (default is agent's scope)
        
    Returns:
        True if the key was found and removed
    """
    memory_system = get_default_memory_system()
    effective_scope = _get_scope_from_context(context, scope)
    
    result = memory_system.delete(key, effective_scope)
    return result

def list_memories(context, pattern: str = "*", scope: Optional[str] = None) -> List[str]:
    """List keys in memory matching a pattern
    
    Args:
        context: Agent context
        pattern: Glob pattern to match keys
        scope: Optional memory scope (default is agent's scope)
        
    Returns:
        List of matching keys
    """
    memory_system = get_default_memory_system()
    effective_scope = _get_scope_from_context(context, scope)
    
    keys = memory_system.list_keys(pattern, effective_scope)
    return keys

# Searchable memory functions
def search_memory(context, query: str, scope: Optional[str] = None, limit: int = 5):
    """Search for relevant information in memory
    
    Args:
        context: Agent context
        query: Search query
        scope: Optional memory scope to search in (default is agent's scope)
        limit: Maximum number of results to return
        
    Returns:
        List of matching memory items
    """
    memory_system = get_default_memory_system()
    effective_scope = _get_scope_from_context(context, scope)
    
    results = memory_system.search(query, effective_scope, limit)
    
    if results:
        formatted_results = []
        for key, value, score in results:
            # Format the result depending on the type
            if hasattr(value, "content"):
                formatted_results.append(f"{value.content} (score: {score:.2f}, key: {key})")
            else:
                formatted_results.append(f"{str(value)} (score: {score:.2f}, key: {key})")
        
        return "\n".join(formatted_results)
    else:
        return "No relevant information found in memory."

# Workspace utilities for file-based memory
def create_workspace(workspace_name: str, context=None) -> str:
    """Create a workspace directory for storing files
    
    Args:
        workspace_name: Name of the workspace
        context: Optional context for scoping
        
    Returns:
        Path to the workspace directory
    """
    memory_system = get_default_memory_system()
    
    # Only works with storage-backed memory systems
    if not isinstance(memory_system, StorageBackedMemorySystem):
        logger.warning("Workspace operations require a StorageBackedMemorySystem")
        raise TypeError("The default memory system does not support workspace operations")
    
    # Get the storage provider's directory
    storage_provider = memory_system.storage_provider
    if not hasattr(storage_provider, 'storage_dir'):
        logger.warning("Storage provider does not have a storage_dir attribute")
        raise AttributeError("The storage provider does not support workspace operations")
        
    # Create the workspace directory
    workspace_dir = os.path.join(storage_provider.storage_dir, "workspaces", workspace_name)
    os.makedirs(workspace_dir, exist_ok=True)
    
    logger.info("Created workspace '%s' at '%s'", workspace_name, workspace_dir)
    return workspace_dir

def workspace_write(workspace_name: str, filename: str, content: str, context=None) -> str:
    """Write content to a file in a workspace
    
    Args:
        workspace_name: Name of the workspace
        filename: Name of the file to write
        content: Content to write to the file
        context: Optional context
        
    Returns:
        Path to the written file
    """
    workspace_dir = create_workspace(workspace_name, context)
    
    # Sanitize the filename
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(workspace_dir, clean_filename)
    
    # Write the content
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info("Wrote %d bytes to '%s'", len(content), file_path)
    return file_path

def workspace_read(workspace_name: str, filename: str, context=None) -> str:
    """Read content from a file in a workspace
    
    Args:
        workspace_name: Name of the workspace
        filename: Name of the file to read
        context: Optional context
        
    Returns:
        Content of the file
    """
    memory_system = get_default_memory_system()
    
    # Only works with storage-backed memory systems
    if not isinstance(memory_system, StorageBackedMemorySystem):
        logger.warning("Workspace operations require a StorageBackedMemorySystem")
        raise TypeError("The default memory system does not support workspace operations")
    
    # Get the storage provider's directory
    storage_provider = memory_system.storage_provider
    if not hasattr(storage_provider, 'storage_dir'):
        logger.warning("Storage provider does not have a storage_dir attribute")
        raise AttributeError("The storage provider does not support workspace operations")
    
    # Get the workspace directory
    workspace_dir = os.path.join(storage_provider.storage_dir, "workspaces", workspace_name)
    
    # Sanitize the filename
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(workspace_dir, clean_filename)
    
    # Read the content
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in workspace '{workspace_name}'")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    logger.info("Read %d bytes from '%s'", len(content), file_path)
    return content

def workspace_search(workspace_name: str, query: str, context=None) -> List[Tuple[str, str]]:
    """Search for files in a workspace matching a query
    
    Args:
        workspace_name: Name of the workspace
        query: Search query
        context: Optional context
        
    Returns:
        List of (filename, content) tuples matching the query
    """
    memory_system = get_default_memory_system()
    
    # Only works with storage-backed memory systems
    if not isinstance(memory_system, StorageBackedMemorySystem):
        logger.warning("Workspace operations require a StorageBackedMemorySystem")
        raise TypeError("The default memory system does not support workspace operations")
    
    # Get the storage provider's directory
    storage_provider = memory_system.storage_provider
    if not hasattr(storage_provider, 'storage_dir'):
        logger.warning("Storage provider does not have a storage_dir attribute")
        raise AttributeError("The storage provider does not support workspace operations")
    
    # Get the workspace directory
    workspace_dir = os.path.join(storage_provider.storage_dir, "workspaces", workspace_name)
    
    if not os.path.exists(workspace_dir):
        raise FileNotFoundError(f"Workspace '{workspace_name}' not found")
    
    # Simple substring search for now
    results = []
    for filename in os.listdir(workspace_dir):
        if os.path.isfile(os.path.join(workspace_dir, filename)):
            try:
                with open(os.path.join(workspace_dir, filename), 'r') as f:
                    content = f.read()
                
                if query.lower() in content.lower():
                    results.append((filename, content))
            except Exception as e:
                logger.warning("Error reading file '%s': %s", filename, str(e))
    
    logger.info("Found %d files matching query '%s' in workspace '%s'", 
               len(results), query, workspace_name)
    return results

def list_keys_by_scope_pattern(scope_pattern: str = "*", memory_system: Optional[MemorySystem] = None) -> Dict[str, List[str]]:
    """List keys grouped by scope matching a pattern
    
    Args:
        scope_pattern: Glob pattern to match scopes
        memory_system: The memory system to use (default: global default)
        
    Returns:
        Dictionary mapping scope names to lists of keys
    """
    import fnmatch
    
    memory = memory_system or get_default_memory_system()
    
    # Only works with BasicMemorySystem or subclasses
    if not isinstance(memory, BasicMemorySystem):
        logger.warning("list_keys_by_scope_pattern only works with BasicMemorySystem")
        return {}
    
    result = {}
    
    # Get all scopes from the memory system
    all_scopes = list(memory.data.keys())
    
    # Filter by pattern
    matching_scopes = [scope for scope in all_scopes if fnmatch.fnmatch(scope, scope_pattern)]
    
    for scope in matching_scopes:
        keys = memory.list_keys("*", scope)
        result[scope] = keys
    
    return result 