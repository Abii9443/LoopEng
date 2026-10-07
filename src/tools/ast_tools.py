"""AST-based code analysis tools."""
import ast
from pathlib import Path
from langchain.tools import tool


@tool
def parse_ast(file_path: str) -> str:
    """
    Parse Python file using AST to find structural issues.
    Analyzes function complexity, class structure, and potential issues.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Analysis results or error message
    """
    try:
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."

        if not file_path.endswith('.py'):
            return f"Skipping {file_path}: Not a Python file."

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            return f"Syntax error in {file_path} at line {e.lineno}: {e.msg}"

        # Analyze the AST
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        analysis = f"AST Analysis for {file_path}:\n"
        analysis += f"  Functions: {len(functions)}\n"
        analysis += f"  Classes: {len(classes)}\n"

        # Check for complexity issues
        complex_functions = []
        for func in functions:
            # Count nested structures as proxy for complexity
            nested_count = sum(1 for _ in ast.walk(func) if isinstance(_, (ast.If, ast.For, ast.While, ast.Try)))
            if nested_count > 5:
                complex_functions.append((func.name, nested_count, func.lineno))

        if complex_functions:
            analysis += f"\n  ⚠️  High complexity functions:\n"
            for name, count, line in complex_functions:
                analysis += f"    - {name}() at line {line}: {count} nested structures\n"

        # Check for missing docstrings
        missing_docs = []
        for func in functions:
            if not ast.get_docstring(func):
                missing_docs.append((func.name, func.lineno))

        if missing_docs and len(missing_docs) <= 5:
            analysis += f"\n  ℹ️  Functions without docstrings:\n"
            for name, line in missing_docs[:5]:
                analysis += f"    - {name}() at line {line}\n"

        # Check for bare excepts
        bare_excepts = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bare_excepts.append(node.lineno)

        if bare_excepts:
            analysis += f"\n  ⚠️  Bare except clauses found at lines: {bare_excepts}\n"
            analysis += "    (These catch all exceptions including KeyboardInterrupt)\n"

        return analysis

    except Exception as e:
        return f"Error parsing AST for {file_path}: {str(e)}"


@tool
def check_complexity(file_path: str) -> str:
    """
    Calculate cyclomatic complexity for functions in a Python file.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Complexity metrics or error message
    """
    try:
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."

        if not file_path.endswith('.py'):
            return f"Skipping {file_path}: Not a Python file."

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            return f"Syntax error in {file_path}: {e.msg}"

        # Simple complexity calculation
        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Count decision points
                complexity = 1  # Base complexity
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.And, ast.Or)):
                        complexity += 1
                    elif isinstance(child, ast.ExceptHandler):
                        complexity += 1

                if complexity > 10:
                    results.append(f"  ⚠️  {node.name}() at line {node.lineno}: complexity {complexity} (high)")
                elif complexity > 5:
                    results.append(f"  {node.name}() at line {node.lineno}: complexity {complexity} (moderate)")

        if results:
            return f"Complexity analysis for {file_path}:\n" + "\n".join(results)
        else:
            return f"All functions in {file_path} have acceptable complexity."

    except Exception as e:
        return f"Error checking complexity: {str(e)}"
