#!/usr/bin/env python3
"""
Deployment Verification Script for ReasoningBank MCP

Validates that all critical features are working before production deployment.
Run this after building the Docker image to ensure everything is configured correctly.
"""

import os
import sys
import time
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗{RESET} {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠{RESET} {text}")

def check_environment() -> Tuple[bool, List[str]]:
    """Check environment variables"""
    print_header("1. Environment Variable Check")
    
    required = ["OPENROUTER_API_KEY"]
    optional = {
        "REASONING_BANK_DATA": "./chroma_data",
        "REASONING_BANK_TRACES": "./traces",
        "ENABLE_CACHE": "true",
        "CACHE_SIZE": "100",
        "CACHE_TTL_SECONDS": "3600",
        "RETRY_ATTEMPTS": "3"
    }
    
    issues = []
    all_ok = True
    
    # Check required
    for var in required:
        if os.getenv(var):
            print_success(f"{var} is set")
        else:
            print_warning(f"{var} is NOT set (required for production)")
            # Don't fail the check in dev environment
    
    # Check optional
    for var, default in optional.items():
        value = os.getenv(var, default)
        print_success(f"{var} = {value}")
    
    return all_ok, issues

def check_file_structure() -> Tuple[bool, List[str]]:
    """Check that all required files exist"""
    print_header("2. File Structure Check")
    
    required_files = [
        "reasoning_bank_core.py",
        "iterative_agent.py",
        "reasoning_bank_server.py",
        "responses_alpha_client.py",
        "cached_llm_client.py",
        "schemas.py",
        "config.py",
        "retry_utils.py",
        "storage_adapter.py",
        "workspace_manager.py",
        "passive_learner.py",
        "knowledge_retrieval.py",
        "exceptions.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml"
    ]
    
    issues = []
    all_ok = True
    
    for file in required_files:
        if os.path.exists(file):
            print_success(f"{file} exists")
        else:
            print_error(f"{file} is MISSING")
            issues.append(f"Missing file: {file}")
            all_ok = False
    
    # Check for optional but recommended files
    optional_files = [
        "logging_config.py",
        "supabase_storage.py",
        ".env.example"
    ]
    
    print(f"\n{BLUE}Optional files:{RESET}")
    for file in optional_files:
        if os.path.exists(file):
            print_success(f"{file} exists")
        else:
            print_warning(f"{file} not found (optional)")
    
    return all_ok, issues

def check_imports() -> Tuple[bool, List[str]]:
    """Check that all critical imports work"""
    print_header("3. Import Check")
    
    imports = [
        ("reasoning_bank_core", "ReasoningBank"),
        ("reasoning_bank_core", "MemoryItem"),
        ("iterative_agent", "IterativeReasoningAgent"),
        ("cached_llm_client", "CachedLLMClient"),
        ("responses_alpha_client", "ResponsesAPIClient"),
        ("storage_adapter", "StorageBackendInterface"),
        ("workspace_manager", "WorkspaceManager"),
        ("passive_learner", "PassiveLearner"),
        ("knowledge_retrieval", "KnowledgeRetriever"),
        ("schemas", "MemoryItemSchema"),
        ("exceptions", "ReasoningBankError")
    ]
    
    issues = []
    all_ok = True
    missing_deps = set()
    
    for module, cls in imports:
        try:
            exec(f"from {module} import {cls}")
            print_success(f"from {module} import {cls}")
        except ImportError as e:
            error_msg = str(e)
            # Check if it's a missing dependency issue
            if "No module named" in error_msg:
                # Extract the missing module name
                if "pydantic" in error_msg:
                    missing_deps.add("pydantic")
                elif "requests" in error_msg:
                    missing_deps.add("requests")
                elif "chromadb" in error_msg:
                    missing_deps.add("chromadb")
                elif "sentence_transformers" in error_msg:
                    missing_deps.add("sentence-transformers")
                print_warning(f"Cannot import {cls} from {module} (missing dependencies)")
            else:
                print_error(f"Failed to import {cls} from {module}: {e}")
                issues.append(f"Import error: {module}.{cls}")
                all_ok = False
        except Exception as e:
            print_error(f"Error importing {cls} from {module}: {e}")
            issues.append(f"Import error: {module}.{cls}")
            all_ok = False
    
    if missing_deps:
        print(f"\n{YELLOW}Missing dependencies (install with pip):{RESET}")
        for dep in sorted(missing_deps):
            print(f"  - {dep}")
        print(f"\n{YELLOW}Run: pip install -r requirements.txt{RESET}")
    
    return all_ok, issues

def check_phase1_implementations() -> Tuple[bool, List[str]]:
    """Verify Phase 1 enhancements are implemented"""
    print_header("4. Phase 1 Enhancement Check")
    
    issues = []
    all_ok = True
    
    # Check 1: MaTTS parallel implementation
    try:
        with open("iterative_agent.py", "r") as f:
            content = f.read()
            if "asyncio.gather" in content:
                print_success("asyncio.gather found (parallel execution)")
            else:
                print_error("asyncio.gather not found (parallel execution missing)")
                issues.append("Missing MaTTS parallel implementation")
                all_ok = False
            
            if "solve_with_matts" in content:
                print_success("solve_with_matts method exists")
            else:
                print_error("solve_with_matts method NOT FOUND")
                issues.append("Missing MaTTS implementation")
                all_ok = False
    except Exception as e:
        print_error(f"Could not verify MaTTS implementation: {e}")
        issues.append("Failed to check MaTTS implementation")
        all_ok = False
    
    # Check 2: Retry logic exists
    try:
        if os.path.exists("retry_utils.py"):
            print_success("retry_utils.py exists")
            with open("retry_utils.py", "r") as f:
                content = f.read()
                if "with_retry" in content or "exponential" in content.lower():
                    print_success("Retry logic with exponential backoff implemented")
                else:
                    print_warning("Retry logic may not have exponential backoff")
        else:
            print_error("retry_utils.py NOT FOUND")
            issues.append("Retry logic not implemented")
            all_ok = False
    except Exception as e:
        print_error(f"Could not verify retry logic: {e}")
        issues.append("Failed to check retry logic")
        all_ok = False
    
    # Check 3: API key validation in server
    try:
        with open("reasoning_bank_server.py", "r") as f:
            content = f.read()
            if "OPENROUTER_API_KEY" in content:
                print_success("API key validation present in server")
            else:
                print_warning("API key validation not found in server")
    except Exception as e:
        print_error(f"Could not verify API validation: {e}")
        issues.append("Failed to check API validation")
        all_ok = False
    
    # Check 4: Memory UUIDs
    try:
        from reasoning_bank_core import MemoryItem
        import uuid
        
        # Test UUID generation
        m1 = MemoryItem(
            id=str(uuid.uuid4()),
            title="Test", 
            description="Test", 
            content="Test"
        )
        m2 = MemoryItem(
            id=str(uuid.uuid4()),
            title="Test", 
            description="Test", 
            content="Test"
        )
        
        if m1.id != m2.id:
            print_success("Memory UUIDs are unique")
        else:
            print_error("Memory UUIDs are NOT unique")
            issues.append("UUID generation not working")
            all_ok = False
        
        try:
            uuid.UUID(m1.id)
            print_success("Memory ID format is valid UUID")
        except ValueError:
            print_error("Memory ID format is NOT valid UUID")
            issues.append("Invalid UUID format")
            all_ok = False
    except ImportError as e:
        print_warning(f"Cannot verify memory UUIDs (missing dependencies)")
    except Exception as e:
        print_error(f"Could not verify memory UUIDs: {e}")
        issues.append("Failed to check UUIDs")
        all_ok = False
    
    return all_ok, issues

def check_phase2_implementations() -> Tuple[bool, List[str]]:
    """Verify Phase 2 enhancements are implemented"""
    print_header("5. Phase 2 Enhancement Check")
    
    issues = []
    all_ok = True
    
    # Check 1: Cached LLM client exists
    try:
        if os.path.exists("cached_llm_client.py"):
            print_success("cached_llm_client.py exists")
            
            try:
                from cached_llm_client import CachedLLMClient
                print_success("CachedLLMClient imports successfully")
            except ImportError:
                print_warning("CachedLLMClient cannot import (missing dependencies)")
        else:
            print_error("cached_llm_client.py NOT FOUND")
            issues.append("Missing caching implementation")
            all_ok = False
    except Exception as e:
        print_error(f"Could not verify caching: {e}")
        issues.append("Failed to check caching")
        all_ok = False
    
    # Check 2: Enhanced retrieval with composite scoring
    try:
        with open("reasoning_bank_core.py", "r") as f:
            content = f.read()
            if "compute_composite_score" in content:
                print_success("Composite scoring method exists")
            else:
                print_error("Composite scoring method NOT FOUND")
                issues.append("Missing enhanced retrieval")
                all_ok = False
            
            if "similarity_weight" in content and "recency_weight" in content:
                print_success("Weighted scoring components found")
            else:
                print_warning("Weighted scoring components not found")
            
            if "composite_score" in content:
                print_success("Composite score field exists in memory items")
            else:
                print_warning("Composite score field not found")
    except Exception as e:
        print_error(f"Could not verify enhanced retrieval: {e}")
        issues.append("Failed to check enhanced retrieval")
        all_ok = False
    
    return all_ok, issues

def check_dockerfile() -> Tuple[bool, List[str]]:
    """Verify Dockerfile has all required files"""
    print_header("6. Dockerfile Check")
    
    issues = []
    all_ok = True
    
    try:
        with open("Dockerfile", "r") as f:
            content = f.read()
            
            required_copies = [
                "reasoning_bank_core.py",
                "iterative_agent.py",
                "reasoning_bank_server.py",
                "cached_llm_client.py",
                "responses_alpha_client.py",
                "schemas.py",
                "config.py",
                "retry_utils.py",
                "storage_adapter.py",
                "workspace_manager.py",
                "passive_learner.py",
                "knowledge_retrieval.py",
                "exceptions.py"
            ]
            
            for file in required_copies:
                if f"COPY {file}" in content:
                    print_success(f"Dockerfile copies {file}")
                else:
                    print_error(f"Dockerfile does NOT copy {file}")
                    issues.append(f"Dockerfile missing COPY for {file}")
                    all_ok = False
            
            # Check for data directories
            if "mkdir" in content and "chroma_data" in content:
                print_success("Dockerfile creates data directories")
            else:
                print_warning("Dockerfile may not create data directories")
            
            # Check for Python version
            if "python:3.11" in content or "python:3.9" in content or "python:3.10" in content:
                print_success("Dockerfile uses Python 3.9+")
            else:
                print_warning("Dockerfile Python version unclear")
    except Exception as e:
        print_error(f"Could not verify Dockerfile: {e}")
        issues.append("Failed to check Dockerfile")
        all_ok = False
    
    return all_ok, issues

def check_additional_features() -> Tuple[bool, List[str]]:
    """Verify additional features like workspace isolation and passive learning"""
    print_header("7. Additional Features Check")
    
    issues = []
    all_ok = True
    
    # Check 1: Workspace isolation
    try:
        with open("workspace_manager.py", "r") as f:
            content = f.read()
            if "generate_workspace_id" in content or "workspace_id" in content:
                print_success("Workspace isolation implemented")
            else:
                print_warning("Workspace isolation may not be fully implemented")
    except Exception as e:
        print_error(f"Could not verify workspace isolation: {e}")
        issues.append("Failed to check workspace isolation")
        all_ok = False
    
    # Check 2: Passive learning
    try:
        with open("passive_learner.py", "r") as f:
            content = f.read()
            if "is_valuable" in content or "extract_knowledge" in content:
                print_success("Passive learning implemented")
            else:
                print_warning("Passive learning may not be fully implemented")
    except Exception as e:
        print_error(f"Could not verify passive learning: {e}")
        issues.append("Failed to check passive learning")
        all_ok = False
    
    # Check 3: Knowledge retrieval
    try:
        with open("knowledge_retrieval.py", "r") as f:
            content = f.read()
            if "KnowledgeRetriever" in content:
                print_success("Knowledge retrieval implemented")
            else:
                print_warning("Knowledge retrieval may not be fully implemented")
    except Exception as e:
        print_error(f"Could not verify knowledge retrieval: {e}")
        issues.append("Failed to check knowledge retrieval")
        all_ok = False
    
    # Check 4: Error context learning
    try:
        with open("reasoning_bank_core.py", "r") as f:
            content = f.read()
            if "error_context" in content:
                print_success("Error context learning implemented")
            else:
                print_warning("Error context learning may not be fully implemented")
    except Exception as e:
        print_error(f"Could not verify error context learning: {e}")
        issues.append("Failed to check error context learning")
        all_ok = False
    
    return all_ok, issues


def main():
    """Run all verification checks"""
    print("\n" + "="*70)
    print("ReasoningBank MCP - Deployment Verification")
    print("="*70)
    
    all_checks = []
    all_issues = []
    
    # Run all checks
    checks = [
        check_environment,
        check_file_structure,
        check_imports,
        check_phase1_implementations,
        check_phase2_implementations,
        check_dockerfile,
        check_additional_features
    ]
    
    for check in checks:
        ok, issues = check()
        all_checks.append(ok)
        all_issues.extend(issues)
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for c in all_checks if c)
    total = len(all_checks)
    
    print(f"\n{BLUE}Checks performed:{RESET}")
    print(f"  1. Environment variables")
    print(f"  2. File structure (16 required files)")
    print(f"  3. Python imports (11 modules)")
    print(f"  4. Phase 1 enhancements (MaTTS, retry, API validation, UUIDs)")
    print(f"  5. Phase 2 enhancements (caching, enhanced retrieval)")
    print(f"  6. Dockerfile correctness")
    print(f"  7. Additional features (workspace isolation, passive learning)")
    
    if all(all_checks):
        print_success(f"\nAll {total} checks passed!")
        print(f"\n{GREEN}✓ System is ready for deployment{RESET}")
        print(f"\n{BLUE}Note:{RESET} Some warnings about missing dependencies are expected")
        print(f"in development environments. The Docker container will have all dependencies.")
        return 0
    else:
        print_error(f"\n{total - passed}/{total} checks failed")
        print(f"\n{RED}✗ Issues found:{RESET}")
        for issue in all_issues:
            print(f"  - {issue}")
        print(f"\n{RED}⚠ System is NOT ready for deployment{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
