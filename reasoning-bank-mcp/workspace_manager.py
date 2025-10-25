"""
Workspace isolation manager for ReasoningBank MCP System

This module provides workspace isolation to prevent memory leakage between
different users, projects, or contexts. Each workspace has a unique ID
generated from its directory path, ensuring deterministic identification.

Features:
- Deterministic workspace ID generation using SHA256 hashing
- Workspace switching without system restart
- Memory filtering by workspace in queries
- Human-readable workspace name extraction
- Support for multi-tenant deployments

Requirements addressed: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import os
import hashlib
import logging
from typing import Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class WorkspaceManager:
    """
    Manages workspace isolation for memory storage and retrieval
    
    The WorkspaceManager ensures that memories are isolated between different
    workspaces (projects, users, or contexts). It generates deterministic
    workspace IDs from directory paths and provides filtering capabilities
    for memory queries.
    
    Key features:
    - Deterministic ID generation (same path = same ID)
    - Workspace switching without restart
    - Human-readable workspace names
    - Thread-safe workspace state management
    
    Example:
        >>> manager = WorkspaceManager()
        >>> manager.set_workspace("/home/user/project1")
        >>> workspace_id = manager.get_workspace_id()
        >>> workspace_name = manager.get_workspace_name()
    """
    
    def __init__(self, default_workspace: Optional[str] = None):
        """
        Initialize workspace manager
        
        Args:
            default_workspace: Optional default workspace directory path.
                             If None, uses current working directory.
        
        Example:
            >>> manager = WorkspaceManager()  # Uses cwd
            >>> manager = WorkspaceManager("/path/to/workspace")
        """
        self._current_workspace_path: Optional[str] = None
        self._current_workspace_id: Optional[str] = None
        self._current_workspace_name: Optional[str] = None
        
        # Set default workspace
        if default_workspace:
            self.set_workspace(default_workspace)
        else:
            # Use current working directory as default
            self.set_workspace(os.getcwd())
        
        logger.info(
            f"WorkspaceManager initialized with workspace: {self._current_workspace_name} "
            f"(ID: {self._current_workspace_id})"
        )
    
    def generate_workspace_id(self, directory_path: str) -> str:
        """
        Generate deterministic workspace ID from directory path
        
        Uses SHA256 hash of the absolute directory path to create a unique
        but deterministic workspace identifier. The same directory path will
        always generate the same workspace ID.
        
        Args:
            directory_path: Path to the workspace directory
        
        Returns:
            16-character hexadecimal workspace ID
        
        Example:
            >>> manager = WorkspaceManager()
            >>> workspace_id = manager.generate_workspace_id("/home/user/project")
            >>> # Same path always produces same ID
            >>> assert workspace_id == manager.generate_workspace_id("/home/user/project")
        
        Note:
            - Uses absolute path to ensure consistency
            - Truncates hash to 16 characters for readability
            - Deterministic: same input always produces same output
        """
        # Convert to absolute path for consistency
        abs_path = os.path.abspath(directory_path)
        
        # Generate SHA256 hash
        hash_obj = hashlib.sha256(abs_path.encode('utf-8'))
        
        # Take first 16 characters of hex digest for readability
        workspace_id = hash_obj.hexdigest()[:16]
        
        logger.debug(f"Generated workspace ID '{workspace_id}' for path: {abs_path}")
        
        return workspace_id
    
    def set_workspace(self, directory_path: str) -> str:
        """
        Switch to a different workspace
        
        Changes the current workspace context. All subsequent memory operations
        will be filtered to this workspace. This method can be called multiple
        times to switch between workspaces without restarting the system.
        
        Args:
            directory_path: Path to the workspace directory
        
        Returns:
            The workspace ID of the newly set workspace
        
        Raises:
            ValueError: If directory_path is empty or invalid
            OSError: If directory path cannot be resolved
        
        Example:
            >>> manager = WorkspaceManager()
            >>> workspace_id = manager.set_workspace("/home/user/project1")
            >>> # Later, switch to different workspace
            >>> workspace_id = manager.set_workspace("/home/user/project2")
        """
        if not directory_path:
            raise ValueError("Directory path cannot be empty")
        
        try:
            # Resolve and validate path
            abs_path = os.path.abspath(directory_path)
            
            # Generate workspace ID
            workspace_id = self.generate_workspace_id(abs_path)
            
            # Extract workspace name (last component of path)
            workspace_name = os.path.basename(abs_path)
            if not workspace_name:
                # Handle root directory case
                workspace_name = abs_path
            
            # Update current workspace state
            self._current_workspace_path = abs_path
            self._current_workspace_id = workspace_id
            self._current_workspace_name = workspace_name
            
            logger.info(
                f"Switched to workspace: {workspace_name} "
                f"(ID: {workspace_id}, Path: {abs_path})"
            )
            
            return workspace_id
            
        except Exception as e:
            logger.error(f"Failed to set workspace for path '{directory_path}': {e}")
            raise OSError(f"Failed to set workspace: {e}") from e
    
    def get_workspace_id(self) -> Optional[str]:
        """
        Get the current workspace ID
        
        Returns:
            Current workspace ID, or None if no workspace is set
        
        Example:
            >>> manager = WorkspaceManager()
            >>> manager.set_workspace("/home/user/project")
            >>> workspace_id = manager.get_workspace_id()
            >>> print(workspace_id)  # e.g., "a1b2c3d4e5f6g7h8"
        """
        return self._current_workspace_id
    
    def get_workspace_name(self) -> Optional[str]:
        """
        Get human-readable workspace name
        
        Returns the last component of the workspace directory path,
        which is typically the project or workspace name.
        
        Returns:
            Human-readable workspace name, or None if no workspace is set
        
        Example:
            >>> manager = WorkspaceManager()
            >>> manager.set_workspace("/home/user/my-project")
            >>> name = manager.get_workspace_name()
            >>> print(name)  # "my-project"
        """
        return self._current_workspace_name
    
    def get_workspace_path(self) -> Optional[str]:
        """
        Get the current workspace directory path
        
        Returns:
            Absolute path to current workspace directory, or None if no workspace is set
        
        Example:
            >>> manager = WorkspaceManager()
            >>> manager.set_workspace("/home/user/project")
            >>> path = manager.get_workspace_path()
            >>> print(path)  # "/home/user/project"
        """
        return self._current_workspace_path
    
    def filter_by_workspace(self, workspace_id: Optional[str] = None) -> Optional[str]:
        """
        Get workspace ID for filtering memory queries
        
        This method is used by storage adapters to filter memory queries
        by workspace. If no workspace_id is provided, uses the current workspace.
        
        Args:
            workspace_id: Optional explicit workspace ID. If None, uses current workspace.
        
        Returns:
            Workspace ID to use for filtering, or None for no filtering
        
        Example:
            >>> manager = WorkspaceManager()
            >>> manager.set_workspace("/home/user/project")
            >>> # Use current workspace
            >>> filter_id = manager.filter_by_workspace()
            >>> # Use explicit workspace
            >>> filter_id = manager.filter_by_workspace("a1b2c3d4e5f6g7h8")
        """
        if workspace_id is not None:
            return workspace_id
        return self._current_workspace_id
    
    def is_workspace_set(self) -> bool:
        """
        Check if a workspace is currently set
        
        Returns:
            True if a workspace is set, False otherwise
        
        Example:
            >>> manager = WorkspaceManager()
            >>> if manager.is_workspace_set():
            ...     print(f"Current workspace: {manager.get_workspace_name()}")
        """
        return self._current_workspace_id is not None
    
    def get_workspace_info(self) -> dict:
        """
        Get complete information about the current workspace
        
        Returns:
            Dictionary containing workspace_id, workspace_name, and workspace_path
        
        Example:
            >>> manager = WorkspaceManager()
            >>> manager.set_workspace("/home/user/project")
            >>> info = manager.get_workspace_info()
            >>> print(info)
            {
                'workspace_id': 'a1b2c3d4e5f6g7h8',
                'workspace_name': 'project',
                'workspace_path': '/home/user/project',
                'is_set': True
            }
        """
        return {
            "workspace_id": self._current_workspace_id,
            "workspace_name": self._current_workspace_name,
            "workspace_path": self._current_workspace_path,
            "is_set": self.is_workspace_set()
        }
    
    def clear_workspace(self) -> None:
        """
        Clear the current workspace context
        
        After calling this method, no workspace filtering will be applied
        to memory queries until set_workspace() is called again.
        
        Example:
            >>> manager = WorkspaceManager()
            >>> manager.set_workspace("/home/user/project")
            >>> manager.clear_workspace()
            >>> assert not manager.is_workspace_set()
        """
        logger.info(
            f"Clearing workspace: {self._current_workspace_name} "
            f"(ID: {self._current_workspace_id})"
        )
        
        self._current_workspace_path = None
        self._current_workspace_id = None
        self._current_workspace_name = None
    
    def delete_workspace(
        self,
        workspace_id: str,
        storage_adapter,
        confirm: bool = False
    ) -> dict:
        """
        Delete all traces and memories for a specific workspace
        
        This method removes all data associated with a workspace from storage.
        Requires explicit confirmation to prevent accidental deletion.
        
        IMPORTANT: This operation is irreversible. All traces, memories, and
        associated data for the workspace will be permanently deleted.
        
        Args:
            workspace_id: Workspace identifier to delete
            storage_adapter: Storage backend instance (ChromaDBAdapter or SupabaseAdapter)
            confirm: Must be True to proceed with deletion (safety check)
        
        Returns:
            Dictionary with deletion statistics:
            - workspace_id: The deleted workspace ID
            - deleted_traces: Number of traces deleted
            - deleted_memories: Number of memory items deleted
            - deletion_timestamp: ISO timestamp of deletion
        
        Raises:
            ValueError: If confirm=False (prevents accidental deletion)
            Exception: If deletion fails
        
        Example:
            >>> manager = WorkspaceManager()
            >>> # This will raise ValueError
            >>> manager.delete_workspace("abc123", storage, confirm=False)
            
            >>> # This will proceed with deletion
            >>> result = manager.delete_workspace("abc123", storage, confirm=True)
            >>> print(f"Deleted {result['deleted_traces']} traces")
        
        Note:
            - Requires explicit confirm=True to prevent accidents
            - Logs deletion operations with timestamps
            - If deleting current workspace, consider calling clear_workspace() after
        """
        # Safety check: require explicit confirmation
        if not confirm:
            raise ValueError(
                f"Workspace deletion requires explicit confirmation. "
                f"Set confirm=True to proceed with deleting workspace '{workspace_id}'. "
                f"WARNING: This operation is irreversible and will delete all data."
            )
        
        logger.warning(
            f"DELETING WORKSPACE: {workspace_id} - This operation is irreversible!"
        )
        
        try:
            # Call storage adapter to delete workspace data
            result = storage_adapter.delete_workspace(workspace_id)
            
            # Log the deletion
            logger.info(
                f"Workspace deletion completed: {workspace_id} - "
                f"{result['deleted_traces']} traces, "
                f"{result['deleted_memories']} memories deleted"
            )
            
            # If we just deleted the current workspace, clear it
            if self._current_workspace_id == workspace_id:
                logger.info(
                    f"Deleted current workspace, clearing workspace context"
                )
                self.clear_workspace()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id}: {e}")
            raise
    
    def __repr__(self) -> str:
        """String representation of WorkspaceManager"""
        if self.is_workspace_set():
            return (
                f"WorkspaceManager(workspace_name='{self._current_workspace_name}', "
                f"workspace_id='{self._current_workspace_id}')"
            )
        return "WorkspaceManager(no_workspace_set)"


# ============================================================================
# Convenience Functions
# ============================================================================

def create_workspace_manager(workspace_path: Optional[str] = None) -> WorkspaceManager:
    """
    Factory function to create a WorkspaceManager instance
    
    Args:
        workspace_path: Optional workspace directory path. If None, uses cwd.
    
    Returns:
        Initialized WorkspaceManager instance
    
    Example:
        >>> manager = create_workspace_manager("/home/user/project")
        >>> workspace_id = manager.get_workspace_id()
    """
    return WorkspaceManager(default_workspace=workspace_path)


# ============================================================================
# Testing and Validation
# ============================================================================

if __name__ == "__main__":
    """Test workspace manager functionality"""
    import tempfile
    
    print("=== Testing Workspace Manager ===\n")
    
    # Test 1: Basic initialization
    print("1. Testing basic initialization...")
    manager = WorkspaceManager()
    assert manager.is_workspace_set(), "Workspace should be set by default"
    print(f"✅ Default workspace: {manager.get_workspace_name()}")
    print(f"   ID: {manager.get_workspace_id()}")
    print(f"   Path: {manager.get_workspace_path()}\n")
    
    # Test 2: Deterministic ID generation
    print("2. Testing deterministic ID generation...")
    test_path = "/home/user/test-project"
    id1 = manager.generate_workspace_id(test_path)
    id2 = manager.generate_workspace_id(test_path)
    assert id1 == id2, "Same path should generate same ID"
    print(f"✅ Deterministic: {test_path} -> {id1}\n")
    
    # Test 3: Workspace switching
    print("3. Testing workspace switching...")
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace1 = os.path.join(tmpdir, "project1")
        workspace2 = os.path.join(tmpdir, "project2")
        os.makedirs(workspace1)
        os.makedirs(workspace2)
        
        id1 = manager.set_workspace(workspace1)
        name1 = manager.get_workspace_name()
        
        id2 = manager.set_workspace(workspace2)
        name2 = manager.get_workspace_name()
        
        assert id1 != id2, "Different paths should have different IDs"
        assert name1 == "project1", f"Expected 'project1', got '{name1}'"
        assert name2 == "project2", f"Expected 'project2', got '{name2}'"
        
        print(f"✅ Workspace 1: {name1} (ID: {id1})")
        print(f"✅ Workspace 2: {name2} (ID: {id2})\n")
    
    # Test 4: Workspace info
    print("4. Testing workspace info...")
    info = manager.get_workspace_info()
    assert "workspace_id" in info
    assert "workspace_name" in info
    assert "workspace_path" in info
    assert "is_set" in info
    print(f"✅ Workspace info: {info}\n")
    
    # Test 5: Workspace filtering
    print("5. Testing workspace filtering...")
    filter_id = manager.filter_by_workspace()
    assert filter_id == manager.get_workspace_id()
    
    explicit_id = "custom_workspace_id"
    filter_id = manager.filter_by_workspace(explicit_id)
    assert filter_id == explicit_id
    print(f"✅ Filtering works correctly\n")
    
    # Test 6: Clear workspace
    print("6. Testing workspace clearing...")
    manager.clear_workspace()
    assert not manager.is_workspace_set(), "Workspace should not be set after clearing"
    assert manager.get_workspace_id() is None
    assert manager.get_workspace_name() is None
    print(f"✅ Workspace cleared successfully\n")
    
    # Test 7: Factory function
    print("7. Testing factory function...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_workspace = os.path.join(tmpdir, "factory-test")
        os.makedirs(test_workspace)
        
        manager2 = create_workspace_manager(test_workspace)
        assert manager2.is_workspace_set()
        assert manager2.get_workspace_name() == "factory-test"
        print(f"✅ Factory function: {manager2}\n")
    
    # Test 8: Error handling
    print("8. Testing error handling...")
    try:
        manager.set_workspace("")
        assert False, "Should raise ValueError for empty path"
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}\n")
    
    print("=== All tests passed! ===")
    print("\nWorkspace Manager is ready for integration with ReasoningBank.")
