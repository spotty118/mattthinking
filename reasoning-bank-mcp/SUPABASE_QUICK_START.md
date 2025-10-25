# Supabase Quick Start Guide

Get your ReasoningBank running on Supabase cloud in 5 minutes!

## 1. Create Supabase Project (2 minutes)

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click **"New Project"**
3. Fill in:
   - **Name**: `reasoning-bank`
   - **Database Password**: (save this!)
   - **Region**: Choose closest to you
4. Click **"Create new project"** and wait ~2 minutes

## 2. Set Up Database (1 minute)

1. In your Supabase project, go to **SQL Editor**
2. Click **"New query"**
3. Copy/paste the entire contents of [`supabase_schema.sql`](./supabase_schema.sql)
4. Click **Run** or press `Ctrl+Enter`
5. You should see: "Success. No rows returned"

## 3. Get Your Credentials (30 seconds)

1. Go to **Settings** → **API**
2. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon public key** (long string starting with `eyJ...`)

## 4. Configure Environment (30 seconds)

Create or update `.env` file:

```bash
# Switch to Supabase
STORAGE_BACKEND=supabase

# Add your credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOi...your-key-here

# Keep your existing OpenRouter key
OPENROUTER_API_KEY=your-openrouter-key
```

## 5. Install Dependencies (30 seconds)

```bash
pip install -r requirements.txt
```

This installs the Supabase client along with other dependencies.

## 6. Start Using! (30 seconds)

```bash
# Start your server
python reasoning_bank_server.py
```

**Done!** Your ReasoningBank now uses Supabase cloud storage. 🎉

## Optional: Migrate Existing Data

If you have existing ChromaDB data:

```bash
# Preview migration
python migrate_to_supabase.py --dry-run

# Actually migrate
python migrate_to_supabase.py
```

## Verify It's Working

1. Go to Supabase **Table Editor**
2. Select `reasoning_traces` table
3. After solving a task, you should see new entries appear!

## Quick Commands

```bash
# Check statistics
python -c "from supabase_storage import SupabaseStorage; s = SupabaseStorage(); print(s.get_statistics())"

# Switch back to ChromaDB
# Edit .env: STORAGE_BACKEND=chromadb

# Re-run schema (if needed)
# Copy supabase_schema.sql to SQL Editor and run
```

## Troubleshooting

**"Failed to connect to Supabase"**
- Double-check your `SUPABASE_URL` and `SUPABASE_KEY`
- Ensure you're using the `anon` key, not `service_role`

**"Table does not exist"**
- Re-run the schema setup (Step 2)

**"Import error: No module named supabase"**
- Run: `pip install supabase>=2.0.0`

## What's Different?

| Feature | ChromaDB (Before) | Supabase (Now) |
|---------|------------------|----------------|
| Storage | Local files | Cloud database |
| Scaling | Limited by disk | PostgreSQL scale |
| Access | Single machine | Access anywhere |
| Backups | Manual | Automatic |
| Search | ChromaDB | pgvector |
| Cost | Free | Free tier available |

## Next Steps

- 📖 Read full [Supabase Setup Guide](./SUPABASE_SETUP.md) for advanced features
- 🔐 Set up Row Level Security for multi-user access
- 📊 Explore your data in Supabase dashboard
- 🚀 Deploy to production with environment variables

Need help? Check the [full setup guide](./SUPABASE_SETUP.md) or open an issue!
