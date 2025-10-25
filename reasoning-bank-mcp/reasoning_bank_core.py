"""
Core ReasoningBank memory management system

This module implements the central ReasoningBank class that manages:
- Memory storage and retrieval with semantic search
- Reasoning trace persistence
- Solution judging and quality evaluation
- Learning extraction from LLM responses
- Memory genealogy tracking
- Composite scoring (similarity + recency + error context)

Requirements addressed: 1.1-1.5, 8.1-8.5, 11.1-11.2, 13.1-13.5, 15.1-15.5
"""

import json
import logging
import math
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from schemas import (
    MemoryItemSchema,
    ReasoningTraceSchema,
    TrajectoryStep,
    OutcomeType,
    DifficultyLevel
)
from storage_adapter import StorageBackendInterface
from cached_llm_client import CachedLLMClient
from workspace_manager import WorkspaceManager
from exceptions import (
    MemoryStorageError,
    MemoryRetrievalError,
    MemoryValidationError,
    JSONParseError,
    LLMGenerationError
)


logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MemoryItem:
    """
    Memory item with all required and optional fields
    
    This is a convenience wrapper around MemoryItemSchema for easier
    manipulation in code. Can be converted to/from MemoryItemSchema.
    """
    id: str
    title: str
    description: str
    content: str
    error_context: Optional[Dict[str, Any]] = None
    parent_memory_id: Optional[str] = None
    derived_from: Optional[List[str]] = None
    evolution_stage: int = 0
    pattern_tags: Optional[List[str]] = None
    difficulty_level: Optional[str] = None
    domain_category: Optional[str] = None
    similarity_score: Optional[float] = None
    recency_score: Optional[float] = None
    composite_score: Optional[float] = None
    trace_outcome: Optional[str] = None
    trace_timestamp: Optional[str] = None
    
    def to_schema(self) -> MemoryItemSchema:
        """Convert to Pydantic schema for validation"""
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
        }
        
        # Add optional fields if present
        if self.error_context:
            data["error_context"] = self.error_context
        if self.parent_memory_id:
            data["parent_memory_id"] = self.parent_memory_id
        if self.derived_from:
            data["derived_from"] = self.derived_from
        if self.evolution_stage:
            data["evolution_stage"] = self.evolution_stage
        if self.pattern_tags:
            data["pattern_tags"] = self.pattern_tags
        if self.difficulty_level:
            data["difficulty_level"] = self.difficulty_level
        if self.domain_category:
            data["domain_category"] = self.domain_category
        
        return MemoryItemSchema(**data)
    
    @classmethod
    def from_schema(cls, schema: MemoryItemSchema) -> "MemoryItem":
        """Create from Pydantic schema"""
        return cls(
            id=schema.id,
            title=schema.title,
            description=schema.description,
            content=schema.content,
            error_context=schema.error_context,
            parent_memory_id=schema.parent_memory_id,
            derived_from=schema.derived_from,
            evolution_stage=schema.evolution_stage,
            pattern_tags=schema.pattern_tags,
            difficulty_level=schema.difficulty_level.value if schema.difficulty_level else None,
            domain_category=schema.domain_category
        )
    
    def format_for_prompt(self) -> str:
        """Format memory for inclusion in LLM prompts"""
        parts = [
            f"## {self.title}",
            f"**Description:** {self.description}",
            f"**Content:**\n{self.content}"
        ]
        
        if self.error_context:
            parts.append(f"\n⚠️ **Error Warning:** This memory contains failure patterns:")
            parts.append(f"- Error Type: {self.error_context.get('error_type', 'Unknown')}")
            parts.append(f"- Pattern: {self.error_context.get('failure_pattern', 'N/A')}")
            parts.append(f"- Guidance: {self.error_context.get('corrective_guidance', 'N/A')}")
        
        if self.pattern_tags:
            parts.append(f"\n**Tags:** {', '.join(self.pattern_tags)}")
        
        if self.difficulty_level:
            parts.append(f"**Difficulty:** {self.difficulty_level}")
        
        return "\n".join(parts)


# ============================================================================
# ReasoningBank Core Class
# ============================================================================

class ReasoningBank:
    """
    Core memory management system for reasoning traces and learned experiences
    
    The ReasoningBank manages the complete lifecycle of reasoning memories:
    1. Store reasoning traces with extracted learnings
    2. Retrieve relevant memories using semantic search + composite scoring
    3. Judge solution quality and extract structured knowledge
    4. Track memory genealogy and evolution
    5. Provide system statistics and health metrics
    
    Features:
    - Semantic search with ChromaDB/Supabase
    - Composite scoring (similarity + recency + error context)
    - Error context learning for hallucination prevention
    - Memory genealogy tracking
    - Workspace isolation support
    """
    
    def __init__(
        self,
        storage_backend: StorageBackendInterface,
        llm_client: CachedLLMClient,
        workspace_manager: Optional[WorkspaceManager] = None,
        max_memory_items: int = 3,
        retrieval_k: int = 3,
        recency_decay_days: float = 30.0,
        similarity_weight: float = 0.6,
        recency_weight: float = 0.3,
        error_weight: float = 0.1
    ):
        """
        Initialize ReasoningBank
        
        Args:
            storage_backend: Storage adapter (ChromaDB or Supabase)
            llm_client: Cached LLM client for judging and extraction
            workspace_manager: Optional workspace manager for isolation
            max_memory_items: Maximum memories to extract per trace
            retrieval_k: Number of memories to retrieve
            recency_decay_days: Half-life for recency scoring (days)
            similarity_weight: Weight for similarity in composite score
            recency_weight: Weight for recency in composite score
            error_weight: Weight for error context in composite score
        """
        self.storage = storage_backend
        self.llm_client = llm_client
        self.workspace_manager = workspace_manager
        self.max_memory_items = max_memory_items
        self.retrieval_k = retrieval_k
        self.recency_decay_days = recency_decay_days
        
        # Composite scoring weights
        self.similarity_weight = similarity_weight
        self.recency_weight = recency_weight
        self.error_weight = error_weight
        
        # Validate weights sum to 1.0
        total_weight = similarity_weight + recency_weight + error_weight
        if not math.isclose(total_weight, 1.0, rel_tol=0.01):
            logger.warning(
                f"Composite score weights sum to {total_weight}, not 1.0. "
                f"Normalizing weights."
            )
            self.similarity_weight /= total_weight
            self.recency_weight /= total_weight
            self.error_weight /= total_weight
        
        logger.info(
            f"ReasoningBank initialized with storage={type(storage_backend).__name__}, "
            f"retrieval_k={retrieval_k}, max_memory_items={max_memory_items}"
        )
    
    def store_trace(
        self,
        task: str,
        trajectory: List[Dict[str, Any]],
        outcome: str,
        memory_items: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        parent_trace_id: Optional[str] = None
    ) -> str:
        """
        Store a complete reasoning trace with memory items
        
        This method persists a reasoning trace including:
        - Original task description
        - Step-by-step trajectory
        - Outcome classification (success/failure/partial)
        - Extracted memory items
        - Metadata (scores, iterations, etc.)
        
        Args:
            task: Original task description
            trajectory: List of trajectory steps
            outcome: Task outcome (success/failure/partial)
            memory_items: List of extracted memory items
            metadata: Additional metadata
            parent_trace_id: Optional parent trace ID for genealogy
        
        Returns:
            Stored trace ID
        
        Raises:
            MemoryStorageError: If storage fails
            MemoryValidationError: If memory items are invalid
        """
        try:
            # Generate trace ID
            trace_id = str(uuid.uuid4())
            
            # Validate memory items
            validated_items = []
            for item in memory_items[:self.max_memory_items]:
                try:
                    # Ensure ID is present
                    if "id" not in item or not item["id"]:
                        item["id"] = str(uuid.uuid4())
                    
                    # Validate using schema
                    validated = MemoryItemSchema(**item)
                    validated_items.append(validated.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid memory item, skipping: {e}")
                    continue
            
            if not validated_items:
                logger.warning(f"No valid memory items to store for trace {trace_id}")
            
            # Get workspace ID if available
            workspace_id = None
            if self.workspace_manager:
                workspace_id = self.workspace_manager.get_workspace_id()
            
            # Store via storage adapter
            stored_id = self.storage.add_trace(
                trace_id=trace_id,
                task=task,
                trajectory=trajectory,
                outcome=outcome,
                memory_items=validated_items,
                metadata=metadata or {},
                workspace_id=workspace_id
            )
            
            logger.info(
                f"Stored trace {stored_id} with {len(validated_items)} memory items "
                f"(outcome: {outcome})"
            )
            
            return stored_id
            
        except Exception as e:
            raise MemoryStorageError(
                f"Failed to store reasoning trace",
                context={"task": task[:100], "error": str(e)}
            )
    
    def retrieve_memories(
        self,
        query: str,
        n_results: Optional[int] = None,
        include_errors: bool = True,
        domain_filter: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Retrieve relevant memories with semantic search and composite scoring
        
        This method:
        1. Performs semantic search using embeddings
        2. Computes composite scores (similarity + recency + error context)
        3. Ranks memories by composite score
        4. Returns top-k most relevant memories
        
        Args:
            query: Search query text
            n_results: Number of results (defaults to self.retrieval_k)
            include_errors: Include memories with error context
            domain_filter: Optional domain category filter
        
        Returns:
            List of MemoryItem objects ranked by composite score
        
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            if n_results is None:
                n_results = self.retrieval_k
            
            # Get workspace ID if available
            workspace_id = None
            if self.workspace_manager:
                workspace_id = self.workspace_manager.get_workspace_id()
            
            # Query storage backend
            memory_schemas = self.storage.query_similar_memories(
                query_text=query,
                n_results=n_results * 2,  # Get more for re-ranking
                include_errors=include_errors,
                domain_filter=domain_filter,
                workspace_id=workspace_id
            )
            
            if not memory_schemas:
                logger.info(f"No memories found for query: {query[:50]}...")
                return []
            
            # Convert to MemoryItem and compute composite scores
            memories_with_scores = []
            current_time = datetime.now()
            
            for schema in memory_schemas:
                memory = MemoryItem.from_schema(schema)
                
                # Compute composite score
                composite_score = self.compute_composite_score(
                    memory=memory,
                    current_time=current_time
                )
                
                memory.composite_score = composite_score
                memories_with_scores.append(memory)
            
            # Sort by composite score (descending)
            memories_with_scores.sort(key=lambda m: m.composite_score or 0.0, reverse=True)
            
            # Return top-k
            top_memories = memories_with_scores[:n_results]
            
            logger.info(
                f"Retrieved {len(top_memories)} memories for query: {query[:50]}... "
                f"(top score: {top_memories[0].composite_score:.3f})"
            )
            
            return top_memories
            
        except Exception as e:
            raise MemoryRetrievalError(
                "Failed to retrieve memories",
                query=query,
                context={"error": str(e)}
            )
    
    def compute_composite_score(
        self,
        memory: MemoryItem,
        current_time: Optional[datetime] = None
    ) -> float:
        """
        Compute composite score combining similarity, recency, and error context
        
        The composite score is a weighted combination of:
        1. Similarity score: Semantic similarity from vector search
        2. Recency score: Exponential decay based on memory age
        3. Error context boost: Bonus for memories with error context
        
        Formula:
            composite = w_sim * similarity + w_rec * recency + w_err * error_boost
        
        Args:
            memory: Memory item to score
            current_time: Current time for recency calculation
        
        Returns:
            Composite score between 0.0 and 1.0
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 1. Similarity score (from vector search)
        similarity = memory.similarity_score or 0.5  # Default if not available
        
        # 2. Recency score (exponential decay)
        recency = 0.5  # Default if timestamp not available
        if memory.trace_timestamp:
            try:
                # Parse timestamp
                if isinstance(memory.trace_timestamp, str):
                    trace_time = datetime.fromisoformat(memory.trace_timestamp.replace('Z', '+00:00'))
                else:
                    trace_time = memory.trace_timestamp
                
                # Calculate age in days
                age_seconds = (current_time - trace_time).total_seconds()
                age_days = age_seconds / 86400.0
                
                # Exponential decay: exp(-age / half_life)
                recency = math.exp(-age_days / self.recency_decay_days)
                
            except Exception as e:
                logger.warning(f"Failed to parse timestamp for recency: {e}")
        
        # 3. Error context boost
        error_boost = 0.0
        if memory.error_context:
            # Boost score for memories with error context
            error_boost = 1.0
        
        # Compute weighted composite score
        composite = (
            self.similarity_weight * similarity +
            self.recency_weight * recency +
            self.error_weight * error_boost
        )
        
        # Clamp to [0, 1]
        composite = max(0.0, min(1.0, composite))
        
        return composite
    
    def get_genealogy(self, memory_id: str) -> Dict[str, Any]:
        """
        Trace memory evolution tree
        
        Returns the complete ancestry and descendant tree for a memory,
        showing how knowledge evolved through refinement and derivation.
        
        Args:
            memory_id: ID of the memory to trace
        
        Returns:
            Dictionary with genealogy information:
            - memory_id: The queried memory ID
            - memory_title: Title of the memory
            - parents: List of parent memory information
            - children: List of derived memory information
            - evolution_stage: Current evolution stage
            - ancestry_chain: Complete chain from root to current
            - derived_from: List of memory IDs this was derived from
        
        Raises:
            MemoryRetrievalError: If memory not found or retrieval fails
        """
        try:
            # Get workspace ID if available
            workspace_id = None
            if self.workspace_manager:
                workspace_id = self.workspace_manager.get_workspace_id()
            
            # Retrieve all memories to build genealogy tree
            # Note: This is a simplified approach. For large datasets,
            # the storage backend should support direct relationship queries
            all_results = self.storage.collection.get(
                where={"workspace_id": workspace_id} if workspace_id else None,
                include=["metadatas"]
            )
            
            if not all_results["ids"]:
                raise MemoryRetrievalError(
                    f"No memories found in workspace",
                    query=memory_id
                )
            
            # Build memory lookup map
            memory_map = {}
            for i, mem_id in enumerate(all_results["ids"]):
                metadata = all_results["metadatas"][i]
                try:
                    memory_data = json.loads(metadata.get("memory_data", "{}"))
                    memory_map[mem_id] = memory_data
                except json.JSONDecodeError:
                    continue
            
            # Find the target memory
            if memory_id not in memory_map:
                raise MemoryRetrievalError(
                    f"Memory not found: {memory_id}",
                    query=memory_id
                )
            
            target_memory = memory_map[memory_id]
            
            # Extract genealogy information
            parent_memory_id = target_memory.get("parent_memory_id")
            derived_from = target_memory.get("derived_from", [])
            evolution_stage = target_memory.get("evolution_stage", 0)
            
            # Build parent information
            parents = []
            if parent_memory_id and parent_memory_id in memory_map:
                parent_data = memory_map[parent_memory_id]
                parents.append({
                    "id": parent_memory_id,
                    "title": parent_data.get("title", "Unknown"),
                    "evolution_stage": parent_data.get("evolution_stage", 0)
                })
            
            # Add derived_from memories
            for derived_id in derived_from:
                if derived_id in memory_map and derived_id != parent_memory_id:
                    derived_data = memory_map[derived_id]
                    parents.append({
                        "id": derived_id,
                        "title": derived_data.get("title", "Unknown"),
                        "evolution_stage": derived_data.get("evolution_stage", 0),
                        "relationship": "derived_from"
                    })
            
            # Find children (memories that have this as parent or in derived_from)
            children = []
            for mem_id, mem_data in memory_map.items():
                if mem_id == memory_id:
                    continue
                
                # Check if this memory is a parent
                if mem_data.get("parent_memory_id") == memory_id:
                    children.append({
                        "id": mem_id,
                        "title": mem_data.get("title", "Unknown"),
                        "evolution_stage": mem_data.get("evolution_stage", 0),
                        "relationship": "child"
                    })
                # Check if this memory was derived from target
                elif memory_id in mem_data.get("derived_from", []):
                    children.append({
                        "id": mem_id,
                        "title": mem_data.get("title", "Unknown"),
                        "evolution_stage": mem_data.get("evolution_stage", 0),
                        "relationship": "derived"
                    })
            
            # Build ancestry chain (trace back to root)
            ancestry_chain = [memory_id]
            current_id = parent_memory_id
            visited = {memory_id}  # Prevent infinite loops
            
            while current_id and current_id in memory_map and current_id not in visited:
                ancestry_chain.insert(0, current_id)
                visited.add(current_id)
                current_memory = memory_map[current_id]
                current_id = current_memory.get("parent_memory_id")
            
            # Build genealogy response
            genealogy = {
                "memory_id": memory_id,
                "memory_title": target_memory.get("title", "Unknown"),
                "evolution_stage": evolution_stage,
                "parents": parents,
                "children": children,
                "derived_from": derived_from,
                "ancestry_chain": ancestry_chain,
                "total_ancestors": len(ancestry_chain) - 1,
                "total_descendants": len(children),
                "is_root": len(parents) == 0,
                "is_leaf": len(children) == 0
            }
            
            logger.info(
                f"Retrieved genealogy for memory {memory_id}: "
                f"{len(parents)} parents, {len(children)} children, "
                f"evolution_stage={evolution_stage}"
            )
            
            return genealogy
            
        except MemoryRetrievalError:
            raise
        except Exception as e:
            logger.error(f"Failed to get genealogy for memory {memory_id}: {e}")
            raise MemoryRetrievalError(
                f"Failed to retrieve genealogy for memory {memory_id}",
                query=memory_id,
                context={"error": str(e)}
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get system performance metrics and statistics
        
        Returns comprehensive statistics including:
        - Total traces and memories
        - Success/failure rates
        - Memory distribution by domain and difficulty
        - Evolution stage statistics
        - Error context frequency
        
        Returns:
            Dictionary with system statistics
        """
        try:
            # Get workspace ID if available
            workspace_id = None
            if self.workspace_manager:
                workspace_id = self.workspace_manager.get_workspace_id()
            
            # Get statistics from storage backend
            stats = self.storage.get_statistics(workspace_id=workspace_id)
            
            # Add workspace info if available
            if self.workspace_manager and self.workspace_manager.is_workspace_set():
                stats["workspace"] = {
                    "id": self.workspace_manager.get_workspace_id(),
                    "name": self.workspace_manager.get_workspace_name(),
                    "path": self.workspace_manager.get_workspace_path()
                }
            
            logger.info(f"Retrieved statistics: {stats['total_traces']} traces, {stats['total_memories']} memories")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e),
                "total_traces": 0,
                "total_memories": 0
            }
    
    def judge_solution(
        self,
        task: str,
        solution: str,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Judge solution quality and extract learnings
        
        Uses LLM to evaluate a solution and extract structured knowledge.
        The judge provides:
        - Verdict (success/failure/partial)
        - Quality score (0.0-1.0)
        - Reasoning for the score
        - Extracted learnings as memory items
        
        Args:
            task: Original task description
            solution: Solution to evaluate
            temperature: LLM temperature (0.0 for deterministic)
        
        Returns:
            Dictionary with:
            - verdict: success/failure/partial
            - score: 0.0-1.0
            - reasoning: Explanation of score
            - learnings: List of extracted memory items
            - error_context: Error information if failure
        
        Raises:
            LLMGenerationError: If LLM call fails
            JSONParseError: If response parsing fails
        """
        try:
            # Build judge prompt
            prompt = self._build_judge_prompt(task, solution)
            
            # Call LLM
            messages = [
                {"role": "system", "content": "You are an expert code reviewer and knowledge extractor."},
                {"role": "user", "content": prompt}
            ]
            
            result = self.llm_client.create(
                messages=messages,
                temperature=temperature,
                max_output_tokens=4000
            )
            
            # Parse JSON response
            judgment = self._parse_judge_response(result.content)
            
            logger.info(
                f"Judged solution: verdict={judgment['verdict']}, "
                f"score={judgment['score']:.2f}"
            )
            
            return judgment
            
        except Exception as e:
            logger.error(f"Failed to judge solution: {e}")
            raise LLMGenerationError(
                "Failed to judge solution",
                context={"task": task[:100], "error": str(e)}
            )
    
    def _build_judge_prompt(self, task: str, solution: str) -> str:
        """Build prompt for solution judging"""
        prompt = f"""You are evaluating a solution to a coding task.

**Task:**
{task}

**Solution:**
{solution}

**Instructions:**
Evaluate the solution and provide your assessment in JSON format with the following structure:

{{
    "verdict": "success" | "failure" | "partial",
    "score": <float between 0.0 and 1.0>,
    "reasoning": "<explanation of why this score was given>",
    "learnings": [
        {{
            "title": "<concise title (5-10 words)>",
            "description": "<one-sentence summary>",
            "content": "<detailed knowledge content with patterns and insights>",
            "pattern_tags": ["<tag1>", "<tag2>", ...],
            "difficulty_level": "simple" | "moderate" | "complex" | "expert",
            "domain_category": "<domain like 'algorithms', 'api_usage', etc.>",
            "error_context": {{
                "error_type": "<error type if failure>",
                "failure_pattern": "<what went wrong>",
                "corrective_guidance": "<how to avoid this error>"
            }}  // Only include if verdict is "failure"
        }}
    ]
}}

**Evaluation Criteria:**
- Correctness: Does it solve the task?
- Code quality: Is it well-structured and readable?
- Error handling: Does it handle edge cases?
- Best practices: Does it follow conventions?

**Scoring Guide:**
- 0.0-0.3: Major issues, doesn't work
- 0.4-0.6: Partial solution, has problems
- 0.7-0.8: Good solution, minor issues
- 0.9-1.0: Excellent solution

Extract 1-3 key learnings that would be valuable for future similar tasks.
"""
        return prompt
    
    def _parse_judge_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from judge LLM"""
        try:
            # Try to extract JSON from response
            # Handle cases where LLM adds markdown code blocks
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            judgment = json.loads(response)
            
            # Validate required fields
            required_fields = ["verdict", "score", "reasoning", "learnings"]
            for field in required_fields:
                if field not in judgment:
                    raise JSONParseError(
                        f"Missing required field: {field}",
                        raw_content=response
                    )
            
            # Validate verdict
            valid_verdicts = ["success", "failure", "partial"]
            if judgment["verdict"] not in valid_verdicts:
                logger.warning(f"Invalid verdict: {judgment['verdict']}, defaulting to 'partial'")
                judgment["verdict"] = "partial"
            
            # Validate score
            score = float(judgment["score"])
            judgment["score"] = max(0.0, min(1.0, score))
            
            # Ensure learnings is a list
            if not isinstance(judgment["learnings"], list):
                judgment["learnings"] = []
            
            return judgment
            
        except json.JSONDecodeError as e:
            raise JSONParseError(
                "Failed to parse judge response as JSON",
                raw_content=response,
                context={"error": str(e)}
            )
        except Exception as e:
            raise JSONParseError(
                "Failed to parse judge response",
                raw_content=response,
                context={"error": str(e)}
            )
    
    def extract_learnings(
        self,
        task: str,
        trajectory: List[Dict[str, Any]],
        outcome: str,
        final_solution: str,
        temperature: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Extract structured knowledge from reasoning trajectory
        
        Uses LLM to analyze the complete reasoning process and extract
        reusable knowledge patterns. This is called after task completion
        to build the memory bank.
        
        Args:
            task: Original task description
            trajectory: Complete reasoning trajectory
            outcome: Task outcome (success/failure/partial)
            final_solution: Final solution produced
            temperature: LLM temperature (0.0 for deterministic)
        
        Returns:
            List of memory item dictionaries ready for storage
        
        Raises:
            LLMGenerationError: If LLM call fails
            JSONParseError: If response parsing fails
        """
        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(
                task, trajectory, outcome, final_solution
            )
            
            # Call LLM
            messages = [
                {"role": "system", "content": "You are an expert at extracting reusable knowledge patterns from problem-solving processes."},
                {"role": "user", "content": prompt}
            ]
            
            result = self.llm_client.create(
                messages=messages,
                temperature=temperature,
                max_output_tokens=6000
            )
            
            # Parse JSON response
            learnings = self._parse_extraction_response(result.content)
            
            # Limit to max_memory_items
            learnings = learnings[:self.max_memory_items]
            
            logger.info(f"Extracted {len(learnings)} learnings from trajectory")
            
            return learnings
            
        except Exception as e:
            logger.error(f"Failed to extract learnings: {e}")
            # Return empty list rather than failing
            return []
    
    def _build_extraction_prompt(
        self,
        task: str,
        trajectory: List[Dict[str, Any]],
        outcome: str,
        final_solution: str
    ) -> str:
        """Build prompt for learning extraction"""
        
        # Format trajectory
        trajectory_text = "\n\n".join([
            f"**Iteration {step.get('iteration', i+1)}:**\n"
            f"Action: {step.get('action', 'unknown')}\n"
            f"Output: {step.get('output', '')[:500]}..."
            for i, step in enumerate(trajectory[:5])  # Limit to first 5 steps
        ])
        
        prompt = f"""Analyze this problem-solving process and extract reusable knowledge patterns.

**Task:**
{task}

**Outcome:** {outcome}

**Reasoning Trajectory:**
{trajectory_text}

**Final Solution:**
{final_solution[:1000]}...

**Instructions:**
Extract 1-{self.max_memory_items} key learnings that would be valuable for future similar tasks.
Focus on:
- Patterns and approaches that worked (or didn't work)
- Common pitfalls and how to avoid them
- Reusable techniques and best practices
- Error patterns if this was a failure

Return your analysis as a JSON array:

[
    {{
        "title": "<concise title (5-10 words)>",
        "description": "<one-sentence summary>",
        "content": "<detailed knowledge content with patterns, code examples, and insights>",
        "pattern_tags": ["<tag1>", "<tag2>", ...],
        "difficulty_level": "simple" | "moderate" | "complex" | "expert",
        "domain_category": "<domain like 'algorithms', 'api_usage', 'debugging', etc.>",
        "error_context": {{
            "error_type": "<error type>",
            "failure_pattern": "<what went wrong>",
            "corrective_guidance": "<how to avoid this>"
        }}  // Only include if outcome is "failure"
    }}
]

Make each learning specific, actionable, and reusable.
"""
        return prompt
    
    def _parse_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON response from extraction LLM"""
        try:
            # Clean response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            learnings = json.loads(response)
            
            # Ensure it's a list
            if not isinstance(learnings, list):
                logger.warning("Extraction response is not a list, wrapping")
                learnings = [learnings]
            
            # Validate and clean each learning
            validated_learnings = []
            for learning in learnings:
                if not isinstance(learning, dict):
                    continue
                
                # Ensure required fields
                if "title" not in learning or "description" not in learning or "content" not in learning:
                    logger.warning("Learning missing required fields, skipping")
                    continue
                
                # Add ID if not present
                if "id" not in learning:
                    learning["id"] = str(uuid.uuid4())
                
                # Ensure pattern_tags is a list
                if "pattern_tags" not in learning:
                    learning["pattern_tags"] = []
                elif not isinstance(learning["pattern_tags"], list):
                    learning["pattern_tags"] = []
                
                validated_learnings.append(learning)
            
            return validated_learnings
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return []
    
    def cleanup_old_traces(
        self,
        retention_days: int = 90,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete traces and memories older than retention_days
        
        This method removes old reasoning traces to manage storage and comply
        with data retention policies. By default, traces older than 90 days
        are deleted.
        
        Args:
            retention_days: Number of days to retain traces (default: 90)
            workspace_id: Optional workspace filter. If None, uses current workspace
        
        Returns:
            Dictionary with cleanup statistics:
            - deleted_traces_count: Number of traces deleted
            - deleted_memories_count: Number of memory items deleted
            - freed_space_mb: Estimated freed space in MB
            - retention_cutoff: ISO timestamp of cutoff date
        
        Raises:
            MemoryStorageError: If cleanup fails
        
        Example:
            >>> bank = ReasoningBank(...)
            >>> result = bank.cleanup_old_traces(retention_days=90)
            >>> print(f"Deleted {result['deleted_traces_count']} traces")
        
        Note:
            - This operation is irreversible
            - Logs cleanup operations with timestamps and counts
            - If workspace_id is None, uses current workspace from WorkspaceManager
        """
        try:
            # Determine workspace_id
            target_workspace_id = workspace_id
            if target_workspace_id is None and self.workspace_manager:
                target_workspace_id = self.workspace_manager.get_workspace_id()
            
            logger.info(
                f"Starting trace cleanup: retention_days={retention_days}, "
                f"workspace_id={target_workspace_id or 'all'}"
            )
            
            # Call storage adapter to delete old traces
            result = self.storage.delete_old_traces(
                retention_days=retention_days,
                workspace_id=target_workspace_id
            )
            
            # Log the cleanup operation
            logger.info(
                f"Trace cleanup completed: "
                f"deleted {result['deleted_traces_count']} traces, "
                f"{result['deleted_memories_count']} memories, "
                f"freed ~{result['freed_space_mb']} MB"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup old traces: {e}")
            raise MemoryStorageError(
                "Failed to cleanup old traces",
                context={
                    "retention_days": retention_days,
                    "workspace_id": workspace_id,
                    "error": str(e)
                }
            )


# ============================================================================
# Convenience Functions
# ============================================================================

def create_reasoning_bank(
    storage_backend: StorageBackendInterface,
    llm_client: CachedLLMClient,
    workspace_manager: Optional[WorkspaceManager] = None,
    **kwargs
) -> ReasoningBank:
    """
    Factory function to create ReasoningBank instance
    
    Args:
        storage_backend: Storage adapter
        llm_client: Cached LLM client
        workspace_manager: Optional workspace manager
        **kwargs: Additional ReasoningBank configuration
    
    Returns:
        Initialized ReasoningBank instance
    """
    return ReasoningBank(
        storage_backend=storage_backend,
        llm_client=llm_client,
        workspace_manager=workspace_manager,
        **kwargs
    )


# ============================================================================
# Testing and Validation
# ============================================================================

if __name__ == "__main__":
    """Test ReasoningBank functionality"""
    print("=== Testing ReasoningBank Core ===\n")
    
    # This would require full system initialization
    # See test_reasoning_bank_core.py for comprehensive tests
    
    print("ReasoningBank core module loaded successfully")
    print("\nKey features:")
    print("  ✅ Memory storage with validation")
    print("  ✅ Semantic retrieval with composite scoring")
    print("  ✅ Solution judging with LLM")
    print("  ✅ Learning extraction from trajectories")
    print("  ✅ Genealogy tracking support")
    print("  ✅ System statistics")
    print("\nReady for integration with MCP server and iterative agent.")
