# Technology Stack

## Core Technologies

- **Language**: Python 3.9+
- **MCP Framework**: FastMCP (mcp>=1.0.0)
- **Vector Database**: ChromaDB (>=0.6.3) or Supabase (>=2.0.0)
- **Embeddings**: sentence-transformers (>=2.2.0)
- **LLM API**: OpenRouter Responses API Alpha
- **Validation**: Pydantic (>=2.0.0)
- **Logging**: structlog (>=24.1.0)
- **Retry Logic**: tenacity (>=8.2.3)

## Deployment

- **Containerization**: Docker + Docker Compose
- **Storage**: Persistent volumes for ChromaDB data and reasoning traces
- **Transport**: stdio (default) or streamable-http

## Common Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENROUTER_API_KEY=your_key_here
export REASONING_BANK_DATA=./chroma_data
export REASONING_BANK_TRACES=./traces

# Run server locally
python reasoning_bank_server.py
```

### Docker Deployment

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f reasoning-bank

# Stop service
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

### Testing

```bash
# Run test suite
python test_server.py
python test_phase1_phase2.py
python test_responses_api.py

# Verify deployment
python verify_deployment.py
```

### Database Migration

```bash
# Migrate from ChromaDB to Supabase
python migrate_to_supabase.py
```

## Configuration

All configuration is managed through environment variables (see `.env.example`). Key settings:

- `OPENROUTER_API_KEY`: Required for LLM calls
- `STORAGE_BACKEND`: "chromadb" (local) or "supabase" (cloud)
- `REASONING_EFFORT`: "minimal", "low", "medium", "high"
- `MAX_ITERATIONS`: Maximum refinement iterations (default: 3)
- `ENABLE_CACHE`: Enable LLM response caching (default: true)

## API Integration

The system uses OpenRouter's Responses API Alpha which provides:
- Extended reasoning token support (up to 9000 output tokens)
- Configurable reasoning effort levels
- Automatic reasoning token tracking
- Support for models like google/gemini-2.5-pro
