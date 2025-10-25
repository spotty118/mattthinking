FROM python:3.11-slim

WORKDIR /app

# Python environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HNSWLIB_NO_NATIVE=1

# Install system dependencies required for ChromaDB and sentence-transformers
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create data directories for persistent storage
RUN mkdir -p /app/chroma_data /app/traces /app/logs

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY reasoning_bank_core.py .
COPY iterative_agent.py .
COPY reasoning_bank_server.py .
COPY responses_alpha_client.py .
COPY cached_llm_client.py .
COPY schemas.py .
COPY config.py .
COPY retry_utils.py .
COPY exceptions.py .
COPY logging_config.py .
COPY supabase_storage.py .
COPY storage_adapter.py .
COPY passive_learner.py .
COPY workspace_manager.py .
COPY knowledge_retrieval.py .

# Copy optional files if they exist
COPY .env.example .

# Configure default environment variables
ENV REASONING_BANK_DATA=/app/chroma_data \
    REASONING_BANK_TRACES=/app/traces \
    MCP_TRANSPORT=stdio \
    STORAGE_BACKEND=chromadb \
    REASONING_MODEL=google/gemini-2.5-pro \
    REASONING_EFFORT=medium \
    MAX_ITERATIONS=3 \
    ENABLE_CACHE=true

# Health check to verify the container is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import chromadb; print('OK')" || exit 1

# Run the MCP server
CMD ["python", "reasoning_bank_server.py"]
