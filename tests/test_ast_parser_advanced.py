#!/usr/bin/env python3
"""
Advanced tests for the ast_parser.py module.
Tests complex Python constructs, decorators, and edge cases.
"""
import os
import sys
import unittest
import tempfile
import subprocess
from pathlib import Path
import json

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from repomap.ast_parser import process_file, find_nodes


class TestAdvancedPythonConstructs(unittest.TestCase):
    """Test ast_parser.py with advanced Python language constructs."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample Python file with advanced constructs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = Path(self.temp_dir.name) / "advanced_sample.py"
        
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"Sample module with advanced Python constructs.\"\"\"
import sys
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, TypeVar, Generic, Callable, Any
from enum import Enum, auto
from functools import wraps, lru_cache

# Type variables and generics
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# Enums
class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()

# Dataclasses
@dataclass
class Point:
    x: float
    y: float
    name: str = "Point"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def distance_from_origin(self) -> float:
        \"\"\"Calculate distance from origin.\"\"\"
        return (self.x ** 2 + self.y ** 2) ** 0.5
    
    def __str__(self) -> str:
        return f"{self.name}({self.x}, {self.y})"

# Decorators
def timing_decorator(func):
    \"\"\"Decorator that times function execution.\"\"\"
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

@timing_decorator
def slow_function():
    \"\"\"A slow function with a decorator.\"\"\"
    import time
    time.sleep(0.1)
    return "Done"

# Closures and higher-order functions
def create_multiplier(factor):
    \"\"\"Create and return a multiplier function.\"\"\"
    def multiplier(x):
        return x * factor
    return multiplier

double = create_multiplier(2)
triple = create_multiplier(3)

# Function with type annotations and default values
def process_data(
    data: List[Union[int, float]], 
    threshold: float = 0.5, 
    callback: Optional[Callable[[float], None]] = None
) -> Dict[str, float]:
    \"\"\"Process numerical data with optional callback.\"\"\"
    result = {
        "mean": sum(data) / len(data) if data else 0,
        "max": max(data) if data else 0,
        "min": min(data) if data else 0
    }
    
    if callback and result["mean"] > threshold:
        callback(result["mean"])
        
    return result

# Async functions
async def fetch_data(url: str) -> str:
    \"\"\"Fetch data from a URL asynchronously.\"\"\"
    await asyncio.sleep(0.1)  # Simulate network delay
    return f"Data from {url}"

async def process_multiple_urls(urls: List[str]) -> List[str]:
    \"\"\"Process multiple URLs in parallel.\"\"\"
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks)

# Context manager
class DatabaseConnection:
    \"\"\"A database connection context manager.\"\"\"
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
        
    def __enter__(self):
        print(f"Connecting to {self.connection_string}")
        self.connection = {"status": "connected"}
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Closing connection")
        self.connection = None
        return False

# Class with property getter and setter
class Temperature:
    \"\"\"Temperature class with Celsius and Fahrenheit properties.\"\"\"
    
    def __init__(self, celsius: float = 0):
        self._celsius = celsius
    
    @property
    def celsius(self) -> float:
        \"\"\"Get temperature in Celsius.\"\"\"
        return self._celsius
    
    @celsius.setter
    def celsius(self, value: float):
        \"\"\"Set temperature in Celsius.\"\"\"
        if value < -273.15:
            raise ValueError("Temperature below absolute zero!")
        self._celsius = value
    
    @property
    def fahrenheit(self) -> float:
        \"\"\"Get temperature in Fahrenheit.\"\"\"
        return self._celsius * 9/5 + 32
    
    @fahrenheit.setter
    def fahrenheit(self, value: float):
        \"\"\"Set temperature in Fahrenheit.\"\"\"
        self.celsius = (value - 32) * 5/9

# Generator function
def fibonacci(n: int):
    \"\"\"Generate first n Fibonacci numbers.\"\"\"
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# Lambda functions
square = lambda x: x ** 2
is_even = lambda x: x % 2 == 0

# List comprehension
squares = [x ** 2 for x in range(10)]
even_squares = [x ** 2 for x in range(10) if x % 2 == 0]

# Dictionary comprehension
char_counts = {char: ord(char) for char in "hello"}

# Using some of the defined elements
if __name__ == "__main__":
    p = Point(3, 4)
    print(f"Distance: {p.distance_from_origin()}")
    
    result = slow_function()
    print(result)
    
    print(f"Double 5: {double(5)}")
    print(f"Triple 5: {triple(5)}")
    
    data = [1, 2, 3, 4, 5]
    stats = process_data(data, callback=lambda x: print(f"Mean: {x}"))
    print(stats)
    
    with DatabaseConnection("mysql://localhost") as conn:
        print(f"Connection status: {conn['status']}")
    
    temp = Temperature(25)
    print(f"{temp.celsius}°C = {temp.fahrenheit}°F")
    temp.fahrenheit = 68
    print(f"{temp.celsius}°C = {temp.fahrenheit}°F")
    
    print("Fibonacci numbers:")
    for num in fibonacci(10):
        print(num, end=" ")
    print()
    
    print(f"Squares: {squares}")
    print(f"Even squares: {even_squares}")
    print(f"Character counts: {char_counts}")
""")

        # Path to the ast_parser.py script
        # Try different possible locations
        ast_parser_path = Path(__file__).parent.parent / "ast_parser.py"
        if ast_parser_path.exists():
            self.ast_parser_path = ast_parser_path
        else:
            # Fallback to module path
            self.ast_parser_path = Path(__file__).parent.parent / "repomap" / "ast_parser.py"
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_find_decorated_classes(self):
        """Test finding decorated classes like dataclasses."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find dataclass
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="Point")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], "Point")
        self.assertEqual(nodes[0]['type'], "ClassDef")
        
    def test_find_decorators(self):
        """Test finding decorated functions."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find decorated function
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="slow_function")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], "slow_function")
        self.assertEqual(nodes[0]['type'], "FunctionDef")
        
    def test_find_properties(self):
        """Test finding property methods."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find properties
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="celsius")
        # Should find both the getter and setter
        self.assertGreaterEqual(len(nodes), 1)
        self.assertTrue(any(node['name'] == "celsius" for node in nodes))
        
    def test_find_async_functions(self):
        """Test finding async functions."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find async functions
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="fetch_data")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], "fetch_data")
        
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="process_multiple_urls")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], "process_multiple_urls")
        
    def test_find_generators(self):
        """Test finding generator functions."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find generator function
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="fibonacci")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], "fibonacci")
        
    def test_find_non_callables_advanced(self):
        """Test finding advanced non-callable elements."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find type variables
        nodes = find_nodes(
            source, 
            str(self.test_file_path), 
            name_pattern="T", 
            include_non_callables=True
        )
        non_callable_T = [node for node in nodes if not node.get('is_callable', True)]
        self.assertGreaterEqual(len(non_callable_T), 1)
        
        # Find lambda-defined variables
        nodes = find_nodes(
            source, 
            str(self.test_file_path), 
            name_pattern="square", 
            include_non_callables=True
        )
        non_callable_square = [node for node in nodes if not node.get('is_callable', True)]
        self.assertGreaterEqual(len(non_callable_square), 1)
        
        # Find comprehension variables
        nodes = find_nodes(
            source, 
            str(self.test_file_path), 
            name_pattern="squares", 
            include_non_callables=True
        )
        non_callable_squares = [node for node in nodes if not node.get('is_callable', True)]
        self.assertGreaterEqual(len(non_callable_squares), 1)
        
    def test_get_code_for_complex_functions(self):
        """Test retrieving code for complex function definitions."""
        # Get code for complex function with type annotations
        results = process_file(
            str(self.test_file_path),
            name_pattern="process_data",
            get_code=True
        )
        
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        code = results['results'][0]['code']
        
        # Check that we got the complete function
        self.assertIn("def process_data(", code)
        self.assertIn("data: List[Union[int, float]]", code)
        self.assertIn("return result", code)
        
    def test_get_code_for_async_functions(self):
        """Test retrieving code for async functions."""
        results = process_file(
            str(self.test_file_path),
            name_pattern="fetch_data",
            get_code=True
        )
        
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        code = results['results'][0]['code']
        
        # Check that we got the complete async function
        self.assertIn("async def fetch_data", code)
        self.assertIn("await asyncio.sleep", code)
        
    def test_get_code_with_decorators(self):
        """Test retrieving code for decorated functions."""
        results = process_file(
            str(self.test_file_path),
            name_pattern="slow_function",
            get_code=True
        )
        
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        code = results['results'][0]['code']
        
        # Check that we got the function with its decorator
        self.assertIn("@timing_decorator", code)
        self.assertIn("def slow_function", code)
        
    def test_signature_only_with_decorators(self):
        """Test retrieving just the signature of decorated functions."""
        results = process_file(
            str(self.test_file_path),
            name_pattern="slow_function",
            signature_only=True
        )
        
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        code = results['results'][0]['code']
        
        # Check that we got the decorator and function signature
        self.assertIn("@timing_decorator", code)
        self.assertIn("def slow_function", code)
        
        # Check that we didn't get the full function body
        self.assertNotIn("time.sleep", code)
        
        # Run through CLI
        result = self.run_ast_parser("slow_function", "--signature-only")
        self.assertEqual(result.returncode, 0)
        # Should include decorator and function declaration
        self.assertIn("@timing_decorator", result.stdout)
        self.assertIn("def slow_function", result.stdout)
        
    def run_ast_parser(self, *args):
        """Run the ast_parser.py script with the given arguments."""
        try:
            # First try with direct script
            cmd = [sys.executable, str(self.ast_parser_path), str(self.test_file_path)] + list(args)
            result = subprocess.run(cmd, 
                                   capture_output=True, 
                                   text=True,
                                   check=False)
            return result
        except Exception:
            # Fallback to module import
            cmd = [sys.executable, "-m", "repomap.ast_parser", str(self.test_file_path)] + list(args)
            result = subprocess.run(cmd, 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
            return result
        
    def test_cli_pattern_matching_advanced(self):
        """Test pattern matching for advanced constructs."""
        # Find all class methods with property decorator
        result = self.run_ast_parser("*", "--line-numbers-only")
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        
        # Should find various advanced constructs
        self.assertIn("Color (ClassDef)", output)
        self.assertIn("Point (ClassDef)", output)
        self.assertIn("DatabaseConnection (ClassDef)", output)
        self.assertIn("Temperature (ClassDef)", output)
        self.assertIn("fetch_data (AsyncFunctionDef)", output)  # Async functions have the correct type
        self.assertIn("fibonacci (FunctionDef)", output)
        
        # Try finding all property getters
        result = self.run_ast_parser("*", "--get-code", "--line-numbers-only")
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        
        # Should find property getters and setters
        self.assertIn("celsius", output)
        self.assertIn("fahrenheit", output)


class TestAstParserEdgeCases(unittest.TestCase):
    """Test ast_parser.py with edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        # Path to the ast_parser.py script
        # Try different possible locations
        ast_parser_path = Path(__file__).parent.parent / "ast_parser.py"
        if ast_parser_path.exists():
            self.ast_parser_path = ast_parser_path
        else:
            # Fallback to module path
            self.ast_parser_path = Path(__file__).parent.parent / "repomap" / "ast_parser.py"
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
        
    def test_nonexistent_file(self):
        """Test behavior with nonexistent file."""
        nonexistent_file = Path(self.temp_dir.name) / "nonexistent.py"
        results = process_file(str(nonexistent_file), name_pattern="*")
        self.assertIn('error', results)
        self.assertIn("File not found", results['error'])
        
    def test_empty_file(self):
        """Test behavior with empty file."""
        empty_file = Path(self.temp_dir.name) / "empty.py"
        with open(empty_file, 'w') as f:
            f.write("")
        
        results = process_file(str(empty_file), name_pattern="*")
        self.assertIn('error', results)
        self.assertIn("No code elements found", results['error'])
        
    def test_syntax_error(self):
        """Test behavior with file containing syntax errors."""
        invalid_file = Path(self.temp_dir.name) / "invalid.py"
        with open(invalid_file, 'w') as f:
            f.write("def invalid_function(:\n    pass")
        
        # Should handle the syntax error gracefully
        results = process_file(str(invalid_file), name_pattern="*")
        self.assertIn('error', results)
        
    def test_binary_file(self):
        """Test behavior with binary file."""
        binary_file = Path(self.temp_dir.name) / "binary.pyc"
        with open(binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')
        
        # Should handle non-text files gracefully
        results = process_file(str(binary_file), name_pattern="*")
        self.assertIn('error', results)
        
    def run_ast_parser(self, file_path, *args):
        """Run the ast_parser.py script with the given arguments."""
        try:
            # First try with direct script
            cmd = [sys.executable, str(self.ast_parser_path), str(file_path)] + list(args)
            result = subprocess.run(cmd, 
                                   capture_output=True, 
                                   text=True,
                                   check=False)
            return result
        except Exception:
            # Fallback to module import
            cmd = [sys.executable, "-m", "repomap.ast_parser", str(file_path)] + list(args)
            result = subprocess.run(cmd, 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
            return result
        
    def test_cli_error_handling(self):
        """Test CLI error handling."""
        # Test with nonexistent file
        nonexistent_file = Path(self.temp_dir.name) / "nonexistent.py"
        result = self.run_ast_parser(nonexistent_file, "*")
        self.assertIn("does not exist or is not accessible", result.stderr)
        
        # Test with invalid pattern
        invalid_file = Path(self.temp_dir.name) / "invalid.py"
        with open(invalid_file, 'w') as f:
            f.write("def sample(): pass")
        
        result = self.run_ast_parser(invalid_file, "[")  # Invalid regex pattern
        self.assertNotEqual(result.returncode, 0)
        
        # Test invalid combination of options
        result = self.run_ast_parser(invalid_file, "*", "--add-line-numbers")
        # Should warn that --add-line-numbers requires --get-code
        self.assertEqual(result.returncode, 0)  # Should still run


if __name__ == "__main__":
    unittest.main()
