from typing import Any, Dict, List, Tuple, Optional
import logging
import uuid
from datetime import datetime

from agents import function_tool

from .system import MemorySystem, BasicMemorySystem

# Set up logger
logger = logging.getLogger("orcs.memory.v2.tools")

# Default memory system instance for simple usage
default_memory_system = BasicMemorySystem()

def get_default_memory_system() -> MemorySystem:
    """Get the default memory system instance
    
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

def get_agent_scope(context) -> str:
    """Calculate the appropriate scope for the current agent
    
    Args:
        context: The agent context
        
    Returns:
        The appropriate scope string for the agent
    """
    agent_id = getattr(context, "agent_id", "unknown_agent")
    workflow_id = getattr(context, "workflow_id", "unknown_workflow")
    return f"workflow:{workflow_id}:agent:{agent_id}"

@function_tool
def remember(context, key: str, value: Any, scope: Optional[str] = None):
    """Store information in memory
    
    Args:
        context: The agent context
        key: The key to store the information under
        value: The information to remember
        scope: Optional memory scope (default is agent's scope)
    
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    memory_system.store(key, value, effective_scope)
    logger.info("Stored '%s' in scope '%s'", key, effective_scope)
    return f"Stored '{key}' in scope '{effective_scope}'"

@function_tool
def recall(context, key: str, scope: Optional[str] = None):
    """Retrieve information from memory
    
    Args:
        context: The agent context
        key: The key to recall information from
        scope: Optional memory scope (default is agent's scope)
        
    Returns:
        The recalled information
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    value = memory_system.retrieve(key, effective_scope)
    
    if value is not None:
        logger.info("Retrieved '%s' from scope '%s'", key, effective_scope)
        return value
    
    logger.info("No information found for '%s' in scope '%s'", key, effective_scope)
    return f"No information found for '{key}' in scope '{effective_scope}'"

@function_tool
def forget(context, key: str, scope: Optional[str] = None):
    """Remove information from memory
    
    Args:
        context: The agent context
        key: The key to forget
        scope: Optional memory scope (default is agent's scope)
        
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    result = memory_system.delete(key, effective_scope)
    
    if result:
        logger.info("Deleted '%s' from scope '%s'", key, effective_scope)
        return f"Deleted '{key}' from scope '{effective_scope}'"
    
    logger.info("No information found to delete for '%s' in scope '%s'", key, effective_scope)
    return f"No information found to delete for '{key}' in scope '{effective_scope}'"

@function_tool
def list_memories(context, pattern: str = "*", scope: Optional[str] = None):
    """List keys in memory matching a pattern
    
    Args:
        context: The agent context
        pattern: Optional pattern to filter keys (default is "*" for all keys)
        scope: Optional memory scope (default is agent's scope)
    
    Returns:
        List of matching keys
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    keys = memory_system.list_keys(pattern, effective_scope)
    
    if keys:
        logger.info("Found %d keys matching pattern '%s' in scope '%s'", 
                   len(keys), pattern, effective_scope)
        return keys
    
    logger.info("No keys found matching pattern '%s' in scope '%s'", pattern, effective_scope)
    return f"No keys found matching pattern '{pattern}' in scope '{effective_scope}'"

@function_tool
def search_memory(context, query: str, scope: Optional[str] = None, limit: int = 5):
    """Search for relevant information in memory
    
    Args:
        context: The agent context
        query: The search query
        scope: Optional memory scope to search in (default is agent's scope)
        limit: Maximum number of results to return
        
    Returns:
        List of matching memory items
    """
    memory_system = get_default_memory_system()
    effective_scope = scope or get_agent_scope(context)
    
    results = memory_system.search(query, effective_scope, limit)
    
    if not results:
        logger.info("No relevant information found for '%s' in scope '%s'", 
                   query, effective_scope)
        return f"No relevant information found for '{query}' in scope '{effective_scope}'"
        
    logger.info("Found %d matches for '%s' in scope '%s'", 
               len(results), query, effective_scope)
    
    formatted_results = []
    for key, value, score in results:
        formatted_results.append(f"Key: {key} (Relevance: {score:.2f})")
        formatted_results.append(f"{value}")
        formatted_results.append("")
    
    return "\n".join(formatted_results)

@function_tool
def create_workspace(context, workspace_id: Optional[str] = None):
    """Create a new workspace for collaboration
    
    Args:
        context: The agent context
        workspace_id: Optional ID for the workspace (auto-generated if not provided)
    
    Returns:
        Confirmation message with workspace ID
    """
    workspace_id = workspace_id or f"workspace_{uuid.uuid4().hex[:8]}"
    
    # We don't actually need to create anything - workspaces are virtual
    # and constructed on-demand when written to
    logger.info("Created workspace '%s'", workspace_id)
    return f"Created workspace '{workspace_id}'"

@function_tool
def workspace_write(context, workspace_id: str, key: str, value: Any):
    """Write to a collaborative workspace
    
    Args:
        context: The agent context
        workspace_id: The ID of the workspace
        key: The key to store the information under
        value: The information to store
    
    Returns:
        Confirmation message
    """
    memory_system = get_default_memory_system()
    scope = f"workspace:{workspace_id}"
    
    # Add metadata about who wrote it
    if isinstance(value, dict) and "content" in value:
        # If it's already in our content format, just add metadata
        value.setdefault("metadata", {})
        value["metadata"]["created_by"] = getattr(context, "agent_id", "unknown_agent")
        value["metadata"]["created_at"] = datetime.now().isoformat()
    else:
        # Otherwise, wrap in a dict with metadata
        value = {
            "content": value,
            "metadata": {
                "created_by": getattr(context, "agent_id", "unknown_agent"),
                "created_at": datetime.now().isoformat()
            }
        }
    
    memory_system.store(key, value, scope)
    logger.info("Stored '%s' in workspace '%s'", key, workspace_id)
    return f"Stored '{key}' in workspace '{workspace_id}'"

@function_tool
def workspace_read(context, workspace_id: str, key: str):
    """Read from a collaborative workspace
    
    Args:
        context: The agent context
        workspace_id: The ID of the workspace
        key: The key to retrieve
    
    Returns:
        The retrieved information, or a message if not found
    """
    memory_system = get_default_memory_system()
    scope = f"workspace:{workspace_id}"
    
    value = memory_system.retrieve(key, scope)
    
    if value is not None:
        # If it's in our content format, extract the actual content
        if isinstance(value, dict) and "content" in value:
            logger.info("Retrieved '%s' from workspace '%s'", key, workspace_id)
            return value["content"]
        
        logger.info("Retrieved '%s' from workspace '%s'", key, workspace_id)
        return value
    
    logger.info("No information found for '%s' in workspace '%s'", key, workspace_id)
    return f"No information found for '{key}' in workspace '{workspace_id}'"

@function_tool
def workspace_search(context, workspace_id: str, query: str, limit: int = 5):
    """Search in a collaborative workspace
    
    Args:
        context: The agent context
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
        logger.info("No relevant information found for '%s' in workspace '%s'", 
                   query, workspace_id)
        return f"No relevant information found for '{query}' in workspace '{workspace_id}'"
        
    logger.info("Found %d matches for '%s' in workspace '%s'", 
               len(results), query, workspace_id)
    
    formatted_results = []
    for key, value, score in results:
        # Extract content if it's in our content format
        if isinstance(value, dict) and "content" in value:
            display_value = value["content"]
            metadata = value.get("metadata", {})
            author = metadata.get("created_by", "unknown")
            timestamp = metadata.get("created_at", "unknown time")
            formatted_results.append(f"Key: {key} (Relevance: {score:.2f}, Author: {author}, Time: {timestamp})")
        else:
            display_value = value
            formatted_results.append(f"Key: {key} (Relevance: {score:.2f})")
            
        formatted_results.append(f"{display_value}")
        formatted_results.append("")
    
    return "\n".join(formatted_results)

@function_tool
def remember_fact(context, fact: str, importance: float = 0.5, tags: Optional[List[str]] = None):
    """Remember an important fact
    
    Stores a fact with metadata for better retrieval.
    
    Args:
        context: The agent context
        fact: The fact to remember
        importance: How important this fact is (0.0 to 1.0)
        tags: Optional list of tags for categorization
    
    Returns:
        Confirmation message with the generated key
    """
    memory_system = get_default_memory_system()
    scope = get_agent_scope(context)
    
    # Generate a unique key for this fact
    key = f"fact_{uuid.uuid4().hex[:8]}"
    
    # Create structured content
    content = {
        "content": fact,
        "type": "fact",
        "metadata": {
            "importance": importance,
            "tags": tags or [],
            "created_by": getattr(context, "agent_id", "unknown_agent"),
            "created_at": datetime.now().isoformat()
        }
    }
    
    memory_system.store(key, content, scope)
    logger.info("Stored fact with key '%s' in scope '%s'", key, scope)
    return f"Stored fact with key '{key}'"

@function_tool
def remember_insight(context, insight: str, importance: float = 0.5, tags: Optional[List[str]] = None):
    """Remember an important insight
    
    Stores an insight with metadata for better retrieval.
    
    Args:
        context: The agent context
        insight: The insight to remember
        importance: How important this insight is (0.0 to 1.0)
        tags: Optional list of tags for categorization
    
    Returns:
        Confirmation message with the generated key
    """
    memory_system = get_default_memory_system()
    scope = get_agent_scope(context)
    
    # Generate a unique key for this insight
    key = f"insight_{uuid.uuid4().hex[:8]}"
    
    # Create structured content
    content = {
        "content": insight,
        "type": "insight",
        "metadata": {
            "importance": importance,
            "tags": tags or [],
            "created_by": getattr(context, "agent_id", "unknown_agent"),
            "created_at": datetime.now().isoformat()
        }
    }
    
    memory_system.store(key, content, scope)
    logger.info("Stored insight with key '%s' in scope '%s'", key, scope)
    return f"Stored insight with key '{key}'"

def get_memory_tools():
    """Get the collection of memory tools for agents
    
    Returns:
        List of memory-related tools
    """
    return [
        remember,
        recall,
        forget,
        list_memories,
        search_memory,
        create_workspace,
        workspace_write,
        workspace_read,
        workspace_search,
        remember_fact,
        remember_insight
    ] 