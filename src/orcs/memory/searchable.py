"""Searchable memory implementation for the v2 memory system.

This module provides classes and utilities for semantic search capabilities
in the memory system, building on top of the core memory abstractions.
"""

import logging
import re
from typing import Any, List, Optional, Tuple, Union, Callable

import numpy as np

from .system import MemorySystem
from .content import MemoryContent, RichMemoryContent, EmbeddableMemoryContent
from .storage_memory import ScopedAccessStorageMemorySystem
from .providers import StorageProvider

# Set up logger
logger = logging.getLogger("orcs.memory.searchable")

class EmbeddingProvider:
    """Abstract base class for embedding providers.
    
    Embedding providers are responsible for converting text into vector embeddings
    that can be used for semantic search operations.
    """
    
    def embed(self, text: str) -> np.ndarray:
        """Convert a text string into a vector embedding.
        
        Args:
            text: The text to embed
            
        Returns:
            A numpy array containing the vector embedding
        """
        raise NotImplementedError("Embedding providers must implement embed method")
    
    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors.
        
        Returns:
            The dimension of the embedding vectors
        """
        raise NotImplementedError("Embedding providers must implement get_dimension method")
    
    def get_name(self) -> str:
        """Get the name of the embedding provider.
        
        Returns:
            The name of the provider
        """
        raise NotImplementedError("Embedding providers must implement get_name method")

class SimpleEmbeddingProvider(EmbeddingProvider):
    """Simple embedding provider that uses a term frequency approach.
    
    This is a basic implementation meant for testing or when more advanced
    embedding capabilities are not available.
    """
    
    def __init__(self, dimension: int = 100, vocabulary_size: int = 10000):
        """Initialize a simple embedding provider.
        
        Args:
            dimension: The dimension of the embedding vectors
            vocabulary_size: The size of the vocabulary to use
        """
        self.dimension = dimension
        self.vocabulary_size = vocabulary_size
        self.word_to_index: dict[str, int] = {}
        self.next_index = 0
    
    def _get_word_index(self, word: str) -> int:
        """Get or create an index for a word.
        
        Args:
            word: The word to get an index for
            
        Returns:
            The index
        """
        if word not in self.word_to_index:
            if self.next_index < self.vocabulary_size:
                self.word_to_index[word] = self.next_index
                self.next_index += 1
            else:
                # If vocabulary is full, use a hash function to determine index
                self.word_to_index[word] = hash(word) % self.vocabulary_size
        
        return self.word_to_index[word]
    
    def embed(self, text: str) -> np.ndarray:
        """Convert text to a simple term frequency vector.
        
        Args:
            text: The text to embed
            
        Returns:
            A numpy array containing the embedding
        """
        # Normalize and tokenize the text
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Create a term frequency vector
        embedding = np.zeros(self.dimension)
        
        for word in words:
            # Get the index for this word, modulo the embedding dimension
            index = self._get_word_index(word) % self.dimension
            embedding[index] += 1
        
        # Normalize to unit length
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding
    
    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors.
        
        Returns:
            The dimension
        """
        return self.dimension
    
    def get_name(self) -> str:
        """Get the name of this embedding provider.
        
        Returns:
            The name
        """
        return "SimpleEmbeddingProvider"

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate the cosine similarity between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        The cosine similarity (between -1 and 1)
    """
    # Handle zero vectors
    if np.all(a == 0) or np.all(b == 0):
        return 0.0
    
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class SearchableMemorySystem(ScopedAccessStorageMemorySystem):
    """Memory system that supports semantic search.
    
    This extends the ScopedAccessStorageMemorySystem with semantic search
    capabilities powered by embedding providers.
    """
    
    def __init__(
        self,
        storage_provider: StorageProvider,
        embedding_provider: EmbeddingProvider,
        default_access_scope: str = "global",
        embedding_field: str = "content"
    ):
        """Initialize a searchable memory system.
        
        Args:
            storage_provider: Provider for storing memory data
            embedding_provider: Provider for generating embeddings
            default_access_scope: The default scope for access control (default: "global")
            embedding_field: The field of MemoryContent to embed (default: "content")
        """
        super().__init__(storage_provider, default_access_scope)
        self.embedding_provider = embedding_provider
        self.embedding_field = embedding_field
        logger.info("Initialized SearchableMemorySystem with %s", embedding_provider.get_name())
    
    def _embed_memory_content(self, content: Union[MemoryContent, RichMemoryContent]) -> EmbeddableMemoryContent:
        """Embed MemoryContent and convert to EmbeddableMemoryContent.
        
        Args:
            content: The memory content to embed
            
        Returns:
            An EmbeddableMemoryContent object
        """
        # If it's already an EmbeddableMemoryContent with embeddings, just return it
        if isinstance(content, EmbeddableMemoryContent) and content.embedding is not None:
            return content
        
        # Generate an embedding for the content
        text_to_embed = getattr(content, self.embedding_field)
        if not isinstance(text_to_embed, str):
            # Try to convert to string if possible
            text_to_embed = str(text_to_embed)
        
        embedding = self.embedding_provider.embed(text_to_embed)
        
        # If it's already an EmbeddableMemoryContent, just set the embedding
        if isinstance(content, EmbeddableMemoryContent):
            content.embedding = embedding
            return content
            
        # Otherwise, create a new EmbeddableMemoryContent object
        # First get all metadata from the original content
        metadata = {}
        if hasattr(content, "metadata") and content.metadata:
            metadata = content.metadata.copy()
            
        # Get importance and tags if present
        importance = getattr(content, "importance", 0.0)
        memory_type = getattr(content, "memory_type", "generic")
        tags = getattr(content, "tags", [])
        
        # Create a new EmbeddableMemoryContent
        return EmbeddableMemoryContent(
            content=content.content,
            embedding=embedding,
            importance=importance,
            memory_type=memory_type,
            tags=tags,
            metadata=metadata
        )
    
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store a value in memory with embedding if applicable.
        
        Args:
            key: The key to store under
            value: The value to store
            scope: The scope to store in (default: "global")
        """
        # If this is a memory content object, add embedding
        if isinstance(value, MemoryContent):
            value = self._embed_memory_content(value)
        
        # Use the parent class to store the value
        super().store(key, value, scope)
    
    def search(
        self,
        query: str,
        scope: str = "global",
        limit: int = 10,
        include_child_scopes: bool = True,
        threshold: float = 0.7,
        filter_fn: Optional[Callable[[Any], bool]] = None
    ) -> List[Tuple[str, Any, float]]:
        """Search for memory items that semantically match the query.
        
        Args:
            query: The search query
            scope: The scope to search in (default: "global")
            limit: Maximum number of results to return (default: 10)
            include_child_scopes: Whether to include child scopes (default: True)
            threshold: Minimum similarity score threshold (default: 0.7)
            filter_fn: Optional function to filter results
            
        Returns:
            List of (key, value, score) tuples
        """
        # Embed the query
        query_embedding = self.embedding_provider.embed(query)
        logger.debug(f"Query embedding shape: {query_embedding.shape}")
        
        # Get all keys from the specified scope
        keys = self.list_keys(pattern="*", scope=scope, include_child_scopes=include_child_scopes)
        logger.debug(f"Found {len(keys)} keys to search")
        
        results = []
        for key in keys:
            try:
                # Get the memory item and its scope
                value = self.retrieve(key, scope)
                
                # Skip if value doesn't exist or doesn't pass the filter
                if value is None or (filter_fn is not None and not filter_fn(value)):
                    continue
                
                # Log the type of value for debugging
                logger.debug(f"Value for key {key} is of type {type(value)}")
                    
                # Check if it's a MemoryContent with embedding
                if isinstance(value, EmbeddableMemoryContent):
                    # Log if embedding is missing
                    if value.embedding is None:
                        logger.warning(f"EmbeddableMemoryContent for key {key} has no embedding")
                        continue
                        
                    # Calculate similarity
                    try:
                        similarity = cosine_similarity(query_embedding, value.embedding)
                        logger.debug(f"Similarity for key {key}: {similarity:.3f}")
                        
                        # Add to results if it meets the threshold
                        if similarity >= threshold:
                            results.append((key, value, similarity))
                    except Exception as e:
                        logger.error(f"Error calculating similarity for key {key}: {str(e)}")
                else:
                    logger.debug(f"Value for key {key} is not EmbeddableMemoryContent")
            except Exception as e:
                logger.warning("Error processing key %s during search: %s", key, str(e))
        
        # Sort by similarity score in descending order
        results.sort(key=lambda x: x[2], reverse=True)
        logger.debug(f"Found {len(results)} results above threshold {threshold}")
        
        # Return the top results
        return results[:limit]
    
    def search_by_embedding(
        self,
        embedding: np.ndarray,
        scope: str = "global",
        limit: int = 10,
        include_child_scopes: bool = True,
        threshold: float = 0.7,
        filter_fn: Optional[Callable[[Any], bool]] = None
    ) -> List[Tuple[str, Any, float]]:
        """Search for memory items using a provided embedding vector.
        
        This is useful for more advanced use cases where you might have
        pre-computed embeddings or want to search based on another memory item.
        
        Args:
            embedding: The embedding vector to search with
            scope: The scope to search in (default: "global")
            limit: Maximum number of results to return (default: 10)
            include_child_scopes: Whether to include child scopes (default: True)
            threshold: Minimum similarity score threshold (default: 0.7)
            filter_fn: Optional function to filter results
            
        Returns:
            List of (key, value, score) tuples
        """
        # Get all keys from the specified scope
        keys = self.list_keys(pattern="*", scope=scope, include_child_scopes=include_child_scopes)
        
        results = []
        for key in keys:
            try:
                # Get the memory item and its scope
                value = self.retrieve(key, scope)
                
                # Skip if value doesn't exist or doesn't pass the filter
                if value is None or (filter_fn is not None and not filter_fn(value)):
                    continue
                
                # If it's an EmbeddableMemoryContent with an embedding, calculate similarity
                if isinstance(value, EmbeddableMemoryContent) and value.embedding is not None:
                    similarity = cosine_similarity(embedding, value.embedding)
                    
                    # Add to results if it meets the threshold
                    if similarity >= threshold:
                        results.append((key, value, similarity))
            except Exception as e:
                logger.warning("Error processing key %s during search: %s", key, str(e))
        
        # Sort by similarity score in descending order
        results.sort(key=lambda x: x[2], reverse=True)
        
        # Return the top results
        return results[:limit] 