# Product Overview

ReasoningBank MCP Server is a self-evolving memory system for LLM agents that learns from both successes and failures to reduce hallucinations and improve problem-solving over time.

## Core Concept

Based on Google's ReasoningBank paper, the system implements an intelligent reasoning loop: Think → Evaluate → Refine → Store Learnings → Apply to Future Tasks. It uses vector-based semantic memory retrieval to help AI agents learn from past experiences and avoid repeating mistakes.

## Key Features

- **Iterative Reasoning**: Multi-iteration refinement loop for high-quality solutions
- **Memory-Aware Test-Time Scaling (MaTTS)**: Generate multiple parallel or sequential solution attempts and select the best one
- **Error Context Learning**: Automatically captures and learns from failures to prevent repeating bugs
- **Hallucination Prevention**: Retrieves relevant error warnings from past failures
- **Passive Learning**: Automatically captures valuable Q&A exchanges without explicit storage requests
- **Workspace Isolation**: Separate memory banks for different projects/users
- **MCP Protocol**: Standard Model Context Protocol for easy integration with LLM agents

## Architecture

- **ReasoningBank Core**: Memory management with ChromaDB or Supabase storage
- **Iterative Agent**: Implements the reasoning loop with evaluation and refinement
- **MCP Server**: Exposes functionality as standardized tools for LLM agents
- **Storage Adapters**: Pluggable backends (ChromaDB for local, Supabase for cloud)

## Use Cases

- AI coding assistants that learn from past solutions
- Debugging systems that remember common pitfalls
- Knowledge bases that evolve through conversation
- Multi-tenant systems requiring memory isolation
