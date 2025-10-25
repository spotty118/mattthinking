"""
Supabase Storage Backend for ReasoningBank

This module provides a Supabase-based storage implementation replacing ChromaDB.
Uses pgvector for semantic similarity search and PostgreSQL for structured storage.

This adapter implements the StorageBackendInterface for compatibility with ReasoningBank.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import numpy as np

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("Supabase not available. Install with: pip install supabase")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

from storage_adapter import StorageBackendInterface
from schemas import MemoryItemSchema
from exceptions import (
    MemoryRetrievalError,
    MemoryStorageError,
    EmbeddingError
)


logger = logging.getLogger(__name__)


class SupabaseAdapter(StorageBackendInterface):
    """
    Supabase-based storage backend for ReasoningBank
    
    Features:
    - pgvector for semantic similarity search
    - PostgreSQL for structured data
    - Cloud-based, scalable storage
    - Built-in authentication and RLS
    """
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        traces_table: str = "reasoning_traces",
        memories_table: str = "memory_items"
    ):
        """
        Initialize Supabase storage backend
        
        Args:
            supabase_url: Supabase project URL (from env: SUPABASE_URL)
            supabase_key: Supabase API key (from env: SUPABASE_KEY)
            embedding_model: Sentence transformer model for embeddings
            traces_table: Name of traces table
            memories_table: Name of memories table
        
        Raises:
            ImportError: If Supabase or sentence-transformers not installed
            ValueError: If credentials not provided
            ConnectionError: If connection to Supabase fails
            EmbeddingError: If embedding model fails to load
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "Supabase not installed. Install with: pip install supabase>=2.0.0"
            )
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. Install with: pip install sentence-transformers>=2.2.0"
            )
        
        # Get credentials from environment or parameters
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase credentials required. Set SUPABASE_URL and SUPABASE_KEY "
                "environment variables or pass them as parameters."
            )
        
        # Initialize Supabase client
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {str(e)}")
        
        # Initialize embedding model
        try:
            self.embedder = SentenceTransformer(embedding_model)
            self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded: {embedding_model} (dim={self.embedding_dim})")
        except Exception as e:
            raise EmbeddingError(
                f"Failed to load embedding model: {embedding_model}",
                model_name=embedding_model,
                context={"error": str(e)}
            )
        
        self.traces_table = traces_table
        self.memories_table = memories_table
        
        # Verify tables exist
        self._verify_schema()
    
    def _verify_schema(self):
        """Verify that required tables and extensions exist"""
        try:
            # Check if pgvector extension is enabled
            result = self.client.rpc('check_pgvector_enabled').execute()
            
            # Simple table existence check
            self.client.table(self.traces_table).select("id", count="exact").limit(0).execute()
            self.client.table(self.memories_table).select("id", count="exact").limit(0).execute()
            
            logger.info("Schema verification passed")
        except Exception as e:
            logger.warning(f"Schema verification failed: {str(e)}")
            logger.warning("Run the SQL schema file (supabase_schema.sql) to create required tables")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")
    
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
        try:
            # Generate embedding for task
            task_embedding = self.generate_embedding(task)
            
            # Prepare trace data
            trace_data = {
                "id": trace_id,
                "task": task,
                "task_embedding": task_embedding,
                "trajectory": json.dumps(trajectory),
                "outcome": outcome,
                "metadata": json.dumps(metadata or {}),
                "timestamp": datetime.now().isoformat(),
                "num_memories": len(memory_items),
                "workspace_id": workspace_id
            }
            
            # Insert trace
            result = self.client.table(self.traces_table).insert(trace_data).execute()
            
            # Insert associated memory items
            for memory_item in memory_items:
                self.add_memory_item(trace_id, memory_item, workspace_id=workspace_id)
            
            logger.info(f"Stored trace {trace_id} with {len(memory_items)} memory items")
            return trace_id
            
        except Exception as e:
            raise MemoryStorageError(
                f"Failed to store trace {trace_id}",
                context={"error": str(e), "trace_id": trace_id}
            )
    
    def add_memory_item(self, trace_id: str, memory_item: Dict, workspace_id: Optional[str] = None) -> str:
        """
        Add a memory item to Supabase
        
        Args:
            trace_id: Parent trace ID
            memory_item: Memory item dictionary
            workspace_id: Optional workspace ID for isolation
            
        Returns:
            Inserted memory ID
        """
        try:
            # Generate embedding for memory content
            combined_text = f"{memory_item.get('title', '')}\n{memory_item.get('description', '')}\n{memory_item.get('content', '')}"
            content_embedding = self.generate_embedding(combined_text)
            
            # Prepare memory data
            memory_data = {
                "id": memory_item.get("id"),
                "trace_id": trace_id,
                "title": memory_item.get("title", ""),
                "description": memory_item.get("description", ""),
                "content": memory_item.get("content", ""),
                "content_embedding": content_embedding,
                "error_context": json.dumps(memory_item.get("error_context")) if memory_item.get("error_context") else None,
                "pattern_tags": memory_item.get("pattern_tags", []),
                "difficulty_level": memory_item.get("difficulty_level"),
                "domain_category": memory_item.get("domain_category"),
                "parent_memory_id": memory_item.get("parent_memory_id"),
                "evolution_stage": memory_item.get("evolution_stage", 0),
                "workspace_id": workspace_id
            }
            
            result = self.client.table(self.memories_table).insert(memory_data).execute()
            return memory_item.get("id")
            
        except Exception as e:
            raise MemoryStorageError(
                f"Failed to add memory item",
                context={"trace_id": trace_id, "error": str(e)}
            )
    
    def query_similar_traces(
        self,
        query_text: str,
        n_results: int = 5,
        outcome_filter: Optional[str] = None,
        domain_filter: Optional[str] = None
    ) -> Tuple[List[str], List[float]]:
        """
        Query similar traces using semantic similarity
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            outcome_filter: Filter by outcome ("success" or "failure")
            domain_filter: Filter by domain category
            
        Returns:
            Tuple of (trace_ids, distances)
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query_text)
            
            # Build RPC call for vector similarity search
            # This uses a custom PostgreSQL function for cosine similarity
            params = {
                "query_embedding": query_embedding,
                "match_count": n_results
            }
            
            if outcome_filter:
                params["outcome_filter"] = outcome_filter
            if domain_filter:
                params["domain_filter"] = domain_filter
            
            # Call stored procedure for semantic search
            result = self.client.rpc(
                "search_similar_traces",
                params
            ).execute()
            
            trace_ids = [row["id"] for row in result.data]
            distances = [row["distance"] for row in result.data]
            
            return trace_ids, distances
            
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to query traces: {str(e)}")
    
    def query_similar_memories(
        self,
        query_text: str,
        n_results: int = 5,
        include_errors: bool = True,
        domain_filter: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> List[MemoryItemSchema]:
        """
        Query similar memory items using semantic similarity
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            include_errors: Include memories with error context
            domain_filter: Filter by domain category
            workspace_id: Optional workspace ID for filtering
            
        Returns:
            List of MemoryItemSchema objects with similarity scores
        
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query_text)
            
            params = {
                "query_embedding": query_embedding,
                "match_count": n_results * 2,  # Get more for filtering
                "workspace_filter": workspace_id
            }
            
            if domain_filter:
                params["domain_filter"] = domain_filter
            
            # Call stored procedure for semantic search
            result = self.client.rpc(
                "search_similar_memories",
                params
            ).execute()
            
            memories = []
            for row in result.data:
                # Parse error context if present
                error_context = None
                if row.get("error_context"):
                    try:
                        error_context = json.loads(row["error_context"]) if isinstance(row["error_context"], str) else row["error_context"]
                    except json.JSONDecodeError:
                        pass
                
                # Filter out error memories if requested
                if not include_errors and error_context:
                    continue
                
                # Create MemoryItemSchema
                memory_data = {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "content": row["content"],
                    "error_context": error_context,
                    "pattern_tags": row.get("pattern_tags", []),
                    "difficulty_level": row.get("difficulty_level"),
                    "domain_category": row.get("domain_category"),
                }
                
                # Add optional fields if present
                if row.get("parent_memory_id"):
                    memory_data["parent_memory_id"] = row["parent_memory_id"]
                if row.get("derived_from"):
                    memory_data["derived_from"] = row["derived_from"]
                if row.get("evolution_stage") is not None:
                    memory_data["evolution_stage"] = row["evolution_stage"]
                
                memory = MemoryItemSchema(**memory_data)
                memories.append(memory)
                
                if len(memories) >= n_results:
                    break
            
            logger.info(f"Retrieved {len(memories)} memories for query: {query_text[:50]}...")
            return memories
            
        except Exception as e:
            raise MemoryRetrievalError(
                "Failed to query similar memories",
                query=query_text,
                context={"error": str(e)}
            )
    
    def get_trace(self, trace_id: str) -> Optional[Dict]:
        """
        Retrieve a trace by ID
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            Trace dictionary or None if not found
        """
        try:
            result = self.client.table(self.traces_table).select("*").eq("id", trace_id).execute()
            
            if not result.data:
                return None
            
            trace = result.data[0]
            trace["trajectory"] = json.loads(trace["trajectory"])
            trace["metadata"] = json.loads(trace["metadata"])
            
            # Fetch associated memory items
            memories_result = self.client.table(self.memories_table).select("*").eq("trace_id", trace_id).execute()
            trace["memory_items"] = memories_result.data
            
            return trace
            
        except Exception as e:
            raise MemoryRetrievalError(f"Failed to get trace: {str(e)}")
    
    def count_traces(self, outcome: Optional[str] = None) -> int:
        """
        Count traces in database
        
        Args:
            outcome: Optional filter by outcome
            
        Returns:
            Total count
        """
        try:
            query = self.client.table(self.traces_table).select("id", count="exact")
            
            if outcome:
                query = query.eq("outcome", outcome)
            
            result = query.execute()
            return result.count
            
        except Exception as e:
            logger.error(f"Failed to count traces: {str(e)}")
            return 0
    
    def count_memories(self, has_error_context: Optional[bool] = None) -> int:
        """
        Count memory items
        
        Args:
            has_error_context: Optional filter by error context presence
            
        Returns:
            Total count
        """
        try:
            query = self.client.table(self.memories_table).select("id", count="exact")
            
            if has_error_context is not None:
                if has_error_context:
                    query = query.not_.is_("error_context", "null")
                else:
                    query = query.is_("error_context", "null")
            
            result = query.execute()
            return result.count
            
        except Exception as e:
            logger.error(f"Failed to count memories: {str(e)}")
            return 0
    
    def get_statistics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Args:
            workspace_id: Optional workspace filter
        
        Returns:
            Dictionary with statistics (total_traces, success_rate, etc.)
        """
        try:
            # Build base query
            traces_query = self.client.table(self.traces_table).select("*", count="exact")
            memories_query = self.client.table(self.memories_table).select("*", count="exact")
            
            # Apply workspace filter if provided
            if workspace_id:
                traces_query = traces_query.eq("workspace_id", workspace_id)
                memories_query = memories_query.eq("workspace_id", workspace_id)
            
            # Get counts
            total_traces_result = traces_query.execute()
            total_traces = total_traces_result.count or 0
            
            success_traces_result = self.client.table(self.traces_table).select("*", count="exact").eq("outcome", "success")
            if workspace_id:
                success_traces_result = success_traces_result.eq("workspace_id", workspace_id)
            success_traces = success_traces_result.execute().count or 0
            
            failure_traces_result = self.client.table(self.traces_table).select("*", count="exact").eq("outcome", "failure")
            if workspace_id:
                failure_traces_result = failure_traces_result.eq("workspace_id", workspace_id)
            failure_traces = failure_traces_result.execute().count or 0
            
            total_memories_result = memories_query.execute()
            total_memories = total_memories_result.count or 0
            
            # Count memories with error context
            error_memories_query = self.client.table(self.memories_table).select("*", count="exact").not_.is_("error_context", "null")
            if workspace_id:
                error_memories_query = error_memories_query.eq("workspace_id", workspace_id)
            memories_with_errors = error_memories_query.execute().count or 0
            
            # Calculate success rate
            success_rate = (success_traces / total_traces * 100) if total_traces > 0 else 0.0
            
            stats = {
                "total_traces": total_traces,
                "success_traces": success_traces,
                "failure_traces": failure_traces,
                "total_memories": total_memories,
                "memories_with_errors": memories_with_errors,
                "success_rate": round(success_rate, 2),
                "avg_evolution_stage": 0.0,  # Could be computed if needed
                "difficulty_distribution": {},
                "domain_distribution": {},
                "pattern_tag_frequency": {}
            }
            
            logger.info(f"Retrieved statistics: {total_traces} traces, {total_memories} memories")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
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
    
    def delete_old_traces(
        self,
        retention_days: int,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete traces and memories older than retention_days
        
        Args:
            retention_days: Number of days to retain traces
            workspace_id: Optional workspace filter
        
        Returns:
            Dictionary with deletion statistics
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_iso = cutoff_date.isoformat()
            
            logger.info(
                f"Starting cleanup of traces older than {retention_days} days "
                f"(cutoff: {cutoff_iso})"
            )
            
            # Build query to find old traces
            query = self.client.table(self.traces_table).select("id")
            
            if workspace_id:
                query = query.eq("workspace_id", workspace_id)
            
            query = query.lt("timestamp", cutoff_iso)
            
            # Get traces to delete
            old_traces_result = query.execute()
            old_trace_ids = [row["id"] for row in old_traces_result.data]
            
            if not old_trace_ids:
                logger.info("No old traces found to delete")
                return {
                    "deleted_traces_count": 0,
                    "deleted_memories_count": 0,
                    "freed_space_mb": 0.0,
                    "retention_cutoff": cutoff_iso
                }
            
            # Delete associated memories first
            deleted_memories = 0
            for trace_id in old_trace_ids:
                memories_result = self.client.table(self.memories_table).delete().eq("trace_id", trace_id).execute()
                if memories_result.data:
                    deleted_memories += len(memories_result.data)
            
            # Delete traces
            deleted_traces = 0
            for trace_id in old_trace_ids:
                self.client.table(self.traces_table).delete().eq("id", trace_id).execute()
                deleted_traces += 1
            
            # Estimate freed space
            freed_space_mb = (deleted_memories * 50) / 1024.0
            
            result = {
                "deleted_traces_count": deleted_traces,
                "deleted_memories_count": deleted_memories,
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
            from exceptions import MemoryStorageError
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
        
        Args:
            workspace_id: Workspace identifier
        
        Returns:
            Dictionary with deletion statistics
        """
        try:
            logger.info(f"Deleting all data for workspace: {workspace_id}")
            
            # Get all traces for this workspace
            traces_result = self.client.table(self.traces_table).select("id").eq("workspace_id", workspace_id).execute()
            
            if not traces_result.data:
                logger.info(f"No data found for workspace {workspace_id}")
                return {
                    "workspace_id": workspace_id,
                    "deleted_traces": 0,
                    "deleted_memories": 0,
                    "deletion_timestamp": datetime.now().isoformat()
                }
            
            trace_ids = [row["id"] for row in traces_result.data]
            
            # Delete all memories for these traces
            deleted_memories = 0
            for trace_id in trace_ids:
                memories_result = self.client.table(self.memories_table).delete().eq("trace_id", trace_id).execute()
                if memories_result.data:
                    deleted_memories += len(memories_result.data)
            
            # Delete all traces
            deleted_traces = 0
            for trace_id in trace_ids:
                self.client.table(self.traces_table).delete().eq("id", trace_id).execute()
                deleted_traces += 1
            
            result = {
                "workspace_id": workspace_id,
                "deleted_traces": deleted_traces,
                "deleted_memories": deleted_memories,
                "deletion_timestamp": datetime.now().isoformat()
            }
            
            logger.info(
                f"Workspace deletion complete: {result['deleted_traces']} traces, "
                f"{result['deleted_memories']} memories deleted"
            )
            
            return result
            
        except Exception as e:
            from exceptions import MemoryStorageError
            raise MemoryStorageError(
                f"Failed to delete workspace {workspace_id}",
                context={"workspace_id": workspace_id, "error": str(e)}
            )
