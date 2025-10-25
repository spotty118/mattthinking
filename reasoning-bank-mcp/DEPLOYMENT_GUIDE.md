# ReasoningBank MCP Server - Deployment Guide

This guide provides step-by-step instructions for deploying the ReasoningBank MCP Server in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Deployment](#local-development-deployment)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Supabase Cloud Deployment](#supabase-cloud-deployment)
- [Configuration](#configuration)
- [Verification](#verification)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **Python 3.9+**: Check with `python --version`
- **pip**: Python package manager
- **OpenRouter API Key**: Sign up at [openrouter.ai](https://openrouter.ai/)

### Optional (for Docker deployment)

- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

### Optional (for Supabase deployment)

- **Supabase Account**: Sign up at [supabase.com](https://supabase.com/)
- **Supabase Project**: Create a new project

## Local Development Deployment

### Step 1: Clone and Navigate

```bash
cd reasoning-bank-mcp
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

Add your OpenRouter API key:

```env
OPENROUTER_API_KEY=your_api_key_here
REASONING_BANK_DATA=./chroma_data
REASONING_BANK_TRACES=./traces
DEFAULT_MODEL=google/gemini-2.5-pro
DEFAULT_REASONING_EFFORT=medium
MAX_ITERATIONS=3
ENABLE_CACHE=true
CACHE_TTL=3600
STORAGE_BACKEND=chromadb
```

### Step 5: Create Data Directories

```bash
mkdir -p chroma_data traces logs
```

### Step 6: Run the Server

```bash
python reasoning_bank_server.py
```

You should see output indicating the server has started successfully:

```
INFO - ReasoningBank MCP Server starting...
INFO - API key validated successfully
INFO - ChromaDB initialized at ./chroma_data
INFO - Server ready on stdio transport
```

### Step 7: Test the Deployment

In a new terminal, run the verification script:

```bash
python verify_deployment.py
```

Expected output:

```
✅ Environment variables present
✅ File structure complete (11 required files)
✅ Python imports successful (7 modules)
✅ Phase 1 enhancements present (4 items)
✅ Phase 2 enhancements present (2 items)
✅ Dockerfile correctness verified
```

## Docker Deployment

### Step 1: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your API key
nano .env
```

### Step 2: Build the Docker Image

```bash
docker-compose build
```

This will:
- Pull the Python 3.11 base image
- Install all dependencies from requirements.txt
- Copy application files
- Create data directories

### Step 3: Start the Service

```bash
docker-compose up -d
```

The `-d` flag runs the container in detached mode (background).

### Step 4: Verify the Service is Running

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f reasoning-bank
```

Expected output:

```
reasoning-bank-mcp | INFO - ReasoningBank MCP Server starting...
reasoning-bank-mcp | INFO - API key validated successfully
reasoning-bank-mcp | INFO - ChromaDB initialized at /app/chroma_data
reasoning-bank-mcp | INFO - Server ready on stdio transport
```

### Step 5: Test the Deployment

```bash
# Run verification inside container
docker-compose exec reasoning-bank python verify_deployment.py
```

### Step 6: Stop the Service

```bash
docker-compose down
```

To stop and remove volumes (WARNING: deletes all data):

```bash
docker-compose down -v
```

## Production Deployment

### Step 1: Prepare Production Environment

```bash
# Create production directory
mkdir -p /opt/reasoning-bank-mcp
cd /opt/reasoning-bank-mcp

# Copy application files
# (use git clone or scp to transfer files)
```

### Step 2: Configure Production Settings

```bash
# Create production .env file
nano .env
```

Production configuration:

```env
# API Configuration
OPENROUTER_API_KEY=your_production_api_key_here
DEFAULT_MODEL=google/gemini-2.5-pro
DEFAULT_REASONING_EFFORT=medium

# Storage Configuration
REASONING_BANK_DATA=/var/lib/reasoning-bank/chroma_data
REASONING_BANK_TRACES=/var/lib/reasoning-bank/traces
STORAGE_BACKEND=chromadb

# Performance Configuration
MAX_ITERATIONS=3
ENABLE_CACHE=true
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/reasoning-bank/server.log
```

### Step 3: Create Data Directories with Proper Permissions

```bash
sudo mkdir -p /var/lib/reasoning-bank/chroma_data
sudo mkdir -p /var/lib/reasoning-bank/traces
sudo mkdir -p /var/log/reasoning-bank

# Set ownership (adjust user as needed)
sudo chown -R reasoning-bank:reasoning-bank /var/lib/reasoning-bank
sudo chown -R reasoning-bank:reasoning-bank /var/log/reasoning-bank
```

### Step 4: Configure Docker Compose for Production

Edit `docker-compose.yml`:

```yaml
version: '3.8'

services:
  reasoning-bank:
    build: .
    container_name: reasoning-bank-mcp-prod
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - REASONING_BANK_DATA=/app/chroma_data
      - REASONING_BANK_TRACES=/app/traces
      - DEFAULT_MODEL=${DEFAULT_MODEL}
      - DEFAULT_REASONING_EFFORT=${DEFAULT_REASONING_EFFORT}
      - ENABLE_CACHE=${ENABLE_CACHE}
      - CACHE_TTL=${CACHE_TTL}
    volumes:
      - /var/lib/reasoning-bank/chroma_data:/app/chroma_data
      - /var/lib/reasoning-bank/traces:/app/traces
      - /var/log/reasoning-bank:/app/logs
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Step 5: Deploy with Docker Compose

```bash
docker-compose up -d --build
```

### Step 6: Configure Log Rotation

Create `/etc/logrotate.d/reasoning-bank`:

```
/var/log/reasoning-bank/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 reasoning-bank reasoning-bank
}
```

### Step 7: Set Up Health Monitoring

Create a health check script `/opt/reasoning-bank-mcp/health_check.sh`:

```bash
#!/bin/bash

# Check if container is running
if ! docker-compose ps | grep -q "Up"; then
    echo "ERROR: Container is not running"
    exit 1
fi

# Check logs for errors
if docker-compose logs --tail=50 | grep -q "ERROR"; then
    echo "WARNING: Errors found in logs"
    exit 1
fi

echo "OK: Service is healthy"
exit 0
```

Make it executable:

```bash
chmod +x /opt/reasoning-bank-mcp/health_check.sh
```

Add to crontab for periodic checks:

```bash
# Check health every 5 minutes
*/5 * * * * /opt/reasoning-bank-mcp/health_check.sh >> /var/log/reasoning-bank/health.log 2>&1
```

## Supabase Cloud Deployment

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com/)
2. Create a new project
3. Note your project URL and API key

### Step 2: Set Up Database Schema

```bash
# Copy the schema file
cat supabase_schema.sql

# Execute in Supabase SQL Editor:
# 1. Go to your Supabase project
# 2. Navigate to SQL Editor
# 3. Paste the contents of supabase_schema.sql
# 4. Run the query
```

### Step 3: Configure Environment for Supabase

```bash
nano .env
```

Add Supabase configuration:

```env
# Storage Backend
STORAGE_BACKEND=supabase

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_api_key_here

# Other settings remain the same
OPENROUTER_API_KEY=your_api_key_here
DEFAULT_MODEL=google/gemini-2.5-pro
```

### Step 4: Migrate Existing Data (Optional)

If you have existing ChromaDB data:

```bash
python migrate_to_supabase.py
```

This will:
- Connect to your local ChromaDB
- Extract all memories and traces
- Upload to Supabase
- Verify migration success

### Step 5: Deploy with Supabase Backend

```bash
docker-compose up -d --build
```

### Step 6: Verify Supabase Connection

```bash
# Check logs for Supabase connection
docker-compose logs -f reasoning-bank | grep -i supabase
```

Expected output:

```
INFO - Connected to Supabase at https://your-project.supabase.co
INFO - Supabase storage backend initialized
```

## Configuration

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | ✅ | - | OpenRouter API key |
| `REASONING_BANK_DATA` | ❌ | `./chroma_data` | ChromaDB storage path |
| `REASONING_BANK_TRACES` | ❌ | `./traces` | Trace storage path |
| `DEFAULT_MODEL` | ❌ | `google/gemini-2.5-pro` | LLM model |
| `DEFAULT_REASONING_EFFORT` | ❌ | `medium` | Reasoning effort level |
| `MAX_ITERATIONS` | ❌ | `3` | Max refinement iterations |
| `ENABLE_CACHE` | ❌ | `true` | Enable response caching |
| `CACHE_TTL` | ❌ | `3600` | Cache TTL (seconds) |
| `CACHE_MAX_SIZE` | ❌ | `100` | Max cache entries |
| `STORAGE_BACKEND` | ❌ | `chromadb` | Storage backend type |
| `SUPABASE_URL` | ❌ | - | Supabase project URL |
| `SUPABASE_KEY` | ❌ | - | Supabase API key |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |

### Model Options

Supported models via OpenRouter:

- `google/gemini-2.5-pro` (recommended)
- `google/gemini-2.0-flash-thinking-exp`
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4-turbo`

### Reasoning Effort Levels

- `minimal`: Fastest, least thorough
- `low`: Fast with basic reasoning
- `medium`: Balanced (recommended)
- `high`: Slower, most thorough

## Verification

### Automated Verification

```bash
python verify_deployment.py
```

### Manual Verification

1. **Check environment variables**:
```bash
docker-compose exec reasoning-bank env | grep OPENROUTER_API_KEY
```

2. **Check file structure**:
```bash
docker-compose exec reasoning-bank ls -la
```

3. **Test Python imports**:
```bash
docker-compose exec reasoning-bank python -c "import reasoning_bank_server; print('OK')"
```

4. **Check ChromaDB**:
```bash
docker-compose exec reasoning-bank ls -la chroma_data/
```

5. **View logs**:
```bash
docker-compose logs -f reasoning-bank
```

## Monitoring

### Log Monitoring

```bash
# Real-time logs
docker-compose logs -f reasoning-bank

# Last 100 lines
docker-compose logs --tail=100 reasoning-bank

# Search for errors
docker-compose logs reasoning-bank | grep ERROR
```

### Performance Monitoring

```bash
# Container resource usage
docker stats reasoning-bank-mcp

# Disk usage
du -sh /var/lib/reasoning-bank/chroma_data
du -sh /var/lib/reasoning-bank/traces
```

### Health Checks

```bash
# Check container health
docker-compose ps

# Check API connectivity
docker-compose exec reasoning-bank python -c "
from responses_alpha_client import ResponsesAPIClient
import os
client = ResponsesAPIClient(os.getenv('OPENROUTER_API_KEY'))
print('API connection OK')
"
```

## Backup and Recovery

### Backup ChromaDB Data

```bash
# Create backup directory
mkdir -p backups

# Backup ChromaDB
tar -czf backups/chroma_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    /var/lib/reasoning-bank/chroma_data/

# Backup traces
tar -czf backups/traces_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    /var/lib/reasoning-bank/traces/
```

### Automated Backup Script

Create `/opt/reasoning-bank-mcp/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/reasoning-bank-mcp/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup ChromaDB
tar -czf $BACKUP_DIR/chroma_$DATE.tar.gz \
    /var/lib/reasoning-bank/chroma_data/

# Backup traces
tar -czf $BACKUP_DIR/traces_$DATE.tar.gz \
    /var/lib/reasoning-bank/traces/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/reasoning-bank-mcp/backup.sh >> /var/log/reasoning-bank/backup.log 2>&1
```

### Restore from Backup

```bash
# Stop the service
docker-compose down

# Restore ChromaDB
tar -xzf backups/chroma_backup_YYYYMMDD_HHMMSS.tar.gz -C /

# Restore traces
tar -xzf backups/traces_backup_YYYYMMDD_HHMMSS.tar.gz -C /

# Restart the service
docker-compose up -d
```

## Troubleshooting

### Container Won't Start

**Symptom**: `docker-compose up` fails

**Solutions**:

1. Check logs:
```bash
docker-compose logs reasoning-bank
```

2. Verify environment variables:
```bash
cat .env | grep OPENROUTER_API_KEY
```

3. Check port conflicts:
```bash
docker-compose ps
```

4. Rebuild image:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### API Key Errors

**Symptom**: `APIKeyError: OPENROUTER_API_KEY not set`

**Solutions**:

1. Verify .env file exists:
```bash
ls -la .env
```

2. Check API key is set:
```bash
grep OPENROUTER_API_KEY .env
```

3. Restart container:
```bash
docker-compose restart
```

### ChromaDB Connection Issues

**Symptom**: `Cannot connect to ChromaDB`

**Solutions**:

1. Check data directory permissions:
```bash
ls -la /var/lib/reasoning-bank/chroma_data/
```

2. Verify volume mounts:
```bash
docker inspect reasoning-bank-mcp | grep Mounts -A 10
```

3. Recreate data directory:
```bash
docker-compose down
sudo rm -rf /var/lib/reasoning-bank/chroma_data
sudo mkdir -p /var/lib/reasoning-bank/chroma_data
docker-compose up -d
```

### Memory Issues

**Symptom**: Container crashes or OOM errors

**Solutions**:

1. Increase Docker memory limit in `docker-compose.yml`:
```yaml
services:
  reasoning-bank:
    mem_limit: 4g
    memswap_limit: 4g
```

2. Monitor memory usage:
```bash
docker stats reasoning-bank-mcp
```

3. Clear cache:
```bash
docker-compose exec reasoning-bank python -c "
from cached_llm_client import CachedLLMClient
# Cache will be cleared on restart
"
docker-compose restart
```

### Slow Performance

**Symptom**: Tasks take too long to complete

**Solutions**:

1. Enable caching:
```env
ENABLE_CACHE=true
```

2. Reduce reasoning effort:
```env
DEFAULT_REASONING_EFFORT=low
```

3. Reduce max iterations:
```env
MAX_ITERATIONS=2
```

4. Check API latency:
```bash
docker-compose logs reasoning-bank | grep "API call took"
```

### Supabase Connection Issues

**Symptom**: `Cannot connect to Supabase`

**Solutions**:

1. Verify Supabase credentials:
```bash
grep SUPABASE .env
```

2. Test connection:
```bash
docker-compose exec reasoning-bank python -c "
from supabase import create_client
import os
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
print('Connection OK')
"
```

3. Check Supabase project status at [supabase.com](https://supabase.com/)

## Security Best Practices

1. **API Key Management**:
   - Never commit `.env` files to version control
   - Use separate API keys for dev/staging/prod
   - Rotate API keys regularly

2. **File Permissions**:
   - Restrict access to data directories
   - Use non-root user in Docker container
   - Set proper file permissions (644 for files, 755 for directories)

3. **Network Security**:
   - Use HTTPS for Supabase connections
   - Implement rate limiting
   - Monitor API usage

4. **Data Privacy**:
   - Enable workspace isolation
   - Implement data retention policies
   - Regular backups with encryption

## Next Steps

After successful deployment:

1. Review the [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for usage examples
2. Test the MCP tools with sample tasks
3. Configure monitoring and alerting
4. Set up automated backups
5. Review logs regularly for issues

## Support

For additional help:

- Check the [README.md](README.md) for general information
- Review test files for usage examples
- Open an issue on GitHub
- Check OpenRouter status at [status.openrouter.ai](https://status.openrouter.ai/)
