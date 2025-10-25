"""
Test script for memory genealogy functionality

This script tests:
1. Creating memories with parent-child relationships
2. Retrieving genealogy information
3. Tracing ancestry chains
4. Finding descendants
"""

import os
import sys
import uuid
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reasoning_bank_core import ReasoningBank
from storage_adapter import create_storage_backend
from cached_llm_client import CachedLLMClient
from responses_alpha_client import ResponsesAPIClient
from config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_genealogy():
    """Test memory genealogy tracking"""
    
    print("=== Testing Memory Genealogy ===\n")
    
    # 1. Initialize components
    print("1. Initializing ReasoningBank...")
    config = get_config()
    
    # Create storage backend
    storage = create_storage_backend(
        backend_type="chromadb",
        persist_directory="./test_genealogy_data",
        collection_name="test_genealogy"
    )
    
    # Create LLM client (mock for testing)
    responses_client = ResponsesAPIClient(
        api_key=config.api_key or "test_key",
        default_model=config.model
    )
    llm_client = CachedLLMClient(
        client=responses_client,
        enable_cache=False  # Disable cache for testing
    )
    
    # Create ReasoningBank
    bank = ReasoningBank(
        storage_backend=storage,
        llm_client=llm_client,
        max_memory_items=5,
        retrieval_k=5
    )
    print("✅ ReasoningBank initialized\n")
    
    # 2. Create root memory (generation 0)
    print("2. Creating root memory...")
    root_memory_id = str(uuid.uuid4())
    root_memory = {
        "id": root_memory_id,
        "title": "Binary Search Algorithm",
        "description": "Efficient search in sorted arrays",
        "content": "Binary search works by repeatedly dividing the search interval in half...",
        "pattern_tags": ["algorithms", "binary_search"],
        "difficulty_level": "moderate",
        "domain_category": "algorithms",
        "evolution_stage": 0
    }
    
    trace_id_1 = bank.store_trace(
        task="Implement binary search",
        trajectory=[{"iteration": 1, "action": "generate", "output": "code"}],
        outcome="success",
        memory_items=[root_memory]
    )
    print(f"✅ Root memory created: {root_memory_id}\n")
    
    # 3. Create child memory (generation 1)
    print("3. Creating child memory derived from root...")
    child_memory_id = str(uuid.uuid4())
    child_memory = {
        "id": child_memory_id,
        "title": "Binary Search with Error Handling",
        "description": "Binary search with input validation",
        "content": "Enhanced binary search that validates input arrays and handles edge cases...",
        "pattern_tags": ["algorithms", "binary_search", "error_handling"],
        "difficulty_level": "moderate",
        "domain_category": "algorithms",
        "parent_memory_id": root_memory_id,
        "evolution_stage": 1
    }
    
    trace_id_2 = bank.store_trace(
        task="Improve binary search with error handling",
        trajectory=[{"iteration": 1, "action": "refine", "output": "improved code"}],
        outcome="success",
        memory_items=[child_memory]
    )
    print(f"✅ Child memory created: {child_memory_id}\n")
    
    # 4. Create grandchild memory (generation 2)
    print("4. Creating grandchild memory...")
    grandchild_memory_id = str(uuid.uuid4())
    grandchild_memory = {
        "id": grandchild_memory_id,
        "title": "Optimized Binary Search with Logging",
        "description": "Binary search with performance optimization and logging",
        "content": "Further optimized binary search with detailed logging for debugging...",
        "pattern_tags": ["algorithms", "binary_search", "optimization", "logging"],
        "difficulty_level": "complex",
        "domain_category": "algorithms",
        "parent_memory_id": child_memory_id,
        "evolution_stage": 2
    }
    
    trace_id_3 = bank.store_trace(
        task="Optimize binary search with logging",
        trajectory=[{"iteration": 1, "action": "refine", "output": "optimized code"}],
        outcome="success",
        memory_items=[grandchild_memory]
    )
    print(f"✅ Grandchild memory created: {grandchild_memory_id}\n")
    
    # 5. Create sibling memory (also generation 1, different branch)
    print("5. Creating sibling memory (alternative evolution)...")
    sibling_memory_id = str(uuid.uuid4())
    sibling_memory = {
        "id": sibling_memory_id,
        "title": "Binary Search for Strings",
        "description": "Binary search adapted for string arrays",
        "content": "Binary search modified to work with string comparisons...",
        "pattern_tags": ["algorithms", "binary_search", "strings"],
        "difficulty_level": "moderate",
        "domain_category": "algorithms",
        "parent_memory_id": root_memory_id,
        "evolution_stage": 1
    }
    
    trace_id_4 = bank.store_trace(
        task="Adapt binary search for strings",
        trajectory=[{"iteration": 1, "action": "adapt", "output": "string version"}],
        outcome="success",
        memory_items=[sibling_memory]
    )
    print(f"✅ Sibling memory created: {sibling_memory_id}\n")
    
    # 6. Create memory derived from multiple parents
    print("6. Creating memory derived from multiple parents...")
    merged_memory_id = str(uuid.uuid4())
    merged_memory = {
        "id": merged_memory_id,
        "title": "Universal Binary Search",
        "description": "Binary search that works with any comparable type",
        "content": "Generic binary search combining error handling and type flexibility...",
        "pattern_tags": ["algorithms", "binary_search", "generics"],
        "difficulty_level": "complex",
        "domain_category": "algorithms",
        "parent_memory_id": child_memory_id,
        "derived_from": [child_memory_id, sibling_memory_id],
        "evolution_stage": 2
    }
    
    trace_id_5 = bank.store_trace(
        task="Create universal binary search",
        trajectory=[{"iteration": 1, "action": "merge", "output": "generic code"}],
        outcome="success",
        memory_items=[merged_memory]
    )
    print(f"✅ Merged memory created: {merged_memory_id}\n")
    
    # 7. Test genealogy retrieval for root
    print("7. Testing genealogy retrieval for root memory...")
    root_genealogy = bank.get_genealogy(root_memory_id)
    print(f"Root Memory Genealogy:")
    print(f"  Memory ID: {root_genealogy['memory_id']}")
    print(f"  Title: {root_genealogy['memory_title']}")
    print(f"  Evolution Stage: {root_genealogy['evolution_stage']}")
    print(f"  Is Root: {root_genealogy['is_root']}")
    print(f"  Is Leaf: {root_genealogy['is_leaf']}")
    print(f"  Total Ancestors: {root_genealogy['total_ancestors']}")
    print(f"  Total Descendants: {root_genealogy['total_descendants']}")
    print(f"  Children: {len(root_genealogy['children'])}")
    for child in root_genealogy['children']:
        print(f"    - {child['title']} (stage {child['evolution_stage']})")
    print()
    
    # 8. Test genealogy retrieval for child
    print("8. Testing genealogy retrieval for child memory...")
    child_genealogy = bank.get_genealogy(child_memory_id)
    print(f"Child Memory Genealogy:")
    print(f"  Memory ID: {child_genealogy['memory_id']}")
    print(f"  Title: {child_genealogy['memory_title']}")
    print(f"  Evolution Stage: {child_genealogy['evolution_stage']}")
    print(f"  Is Root: {child_genealogy['is_root']}")
    print(f"  Is Leaf: {child_genealogy['is_leaf']}")
    print(f"  Total Ancestors: {child_genealogy['total_ancestors']}")
    print(f"  Total Descendants: {child_genealogy['total_descendants']}")
    print(f"  Parents: {len(child_genealogy['parents'])}")
    for parent in child_genealogy['parents']:
        print(f"    - {parent['title']} (stage {parent['evolution_stage']})")
    print(f"  Children: {len(child_genealogy['children'])}")
    for child in child_genealogy['children']:
        print(f"    - {child['title']} (stage {child['evolution_stage']})")
    print(f"  Ancestry Chain: {' -> '.join(child_genealogy['ancestry_chain'])}")
    print()
    
    # 9. Test genealogy retrieval for grandchild
    print("9. Testing genealogy retrieval for grandchild memory...")
    grandchild_genealogy = bank.get_genealogy(grandchild_memory_id)
    print(f"Grandchild Memory Genealogy:")
    print(f"  Memory ID: {grandchild_genealogy['memory_id']}")
    print(f"  Title: {grandchild_genealogy['memory_title']}")
    print(f"  Evolution Stage: {grandchild_genealogy['evolution_stage']}")
    print(f"  Is Root: {grandchild_genealogy['is_root']}")
    print(f"  Is Leaf: {grandchild_genealogy['is_leaf']}")
    print(f"  Total Ancestors: {grandchild_genealogy['total_ancestors']}")
    print(f"  Ancestry Chain Length: {len(grandchild_genealogy['ancestry_chain'])}")
    print(f"  Ancestry Chain: {' -> '.join(grandchild_genealogy['ancestry_chain'])}")
    print()
    
    # 10. Test genealogy for merged memory
    print("10. Testing genealogy retrieval for merged memory...")
    merged_genealogy = bank.get_genealogy(merged_memory_id)
    print(f"Merged Memory Genealogy:")
    print(f"  Memory ID: {merged_genealogy['memory_id']}")
    print(f"  Title: {merged_genealogy['memory_title']}")
    print(f"  Evolution Stage: {merged_genealogy['evolution_stage']}")
    print(f"  Parents: {len(merged_genealogy['parents'])}")
    for parent in merged_genealogy['parents']:
        relationship = parent.get('relationship', 'parent')
        print(f"    - {parent['title']} (stage {parent['evolution_stage']}, {relationship})")
    print(f"  Derived From: {merged_genealogy['derived_from']}")
    print()
    
    # 11. Verify requirements
    print("11. Verifying requirements...")
    
    # Requirement 8.1: Parent memory UUID recorded
    assert child_genealogy['parents'][0]['id'] == root_memory_id, "Parent UUID not recorded correctly"
    print("✅ Requirement 8.1: Parent memory UUID recorded")
    
    # Requirement 8.2: Evolution stage tracking
    assert root_genealogy['evolution_stage'] == 0, "Root evolution stage incorrect"
    assert child_genealogy['evolution_stage'] == 1, "Child evolution stage incorrect"
    assert grandchild_genealogy['evolution_stage'] == 2, "Grandchild evolution stage incorrect"
    print("✅ Requirement 8.2: Evolution stage numbers tracked")
    
    # Requirement 8.3: Complete ancestry tree returned
    assert len(grandchild_genealogy['ancestry_chain']) == 3, "Ancestry chain incomplete"
    assert grandchild_genealogy['ancestry_chain'][0] == root_memory_id, "Ancestry chain root incorrect"
    assert grandchild_genealogy['ancestry_chain'][-1] == grandchild_memory_id, "Ancestry chain leaf incorrect"
    print("✅ Requirement 8.3: Complete ancestry tree returned")
    
    # Requirement 8.4: Query all memories derived from parent
    assert root_genealogy['total_descendants'] >= 2, "Descendants not found"
    print("✅ Requirement 8.4: All derived memories queryable")
    
    # Requirement 8.5: Genealogy metadata included
    assert 'evolution_stage' in child_genealogy, "Evolution stage missing"
    assert 'parents' in child_genealogy, "Parents missing"
    assert 'children' in child_genealogy, "Children missing"
    print("✅ Requirement 8.5: Genealogy metadata included")
    
    print("\n=== All Genealogy Tests Passed! ===")
    
    return True


if __name__ == "__main__":
    try:
        success = test_genealogy()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
