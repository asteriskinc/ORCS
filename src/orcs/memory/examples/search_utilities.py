"""Example utilities for semantic search with memory content.

This module demonstrates how to create utility functions for performing
semantic search operations with the memory system.
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import logging

import numpy as np

from orcs.memory import (
    MemorySystem,
    MemoryContent, 
    RichMemoryContent, 
    EmbeddableMemoryContent,
    SearchableMemorySystem
)

# Set up logger
logger = logging.getLogger("orcs.memory.examples.search_utilities")

def search_memory(
    query: str,
    scope: str,
    memory_system: SearchableMemorySystem,
    include_child_scopes: bool = True,
    limit: int = 10,
    threshold: float = 0.7,
    memory_type: Optional[str] = None
) -> List[Tuple[str, Any, float]]:
    """Search for memory items that semantically match the query.
    
    Args:
        query: The search query
        scope: The scope to search in
        memory_system: SearchableMemorySystem instance to use
        include_child_scopes: Whether to include child scopes
        limit: Maximum number of results to return
        threshold: Minimum similarity score threshold
        memory_type: Optional memory type to filter by
        
    Returns:
        List of (key, value, score) tuples
    """
    # Create a filter function if memory_type is specified
    filter_fn = None
    if memory_type is not None:
        def filter_by_type(value: Any) -> bool:
            if isinstance(value, RichMemoryContent):
                return value.memory_type == memory_type
            return False
        filter_fn = filter_by_type
    
    # Perform the search
    results = memory_system.search(
        query=query,
        scope=scope,
        include_child_scopes=include_child_scopes,
        limit=limit,
        threshold=threshold,
        filter_fn=filter_fn
    )
    
    logger.info("Found %d results for query '%s' in scope '%s'", 
               len(results), query, scope)
    return results

def search_by_content(
    content: Union[str, MemoryContent],
    scope: str, 
    memory_system: SearchableMemorySystem,
    include_child_scopes: bool = True,
    limit: int = 10,
    threshold: float = 0.7,
    memory_type: Optional[str] = None
) -> List[Tuple[str, Any, float]]:
    """Search for memory items similar to provided content.
    
    Args:
        content: The content to search for (string or MemoryContent)
        scope: The scope to search in
        memory_system: SearchableMemorySystem instance to use
        include_child_scopes: Whether to include child scopes
        limit: Maximum number of results to return
        threshold: Minimum similarity score threshold
        memory_type: Optional memory type to filter by
        
    Returns:
        List of (key, value, score) tuples
    """
    # If the content is a string, treat it like a query
    if isinstance(content, str):
        return search_memory(
            query=content,
            scope=scope,
            memory_system=memory_system,
            include_child_scopes=include_child_scopes,
            limit=limit,
            threshold=threshold,
            memory_type=memory_type
        )
    
    # If the content is a MemoryContent object, use its embedding if available
    if isinstance(content, EmbeddableMemoryContent) and content.embedding is not None:
        embedding = content.embedding
    else:
        # Otherwise, embed the content's text
        if not hasattr(content, memory_system.embedding_field):
            logger.warning("Content does not have the expected embedding field: %s", 
                          memory_system.embedding_field)
            return []
        
        text_to_embed = getattr(content, memory_system.embedding_field)
        if not isinstance(text_to_embed, str):
            text_to_embed = str(text_to_embed)
        
        embedding = memory_system.embedding_provider.embed(text_to_embed)
    
    # Create a filter function if memory_type is specified
    filter_fn = None
    if memory_type is not None:
        def filter_by_type(value: Any) -> bool:
            if isinstance(value, RichMemoryContent):
                return value.memory_type == memory_type
            return False
        filter_fn = filter_by_type
    
    # Perform the search by embedding
    results = memory_system.search_by_embedding(
        embedding=embedding,
        scope=scope,
        include_child_scopes=include_child_scopes,
        limit=limit,
        threshold=threshold,
        filter_fn=filter_fn
    )
    
    logger.info("Found %d similar items in scope '%s'", len(results), scope)
    return results

def format_search_results(
    results: List[Tuple[str, Any, float]], 
    include_scores: bool = True,
    include_keys: bool = True
) -> str:
    """Format search results into a readable string.
    
    Args:
        results: The search results
        include_scores: Whether to include similarity scores
        include_keys: Whether to include keys
        
    Returns:
        A formatted string
    """
    if not results:
        return "No results found."
    
    formatted_results = []
    for i, (key, value, score) in enumerate(results):
        item = f"{i+1}. "
        
        if include_keys:
            item += f"[{key}] "
        
        if isinstance(value, MemoryContent):
            item += value.content
            
            # Include memory type and tags if available
            if isinstance(value, RichMemoryContent):
                if value.memory_type:
                    item += f" (Type: {value.memory_type}"
                    if value.tags:
                        item += f", Tags: {', '.join(value.tags)}"
                    item += ")"
        else:
            item += str(value)
        
        if include_scores:
            item += f" [similarity: {score:.2f}]"
        
        formatted_results.append(item)
    
    return "\n".join(formatted_results) 