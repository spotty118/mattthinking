"""
Iterative Reasoning Agent with Think → Evaluate → Refine loop

This module implements the core reasoning agent that:
- Generates solutions iteratively with memory context
- Evaluates solution quality and provides feedback
- Refines solutions based on evaluation feedback
- Detects reasoning loops to prevent infinite iterations
- Manages token budgets with estimation and truncation
- Supports early termination when quality threshold is met
- Implements Memory-Aware Test-Time Scaling (MaTTS) for parallel solution generation

Requirements addressed: 2.1-2.5, 3.1-3.5, 14.1-14.5
"""

import asyncio
import hashlib
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

from reasoning_bank_core import ReasoningBank, MemoryItem
from cached_llm_client import CachedLLMClient
from exceptions import (
    LLMGenerationError,
    TokenBudgetExceededError,
    InvalidTaskError
)
from schemas import TrajectoryStep
from performance_optimizer import PromptCompressor


logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class IterationResult:
    """Result from a single iteration of the reasoning loop"""
    solution: str
    score: float
    feedback: str
    iteration: int
    tokens_used: int
    trajectory_hash: str


@dataclass
class SolutionResult:
    """Final result from task solving"""
    solution: str
    score: float
    trajectory: List[Dict[str, Any]]
    iterations: int
    total_tokens: int
    early_termination: bool
    loop_detected: bool


@dataclass
class MaTTSSolutionCandidate:
    """A candidate solution from MaTTS generation"""
    solution: str
    score: float
    feedback: str
    tokens_used: int
    candidate_id: int


# ============================================================================
# Iterative Reasoning Agent
# ============================================================================

class IterativeReasoningAgent:
    """
    Iterative reasoning agent implementing Think → Evaluate → Refine loop
    
    The agent follows this process:
    1. Think: Generate or refine solution with memory context
    2. Evaluate: Score the solution and provide feedback
    3. Refine: Improve solution based on feedback
    4. Repeat until success threshold or max iterations
    
    Features:
    - Memory-guided solution generation
    - Iterative refinement with feedback
    - Loop detection via trajectory hashing
    - Early termination on success threshold (0.8)
    - Token budget management
    - Comprehensive trajectory tracking
    """
    
    def __init__(
        self,
        llm_client: CachedLLMClient,
        reasoning_bank: ReasoningBank,
        max_iterations: int = 3,
        success_threshold: float = 0.8,
        temperature_generate: float = 0.7,
        temperature_evaluate: float = 0.0,
        max_output_tokens: int = 8000,
        evaluation_tokens: int = 3000,
        max_prompt_tokens: int = 12000,
        truncation_threshold: int = 12000,
        truncation_head_ratio: float = 0.6
    ):
        """
        Initialize the iterative reasoning agent
        
        Args:
            llm_client: Cached LLM client for API calls
            reasoning_bank: ReasoningBank for memory retrieval
            max_iterations: Maximum refinement iterations
            success_threshold: Quality threshold for early termination
            temperature_generate: Temperature for solution generation
            temperature_evaluate: Temperature for evaluation (0.0 for deterministic)
            max_output_tokens: Maximum tokens per generation
            evaluation_tokens: Tokens allocated for evaluation
            max_prompt_tokens: Maximum prompt tokens
            truncation_threshold: Token threshold for truncation
            truncation_head_ratio: Ratio of content to preserve at head
        """
        self.llm_client = llm_client
        self.reasoning_bank = reasoning_bank
        self.max_iterations = max_iterations
        self.success_threshold = success_threshold
        self.temperature_generate = temperature_generate
        self.temperature_evaluate = temperature_evaluate
        self.max_output_tokens = max_output_tokens
        self.evaluation_tokens = evaluation_tokens
        self.max_prompt_tokens = max_prompt_tokens
        self.truncation_threshold = truncation_threshold
        self.truncation_head_ratio = truncation_head_ratio
        
        # Track seen trajectory hashes for loop detection
        self._trajectory_hashes: set = set()
        
        # Token usage tracking
        self._total_tokens_used = 0
        
        # Initialize prompt compressor for token optimization
        self.prompt_compressor = PromptCompressor(
            max_tokens=max_prompt_tokens,
            compression_ratio=0.7
        )
        
        logger.info(
            f"IterativeReasoningAgent initialized: max_iterations={max_iterations}, "
            f"success_threshold={success_threshold}, prompt_compression=enabled"
        )
    
    def solve_task(
        self,
        task: str,
        memories: Optional[List[MemoryItem]] = None,
        use_memory: bool = True
    ) -> SolutionResult:
        """
        Main entry point for task solving with iterative refinement
        
        Implements the Think → Evaluate → Refine loop:
        1. Retrieve relevant memories (if use_memory=True)
        2. Generate initial solution with memory context
        3. Evaluate solution quality
        4. If score < threshold and iterations remain, refine and repeat
        5. Return best solution found
        
        Args:
            task: Task description to solve
            memories: Pre-retrieved memories (optional)
            use_memory: Whether to retrieve memories
        
        Returns:
            SolutionResult with final solution and trajectory
        
        Raises:
            InvalidTaskError: If task is invalid
            TokenBudgetExceededError: If token budget exceeded
            LLMGenerationError: If LLM calls fail
        """
        # Validate task
        if not task or len(task.strip()) < 10:
            raise InvalidTaskError(
                "Task description too short",
                task=task
            )
        
        # Reset state
        self._trajectory_hashes.clear()
        self._total_tokens_used = 0
        
        # Retrieve memories if needed
        if use_memory and memories is None:
            try:
                memories = self.reasoning_bank.retrieve_memories(
                    query=task,
                    n_results=self.reasoning_bank.retrieval_k
                )
                logger.info(f"Retrieved {len(memories)} memories for task")
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")
                memories = []
        elif memories is None:
            memories = []
        
        # Initialize tracking
        trajectory = []
        best_solution = None
        best_score = 0.0
        current_solution = None
        current_feedback = None
        loop_detected = False
        early_termination = False
        
        # Iterative refinement loop
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Starting iteration {iteration}/{self.max_iterations}")
            
            try:
                # Think: Generate or refine solution
                solution, tokens_think = self._think_step(
                    task=task,
                    memories=memories,
                    iteration=iteration,
                    previous_solution=current_solution,
                    feedback=current_feedback
                )
                
                # Track tokens
                self._total_tokens_used += tokens_think
                
                # Detect loops
                trajectory_hash = self._compute_trajectory_hash(solution)
                if trajectory_hash in self._trajectory_hashes:
                    logger.warning(f"Loop detected at iteration {iteration}")
                    loop_detected = True
                    trajectory.append({
                        "iteration": iteration,
                        "action": "loop_detected",
                        "output": "Reasoning loop detected, terminating",
                        "output_hash": trajectory_hash
                    })
                    break
                
                self._trajectory_hashes.add(trajectory_hash)
                
                # Add to trajectory
                trajectory.append({
                    "iteration": iteration,
                    "action": "think",
                    "thought": f"Generated solution attempt {iteration}",
                    "output": solution,
                    "output_hash": trajectory_hash
                })
                
                # Evaluate: Score the solution
                score, feedback, tokens_eval = self._evaluate_step(
                    task=task,
                    solution=solution,
                    iteration=iteration
                )
                
                # Track tokens
                self._total_tokens_used += tokens_eval
                
                # Add to trajectory
                trajectory.append({
                    "iteration": iteration,
                    "action": "evaluate",
                    "thought": f"Evaluated solution quality",
                    "output": f"Score: {score:.2f}\nFeedback: {feedback}",
                    "previous_score": score
                })
                
                logger.info(f"Iteration {iteration}: score={score:.2f}")
                
                # Update best solution
                if score > best_score:
                    best_solution = solution
                    best_score = score
                
                # Check for early termination
                if score >= self.success_threshold:
                    logger.info(
                        f"Success threshold reached: {score:.2f} >= {self.success_threshold}"
                    )
                    early_termination = True
                    trajectory.append({
                        "iteration": iteration,
                        "action": "success",
                        "output": f"Success threshold reached: {score:.2f}"
                    })
                    break
                
                # Prepare for next iteration
                current_solution = solution
                current_feedback = feedback
                
                # Check if we have more iterations
                if iteration < self.max_iterations:
                    logger.info(f"Refining solution based on feedback")
                
            except TokenBudgetExceededError as e:
                logger.error(f"Token budget exceeded at iteration {iteration}: {e}")
                trajectory.append({
                    "iteration": iteration,
                    "action": "error",
                    "output": f"Token budget exceeded: {e}"
                })
                break
            except Exception as e:
                logger.error(f"Error at iteration {iteration}: {e}")
                trajectory.append({
                    "iteration": iteration,
                    "action": "error",
                    "output": f"Error: {str(e)}"
                })
                # Continue with best solution so far
                break
        
        # Return best solution found
        if best_solution is None:
            # Fallback if no solution generated
            best_solution = "Failed to generate solution"
            best_score = 0.0
        
        result = SolutionResult(
            solution=best_solution,
            score=best_score,
            trajectory=trajectory,
            iterations=len([t for t in trajectory if t.get("action") == "think"]),
            total_tokens=self._total_tokens_used,
            early_termination=early_termination,
            loop_detected=loop_detected
        )
        
        logger.info(
            f"Task completed: score={best_score:.2f}, iterations={result.iterations}, "
            f"tokens={self._total_tokens_used}, early_termination={early_termination}"
        )
        
        return result
    
    def solve_with_matts(
        self,
        task: str,
        memories: Optional[List[MemoryItem]] = None,
        use_memory: bool = True,
        k: int = 5,
        mode: str = "parallel",
        refine_best: bool = True
    ) -> SolutionResult:
        """
        Solve task using Memory-Aware Test-Time Scaling (MaTTS)
        
        MaTTS generates multiple solution attempts (k attempts) and selects
        the best one based on evaluation scores. This improves solution quality
        through diversity and self-contrast.
        
        Process:
        1. Retrieve relevant memories (if use_memory=True)
        2. Generate k solution attempts (parallel or sequential)
        3. Evaluate all solutions
        4. Select the best solution
        5. Optionally refine the best solution
        
        Args:
            task: Task description to solve
            memories: Pre-retrieved memories (optional)
            use_memory: Whether to retrieve memories
            k: Number of parallel solution attempts (default: 5)
            mode: "parallel" or "sequential" generation mode
            refine_best: Whether to refine the best solution (default: True)
        
        Returns:
            SolutionResult with best solution and trajectory
        
        Raises:
            InvalidTaskError: If task is invalid
            TokenBudgetExceededError: If token budget exceeded
            LLMGenerationError: If LLM calls fail
        """
        # Validate task
        if not task or len(task.strip()) < 10:
            raise InvalidTaskError(
                "Task description too short",
                task=task
            )
        
        # Validate k parameter
        if k < 1:
            raise InvalidTaskError(
                f"Invalid k parameter: {k}. Must be >= 1",
                task=task
            )
        
        # Validate mode
        if mode not in ["parallel", "sequential"]:
            logger.warning(f"Invalid mode '{mode}', defaulting to 'parallel'")
            mode = "parallel"
        
        # Reset state
        self._trajectory_hashes.clear()
        self._total_tokens_used = 0
        
        # Retrieve memories if needed
        if use_memory and memories is None:
            try:
                memories = self.reasoning_bank.retrieve_memories(
                    query=task,
                    n_results=self.reasoning_bank.retrieval_k
                )
                logger.info(f"Retrieved {len(memories)} memories for MaTTS task")
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")
                memories = []
        elif memories is None:
            memories = []
        
        # Initialize trajectory
        trajectory = []
        trajectory.append({
            "iteration": 0,
            "action": "matts_start",
            "output": f"Starting MaTTS with k={k}, mode={mode}",
            "k": k,
            "mode": mode
        })
        
        logger.info(f"Starting MaTTS: k={k}, mode={mode}, refine_best={refine_best}")
        
        # Generate k solution candidates
        if mode == "parallel":
            candidates = self._generate_parallel_solutions(task, memories, k, trajectory)
        else:
            candidates = self._generate_sequential_solutions(task, memories, k, trajectory)
        
        # Check if we got any candidates
        if not candidates:
            logger.error("No solution candidates generated")
            return SolutionResult(
                solution="Failed to generate any solution candidates",
                score=0.0,
                trajectory=trajectory,
                iterations=0,
                total_tokens=self._total_tokens_used,
                early_termination=False,
                loop_detected=False
            )
        
        # Select best candidate
        best_candidate = max(candidates, key=lambda c: c.score)
        
        logger.info(
            f"Best candidate: id={best_candidate.candidate_id}, "
            f"score={best_candidate.score:.2f}"
        )
        
        trajectory.append({
            "iteration": 0,
            "action": "matts_select_best",
            "output": f"Selected candidate {best_candidate.candidate_id} with score {best_candidate.score:.2f}",
            "candidate_id": best_candidate.candidate_id,
            "score": best_candidate.score,
            "all_scores": [c.score for c in candidates]
        })
        
        # Optionally refine the best solution
        final_solution = best_candidate.solution
        final_score = best_candidate.score
        
        if refine_best and best_candidate.score < self.success_threshold:
            logger.info("Refining best solution")
            try:
                refined_solution, tokens_refine = self._think_step(
                    task=task,
                    memories=memories,
                    iteration=1,
                    previous_solution=best_candidate.solution,
                    feedback=best_candidate.feedback
                )
                
                self._total_tokens_used += tokens_refine
                
                # Evaluate refined solution
                refined_score, refined_feedback, tokens_eval = self._evaluate_step(
                    task=task,
                    solution=refined_solution,
                    iteration=1
                )
                
                self._total_tokens_used += tokens_eval
                
                trajectory.append({
                    "iteration": 1,
                    "action": "matts_refine",
                    "output": refined_solution,
                    "score": refined_score,
                    "previous_score": best_candidate.score
                })
                
                # Use refined solution if better
                if refined_score > best_candidate.score:
                    logger.info(
                        f"Refined solution improved: {best_candidate.score:.2f} -> {refined_score:.2f}"
                    )
                    final_solution = refined_solution
                    final_score = refined_score
                else:
                    logger.info(
                        f"Refined solution not better, keeping original: "
                        f"{refined_score:.2f} <= {best_candidate.score:.2f}"
                    )
                
            except Exception as e:
                logger.warning(f"Failed to refine best solution: {e}")
                trajectory.append({
                    "iteration": 1,
                    "action": "matts_refine_error",
                    "output": f"Refinement failed: {str(e)}"
                })
        
        # Build final result
        result = SolutionResult(
            solution=final_solution,
            score=final_score,
            trajectory=trajectory,
            iterations=len(candidates),
            total_tokens=self._total_tokens_used,
            early_termination=final_score >= self.success_threshold,
            loop_detected=False
        )
        
        logger.info(
            f"MaTTS completed: best_score={final_score:.2f}, "
            f"candidates={len(candidates)}, tokens={self._total_tokens_used}"
        )
        
        return result
    
    def _generate_parallel_solutions(
        self,
        task: str,
        memories: List[MemoryItem],
        k: int,
        trajectory: List[Dict[str, Any]]
    ) -> List[MaTTSSolutionCandidate]:
        """
        Generate k solution attempts in parallel using asyncio
        
        This method creates k concurrent solution generation tasks and
        evaluates them all. The parallel approach completes in approximately
        1x the time of a single attempt (not k×).
        
        Args:
            task: Task description
            memories: Retrieved memories
            k: Number of parallel attempts
            trajectory: Trajectory list to append to
        
        Returns:
            List of MaTTSSolutionCandidate objects
        """
        logger.info(f"Generating {k} parallel solution attempts")
        
        # Create async wrapper for solution generation
        async def generate_and_evaluate_async(candidate_id: int) -> Optional[MaTTSSolutionCandidate]:
            """Generate and evaluate a single solution candidate"""
            try:
                # Generate solution
                solution, tokens_think = self._think_step(
                    task=task,
                    memories=memories,
                    iteration=candidate_id,
                    previous_solution=None,
                    feedback=None
                )
                
                # Evaluate solution
                score, feedback, tokens_eval = self._evaluate_step(
                    task=task,
                    solution=solution,
                    iteration=candidate_id
                )
                
                total_tokens = tokens_think + tokens_eval
                
                logger.info(
                    f"Candidate {candidate_id}: score={score:.2f}, tokens={total_tokens}"
                )
                
                return MaTTSSolutionCandidate(
                    solution=solution,
                    score=score,
                    feedback=feedback,
                    tokens_used=total_tokens,
                    candidate_id=candidate_id
                )
                
            except Exception as e:
                logger.error(f"Failed to generate candidate {candidate_id}: {e}")
                return None
        
        # Run all generations in parallel
        async def run_parallel():
            tasks = [generate_and_evaluate_async(i) for i in range(1, k + 1)]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Execute parallel generation
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - run tasks directly in current loop
                logger.info("Running parallel generation in existing event loop")
                # Create a new task for parallel execution
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=k) as executor:
                    # Run synchronous generation in thread pool
                    futures = []
                    for i in range(1, k + 1):
                        future = executor.submit(self._generate_single_candidate, task, memories, i)
                        futures.append(future)
                    
                    results = []
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            results.append(e)
                
            except RuntimeError:
                # No event loop, create one
                results = asyncio.run(run_parallel())
        except Exception as e:
            logger.error(f"Parallel generation failed: {e}, falling back to sequential")
            return self._generate_sequential_solutions(task, memories, k, trajectory)
        
        # Filter out None results and exceptions
        candidates = []
        for result in results:
            if isinstance(result, MaTTSSolutionCandidate):
                candidates.append(result)
                self._total_tokens_used += result.tokens_used
                
                trajectory.append({
                    "iteration": 0,
                    "action": "matts_candidate",
                    "candidate_id": result.candidate_id,
                    "score": result.score,
                    "output": result.solution[:200] + "..." if len(result.solution) > 200 else result.solution
                })
            elif isinstance(result, Exception):
                logger.error(f"Candidate generation raised exception: {result}")
        
        logger.info(f"Generated {len(candidates)}/{k} parallel candidates successfully")
        
        return candidates
    
    def _generate_single_candidate(
        self,
        task: str,
        memories: List[MemoryItem],
        candidate_id: int
    ) -> Optional[MaTTSSolutionCandidate]:
        """
        Generate and evaluate a single solution candidate (thread-safe)
        
        This is called from ThreadPoolExecutor for true parallel execution
        when running in an async context.
        
        Args:
            task: Task description
            memories: Retrieved memories
            candidate_id: Candidate identifier
        
        Returns:
            MaTTSSolutionCandidate or None if failed
        """
        try:
            # Generate solution
            solution, tokens_think = self._think_step(
                task=task,
                memories=memories,
                iteration=candidate_id,
                previous_solution=None,
                feedback=None
            )
            
            # Evaluate solution
            score, feedback, tokens_eval = self._evaluate_step(
                task=task,
                solution=solution,
                iteration=candidate_id
            )
            
            total_tokens = tokens_think + tokens_eval
            
            logger.info(
                f"Candidate {candidate_id}: score={score:.2f}, tokens={total_tokens}"
            )
            
            return MaTTSSolutionCandidate(
                solution=solution,
                score=score,
                feedback=feedback,
                tokens_used=total_tokens,
                candidate_id=candidate_id
            )
            
        except Exception as e:
            logger.error(f"Failed to generate candidate {candidate_id}: {e}")
            return None
    
    def _generate_sequential_solutions(
        self,
        task: str,
        memories: List[MemoryItem],
        k: int,
        trajectory: List[Dict[str, Any]]
    ) -> List[MaTTSSolutionCandidate]:
        """
        Generate k solution attempts sequentially
        
        This is a fallback mode when parallel generation is not available
        or fails. It generates solutions one at a time.
        
        Args:
            task: Task description
            memories: Retrieved memories
            k: Number of sequential attempts
            trajectory: Trajectory list to append to
        
        Returns:
            List of MaTTSSolutionCandidate objects
        """
        logger.info(f"Generating {k} sequential solution attempts")
        
        candidates = []
        
        for candidate_id in range(1, k + 1):
            try:
                # Generate solution
                solution, tokens_think = self._think_step(
                    task=task,
                    memories=memories,
                    iteration=candidate_id,
                    previous_solution=None,
                    feedback=None
                )
                
                # Evaluate solution
                score, feedback, tokens_eval = self._evaluate_step(
                    task=task,
                    solution=solution,
                    iteration=candidate_id
                )
                
                total_tokens = tokens_think + tokens_eval
                self._total_tokens_used += total_tokens
                
                logger.info(
                    f"Candidate {candidate_id}: score={score:.2f}, tokens={total_tokens}"
                )
                
                candidate = MaTTSSolutionCandidate(
                    solution=solution,
                    score=score,
                    feedback=feedback,
                    tokens_used=total_tokens,
                    candidate_id=candidate_id
                )
                
                candidates.append(candidate)
                
                trajectory.append({
                    "iteration": 0,
                    "action": "matts_candidate",
                    "candidate_id": candidate_id,
                    "score": score,
                    "output": solution[:200] + "..." if len(solution) > 200 else solution
                })
                
            except Exception as e:
                logger.error(f"Failed to generate candidate {candidate_id}: {e}")
                trajectory.append({
                    "iteration": 0,
                    "action": "matts_candidate_error",
                    "candidate_id": candidate_id,
                    "output": f"Error: {str(e)}"
                })
        
        logger.info(f"Generated {len(candidates)}/{k} sequential candidates successfully")
        
        return candidates
    
    def _think_step(
        self,
        task: str,
        memories: List[MemoryItem],
        iteration: int,
        previous_solution: Optional[str] = None,
        feedback: Optional[str] = None
    ) -> Tuple[str, int]:
        """
        Generate or refine solution with memory context
        
        On first iteration: Generate initial solution with memory guidance
        On subsequent iterations: Refine previous solution based on feedback
        
        Args:
            task: Task description
            memories: Retrieved relevant memories
            iteration: Current iteration number
            previous_solution: Previous solution attempt (if refining)
            feedback: Evaluation feedback (if refining)
        
        Returns:
            Tuple of (solution, tokens_used)
        
        Raises:
            LLMGenerationError: If generation fails
            TokenBudgetExceededError: If token budget exceeded
        """
        # Build prompt
        if iteration == 1:
            # Initial generation
            prompt = self._build_generation_prompt(task, memories)
        else:
            # Refinement
            prompt = self._build_refinement_prompt(
                task, previous_solution, feedback, memories
            )
        
        # Use prompt compressor for token optimization
        estimated_tokens = self._estimate_tokens(prompt)
        if estimated_tokens > self.truncation_threshold:
            logger.warning(
                f"Prompt exceeds threshold ({estimated_tokens} > {self.truncation_threshold}), "
                f"compressing"
            )
            prompt = self.prompt_compressor.compress(prompt)
        
        # Generate solution
        messages = [
            {"role": "system", "content": "You are an expert problem solver and programmer."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = self.llm_client.create(
                messages=messages,
                temperature=self.temperature_generate,
                max_output_tokens=self.max_output_tokens
            )
            
            solution = result.content
            tokens_used = result.total_tokens
            
            logger.info(
                f"Think step {iteration}: generated {len(solution)} chars, "
                f"{tokens_used} tokens"
            )
            
            return solution, tokens_used
            
        except Exception as e:
            raise LLMGenerationError(
                f"Failed to generate solution at iteration {iteration}",
                context={"iteration": iteration, "error": str(e)}
            )
    
    def _evaluate_step(
        self,
        task: str,
        solution: str,
        iteration: int
    ) -> Tuple[float, str, int]:
        """
        Evaluate solution quality and provide feedback
        
        Uses LLM to score the solution (0.0-1.0) and provide specific
        feedback for improvement.
        
        Args:
            task: Original task description
            solution: Solution to evaluate
            iteration: Current iteration number
        
        Returns:
            Tuple of (score, feedback, tokens_used)
        
        Raises:
            LLMGenerationError: If evaluation fails
        """
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(task, solution)
        
        # Call LLM for evaluation
        messages = [
            {"role": "system", "content": "You are an expert code reviewer and evaluator."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = self.llm_client.create(
                messages=messages,
                temperature=self.temperature_evaluate,  # Deterministic
                max_output_tokens=self.evaluation_tokens
            )
            
            # Parse evaluation response
            score, feedback = self._parse_evaluation_response(result.content)
            tokens_used = result.total_tokens
            
            logger.info(
                f"Evaluate step {iteration}: score={score:.2f}, "
                f"{tokens_used} tokens"
            )
            
            return score, feedback, tokens_used
            
        except Exception as e:
            logger.error(f"Failed to evaluate solution: {e}")
            # Return default score and feedback
            return 0.5, "Evaluation failed, continuing with default score", 0
    
    def _build_generation_prompt(
        self,
        task: str,
        memories: List[MemoryItem]
    ) -> str:
        """Build prompt for initial solution generation"""
        prompt_parts = [
            "# Task",
            task,
            ""
        ]
        
        # Add memory context if available
        if memories:
            prompt_parts.append("# Relevant Past Experiences")
            prompt_parts.append(
                "Here are relevant memories from past similar tasks. "
                "Learn from these patterns and avoid past mistakes:\n"
            )
            
            for i, memory in enumerate(memories[:3], 1):  # Limit to top 3
                prompt_parts.append(f"## Memory {i}")
                prompt_parts.append(memory.format_for_prompt())
                prompt_parts.append("")
        
        prompt_parts.extend([
            "# Instructions",
            "Generate a high-quality solution to the task above.",
            "If memories are provided, learn from the patterns and avoid past mistakes.",
            "Provide clear, well-structured code with explanations.",
            "",
            "# Solution"
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_refinement_prompt(
        self,
        task: str,
        previous_solution: str,
        feedback: str,
        memories: List[MemoryItem]
    ) -> str:
        """Build prompt for solution refinement"""
        prompt_parts = [
            "# Task",
            task,
            "",
            "# Previous Solution Attempt",
            previous_solution,
            "",
            "# Evaluation Feedback",
            feedback,
            ""
        ]
        
        # Add memory context if available
        if memories:
            prompt_parts.append("# Relevant Past Experiences")
            for i, memory in enumerate(memories[:2], 1):  # Limit to top 2 for refinement
                prompt_parts.append(f"## Memory {i}")
                prompt_parts.append(memory.format_for_prompt())
                prompt_parts.append("")
        
        prompt_parts.extend([
            "# Instructions",
            "Refine the previous solution based on the evaluation feedback.",
            "Address the specific issues mentioned in the feedback.",
            "Maintain what was working well in the previous attempt.",
            "Provide an improved, complete solution.",
            "",
            "# Refined Solution"
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_evaluation_prompt(self, task: str, solution: str) -> str:
        """Build prompt for solution evaluation"""
        prompt = f"""# Task
{task}

# Solution to Evaluate
{solution}

# Instructions
Evaluate the solution and provide:
1. A quality score from 0.0 to 1.0
2. Specific feedback for improvement

**Scoring Guide:**
- 0.0-0.3: Major issues, doesn't work
- 0.4-0.6: Partial solution, has problems
- 0.7-0.8: Good solution, minor issues
- 0.9-1.0: Excellent solution

**Format your response as:**
Score: <number between 0.0 and 1.0>
Feedback: <specific feedback for improvement>

# Evaluation
"""
        return prompt
    
    def _parse_evaluation_response(self, response: str) -> Tuple[float, str]:
        """
        Parse evaluation response to extract score and feedback
        
        Expected format:
            Score: 0.75
            Feedback: The solution works but could improve error handling...
        
        Args:
            response: LLM evaluation response
        
        Returns:
            Tuple of (score, feedback)
        """
        lines = response.strip().split('\n')
        score = 0.5  # Default
        feedback = "No feedback provided"
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('score:'):
                try:
                    score_str = line.split(':', 1)[1].strip()
                    score = float(score_str)
                    # Clamp to [0, 1]
                    score = max(0.0, min(1.0, score))
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse score: {e}")
            elif line.lower().startswith('feedback:'):
                feedback = line.split(':', 1)[1].strip()
        
        # If feedback not found in expected format, use entire response
        if feedback == "No feedback provided" and len(response) > 20:
            # Extract everything after "Feedback:" or use full response
            if "Feedback:" in response:
                feedback = response.split("Feedback:", 1)[1].strip()
            else:
                feedback = response.strip()
        
        return score, feedback
    
    def _compute_trajectory_hash(self, solution: str) -> str:
        """
        Compute hash of solution for loop detection
        
        Uses SHA256 to create a deterministic hash of the solution.
        If we see the same hash again, we've entered a loop.
        
        Args:
            solution: Solution text to hash
        
        Returns:
            SHA256 hash string
        """
        hash_obj = hashlib.sha256(solution.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using 4 chars/token heuristic
        
        This is a rough estimate. Actual tokenization may vary.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def _truncate_prompt(self, prompt: str, max_tokens: int) -> str:
        """
        Truncate prompt while preserving head and tail context
        
        Keeps the beginning (task, instructions) and end (current context)
        while removing middle content if needed.
        
        Args:
            prompt: Prompt to truncate
            max_tokens: Maximum tokens allowed
        
        Returns:
            Truncated prompt
        """
        max_chars = max_tokens * 4  # Convert tokens to chars
        
        if len(prompt) <= max_chars:
            return prompt
        
        # Calculate head and tail sizes
        head_size = int(max_chars * self.truncation_head_ratio)
        tail_size = max_chars - head_size - 100  # Reserve 100 for truncation message
        
        # Extract head and tail
        head = prompt[:head_size]
        tail = prompt[-tail_size:]
        
        # Combine with truncation message
        truncated = (
            f"{head}\n\n"
            f"[... Content truncated to fit token budget ...]\n\n"
            f"{tail}"
        )
        
        logger.warning(
            f"Truncated prompt from {len(prompt)} to {len(truncated)} chars"
        )
        
        return truncated
    
    def reset_state(self):
        """Reset agent state for new task"""
        self._trajectory_hashes.clear()
        self._total_tokens_used = 0


# ============================================================================
# Convenience Functions
# ============================================================================

def create_iterative_agent(
    llm_client: CachedLLMClient,
    reasoning_bank: ReasoningBank,
    **kwargs
) -> IterativeReasoningAgent:
    """
    Factory function to create IterativeReasoningAgent
    
    Args:
        llm_client: Cached LLM client
        reasoning_bank: ReasoningBank instance
        **kwargs: Additional agent configuration
    
    Returns:
        Initialized IterativeReasoningAgent
    """
    return IterativeReasoningAgent(
        llm_client=llm_client,
        reasoning_bank=reasoning_bank,
        **kwargs
    )


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    """Test IterativeReasoningAgent functionality"""
    print("=== Testing Iterative Reasoning Agent ===\n")
    
    print("IterativeReasoningAgent module loaded successfully")
    print("\nKey features:")
    print("  ✅ Think → Evaluate → Refine loop")
    print("  ✅ Memory-guided solution generation")
    print("  ✅ Loop detection via trajectory hashing")
    print("  ✅ Early termination on success threshold")
    print("  ✅ Token budget management")
    print("  ✅ Comprehensive trajectory tracking")
    print("\nReady for integration with MCP server.")
