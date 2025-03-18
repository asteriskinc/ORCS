"""Memory tools for ORCS agents"""

from typing import Any, Dict, List, Optional
import logging
from functools import wraps
import json
from openai import OpenAI
from datetime import datetime

from ..memory import SearchableAgentContext, MemoryContent

# Set up logger
logger = logging.getLogger("orcs.agent.memory_tools")

def memory_tool(func):
    """Decorator for agent memory tools to handle common error cases"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Error in memory tool %s: %s", func.__name__, str(e))
            return f"Error using memory tool: {str(e)}"
    return wrapper

@memory_tool
def remember_insight(context, insight: str, importance: Optional[float] = None) -> str:
    """Store an important insight in memory for future reference
    
    Args:
        context: The agent context
        insight: The insight text
        importance: Importance score (0.0 to 1.0), higher for more important insights
            
    Returns:
        Confirmation message
    """
    # Validate context type
    if not isinstance(context.context, SearchableAgentContext):
        return "Error: This tool requires a SearchableAgentContext"
    
    agent_context = context.context
    
    # Auto-determine importance if not provided
    if importance is None:
        # Attempt to assess importance using a simple heuristic
        words = insight.split()
        # Higher importance for longer insights (up to a cap)
        importance = min(0.7, 0.3 + (len(words) / 100))
    
    # Clamp importance to valid range
    importance = max(0.0, min(1.0, importance))
    
    try:
        # Store the insight
        key = agent_context.remember_insight(
            insight=insight,
            importance=importance
        )
        
        logger.info("Agent '%s' stored insight with importance %.2f", 
                   agent_context.agent_id, importance)
        return f"Successfully stored insight with importance {importance:.2f}"
    except Exception as e:
        logger.error("Failed to store insight: %s", str(e))
        return f"Error storing insight: {str(e)}"

@memory_tool
def remember_for_agent(context, target_agent_id: str, content: str, 
                     memory_type: str = "shared") -> str:
    """Store information specifically for another agent
    
    Args:
        context: The agent context
        target_agent_id: ID of the agent this memory is for
        content: The content to share
        memory_type: Type of memory ("shared", "insight", "fact", etc.)
            
    Returns:
        Confirmation message
    """
    # Validate context type
    if not isinstance(context.context, SearchableAgentContext):
        return "Error: This tool requires a SearchableAgentContext"
    
    agent_context = context.context
    
    try:
        # Store the memory for the target agent
        key = agent_context.remember_for_agent(
            target_agent_id=target_agent_id,
            content_text=content,
            memory_type=memory_type
        )
        
        logger.info("Agent '%s' stored memory for agent '%s'", 
                   agent_context.agent_id, target_agent_id)
        return f"Successfully shared memory with agent {target_agent_id}"
    except Exception as e:
        logger.error("Failed to store memory for agent: %s", str(e))
        return f"Error sharing memory: {str(e)}"

@memory_tool
def get_relevant_context(context, query: str, limit: int = 5) -> str:
    """Retrieve memory items relevant to a specific query
    
    Args:
        context: The agent context
        query: The search query
        limit: Maximum number of results to return
            
    Returns:
        Formatted string with relevant memories
    """
    # Validate context type
    if not isinstance(context.context, SearchableAgentContext):
        return "Error: This tool requires a SearchableAgentContext"
    
    agent_context = context.context
    
    try:
        # Get formatted context
        result = agent_context.get_relevant_context(query, limit)
        if not result or result == "No relevant context found in memory.":
            logger.info("No relevant context found for query '%s'", query)
            return "No relevant information found in memory for this query."
            
        logger.info("Retrieved relevant context for query '%s'", query)
        return result
    except Exception as e:
        logger.error("Failed to retrieve relevant context: %s", str(e))
        return f"Error retrieving context: {str(e)}"

@memory_tool
def reflect_on_memory(context, reflection_query: str) -> str:
    """Reflect on existing memories to generate insights or summaries
    
    Args:
        context: The agent context
        reflection_query: Query describing what to reflect on
            
    Returns:
        Reflection result
    """
    # Validate context type
    if not isinstance(context.context, SearchableAgentContext):
        return "Error: This tool requires a SearchableAgentContext"
    
    agent_context = context.context
    
    try:
        # First retrieve relevant memories
        results = agent_context.search_memory(
            query=reflection_query,
            limit=10,
            min_similarity=0.3
        )
        
        if not results:
            logger.info("No memories found to reflect on for query '%s'", reflection_query)
            return "No relevant memories found to reflect on."
        
        # Format memories for reflection
        memories_text = []
        for i, (content, similarity) in enumerate(results, 1):
            memories_text.append(f"Memory {i}:")
            memories_text.append(f"- Type: {content.memory_type}")
            memories_text.append(f"- Content: {content.content}")
            memories_text.append(f"- Importance: {content.importance:.2f}")
            memories_text.append(f"- Relevance: {similarity:.2f}")
            memories_text.append("")
        
        memories_str = "\n".join(memories_text)
        
        # Use OpenAI to generate reflection if available
        try:
            from openai import OpenAI
            client = OpenAI()
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a memory reflection assistant. "
                     "Your task is to analyze memories and generate insights, patterns, "
                     "or summaries based on the provided memories."},
                    {"role": "user", "content": f"Based on the following memories, {reflection_query}\n\n{memories_str}"}
                ],
                max_tokens=500
            )
            
            reflection = response.choices[0].message.content.strip()
            
            # Store the reflection as a new insight
            agent_context.remember_insight(
                insight=f"Reflection: {reflection}",
                importance=0.8,
                tags=["reflection"]
            )
            
            logger.info("Generated reflection for query '%s'", reflection_query)
            return f"Reflection:\n\n{reflection}"
            
        except (ImportError, Exception) as e:
            # Fall back to simpler summary if OpenAI is unavailable
            logger.warning("Could not use OpenAI for reflection: %s", str(e))
            summary = f"Found {len(results)} memories related to '{reflection_query}'."
            summary += "\nHere are the most relevant memories:\n\n"
            
            for i, (content, similarity) in enumerate(results[:3], 1):
                summary += f"{i}. {content.content}\n"
                
            return summary
            
    except Exception as e:
        logger.error("Failed to reflect on memories: %s", str(e))
        return f"Error reflecting on memories: {str(e)}"

def get_memory_tools():
    """Get a list of all memory tools
    
    Returns:
        List of all memory tool functions
    """
    return [
        remember_insight,
        remember_for_agent,
        get_relevant_context,
        reflect_on_memory
    ] 