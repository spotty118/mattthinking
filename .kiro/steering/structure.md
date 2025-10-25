# Project Structure

## Directory Layout

```
reasoning-bank-mcp/
├── reasoning_bank_server.py      # MCP server entry point with tool definitions
├── reasoning_bank_core.py        # Core memory management and trajectory judging
├── iterative_agent.py            # Think→Evaluate→Refine loop implementation
├── responses_alpha_client.py     # OpenRouter Responses API client
├── cached_llm_client.py          # LLM response caching layer
├── passive_learner.py            # Automatic Q&A knowledge capture
├── workspace_manager.py          # Multi-tenant workspace isolation
├── knowledge_retrieval.py        # Knowledge retrieval from passive learning
├── storage_adapter.py            # Abstract storage interface
├── supabase_storage.py           # Supabase storage implementation
├── schemas.py                    # Pydantic models and validation
├── config.py                     # Configuration management
├── retry_utils.py                # API retry logic with exponential backoff
├── logging_config.py             # Structured logging setup
├── exceptions.py                 # Custom exception classes
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container image definition
├── docker-compose.yml            # Docker orchestration
├── .env.example                  # Environment variable template
├── chroma_data/                  # ChromaDB persistent storage (local)
├── traces/                       # Reasoning trace JSON files
└── logs/                         # Application logs
```

## Key Modules

### Server Layer
- `reasoning_bank_server.py`: FastMCP server exposing tools (`solve_coding_task`, `retrieve_memories`, `get_statistics`, etc.)

### Core Logic
- `reasoning_bank_core.py`: Memory storage, retrieval, trajectory judging, memory extraction
- `iterative_agent.py`: Iterative reasoning loop with MaTTS support (parallel and sequential modes)

### Storage
- `storage_adapter.py`: Abstract interface for pluggable storage backends
- `supabase_storage.py`: Cloud storage implementation
- ChromaDB: Local vector database (embedded in `reasoning_bank_core.py`)

### LLM Integration
- `responses_alpha_client.py`: Wrapper for OpenRouter Responses API with reasoning token tracking
- `cached_llm_client.py`: Caching layer to reduce API costs

### Learning
- `passive_learner.py`: Automatic knowledge capture from conversations
- `knowledge_retrieval.py`: Retrieve and format learned knowledge

### Infrastructure
- `config.py`: Centralized configuration with Pydantic validation
- `retry_utils.py`: Exponential backoff retry decorator
- `logging_config.py`: Structured logging with context
- `schemas.py`: Type-safe data models for all entities

## Code Organization Patterns

### Separation of Concerns
- Server layer handles MCP protocol and tool definitions
- Core layer handles business logic (memory, reasoning)
- Storage layer is abstracted for multiple backends
- LLM layer handles API communication with retry/cache

### Configuration Management
- All settings in `config.py` with environment variable overrides
- Pydantic validation ensures type safety
- Default values for all optional settings

### Error Handling
- Custom exceptions in `exceptions.py`
- Retry logic with exponential backoff for transient failures
- Structured logging for debugging

### Data Models
- All entities defined as Pydantic models in `schemas.py`
- JSON schema generation for MCP tools
- Runtime validation of inputs/outputs

## Testing Files

- `test_server.py`: MCP server integration tests
- `test_phase1_phase2.py`: Core functionality tests
- `test_responses_api.py`: API client tests
- `verify_deployment.py`: Deployment verification script
