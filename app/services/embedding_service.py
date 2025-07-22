"""Embedding service for text-to-vector conversion."""

import os
import asyncio
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Convert text to embedding vector."""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple texts to embedding vectors."""
        pass
    
    @abstractmethod
    def get_dimensions(self) -> int:
        """Get the dimensions of the embeddings produced by this provider."""
        pass



class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._dimensions = self._get_model_dimensions(model)
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
    
    def _get_model_dimensions(self, model: str) -> int:
        """Get dimensions for OpenAI models."""
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return model_dimensions.get(model, 1536)
    
    async def embed_text(self, text: str) -> List[float]:
        """Convert text to embedding vector using OpenAI."""
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=self.api_key)
            
            # Run the OpenAI call in a thread to avoid blocking
            response = await client.embeddings.create(
                model=self.model,
                input=text
            )
            
            return response.data[0].embedding
            
        except ImportError:
            raise RuntimeError("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            logger.error("OpenAI embedding failed", error=str(e), text_length=len(text))
            raise RuntimeError(f"OpenAI embedding failed: {e}")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple texts to embedding vectors using OpenAI."""
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=self.api_key)
            
            # OpenAI supports batch processing
            response = await client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            return [item.embedding for item in response.data]
            
        except ImportError:
            raise RuntimeError("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            logger.error("OpenAI batch embedding failed", error=str(e), texts_count=len(texts))
            raise RuntimeError(f"OpenAI batch embedding failed: {e}")
    
    def get_dimensions(self) -> int:
        """Get the dimensions of OpenAI embeddings."""
        return self._dimensions


class SentenceTransformersProvider(EmbeddingProvider):
    """Local sentence transformers embedding provider."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimensions = None
    
    async def _load_model(self):
        """Load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # Load in thread to avoid blocking
                loop = asyncio.get_event_loop()
                self._model = await loop.run_in_executor(
                    None, SentenceTransformer, self.model_name
                )
                
                # Get dimensions by encoding a test string
                test_embedding = await loop.run_in_executor(
                    None, self._model.encode, "test"
                )
                self._dimensions = len(test_embedding)
                
                logger.info("Loaded sentence transformer model", 
                           model=self.model_name, dimensions=self._dimensions)
                
            except ImportError as e:
                logger.error("sentence-transformers not installed", error=str(e))
                raise RuntimeError(
                    "sentence-transformers library not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                logger.error("Failed to load sentence transformer model", error=str(e), model=self.model_name)
                raise RuntimeError(
                    f"Failed to load sentence transformer model '{self.model_name}': {e}"
                )
    
    async def embed_text(self, text: str) -> List[float]:
        """Convert text to embedding vector using sentence transformers."""
        await self._load_model()
        
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, self._model.encode, text)
        return embedding.tolist()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple texts to embedding vectors."""
        await self._load_model()
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, texts)
        return [emb.tolist() for emb in embeddings]
    
    def get_dimensions(self) -> int:
        """Get the dimensions of the embeddings."""
        if self._dimensions is None:
            raise RuntimeError("Model not loaded yet. Call embed_text() first.")
        return self._dimensions


class EmbeddingService:
    """Service for text-to-vector embedding conversion."""
    
    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or self._create_default_provider()
        logger.info("Initialized embedding service", provider=type(self.provider).__name__)
    
    def _create_default_provider(self) -> EmbeddingProvider:
        """Create the default embedding provider based on configuration."""
        from app.config.settings import settings
        
        # Check if OpenAI API key is available
        openai_key = settings.embedding.openai_api_key or os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                logger.info("OpenAI API key found, attempting to use OpenAI embeddings")
                return OpenAIEmbeddingProvider(
                    api_key=openai_key,
                    model=settings.embedding.openai_model
                )
            except Exception as e:
                logger.warning("Failed to initialize OpenAI provider", error=str(e))
        else:
            logger.warning(
                "No OpenAI API key found. Set OPENAI_API_KEY or EMBEDDING_OPENAI_API_KEY "
                "environment variable to use OpenAI embeddings. Falling back to local sentence transformers."
            )
        
        # Fall back to sentence transformers
        try:
            logger.info("Attempting to use sentence transformers for embeddings")
            return SentenceTransformersProvider(
                model_name=settings.embedding.sentence_transformers_model
            )
        except Exception as e:
            logger.error("Failed to initialize sentence transformers provider", error=str(e))
            
            raise RuntimeError(
                "Text search functionality is not available. No embedding provider could be initialized.\n"
                "To enable text search, you must either:\n"
                "1. Set OPENAI_API_KEY environment variable to use OpenAI embeddings, or\n"
                "2. Install sentence-transformers: pip install sentence-transformers\n"
                f"Error details: {e}"
            )
    
    async def text_to_vector(self, text: str) -> List[float]:
        """Convert text to embedding vector."""
        from app.config.settings import settings
        
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty")
        
        if len(text) > settings.embedding.max_text_length:
            raise ValueError(f"Text length ({len(text)}) exceeds maximum ({settings.embedding.max_text_length})")
        
        try:
            embedding = await self.provider.embed_text(text)
            logger.debug("Generated embedding", text_length=len(text), vector_dim=len(embedding))
            return embedding
        except Exception as e:
            logger.error("Text to vector conversion failed", error=str(e), text_length=len(text))
            raise
    
    async def texts_to_vectors(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple texts to embedding vectors."""
        if not texts:
            return []
        
        # Filter empty texts
        non_empty_texts = [text.strip() for text in texts if text.strip()]
        if not non_empty_texts:
            raise ValueError("All texts are empty")
        
        try:
            embeddings = await self.provider.embed_texts(non_empty_texts)
            logger.debug("Generated batch embeddings", 
                        count=len(embeddings), vector_dim=len(embeddings[0]) if embeddings else 0)
            return embeddings
        except Exception as e:
            logger.error("Batch text to vector conversion failed", 
                        error=str(e), texts_count=len(texts))
            raise
    
    def get_embedding_dimensions(self) -> int:
        """Get the dimensions of embeddings produced by this service."""
        return self.provider.get_dimensions()
    
    async def validate_compatibility(self, dataset_dimensions: int) -> bool:
        """Check if the embedding dimensions match the dataset dimensions."""
        try:
            # For sentence transformers, we need to load the model first to get dimensions
            if hasattr(self.provider, '_load_model'):
                await self.provider._load_model()
            
            embedding_dims = self.get_embedding_dimensions()
            compatible = embedding_dims == dataset_dimensions
            
            if not compatible:
                logger.warning("Dimension mismatch", 
                              embedding_dims=embedding_dims, 
                              dataset_dims=dataset_dimensions)
            
            return compatible
        except Exception as e:
            logger.error("Failed to validate embedding compatibility", error=str(e))
            # If we can't validate, assume it's compatible and let the actual embedding call fail
            return True


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    
    return _embedding_service


async def close_embedding_service():
    """Close the embedding service and cleanup resources."""
    global _embedding_service
    
    if _embedding_service is not None:
        # Cleanup any resources if needed
        _embedding_service = None
        logger.info("Embedding service closed")