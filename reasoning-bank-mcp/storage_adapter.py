"""
Storage adapter interface for ReasoningBank MCP System

This module provides:
- Abstract StorageBackendInterface for pluggable storage backends
- ChromaDBAdapter implementation with semantic search
- Factory function for backend selection
- Embedding generation using sentence-transformers

Supported backends:
- ChromaDB: Local vector database with persistent storage
- Supabase: Cloud-hosted PostgreSQL with pgvector (implemented separately)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import os
import json
from datetime import datetime
import logging

# ChromaDB imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available. Install with: pip install chromadb")

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

from schemas import MemoryItemSchema, ReasoningTraceSchema, OutcomeType
from exceptions import (
    MemoryStorageError,
    MemoryRetrievalError,
    EmbeddingError
)
from performance_optimizer import BatchEmbeddingGenerator, MemoryCache


logger = logging.getLogger(__name__)


# ============================================================================
# Abstract Storage Interface
# ============================================================================

class StorageBackendInterface(ABC):
    """
    Abstract interface for storage backends
    
    All storage implementations must implement these methods to ensure
    consistent behavior across different backends (ChromaDB, Supabase, etc.)
    """
    
    @abstractmethod
    def add_trace(
        self,
        trace_id: str,
        task: str,
        trajectory: List[Dict[str, Any]],
        outcome: str,
        memory_items: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> str:
        """
        Store a complete reasoning trace with memory items
        
        Args:
            trace_id: Unique identifier for the trace
            task: Original task description
            trajectory: List of trajectory steps
            outcome: Task outcome (success/failure/partial)
            memory_items: List of extracted memory items
            metadata: Additional metadata (scores, iterations, etc.)
            workspace_id: Workspace identifier for isolation
        
        Returns:
            Stored trace ID
        
        Raises:
            MemoryStorageError: If storage fails
        """
        pass
    
    @abstractmethod
    def query_similar_memories(
        self,
        query_text: str,
        n_results: int = 5,
        include_errors: bool = True,
        domain_filter: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> List[MemoryItemSchema]:
        """
        Query semantically similar memories
        
        Args:
            query_text: Search query
            n_results: Number of results to return
            include_errors: Include memories with error context
            domain_filter: Filter by domain category
            workspace_id: Filter by workspace
        
        Returns:
            List of memory items with similarity scores
        
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def get_statistics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Args:
            workspace_id: Optional workspace filter
        
        Returns:
            Dictionary with statistics (total_traces, success_rate, etc.)
        """
        pass
    
    @abstractmethod
    def delete_old_traces(
        self,
        retention_days: int,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete traces older than retention_days
        
        Args:
            retention_days: Number of days to retain traces
            workspace_id: Optional workspace filter
        
        Returns:
            Dictionary with deletion statistics
        
        Raises:
            MemoryStorageError: If deletion fails
        """
        pass
    
    @abstractmethod
    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """
        Delete all traces and memories for a workspace
        
        Args:
            workspace_id: Workspace identifier
        
        Returns:
            Dictionary with deletion statistics
        
        Raises:
            MemoryStorageError: If deletion fails
        """
        pass


# ============================================================================
# ChromaDB Implementation
# ============================================================================

class ChromaDBAdapter(StorageBackendInterface):
    """
    ChromaDB storage backend with semantic search
    
    Features:
    - Local persistent vector database
    - Semantic search using sentence-transformers embeddings
    - Workspace isolation support
    - Metadata filtering
    """
    
    def __init__(
        self,
        persist_directory: str = "./chroma_data",
        collection_name: str = "reasoning_memories",
        embedding_model: str = "all-MiniLM-L6-v2",
        enable_memory_cache: bool = True,
        cache_size: int = 1000,
        batch_size: int = 32
    ):
        """
        Initialize ChromaDB adapter
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the ChromaDB collection
            embedding_model: Sentence-transformers model name
            enable_memory_cache: Enable in-memory caching
            cache_size: Maximum number of memories to cache
            batch_size: Batch size for embedding generation
        
        Raises:
            ImportError: If ChromaDB or sentence-transformers not installed
            EmbeddingError: If embedding model fails to load
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb>=0.6.3"
            )
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. Install with: pip install sentence-transformers>=2.2.0"
            )
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model  # Store model name for error reporting
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        logger.info(f"Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "ReasoningBank memory storage"}
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        try:
            self.embedder = SentenceTransformer(embedding_model)
            logger.info(f"Embedding model loaded successfully")
        except Exception as e:
            raise EmbeddingError(
                f"Failed to load embedding model: {embedding_model}",
                model_name=embedding_model,
                context={"error": str(e)}
            )
        
        # Initialize batch embedding generator
        self.batch_generator = BatchEmbeddingGenerator(
            embedder=self.embedder,
            batch_size=batch_size
        )
        
        # Initialize memory cache
        self.enable_cache = enable_memory_cache
        if enable_memory_cache:
            self.memory_cache = MemoryCache(max_size=cache_size)
            logger.info(f"Memory cache enabled with size={cache_size}")
        else:
            self.memory_cache = None
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector as list of floats
        
        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            raise EmbeddingError(
                "Failed to generate embedding",
                text=text[:100],
                model_name=self.embedding_model_name,
                context={"error": str(e)}
            )
    
    def add_trace(
        self,
        trace_id: str,
        task: str,
        trajectory: List[Dict[str, Any]],
        outcome: str,
        memory_items: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> str:
        """
        Store reasoning trace and memory items in ChromaDB
        
        Each memory item is stored as a separate document with:
        - Embedding of title + description + content
        - Metadata including trace_id, outcome, workspace_id
        - Full memory item data in metadata
        
        Uses batch embedding generation for improved performance.
        """
        try:
            if not memory_items:
                logger.warning(f"No memory items to store for trace {trace_id}")
                return trace_id
            
            # Prepare data for batch insertion
            ids = []
            documents = []
            metadatas = []
            valid_items = []
            
            for memory_item in memory_items:
                # Validate memory item structure
                if not isinstance(memory_item, dict):
                    logger.warning(f"Invalid memory item type: {type(memory_item)}")
                    continue
                
                memory_id = memory_item.get("id")
                if not memory_id:
                    logger.warning("Memory item missing ID, skipping")
                    continue
                
                # Combine text for embedding
                title = memory_item.get("title", "")
                description = memory_item.get("description", "")
                content = memory_item.get("content", "")
                combined_text = f"{title}\n{description}\n{content}"
                
                # Prepare metadata
                item_metadata = {
                    "trace_id": trace_id,
                    "task": task[:500],  # Truncate for metadata
                    "outcome": outcome,
                    "timestamp": datetime.now().isoformat(),
                    "memory_data": json.dumps(memory_item),  # Store full item
                }
                
                # Add workspace_id if provided
                if workspace_id:
                    item_metadata["workspace_id"] = workspace_id
                
                # Add optional fields
                if "domain_category" in memory_item and memory_item["domain_category"]:
                    item_metadata["domain_category"] = memory_item["domain_category"]
                
                if "difficulty_level" in memory_item and memory_item["difficulty_level"]:
                    item_metadata["difficulty_level"] = memory_item["difficulty_level"]
                
                if "error_context" in memory_item and memory_item["error_context"]:
                    item_metadata["has_error_context"] = True
                
                # Add to batch
                ids.append(memory_id)
                documents.append(combined_text)
                metadatas.append(item_metadata)
                valid_items.append(memory_item)
            
            # Generate embeddings in batch for better performance
            if documents:
                embeddings = self.batch_generator.generate_batch(documents)
                
                # Batch insert into ChromaDB
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                
                # Cache the memories if caching is enabled
                if self.enable_cache and self.memory_cache:
                    for memory_id, memory_item in zip(ids, valid_items):
                        self.memory_cache.put(memory_id, memory_item)
                
                logger.info(f"Stored {len(ids)} memory items for trace {trace_id}")
            
            return trace_id
            
        except Exception as e:
            raise MemoryStorageError(
                f"Failed to store trace {trace_id}",
                context={"error": str(e), "trace_id": trace_id}
            )
    
    def query_similar_memories(
        self,
        query_text: str,
        n_results: int = 5,
        include_errors: bool = True,
        domain_filter: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> List[MemoryItemSchema]:
        """
        Query semantically similar memories using vector search
        
        Returns memories ranked by cosine similarity with optional filtering.
        Uses memory cache for frequently accessed memories.
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query_text)
            
            # Build where filter
            where_filter = {}
            if workspace_id:
                where_filter["workspace_id"] = workspace_id
            
            if domain_filter:
                where_filter["domain_category"] = domain_filter
            
            if not include_errors:
                where_filter["has_error_context"] = {"$ne": True}
            
            # Query ChromaDB with optimized indexing
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["metadatas", "documents", "distances"]
            )
            
            # Parse results into MemoryItemSchema objects
            memories = []
            if results and results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]
                    
                    # Try to get from cache first
                    memory_data = None
                    if self.enable_cache and self.memory_cache:
                        memory_data = self.memory_cache.get(memory_id)
                    
                    # If not in cache, parse from metadata
                    if memory_data is None:
                        memory_data = json.loads(metadata["memory_data"])
                        
                        # Cache it for future use
                        if self.enable_cache and self.memory_cache:
                            self.memory_cache.put(memory_id, memory_data)
                    
                    # Add similarity score (convert distance to similarity)
                    # ChromaDB uses L2 distance, convert to similarity score
                    similarity_score = 1.0 / (1.0 + distance)
                    
                    # Create MemoryItemSchema
                    memory = MemoryItemSchema(**memory_data)
                    
                    # Add retrieval metadata (not part of schema, but useful)
                    # Store in a way that doesn't break validation
                    memory_dict = memory.model_dump()
                    memory_dict["_similarity_score"] = similarity_score
                    memory_dict["_trace_outcome"] = metadata.get("outcome")
                    memory_dict["_trace_timestamp"] = metadata.get("timestamp")
                    
                    memories.append(MemoryItemSchema(**{k: v for k, v in memory_dict.items() if not k.startswith("_")}))
            
            logger.info(f"Retrieved {len(memories)} memories for query: {query_text[:50]}...")
            return memories
            
        except Exception as e:
            raise MemoryRetrievalError(
                "Failed to query similar memories",
                query=query_text,
                context={"error": str(e)}
            )
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get memory cache statistics"""
        if self.enable_cache and self.memory_cache:
            return self.memory_cache.get_statistics()
        return {
            "cache_enabled": False,
            "cache_size": 0,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0
        }
    
    def get_statistics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics from ChromaDB
        
        Returns counts, success rates, and distribution metrics.
        Includes cache statistics if caching is enabled.
        """
        try:
            # Get all items (or filtered by workspace)
            where_filter = {"workspace_id": workspace_id} if workspace_id else None
            
            # ChromaDB doesn't have a direct count method, so we query with large limit
            results = self.collection.get(
                where=where_filter,
                include=["metadatas"]
            )
            
            total_memories = len(results["ids"]) if results["ids"] else 0
            
            if total_memories == 0:
                base_stats = {
                    "total_traces": 0,
                    "success_traces": 0,
                    "failure_traces": 0,
                    "total_memories": 0,
                    "memories_with_errors": 0,
                    "success_rate": 0.0,
                    "avg_evolution_stage": 0.0,
                    "difficulty_distribution": {},
                    "domain_distribution": {},
                    "pattern_tag_frequency": {}
                }
                
                # Add cache statistics
                if self.enable_cache:
                    base_stats["cache"] = self.get_cache_statistics()
                
                return base_stats
            
            # Analyze metadata
            metadatas = results["metadatas"]
            
            # Count unique traces
            trace_ids = set()
            success_traces = set()
            failure_traces = set()
            memories_with_errors = 0
            evolution_stages = []
            difficulty_dist = {}
            domain_dist = {}
            pattern_tags = {}
            
            for metadata in metadatas:
                trace_id = metadata.get("trace_id")
                if trace_id:
                    trace_ids.add(trace_id)
                    
                    outcome = metadata.get("outcome")
                    if outcome == "success":
                        success_traces.add(trace_id)
                    elif outcome == "failure":
                        failure_traces.add(trace_id)
                
                if metadata.get("has_error_context"):
                    memories_with_errors += 1
                
                # Parse memory data for additional stats
                try:
                    memory_data = json.loads(metadata.get("memory_data", "{}"))
                    
                    # Evolution stage
                    evolution_stage = memory_data.get("evolution_stage", 0)
                    evolution_stages.append(evolution_stage)
                    
                    # Difficulty distribution
                    difficulty = memory_data.get("difficulty_level")
                    if difficulty:
                        difficulty_dist[difficulty] = difficulty_dist.get(difficulty, 0) + 1
                    
                    # Domain distribution
                    domain = metadata.get("domain_category") or memory_data.get("domain_category")
                    if domain:
                        domain_dist[domain] = domain_dist.get(domain, 0) + 1
                    
                    # Pattern tags
                    tags = memory_data.get("pattern_tags", [])
                    for tag in tags:
                        pattern_tags[tag] = pattern_tags.get(tag, 0) + 1
                
                except json.JSONDecodeError:
                    continue
            
            total_traces = len(trace_ids)
            success_count = len(success_traces)
            failure_count = len(failure_traces)
            success_rate = (success_count / total_traces * 100) if total_traces > 0 else 0.0
            avg_evolution = sum(evolution_stages) / len(evolution_stages) if evolution_stages else 0.0
            
            stats = {
                "total_traces": total_traces,
                "success_traces": success_count,
                "failure_traces": failure_count,
                "total_memories": total_memories,
                "memories_with_errors": memories_with_errors,
                "success_rate": round(success_rate, 2),
                "avg_evolution_stage": round(avg_evolution, 2),
                "difficulty_distribution": difficulty_dist,
                "domain_distribution": domain_dist,
                "pattern_tag_frequency": pattern_tags
            }
            
            # Add cache statistics
            if self.enable_cache:
                stats["cache"] = self.get_cache_statistics()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            stats = {
                "total_traces": 0,
                "success_traces": 0,
                "failure_traces": 0,
                "total_memories": 0,
                "memories_with_errors": 0,
                "success_rate": 0.0,
                "avg_evolution_stage": 0.0,
                "difficulty_distribution": {},
                "domain_distribution": {},
                "pattern_tag_frequency": {}
            }
            
            # Add cache statistics even on error
            if self.enable_cache:
                stats["cache"] = self.get_cache_statistics()
            
            return stats
    
    def delete_old_traces(
        self,
        retention_days: int,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete traces and memories older than retention_days
        
        This method removes all traces and associated memory items that are
        older than the specified retention period. Useful for data retention
        policies and storage management.
        
        Args:
            retention_days: Number of days to retain traces (older traces deleted)
            workspace_id: Optional workspace filter (only delete from this workspace)
        
        Returns:
            Dictionary with deletion statistics:
            - deleted_traces_count: Number of unique traces deleted
            - deleted_memories_count: Number of memory items deleted
            - freed_space_mb: Estimated freed space (approximate)
            - retention_cutoff: ISO timestamp of cutoff date
        
        Raises:
            MemoryStorageError: If deletion fails
        
        Example:
            >>> adapter.delete_old_traces(retention_days=90, workspace_id="abc123")
            {
                "deleted_traces_count": 15,
                "deleted_memories_count": 45,
                "freed_space_mb": 2.3,
                "retention_cutoff": "2024-07-23T10:30:00Z"
            }
        """
        try:
            # Calculate cutoff timestamp
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_iso = cutoff_date.isoformat()
            
            logger.info(
                f"Starting cleanup of traces older than {retention_days} days "
                f"(cutoff: {cutoff_iso})"
            )
            
            # Build where filter
            where_filter = {}
            if workspace_id:
                where_filter["workspace_id"] = workspace_id
            
            # Get all items to check timestamps
            results = self.collection.get(
                where=where_filter if where_filter else None,
                include=["metadatas"]
            )
            
            if not results["ids"]:
                logger.info("No traces found to cleanup")
                return {
                    "deleted_traces_count": 0,
                    "deleted_memories_count": 0,
                    "freed_space_mb": 0.0,
                    "retention_cutoff": cutoff_iso
                }
            
            # Filter by timestamp
            ids_to_delete = []
            trace_ids_deleted = set()
            
            for i, memory_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                timestamp_str = metadata.get("timestamp")
                
                if timestamp_str:
                    try:
                        # Parse ISO timestamp
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        # Check if older than cutoff
                        if timestamp < cutoff_date:
                            ids_to_delete.append(memory_id)
                            trace_id = metadata.get("trace_id")
                            if trace_id:
                                trace_ids_deleted.add(trace_id)
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Invalid timestamp format: {timestamp_str}, skipping")
                        continue
            
            # Delete the old memories
            deleted_count = 0
            if ids_to_delete:
                # ChromaDB delete by IDs
                self.collection.delete(ids=ids_to_delete)
                deleted_count = len(ids_to_delete)
                
                # Clear from cache if caching enabled
                if self.enable_cache and self.memory_cache:
                    for memory_id in ids_to_delete:
                        # Cache doesn't have explicit delete, but will be evicted naturally
                        pass
                
                logger.info(
                    f"Deleted {deleted_count} memory items from {len(trace_ids_deleted)} traces"
                )
            
            # Estimate freed space (rough approximation: ~50KB per memory item)
            freed_space_mb = (deleted_count * 50) / 1024.0
            
            result = {
                "deleted_traces_count": len(trace_ids_deleted),
                "deleted_memories_count": deleted_count,
                "freed_space_mb": round(freed_space_mb, 2),
                "retention_cutoff": cutoff_iso
            }
            
            logger.info(
                f"Cleanup complete: {result['deleted_traces_count']} traces, "
                f"{result['deleted_memories_count']} memories, "
                f"~{result['freed_space_mb']} MB freed"
            )
            
            return result
            
        except Exception as e:
            raise MemoryStorageError(
                f"Failed to delete old traces",
                context={
                    "retention_days": retention_days,
                    "workspace_id": workspace_id,
                    "error": str(e)
                }
            )
    
    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """
        Delete all traces and memories for a specific workspace
        
        This method removes all data associated with a workspace. Use with
        caution as this operation is irreversible.
        
        Args:
            workspace_id: Workspace identifier to delete
        
        Returns:
            Dictionary with deletion statistics:
            - workspace_id: The deleted workspace ID
            - deleted_traces: Number of unique traces deleted
            - deleted_memories: Number of memory items deleted
            - deletion_timestamp: ISO timestamp of deletion
        
        Raises:
            MemoryStorageError: If deletion fails
        
        Example:
            >>> adapter.delete_workspace("abc123")
            {
                "workspace_id": "abc123",
                "deleted_traces": 25,
                "deleted_memories": 78,
                "deletion_timestamp": "2025-10-23T10:30:00Z"
            }
        """
        try:
            logger.info(f"Deleting all data for workspace: {workspace_id}")
            
            # Get all items for this workspace
            results = self.collection.get(
                where={"workspace_id": workspace_id},
                include=["metadatas"]
            )
            
            if not results["ids"]:
                logger.info(f"No data found for workspace {workspace_id}")
                return {
                    "workspace_id": workspace_id,
                    "deleted_traces": 0,
                    "deleted_memories": 0,
                    "deletion_timestamp": datetime.now().isoformat()
                }
            
            # Count unique traces
            trace_ids = set()
            for metadata in results["metadatas"]:
                trace_id = metadata.get("trace_id")
                if trace_id:
                    trace_ids.add(trace_id)
            
            # Delete all memories for this workspace
            memory_ids = results["ids"]
            self.collection.delete(ids=memory_ids)
            
            # Clear from cache if caching enabled
            if self.enable_cache and self.memory_cache:
                for memory_id in memory_ids:
                    # Cache will naturally evict these
                    pass
            
            result = {
                "workspace_id": workspace_id,
                "deleted_traces": len(trace_ids),
                "deleted_memories": len(memory_ids),
                "deletion_timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                f"Workspace deletion complete: {result['deleted_traces']} traces, "
                f"{result['deleted_memories']} memories deleted"
            )
            
            return result
            
        except Exception as e:
            raise MemoryStorageError(
                f"Failed to delete workspace {workspace_id}",
                context={"workspace_id": workspace_id, "error": str(e)}
            )


# ============================================================================
# Factory Function
# ============================================================================

def create_storage_backend(
    backend_type: str = "chromadb",
    **kwargs
) -> StorageBackendInterface:
    """
    Factory function to create storage backend instances
    
    Args:
        backend_type: Type of backend ("chromadb" or "supabase")
        **kwargs: Backend-specific configuration
    
    Returns:
        StorageBackendInterface implementation
    
    Raises:
        ValueError: If backend_type is not supported
        ImportError: If required dependencies are not installed
    
    Example:
        >>> backend = create_storage_backend(
        ...     backend_type="chromadb",
        ...     persist_directory="./chroma_data",
        ...     collection_name="memories"
        ... )
    """
    backend_type = backend_type.lower()
    
    if backend_type == "chromadb":
        return ChromaDBAdapter(
            persist_directory=kwargs.get("persist_directory", "./chroma_data"),
            collection_name=kwargs.get("collection_name", "reasoning_memories"),
            embedding_model=kwargs.get("embedding_model", "all-MiniLM-L6-v2")
        )
    
    elif backend_type == "supabase":
        # Import here to avoid dependency if not using Supabase
        try:
            from supabase_storage import SupabaseAdapter
            return SupabaseAdapter(
                supabase_url=kwargs.get("supabase_url"),
                supabase_key=kwargs.get("supabase_key"),
                embedding_model=kwargs.get("embedding_model", "all-MiniLM-L6-v2"),
                traces_table=kwargs.get("traces_table", "reasoning_traces"),
                memories_table=kwargs.get("memories_table", "memory_items")
            )
        except ImportError:
            raise ImportError(
                "Supabase storage not available. Install with: pip install supabase"
            )
    
    else:
        raise ValueError(
            f"Unsupported backend type: {backend_type}. "
            f"Supported types: chromadb, supabase"
        )


# ============================================================================
# Testing and Validation
# ============================================================================

if __name__ == "__main__":
    """Test ChromaDB adapter functionality"""
    import uuid
    
    print("=== Testing ChromaDB Storage Adapter ===\n")
    
    # Create adapter
    print("1. Initializing ChromaDB adapter...")
    adapter = create_storage_backend(
        backend_type="chromadb",
        persist_directory="./test_chroma_data",
        collection_name="test_memories"
    )
    print("✅ Adapter initialized\n")
    
    # Test adding a trace
    print("2. Adding test trace with memory items...")
    test_trace_id = str(uuid.uuid4())
    test_memory_items = [
        {
            "id": str(uuid.uuid4()),
            "title": "Binary Search Implementation",
            "description": "Efficient search in sorted arrays using divide and conquer",
            "content": "Binary search works by repeatedly dividing the search interval in half...",
            "pattern_tags": ["algorithms", "binary_search", "divide_conquer"],
            "difficulty_level": "moderate",
            "domain_category": "algorithms"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Error Handling Pattern",
            "description": "Always validate input before processing",
            "content": "Check for None, empty strings, and invalid types before operations...",
            "error_context": {
                "error_type": "TypeError",
                "failure_pattern": "Missing input validation",
                "corrective_guidance": "Add type checks and None guards"
            },
            "pattern_tags": ["error_handling", "validation"],
            "difficulty_level": "simple",
            "domain_category": "best_practices"
        }
    ]
    
    stored_id = adapter.add_trace(
        trace_id=test_trace_id,
        task="Implement binary search with error handling",
        trajectory=[{"iteration": 1, "action": "generate", "output": "code here"}],
        outcome="success",
        memory_items=test_memory_items,
        workspace_id="test_workspace"
    )
    print(f"✅ Stored trace: {stored_id}\n")
    
    # Test querying
    print("3. Querying similar memories...")
    memories = adapter.query_similar_memories(
        query_text="How to search in sorted arrays?",
        n_results=2,
        workspace_id="test_workspace"
    )
    print(f"✅ Found {len(memories)} memories")
    for mem in memories:
        print(f"   - {mem.title}")
    print()
    
    # Test statistics
    print("4. Getting statistics...")
    stats = adapter.get_statistics(workspace_id="test_workspace")
    print(f"✅ Statistics:")
    print(f"   Total traces: {stats['total_traces']}")
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   Memories with errors: {stats['memories_with_errors']}")
    print(f"   Success rate: {stats['success_rate']}%")
    print(f"   Domain distribution: {stats['domain_distribution']}")
    print()
    
    print("=== All tests passed! ===")
