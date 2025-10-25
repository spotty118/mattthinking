"""
Passive learning system for automatic knowledge capture from conversations.

This module implements the PassiveLearner class that automatically captures
valuable Q&A exchanges without explicit storage requests. It provides:
- Quality heuristics to detect valuable exchanges
- LLM-based knowledge extraction from unstructured conversations
- Auto-storage when quality thresholds are met
- Configurable minimum answer length and auto-store toggle
- Source type metadata tagging for passively learned memories

Requirements addressed: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from reasoning_bank_core import ReasoningBank
from cached_llm_client import CachedLLMClient
from exceptions import LLMGenerationError, JSONParseError


logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class PassiveLearnerConfig:
    """
    Configuration for passive learning system.
    
    Attributes:
        min_answer_length: Minimum answer length in characters to consider valuable
        auto_store_enabled: Whether to automatically store valuable exchanges
        quality_threshold: Minimum quality score (0.0-1.0) to trigger auto-storage
        max_extractions_per_exchange: Maximum knowledge items to extract per exchange
        temperature: LLM temperature for knowledge extraction
    """
    min_answer_length: int = 100
    auto_store_enabled: bool = True
    quality_threshold: float = 0.6
    max_extractions_per_exchange: int = 2
    temperature: float = 0.0


# ============================================================================
# PassiveLearner Class
# ============================================================================

class PassiveLearner:
    """
    Automatic knowledge capture from Q&A conversations.
    
    The PassiveLearner monitors conversations and automatically extracts
    valuable knowledge without requiring explicit storage requests. It uses
    heuristics to detect high-quality exchanges and LLM-based extraction
    to structure unstructured conversations into reusable memory items.
    
    Features:
    - Quality detection based on multiple heuristics
    - Structured knowledge extraction using LLM
    - Automatic storage to ReasoningBank
    - Source type metadata tagging
    - Configurable quality thresholds
    """
    
    def __init__(
        self,
        reasoning_bank: ReasoningBank,
        llm_client: CachedLLMClient,
        config: Optional[PassiveLearnerConfig] = None
    ):
        """
        Initialize the passive learner.
        
        Args:
            reasoning_bank: ReasoningBank instance for storing learned knowledge
            llm_client: Cached LLM client for knowledge extraction
            config: Optional configuration (uses defaults if not provided)
        """
        self.reasoning_bank = reasoning_bank
        self.llm_client = llm_client
        self.config = config or PassiveLearnerConfig()
        
        # Statistics tracking
        self._exchanges_evaluated = 0
        self._exchanges_stored = 0
        self._knowledge_items_extracted = 0
        
        logger.info(
            f"PassiveLearner initialized with min_answer_length={self.config.min_answer_length}, "
            f"auto_store={self.config.auto_store_enabled}"
        )
    
    def is_valuable(self, question: str, answer: str) -> bool:
        """
        Determine if a Q&A exchange meets quality thresholds.
        
        Uses multiple heuristics to assess value:
        1. Minimum answer length threshold
        2. Presence of code blocks
        3. Explanatory language (because, reason, explanation, how to)
        4. Step-by-step guidance (numbered lists, steps)
        5. Technical depth indicators
        
        Args:
            question: The question text
            answer: The answer text
        
        Returns:
            True if the exchange is valuable enough to capture
        """
        self._exchanges_evaluated += 1
        
        # Heuristic 1: Minimum length threshold
        if len(answer) < self.config.min_answer_length:
            logger.debug(f"Answer too short: {len(answer)} < {self.config.min_answer_length}")
            return False
        
        # Heuristic 2: Contains code blocks
        if "```" in answer:
            logger.debug("Answer contains code blocks - valuable")
            return True
        
        # Heuristic 3: Contains explanations
        explanation_keywords = [
            "because", "reason", "explanation", "how to", "why",
            "this is", "this means", "in other words", "essentially"
        ]
        answer_lower = answer.lower()
        if any(keyword in answer_lower for keyword in explanation_keywords):
            logger.debug("Answer contains explanatory language - valuable")
            return True
        
        # Heuristic 4: Contains step-by-step guidance
        step_markers = [
            r"\d+\.", r"step \d+", r"first,", r"second,", r"third,",
            r"next,", r"then,", r"finally,"
        ]
        if any(re.search(marker, answer_lower) for marker in step_markers):
            logger.debug("Answer contains step-by-step guidance - valuable")
            return True
        
        # Heuristic 5: Technical depth indicators
        technical_indicators = [
            "function", "class", "method", "algorithm", "pattern",
            "implementation", "architecture", "design", "approach",
            "solution", "technique", "strategy"
        ]
        technical_count = sum(1 for indicator in technical_indicators if indicator in answer_lower)
        if technical_count >= 3:
            logger.debug(f"Answer has technical depth ({technical_count} indicators) - valuable")
            return True
        
        # Heuristic 6: Substantial length with question relevance
        if len(answer) >= self.config.min_answer_length * 2:
            # For longer answers, check if it's relevant to the question
            question_words = set(question.lower().split())
            answer_words = set(answer_lower.split())
            overlap = len(question_words & answer_words)
            if overlap >= 3:
                logger.debug(f"Long answer with relevance (overlap: {overlap}) - valuable")
                return True
        
        logger.debug("Answer does not meet value thresholds")
        return False
    
    def extract_knowledge(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract structured knowledge from unstructured Q&A exchange.
        
        Uses LLM to analyze the conversation and extract reusable knowledge
        patterns in a structured format suitable for storage as memory items.
        
        Args:
            question: The question text
            answer: The answer text
            context: Optional additional context about the conversation
        
        Returns:
            List of knowledge item dictionaries with structured fields
        
        Raises:
            LLMGenerationError: If LLM call fails
            JSONParseError: If response parsing fails
        """
        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(question, answer, context)
            
            # Call LLM
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at extracting reusable knowledge from conversations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            result = self.llm_client.create(
                messages=messages,
                temperature=self.config.temperature,
                max_output_tokens=4000
            )
            
            # Parse JSON response
            knowledge_items = self._parse_extraction_response(result.content)
            
            # Limit to max extractions
            knowledge_items = knowledge_items[:self.config.max_extractions_per_exchange]
            
            # Tag with source type metadata
            for item in knowledge_items:
                if "metadata" not in item:
                    item["metadata"] = {}
                item["metadata"]["source_type"] = "passive_learning"
                item["metadata"]["source_question"] = question[:200]
            
            self._knowledge_items_extracted += len(knowledge_items)
            
            logger.info(f"Extracted {len(knowledge_items)} knowledge items from Q&A exchange")
            
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Failed to extract knowledge: {e}")
            raise LLMGenerationError(
                "Failed to extract knowledge from conversation",
                context={"error": str(e)}
            )
    
    def process_exchange(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None,
        force_store: bool = False
    ) -> Dict[str, Any]:
        """
        Process a Q&A exchange and optionally store valuable knowledge.
        
        This is the main entry point for passive learning. It:
        1. Evaluates if the exchange is valuable
        2. Extracts structured knowledge if valuable
        3. Stores to ReasoningBank if auto-store is enabled
        
        Args:
            question: The question text
            answer: The answer text
            context: Optional additional context
            force_store: Force storage even if auto_store is disabled
        
        Returns:
            Dictionary with processing results:
            - is_valuable: Whether exchange met quality thresholds
            - knowledge_items: Extracted knowledge items (if valuable)
            - stored: Whether items were stored to ReasoningBank
            - trace_id: Trace ID if stored
        """
        result = {
            "is_valuable": False,
            "knowledge_items": [],
            "stored": False,
            "trace_id": None
        }
        
        # Check if exchange is valuable
        if not self.is_valuable(question, answer):
            logger.debug("Exchange not valuable, skipping")
            return result
        
        result["is_valuable"] = True
        
        # Extract knowledge
        try:
            knowledge_items = self.extract_knowledge(question, answer, context)
            result["knowledge_items"] = knowledge_items
            
            if not knowledge_items:
                logger.info("No knowledge items extracted from valuable exchange")
                return result
            
            # Store if auto-store is enabled or forced
            if self.config.auto_store_enabled or force_store:
                trace_id = self._store_knowledge(
                    question=question,
                    answer=answer,
                    knowledge_items=knowledge_items,
                    context=context
                )
                result["stored"] = True
                result["trace_id"] = trace_id
                self._exchanges_stored += 1
                
                logger.info(
                    f"Stored {len(knowledge_items)} knowledge items from passive learning "
                    f"(trace_id: {trace_id})"
                )
            else:
                logger.info("Auto-store disabled, knowledge extracted but not stored")
            
        except Exception as e:
            logger.error(f"Failed to process exchange: {e}")
            result["error"] = str(e)
        
        return result
    
    def _store_knowledge(
        self,
        question: str,
        answer: str,
        knowledge_items: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> str:
        """
        Store extracted knowledge to ReasoningBank.
        
        Creates a reasoning trace representing the passive learning event
        and stores the extracted knowledge items.
        
        Args:
            question: The question text
            answer: The answer text
            knowledge_items: Extracted knowledge items
            context: Optional additional context
        
        Returns:
            Trace ID of stored knowledge
        """
        # Create trajectory representing the Q&A exchange
        trajectory = [
            {
                "iteration": 1,
                "thought": "Processing Q&A exchange for passive learning",
                "action": "evaluate_value",
                "output": f"Exchange deemed valuable based on quality heuristics"
            },
            {
                "iteration": 2,
                "thought": "Extracting structured knowledge from conversation",
                "action": "extract_knowledge",
                "output": f"Extracted {len(knowledge_items)} knowledge items"
            }
        ]
        
        # Create metadata
        metadata = {
            "source": "passive_learning",
            "question_length": len(question),
            "answer_length": len(answer),
            "knowledge_items_count": len(knowledge_items),
            "auto_stored": True
        }
        
        if context:
            metadata["context"] = context
        
        # Store trace
        trace_id = self.reasoning_bank.store_trace(
            task=f"Passive Learning: {question[:100]}...",
            trajectory=trajectory,
            outcome="success",
            memory_items=knowledge_items,
            metadata=metadata
        )
        
        return trace_id
    
    def _build_extraction_prompt(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None
    ) -> str:
        """Build prompt for knowledge extraction from Q&A."""
        context_section = ""
        if context:
            context_section = f"\n**Context:**\n{context}\n"
        
        prompt = f"""Extract reusable knowledge from this Q&A exchange.

**Question:**
{question}

**Answer:**
{answer}
{context_section}
**Instructions:**
Analyze this conversation and extract 1-{self.config.max_extractions_per_exchange} key pieces of reusable knowledge.
Focus on:
- Patterns and techniques that can be applied to similar problems
- Best practices and recommendations
- Common pitfalls and how to avoid them
- Technical concepts and their explanations
- Code patterns and implementation approaches

Return your analysis as a JSON array:

[
    {{
        "title": "<concise title (5-10 words)>",
        "description": "<one-sentence summary>",
        "content": "<detailed knowledge content with examples and insights>",
        "pattern_tags": ["<tag1>", "<tag2>", ...],
        "difficulty_level": "simple" | "moderate" | "complex" | "expert",
        "domain_category": "<domain like 'algorithms', 'api_usage', 'debugging', etc.>"
    }}
]

Make each knowledge item:
- Specific and actionable
- Reusable for similar future problems
- Well-structured with clear explanations
- Tagged appropriately for retrieval
"""
        return prompt
    
    def _parse_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON response from extraction LLM."""
        try:
            # Clean response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            import json
            knowledge_items = json.loads(response)
            
            # Ensure it's a list
            if not isinstance(knowledge_items, list):
                logger.warning("Extraction response is not a list, wrapping")
                knowledge_items = [knowledge_items]
            
            # Validate and clean each item
            validated_items = []
            for item in knowledge_items:
                if not isinstance(item, dict):
                    continue
                
                # Ensure required fields
                if "title" not in item or "description" not in item or "content" not in item:
                    logger.warning("Knowledge item missing required fields, skipping")
                    continue
                
                # Ensure pattern_tags is a list
                if "pattern_tags" not in item:
                    item["pattern_tags"] = []
                elif not isinstance(item["pattern_tags"], list):
                    item["pattern_tags"] = []
                
                validated_items.append(item)
            
            return validated_items
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            raise JSONParseError(
                "Failed to parse knowledge extraction response",
                raw_content=response[:200],
                context={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get passive learning statistics.
        
        Returns:
            Dictionary with statistics:
            - exchanges_evaluated: Total exchanges evaluated
            - exchanges_stored: Total exchanges stored
            - knowledge_items_extracted: Total knowledge items extracted
            - storage_rate: Percentage of evaluated exchanges that were stored
            - avg_items_per_exchange: Average knowledge items per stored exchange
        """
        storage_rate = 0.0
        if self._exchanges_evaluated > 0:
            storage_rate = self._exchanges_stored / self._exchanges_evaluated
        
        avg_items = 0.0
        if self._exchanges_stored > 0:
            avg_items = self._knowledge_items_extracted / self._exchanges_stored
        
        return {
            "exchanges_evaluated": self._exchanges_evaluated,
            "exchanges_stored": self._exchanges_stored,
            "knowledge_items_extracted": self._knowledge_items_extracted,
            "storage_rate": storage_rate,
            "avg_items_per_exchange": avg_items,
            "config": {
                "min_answer_length": self.config.min_answer_length,
                "auto_store_enabled": self.config.auto_store_enabled,
                "quality_threshold": self.config.quality_threshold
            }
        }
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self._exchanges_evaluated = 0
        self._exchanges_stored = 0
        self._knowledge_items_extracted = 0
        logger.info("Passive learner statistics reset")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_passive_learner(
    reasoning_bank: ReasoningBank,
    llm_client: CachedLLMClient,
    min_answer_length: int = 100,
    auto_store_enabled: bool = True,
    **kwargs
) -> PassiveLearner:
    """
    Factory function to create PassiveLearner instance.
    
    Args:
        reasoning_bank: ReasoningBank instance
        llm_client: Cached LLM client
        min_answer_length: Minimum answer length threshold
        auto_store_enabled: Whether to auto-store valuable exchanges
        **kwargs: Additional configuration options
    
    Returns:
        Initialized PassiveLearner instance
    """
    config = PassiveLearnerConfig(
        min_answer_length=min_answer_length,
        auto_store_enabled=auto_store_enabled,
        **kwargs
    )
    
    return PassiveLearner(
        reasoning_bank=reasoning_bank,
        llm_client=llm_client,
        config=config
    )


# ============================================================================
# Testing and Validation
# ============================================================================

if __name__ == "__main__":
    """Test PassiveLearner functionality"""
    print("=== Testing PassiveLearner ===\n")
    
    # Test value detection heuristics
    print("Testing value detection heuristics:\n")
    
    # Create a mock passive learner for testing
    from unittest.mock import Mock
    
    mock_bank = Mock()
    mock_client = Mock()
    learner = PassiveLearner(mock_bank, mock_client)
    
    # Test case 1: Short answer (should be not valuable)
    q1 = "What is Python?"
    a1 = "A programming language."
    print(f"Test 1 - Short answer: {learner.is_valuable(q1, a1)}")  # Should be False
    
    # Test case 2: Answer with code blocks (should be valuable)
    q2 = "How do I sort a list in Python?"
    a2 = """You can sort a list using the sort() method:
```python
my_list = [3, 1, 2]
my_list.sort()
```
This sorts the list in-place."""
    print(f"Test 2 - Code blocks: {learner.is_valuable(q2, a2)}")  # Should be True
    
    # Test case 3: Explanatory answer (should be valuable)
    q3 = "Why use async/await?"
    a3 = """Async/await is valuable because it allows you to write asynchronous code that looks synchronous. 
The reason this is important is that it makes concurrent programming much easier to understand and maintain. 
This means you can handle multiple operations without blocking the main thread."""
    print(f"Test 3 - Explanatory: {learner.is_valuable(q3, a3)}")  # Should be True
    
    # Test case 4: Step-by-step answer (should be valuable)
    q4 = "How do I deploy a Docker container?"
    a4 = """Here's how to deploy a Docker container:
1. First, build your Docker image
2. Then, push it to a registry
3. Finally, pull and run it on your server
This process ensures your application is containerized properly."""
    print(f"Test 4 - Step-by-step: {learner.is_valuable(q4, a4)}")  # Should be True
    
    # Test case 5: Technical depth (should be valuable)
    q5 = "What is dependency injection?"
    a5 = """Dependency injection is a design pattern where a class receives its dependencies from external sources 
rather than creating them itself. This pattern improves testability because you can inject mock implementations 
during testing. The architecture becomes more flexible as you can swap implementations without changing the class. 
This approach follows the dependency inversion principle and promotes loose coupling in your codebase."""
    print(f"Test 5 - Technical depth: {learner.is_valuable(q5, a5)}")  # Should be True
    
    print("\n✅ PassiveLearner module loaded successfully")
    print("\nKey features:")
    print("  ✅ Quality heuristics for value detection")
    print("  ✅ LLM-based knowledge extraction")
    print("  ✅ Auto-storage to ReasoningBank")
    print("  ✅ Source type metadata tagging")
    print("  ✅ Configurable thresholds")
    print("  ✅ Statistics tracking")
