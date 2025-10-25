"""
Basic verification test for KnowledgeRetriever implementation.

This script tests core functionality:
- Integration with ReasoningBank
- Domain category filtering
- Pattern tag filtering
- Relevance ranking
- Formatted output generation
"""

from unittest.mock import Mock, MagicMock
from knowledge_retrieval import KnowledgeRetriever, KnowledgeRetrieverConfig
from reasoning_bank_core import MemoryItem


def test_initialization():
    """Test that KnowledgeRetriever initializes correctly."""
    print("Testing initialization...")
    
    # Create mock ReasoningBank
    mock_bank = Mock()
    
    # Test with default config
    retriever = KnowledgeRetriever(mock_bank)
    assert retriever.reasoning_bank == mock_bank
    assert retriever.config.default_n_results == 5
    assert retriever.config.min_relevance_score == 0.3
    
    # Test with custom config
    custom_config = KnowledgeRetrieverConfig(
        default_n_results=10,
        min_relevance_score=0.5
    )
    retriever2 = KnowledgeRetriever(mock_bank, custom_config)
    assert retriever2.config.default_n_results == 10
    assert retriever2.config.min_relevance_score == 0.5
    
    print("✓ Initialization works correctly")


def test_retrieve_basic():
    """Test basic retrieval functionality."""
    print("\nTesting basic retrieval...")
    
    # Create mock ReasoningBank
    mock_bank = Mock()
    
    # Create mock memory items
    mock_memories = [
        MemoryItem(
            id="mem1",
            title="Binary Search",
            description="Search in sorted arrays",
            content="Use left/right pointers...",
            composite_score=0.9,
            pattern_tags=["algorithms", "binary_search"],
            domain_category="algorithms"
        ),
        MemoryItem(
            id="mem2",
            title="Error Handling",
            description="Validate inputs",
            content="Check for None...",
            composite_score=0.7,
            pattern_tags=["error_handling"],
            domain_category="best_practices"
        )
    ]
    
    mock_bank.retrieve_memories = Mock(return_value=mock_memories)
    
    retriever = KnowledgeRetriever(mock_bank)
    
    # Test basic retrieval
    results = retriever.retrieve(query="how to search arrays", n_results=5)
    
    assert len(results) == 2
    assert results[0].title == "Binary Search"
    assert mock_bank.retrieve_memories.called
    
    # Verify the call arguments
    call_args = mock_bank.retrieve_memories.call_args
    assert call_args[1]["query"] == "how to search arrays"
    assert call_args[1]["n_results"] == 5
    
    print("✓ Basic retrieval works correctly")


def test_domain_filtering():
    """Test domain category filtering."""
    print("\nTesting domain filtering...")
    
    mock_bank = Mock()
    
    mock_memories = [
        MemoryItem(
            id="mem1",
            title="Algorithm Memory",
            description="Test",
            content="Test content",
            composite_score=0.8,
            domain_category="algorithms"
        )
    ]
    
    mock_bank.retrieve_memories = Mock(return_value=mock_memories)
    
    retriever = KnowledgeRetriever(mock_bank)
    
    # Test domain filtering
    results = retriever.retrieve_by_domain(
        query="test query",
        domain="algorithms",
        n_results=5
    )
    
    # Verify domain filter was passed
    call_args = mock_bank.retrieve_memories.call_args
    assert call_args[1]["domain_filter"] == "algorithms"
    
    print("✓ Domain filtering works correctly")


def test_pattern_tag_filtering():
    """Test pattern tag filtering."""
    print("\nTesting pattern tag filtering...")
    
    mock_bank = Mock()
    
    # Create memories with different tags
    mock_memories = [
        MemoryItem(
            id="mem1",
            title="Memory 1",
            description="Test",
            content="Test",
            composite_score=0.9,
            pattern_tags=["algorithms", "binary_search"]
        ),
        MemoryItem(
            id="mem2",
            title="Memory 2",
            description="Test",
            content="Test",
            composite_score=0.8,
            pattern_tags=["error_handling", "validation"]
        ),
        MemoryItem(
            id="mem3",
            title="Memory 3",
            description="Test",
            content="Test",
            composite_score=0.7,
            pattern_tags=["algorithms", "sorting"]
        )
    ]
    
    mock_bank.retrieve_memories = Mock(return_value=mock_memories)
    
    retriever = KnowledgeRetriever(mock_bank)
    
    # Test tag filtering
    results = retriever.retrieve_by_tags(
        query="test query",
        tags=["algorithms"],
        n_results=5
    )
    
    # Should return memories with "algorithms" tag
    assert len(results) == 2
    assert all("algorithms" in (m.pattern_tags or []) for m in results)
    
    print("✓ Pattern tag filtering works correctly")


def test_error_pattern_retrieval():
    """Test retrieval of error patterns."""
    print("\nTesting error pattern retrieval...")
    
    mock_bank = Mock()
    
    mock_memories = [
        MemoryItem(
            id="mem1",
            title="Success Memory",
            description="Test",
            content="Test",
            composite_score=0.9,
            error_context=None
        ),
        MemoryItem(
            id="mem2",
            title="Error Memory",
            description="Test",
            content="Test",
            composite_score=0.8,
            error_context={
                "error_type": "TypeError",
                "failure_pattern": "Missing validation",
                "corrective_guidance": "Add type checks"
            }
        )
    ]
    
    mock_bank.retrieve_memories = Mock(return_value=mock_memories)
    
    retriever = KnowledgeRetriever(mock_bank)
    
    # Test error pattern retrieval
    results = retriever.retrieve_error_patterns(
        query="common errors",
        n_results=5
    )
    
    # Should only return memories with error context
    assert len(results) == 1
    assert results[0].error_context is not None
    
    print("✓ Error pattern retrieval works correctly")


def test_format_for_prompt():
    """Test formatting memories for LLM prompts."""
    print("\nTesting prompt formatting...")
    
    mock_bank = Mock()
    retriever = KnowledgeRetriever(mock_bank)
    
    memories = [
        MemoryItem(
            id="mem1",
            title="Binary Search",
            description="Efficient search in sorted arrays",
            content="Use divide and conquer approach with left/right pointers",
            composite_score=0.9,
            pattern_tags=["algorithms", "binary_search"],
            difficulty_level="moderate",
            domain_category="algorithms"
        ),
        MemoryItem(
            id="mem2",
            title="Error Handling",
            description="Always validate inputs",
            content="Check for None and invalid types",
            composite_score=0.7,
            error_context={
                "error_type": "TypeError",
                "failure_pattern": "Missing validation",
                "corrective_guidance": "Add type checks"
            }
        )
    ]
    
    # Test formatting
    formatted = retriever.format_for_prompt(memories, include_metadata=True)
    
    assert "Binary Search" in formatted
    assert "Error Handling" in formatted
    assert "⚠️" in formatted  # Error warning symbol
    assert "algorithms" in formatted
    assert "moderate" in formatted
    
    print("✓ Prompt formatting works correctly")


def test_statistics():
    """Test statistics tracking."""
    print("\nTesting statistics tracking...")
    
    mock_bank = Mock()
    mock_bank.retrieve_memories = Mock(return_value=[])
    
    retriever = KnowledgeRetriever(mock_bank)
    
    # Make some queries
    retriever.retrieve(query="test1", n_results=5)
    retriever.retrieve(query="test2", n_results=5)
    
    stats = retriever.get_statistics()
    
    assert stats["queries_executed"] == 2
    assert "avg_memories_per_query" in stats
    assert "config" in stats
    
    print(f"✓ Statistics tracking works correctly: {stats}")


def test_relevance_ranking():
    """Test relevance ranking functionality."""
    print("\nTesting relevance ranking...")
    
    mock_bank = Mock()
    retriever = KnowledgeRetriever(mock_bank)
    
    # Create memories with different scores
    memories = [
        MemoryItem(
            id="mem1",
            title="Low Score",
            description="Test",
            content="Test",
            composite_score=0.5
        ),
        MemoryItem(
            id="mem2",
            title="High Score",
            description="Test",
            content="Test",
            composite_score=0.9
        ),
        MemoryItem(
            id="mem3",
            title="Medium Score",
            description="Test",
            content="Test",
            composite_score=0.7
        )
    ]
    
    # Test ranking
    ranked = retriever.rank_by_relevance(memories, query="test")
    
    # Should be sorted by composite score (descending)
    assert ranked[0].composite_score == 0.9
    assert ranked[1].composite_score == 0.7
    assert ranked[2].composite_score == 0.5
    
    print("✓ Relevance ranking works correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running KnowledgeRetriever verification tests")
    print("=" * 60)
    
    try:
        test_initialization()
        test_retrieve_basic()
        test_domain_filtering()
        test_pattern_tag_filtering()
        test_error_pattern_retrieval()
        test_format_for_prompt()
        test_statistics()
        test_relevance_ranking()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
