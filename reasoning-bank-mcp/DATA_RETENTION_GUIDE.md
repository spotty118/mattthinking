# Data Retention and Cleanup Guide

## Quick Reference

This guide provides practical examples for using the data retention, cleanup, and backup features in ReasoningBank MCP System.

## Table of Contents

1. [Trace Cleanup](#trace-cleanup)
2. [Workspace Deletion](#workspace-deletion)
3. [Backup Operations](#backup-operations)
4. [Restore Operations](#restore-operations)
5. [Best Practices](#best-practices)

---

## Trace Cleanup

### Basic Cleanup (90-day retention)

```python
from reasoning_bank_core import ReasoningBank
from storage_adapter import create_storage_backend
from cached_llm_client import CachedLLMClient

# Initialize components
storage = create_storage_backend("chromadb")
llm_client = CachedLLMClient(...)
bank = ReasoningBank(storage, llm_client)

# Clean up traces older than 90 days (default)
result = bank.cleanup_old_traces()

print(f"Deleted {result['deleted_traces_count']} traces")
print(f"Deleted {result['deleted_memories_count']} memories")
print(f"Freed approximately {result['freed_space_mb']} MB")
print(f"Cutoff date: {result['retention_cutoff']}")
```

### Custom Retention Period

```python
# Keep only last 30 days
result = bank.cleanup_old_traces(retention_days=30)

# Keep only last 7 days
result = bank.cleanup_old_traces(retention_days=7)

# Keep only last 180 days (6 months)
result = bank.cleanup_old_traces(retention_days=180)
```

### Workspace-Specific Cleanup

```python
# Clean up specific workspace
result = bank.cleanup_old_traces(
    retention_days=90,
    workspace_id="project_abc123"
)

# Clean up current workspace
from workspace_manager import WorkspaceManager

workspace_manager = WorkspaceManager()
current_workspace = workspace_manager.get_workspace_id()

result = bank.cleanup_old_traces(
    retention_days=90,
    workspace_id=current_workspace
)
```

### Scheduled Cleanup Example

```python
import schedule
import time

def daily_cleanup():
    """Run daily cleanup keeping last 90 days"""
    result = bank.cleanup_old_traces(retention_days=90)
    print(f"Daily cleanup: deleted {result['deleted_traces_count']} traces")

# Schedule cleanup to run daily at 2 AM
schedule.every().day.at("02:00").do(daily_cleanup)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
```

---

## Workspace Deletion

### Safe Deletion (with confirmation)

```python
from workspace_manager import WorkspaceManager
from storage_adapter import create_storage_backend

workspace_manager = WorkspaceManager()
storage = create_storage_backend("chromadb")

# This will raise ValueError (safety check)
try:
    result = workspace_manager.delete_workspace(
        workspace_id="old_project",
        storage_adapter=storage,
        confirm=False  # Default
    )
except ValueError as e:
    print(f"Prevented accidental deletion: {e}")

# Explicit confirmation required
result = workspace_manager.delete_workspace(
    workspace_id="old_project",
    storage_adapter=storage,
    confirm=True  # Must be explicit
)

print(f"Deleted workspace: {result['workspace_id']}")
print(f"Deleted {result['deleted_traces']} traces")
print(f"Deleted {result['deleted_memories']} memories")
print(f"Deletion timestamp: {result['deletion_timestamp']}")
```

### Delete Current Workspace

```python
# Get current workspace
current_workspace = workspace_manager.get_workspace_id()

# Delete it (will also clear workspace context)
result = workspace_manager.delete_workspace(
    workspace_id=current_workspace,
    storage_adapter=storage,
    confirm=True
)

# Workspace context is automatically cleared
assert not workspace_manager.is_workspace_set()
```

### Bulk Workspace Deletion

```python
# Delete multiple old workspaces
old_workspaces = [
    "project_2023_q1",
    "project_2023_q2",
    "project_2023_q3"
]

for workspace_id in old_workspaces:
    try:
        result = workspace_manager.delete_workspace(
            workspace_id=workspace_id,
            storage_adapter=storage,
            confirm=True
        )
        print(f"✅ Deleted {workspace_id}: {result['deleted_traces']} traces")
    except Exception as e:
        print(f"❌ Failed to delete {workspace_id}: {e}")
```

---

## Backup Operations

### Create Full Backup

```python
from backup_restore import BackupManager
from storage_adapter import create_storage_backend
from datetime import datetime

storage = create_storage_backend("chromadb")
backup_manager = BackupManager(storage, backup_directory="./backups")

# Create backup with timestamp in filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"./backups/full_backup_{timestamp}.tar.gz"

result = backup_manager.backup_chromadb(
    output_path=backup_path
)

print(f"Backup created: {result['backup_path']}")
print(f"Size: {result['backup_size_mb']} MB")
print(f"Traces: {result['trace_count']}")
print(f"Memories: {result['memory_count']}")
print(f"Checksum: {result['checksum']}")
```

### Workspace-Specific Backup

```python
# Backup specific workspace
result = backup_manager.backup_chromadb(
    output_path="./backups/project_abc_backup.tar.gz",
    workspace_id="project_abc123"
)
```

### Incremental Backup

```python
# First backup (full)
result1 = backup_manager.backup_chromadb(
    output_path="./backups/full_backup.tar.gz"
)

# Later, incremental backup (only new data)
result2 = backup_manager.backup_chromadb(
    output_path="./backups/incremental_backup.tar.gz",
    incremental=True
)

print(f"Incremental backup: {result2['memory_count']} new memories")
```

### Automated Daily Backups

```python
import schedule
from datetime import datetime

def daily_backup():
    """Create daily backup"""
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_path = f"./backups/daily_backup_{timestamp}.tar.gz"
    
    result = backup_manager.backup_chromadb(
        output_path=backup_path,
        incremental=True
    )
    
    print(f"Daily backup: {result['memory_count']} memories, {result['backup_size_mb']} MB")

# Schedule daily backup at 3 AM
schedule.every().day.at("03:00").do(daily_backup)
```

### Validate Backup

```python
# Validate backup before restore
validation = backup_manager.validate_backup(
    "./backups/full_backup_20251023.tar.gz"
)

if validation['valid']:
    print("✅ Backup is valid")
    print(f"Metadata: {validation['metadata']}")
    
    if validation['warnings']:
        print(f"⚠️  Warnings: {validation['warnings']}")
else:
    print("❌ Backup is invalid")
    print(f"Errors: {validation['errors']}")
```

---

## Restore Operations

### Basic Restore

```python
# Restore from backup to original workspace
result = backup_manager.restore_chromadb(
    backup_path="./backups/full_backup_20251023.tar.gz"
)

print(f"Restored {result['restored_traces']} traces")
print(f"Restored {result['restored_memories']} memories")
print(f"Target workspace: {result['target_workspace_id']}")
```

### Restore to Different Workspace

```python
# Restore to new workspace (useful for testing or migration)
result = backup_manager.restore_chromadb(
    backup_path="./backups/full_backup_20251023.tar.gz",
    target_workspace_id="new_project_workspace"
)

print(f"Restored to workspace: {result['target_workspace_id']}")
```

### Restore with Overwrite

```python
# Overwrite existing data (use with caution)
result = backup_manager.restore_chromadb(
    backup_path="./backups/full_backup_20251023.tar.gz",
    overwrite=True
)
```

### Safe Restore Workflow

```python
# 1. Validate backup first
validation = backup_manager.validate_backup(backup_path)

if not validation['valid']:
    print(f"Cannot restore: {validation['errors']}")
    exit(1)

# 2. Check what will be restored
metadata = validation['metadata']
print(f"Will restore:")
print(f"  - {metadata['trace_count']} traces")
print(f"  - {metadata['memory_count']} memories")
print(f"  - From: {metadata['timestamp']}")

# 3. Confirm with user
confirm = input("Proceed with restore? (yes/no): ")
if confirm.lower() != 'yes':
    print("Restore cancelled")
    exit(0)

# 4. Perform restore
result = backup_manager.restore_chromadb(backup_path)
print(f"✅ Restore completed: {result['restored_memories']} memories")
```

---

## Best Practices

### 1. Regular Cleanup Schedule

```python
# Recommended: Clean up old traces monthly
# Keep 90 days of data for most use cases
# Keep 180 days for compliance-heavy environments

def monthly_cleanup():
    result = bank.cleanup_old_traces(retention_days=90)
    print(f"Monthly cleanup: freed {result['freed_space_mb']} MB")

schedule.every().month.do(monthly_cleanup)
```

### 2. Backup Before Major Operations

```python
def safe_workspace_deletion(workspace_id):
    """Delete workspace with backup"""
    # 1. Create backup first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"./backups/pre_delete_{workspace_id}_{timestamp}.tar.gz"
    
    backup_result = backup_manager.backup_chromadb(
        output_path=backup_path,
        workspace_id=workspace_id
    )
    print(f"✅ Backup created: {backup_path}")
    
    # 2. Delete workspace
    delete_result = workspace_manager.delete_workspace(
        workspace_id=workspace_id,
        storage_adapter=storage,
        confirm=True
    )
    print(f"✅ Workspace deleted: {delete_result['deleted_traces']} traces")
    
    return backup_path, delete_result
```

### 3. Backup Rotation Strategy

```python
import os
from pathlib import Path

def rotate_backups(backup_dir="./backups", keep_days=30):
    """Delete backups older than keep_days"""
    cutoff_time = datetime.now() - timedelta(days=keep_days)
    
    for backup_file in Path(backup_dir).glob("*.tar.gz"):
        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        
        if file_time < cutoff_time:
            backup_file.unlink()
            print(f"Deleted old backup: {backup_file.name}")

# Run weekly
schedule.every().week.do(lambda: rotate_backups(keep_days=30))
```

### 4. Monitor Storage Usage

```python
def check_storage_health():
    """Monitor storage and trigger cleanup if needed"""
    stats = storage.get_statistics()
    
    print(f"Storage Health:")
    print(f"  Total traces: {stats['total_traces']}")
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Success rate: {stats['success_rate']}%")
    
    # Trigger cleanup if too many traces
    if stats['total_traces'] > 10000:
        print("⚠️  High trace count, running cleanup...")
        result = bank.cleanup_old_traces(retention_days=60)
        print(f"✅ Cleaned up {result['deleted_traces_count']} traces")

# Check daily
schedule.every().day.at("01:00").do(check_storage_health)
```

### 5. Disaster Recovery Plan

```python
# 1. Daily incremental backups
schedule.every().day.at("03:00").do(
    lambda: backup_manager.backup_chromadb(
        f"./backups/daily_{datetime.now().strftime('%Y%m%d')}.tar.gz",
        incremental=True
    )
)

# 2. Weekly full backups
schedule.every().sunday.at("02:00").do(
    lambda: backup_manager.backup_chromadb(
        f"./backups/weekly_{datetime.now().strftime('%Y%m%d')}.tar.gz",
        incremental=False
    )
)

# 3. Monthly archive backups (keep forever)
def monthly_archive():
    timestamp = datetime.now().strftime("%Y%m")
    backup_path = f"./backups/archive/monthly_{timestamp}.tar.gz"
    os.makedirs("./backups/archive", exist_ok=True)
    
    result = backup_manager.backup_chromadb(backup_path)
    print(f"Monthly archive: {result['backup_size_mb']} MB")

schedule.every().month.do(monthly_archive)
```

### 6. Workspace Lifecycle Management

```python
class WorkspaceLifecycleManager:
    """Manage workspace lifecycle with backups"""
    
    def __init__(self, workspace_manager, storage, backup_manager):
        self.workspace_manager = workspace_manager
        self.storage = storage
        self.backup_manager = backup_manager
    
    def archive_workspace(self, workspace_id):
        """Archive workspace before deletion"""
        # Create backup
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_path = f"./backups/archive/{workspace_id}_{timestamp}.tar.gz"
        
        backup_result = self.backup_manager.backup_chromadb(
            output_path=backup_path,
            workspace_id=workspace_id
        )
        
        # Delete workspace
        delete_result = self.workspace_manager.delete_workspace(
            workspace_id=workspace_id,
            storage_adapter=self.storage,
            confirm=True
        )
        
        return {
            "backup_path": backup_path,
            "backup_size_mb": backup_result['backup_size_mb'],
            "deleted_traces": delete_result['deleted_traces'],
            "deleted_memories": delete_result['deleted_memories']
        }
    
    def restore_workspace(self, backup_path, new_workspace_id=None):
        """Restore archived workspace"""
        # Validate backup
        validation = self.backup_manager.validate_backup(backup_path)
        if not validation['valid']:
            raise ValueError(f"Invalid backup: {validation['errors']}")
        
        # Restore
        result = self.backup_manager.restore_chromadb(
            backup_path=backup_path,
            target_workspace_id=new_workspace_id
        )
        
        return result

# Usage
lifecycle = WorkspaceLifecycleManager(workspace_manager, storage, backup_manager)

# Archive old project
result = lifecycle.archive_workspace("old_project_2023")
print(f"Archived: {result['backup_path']}")

# Restore if needed
result = lifecycle.restore_workspace(
    "./backups/archive/old_project_2023_20251023.tar.gz",
    new_workspace_id="restored_project"
)
```

---

## Error Handling

### Robust Cleanup

```python
def safe_cleanup(retention_days=90):
    """Cleanup with error handling"""
    try:
        result = bank.cleanup_old_traces(retention_days=retention_days)
        print(f"✅ Cleanup successful: {result['deleted_traces_count']} traces")
        return result
    except MemoryStorageError as e:
        print(f"❌ Cleanup failed: {e}")
        # Log error, send alert, etc.
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
```

### Robust Backup

```python
def safe_backup(output_path, workspace_id=None):
    """Backup with error handling and validation"""
    try:
        # Create backup
        result = backup_manager.backup_chromadb(
            output_path=output_path,
            workspace_id=workspace_id
        )
        
        # Validate immediately
        validation = backup_manager.validate_backup(output_path)
        
        if not validation['valid']:
            print(f"⚠️  Backup created but validation failed: {validation['errors']}")
            return None
        
        print(f"✅ Backup successful: {result['backup_size_mb']} MB")
        return result
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None
```

---

## Summary

Key points to remember:

1. **Cleanup**: Use `cleanup_old_traces()` for regular maintenance
2. **Deletion**: Always use `confirm=True` for workspace deletion
3. **Backup**: Create backups before major operations
4. **Validation**: Always validate backups before restore
5. **Automation**: Use scheduling for regular maintenance
6. **Monitoring**: Track storage usage and health metrics

For more details, see:
- `TASK_27_IMPLEMENTATION.md` - Technical implementation details
- `backup_restore.py` - Backup/restore source code
- `storage_adapter.py` - Storage interface and implementation
- `workspace_manager.py` - Workspace management
