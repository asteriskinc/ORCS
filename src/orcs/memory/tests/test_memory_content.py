"""Tests for rich memory content and searchable memory functionality."""

import unittest
import tempfile
import shutil
import os
import numpy as np
from pathlib import Path

from orcs.memory import (
    MemoryContent,
    RichMemoryContent,
    EmbeddableMemoryContent,
    generate_memory_key,
    SimpleEmbeddingProvider,
    SearchableMemorySystem,
    FileStorageProvider,
    store_memory_content,
    retrieve_memory_content,
    create_insight,
    create_fact,
    search_memory,
    search_by_content,
    format_search_results,
)

class TestMemoryContent(unittest.TestCase):
    """Tests for the memory content model."""
    
    def test_memory_content_basics(self):
        """Test basic MemoryContent functionality."""
        content = MemoryContent(content="This is a test memory")
        
        # Test content access
        self.assertEqual(content.content, "This is a test memory")
        
        # Test metadata
        content.metadata["test_key"] = "test_value"
        self.assertEqual(content.metadata["test_key"], "test_value")
        
        # Test to_dict and from_dict
        content_dict = content.to_dict()
        self.assertEqual(content_dict["content"], "This is a test memory")
        self.assertEqual(content_dict["metadata"]["test_key"], "test_value")
        
        new_content = MemoryContent.from_dict(content_dict)
        self.assertEqual(new_content.content, content.content)
        self.assertEqual(new_content.metadata["test_key"], content.metadata["test_key"])
    
    def test_rich_memory_content(self):
        """Test RichMemoryContent functionality."""
        content = RichMemoryContent(
            content="This is an important insight",
            importance=0.8,
            memory_type="insight",
            tags=["test", "important"]
        )
        
        # Test attributes
        self.assertEqual(content.content, "This is an important insight")
        self.assertEqual(content.importance, 0.8)
        self.assertEqual(content.memory_type, "insight")
        self.assertEqual(content.tags, ["test", "important"])
        
        # Test access tracking
        self.assertEqual(content.metadata.get("access_count", 0), 0)
        content.was_accessed()
        self.assertEqual(content.metadata["access_count"], 1)
        self.assertIn("last_access_time", content.metadata)
        
        # Test importance update
        content.update_importance(0.9)
        self.assertEqual(content.importance, 0.9)
        
        # Test tag manipulation
        content.add_tags(["new_tag"])
        self.assertIn("new_tag", content.tags)
        
        # Test serialization
        content_dict = content.to_dict()
        new_content = RichMemoryContent.from_dict(content_dict)
        self.assertEqual(new_content.content, content.content)
        self.assertEqual(new_content.importance, content.importance)
        self.assertEqual(new_content.memory_type, content.memory_type)
        self.assertEqual(set(new_content.tags), set(content.tags))
    
    def test_embeddable_memory_content(self):
        """Test EmbeddableMemoryContent functionality."""
        embedding = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        content = EmbeddableMemoryContent(
            content="This is embeddable content",
            embedding=embedding,
            importance=0.7,
            memory_type="fact",
            tags=["test", "embedding"]
        )
        
        # Test embedding storage
        np.testing.assert_array_equal(content.embedding, embedding)
        
        # Test serialization with embedding
        content_dict = content.to_dict()
        self.assertIn("embedding", content_dict)
        
        new_content = EmbeddableMemoryContent.from_dict(content_dict)
        np.testing.assert_array_equal(new_content.embedding, embedding)
        
    def test_generate_memory_key(self):
        """Test memory key generation."""
        key1 = generate_memory_key("test")
        key2 = generate_memory_key("test")
        
        # Keys should be different even with same prefix
        self.assertNotEqual(key1, key2)
        
        # Keys should have the correct prefix
        self.assertTrue(key1.startswith("test_"))
        self.assertTrue(key2.startswith("test_"))

class TestSearchableMemory(unittest.TestCase):
    """Tests for searchable memory functionality."""
    
    def setUp(self):
        """Set up a test environment with a searchable memory system."""
        # Create a temporary directory for file storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Create embedding and storage providers
        self.embedding_provider = SimpleEmbeddingProvider(dimension=10)
        self.storage_provider = FileStorageProvider(storage_dir=self.temp_dir)
        
        # Create a searchable memory system
        self.memory = SearchableMemorySystem(
            storage_provider=self.storage_provider,
            embedding_provider=self.embedding_provider,
            default_access_scope="test"
        )
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_memory_content_storage_and_retrieval(self):
        """Test storing and retrieving memory content."""
        # Create and store some memory content
        content1 = create_insight("The sky is blue", importance=0.8, tags=["nature"])
        content2 = create_fact("Water boils at 100°C", importance=0.6, tags=["science"])
        
        key1 = store_memory_content("insight_1", content1, "test", self.memory)
        key2 = store_memory_content("fact_1", content2, "test", self.memory)
        
        # Retrieve the content
        retrieved1 = retrieve_memory_content(key1, "test", self.memory)
        retrieved2 = retrieve_memory_content(key2, "test", self.memory)
        
        # Check if the content was retrieved correctly
        self.assertEqual(retrieved1.content, "The sky is blue")
        self.assertEqual(retrieved2.content, "Water boils at 100°C")
        
        # Check if the retrieved content has embeddings
        self.assertIsInstance(retrieved1, EmbeddableMemoryContent)
        self.assertIsInstance(retrieved2, EmbeddableMemoryContent)
        self.assertIsNotNone(retrieved1.embedding)
        self.assertIsNotNone(retrieved2.embedding)
    
    def test_semantic_search(self):
        """Test semantic search functionality."""
        # Create and store several memory items
        contents = [
            create_insight("The sky is blue", importance=0.8, tags=["nature"]),
            create_insight("The ocean is deep", importance=0.7, tags=["nature"]),
            create_fact("Water boils at 100°C", importance=0.6, tags=["science"]),
            create_fact("Gravity pulls objects toward Earth", importance=0.7, tags=["science"]),
            create_insight("Programming is about problem-solving", importance=0.9, tags=["tech"]),
        ]
        
        for i, content in enumerate(contents):
            store_memory_content(f"memory_{i}", content, "test", self.memory)
        
        # Test search by query
        results = search_memory(
            query="nature and blue skies",
            scope="test",
            memory_system=self.memory,
            limit=3,
            threshold=0.1  # Low threshold for simple embedding provider
        )
        
        # We should get at least some results
        self.assertGreater(len(results), 0)
        
        # The first result should be about the sky being blue
        self.assertIn("sky", results[0][1].content.lower())
        
        # Test search by content
        results = search_by_content(
            content=contents[0],  # "The sky is blue"
            scope="test",
            memory_system=self.memory,
            limit=3,
            threshold=0.1
        )
        
        # Should find at least itself
        self.assertGreater(len(results), 0)
        
        # Test search with memory type filter
        results = search_memory(
            query="science facts",
            scope="test",
            memory_system=self.memory,
            limit=3,
            threshold=0.1,
            memory_type="fact"
        )
        
        # Should find facts
        for key, value, score in results:
            self.assertEqual(value.memory_type, "fact")
    
    def test_result_formatting(self):
        """Test formatting of search results."""
        # Create and store a memory item
        content = create_insight("The sky is blue", importance=0.8, tags=["nature"])
        key = store_memory_content("test_key", content, "test", self.memory)
        
        # Perform a search to get results
        results = search_memory(
            query="blue sky",
            scope="test",
            memory_system=self.memory,
            limit=1,
            threshold=0.1
        )
        
        # Format the results
        formatted = format_search_results(results)
        
        # Check if the formatting includes expected elements
        self.assertIn("test_key", formatted)
        self.assertIn("The sky is blue", formatted)
        self.assertIn("similarity", formatted)
        
        # Test without scores
        formatted = format_search_results(results, include_scores=False)
        self.assertNotIn("similarity", formatted)
        
        # Test without keys
        formatted = format_search_results(results, include_keys=False)
        self.assertNotIn("test_key", formatted)

if __name__ == "__main__":
    unittest.main() 