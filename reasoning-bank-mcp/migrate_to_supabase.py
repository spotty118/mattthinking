#!/usr/bin/env python3
"""
Migration script to transfer data from ChromaDB to Supabase

This script:
1. Reads existing traces from ChromaDB and JSON files
2. Connects to Supabase
3. Uploads all traces and memory items to Supabase
4. Verifies migration success
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Any
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from supabase_storage import SupabaseStorage
    from reasoning_bank_core import ReasoningBank, MemoryItem, ReasoningTrace
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you've installed all dependencies: pip install -r requirements.txt")
    sys.exit(1)


class MigrationManager:
    """Manages migration from ChromaDB to Supabase"""
    
    def __init__(
        self,
        chromadb_data_dir: str = "./chroma_data",
        traces_file: str = None,
        supabase_url: str = None,
        supabase_key: str = None,
        dry_run: bool = False
    ):
        """
        Initialize migration manager
        
        Args:
            chromadb_data_dir: ChromaDB data directory
            traces_file: Path to traces.json file
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            dry_run: If True, only validate without uploading
        """
        self.chromadb_data_dir = chromadb_data_dir
        self.traces_file = traces_file or os.path.join(chromadb_data_dir, "traces.json")
        self.dry_run = dry_run
        
        logger.info(f"ChromaDB data directory: {self.chromadb_data_dir}")
        logger.info(f"Traces file: {self.traces_file}")
        logger.info(f"Dry run mode: {self.dry_run}")
        
        # Initialize Supabase storage (only if not dry run)
        if not dry_run:
            try:
                self.supabase_storage = SupabaseStorage(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key,
                    logger=logger
                )
                logger.info("✓ Supabase connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
                raise
    
    def load_traces_from_chromadb(self) -> List[Dict]:
        """
        Load traces from ChromaDB JSON file
        
        Returns:
            List of trace dictionaries
        """
        if not os.path.exists(self.traces_file):
            logger.warning(f"Traces file not found: {self.traces_file}")
            return []
        
        try:
            with open(self.traces_file, 'r') as f:
                traces = json.load(f)
            logger.info(f"✓ Loaded {len(traces)} traces from {self.traces_file}")
            return traces
        except Exception as e:
            logger.error(f"Failed to load traces: {e}")
            return []
    
    def validate_trace(self, trace: Dict) -> bool:
        """
        Validate trace data structure
        
        Args:
            trace: Trace dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["id", "task", "trajectory", "outcome", "memory_items"]
        
        for field in required_fields:
            if field not in trace:
                logger.warning(f"Trace {trace.get('id', 'unknown')} missing field: {field}")
                return False
        
        if not isinstance(trace["memory_items"], list):
            logger.warning(f"Trace {trace['id']} has invalid memory_items type")
            return False
        
        return True
    
    def migrate_trace(self, trace: Dict) -> bool:
        """
        Migrate a single trace to Supabase
        
        Args:
            trace: Trace dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate trace
            if not self.validate_trace(trace):
                return False
            
            # Extract trace data
            trace_id = trace["id"]
            task = trace["task"]
            trajectory = trace["trajectory"]
            outcome = trace["outcome"]
            metadata = trace.get("metadata", {})
            parent_trace_id = trace.get("parent_trace_id")
            
            # Convert memory items
            memory_items = []
            for mem_dict in trace["memory_items"]:
                # Ensure all required fields exist
                memory_item = {
                    "id": mem_dict.get("id"),
                    "title": mem_dict.get("title", "Untitled"),
                    "description": mem_dict.get("description", ""),
                    "content": mem_dict.get("content", ""),
                    "error_context": mem_dict.get("error_context"),
                    "pattern_tags": mem_dict.get("pattern_tags", []),
                    "difficulty_level": mem_dict.get("difficulty_level"),
                    "domain_category": mem_dict.get("domain_category"),
                    "parent_memory_id": mem_dict.get("parent_memory_id"),
                    "evolution_stage": mem_dict.get("evolution_stage", 0)
                }
                memory_items.append(memory_item)
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate trace {trace_id} with {len(memory_items)} memories")
                return True
            
            # Upload to Supabase
            self.supabase_storage.add_trace(
                trace_id=trace_id,
                task=task,
                trajectory=trajectory,
                outcome=outcome,
                memory_items=memory_items,
                metadata=metadata,
                parent_trace_id=parent_trace_id
            )
            
            logger.info(f"✓ Migrated trace {trace_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate trace {trace.get('id', 'unknown')}: {e}")
            return False
    
    def run_migration(self) -> Dict[str, Any]:
        """
        Run the full migration process
        
        Returns:
            Migration statistics
        """
        logger.info("="*60)
        logger.info("Starting ChromaDB to Supabase Migration")
        logger.info("="*60)
        
        # Load traces
        traces = self.load_traces_from_chromadb()
        
        if not traces:
            logger.warning("No traces found to migrate")
            return {
                "total_traces": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0
            }
        
        # Migrate traces
        stats = {
            "total_traces": len(traces),
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for i, trace in enumerate(traces, 1):
            logger.info(f"Processing trace {i}/{len(traces)}: {trace.get('id', 'unknown')}")
            
            if self.migrate_trace(trace):
                stats["successful"] += 1
            else:
                stats["failed"] += 1
        
        # Print summary
        logger.info("="*60)
        logger.info("Migration Summary")
        logger.info("="*60)
        logger.info(f"Total traces: {stats['total_traces']}")
        logger.info(f"Successful: {stats['successful']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        
        if not self.dry_run and stats["successful"] > 0:
            # Verify migration
            logger.info("\nVerifying migration...")
            try:
                supabase_stats = self.supabase_storage.get_statistics()
                logger.info(f"✓ Supabase now contains {supabase_stats['total_traces']} traces")
                logger.info(f"✓ Supabase now contains {supabase_stats['total_memories']} memories")
            except Exception as e:
                logger.warning(f"Could not verify migration: {e}")
        
        return stats


def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(
        description="Migrate ReasoningBank data from ChromaDB to Supabase"
    )
    parser.add_argument(
        "--chromadb-dir",
        default="./chroma_data",
        help="ChromaDB data directory (default: ./chroma_data)"
    )
    parser.add_argument(
        "--traces-file",
        help="Path to traces.json file (default: <chromadb-dir>/traces.json)"
    )
    parser.add_argument(
        "--supabase-url",
        help="Supabase project URL (or set SUPABASE_URL env var)"
    )
    parser.add_argument(
        "--supabase-key",
        help="Supabase API key (or set SUPABASE_KEY env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without uploading to Supabase"
    )
    
    args = parser.parse_args()
    
    # Get Supabase credentials
    supabase_url = args.supabase_url or os.getenv("SUPABASE_URL")
    supabase_key = args.supabase_key or os.getenv("SUPABASE_KEY")
    
    if not args.dry_run and (not supabase_url or not supabase_key):
        logger.error("Supabase credentials required. Set SUPABASE_URL and SUPABASE_KEY environment variables")
        logger.error("or use --supabase-url and --supabase-key arguments")
        sys.exit(1)
    
    # Create migration manager
    try:
        manager = MigrationManager(
            chromadb_data_dir=args.chromadb_dir,
            traces_file=args.traces_file,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            dry_run=args.dry_run
        )
        
        # Run migration
        stats = manager.run_migration()
        
        # Exit with appropriate code
        if stats["failed"] > 0:
            logger.warning("Migration completed with errors")
            sys.exit(1)
        else:
            logger.info("✓ Migration completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
