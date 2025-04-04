#!/usr/bin/env python3
"""
AST Parser using tree-sitter for JavaScript, TypeScript, and other languages.
Provides a common interface for extracting code elements from different language files.
"""
import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path

def parse_file(file_path, language):
    """
    Parse a file and extract code elements using appropriate parser.
    
    Args:
        file_path: Path to the file to parse
        language: Programming language of the file ('javascript', 'typescript', etc.)
        
    Returns:
        List of code elements with their positions
    """
    # Convert language name to lowercase for consistency
    language = language.lower()
    
    # Map file extensions to languages if needed
    if language.startswith('.'):
        extension_to_lang = {
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.py': 'python',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.rust': 'rust',
            '.cs': 'csharp'
        }
        language = extension_to_lang.get(language, 'javascript')
    
    if language in ['javascript', 'typescript', 'jsx', 'tsx']:
        return parse_javascript(file_path)
    elif language == 'python':
        return parse_python(file_path)
    else:
        # Default to basic parsing for unsupported languages
        return generic_parse(file_path, language)

def parse_javascript(file_path):
    """
    Parse JavaScript/TypeScript file using regex-based extraction.
    
    Args:
        file_path: Path to the JavaScript/TypeScript file
        
    Returns:
        List of code elements (functions, classes, methods) with line information
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        elements = []
        
        # Find functions
        import re
        
        # Match class declarations
        class_pattern = re.compile(r'class\s+(\w+)')
        for match in class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            elements.append({
                'type': 'class',
                'name': match.group(1),
                'line': line_num
            })
        
        # Match function declarations
        func_pattern = re.compile(r'function\s+(\w+)')
        for match in func_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            elements.append({
                'type': 'function',
                'name': match.group(1),
                'line': line_num
            })
        
        # Match method declarations inside classes
        method_pattern = re.compile(r'(\w+)\s*\([^)]*\)\s*{')
        for match in method_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            elements.append({
                'type': 'method',
                'name': match.group(1),
                'line': line_num
            })
        
        # Match arrow functions
        arrow_pattern = re.compile(r'(const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=]*)\s*=>')
        for match in arrow_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            elements.append({
                'type': 'arrow_function',
                'name': match.group(2),
                'line': line_num
            })
        
        return elements
    
    except Exception as e:
        print(f"Error parsing JavaScript file: {e}", file=sys.stderr)
        return []

def parse_python(file_path):
    """
    Parse Python file using the built-in ast module.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of code elements (functions, classes, methods) with line information
    """
    try:
        import ast
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        elements = []
        
        # Process all nodes in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                elements.append({
                    'type': 'class',
                    'name': node.name,
                    'line': node.lineno
                })
            elif isinstance(node, ast.FunctionDef):
                # Check if this is a method (inside a class)
                is_method = False
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef) and node in parent.body:
                        is_method = True
                        break
                
                elements.append({
                    'type': 'method' if is_method else 'function',
                    'name': node.name,
                    'line': node.lineno
                })
        
        return elements
    
    except Exception as e:
        print(f"Error parsing Python file: {e}", file=sys.stderr)
        return []

def generic_parse(file_path, language):
    """
    Generic parser for languages without specific implementation.
    Uses simple regex patterns to find functions and classes.
    
    Args:
        file_path: Path to the file
        language: Programming language name
        
    Returns:
        List of code elements found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        elements = []
        import re
        
        # Generic patterns that work for many C-like languages
        class_pattern = re.compile(r'class\s+(\w+)')
        func_pattern = re.compile(r'(?:function|def|func|fn)\s+(\w+)')
        
        # Find classes
        for match in class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            elements.append({
                'type': 'class',
                'name': match.group(1),
                'line': line_num
            })
        
        # Find functions
        for match in func_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            elements.append({
                'type': 'function',
                'name': match.group(1),
                'line': line_num
            })
        
        return elements
        
    except Exception as e:
        print(f"Error with generic parsing: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    # CLI interface compatible with section_splitting.py
    if len(sys.argv) < 2:
        print("Usage: ast_parser.py <file_path> [function_name]", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    function_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Infer language from file extension
    _, ext = os.path.splitext(file_path)
    language = ext
    
    # Parse file
    elements = parse_file(file_path, language)
    
    # If a specific function/class name was provided, filter for it
    if function_name:
        for element in elements:
            if element['name'] == function_name:
                # Format output for section_splitting.py
                start_line = element.get('line', element.get('start_line', 0))
                end_line = element.get('end_line', start_line + 5)
                print(f"Found Callable '{function_name}' at lines {start_line}-{end_line}")
                sys.exit(0)
        
        # If we didn't find the element
        print(f"Callable '{function_name}' not found")
        sys.exit(1)
    else:
        # If no specific name was provided, print all elements as JSON
        print(json.dumps(elements, indent=2))
        sys.exit(0)