"""Tests for the memory content classes in the v2 memory system."""

import unittest
from datetime import datetime
import numpy as np

from orcs.memory.v2 import (
    MemoryContent,
    RichMemoryContent,
    EmbeddableMemoryContent
)

class TestMemoryContent(unittest.TestCase):
    """Test the MemoryContent class."""
    
    def test_init(self):
        """Test initialization with basic attributes."""
        content = MemoryContent(content="Test content")
        self.assertEqual(content.content, "Test content")
        self.assertIsInstance(content.metadata, dict)
        self.assertEqual(len(content.metadata), 1)  # Contains creation_time
        self.assertIn("creation_time", content.metadata)
    
    def test_metadata(self):
        """Test metadata operations."""
        content = MemoryContent(content="Test content")
        
        # Test adding metadata
        content.add_metadata("key", "value")
        self.assertEqual(content.metadata["key"], "value")
        
        # Test adding multiple metadata items
        content.add_metadata("key2", "value2")
        self.assertEqual(content.metadata["key2"], "value2")
        
        # Test retrieving metadata
        self.assertEqual(content.get_metadata("key"), "value")
        self.assertEqual(content.get_metadata("key2"), "value2")
        
        # Test retrieving non-existent metadata
        self.assertIsNone(content.get_metadata("nonexistent"))
        self.assertEqual(content.get_metadata("nonexistent", "default"), "default")
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        content = MemoryContent(content="Test content")
        content.add_metadata("key", "value")
        
        data = content.to_dict()
        self.assertEqual(data["content"], "Test content")
        self.assertEqual(data["metadata"]["key"], "value")
        self.assertIn("creation_time", data["metadata"])
        self.assertEqual(data["type"], "MemoryContent")
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "content": "Test content",
            "metadata": {"key": "value", "creation_time": "2023-01-01T00:00:00"}
        }
        
        content = MemoryContent.from_dict(data)
        self.assertEqual(content.content, "Test content")
        self.assertEqual(content.get_metadata("key"), "value")

class TestRichMemoryContent(unittest.TestCase):
    """Test the RichMemoryContent class."""
    
    def test_init(self):
        """Test initialization with rich attributes."""
        content = RichMemoryContent(
            content="Test content",
            importance=0.8,
            memory_type="insight",
            tags=["important", "test"]
        )
        
        self.assertEqual(content.content, "Test content")
        self.assertEqual(content.importance, 0.8)
        self.assertEqual(content.memory_type, "insight")
        self.assertListEqual(content.tags, ["important", "test"])
        
        # Test importance clamping
        content_high = RichMemoryContent(content="Test", importance=1.5)
        self.assertEqual(content_high.importance, 1.0)
        
        content_low = RichMemoryContent(content="Test", importance=-0.5)
        self.assertEqual(content_low.importance, 0.0)
    
    def test_was_accessed(self):
        """Test access tracking."""
        content = RichMemoryContent(content="Test content")
        
        # Check if access count is initially not present
        self.assertIsNone(content.get_metadata("access_count"))
        
        # Mark as accessed
        content.was_accessed()
        
        # Check if access count and last_access_time are updated
        access_count = content.get_metadata("access_count")
        last_access_time = content.get_metadata("last_access_time")
        self.assertEqual(access_count, 1)
        self.assertIsNotNone(last_access_time)
        
        # Access again and verify timestamp and count are updated
        first_access = last_access_time
        content.was_accessed()
        second_access = content.get_metadata("last_access_time")
        self.assertNotEqual(first_access, second_access)
        self.assertEqual(content.get_metadata("access_count"), 2)
    
    def test_update_importance(self):
        """Test importance updating."""
        content = RichMemoryContent(content="Test content", importance=0.5)
        
        # Increase importance
        content.update_importance(0.7)
        self.assertEqual(content.importance, 0.7)
        
        # Increase beyond max
        content.update_importance(1.2)
        self.assertEqual(content.importance, 1.0)
        
        # Decrease importance
        content.update_importance(0.3)
        self.assertEqual(content.importance, 0.3)
        
        # Decrease below min
        content.update_importance(-0.1)
        self.assertEqual(content.importance, 0.0)
    
    def test_add_tags(self):
        """Test adding tags."""
        content = RichMemoryContent(content="Test content", tags=["initial"])
        
        # Add a single tag as a string
        content.add_tags(["new"])
        self.assertIn("new", content.tags)
        self.assertIn("initial", content.tags)
        
        # Add multiple tags
        content.add_tags(["another", "yetanother"])
        self.assertIn("another", content.tags)
        self.assertIn("yetanother", content.tags)
        
        # Add duplicate tags
        original_count = len(content.tags)
        content.add_tags(["new", "initial"])
        self.assertEqual(len(content.tags), original_count)
    
    def test_to_dict(self):
        """Test conversion to dictionary with rich attributes."""
        content = RichMemoryContent(
            content="Test content",
            importance=0.8,
            memory_type="insight",
            tags=["important", "test"]
        )
        content.was_accessed()
        
        data = content.to_dict()
        self.assertEqual(data["content"], "Test content")
        self.assertEqual(data["importance"], 0.8)
        self.assertEqual(data["memory_type"], "insight")
        self.assertListEqual(data["tags"], ["important", "test"])
        self.assertIn("last_access_time", data["metadata"])
        self.assertEqual(data["type"], "RichMemoryContent")
    
    def test_from_dict(self):
        """Test creation from dictionary with rich attributes."""
        now = datetime.now().isoformat()
        data = {
            "content": "Test content",
            "importance": 0.8,
            "memory_type": "insight",
            "tags": ["important", "test"],
            "metadata": {
                "creation_time": now,
                "access_count": 1,
                "last_access_time": now,
                "custom": "value"
            }
        }
        
        content = RichMemoryContent.from_dict(data)
        self.assertEqual(content.content, "Test content")
        self.assertEqual(content.importance, 0.8)
        self.assertEqual(content.memory_type, "insight")
        self.assertListEqual(content.tags, ["important", "test"])
        self.assertEqual(content.get_metadata("creation_time"), now)
        self.assertEqual(content.get_metadata("custom"), "value")

class TestEmbeddableMemoryContent(unittest.TestCase):
    """Test the EmbeddableMemoryContent class."""
    
    def test_init(self):
        """Test initialization with embedding."""
        embedding = np.array([0.1, 0.2, 0.3])
        content = EmbeddableMemoryContent(
            content="Test content",
            embedding=embedding
        )
        
        self.assertEqual(content.content, "Test content")
        np.testing.assert_array_equal(content.embedding, embedding)
    
    def test_to_dict(self):
        """Test conversion to dictionary with embedding."""
        embedding = np.array([0.1, 0.2, 0.3])
        content = EmbeddableMemoryContent(
            content="Test content",
            embedding=embedding
        )
        
        data = content.to_dict()
        self.assertEqual(data["content"], "Test content")
        np.testing.assert_array_equal(np.array(data["embedding"]), embedding)
        self.assertEqual(data["type"], "EmbeddableMemoryContent")
    
    def test_from_dict(self):
        """Test creation from dictionary with embedding."""
        embedding = [0.1, 0.2, 0.3]
        data = {
            "content": "Test content",
            "importance": 0.8,
            "memory_type": "insight",
            "tags": ["important", "test"],
            "embedding": embedding,
            "metadata": {
                "custom": "value"
            }
        }
        
        content = EmbeddableMemoryContent.from_dict(data)
        self.assertEqual(content.content, "Test content")
        np.testing.assert_array_equal(content.embedding, np.array(embedding))
        self.assertEqual(content.importance, 0.8)
        self.assertEqual(content.memory_type, "insight")

if __name__ == "__main__":
    unittest.main() 