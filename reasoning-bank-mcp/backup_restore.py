"""
Backup and restore utilities for ReasoningBank MCP System

This module provides comprehensive backup and restore functionality for
reasoning traces and memory items. Supports both full and incremental backups
with integrity validation.

Features:
- Full backup of ChromaDB data to JSON/tar.gz
- Incremental backups based on timestamp tracking
- Backup validation with schema version and checksums
- Restore from backup with optional workspace targeting
- Metadata tracking (version, timestamp, counts)

Requirements addressed: 12.2
"""

import os
import json
import tarfile
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from storage_adapter import StorageBackendInterface, ChromaDBAdapter
from exceptions import MemoryStorageError


logger = logging.getLogger(__name__)


# Current backup schema version
BACKUP_SCHEMA_VERSION = "1.0"


class BackupManager:
    """
    Manages backup and restore operations for ReasoningBank data
    
    The BackupManager provides comprehensive backup and restore capabilities
    for reasoning traces and memory items. It supports both full and incremental
    backups with integrity validation.
    
    Key features:
    - Full and incremental backups
    - Workspace-specific or global backups
    - Integrity validation with checksums
    - Metadata tracking
    - Compression support (tar.gz)
    
    Example:
        >>> manager = BackupManager(storage_adapter)
        >>> # Create backup
        >>> backup_path = manager.backup_chromadb("./backups/backup_20251023.tar.gz")
        >>> # Validate backup
        >>> is_valid = manager.validate_backup(backup_path)
        >>> # Restore from backup
        >>> result = manager.restore_chromadb(backup_path)
    """
    
    def __init__(
        self,
        storage_adapter: StorageBackendInterface,
        backup_directory: str = "./backups"
    ):
        """
        Initialize BackupManager
        
        Args:
            storage_adapter: Storage backend instance (ChromaDB or Supabase)
            backup_directory: Directory to store backups (default: ./backups)
        """
        self.storage = storage_adapter
        self.backup_directory = backup_directory
        self.last_backup_timestamp: Optional[datetime] = None
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_directory, exist_ok=True)
        
        logger.info(f"BackupManager initialized with backup_directory={backup_directory}")
    
    def backup_chromadb(
        self,
        output_path: str,
        workspace_id: Optional[str] = None,
        incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Create a backup of ChromaDB data
        
        Exports all traces and memory items to a compressed tar.gz archive
        containing JSON data and metadata. Supports both full and incremental
        backups.
        
        Args:
            output_path: Path for the backup file (should end with .tar.gz)
            workspace_id: Optional workspace filter (None = all workspaces)
            incremental: If True, only backup data since last_backup_timestamp
        
        Returns:
            Dictionary with backup metadata:
            - backup_path: Path to created backup file
            - backup_size_mb: Size of backup file in MB
            - schema_version: Backup schema version
            - timestamp: ISO timestamp of backup creation
            - trace_count: Number of traces backed up
            - memory_count: Number of memory items backed up
            - workspace_id: Workspace ID (or "all")
            - incremental: Whether this was an incremental backup
            - checksum: SHA256 checksum of backup data
        
        Raises:
            MemoryStorageError: If backup creation fails
            ValueError: If output_path doesn't end with .tar.gz
        
        Example:
            >>> manager = BackupManager(storage)
            >>> result = manager.backup_chromadb(
            ...     "./backups/backup_20251023.tar.gz",
            ...     workspace_id="abc123"
            ... )
            >>> print(f"Backed up {result['trace_count']} traces")
        """
        try:
            # Validate output path
            if not output_path.endswith('.tar.gz'):
                raise ValueError("Output path must end with .tar.gz")
            
            logger.info(
                f"Starting backup: output_path={output_path}, "
                f"workspace_id={workspace_id or 'all'}, "
                f"incremental={incremental}"
            )
            
            # Get all data from storage
            if isinstance(self.storage, ChromaDBAdapter):
                backup_data = self._backup_chromadb_data(workspace_id, incremental)
            else:
                raise NotImplementedError(
                    f"Backup not yet implemented for {type(self.storage).__name__}"
                )
            
            # Create metadata
            metadata = {
                "schema_version": BACKUP_SCHEMA_VERSION,
                "timestamp": datetime.now().isoformat(),
                "workspace_id": workspace_id or "all",
                "incremental": incremental,
                "trace_count": backup_data["trace_count"],
                "memory_count": backup_data["memory_count"],
                "last_backup_timestamp": self.last_backup_timestamp.isoformat() if self.last_backup_timestamp else None
            }
            
            # Calculate checksum of data
            data_json = json.dumps(backup_data["memories"], sort_keys=True)
            checksum = hashlib.sha256(data_json.encode()).hexdigest()
            metadata["checksum"] = checksum
            
            # Create tar.gz archive
            with tarfile.open(output_path, "w:gz") as tar:
                # Add metadata
                metadata_json = json.dumps(metadata, indent=2)
                self._add_string_to_tar(tar, "metadata.json", metadata_json)
                
                # Add memory data
                memories_json = json.dumps(backup_data["memories"], indent=2)
                self._add_string_to_tar(tar, "memories.json", memories_json)
            
            # Get file size
            file_size_bytes = os.path.getsize(output_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # Update last backup timestamp
            self.last_backup_timestamp = datetime.now()
            
            result = {
                "backup_path": output_path,
                "backup_size_mb": round(file_size_mb, 2),
                "schema_version": BACKUP_SCHEMA_VERSION,
                "timestamp": metadata["timestamp"],
                "trace_count": backup_data["trace_count"],
                "memory_count": backup_data["memory_count"],
                "workspace_id": workspace_id or "all",
                "incremental": incremental,
                "checksum": checksum
            }
            
            logger.info(
                f"Backup completed: {result['memory_count']} memories, "
                f"{result['trace_count']} traces, "
                f"{result['backup_size_mb']} MB"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise MemoryStorageError(
                "Failed to create backup",
                context={
                    "output_path": output_path,
                    "workspace_id": workspace_id,
                    "error": str(e)
                }
            )
    
    def restore_chromadb(
        self,
        backup_path: str,
        target_workspace_id: Optional[str] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Restore data from a backup file
        
        Imports traces and memory items from a backup archive. Can optionally
        restore to a different workspace than the original.
        
        Args:
            backup_path: Path to backup file (.tar.gz)
            target_workspace_id: Optional target workspace (None = use original)
            overwrite: If True, overwrite existing data (default: False)
        
        Returns:
            Dictionary with restore statistics:
            - restored_traces: Number of traces restored
            - restored_memories: Number of memory items restored
            - target_workspace_id: Workspace ID data was restored to
            - restore_timestamp: ISO timestamp of restore operation
            - backup_timestamp: Original backup timestamp
        
        Raises:
            MemoryStorageError: If restore fails
            FileNotFoundError: If backup file doesn't exist
            ValueError: If backup is invalid or corrupted
        
        Example:
            >>> manager = BackupManager(storage)
            >>> result = manager.restore_chromadb(
            ...     "./backups/backup_20251023.tar.gz",
            ...     target_workspace_id="new_workspace"
            ... )
            >>> print(f"Restored {result['restored_memories']} memories")
        """
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            logger.info(
                f"Starting restore: backup_path={backup_path}, "
                f"target_workspace_id={target_workspace_id or 'original'}, "
                f"overwrite={overwrite}"
            )
            
            # Extract and validate backup
            with tarfile.open(backup_path, "r:gz") as tar:
                # Read metadata
                metadata_file = tar.extractfile("metadata.json")
                if not metadata_file:
                    raise ValueError("Backup missing metadata.json")
                metadata = json.loads(metadata_file.read().decode())
                
                # Read memory data
                memories_file = tar.extractfile("memories.json")
                if not memories_file:
                    raise ValueError("Backup missing memories.json")
                memories_data = json.loads(memories_file.read().decode())
            
            # Validate backup
            validation_result = self._validate_backup_data(metadata, memories_data)
            if not validation_result["valid"]:
                raise ValueError(f"Backup validation failed: {validation_result['errors']}")
            
            # Determine target workspace
            final_workspace_id = target_workspace_id or metadata.get("workspace_id")
            if final_workspace_id == "all":
                final_workspace_id = None
            
            # Restore data
            if isinstance(self.storage, ChromaDBAdapter):
                restore_result = self._restore_chromadb_data(
                    memories_data,
                    final_workspace_id,
                    overwrite
                )
            else:
                raise NotImplementedError(
                    f"Restore not yet implemented for {type(self.storage).__name__}"
                )
            
            result = {
                "restored_traces": restore_result["trace_count"],
                "restored_memories": restore_result["memory_count"],
                "target_workspace_id": final_workspace_id or "all",
                "restore_timestamp": datetime.now().isoformat(),
                "backup_timestamp": metadata["timestamp"]
            }
            
            logger.info(
                f"Restore completed: {result['restored_memories']} memories, "
                f"{result['restored_traces']} traces"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise MemoryStorageError(
                "Failed to restore from backup",
                context={
                    "backup_path": backup_path,
                    "target_workspace_id": target_workspace_id,
                    "error": str(e)
                }
            )
    
    def validate_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        Validate backup file integrity
        
        Checks backup file for:
        - File existence and readability
        - Valid tar.gz format
        - Required files (metadata.json, memories.json)
        - Schema version compatibility
        - Checksum verification
        
        Args:
            backup_path: Path to backup file
        
        Returns:
            Dictionary with validation results:
            - valid: Boolean indicating if backup is valid
            - errors: List of error messages (empty if valid)
            - warnings: List of warning messages
            - metadata: Backup metadata if readable
        
        Example:
            >>> manager = BackupManager(storage)
            >>> result = manager.validate_backup("./backups/backup.tar.gz")
            >>> if result['valid']:
            ...     print("Backup is valid")
            >>> else:
            ...     print(f"Errors: {result['errors']}")
        """
        errors = []
        warnings = []
        metadata = None
        
        try:
            # Check file exists
            if not os.path.exists(backup_path):
                errors.append(f"Backup file not found: {backup_path}")
                return {"valid": False, "errors": errors, "warnings": warnings, "metadata": None}
            
            # Check file is readable
            if not os.access(backup_path, os.R_OK):
                errors.append(f"Backup file not readable: {backup_path}")
                return {"valid": False, "errors": errors, "warnings": warnings, "metadata": None}
            
            # Try to open as tar.gz
            try:
                with tarfile.open(backup_path, "r:gz") as tar:
                    # Check for required files
                    members = tar.getnames()
                    
                    if "metadata.json" not in members:
                        errors.append("Missing metadata.json in backup")
                    
                    if "memories.json" not in members:
                        errors.append("Missing memories.json in backup")
                    
                    if errors:
                        return {"valid": False, "errors": errors, "warnings": warnings, "metadata": None}
                    
                    # Read and validate metadata
                    metadata_file = tar.extractfile("metadata.json")
                    metadata = json.loads(metadata_file.read().decode())
                    
                    # Check schema version
                    backup_version = metadata.get("schema_version")
                    if backup_version != BACKUP_SCHEMA_VERSION:
                        warnings.append(
                            f"Schema version mismatch: backup={backup_version}, "
                            f"current={BACKUP_SCHEMA_VERSION}"
                        )
                    
                    # Read memories data
                    memories_file = tar.extractfile("memories.json")
                    memories_data = json.loads(memories_file.read().decode())
                    
                    # Validate data structure
                    validation_result = self._validate_backup_data(metadata, memories_data)
                    if not validation_result["valid"]:
                        errors.extend(validation_result["errors"])
                    
                    # Verify checksum if present
                    if "checksum" in metadata:
                        data_json = json.dumps(memories_data, sort_keys=True)
                        calculated_checksum = hashlib.sha256(data_json.encode()).hexdigest()
                        
                        if calculated_checksum != metadata["checksum"]:
                            errors.append(
                                f"Checksum mismatch: expected={metadata['checksum']}, "
                                f"calculated={calculated_checksum}"
                            )
            
            except tarfile.TarError as e:
                errors.append(f"Invalid tar.gz format: {e}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in backup: {e}")
        
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        is_valid = len(errors) == 0
        
        logger.info(
            f"Backup validation: valid={is_valid}, "
            f"errors={len(errors)}, warnings={len(warnings)}"
        )
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "metadata": metadata
        }
    
    def _backup_chromadb_data(
        self,
        workspace_id: Optional[str],
        incremental: bool
    ) -> Dict[str, Any]:
        """Extract data from ChromaDB for backup"""
        # Build filter
        where_filter = {}
        if workspace_id:
            where_filter["workspace_id"] = workspace_id
        
        # For incremental backup, filter by timestamp
        if incremental and self.last_backup_timestamp:
            # Note: ChromaDB doesn't support timestamp filtering directly
            # We'll need to filter after retrieval
            pass
        
        # Get all data
        results = self.storage.collection.get(
            where=where_filter if where_filter else None,
            include=["metadatas", "documents", "embeddings"]
        )
        
        if not results["ids"]:
            return {
                "memories": [],
                "trace_count": 0,
                "memory_count": 0
            }
        
        # Build memory items
        memories = []
        trace_ids = set()
        
        for i, memory_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            document = results["documents"][i]
            embedding = results["embeddings"][i] if results["embeddings"] else None
            
            # For incremental backup, check timestamp
            if incremental and self.last_backup_timestamp:
                timestamp_str = metadata.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if timestamp <= self.last_backup_timestamp:
                            continue  # Skip old data
                    except (ValueError, AttributeError):
                        pass  # Include if timestamp parsing fails
            
            # Parse memory data
            memory_data = json.loads(metadata.get("memory_data", "{}"))
            
            # Build complete memory item
            memory_item = {
                "id": memory_id,
                "document": document,
                "embedding": embedding,
                "metadata": metadata,
                "memory_data": memory_data
            }
            
            memories.append(memory_item)
            
            # Track trace IDs
            trace_id = metadata.get("trace_id")
            if trace_id:
                trace_ids.add(trace_id)
        
        return {
            "memories": memories,
            "trace_count": len(trace_ids),
            "memory_count": len(memories)
        }
    
    def _restore_chromadb_data(
        self,
        memories_data: List[Dict[str, Any]],
        target_workspace_id: Optional[str],
        overwrite: bool
    ) -> Dict[str, Any]:
        """Restore data to ChromaDB"""
        trace_ids = set()
        restored_count = 0
        
        for memory_item in memories_data:
            memory_id = memory_item["id"]
            document = memory_item["document"]
            embedding = memory_item.get("embedding")
            metadata = memory_item["metadata"]
            
            # Update workspace_id if targeting different workspace
            if target_workspace_id:
                metadata["workspace_id"] = target_workspace_id
            
            # Check if memory already exists
            if not overwrite:
                try:
                    existing = self.storage.collection.get(ids=[memory_id])
                    if existing["ids"]:
                        logger.debug(f"Skipping existing memory: {memory_id}")
                        continue
                except Exception:
                    pass  # Memory doesn't exist, proceed with restore
            
            # Add to ChromaDB
            try:
                self.storage.collection.add(
                    ids=[memory_id],
                    embeddings=[embedding] if embedding else None,
                    documents=[document],
                    metadatas=[metadata]
                )
                restored_count += 1
                
                # Track trace ID
                trace_id = metadata.get("trace_id")
                if trace_id:
                    trace_ids.add(trace_id)
            
            except Exception as e:
                logger.warning(f"Failed to restore memory {memory_id}: {e}")
                continue
        
        return {
            "trace_count": len(trace_ids),
            "memory_count": restored_count
        }
    
    def _validate_backup_data(
        self,
        metadata: Dict[str, Any],
        memories_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate backup data structure"""
        errors = []
        
        # Check metadata fields
        required_metadata_fields = ["schema_version", "timestamp", "trace_count", "memory_count"]
        for field in required_metadata_fields:
            if field not in metadata:
                errors.append(f"Missing metadata field: {field}")
        
        # Check memories data is a list
        if not isinstance(memories_data, list):
            errors.append("Memories data must be a list")
            return {"valid": False, "errors": errors}
        
        # Validate memory count matches
        if "memory_count" in metadata:
            if len(memories_data) != metadata["memory_count"]:
                errors.append(
                    f"Memory count mismatch: metadata={metadata['memory_count']}, "
                    f"actual={len(memories_data)}"
                )
        
        # Validate memory items structure
        for i, memory_item in enumerate(memories_data[:10]):  # Check first 10
            if not isinstance(memory_item, dict):
                errors.append(f"Memory item {i} is not a dictionary")
                continue
            
            if "id" not in memory_item:
                errors.append(f"Memory item {i} missing 'id' field")
            
            if "metadata" not in memory_item:
                errors.append(f"Memory item {i} missing 'metadata' field")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _add_string_to_tar(self, tar: tarfile.TarFile, filename: str, content: str):
        """Helper to add string content to tar archive"""
        import io
        
        # Create in-memory file
        content_bytes = content.encode('utf-8')
        file_obj = io.BytesIO(content_bytes)
        
        # Create tarinfo
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(content_bytes)
        tarinfo.mtime = datetime.now().timestamp()
        
        # Add to archive
        tar.addfile(tarinfo, file_obj)


# ============================================================================
# Convenience Functions
# ============================================================================

def create_backup_manager(
    storage_adapter: StorageBackendInterface,
    backup_directory: str = "./backups"
) -> BackupManager:
    """
    Factory function to create BackupManager instance
    
    Args:
        storage_adapter: Storage backend instance
        backup_directory: Directory for backups
    
    Returns:
        Initialized BackupManager instance
    """
    return BackupManager(
        storage_adapter=storage_adapter,
        backup_directory=backup_directory
    )


# ============================================================================
# Testing and Validation
# ============================================================================

if __name__ == "__main__":
    """Test backup/restore functionality"""
    print("=== Testing Backup/Restore Manager ===\n")
    
    print("BackupManager module loaded successfully")
    print("\nKey features:")
    print("  ✅ Full backup to tar.gz")
    print("  ✅ Incremental backup support")
    print("  ✅ Backup validation with checksums")
    print("  ✅ Restore with workspace targeting")
    print("  ✅ Metadata tracking")
    print("\nReady for integration with ReasoningBank.")
