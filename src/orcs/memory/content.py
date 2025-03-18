from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime
import logging

# Set up logger
logger = logging.getLogger("orcs.memory.content")

class MemoryContent:
    """Rich content model for agent memories
    
    This class represents a rich memory entity that can be stored in the memory system,
    with support for metadata, importance ranking, and embeddings.
    """
    
    def __init__(self, 
                 content: Any,
                 importance: float = 0.5,
                 memory_type: str = "knowledge",
                 tags: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize a memory content object
        
        Args:
            content: The actual content to be stored
            importance: Importance score (0.0 to 1.0) for this memory
            memory_type: Type of memory (e.g., "knowledge", "insight", "observation")
            tags: List of tags for better retrieval
            metadata: Additional metadata for this memory
        """
        self.content = content
        self.importance = max(0.0, min(1.0, importance))  # Clamp to [0.0, 1.0]
        self.memory_type = memory_type
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_accessed_at = None
        self.access_count = 0
        self.embedding = None
        
    def was_accessed(self) -> None:
        """Update access metadata when this memory is retrieved"""
        self.last_accessed_at = datetime.now()
        self.access_count += 1
        
    def update_importance(self, new_importance: float) -> None:
        """Update the importance score
        
        Args:
            new_importance: New importance score (0.0 to 1.0)
        """
        self.importance = max(0.0, min(1.0, new_importance))
        
    def add_tags(self, new_tags: List[str]) -> None:
        """Add tags to this memory
        
        Args:
            new_tags: List of tags to add
        """
        self.tags.extend([tag for tag in new_tags if tag not in self.tags])
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization
        
        Returns:
            Dictionary representation of this memory content
        """
        return {
            "content": self.content,
            "importance": self.importance,
            "memory_type": self.memory_type,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_count": self.access_count,
            # Embedding is not included as it may be large and is typically regenerated
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryContent':
        """Create a MemoryContent object from a dictionary
        
        Args:
            data: Dictionary representation of memory content
            
        Returns:
            MemoryContent object
        """
        content = cls(
            content=data["content"],
            importance=data.get("importance", 0.5),
            memory_type=data.get("memory_type", "knowledge"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
        
        # Restore timestamps
        if "created_at" in data:
            content.created_at = datetime.fromisoformat(data["created_at"])
        if "last_accessed_at" in data and data["last_accessed_at"]:
            content.last_accessed_at = datetime.fromisoformat(data["last_accessed_at"])
        
        # Restore access count
        content.access_count = data.get("access_count", 0)
        
        return content


def generate_memory_key(memory_type: str = "memory", prefix: str = "") -> str:
    """Generate a unique key for a memory
    
    Args:
        memory_type: Type of memory for prefixing
        prefix: Additional prefix for the key
        
    Returns:
        A unique memory key
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}:{memory_type}:{unique_id}"
    return f"{memory_type}:{unique_id}" 