"""
Integration test for workspace manager with storage adapter

This test verifies that workspace isolation works correctly with
the storage backend, ensuring memories don't leak across workspaces.
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workspace_manager import WorkspaceManager, create_workspace_manager
from storage_adapter import create_storage_backend


def test_workspace_isolation():
    """Test that memories are isolated between workspaces"""
    print("=== Testing Workspace Isolation with Storage ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two workspace directories
        workspace1_path = os.path.join(tmpdir, "project1")
        workspace2_path = os.path.join(tmpdir, "project2")
        os.makedirs(workspace1_path)
        os.makedirs(workspace2_path)
        
        # Create storage backend
        storage_dir = os.path.join(tmpdir, "test_storage")
        storage = create_storage_backend(
            backend_type="chromadb",
            persist_directory=storage_dir,
            collection_name="test_workspace_isolation"
        )
        
        # Create workspace manager
        workspace_mgr = WorkspaceManager()
        
        # Test 1: Store memory in workspace 1
        print("1. Storing memory in workspace 1...")
        workspace_mgr.set_workspace(workspace1_path)
        workspace1_id = workspace_mgr.get_workspace_id()
        
        memory1 = {
            "id": str(uuid.uuid4()),
            "title": "Workspace 1 Memory",
            "description": "This memory belongs to workspace 1",
            "content": "Content specific to workspace 1 project",
            "pattern_tags": ["workspace1"],
            "domain_category": "test"
        }
        
        trace1_id = storage.add_trace(
            trace_id=str(uuid.uuid4()),
            task="Test task for workspace 1",
            trajectory=[{"iteration": 1, "action": "test", "output": "test"}],
            outcome="success",
            memory_items=[memory1],
            workspace_id=workspace1_id
        )
        print(f"✅ Stored memory in workspace 1 (ID: {workspace1_id})\n")
        
        # Test 2: Store memory in workspace 2
        print("2. Storing memory in workspace 2...")
        workspace_mgr.set_workspace(workspace2_path)
        workspace2_id = workspace_mgr.get_workspace_id()
        
        memory2 = {
            "id": str(uuid.uuid4()),
            "title": "Workspace 2 Memory",
            "description": "This memory belongs to workspace 2",
            "content": "Content specific to workspace 2 project",
            "pattern_tags": ["workspace2"],
            "domain_category": "test"
        }
        
        trace2_id = storage.add_trace(
            trace_id=str(uuid.uuid4()),
            task="Test task for workspace 2",
            trajectory=[{"iteration": 1, "action": "test", "output": "test"}],
            outcome="success",
            memory_items=[memory2],
            workspace_id=workspace2_id
        )
        print(f"✅ Stored memory in workspace 2 (ID: {workspace2_id})\n")
        
        # Test 3: Query from workspace 1 - should only get workspace 1 memories
        print("3. Querying from workspace 1...")
        workspace_mgr.set_workspace(workspace1_path)
        memories_ws1 = storage.query_similar_memories(
            query_text="workspace memory",
            n_results=10,
            workspace_id=workspace1_id
        )
        
        print(f"   Found {len(memories_ws1)} memories")
        for mem in memories_ws1:
            print(f"   - {mem.title}")
        
        # Verify only workspace 1 memory is returned
        assert len(memories_ws1) == 1, f"Expected 1 memory, got {len(memories_ws1)}"
        assert memories_ws1[0].title == "Workspace 1 Memory"
        print("✅ Workspace 1 isolation verified\n")
        
        # Test 4: Query from workspace 2 - should only get workspace 2 memories
        print("4. Querying from workspace 2...")
        workspace_mgr.set_workspace(workspace2_path)
        memories_ws2 = storage.query_similar_memories(
            query_text="workspace memory",
            n_results=10,
            workspace_id=workspace2_id
        )
        
        print(f"   Found {len(memories_ws2)} memories")
        for mem in memories_ws2:
            print(f"   - {mem.title}")
        
        # Verify only workspace 2 memory is returned
        assert len(memories_ws2) == 1, f"Expected 1 memory, got {len(memories_ws2)}"
        assert memories_ws2[0].title == "Workspace 2 Memory"
        print("✅ Workspace 2 isolation verified\n")
        
        # Test 5: Query without workspace filter - should get all memories
        print("5. Querying without workspace filter...")
        memories_all = storage.query_similar_memories(
            query_text="workspace memory",
            n_results=10,
            workspace_id=None
        )
        
        print(f"   Found {len(memories_all)} memories")
        for mem in memories_all:
            print(f"   - {mem.title}")
        
        # Verify both memories are returned
        assert len(memories_all) == 2, f"Expected 2 memories, got {len(memories_all)}"
        print("✅ Unfiltered query returns all memories\n")
        
        # Test 6: Statistics per workspace
        print("6. Testing workspace-specific statistics...")
        stats_ws1 = storage.get_statistics(workspace_id=workspace1_id)
        stats_ws2 = storage.get_statistics(workspace_id=workspace2_id)
        stats_all = storage.get_statistics(workspace_id=None)
        
        print(f"   Workspace 1 stats: {stats_ws1['total_memories']} memories")
        print(f"   Workspace 2 stats: {stats_ws2['total_memories']} memories")
        print(f"   All workspaces: {stats_all['total_memories']} memories")
        
        assert stats_ws1['total_memories'] == 1
        assert stats_ws2['total_memories'] == 1
        assert stats_all['total_memories'] == 2
        print("✅ Workspace-specific statistics work correctly\n")
        
        print("=== All workspace isolation tests passed! ===")


def test_workspace_manager_api():
    """Test workspace manager API methods"""
    print("\n=== Testing Workspace Manager API ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = os.path.join(tmpdir, "test-project")
        os.makedirs(workspace_path)
        
        # Test factory function
        print("1. Testing factory function...")
        manager = create_workspace_manager(workspace_path)
        assert manager.is_workspace_set()
        assert manager.get_workspace_name() == "test-project"
        print(f"✅ Factory created manager for: {manager.get_workspace_name()}\n")
        
        # Test workspace info
        print("2. Testing workspace info...")
        info = manager.get_workspace_info()
        assert info['is_set'] == True
        assert info['workspace_name'] == "test-project"
        assert info['workspace_id'] is not None
        assert info['workspace_path'] == workspace_path
        print(f"✅ Workspace info: {info['workspace_name']} (ID: {info['workspace_id']})\n")
        
        # Test filter_by_workspace
        print("3. Testing filter_by_workspace...")
        filter_id = manager.filter_by_workspace()
        assert filter_id == manager.get_workspace_id()
        
        custom_id = "custom_workspace_123"
        filter_id = manager.filter_by_workspace(custom_id)
        assert filter_id == custom_id
        print("✅ Filtering works correctly\n")
        
        # Test clear workspace
        print("4. Testing clear workspace...")
        manager.clear_workspace()
        assert not manager.is_workspace_set()
        assert manager.get_workspace_id() is None
        print("✅ Workspace cleared successfully\n")
        
        # Test repr
        print("5. Testing string representation...")
        manager.set_workspace(workspace_path)
        repr_str = repr(manager)
        assert "test-project" in repr_str
        print(f"✅ Repr: {repr_str}\n")
        
        print("=== All API tests passed! ===")


if __name__ == "__main__":
    try:
        test_workspace_isolation()
        test_workspace_manager_api()
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - Workspace Manager is production ready!")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
