# Docker Deployment Steps - Supabase Edition

## ✅ Completed Setup

### 1. Supabase Project Created
- **Project Name**: ReasoningBank
- **Region**: us-east-1
- **Status**: ACTIVE_HEALTHY
- **URL**: https://uvozrafrhjesezzqsnrn.supabase.co

### 2. Database Schema Deployed
- ✅ pgvector extension enabled
- ✅ `reasoning_traces` table created
- ✅ `memory_items` table created
- ✅ Vector HNSW indexes created
- ✅ Search functions deployed
- ✅ Row Level Security enabled

### 3. Configuration Updated
- ✅ `.env` file configured with Supabase credentials
- ✅ `STORAGE_BACKEND=supabase` set
- ✅ All connection details added

## 🚧 Next Step: Docker Build

### Current Issue
Docker is experiencing network connectivity issues preventing the build.

### Solution Options

**Option 1: Wait and Retry (Simplest)**
Once Docker Desktop is fully restarted:
```bash
cd /Users/justin/Downloads/mattthinking/reasoning-bank-mcp
docker-compose build
docker-compose up -d
```

**Option 2: Manual Proxy Fix**
1. Open Docker Desktop
2. Go to Settings → Resources → Proxies
3. Ensure "Manual proxy configuration" is UNCHECKED
4. Click "Apply & Restart"
5. Then run:
```bash
docker-compose build
docker-compose up -d
```

**Option 3: Build Without Docker**
If Docker issues persist, run directly:
```bash
pip3 install -r requirements.txt
python3 reasoning_bank_server.py
```

## 📝 Files Created for Supabase

### New Files
- `supabase_storage.py` - Supabase backend implementation
- `storage_adapter.py` - Unified storage interface
- `supabase_schema.sql` - Database schema
- `migrate_to_supabase.py` - Migration script
- `SUPABASE_SETUP.md` - Full setup guide
- `SUPABASE_QUICK_START.md` - Quick reference
- `SUPABASE_MIGRATION_SUMMARY.md` - Technical details

### Updated Files
- `schemas.py` - Added StorageBackend enum and Supabase config
- `config.py` - Load Supabase from environment
- `requirements.txt` - Added `supabase>=2.0.0`
- `.env` - Configured with Supabase credentials
- `docker-compose.yml` - Added Supabase environment variables

## 🎯 When Docker Build Succeeds

### 1. Verify Container
```bash
docker-compose ps
docker-compose logs -f
```

### 2. Test Connection
The container should show:
```
INFO     Supabase adapter initialized
INFO     ✓ Supabase connection established
```

### 3. Verify Data Storage
After solving a task, check Supabase:
- Dashboard: https://supabase.com/dashboard/project/uvozrafrhjesezzqsnrn
- Table Editor → `reasoning_traces`

## 🔧 Troubleshooting

### "No module named 'supabase'"
The new image includes it in `requirements.txt`. Rebuild with:
```bash
docker-compose build --no-cache
```

### "Connection refused" to Supabase
Check your `.env` file has the correct credentials.

### Container keeps restarting
Check logs:
```bash
docker-compose logs --tail=100
```

## ✅ Success Criteria

Your deployment is complete when:
1. ✅ Docker container builds successfully
2. ✅ Container starts without errors
3. ✅ Logs show "Supabase adapter initialized"
4. ✅ Tasks are stored in Supabase (check dashboard)

## 📊 Current Status

- Supabase Project: ✅ Created
- Database Schema: ✅ Deployed
- Configuration: ✅ Updated
- Docker Build: ⏳ Pending (network issue)
- Docker Deploy: ⏳ Pending

## 🔄 Next Command to Try

Once Docker is fully running:
```bash
docker-compose build && docker-compose up -d
```

Then verify:
```bash
docker-compose logs -f
```

You should see the ReasoningBank MCP server start up with Supabase connection!
