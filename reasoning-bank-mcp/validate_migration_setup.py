#!/usr/bin/env python3
"""
Validation script for Supabase migration setup

This script checks that all required files and components are in place
for migrating from ChromaDB to Supabase.
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} MISSING: {filepath}")
        return False

def check_file_content(filepath, required_strings, description):
    """Check if file contains required strings"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        missing = []
        for req_str in required_strings:
            if req_str not in content:
                missing.append(req_str)
        
        if not missing:
            print(f"✓ {description} contains required content")
            return True
        else:
            print(f"✗ {description} missing: {', '.join(missing)}")
            return False
    except Exception as e:
        print(f"✗ Error reading {filepath}: {e}")
        return False

def main():
    """Run validation checks"""
    print("="*60)
    print("Supabase Migration Setup Validation")
    print("="*60)
    print()
    
    all_checks_passed = True
    
    # Check core files exist
    print("1. Checking core migration files...")
    files_to_check = [
        ("reasoning-bank-mcp/supabase_storage.py", "Supabase storage adapter"),
        ("reasoning-bank-mcp/migrate_to_supabase.py", "Migration script"),
        ("reasoning-bank-mcp/supabase_schema.sql", "Database schema"),
        ("reasoning-bank-mcp/storage_adapter.py", "Storage adapter interface"),
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    print()
    
    # Check documentation files
    print("2. Checking documentation files...")
    doc_files = [
        ("reasoning-bank-mcp/MIGRATION_GUIDE.md", "Migration guide"),
        ("reasoning-bank-mcp/SUPABASE_MIGRATION_README.md", "Supabase README"),
    ]
    
    for filepath, description in doc_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    print()
    
    # Check SupabaseAdapter implementation
    print("3. Checking SupabaseAdapter implementation...")
    required_methods = [
        "class SupabaseAdapter(StorageBackendInterface)",
        "def add_trace(",
        "def query_similar_memories(",
        "def get_statistics(",
        "workspace_id"
    ]
    
    if not check_file_content(
        "reasoning-bank-mcp/supabase_storage.py",
        required_methods,
        "SupabaseAdapter"
    ):
        all_checks_passed = False
    print()
    
    # Check schema has required tables
    print("4. Checking database schema...")
    required_schema = [
        "CREATE TABLE IF NOT EXISTS reasoning_traces",
        "CREATE TABLE IF NOT EXISTS memory_items",
        "CREATE EXTENSION IF NOT EXISTS vector",
        "CREATE OR REPLACE FUNCTION search_similar_memories",
        "workspace_id TEXT"
    ]
    
    if not check_file_content(
        "reasoning-bank-mcp/supabase_schema.sql",
        required_schema,
        "Database schema"
    ):
        all_checks_passed = False
    print()
    
    # Check migration script has required functionality
    print("5. Checking migration script...")
    required_migration = [
        "class MigrationManager",
        "def load_traces_from_chromadb",
        "def migrate_trace",
        "def run_migration",
        "--dry-run"
    ]
    
    if not check_file_content(
        "reasoning-bank-mcp/migrate_to_supabase.py",
        required_migration,
        "Migration script"
    ):
        all_checks_passed = False
    print()
    
    # Check storage adapter factory
    print("6. Checking storage adapter factory...")
    required_factory = [
        "def create_storage_backend",
        'backend_type == "supabase"',
        "from supabase_storage import SupabaseAdapter"
    ]
    
    if not check_file_content(
        "reasoning-bank-mcp/storage_adapter.py",
        required_factory,
        "Storage adapter factory"
    ):
        all_checks_passed = False
    print()
    
    # Check requirements.txt
    print("7. Checking dependencies...")
    if check_file_exists("reasoning-bank-mcp/requirements.txt", "Requirements file"):
        if not check_file_content(
            "reasoning-bank-mcp/requirements.txt",
            ["supabase>=2.0.0"],
            "Supabase dependency"
        ):
            all_checks_passed = False
    else:
        all_checks_passed = False
    print()
    
    # Summary
    print("="*60)
    if all_checks_passed:
        print("✓ All validation checks passed!")
        print()
        print("Next steps:")
        print("1. Set up Supabase project at https://supabase.com")
        print("2. Run supabase_schema.sql in Supabase SQL Editor")
        print("3. Set SUPABASE_URL and SUPABASE_KEY environment variables")
        print("4. Run: python migrate_to_supabase.py --dry-run")
        print("5. Run: python migrate_to_supabase.py")
        print()
        return 0
    else:
        print("✗ Some validation checks failed")
        print("Please review the errors above and fix missing components")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
