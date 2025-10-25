"""
ReasoningBank MCP Server

This module implements the FastMCP server that exposes ReasoningBank functionality
as Model Context Protocol (MCP) tools. It provides:
- solve_coding_task: Iterative reasoning with memory guidance
- retrieve_memories: Query past experiences
- get_memory_genealogy: Trace memory evolution
- get_statistics: System performance metrics

The server initializes all components during lifespan startup:
- ReasoningBank core for memory management
- IterativeAgent for reasoning loops
- CachedLLMClient for API calls with caching
- PassiveLearner for automatic knowledge capture
- WorkspaceManager for multi-tenant isolation
- KnowledgeRetriever for advanced memory queries

Requirements addressed: 5.5, 12.3
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

# FastMCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ReasoningBank components
from config import get_config
from reasoning_bank_core import ReasoningBank
from iterative_agent import IterativeReasoningAgent
from cached_llm_client import CachedLLMClient
from responses_alpha_client import ResponsesAPIClient
from passive_learner import PassiveLearner
from workspace_manager import WorkspaceManager
from knowledge_retrieval import KnowledgeRetriever
from storage_adapter import create_storage_backend
from exceptions import (
    APIKeyError,
    InvalidTaskError,
    MemoryRetrievalError,
    LLMGenerationError
)
from schemas import (
    SolveCodingTaskInput,
    RetrieveMemoriesInput,
    OutcomeType
)


# Configure structured logging
try:
    from logging_config import configure_logging
    configure_logging()
except ImportError:
    # Fallback to basic logging if logging_config not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)


# ============================================================================
# Global Component References
# ============================================================================

# These will be initialized during lifespan startup
reasoning_bank: Optional[ReasoningBank] = None
iterative_agent: Optional[IterativeReasoningAgent] = None
cached_llm_client: Optional[CachedLLMClient] = None
passive_learner: Optional[PassiveLearner] = None
workspace_manager: Optional[WorkspaceManager] = None
knowledge_retriever: Optional[KnowledgeRetriever] = None
config = None


# ============================================================================
# Component Initialization
# ============================================================================

@asynccontextmanager
async def lifespan(app: Server):
    """
    Lifespan context manager for component initialization and cleanup
    
    This function:
    1. Loads configuration from environment variables
    2. Validates API key (fail-fast if missing/invalid)
    3. Initializes all system components with proper dependency injection
    4. Yields control to the server
    5. Performs cleanup on shutdown
    
    Raises:
        APIKeyError: If API key is missing or invalid
        ImportError: If required dependencies are not installed
    """
    global reasoning_bank, iterative_agent, cached_llm_client
    global passive_learner, workspace_manager, knowledge_retriever, config
    
    logger.info("=== ReasoningBank MCP Server Starting ===")
    
    try:
        # 1. Load configuration
        logger.info("Loading configuration from environment...")
        config = get_config()
        logger.info(f"Configuration loaded: model={config.model}, "
                   f"storage={config.storage_backend.value}")
        
        # 2. Validate API key (fail-fast)
        logger.info("Validating API key...")
        if not config.api_key:
            raise APIKeyError(
                "OPENROUTER_API_KEY environment variable not set. "
                "Please set it before starting the server.",
                key_name="OPENROUTER_API_KEY"
            )
        
        # Test API key with a minimal request
        test_client = ResponsesAPIClient(
            api_key=config.api_key,
            default_model=config.model,
            default_reasoning_effort=config.reasoning_effort.value
        )
        
        try:
            test_client.validate_api_key()
            logger.info("✅ API key validated successfully")
        except Exception as e:
            raise APIKeyError(
                f"API key validation failed: {str(e)}",
                key_name="OPENROUTER_API_KEY",
                context={"error": str(e)}
            )
        
        # 3. Initialize storage backend
        logger.info(f"Initializing {config.storage_backend.value} storage backend...")
        storage_backend = create_storage_backend(
            backend_type=config.storage_backend.value,
            persist_directory=config.persist_directory,
            collection_name=config.collection_name,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            traces_table=config.supabase_traces_table,
            memories_table=config.supabase_memories_table
        )
        logger.info("✅ Storage backend initialized")
        
        # 4. Initialize LLM clients
        logger.info("Initializing LLM clients...")
        responses_client = ResponsesAPIClient(
            api_key=config.api_key,
            default_model=config.model,
            default_reasoning_effort=config.reasoning_effort.value
        )
        
        cached_llm_client = CachedLLMClient(
            client=responses_client,
            max_cache_size=config.cache_size,
            ttl_seconds=config.cache_ttl_seconds,
            enable_cache=config.enable_cache
        )
        logger.info("✅ LLM clients initialized")
        
        # 5. Initialize workspace manager
        logger.info("Initializing workspace manager...")
        workspace_manager = WorkspaceManager(
            default_workspace=os.getcwd()
        )
        logger.info(f"✅ Workspace manager initialized: {workspace_manager.get_workspace_name()}")
        
        # 6. Initialize ReasoningBank core
        logger.info("Initializing ReasoningBank core...")
        reasoning_bank = ReasoningBank(
            storage_backend=storage_backend,
            llm_client=cached_llm_client,
            workspace_manager=workspace_manager,
            max_memory_items=config.max_memory_items,
            retrieval_k=config.retrieval_k
        )
        logger.info("✅ ReasoningBank core initialized")
        
        # 7. Initialize iterative agent
        logger.info("Initializing iterative reasoning agent...")
        iterative_agent = IterativeReasoningAgent(
            llm_client=cached_llm_client,
            reasoning_bank=reasoning_bank,
            max_iterations=config.max_iterations,
            success_threshold=config.success_threshold,
            temperature_generate=config.temperature_generate,
            temperature_evaluate=config.temperature_judge,
            max_output_tokens=config.token_budget.max_output_tokens,
            evaluation_tokens=config.token_budget.evaluation_tokens,
            max_prompt_tokens=config.token_budget.max_prompt_tokens,
            truncation_threshold=config.token_budget.truncation_threshold,
            truncation_head_ratio=config.token_budget.truncation_head_ratio
        )
        logger.info("✅ Iterative agent initialized")
        
        # 8. Initialize passive learner
        logger.info("Initializing passive learner...")
        passive_learner = PassiveLearner(
            reasoning_bank=reasoning_bank,
            llm_client=cached_llm_client
        )
        logger.info("✅ Passive learner initialized")
        
        # 9. Initialize knowledge retriever
        logger.info("Initializing knowledge retriever...")
        knowledge_retriever = KnowledgeRetriever(
            reasoning_bank=reasoning_bank
        )
        logger.info("✅ Knowledge retriever initialized")
        
        logger.info("=== All components initialized successfully ===")
        logger.info(f"Server ready to accept requests")
        logger.info(f"Model: {config.model}")
        logger.info(f"Storage: {config.storage_backend.value}")
        logger.info(f"Workspace: {workspace_manager.get_workspace_name()}")
        logger.info(f"Cache enabled: {config.enable_cache}")
        
        # Yield control to server
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("=== ReasoningBank MCP Server Shutting Down ===")
        
        # Log final statistics
        if reasoning_bank:
            try:
                stats = reasoning_bank.get_statistics()
                logger.info(f"Final statistics:")
                logger.info(f"  Total traces: {stats.get('total_traces', 0)}")
                logger.info(f"  Total memories: {stats.get('total_memories', 0)}")
                logger.info(f"  Success rate: {stats.get('success_rate', 0)}%")
            except Exception as e:
                logger.warning(f"Failed to get final statistics: {e}")
        
        if cached_llm_client:
            try:
                cache_stats = cached_llm_client.get_statistics()
                logger.info(f"Cache statistics:")
                logger.info(f"  Hit rate: {cache_stats.hit_rate:.1%}")
                logger.info(f"  Total requests: {cache_stats.total_requests}")
                logger.info(f"  Cost savings: {cache_stats.cost_savings_estimate:.1%}")
            except Exception as e:
                logger.warning(f"Failed to get cache statistics: {e}")
        
        logger.info("Server shutdown complete")


# ============================================================================
# MCP Server Initialization
# ============================================================================

# Create FastMCP server instance with lifespan context manager
server = Server("reasoning-bank", lifespan=lifespan)


# ============================================================================
# MCP Tool: solve_coding_task
# ============================================================================

@server.call_tool()
async def solve_coding_task(
    task: str,
    use_memory: bool = True,
    enable_matts: bool = False,
    matts_k: int = 3,
    matts_mode: str = "parallel",
    store_result: bool = True
) -> Dict[str, Any]:
    """
    Solve a coding task using iterative reasoning with memory guidance
    
    This tool implements the complete Think → Evaluate → Refine loop:
    1. Retrieves relevant memories from past experiences (if use_memory=True)
    2. Generates solution with memory context
    3. Evaluates solution quality
    4. Refines based on feedback (up to max_iterations)
    5. Stores learnings to ReasoningBank (if store_result=True)
    
    Args:
        task: The coding task description
        use_memory: Whether to retrieve and use past memories
        enable_matts: Enable Memory-Aware Test-Time Scaling (parallel solutions)
        matts_k: Number of parallel solution attempts (if MaTTS enabled)
        matts_mode: MaTTS execution mode ("parallel" or "sequential")
        store_result: Whether to store the result as new memory
    
    Returns:
        Dictionary with:
        - solution: The generated solution
        - score: Quality score (0.0-1.0)
        - trajectory: Step-by-step reasoning process
        - iterations: Number of iterations taken
        - memories_used: Number of memories retrieved
        - early_termination: Whether success threshold was reached
        - trace_id: ID of stored trace (if store_result=True)
    """
    logger.info(f"solve_coding_task called: task='{task[:50]}...', "
               f"use_memory={use_memory}, enable_matts={enable_matts}")
    
    try:
        # Validate inputs
        if not task or len(task.strip()) < 10:
            raise InvalidTaskError(
                "Task description too short (minimum 10 characters)",
                task=task
            )
        
        # Retrieve memories if requested
        memories = []
        if use_memory:
            try:
                memories = reasoning_bank.retrieve_memories(
                    query=task,
                    n_results=config.retrieval_k
                )
                logger.info(f"Retrieved {len(memories)} relevant memories")
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")
                memories = []
        
        # Solve task with or without MaTTS
        if enable_matts:
            logger.info(f"Solving with MaTTS: k={matts_k}, mode={matts_mode}")
            result = iterative_agent.solve_with_matts(
                task=task,
                memories=memories,
                use_memory=use_memory,
                k=matts_k,
                mode=matts_mode,
                refine_best=True
            )
        else:
            logger.info("Solving with standard iterative refinement")
            result = iterative_agent.solve_task(
                task=task,
                memories=memories,
                use_memory=use_memory
            )
        
        logger.info(f"Task completed: score={result.score:.2f}, "
                   f"iterations={result.iterations}, "
                   f"early_termination={result.early_termination}")
        
        # Judge solution and extract learnings
        judgment = reasoning_bank.judge_solution(
            task=task,
            solution=result.solution,
            temperature=config.temperature_judge
        )
        
        # Store result if requested
        trace_id = None
        if store_result:
            try:
                # Determine outcome
                if judgment["verdict"] == "success":
                    outcome = OutcomeType.SUCCESS.value
                elif judgment["verdict"] == "failure":
                    outcome = OutcomeType.FAILURE.value
                else:
                    outcome = OutcomeType.PARTIAL.value
                
                # Store trace with learnings
                trace_id = reasoning_bank.store_trace(
                    task=task,
                    trajectory=result.trajectory,
                    outcome=outcome,
                    memory_items=judgment.get("learnings", []),
                    metadata={
                        "score": result.score,
                        "iterations": result.iterations,
                        "total_tokens": result.total_tokens,
                        "early_termination": result.early_termination,
                        "loop_detected": result.loop_detected,
                        "matts_enabled": enable_matts,
                        "matts_k": matts_k if enable_matts else None,
                        "matts_mode": matts_mode if enable_matts else None,
                        "memories_used": len(memories)
                    }
                )
                logger.info(f"Stored trace: {trace_id}")
            except Exception as e:
                logger.error(f"Failed to store trace: {e}")
        
        # Build response
        response = {
            "success": result.score >= config.success_threshold,
            "solution": result.solution,
            "score": result.score,
            "trajectory": result.trajectory,
            "iterations": result.iterations,
            "memories_used": len(memories),
            "early_termination": result.early_termination,
            "loop_detected": result.loop_detected,
            "total_tokens": result.total_tokens,
            "judge_verdict": judgment["verdict"],
            "judge_score": judgment["score"],
            "judge_reasoning": judgment["reasoning"],
            "learnings_extracted": len(judgment.get("learnings", [])),
            "trace_id": trace_id
        }
        
        return response
        
    except InvalidTaskError as e:
        logger.error(f"Invalid task: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "InvalidTaskError"
        }
    except Exception as e:
        logger.error(f"Error solving task: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: retrieve_memories
# ============================================================================

@server.call_tool()
async def retrieve_memories(
    query: str,
    n_results: int = 5,
    include_failures: bool = True,
    domain_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve relevant memories from past experiences
    
    Uses semantic search with composite scoring (similarity + recency + error context)
    to find the most relevant memories for a given query.
    
    Args:
        query: Search query text
        n_results: Number of memories to retrieve (1-20)
        include_failures: Include memories from failed attempts
        domain_filter: Filter by domain category (e.g., "algorithms", "api_usage")
    
    Returns:
        Dictionary with:
        - memories: List of memory items with scores
        - total_found: Total number of memories found
        - has_error_warnings: Whether any memories contain error context
    """
    logger.info(f"retrieve_memories called: query='{query[:50]}...', n_results={n_results}")
    
    try:
        # Validate inputs
        if not query or len(query.strip()) < 3:
            raise MemoryRetrievalError(
                "Query too short (minimum 3 characters)",
                query=query
            )
        
        n_results = max(1, min(20, n_results))  # Clamp to [1, 20]
        
        # Retrieve memories
        memories = reasoning_bank.retrieve_memories(
            query=query,
            n_results=n_results,
            include_errors=include_failures,
            domain_filter=domain_filter
        )
        
        # Check for error warnings
        has_error_warnings = any(m.error_context for m in memories)
        
        # Format memories for response
        formatted_memories = []
        for memory in memories:
            memory_dict = {
                "id": memory.id,
                "title": memory.title,
                "description": memory.description,
                "content": memory.content,
                "composite_score": memory.composite_score,
                "similarity_score": memory.similarity_score,
                "recency_score": memory.recency_score,
                "pattern_tags": memory.pattern_tags,
                "difficulty_level": memory.difficulty_level,
                "domain_category": memory.domain_category,
                "has_error_context": memory.error_context is not None
            }
            
            # Include error context if present
            if memory.error_context is not None:
                memory_dict["error_context"] = memory.error_context
            
            formatted_memories.append(memory_dict)
        
        logger.info(f"Retrieved {len(memories)} memories, "
                   f"has_error_warnings={has_error_warnings}")
        
        return {
            "memories": formatted_memories,
            "total_found": len(memories),
            "has_error_warnings": has_error_warnings,
            "query": query,
            "domain_filter": domain_filter
        }
        
    except MemoryRetrievalError as e:
        logger.error(f"Memory retrieval error: {e}")
        return {
            "memories": [],
            "total_found": 0,
            "has_error_warnings": False,
            "error": str(e),
            "error_type": "MemoryRetrievalError"
        }
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}", exc_info=True)
        return {
            "memories": [],
            "total_found": 0,
            "has_error_warnings": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: get_memory_genealogy
# ============================================================================

@server.call_tool()
async def get_memory_genealogy(memory_id: str) -> Dict[str, Any]:
    """
    Trace memory evolution tree
    
    Returns the complete ancestry and descendant tree for a memory,
    showing how knowledge evolved through refinement and derivation.
    
    Args:
        memory_id: ID of the memory to trace
    
    Returns:
        Dictionary with:
        - memory_id: The queried memory ID
        - parents: List of parent memory IDs
        - children: List of derived memory IDs
        - evolution_stage: Current evolution stage
        - ancestry_chain: Complete chain from root to current
    """
    logger.info(f"get_memory_genealogy called: memory_id={memory_id}")
    
    try:
        genealogy = reasoning_bank.get_genealogy(memory_id)
        return genealogy
    except Exception as e:
        logger.error(f"Error getting genealogy: {e}", exc_info=True)
        return {
            "memory_id": memory_id,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: get_statistics
# ============================================================================

@server.call_tool()
async def get_statistics() -> Dict[str, Any]:
    """
    Get system performance metrics and statistics
    
    Returns comprehensive statistics including:
    - Total traces and memories
    - Success/failure rates
    - Cache hit rates
    - Memory distribution by domain and difficulty
    - Workspace information
    
    Returns:
        Dictionary with system statistics
    """
    logger.info("get_statistics called")
    
    try:
        # Get ReasoningBank statistics
        bank_stats = reasoning_bank.get_statistics()
        
        # Get cache statistics
        cache_stats = cached_llm_client.get_statistics()
        
        # Get passive learner statistics
        passive_stats = passive_learner.get_statistics()
        
        # Get knowledge retriever statistics
        retriever_stats = knowledge_retriever.get_statistics()
        
        # Combine all statistics
        combined_stats = {
            "reasoning_bank": bank_stats,
            "cache": {
                "hit_rate": cache_stats.hit_rate,
                "total_requests": cache_stats.total_requests,
                "cache_hits": cache_stats.cache_hits,
                "cache_misses": cache_stats.cache_misses,
                "cache_bypassed": cache_stats.cache_bypassed,
                "cost_savings_estimate": cache_stats.cost_savings_estimate
            },
            "passive_learner": passive_stats,
            "knowledge_retriever": retriever_stats,
            "configuration": {
                "model": config.model,
                "reasoning_effort": config.reasoning_effort.value,
                "storage_backend": config.storage_backend.value,
                "max_iterations": config.max_iterations,
                "success_threshold": config.success_threshold,
                "retrieval_k": config.retrieval_k,
                "cache_enabled": config.enable_cache
            }
        }
        
        return combined_stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: capture_knowledge (Passive Learning)
# ============================================================================

@server.call_tool()
async def capture_knowledge(
    question: str,
    answer: str,
    context: Optional[str] = None,
    force_store: bool = False
) -> Dict[str, Any]:
    """
    Capture knowledge from a Q&A exchange using passive learning
    
    Automatically evaluates if the Q&A exchange is valuable and extracts
    structured knowledge that can be reused for future tasks. Uses quality
    heuristics to determine value (code blocks, explanations, technical depth)
    and LLM-based extraction to structure the knowledge.
    
    Args:
        question: The question text from the conversation
        answer: The answer text to analyze for knowledge extraction
        context: Optional additional context about the conversation
        force_store: Force storage even if auto_store is disabled (default: False)
    
    Returns:
        Dictionary with:
        - is_valuable: Whether the exchange met quality thresholds
        - knowledge_items: List of extracted knowledge items (if valuable)
        - stored: Whether items were stored to ReasoningBank
        - trace_id: Trace ID if knowledge was stored
        - statistics: Current passive learning statistics
    
    Example:
        >>> result = capture_knowledge(
        ...     question="How do I implement binary search?",
        ...     answer="Binary search works by...\n```python\ndef binary_search(arr, target):\n...",
        ...     force_store=True
        ... )
        >>> print(result['stored'])  # True if valuable and stored
    """
    logger.info(
        f"capture_knowledge called: question_len={len(question)}, "
        f"answer_len={len(answer)}, force_store={force_store}"
    )
    
    try:
        # Process the exchange through passive learner
        result = passive_learner.process_exchange(
            question=question,
            answer=answer,
            context=context,
            force_store=force_store
        )
        
        # Add current statistics
        result["statistics"] = passive_learner.get_statistics()
        
        logger.info(
            f"Knowledge capture result: is_valuable={result['is_valuable']}, "
            f"stored={result['stored']}, "
            f"items_extracted={len(result.get('knowledge_items', []))}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error capturing knowledge: {e}", exc_info=True)
        return {
            "is_valuable": False,
            "knowledge_items": [],
            "stored": False,
            "trace_id": None,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: search_knowledge (Knowledge Retrieval)
# ============================================================================

@server.call_tool()
async def search_knowledge(
    query: str,
    n_results: int = 5,
    domain_filter: Optional[str] = None,
    pattern_tags: Optional[List[str]] = None,
    include_errors: bool = True,
    min_score: Optional[float] = None
) -> Dict[str, Any]:
    """
    Search for relevant knowledge using advanced filtering and ranking
    
    Performs semantic search across the ReasoningBank memory system with
    support for domain filtering, pattern tag matching, and relevance scoring.
    Unlike retrieve_memories which provides raw memory retrieval, this tool
    offers advanced filtering and knowledge-specific features.
    
    Args:
        query: Search query text describing what knowledge you need
        n_results: Number of results to return (1-20, default: 5)
        domain_filter: Filter by domain category (e.g., "algorithms", "api_usage", "debugging")
        pattern_tags: Filter by pattern tags (returns memories with matching tags)
        include_errors: Include memories with error context/warnings (default: True)
        min_score: Minimum relevance score threshold (0.0-1.0, default: 0.3)
    
    Returns:
        Dictionary with:
        - knowledge_items: List of relevant knowledge items with scores
        - total_found: Total number of items found
        - query: The original search query
        - filters_applied: Dictionary of filters that were applied
        - has_error_warnings: Whether any items contain error context
    
    Example:
        >>> result = search_knowledge(
        ...     query="sorting algorithms in Python",
        ...     n_results=3,
        ...     domain_filter="algorithms",
        ...     pattern_tags=["sorting", "optimization"]
        ... )
        >>> for item in result['knowledge_items']:
        ...     print(f"{item['title']}: score={item['composite_score']:.2f}")
    """
    logger.info(
        f"search_knowledge called: query='{query[:50]}...', n_results={n_results}, "
        f"domain={domain_filter}, tags={pattern_tags}"
    )
    
    try:
        # Validate and clamp n_results
        n_results = max(1, min(20, n_results))
        
        # Use knowledge retriever for advanced search
        memories = knowledge_retriever.retrieve(
            query=query,
            n_results=n_results,
            domain_filter=domain_filter,
            pattern_tags=pattern_tags,
            include_errors=include_errors,
            min_score=min_score
        )
        
        # Check for error warnings
        has_error_warnings = any(m.error_context for m in memories)
        
        # Format knowledge items for response
        knowledge_items = []
        for memory in memories:
            item = {
                "id": memory.id,
                "title": memory.title,
                "description": memory.description,
                "content": memory.content,
                "composite_score": memory.composite_score,
                "similarity_score": memory.similarity_score,
                "recency_score": memory.recency_score,
                "pattern_tags": memory.pattern_tags or [],
                "difficulty_level": memory.difficulty_level,
                "domain_category": memory.domain_category,
                "has_error_context": memory.error_context is not None
            }
            
            # Include error context if present
            if memory.error_context is not None:
                item["error_context"] = memory.error_context
            
            knowledge_items.append(item)
        
        # Get retriever statistics
        retriever_stats = knowledge_retriever.get_statistics()
        
        logger.info(
            f"Knowledge search completed: found {len(knowledge_items)} items, "
            f"has_warnings={has_error_warnings}"
        )
        
        return {
            "knowledge_items": knowledge_items,
            "total_found": len(knowledge_items),
            "query": query,
            "filters_applied": {
                "domain": domain_filter,
                "pattern_tags": pattern_tags,
                "min_score": min_score,
                "include_errors": include_errors
            },
            "has_error_warnings": has_error_warnings,
            "retriever_statistics": retriever_stats
        }
        
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}", exc_info=True)
        return {
            "knowledge_items": [],
            "total_found": 0,
            "query": query,
            "filters_applied": {},
            "has_error_warnings": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: manage_workspace (Workspace Management)
# ============================================================================

@server.call_tool()
async def manage_workspace(
    action: str,
    workspace_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manage workspace isolation for memory storage
    
    Workspaces isolate memories between different projects or contexts.
    Each workspace has a unique ID derived from its directory path,
    ensuring memories don't mix between different projects.
    
    Args:
        action: Action to perform - "get", "set", or "list"
        workspace_path: Directory path for "set" action
    
    Actions:
        - "get": Get current workspace information
        - "set": Switch to a different workspace
        - "list": List workspace information (same as "get" currently)
    
    Returns:
        Dictionary with:
        - workspace_id: Current workspace identifier
        - workspace_name: Human-readable workspace name
        - workspace_path: Absolute path to workspace directory
        - action_performed: The action that was executed
    
    Example:
        >>> # Get current workspace
        >>> result = manage_workspace(action="get")
        >>> print(result['workspace_name'])
        
        >>> # Switch workspace
        >>> result = manage_workspace(
        ...     action="set",
        ...     workspace_path="/Users/justin/projects/my-app"
        ... )
    """
    logger.info(f"manage_workspace called: action={action}, path={workspace_path}")
    
    try:
        if action == "set":
            if not workspace_path:
                return {
                    "error": "workspace_path required for 'set' action",
                    "error_type": "ValueError"
                }
            
            # Set new workspace
            workspace_id = workspace_manager.set_workspace(workspace_path)
            
            logger.info(f"Workspace switched: {workspace_manager.get_workspace_name()}")
            
            return {
                "workspace_id": workspace_id,
                "workspace_name": workspace_manager.get_workspace_name(),
                "workspace_path": workspace_manager.get_workspace_path(),
                "action_performed": "set"
            }
        
        elif action in ["get", "list"]:
            # Get current workspace info
            return {
                "workspace_id": workspace_manager.get_workspace_id(),
                "workspace_name": workspace_manager.get_workspace_name(),
                "workspace_path": workspace_manager.get_workspace_path(),
                "is_set": workspace_manager.is_workspace_set(),
                "action_performed": action
            }
        
        else:
            return {
                "error": f"Invalid action: {action}. Valid actions: get, set, list",
                "error_type": "ValueError"
            }
    
    except Exception as e:
        logger.error(f"Error managing workspace: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# MCP Tool: backup_memories (Backup & Restore)
# ============================================================================

@server.call_tool()
async def backup_memories(
    action: str,
    backup_path: Optional[str] = None,
    workspace_id: Optional[str] = None,
    incremental: bool = False,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Backup and restore memory data
    
    Create backups of your ReasoningBank memories and traces for disaster
    recovery, migration, or archival purposes. Supports full and incremental
    backups with integrity validation.
    
    Args:
        action: Action to perform - "create", "restore", or "validate"
        backup_path: Path to backup file (.tar.gz)
        workspace_id: Filter by workspace (None = all workspaces)
        incremental: For "create" - only backup data since last backup
        overwrite: For "restore" - overwrite existing memories
    
    Actions:
        - "create": Create a new backup file
        - "restore": Restore from an existing backup
        - "validate": Validate a backup file's integrity
    
    Returns:
        Dictionary with action-specific results:
        
        For "create":
        - backup_path: Path to created backup file
        - backup_size_mb: Size in megabytes
        - trace_count: Number of traces backed up
        - memory_count: Number of memories backed up
        - checksum: SHA256 integrity checksum
        
        For "restore":
        - restored_count: Number of memories restored
        - trace_ids: Number of unique traces
        - target_workspace: Workspace ID where restored
        
        For "validate":
        - valid: Whether backup is valid
        - errors: List of validation errors (if any)
        - warnings: List of warnings
        - metadata: Backup metadata information
    
    Example:
        >>> # Create backup
        >>> result = backup_memories(
        ...     action="create",
        ...     backup_path="./backups/my_backup.tar.gz"
        ... )
        >>> print(f"Backed up {result['memory_count']} memories")
        
        >>> # Validate backup
        >>> result = backup_memories(
        ...     action="validate",
        ...     backup_path="./backups/my_backup.tar.gz"
        ... )
        >>> print(f"Valid: {result['valid']}")
        
        >>> # Restore backup
        >>> result = backup_memories(
        ...     action="restore",
        ...     backup_path="./backups/my_backup.tar.gz",
        ...     overwrite=True
        ... )
    """
    logger.info(
        f"backup_memories called: action={action}, path={backup_path}, "
        f"workspace={workspace_id}, incremental={incremental}"
    )
    
    try:
        # Import backup manager
        from backup_restore import BackupManager
        
        # Create backup manager instance
        backup_manager = BackupManager(
            storage_adapter=reasoning_bank.storage,
            backup_directory="./backups"
        )
        
        if action == "create":
            if not backup_path:
                return {
                    "error": "backup_path required for 'create' action",
                    "error_type": "ValueError"
                }
            
            # Create backup
            result = backup_manager.backup_chromadb(
                output_path=backup_path,
                workspace_id=workspace_id,
                incremental=incremental
            )
            
            logger.info(
                f"Backup created: {result['memory_count']} memories, "
                f"{result['backup_size_mb']} MB"
            )
            
            return result
        
        elif action == "restore":
            if not backup_path:
                return {
                    "error": "backup_path required for 'restore' action",
                    "error_type": "ValueError"
                }
            
            # Restore from backup
            result = backup_manager.restore_chromadb(
                backup_path=backup_path,
                target_workspace_id=workspace_id,
                overwrite=overwrite
            )
            
            logger.info(
                f"Backup restored: {result['restored_count']} memories"
            )
            
            return result
        
        elif action == "validate":
            if not backup_path:
                return {
                    "error": "backup_path required for 'validate' action",
                    "error_type": "ValueError"
                }
            
            # Validate backup
            result = backup_manager.validate_backup(backup_path)
            
            logger.info(
                f"Backup validation: valid={result['valid']}, "
                f"errors={len(result['errors'])}"
            )
            
            return result
        
        else:
            return {
                "error": f"Invalid action: {action}. Valid actions: create, restore, validate",
                "error_type": "ValueError"
            }
    
    except Exception as e:
        logger.error(f"Error in backup operation: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# Tool 9: Data Retention Management
# ============================================================================

@server.call_tool()
async def cleanup_old_data(
    retention_days: int,
    workspace_id: Optional[str] = None,
    delete_workspace: bool = False,
    confirm_workspace_delete: bool = False
) -> Dict[str, Any]:
    """
    Cleanup old data with flexible retention and workspace deletion options
    
    This tool provides data retention management capabilities:
    - Delete traces/memories older than specified days
    - Delete entire workspaces (with safety confirmation)
    - Free storage space and maintain database hygiene
    
    Args:
        retention_days: Number of days to retain data (older data deleted)
        workspace_id: Optional workspace to filter deletion (None = all workspaces)
        delete_workspace: If True, delete entire workspace instead of old traces
        confirm_workspace_delete: Required safety confirmation for workspace deletion
    
    Returns:
        Dictionary with deletion statistics:
        - operation: Type of operation performed
        - deleted_traces_count: Number of traces deleted
        - deleted_memories_count: Number of memory items deleted
        - freed_space_mb: Estimated freed space
        - retention_cutoff: ISO timestamp of cutoff (if applicable)
        - workspace_id: Workspace affected (if applicable)
    
    Examples:
        >>> # Delete data older than 90 days
        >>> cleanup_old_data(retention_days=90)
        
        >>> # Delete old data from specific workspace
        >>> cleanup_old_data(retention_days=60, workspace_id="abc123")
        
        >>> # Delete entire workspace (requires confirmation)
        >>> cleanup_old_data(
        ...     retention_days=0,
        ...     workspace_id="abc123",
        ...     delete_workspace=True,
        ...     confirm_workspace_delete=True
        ... )
    
    Note:
        Workspace deletion is irreversible and requires explicit confirmation
        via confirm_workspace_delete=True parameter.
    """
    logger.info(
        f"cleanup_old_data called: retention_days={retention_days}, "
        f"workspace={workspace_id}, delete_workspace={delete_workspace}"
    )
    
    try:
        if delete_workspace:
            # Workspace deletion mode
            if not workspace_id:
                return {
                    "error": "workspace_id required for workspace deletion",
                    "error_type": "ValueError"
                }
            
            if not confirm_workspace_delete:
                return {
                    "error": (
                        "Workspace deletion requires explicit confirmation. "
                        "Set confirm_workspace_delete=True to proceed. "
                        "WARNING: This operation is irreversible."
                    ),
                    "error_type": "ValueError",
                    "requires_confirmation": True
                }
            
            # Use WorkspaceManager for safe deletion
            workspace_manager = WorkspaceManager()
            
            result = workspace_manager.delete_workspace(
                workspace_id=workspace_id,
                storage_adapter=reasoning_bank.storage,
                confirm=True
            )
            
            result["operation"] = "delete_workspace"
            logger.info(
                f"Workspace deleted: {workspace_id}, "
                f"{result['deleted_traces']} traces, "
                f"{result['deleted_memories']} memories"
            )
            
            return result
        
        else:
            # Retention-based deletion mode
            result = reasoning_bank.storage.delete_old_traces(
                retention_days=retention_days,
                workspace_id=workspace_id
            )
            
            result["operation"] = "delete_old_traces"
            logger.info(
                f"Old data deleted: {result['deleted_traces_count']} traces, "
                f"{result['deleted_memories_count']} memories, "
                f"~{result['freed_space_mb']} MB freed"
            )
            
            return result
    
    except Exception as e:
        logger.error(f"Error in cleanup operation: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# Tool 10: Performance Monitoring
# ============================================================================

@server.call_tool()
async def get_performance_metrics(
    reset_after_read: bool = False
) -> Dict[str, Any]:
    """
    Get comprehensive performance metrics for the ReasoningBank system
    
    This tool provides insight into system performance including:
    - API call latencies (min/max/avg)
    - Cache hit rates
    - Token consumption
    - Embeddings generation stats
    - System uptime
    
    Args:
        reset_after_read: If True, reset metrics after reading (default: False)
    
    Returns:
        Dictionary with performance metrics:
        - uptime_seconds: System uptime
        - api_calls: Total API calls made
        - avg_api_latency: Average API latency in seconds
        - min_api_latency: Minimum API latency
        - max_api_latency: Maximum API latency
        - cache_hit_rate: Cache hit rate percentage
        - total_tokens_used: Total tokens consumed
        - embeddings_generated: Total embeddings generated
        - memories_cached: Total memories cached
        - storage_stats: Storage backend statistics
    
    Examples:
        >>> # Get current performance metrics
        >>> metrics = get_performance_metrics()
        >>> print(f"Cache hit rate: {metrics['cache_hit_rate']}%")
        
        >>> # Get metrics and reset counters
        >>> metrics = get_performance_metrics(reset_after_read=True)
    """
    logger.info(f"get_performance_metrics called: reset_after_read={reset_after_read}")
    
    try:
        # Check if performance monitor exists
        if not hasattr(reasoning_bank, 'performance_monitor'):
            # Initialize performance monitor if not exists
            from performance_optimizer import PerformanceMonitor
            reasoning_bank.performance_monitor = PerformanceMonitor()
        
        # Get performance statistics
        metrics = reasoning_bank.performance_monitor.get_statistics()
        
        # Add storage statistics
        try:
            storage_stats = reasoning_bank.storage.get_statistics()
            metrics["storage_stats"] = storage_stats
        except Exception as e:
            logger.warning(f"Could not get storage stats: {e}")
            metrics["storage_stats"] = {"error": str(e)}
        
        # Reset if requested
        if reset_after_read:
            reasoning_bank.performance_monitor.reset()
            logger.info("Performance metrics reset after read")
        
        logger.info(f"Performance metrics retrieved: {metrics['api_calls']} API calls")
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# Tool 11: Cache Management
# ============================================================================

@server.call_tool()
async def manage_cache(
    action: str,
    memory_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manage the in-memory cache for frequently accessed memories
    
    This tool provides cache management operations:
    - Get cache statistics (size, hit rate, evictions)
    - Clear entire cache
    - Invalidate specific memory from cache
    
    Args:
        action: Cache action to perform
            - "statistics": Get cache statistics
            - "clear": Clear entire cache
            - "invalidate": Invalidate specific memory (requires memory_id)
        memory_id: Memory ID to invalidate (required for "invalidate" action)
    
    Returns:
        Dictionary with cache operation results:
        - For "statistics": Cache statistics (size, hits, misses, hit_rate, etc.)
        - For "clear": Confirmation of cache clear
        - For "invalidate": Confirmation of memory invalidation
    
    Examples:
        >>> # Get cache statistics
        >>> stats = manage_cache(action="statistics")
        >>> print(f"Cache hit rate: {stats['hit_rate']}%")
        
        >>> # Clear entire cache
        >>> manage_cache(action="clear")
        
        >>> # Invalidate specific memory
        >>> manage_cache(action="invalidate", memory_id="mem_12345")
    """
    logger.info(f"manage_cache called: action={action}, memory_id={memory_id}")
    
    try:
        # Check if storage has cache enabled
        storage = reasoning_bank.storage
        
        if not hasattr(storage, 'memory_cache') or storage.memory_cache is None:
            return {
                "error": "Memory cache is not enabled in storage backend",
                "error_type": "ValueError",
                "cache_enabled": False
            }
        
        cache = storage.memory_cache
        
        if action == "statistics":
            # Get cache statistics
            stats = cache.get_statistics()
            logger.info(f"Cache statistics: {stats['hit_rate']}% hit rate")
            return stats
        
        elif action == "clear":
            # Clear entire cache
            cache.clear()
            logger.info("Cache cleared")
            return {
                "success": True,
                "action": "clear",
                "message": "Cache cleared successfully"
            }
        
        elif action == "invalidate":
            # Invalidate specific memory
            if not memory_id:
                return {
                    "error": "memory_id required for 'invalidate' action",
                    "error_type": "ValueError"
                }
            
            cache.invalidate(memory_id)
            logger.info(f"Memory {memory_id} invalidated from cache")
            return {
                "success": True,
                "action": "invalidate",
                "memory_id": memory_id,
                "message": f"Memory {memory_id} invalidated from cache"
            }
        
        else:
            return {
                "error": f"Invalid action: {action}. Valid actions: statistics, clear, invalidate",
                "error_type": "ValueError"
            }
    
    except Exception as e:
        logger.error(f"Error managing cache: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# Tool 12: Database Migration
# ============================================================================

@server.call_tool()
async def migrate_database(
    target_backend: str,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    chromadb_dir: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Migrate database from ChromaDB to Supabase or validate migration setup
    
    This tool provides database migration capabilities:
    - Migrate traces and memories from ChromaDB to Supabase
    - Dry-run validation without actual migration
    - Migration statistics and verification
    
    Args:
        target_backend: Target backend (currently only "supabase" supported)
        supabase_url: Supabase project URL (or set SUPABASE_URL env var)
        supabase_key: Supabase API key (or set SUPABASE_KEY env var)
        chromadb_dir: ChromaDB data directory (default: ./chroma_data)
        dry_run: If True, validate without actually migrating (default: False)
    
    Returns:
        Dictionary with migration results:
        - total_traces: Total traces found
        - successful: Successfully migrated traces
        - failed: Failed trace migrations
        - skipped: Skipped traces
        - verification: Post-migration verification (if not dry_run)
    
    Examples:
        >>> # Dry-run validation
        >>> result = migrate_database(
        ...     target_backend="supabase",
        ...     dry_run=True
        ... )
        
        >>> # Actual migration
        >>> result = migrate_database(
        ...     target_backend="supabase",
        ...     supabase_url="https://xxx.supabase.co",
        ...     supabase_key="your-api-key",
        ...     chromadb_dir="./chroma_data"
        ... )
    
    Note:
        - Set SUPABASE_URL and SUPABASE_KEY environment variables
        - Run supabase_schema.sql in Supabase before migration
        - Always test with dry_run=True first
    """
    logger.info(
        f"migrate_database called: target={target_backend}, "
        f"chromadb_dir={chromadb_dir}, dry_run={dry_run}"
    )
    
    try:
        if target_backend != "supabase":
            return {
                "error": f"Unsupported target backend: {target_backend}. Only 'supabase' supported.",
                "error_type": "ValueError"
            }
        
        # Import migration manager
        import os
        from migrate_to_supabase import MigrationManager
        
        # Get credentials from env if not provided
        supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not dry_run and (not supabase_url or not supabase_key):
            return {
                "error": (
                    "Supabase credentials required for migration. "
                    "Set SUPABASE_URL and SUPABASE_KEY environment variables "
                    "or provide supabase_url and supabase_key parameters."
                ),
                "error_type": "ValueError"
            }
        
        # Create migration manager
        migration_manager = MigrationManager(
            chromadb_data_dir=chromadb_dir or "./chroma_data",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            dry_run=dry_run
        )
        
        # Run migration
        stats = migration_manager.run_migration()
        
        logger.info(
            f"Migration completed: {stats['successful']}/{stats['total_traces']} "
            f"traces migrated successfully"
        )
        
        return stats
    
    except Exception as e:
        logger.error(f"Error in database migration: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# Tool 13: Prompt Compression
# ============================================================================

@server.call_tool()
async def compress_prompt(
    prompt: str,
    max_tokens: int = 12000,
    compression_ratio: float = 0.7
) -> Dict[str, Any]:
    """
    Compress prompts to reduce token consumption while preserving meaning
    
    This tool provides prompt compression for token optimization:
    - Remove redundant whitespace
    - Compress code blocks (remove comments, empty lines)
    - Intelligent truncation preserving structure
    - Token count estimation and reduction stats
    
    Args:
        prompt: Original prompt text to compress
        max_tokens: Maximum tokens allowed (default: 12000)
        compression_ratio: Target compression ratio 0.0-1.0 (default: 0.7)
    
    Returns:
        Dictionary with compression results:
        - compressed_prompt: Compressed prompt text
        - original_tokens: Estimated original token count
        - compressed_tokens: Estimated compressed token count
        - reduction_percentage: Percentage reduction
        - compression_applied: Whether compression was needed
    
    Examples:
        >>> # Compress a long prompt
        >>> result = compress_prompt(
        ...     prompt="Very long prompt text...",
        ...     max_tokens=8000
        ... )
        >>> print(result['compressed_prompt'])
        >>> print(f"Reduced by {result['reduction_percentage']}%")
        
        >>> # Aggressive compression
        >>> result = compress_prompt(
        ...     prompt=long_text,
        ...     max_tokens=4000,
        ...     compression_ratio=0.5
        ... )
    
    Note:
        - Compression preserves structure and key information
        - Code blocks are compressed by removing comments
        - Token estimation uses 4 chars per token heuristic
    """
    logger.info(
        f"compress_prompt called: prompt_length={len(prompt)}, "
        f"max_tokens={max_tokens}, compression_ratio={compression_ratio}"
    )
    
    try:
        from performance_optimizer import PromptCompressor
        
        # Create compressor
        compressor = PromptCompressor(
            max_tokens=max_tokens,
            compression_ratio=compression_ratio
        )
        
        # Estimate original tokens
        original_tokens = len(prompt) // 4
        
        # Compress prompt
        compressed = compressor.compress(prompt)
        
        # Estimate compressed tokens
        compressed_tokens = len(compressed) // 4
        
        # Calculate reduction
        if original_tokens > 0:
            reduction = (1 - compressed_tokens / original_tokens) * 100
        else:
            reduction = 0.0
        
        compression_applied = len(compressed) < len(prompt)
        
        logger.info(
            f"Prompt compressed: {original_tokens} -> {compressed_tokens} tokens "
            f"({reduction:.1f}% reduction)"
        )
        
        return {
            "compressed_prompt": compressed,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "reduction_percentage": round(reduction, 2),
            "compression_applied": compression_applied,
            "original_length": len(prompt),
            "compressed_length": len(compressed)
        }
    
    except Exception as e:
        logger.error(f"Error compressing prompt: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """
    Main entry point for the MCP server
    
    Starts the server with stdio transport and lifespan management.
    """
    logger.info("Starting ReasoningBank MCP Server...")
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    
    # Run the server
    asyncio.run(main())
