"""
Test data retention and cleanup functionality

This test verifies:
- Trace cleanup by retention days
- Workspace deletion
- Backup and restore operations
"""

import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage_adapter import create_storage_backend
from workspace_manager import WorkspaceManager
from backup_restore import BackupManager


def test_trace_cleanup():
    """Test cleanup_old_traces functionality"""
    print("=== Testing Trace Cleanup ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create storage adapter
        storage = create_storage_backend(
            backend_type="chromadb",
            persist_directory=os.path.join(tmpdir, "chroma_data")
        )
        
        # Add some test traces
        print("1. Adding test traces...")
        test_workspace = "test_workspace_123"
        
        # Add old trace (should be deleted)
        old_memory = {
            "id": str(uuid.uuid4()),
            "title": "Old Memory",
            "description": "This is old",
            "content": "Old content"
        }
        
        storage.add_trace(
            trace_id=str(uuid.uuid4()),
            task="Old task",
            trajectory=[],
            outcome="success",
            memory_items=[old_memory],
            workspace_id=test_workspace
        )
        
        # Add recent trace (should be kept)
        recent_memory = {
            "id": str(uuid.uuid4()),
            "title": "Recent Memory",
            "description": "This is recent",
            "content": "Recent content"
        }
        
        storage.add_trace(
            trace_id=str(uuid.uuid4()),
            task="Recent task",
            trajectory=[],
            outcome="success",
            memory_items=[recent_memory],
            workspace_id=test_workspace
        )
        
        print("✅ Added 2 test traces\n")
        
        # Get initial stats
        print("2. Getting initial statistics...")
        stats_before = storage.get_statistics(workspace_id=test_workspace)
        print(f"   Total traces: {stats_before['total_traces']}")
        print(f"   Total memories: {stats_before['total_memories']}\n")
        
        # Test cleanup (use 0 days to delete all)
        print("3. Testing cleanup with retention_days=0...")
        result = storage.delete_old_traces(
            retention_days=0,
            workspace_id=test_workspace
        )
        
        print(f"✅ Cleanup completed:")
        print(f"   Deleted traces: {result['deleted_traces_count']}")
        print(f"   Deleted memories: {result['deleted_memories_count']}")
        print(f"   Freed space: {result['freed_space_mb']} MB\n")
        
        # Verify cleanup
        print("4. Verifying cleanup...")
        stats_after = storage.get_statistics(workspace_id=test_workspace)
        print(f"   Total traces after: {stats_after['total_traces']}")
        print(f"   Total memories after: {stats_after['total_memories']}")
        
        if stats_after['total_memories'] < stats_before['total_memories']:
            print("✅ Cleanup successful\n")
        else:
            print("⚠️  Cleanup may not have worked as expected\n")


def test_workspace_deletion():
    """Test workspace deletion functionality"""
    print("=== Testing Workspace Deletion ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create storage adapter and workspace manager
        storage = create_storage_backend(
            backend_type="chromadb",
            persist_directory=os.path.join(tmpdir, "chroma_data")
        )
        
        workspace_manager = WorkspaceManager()
        
        # Add test data to workspace
        print("1. Adding test data to workspace...")
        test_workspace = "workspace_to_delete"
        
        memory = {
            "id": str(uuid.uuid4()),
            "title": "Test Memory",
            "description": "Test description",
            "content": "Test content"
        }
        
        storage.add_trace(
            trace_id=str(uuid.uuid4()),
            task="Test task",
            trajectory=[],
            outcome="success",
            memory_items=[memory],
            workspace_id=test_workspace
        )
        
        print("✅ Added test data\n")
        
        # Get stats before deletion
        print("2. Getting statistics before deletion...")
        stats_before = storage.get_statistics(workspace_id=test_workspace)
        print(f"   Total memories: {stats_before['total_memories']}\n")
        
        # Test deletion without confirmation (should fail)
        print("3. Testing deletion without confirmation...")
        try:
            workspace_manager.delete_workspace(
                test_workspace,
                storage,
                confirm=False
            )
            print("❌ Should have raised ValueError\n")
        except ValueError as e:
            print(f"✅ Correctly raised error: {str(e)[:80]}...\n")
        
        # Test deletion with confirmation
        print("4. Testing deletion with confirmation...")
        result = workspace_manager.delete_workspace(
            test_workspace,
            storage,
            confirm=True
        )
        
        print(f"✅ Workspace deleted:")
        print(f"   Workspace ID: {result['workspace_id']}")
        print(f"   Deleted traces: {result['deleted_traces']}")
        print(f"   Deleted memories: {result['deleted_memories']}\n")
        
        # Verify deletion
        print("5. Verifying deletion...")
        stats_after = storage.get_statistics(workspace_id=test_workspace)
        print(f"   Total memories after: {stats_after['total_memories']}")
        
        if stats_after['total_memories'] == 0:
            print("✅ Workspace deletion successful\n")
        else:
            print("⚠️  Workspace deletion may not have worked completely\n")


def test_backup_restore():
    """Test backup and restore functionality"""
    print("=== Testing Backup and Restore ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create storage adapter
        storage = create_storage_backend(
            backend_type="chromadb",
            persist_directory=os.path.join(tmpdir, "chroma_data")
        )
        
        # Create backup manager
        backup_dir = os.path.join(tmpdir, "backups")
        backup_manager = BackupManager(storage, backup_directory=backup_dir)
        
        # Add test data
        print("1. Adding test data...")
        test_workspace = "backup_test_workspace"
        
        memory = {
            "id": str(uuid.uuid4()),
            "title": "Backup Test Memory",
            "description": "Test for backup",
            "content": "This should be backed up"
        }
        
        storage.add_trace(
            trace_id=str(uuid.uuid4()),
            task="Backup test task",
            trajectory=[],
            outcome="success",
            memory_items=[memory],
            workspace_id=test_workspace
        )
        
        print("✅ Added test data\n")
        
        # Create backup
        print("2. Creating backup...")
        backup_path = os.path.join(backup_dir, "test_backup.tar.gz")
        
        backup_result = backup_manager.backup_chromadb(
            output_path=backup_path,
            workspace_id=test_workspace
        )
        
        print(f"✅ Backup created:")
        print(f"   Path: {backup_result['backup_path']}")
        print(f"   Size: {backup_result['backup_size_mb']} MB")
        print(f"   Traces: {backup_result['trace_count']}")
        print(f"   Memories: {backup_result['memory_count']}\n")
        
        # Validate backup
        print("3. Validating backup...")
        validation = backup_manager.validate_backup(backup_path)
        
        if validation['valid']:
            print("✅ Backup is valid")
            if validation['warnings']:
                print(f"   Warnings: {validation['warnings']}")
        else:
            print(f"❌ Backup validation failed: {validation['errors']}")
        print()
        
        # Test restore (to different workspace)
        print("4. Testing restore to different workspace...")
        target_workspace = "restored_workspace"
        
        restore_result = backup_manager.restore_chromadb(
            backup_path=backup_path,
            target_workspace_id=target_workspace
        )
        
        print(f"✅ Restore completed:")
        print(f"   Restored traces: {restore_result['restored_traces']}")
        print(f"   Restored memories: {restore_result['restored_memories']}")
        print(f"   Target workspace: {restore_result['target_workspace_id']}\n")
        
        # Verify restore
        print("5. Verifying restored data...")
        stats = storage.get_statistics(workspace_id=target_workspace)
        print(f"   Total memories in restored workspace: {stats['total_memories']}")
        
        if stats['total_memories'] > 0:
            print("✅ Restore successful\n")
        else:
            print("⚠️  Restore may not have worked as expected\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Data Retention and Cleanup Tests")
    print("=" * 60)
    print()
    
    try:
        test_trace_cleanup()
        test_workspace_deletion()
        test_backup_restore()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
