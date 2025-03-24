from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np
import logging
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

# Set up logger
logger = logging.getLogger("orcs.memory.embeddings")

class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers
    
    This abstract class defines the operations that any embedding provider
    must implement to be used with the semantic memory system.
    """
    
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Generate an embedding vector for a text string
        
        Args:
            text: The text to embed
            
        Returns:
            A numpy array containing the embedding vector
        """
        pass
    
    @abstractmethod
    def dimension(self) -> int:
        """Get the dimension of the embedding vectors
        
        Returns:
            The dimension of the embedding vectors
        """
        pass
    
    def batch_embed(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embedding vectors for multiple texts
        
        By default, this calls embed() for each text, but providers
        should override this with a more efficient batch implementation.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]


class MockEmbeddingProvider(EmbeddingProvider):
    """Simple mock embedding provider for testing
    
    This provider generates random embeddings and is useful for
    development and testing without requiring external services.
    """
    
    def __init__(self, dimensions: int = 384, seed: Optional[int] = None):
        """Initialize mock embedding provider
        
        Args:
            dimensions: The dimensionality of embeddings to generate
            seed: Random seed for reproducibility
        """
        self.dimensions = dimensions
        self.rng = np.random.RandomState(seed)
        logger.info("Initialized MockEmbeddingProvider with %d dimensions", dimensions)
        
    def embed(self, text: str) -> np.ndarray:
        """Generate a mock embedding vector 
        
        Creates a reproducible embedding based on the hash of the text.
        This ensures the same text always gets the same embedding.
        
        Args:
            text: The text to embed
            
        Returns:
            A numpy array containing the mock embedding vector
        """
        # Use hash of text as seed for reproducible "embeddings"
        text_hash = hash(text) % 2**32
        text_rng = np.random.RandomState(text_hash)
        
        # Generate a random vector
        embedding = text_rng.randn(self.dimensions)
        
        # Normalize to unit length (typical for embeddings)
        embedding = embedding / np.linalg.norm(embedding)
        
        logger.debug("Generated mock embedding for text (length %d chars)", len(text))
        return embedding
    
    def dimension(self) -> int:
        """Get the dimension of the embedding vectors
        
        Returns:
            The dimension of the embedding vectors
        """
        return self.dimensions
    
    def batch_embed(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embedding vectors for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        logger.debug("Generating batch of %d mock embeddings", len(texts))
        return [self.embed(text) for text in texts]


# Try to import optional dependencies for real embeddings
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available, OpenAIEmbeddingProvider will not work")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers package not available, HuggingFaceEmbeddingProvider will not work")


if OPENAI_AVAILABLE:
    class OpenAIEmbeddingProvider(EmbeddingProvider):
        """Embedding provider using OpenAI's embedding models"""
        
        def __init__(self, 
                    model: str = "text-embedding-3-small", 
                    api_key: Optional[str] = None,
                    dimensions: Optional[int] = None):
            """Initialize OpenAI embedding provider
            
            Args:
                model: The OpenAI embedding model to use
                api_key: OpenAI API key (defaults to environment variable)
                dimensions: Optionally specify output dimensions (for dimension reduction)
            """
            self.model = model
            self.client = openai.OpenAI(api_key=api_key)
            
            # Set dimensions based on model if not specified
            if dimensions is None:
                if model == "text-embedding-3-small":
                    self._dimensions = 1536
                elif model == "text-embedding-3-large":
                    self._dimensions = 3072
                elif model == "text-embedding-ada-002":
                    self._dimensions = 1536
                else:
                    self._dimensions = 1536  # Default for unknown models
            else:
                self._dimensions = dimensions
                
            logger.info("Initialized OpenAIEmbeddingProvider with model '%s' (%d dimensions)", 
                       model, self._dimensions)
            
        def embed(self, text: str) -> np.ndarray:
            """Generate an embedding using OpenAI API
            
            Args:
                text: The text to embed
                
            Returns:
                A numpy array containing the embedding vector
            """
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    dimensions=self._dimensions
                )
                embedding = np.array(response.data[0].embedding)
                logger.debug("Generated OpenAI embedding for text (length %d chars)", len(text))
                return embedding
            except Exception as e:
                logger.error("Failed to generate OpenAI embedding: %s", str(e))
                raise
        
        def batch_embed(self, texts: List[str]) -> List[np.ndarray]:
            """Generate embedding vectors for multiple texts
            
            Args:
                texts: List of texts to embed
                
            Returns:
                List of embedding vectors
            """
            if not texts:
                return []
                
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=self._dimensions
                )
                
                # Sort by index to ensure order matches input
                sorted_data = sorted(response.data, key=lambda x: x.index)
                embeddings = [np.array(item.embedding) for item in sorted_data]
                
                logger.debug("Generated batch of %d OpenAI embeddings", len(texts))
                return embeddings
            except Exception as e:
                logger.error("Failed to generate batch OpenAI embeddings: %s", str(e))
                # Fall back to individual embedding
                logger.warning("Falling back to individual embedding")
                return [self.embed(text) for text in texts]
        
        def dimension(self) -> int:
            """Get the dimension of the embedding vectors
            
            Returns:
                The dimension of the embedding vectors
            """
            return self._dimensions


if SENTENCE_TRANSFORMERS_AVAILABLE:
    class HuggingFaceEmbeddingProvider(EmbeddingProvider):
        """Embedding provider using HuggingFace's Sentence Transformers"""
        
        def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
            """Initialize Hugging Face embedding provider
            
            Args:
                model_name: The model name to load from HuggingFace
            """
            self.model_name = model_name
            self.model = SentenceTransformer(model_name)
            dim = self.model.get_sentence_embedding_dimension()
            self._dimensions: int = dim if dim is not None else 384  # Default if None
            
            logger.info("Initialized HuggingFaceEmbeddingProvider with model '%s' (%d dimensions)", 
                       model_name, self._dimensions)
            
        def embed(self, text: str) -> np.ndarray:
            """Generate an embedding using Sentence Transformers
            
            Args:
                text: The text to embed
                
            Returns:
                A numpy array containing the embedding vector
            """
            try:
                embedding = self.model.encode(text, normalize_embeddings=True)
                logger.debug("Generated HuggingFace embedding for text (length %d chars)", len(text))
                return np.array(embedding)
            except Exception as e:
                logger.error("Failed to generate HuggingFace embedding: %s", str(e))
                raise
        
        def batch_embed(self, texts: List[str]) -> List[np.ndarray]:
            """Generate embedding vectors for multiple texts
            
            Args:
                texts: List of texts to embed
                
            Returns:
                List of embedding vectors
            """
            if not texts:
                return []
                
            try:
                embeddings = self.model.encode(texts, normalize_embeddings=True)
                logger.debug("Generated batch of %d HuggingFace embeddings", len(texts))
                return [np.array(embedding) for embedding in embeddings]
            except Exception as e:
                logger.error("Failed to generate batch HuggingFace embeddings: %s", str(e))
                raise
        
        def dimension(self) -> int:
            """Get the dimension of the embedding vectors
            
            Returns:
                The dimension of the embedding vectors
            """
            return self._dimensions


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        Cosine similarity (between -1 and 1)
    """
    if len(v1.shape) == 1 and len(v2.shape) == 1:
        # Reshape for sklearn's cosine_similarity
        v1_reshaped = v1.reshape(1, -1)
        v2_reshaped = v2.reshape(1, -1)
        return float(sklearn_cosine_similarity(v1_reshaped, v2_reshaped)[0][0])
    else:
        return float(sklearn_cosine_similarity(v1, v2)[0][0])


def create_default_embedding_provider() -> EmbeddingProvider:
    """Create a default embedding provider based on available dependencies
    
    Returns:
        An instance of an embedding provider
    """
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        logger.info("Creating default embedding provider using HuggingFace")
        return HuggingFaceEmbeddingProvider()
    elif OPENAI_AVAILABLE:
        logger.info("Creating default embedding provider using OpenAI")
        return OpenAIEmbeddingProvider()
    else:
        logger.warning("No production embedding providers available, using mock provider")
        return MockEmbeddingProvider() 