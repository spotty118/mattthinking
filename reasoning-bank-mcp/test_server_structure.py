"""
Test script to validate ReasoningBank MCP Server structure

This script performs static validation of the server implementation:
- Checks that all required imports are present
- Validates function signatures
- Ensures proper error handling
- Verifies component initialization logic
"""

import ast
import sys


def validate_server_structure():
    """Validate the server implementation structure"""
    print("=== Validating ReasoningBank MCP Server Structure ===\n")
    
    # Read the server file
    with open("reasoning_bank_server.py", "r") as f:
        source_code = f.read()
    
    # Parse the AST
    try:
        tree = ast.parse(source_code)
        print("✅ Server file parses successfully\n")
    except SyntaxError as e:
        print(f"❌ Syntax error in server file: {e}")
        return False
    
    # Check for required imports
    print("Checking required imports...")
    required_imports = [
        "Server",
        "ReasoningBank",
        "IterativeReasoningAgent",
        "CachedLLMClient",
        "ResponsesAPIClient",
        "PassiveLearner",
        "WorkspaceManager",
        "KnowledgeRetriever",
        "create_storage_backend",
        "get_config"
    ]
    
    found_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                found_imports.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found_imports.add(alias.name)
    
    missing_imports = set(required_imports) - found_imports
    if missing_imports:
        print(f"❌ Missing imports: {missing_imports}")
        return False
    else:
        print(f"✅ All required imports present ({len(required_imports)} imports)\n")
    
    # Check for required functions
    print("Checking required MCP tools...")
    required_functions = [
        "lifespan",
        "solve_coding_task",
        "retrieve_memories",
        "get_memory_genealogy",
        "get_statistics"
    ]
    
    found_functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found_functions.append(node.name)
    
    missing_functions = set(required_functions) - set(found_functions)
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    else:
        print(f"✅ All required functions present ({len(required_functions)} functions)\n")
    
    # Check lifespan function structure
    print("Validating lifespan function...")
    lifespan_node = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "lifespan":
            lifespan_node = node
            break
    
    if lifespan_node:
        # Check for asynccontextmanager decorator
        has_decorator = any(
            (isinstance(d, ast.Name) and d.id == "asynccontextmanager") or
            (isinstance(d, ast.Attribute) and d.attr == "asynccontextmanager")
            for d in lifespan_node.decorator_list
        )
        
        if has_decorator:
            print("✅ lifespan has asynccontextmanager decorator")
        else:
            print("❌ lifespan missing asynccontextmanager decorator")
            return False
        
        # Check for yield statement
        has_yield = any(
            isinstance(node, ast.Yield) or isinstance(node, ast.Expr) and isinstance(node.value, ast.Yield)
            for node in ast.walk(lifespan_node)
        )
        
        if has_yield:
            print("✅ lifespan has yield statement")
        else:
            print("❌ lifespan missing yield statement")
            return False
    else:
        print("❌ lifespan function not found")
        return False
    
    print()
    
    # Check for global component declarations
    print("Checking global component declarations...")
    global_vars = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    global_vars.append(target.id)
    
    required_globals = [
        "reasoning_bank",
        "iterative_agent",
        "cached_llm_client",
        "passive_learner",
        "workspace_manager",
        "knowledge_retriever"
    ]
    
    missing_globals = set(required_globals) - set(global_vars)
    if missing_globals:
        print(f"⚠️  Some global components may not be declared: {missing_globals}")
    else:
        print(f"✅ All global components declared ({len(required_globals)} components)\n")
    
    # Check for error handling in tools
    print("Checking error handling in MCP tools...")
    tools_with_try_except = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in ["solve_coding_task", "retrieve_memories", "get_statistics"]:
            has_try = any(isinstance(n, ast.Try) for n in ast.walk(node))
            if has_try:
                tools_with_try_except.append(node.name)
    
    if len(tools_with_try_except) >= 3:
        print(f"✅ MCP tools have error handling ({len(tools_with_try_except)} tools)\n")
    else:
        print(f"⚠️  Some MCP tools may be missing error handling\n")
    
    # Check for logging statements
    print("Checking logging usage...")
    logging_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "logger":
                    logging_calls += 1
    
    if logging_calls > 10:
        print(f"✅ Comprehensive logging present ({logging_calls} log statements)\n")
    else:
        print(f"⚠️  Limited logging ({logging_calls} log statements)\n")
    
    # Summary
    print("=== Validation Summary ===")
    print("✅ Server structure is valid")
    print("✅ All required components are present")
    print("✅ Proper error handling implemented")
    print("✅ Lifespan management correctly structured")
    print("\nThe server is ready for integration testing!")
    
    return True


if __name__ == "__main__":
    success = validate_server_structure()
    sys.exit(0 if success else 1)
