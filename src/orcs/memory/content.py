"""Memory content model for the v2 memory system.

This module provides classes for structured memory content with various
capabilities including rich metadata, importance, tagging, and embedding.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import numpy as np
import json

class MemoryContent:
    """Base class for structured memory content.
    
    This class serves as a lightweight container for structured content
    with basic metadata. It can be extended with additional functionality.
    """
    
    def __init__(self, content: Any, metadata: Optional[Dict[str, Any]] = None):
        """Initialize memory content.
        
        Args:
            content: The primary content to store
            metadata: Optional metadata dictionary
        """
        self.content = content
        self.metadata = metadata or {}
        
        # Record creation time if not provided
        if "creation_time" not in self.metadata:
            self.metadata["creation_time"] = datetime.now().isoformat()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add a metadata item.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata item.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            The metadata value or default
        """
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "content": self.content,
            "metadata": self.metadata,
            "type": self.__class__.__name__
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryContent":
        """Create a MemoryContent instance from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            MemoryContent instance
        """
        return cls(
            content=data["content"],
            metadata=data["metadata"]
        )

class RichMemoryContent(MemoryContent):
    """Enhanced memory content with importance ranking, type, and tagging.
    
    This class extends MemoryContent with features useful for prioritizing
    and categorizing memories.
    """
    
    def __init__(
        self, 
        content: Any, 
        importance: float = 0.5, 
        memory_type: str = "general",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize rich memory content.
        
        Args:
            content: The primary content to store
            importance: Importance score (0.0 to 1.0)
            memory_type: Type of memory (e.g., "insight", "fact")
            tags: Optional list of tags
            metadata: Optional metadata dictionary
        """
        super().__init__(content, metadata)
        self.importance = max(0.0, min(1.0, importance))  # Clamp to [0, 1]
        self.memory_type = memory_type
        self.tags = tags or []
        
    def was_accessed(self) -> None:
        """Update access tracking metadata.
        
        This method should be called whenever the memory is retrieved,
        to keep track of access patterns.
        """
        access_count = self.metadata.get("access_count", 0)
        self.metadata["access_count"] = access_count + 1
        self.metadata["last_access_time"] = datetime.now().isoformat()
    
    def update_importance(self, importance: float) -> None:
        """Update the importance score.
        
        Args:
            importance: New importance score (0.0 to 1.0)
        """
        self.importance = max(0.0, min(1.0, importance))  # Clamp to [0, 1]
    
    def add_tags(self, tags: List[str]) -> None:
        """Add tags to the memory.
        
        Args:
            tags: List of tags to add
        """
        for tag in tags:
            if tag not in self.tags:
                self.tags.append(tag)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        data = super().to_dict()
        data.update({
            "importance": self.importance,
            "memory_type": self.memory_type,
            "tags": self.tags
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RichMemoryContent":
        """Create a RichMemoryContent instance from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            RichMemoryContent instance
        """
        return cls(
            content=data["content"],
            importance=data["importance"],
            memory_type=data["memory_type"],
            tags=data["tags"],
            metadata=data["metadata"]
        )

class EmbeddableMemoryContent(RichMemoryContent):
    """Memory content with embedding support for semantic search.
    
    This class extends RichMemoryContent with embedding capabilities
    for semantic search operations.
    """
    
    def __init__(
        self, 
        content: Any, 
        embedding: Optional[np.ndarray] = None,
        importance: float = 0.5, 
        memory_type: str = "general",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize embeddable memory content.
        
        Args:
            content: The primary content to store
            embedding: Vector embedding for semantic search
            importance: Importance score (0.0 to 1.0)
            memory_type: Type of memory (e.g., "insight", "fact")
            tags: Optional list of tags
            metadata: Optional metadata dictionary
        """
        super().__init__(
            content, 
            importance, 
            memory_type, 
            tags, 
            metadata
        )
        self.embedding = embedding
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        data = super().to_dict()
        
        # Convert embedding to list for JSON serialization if present
        if self.embedding is not None:
            data["embedding"] = self.embedding.tolist()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddableMemoryContent":
        """Create an EmbeddableMemoryContent instance from a dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            EmbeddableMemoryContent instance
        """
        # Convert embedding from list back to numpy array if present
        embedding = None
        if "embedding" in data:
            embedding = np.array(data["embedding"])
        
        return cls(
            content=data["content"],
            embedding=embedding,
            importance=data["importance"],
            memory_type=data["memory_type"],
            tags=data["tags"],
            metadata=data["metadata"]
        ) 