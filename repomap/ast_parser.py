#!/usr/bin/env python3
"""
Advanced AST Parser for Python code analysis.
Provides comprehensive code search and extraction features.
"""
import ast
import sys
import re
import argparse
from pathlib import Path
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Tuple, Set, Union


def get_source_lines(filename: str) -> List[str]:
    """Read source file and return its lines."""
    filepath = Path(filename)
    try:
        source = filepath.read_text(encoding='utf-8')
        return source.splitlines(keepends=True)
    except Exception as e:
        print(f"Error reading file '{filename}': {e}", file=sys.stderr)
        return []


def match_name_pattern(node_name: str, pattern: str) -> bool:
    """
    Match a node name against a pattern, supporting wildcards.
    """
    if pattern == '*':
        return True
    
    # Convert glob-style pattern to regex
    regex_pattern = pattern.replace('*', '.*').replace('?', '.')
    return bool(re.fullmatch(regex_pattern, node_name))


def extract_line_range(
    node: Union[ast.AST, Dict[str, Any]], 
    source_lines: List[str],
    context_lines: int = 0
) -> Tuple[int, int, List[str]]:
    """
    Extract the line range and source code for a given AST node or node info dict.
    
    Args:
        node: The AST node or a dictionary with lineno and end_lineno keys
        source_lines: Source code lines
        context_lines: Number of context lines to include before and after
        
    Returns:
        Tuple of (start_line, end_line, source_code_lines)
    """
    # Handle both AST nodes and dictionaries
    if isinstance(node, dict):
        if 'lineno' not in node or 'end_lineno' not in node:
            return (0, 0, [])
        start_line = max(0, node['lineno'] - 1)  # Convert to 0-based indexing
        end_line = node['end_lineno']  # Already 0-based when accessing list
    elif hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
        start_line = max(0, node.lineno - 1)  # Convert to 0-based indexing
        end_line = node.end_lineno  # Already 0-based when accessing list
    else:
        return (0, 0, [])
    
    # Add context if requested
    context_start = max(0, start_line - context_lines)
    context_end = min(len(source_lines), end_line + context_lines)
    
    # Extract the lines
    code_lines = source_lines[context_start:context_end]
    
    # Convert back to 1-based indexing for return values
    return (context_start + 1, context_end, code_lines)


def find_nodes(
    source: str, 
    filename: str,
    name_pattern: str = '*',
    include_non_callables: bool = False,
    feature_version: Tuple[int, int] = (3, 10)
) -> List[Dict[str, Any]]:
    """
    Find nodes in source code matching the given pattern.
    
    Args:
        source: Source code as string
        filename: Name of the source file
        name_pattern: Pattern to match node names (supports wildcards)
        include_non_callables: Whether to include non-callable nodes
        feature_version: Python feature version for AST parsing
        
    Returns:
        List of matching nodes with metadata
    """
    try:
        module_node = ast.parse(source, filename=str(filename), 
                               type_comments=True, 
                               feature_version=feature_version)
    except SyntaxError as e:
        print(f"Syntax error in {filename}: {e}", file=sys.stderr)
        return []
    
    result = []
    
    # Track unique names to detect duplicates
    seen_names = {}
    
    # Find callable objects (functions, methods, classes)
    callable_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    
    # Process all nodes in the AST
    for node in ast.walk(module_node):
        node_info = None
        
        # Handle callables
        if isinstance(node, callable_types):
            if match_name_pattern(node.name, name_pattern):
                node_info = {
                    'name': node.name,
                    'type': node.__class__.__name__,
                    'lineno': getattr(node, 'lineno', 0),
                    'end_lineno': getattr(node, 'end_lineno', 0),
                    'is_callable': True,
                }
        
        # Handle non-callables if requested
        elif include_non_callables:
            node_name = None
            
            # Assignments (variables, constants)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if match_name_pattern(target.id, name_pattern):
                            node_name = target.id
                            node_info = {
                                'name': node_name,
                                'type': 'Variable',
                                'lineno': getattr(node, 'lineno', 0),
                                'end_lineno': getattr(node, 'end_lineno', 0),
                                'is_callable': False,
                            }
            
            # Import statements
            elif isinstance(node, ast.Import):
                for name in node.names:
                    alias = name.asname or name.name
                    if match_name_pattern(alias, name_pattern):
                        node_name = alias
                        node_info = {
                            'name': node_name,
                            'type': 'Import',
                            'lineno': getattr(node, 'lineno', 0),
                            'end_lineno': getattr(node, 'end_lineno', 0),
                            'is_callable': False,
                        }
            
            # Import from statements
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    alias = name.asname or name.name
                    if match_name_pattern(alias, name_pattern):
                        node_name = alias
                        node_info = {
                            'name': node_name,
                            'type': 'ImportFrom',
                            'lineno': getattr(node, 'lineno', 0),
                            'end_lineno': getattr(node, 'end_lineno', 0),
                            'is_callable': False,
                            'module': node.module or '',
                        }
            
            # Global variables
            elif isinstance(node, ast.Global):
                for name in node.names:
                    if match_name_pattern(name, name_pattern):
                        node_name = name
                        node_info = {
                            'name': node_name,
                            'type': 'Global',
                            'lineno': getattr(node, 'lineno', 0),
                            'end_lineno': getattr(node, 'end_lineno', 0),
                            'is_callable': False,
                        }
            
            # Class attributes
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if match_name_pattern(node.target.id, name_pattern):
                    node_name = node.target.id
                    node_info = {
                        'name': node_name,
                        'type': 'Attribute',
                        'lineno': getattr(node, 'lineno', 0),
                        'end_lineno': getattr(node, 'end_lineno', 0),
                        'is_callable': False,
                    }
        
        # Add the node if it matched
        if node_info:
            # Check for duplicates
            if node_info['name'] in seen_names:
                # For duplicates, add an index to make the name unique
                duplicate_count = seen_names[node_info['name']]
                seen_names[node_info['name']] = duplicate_count + 1
                node_info['duplicate_index'] = duplicate_count
            else:
                seen_names[node_info['name']] = 1
            
            result.append(node_info)
    
    return result


def format_code_with_line_numbers(
    code_lines: List[str], 
    start_line: int,
    add_line_numbers: bool = False
) -> str:
    """
    Format code lines, optionally adding line numbers.
    
    Args:
        code_lines: The source code lines
        start_line: Starting line number (1-based)
        add_line_numbers: Whether to add line numbers
        
    Returns:
        Formatted code as string
    """
    if not add_line_numbers:
        return ''.join(code_lines)
    
    # Calculate padding for line numbers based on the highest line number
    max_line = start_line + len(code_lines) - 1
    padding = len(str(max_line))
    
    # Format each line with line number
    formatted_lines = []
    for i, line in enumerate(code_lines):
        line_num = start_line + i
        formatted_lines.append(f"{line_num:{padding}} 〉{line}")
    
    return ''.join(formatted_lines)


def process_file(
    filename: str,
    name_pattern: str = '*',
    get_code: bool = False,
    line_numbers_only: bool = False,
    include_non_callables: bool = False,
    add_context: int = 0,
    add_line_numbers: bool = False,
    feature_version: Tuple[int, int] = (3, 10)
) -> Dict[str, Any]:
    """
    Process a Python source file to find and extract code elements.
    
    Args:
        filename: Path to the Python file
        name_pattern: Pattern to match node names (supports wildcards)
        get_code: Whether to return the actual source code
        line_numbers_only: Only return line numbers, not AST details
        include_non_callables: Include non-callable nodes like variables
        add_context: Number of context lines to include before and after
        add_line_numbers: Whether to add line numbers to the output
        feature_version: Python feature version to use for parsing
        
    Returns:
        Dictionary with results
    """
    filepath = Path(filename)
    if not filepath.is_file():
        print(f"Error: File '{filename}' does not exist or is not accessible.", file=sys.stderr)
        return {'error': f"File not found: {filename}"}
    
    try:
        source = filepath.read_text(encoding='utf-8')
        source_lines = source.splitlines(keepends=True)
    except Exception as e:
        print(f"Error reading file '{filename}': {e}", file=sys.stderr)
        return {'error': f"Error reading file: {e}"}
    
    # Find matching nodes
    nodes = find_nodes(
        source, 
        filename,
        name_pattern=name_pattern,
        include_non_callables=include_non_callables,
        feature_version=feature_version
    )
    
    if not nodes:
        if name_pattern == '*':
            return {'error': f"No code elements found in {filename}."}
        else:
            return {'error': f"No elements matching '{name_pattern}' found in {filename}."}
    
    results = []
    
    for node in nodes:
        node_name = node['name']
        start_line = node['lineno']
        end_line = node['end_lineno']
        node_type = node.get('type', 'Unknown')
        
        # Handle different output formats
        if get_code:
            # Extract code including context if requested
            code_start, code_end, code_lines = extract_line_range(
                node,  # Use the node object directly 
                source_lines,
                context_lines=add_context
            )
            
            # Format with line numbers if requested
            formatted_code = format_code_with_line_numbers(
                code_lines, 
                code_start,
                add_line_numbers=add_line_numbers
            )
            
            result_entry = {
                'name': node_name,
                'type': node_type,
                'start_line': code_start,
                'end_line': code_end,
                'code': formatted_code
            }
        elif line_numbers_only:
            result_entry = {
                'name': node_name,
                'type': node_type,
                'start_line': start_line,
                'end_line': end_line
            }
        else:
            # Default: return details about the node
            result_entry = {
                'name': node_name,
                'type': node_type,
                'start_line': start_line,
                'end_line': end_line,
                'is_callable': node.get('is_callable', True)
            }
            
            # Add module information for imports
            if 'module' in node:
                result_entry['module'] = node['module']
        
        results.append(result_entry)
    
    return {'results': results, 'filename': filename}


def print_results(results: Dict[str, Any], line_numbers_only: bool = False, get_code: bool = False) -> None:
    """Print results in a structured format."""
    if 'error' in results:
        print(results['error'])
        return
    
    if not results.get('results'):
        print(f"No matches found in {results.get('filename', 'file')}.")
        return
    
    nodes = results['results']
    
    # Different output formats based on options
    if get_code:
        for node in nodes:
            print(f"// {node['name']} ({node['type']}, lines {node['start_line']}-{node['end_line']}):")
            print(node['code'])
            print()
    elif line_numbers_only:
        for node in nodes:
            if 'module' in node:
                print(f"{node['name']} ({node['type']} from {node['module']}): {node['start_line']}-{node['end_line']}")
            else:
                print(f"{node['name']} ({node['type']}): {node['start_line']}-{node['end_line']}")
    else:
        for node in nodes:
            if node.get('is_callable', True):
                print(f"Found Callable '{node['name']}' at lines {node['start_line']}-{node['end_line']}")
            else:
                if 'module' in node:
                    print(f"Found {node['type']} '{node['name']}' (from {node['module']}) at lines {node['start_line']}-{node['end_line']}")
                else:
                    print(f"Found {node['type']} '{node['name']}' at lines {node['start_line']}-{node['end_line']}")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Advanced Python AST parser for code analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Find a specific function:
    ast_parser.py myfile.py function_name
  
  Find all callable elements:
    ast_parser.py myfile.py "*" 
  
  Get the source code of a class with line numbers:
    ast_parser.py myfile.py MyClass --get-code --add-line-numbers
  
  Find all elements (callable and non-callable) with 5 lines of context:
    ast_parser.py myfile.py "*" --non-callables --get-code --add-context 5
  
  Get a compact listing of all callable elements:
    ast_parser.py myfile.py "*" --line-numbers-only
"""
    )
    
    parser.add_argument('filename', help='Python source file to analyze')
    parser.add_argument('pattern', help='Name pattern to search for (supports wildcards * and ?)')
    
    parser.add_argument('--non-callables', action='store_true', 
                      help='Include non-callable elements like variables and imports')
    
    parser.add_argument('--line-numbers-only', action='store_true',
                      help='Only print line number ranges, not full AST details')
    
    parser.add_argument('--get-code', action='store_true',
                      help='Extract and print the source code of matching elements')
    
    parser.add_argument('--add-context', nargs='?', type=int, const=10, metavar='LINES',
                      help='Add context lines before and after (default: 10 if flag used without value)')
    
    parser.add_argument('--add-line-numbers', action='store_true',
                      help='Add line numbers to extracted code (only with --get-code)')
    
    parser.add_argument('--version', type=str, default='3.10',
                      help='Python language version to use for parsing (e.g., 3.9, 3.10)')
    
    args = parser.parse_args()
    
    # Process version
    try:
        major, minor = map(int, args.version.split('.'))
        feature_version = (major, minor)
    except ValueError:
        print(f"Invalid version format: {args.version}. Using default (3.10).", file=sys.stderr)
        feature_version = (3, 10)
    
    # Handle context lines
    add_context = args.add_context if args.get_code and args.add_context is not None else 0
    
    # Process the file
    results = process_file(
        args.filename,
        name_pattern=args.pattern,
        get_code=args.get_code,
        line_numbers_only=args.line_numbers_only,
        include_non_callables=args.non_callables,
        add_context=add_context,
        add_line_numbers=args.add_line_numbers and args.get_code,
        feature_version=feature_version
    )
    
    # Print results
    print_results(results, args.line_numbers_only, args.get_code)
    
    # For compatibility with older scripts
    if len(sys.argv) > 2 and sys.argv[2] != "*":
        # Check if any results matched
        if 'results' in results and results['results']:
            # Find the first matching callable
            for node in results['results']:
                if node.get('is_callable', True) and node['name'] == sys.argv[2]:
                    print(f"Found Callable '{node['name']}' at lines {node['start_line']}-{node['end_line']}")
                    sys.exit(0)


if __name__ == "__main__":
    # Check if simple command line arguments are used
    if len(sys.argv) == 3 and not sys.argv[2].startswith('--') and sys.argv[2] != '*':
        # For backward compatibility with section_splitting.py (exact name match)
        filename = sys.argv[1]
        pattern = sys.argv[2]
        
        results = process_file(filename, name_pattern=pattern)
        
        if 'results' in results and results['results']:
            for node in results['results']:
                if node.get('is_callable', True) and node['name'] == pattern:
                    print(f"Found Callable '{node['name']}' at lines {node['start_line']}-{node['end_line']}")
                    sys.exit(0)
                    
            # If we get here, no exact match was found
            print(f"Callable '{pattern}' not found")
            sys.exit(1)
        else:
            print(f"Callable '{pattern}' not found")
            sys.exit(1)
    else:
        # Use the modern argparse interface
        main()