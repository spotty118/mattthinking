"""
Specification-driven schemas for ReasoningBank MCP Server

This module provides Pydantic models and JSON schemas for:
- Data structures (MemoryItem, ReasoningTrace, Config)
- MCP tool inputs/outputs
- API contracts

Benefits:
- Runtime validation
- Auto-generated JSON schemas for MCP tools
- Type safety
- Documentation generation
- API contract enforcement
"""

from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import uuid


# ============================================================================
# Enums for type safety
# ============================================================================

class OutcomeType(str, Enum):
    """Task outcome classification"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class DifficultyLevel(str, Enum):
    """Task difficulty classification"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ReasoningEffort(str, Enum):
    """Reasoning effort for LLM calls"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StorageBackend(str, Enum):
    """Storage backend type"""
    CHROMADB = "chromadb"
    SUPABASE = "supabase"


class MaTTSMode(str, Enum):
    """Memory-Aware Test-Time Scaling modes"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


# ============================================================================
# Core Data Models
# ============================================================================

class MemoryItemSchema(BaseModel):
    """
    Structured memory item with genealogy tracking
    
    Represents a single unit of learned knowledge from successful or failed
    task attempts. Supports evolution tracking and error context.
    """
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for memory item"
    )
    title: str = Field(
        ...,
        description="Concise title (5-10 words)",
        min_length=5,
        max_length=200
    )
    description: str = Field(
        ...,
        description="Brief one-sentence summary",
        min_length=10,
        max_length=500
    )
    content: str = Field(
        ...,
        description="Detailed memory content with patterns and insights",
        min_length=20
    )
    
    # Error context for failure learning
    error_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Bug/error information if this memory is from a failure"
    )
    
    # Genealogy tracking
    parent_memory_id: Optional[str] = Field(
        None,
        description="ID of parent memory this evolved from"
    )
    derived_from: Optional[List[str]] = Field(
        default_factory=list,
        description="List of memory IDs this was derived from"
    )
    evolution_stage: int = Field(
        default=0,
        description="Evolution level (0 = original, 1+ = refined)",
        ge=0
    )
    
    # Case-based reasoning metadata
    pattern_tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Pattern classification tags"
    )
    difficulty_level: Optional[DifficultyLevel] = Field(
        None,
        description="Task difficulty classification"
    )
    domain_category: Optional[str] = Field(
        None,
        description="Domain classification (e.g., algorithms, api_usage)"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    
    @field_validator("pattern_tags")
    @classmethod
    def validate_tags(cls, v):
        """Limit to 10 tags maximum"""
        if len(v) > 10:
            raise ValueError("Maximum 10 pattern tags allowed")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Binary Search Implementation Pattern",
                "description": "Use left/right pointers to efficiently search sorted arrays",
                "content": "Pattern: Binary search with two-pointer approach...",
                "pattern_tags": ["algorithms", "binary_search", "optimization"],
                "difficulty_level": "moderate",
                "domain_category": "algorithms"
            }
        }


class TrajectoryStep(BaseModel):
    """Single step in reasoning trajectory"""
    iteration: int = Field(..., description="Step number in trajectory", ge=1)
    thought: str = Field(..., description="Reasoning at this step")
    action: str = Field(..., description="Action taken (generate, refine, etc.)")
    output: str = Field(..., description="Output produced")
    output_hash: Optional[str] = Field(None, description="Hash for loop detection")
    refinement_stage: Optional[int] = Field(None, description="Refinement stage if applicable")
    trajectory_id: Optional[int] = Field(None, description="Trajectory ID for parallel MaTTS")
    previous_score: Optional[float] = Field(None, description="Score before this step", ge=0.0, le=1.0)
    reflection: Optional[str] = Field(None, description="Self-reflection on this step")


class ReasoningTraceSchema(BaseModel):
    """
    Complete reasoning trace with trajectory and extracted memories
    """
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique trace identifier"
    )
    task: str = Field(..., description="Original task description", min_length=5)
    trajectory: List[TrajectoryStep] = Field(..., description="Step-by-step reasoning process")
    outcome: OutcomeType = Field(..., description="Task outcome classification")
    memory_items: List[MemoryItemSchema] = Field(
        default_factory=list,
        description="Extracted memory items from this trace"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Trace creation timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (scores, iterations, etc.)"
    )
    
    # Genealogy
    parent_trace_id: Optional[str] = Field(None, description="Parent trace ID")
    related_trace_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="Related trace IDs"
    )
    
    @field_validator("trajectory")
    @classmethod
    def validate_trajectory(cls, v):
        """Ensure at least one trajectory step"""
        if not v:
            raise ValueError("Trajectory must have at least one step")
        return v


# ============================================================================
# Configuration Models
# ============================================================================

class TokenBudgetConfig(BaseModel):
    """Token allocation for different operations"""
    max_output_tokens: int = Field(
        default=9000,
        description="Maximum output tokens per LLM call",
        ge=100,
        le=9000
    )
    max_prompt_tokens: int = Field(
        default=12000,
        description="Maximum prompt tokens",
        ge=100,
        le=100000
    )
    generation_tokens: int = Field(
        default=8000,
        description="Tokens for solution generation",
        ge=100
    )
    evaluation_tokens: int = Field(
        default=3000,
        description="Tokens for solution evaluation",
        ge=100
    )
    judgment_tokens: int = Field(
        default=4000,
        description="Tokens for trajectory judgment",
        ge=100
    )
    memory_extraction_tokens: int = Field(
        default=6000,
        description="Tokens for memory extraction",
        ge=100
    )
    truncation_threshold: int = Field(
        default=12000,
        description="Token threshold for truncation"
    )
    truncation_head_ratio: float = Field(
        default=0.6,
        description="Ratio of content to preserve at head",
        ge=0.0,
        le=1.0
    )


class ReasoningBankConfig(BaseModel):
    """
    Comprehensive configuration for ReasoningBank system
    
    All settings can be overridden via environment variables.
    """
    # Model configuration
    model: str = Field(
        default="google/gemini-2.5-pro",
        description="LLM model identifier"
    )
    reasoning_effort: ReasoningEffort = Field(
        default=ReasoningEffort.MEDIUM,
        description="Reasoning effort level for reasoning models"
    )
    api_key: Optional[str] = Field(
        None,
        description="OpenRouter API key (or from OPENROUTER_API_KEY env)"
    )
    
    # Token management
    token_budget: TokenBudgetConfig = Field(
        default_factory=TokenBudgetConfig,
        description="Token allocation settings"
    )
    
    # Memory configuration
    retrieval_k: int = Field(
        default=3,
        description="Number of memories to retrieve",
        ge=1,
        le=20
    )
    max_memory_items: int = Field(
        default=3,
        description="Maximum memory items to extract per trace",
        ge=1,
        le=10
    )
    
    # Iteration configuration
    max_iterations: int = Field(
        default=3,
        description="Maximum refinement iterations",
        ge=1,
        le=10
    )
    success_threshold: float = Field(
        default=0.8,
        description="Quality threshold for success",
        ge=0.0,
        le=1.0
    )
    
    # Temperature settings
    temperature_generate: float = Field(
        default=0.7,
        description="Temperature for generation",
        ge=0.0,
        le=2.0
    )
    temperature_judge: float = Field(
        default=0.0,
        description="Temperature for judging (deterministic)",
        ge=0.0,
        le=2.0
    )
    
    # Storage backend selection
    storage_backend: StorageBackend = Field(
        default=StorageBackend.CHROMADB,
        description="Storage backend to use (chromadb or supabase)"
    )
    
    # ChromaDB paths (used if storage_backend=chromadb)
    persist_directory: str = Field(
        default="./chroma_data",
        description="ChromaDB storage directory"
    )
    traces_directory: str = Field(
        default="./traces",
        description="Traces storage directory"
    )
    collection_name: str = Field(
        default="reasoning_memories",
        description="ChromaDB collection name"
    )
    
    # Supabase configuration (used if storage_backend=supabase)
    supabase_url: Optional[str] = Field(
        None,
        description="Supabase project URL (or from SUPABASE_URL env)"
    )
    supabase_key: Optional[str] = Field(
        None,
        description="Supabase API key (or from SUPABASE_KEY env)"
    )
    supabase_traces_table: str = Field(
        default="reasoning_traces",
        description="Supabase table name for traces"
    )
    supabase_memories_table: str = Field(
        default="memory_items",
        description="Supabase table name for memory items"
    )
    
    # Retry configuration
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for API calls",
        ge=1,
        le=10
    )
    retry_min_wait: int = Field(
        default=2,
        description="Minimum wait between retries (seconds)",
        ge=1
    )
    retry_max_wait: int = Field(
        default=10,
        description="Maximum wait between retries (seconds)",
        ge=1
    )
    
    # Cache configuration
    enable_cache: bool = Field(
        default=True,
        description="Enable LLM response caching"
    )
    cache_size: int = Field(
        default=100,
        description="Maximum cache entries",
        ge=10,
        le=1000
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache entry TTL in seconds",
        ge=60
    )
    
    @model_validator(mode='after')
    def validate_retry_config(self):
        """Ensure retry max >= min"""
        if self.retry_max_wait < self.retry_min_wait:
            raise ValueError("retry_max_wait must be >= retry_min_wait")
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "google/gemini-2.5-pro",
                "reasoning_effort": "medium",
                "max_iterations": 3,
                "success_threshold": 0.8,
                "retrieval_k": 5
            }
        }


# ============================================================================
# MCP Tool Schemas
# ============================================================================

class SolveCodingTaskInput(BaseModel):
    """Input schema for solve_coding_task MCP tool"""
    task: str = Field(
        ...,
        description="The coding task description",
        min_length=10
    )
    use_memory: bool = Field(
        default=True,
        description="Retrieve relevant past experiences"
    )
    enable_matts: bool = Field(
        default=False,
        description="Enable Memory-Aware Test-Time Scaling"
    )
    matts_k: int = Field(
        default=3,
        description="Number of parallel solution attempts (if MaTTS enabled)",
        ge=2,
        le=10
    )
    matts_mode: MaTTSMode = Field(
        default=MaTTSMode.PARALLEL,
        description="MaTTS execution mode"
    )
    store_result: bool = Field(
        default=True,
        description="Store the result as new memory"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "Write a Python function to calculate fibonacci numbers",
                "use_memory": True,
                "enable_matts": False,
                "matts_k": 3,
                "store_result": True
            }
        }


class SolveCodingTaskOutput(BaseModel):
    """Output schema for solve_coding_task MCP tool"""
    success: bool = Field(..., description="Whether task was completed successfully")
    output: str = Field(..., description="Solution code or text")
    trajectory: List[TrajectoryStep] = Field(..., description="Step-by-step reasoning process")
    score: float = Field(..., description="Quality score (0.0-1.0)", ge=0.0, le=1.0)
    iterations: int = Field(..., description="Number of iterations taken", ge=1)
    memories_extracted: int = Field(..., description="Number of memories extracted", ge=0)
    judge_reasoning: str = Field(..., description="Judge's evaluation reasoning")
    all_outputs: Optional[List[str]] = Field(
        None,
        description="All outputs if MaTTS parallel mode used"
    )
    selected_trajectory: Optional[int] = Field(
        None,
        description="Selected trajectory index if MaTTS used"
    )
    contrast_analysis: Optional[str] = Field(
        None,
        description="Self-contrast analysis if MaTTS used"
    )
    refinements: Optional[int] = Field(
        None,
        description="Number of refinements if MaTTS sequential mode used"
    )


class RetrieveMemoriesInput(BaseModel):
    """Input schema for retrieve_memories MCP tool"""
    query: str = Field(
        ...,
        description="Search query",
        min_length=3
    )
    n_results: int = Field(
        default=5,
        description="Number of memories to retrieve",
        ge=1,
        le=20
    )
    include_failures: bool = Field(
        default=True,
        description="Include memories from failed attempts"
    )
    domain_filter: Optional[str] = Field(
        None,
        description="Filter by domain category"
    )


class RetrieveMemoriesOutput(BaseModel):
    """Output schema for retrieve_memories MCP tool"""
    memories: List[MemoryItemSchema] = Field(..., description="Retrieved memory items")
    total_found: int = Field(..., description="Total memories found", ge=0)
    has_error_warnings: bool = Field(..., description="Whether any contain error context")


class GetStatisticsOutput(BaseModel):
    """Output schema for get_statistics MCP tool"""
    total_traces: int = Field(..., ge=0)
    success_traces: int = Field(..., ge=0)
    failure_traces: int = Field(..., ge=0)
    total_memories: int = Field(..., ge=0)
    memories_with_errors: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0.0, le=100.0)
    avg_evolution_stage: float = Field(..., ge=0.0)
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict)
    domain_distribution: Dict[str, int] = Field(default_factory=dict)
    pattern_tag_frequency: Dict[str, int] = Field(default_factory=dict)


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_memory_item(data: Dict[str, Any]) -> MemoryItemSchema:
    """
    Validate and construct MemoryItem from dict
    
    Raises:
        ValidationError: If validation fails with detailed error messages
    """
    return MemoryItemSchema(**data)


def validate_reasoning_trace(data: Dict[str, Any]) -> ReasoningTraceSchema:
    """
    Validate and construct ReasoningTrace from dict
    
    Raises:
        ValidationError: If validation fails with detailed error messages
    """
    return ReasoningTraceSchema(**data)


def validate_config(data: Dict[str, Any]) -> ReasoningBankConfig:
    """
    Validate and construct ReasoningBankConfig from dict
    
    Raises:
        ValidationError: If validation fails with detailed error messages
    """
    return ReasoningBankConfig(**data)


# ============================================================================
# JSON Schema Generation
# ============================================================================

def get_mcp_tool_schemas() -> Dict[str, Dict]:
    """
    Generate JSON schemas for all MCP tools
    
    Returns:
        Dict mapping tool names to their input/output schemas
    """
    return {
        "solve_coding_task": {
            "input_schema": SolveCodingTaskInput.model_json_schema(),
            "output_schema": SolveCodingTaskOutput.model_json_schema()
        },
        "retrieve_memories": {
            "input_schema": RetrieveMemoriesInput.model_json_schema(),
            "output_schema": RetrieveMemoriesOutput.model_json_schema()
        },
        "get_statistics": {
            "output_schema": GetStatisticsOutput.model_json_schema()
        }
    }


def export_schemas_to_file(filepath: str = "mcp_tool_schemas.json"):
    """Export all MCP tool schemas to JSON file"""
    import json
    schemas = get_mcp_tool_schemas()
    with open(filepath, 'w') as f:
        json.dump(schemas, f, indent=2)
    print(f"Schemas exported to {filepath}")


if __name__ == "__main__":
    # Generate and print example schemas
    print("=== MCP Tool Schemas ===\n")
    schemas = get_mcp_tool_schemas()
    import json
    print(json.dumps(schemas, indent=2))
    
    # Example validation
    print("\n=== Example Validation ===\n")
    example_memory = {
        "title": "Binary Search Pattern",
        "description": "Efficient search in sorted arrays",
        "content": "Use left/right pointers...",
        "pattern_tags": ["algorithms", "binary_search"],
        "difficulty_level": "moderate"
    }
    validated = validate_memory_item(example_memory)
    print(f"Validated MemoryItem: {validated.id}")
    print(f"Title: {validated.title}")
