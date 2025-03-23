"""
Example of building agent tools using the memory system v2.

This file shows how to create agent-specific tools for memory operations
using the core abstractions provided by the memory system.
"""

from typing import Any, List, Optional
import logging
from functools import wraps

# This would be your agent framework's tool decorator
def function_tool(func):
    """Example decorator for agent tools."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

# Import memory system components
from orcs.memory import (
    MemorySystem,
    SearchableMemorySystem,
    MemoryContent,
    RichMemoryContent,
    EmbeddableMemoryContent,
    get_default_memory_system
)

# Import utility functions from our examples
from .content_utilities import (
    generate_memory_key,
    store_memory_content,
    retrieve_memory_content,
    create_insight,
    create_fact
)

from .search_utilities import (
    search_memory,
    search_by_content,
    format_search_results
)

# Set up logger
logger = logging.getLogger("orcs.memory.example.agent_tools")

def get_agent_scope(context):
    """Extract scope from agent context.
    
    This is an example utility function that extracts a scope string
    from your agent context object. Implementation would depend on
    your specific agent framework.
    
    Args:
        context: Your agent context object
        
    Returns:
        A scope string
    """
    # Example implementation - adapt to your agent framework
    if hasattr(context, "agent_id"):
        return f"agent_{context.agent_id}"
    elif hasattr(context, "scope"):
        return context.scope
    else:
        return "default"

#
# Basic Memory Tools
#

@function_tool
def remember_for_agent(context, key: str, value: Any) -> str:
    """Store a value in memory for the agent.
    
    Args:
        context: The agent context
        key: The key to store under
        value: The value to store
        
    Returns:
        Confirmation message
    """
    memory = get_default_memory_system()
    scope = get_agent_scope(context)
    
    memory.store(key, value, scope)
    
    logger.info("Stored value under key '%s' in scope '%s'", key, scope)
    return f"Successfully stored '{key}' in memory"

@function_tool
def recall_for_agent(context, key: str) -> Any:
    """Retrieve a value from memory for the agent.
    
    Args:
        context: The agent context
        key: The key to retrieve
        
    Returns:
        The retrieved value or an error message
    """
    memory = get_default_memory_system()
    scope = get_agent_scope(context)
    
    try:
        value = memory.retrieve(key, scope)
        if value is None:
            return f"No value found for key '{key}'"
        return value
    except Exception as e:
        logger.error("Error retrieving key '%s': %s", key, str(e))
        return f"Error retrieving memory: {str(e)}"

#
# Rich Content Tools
#

@function_tool
def remember_insight(context, insight: str, importance: float = 0.7, tags: Optional[List[str]] = None) -> str:
    """Store an important insight in memory.
    
    Args:
        context: The agent context
        insight: The insight text
        importance: Importance score (0.0 to 1.0)
        tags: Optional list of tags
        
    Returns:
        Confirmation message
    """
    memory = get_default_memory_system()
    scope = get_agent_scope(context)
    
    # Create memory content
    memory_content = create_insight(insight, importance, tags)
    
    # Generate key
    key = generate_memory_key("insight")
    
    # Store in memory
    store_memory_content(key, memory_content, scope, memory)
    
    logger.info("Stored insight with importance %.2f under key '%s'", 
               importance, key)
    return f"Successfully stored insight in memory"

@function_tool
def remember_fact(context, fact: str, importance: float = 0.5, tags: Optional[List[str]] = None) -> str:
    """Store a factual observation in memory.
    
    Args:
        context: The agent context
        fact: The fact text
        importance: Importance score (0.0 to 1.0)
        tags: Optional list of tags
        
    Returns:
        Confirmation message
    """
    memory = get_default_memory_system()
    scope = get_agent_scope(context)
    
    # Create memory content
    memory_content = create_fact(fact, importance, tags)
    
    # Generate key
    key = generate_memory_key("fact")
    
    # Store in memory
    store_memory_content(key, memory_content, scope, memory)
    
    logger.info("Stored fact with importance %.2f under key '%s'", 
               importance, key)
    return f"Successfully stored fact in memory"

#
# Search Tools
#

@function_tool
def search_memory_semantic(context, query: str, limit: int = 5, threshold: float = 0.7) -> str:
    """Search memory for items that semantically match a query.
    
    Args:
        context: The agent context
        query: The search query
        limit: Maximum number of results to return
        threshold: Minimum similarity score threshold (0.0 to 1.0)
        
    Returns:
        Formatted search results
    """
    memory = get_default_memory_system()
    
    # Check if memory system supports search
    if not isinstance(memory, SearchableMemorySystem):
        return "Semantic search is not available in the current memory system."
    
    scope = get_agent_scope(context)
    
    results = search_memory(
        query=query,
        scope=scope,
        memory_system=memory,
        limit=limit,
        threshold=threshold
    )
    
    return format_search_results(results)

@function_tool
def find_related_memories(context, content: str, limit: int = 5, threshold: float = 0.7) -> str:
    """Find memories related to the given content.
    
    Args:
        context: The agent context
        content: The content to find related memories for
        limit: Maximum number of results to return
        threshold: Minimum similarity score threshold (0.0 to 1.0)
        
    Returns:
        Formatted list of related memories
    """
    memory = get_default_memory_system()
    
    # Check if memory system supports search
    if not isinstance(memory, SearchableMemorySystem):
        return "Semantic search is not available in the current memory system."
    
    scope = get_agent_scope(context)
    
    results = search_by_content(
        content=content,
        scope=scope,
        memory_system=memory,
        limit=limit,
        threshold=threshold
    )
    
    return format_search_results(results)

#
# Tool Registration Helper
#

def get_memory_tools() -> List[callable]:
    """Get all memory-related tools for agent registration.
    
    Returns:
        List of memory tool functions
    """
    return [
        # Basic tools
        remember_for_agent,
        recall_for_agent,
        
        # Rich content tools
        remember_insight,
        remember_fact,
        
        # Search tools
        search_memory_semantic,
        find_related_memories
    ]

#
# Example Usage
#

if __name__ == "__main__":
    # This section demonstrates how you might use these tools
    
    # Mock agent context
    class AgentContext:
        def __init__(self, agent_id):
            self.agent_id = agent_id
    
    # Create a context
    context = AgentContext("test_agent")
    
    # Store some memories
    remember_insight(context, "Understanding abstractions helps create better software")
    remember_fact(context, "Python is a high-level programming language")
    
    # Search for related memories
    results = search_memory_semantic(context, "programming languages")
    print(results) 