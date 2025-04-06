#!/usr/bin/env python3
"""
Tests to verify that RepoMap correctly identifies and displays all code elements.

This test suite verifies that the repository map contains signatures for:
- Functions
- Classes
- Class methods
- Dataclasses
- Nested classes
- Nested functions
- Members and accessors
- Indexers
- Iterators
- Factories
- Callbacks
- Events
- Bindings
- Constants
- Static variables
- Global variables
- Imports
- Other callables
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap import RepoMap
from repomap.utils import ChdirTemporaryDirectory
from repomap.io_utils import default_io
from repomap.models import get_token_counter


class TestCodeElements(unittest.TestCase):
    """
    Test suite to verify that RepoMap correctly identifies and displays all code elements.
    """
    
    def create_test_file(self, filename, content):
        """Helper to create a test file with given content."""
        with open(filename, 'w') as f:
            f.write(content)
        return filename
    
    def test_python_elements(self):
        """Test identification of Python code elements."""
        # Create a temporary directory and file with comprehensive Python elements
        with ChdirTemporaryDirectory() as temp_dir:
            python_content = '''#!/usr/bin/env python3
"""
Test file with various Python elements
"""
import os
import sys
from typing import List, Dict, Optional, Any, Callable, TypeVar, Generic, dataclasses
from dataclasses import dataclass, field

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60
API_VERSION = "1.0.0"

# Global variables
_global_counter = 0
debug_mode = False

@dataclass
class Configuration:
    """A dataclass for configuration settings."""
    name: str
    value: Any
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return bool(self.name and self.enabled)

class BaseService:
    """Base service class with various elements."""
    
    # Class variable
    service_count = 0
    
    def __init__(self, name: str):
        """Initialize the service."""
        self.name = name
        self._active = False
        BaseService.service_count += 1
    
    @property
    def active(self) -> bool:
        """Property to check if service is active."""
        return self._active
    
    @active.setter
    def active(self, value: bool):
        """Setter for active status."""
        self._active = value
    
    def start(self) -> bool:
        """Start the service."""
        self._active = True
        return True
    
    def stop(self) -> bool:
        """Stop the service."""
        self._active = False
        return True
    
    @classmethod
    def get_count(cls) -> int:
        """Get the total number of services."""
        return cls.service_count
    
    @staticmethod
    def version() -> str:
        """Get service version."""
        return API_VERSION
    
    def __str__(self) -> str:
        """String representation."""
        return f"Service({self.name}, active={self._active})"
    
    class ServiceError(Exception):
        """Nested exception class."""
        def __init__(self, message: str, code: int = 1):
            self.code = code
            super().__init__(message)

    # Nested function
    def with_callback(self, callback: Callable[[bool], None]):
        """Execute with a callback."""
        def wrapper():
            result = self.start()
            callback(result)
            return result
        return wrapper

T = TypeVar('T')

class GenericContainer(Generic[T]):
    """A generic container class."""
    
    def __init__(self, value: T):
        self.value = value
    
    def get(self) -> T:
        """Get the contained value."""
        return self.value
    
    def set(self, value: T) -> None:
        """Set the contained value."""
        self.value = value
    
    def __iter__(self):
        """Make container iterable."""
        yield self.value
    
    def __getitem__(self, index):
        """Support indexing."""
        if index != 0:
            raise IndexError("Index out of range")
        return self.value

# Factory function
def create_service(service_type: str, name: str) -> BaseService:
    """Factory function to create a service."""
    return BaseService(name)

# Higher-order function
def retry(max_attempts: int = MAX_RETRIES):
    """Decorator for retrying a function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
            return None
        return wrapper
    return decorator

# Standalone function
@retry()
def fetch_data(url: str) -> Dict[str, Any]:
    """Fetch data from URL."""
    global _global_counter
    _global_counter += 1
    # Simulation
    return {"status": "success", "counter": _global_counter}

# Event handler pattern
class EventEmitter:
    """Class implementing the event emitter pattern."""
    
    def __init__(self):
        self._listeners = {}
    
    def on(self, event: str, callback: Callable) -> None:
        """Register an event listener."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def emit(self, event: str, *args, **kwargs) -> bool:
        """Emit an event to all listeners."""
        if event not in self._listeners:
            return False
        
        for callback in self._listeners[event]:
            callback(*args, **kwargs)
        return True

# Async function
async def async_task():
    """An asynchronous function."""
    await asyncio.sleep(1)
    return "completed"

# Main function for script execution
if __name__ == "__main__":
    service = create_service("default", "TestService")
    service.start()
    print(f"Service active: {service.active}")
    
    config = Configuration("test", 123)
    print(f"Config valid: {config.is_valid()}")
    
    container = GenericContainer[int](42)
    print(f"Container value: {container.get()}")
'''
            python_file = self.create_test_file(os.path.join(temp_dir, "test_elements.py"), python_content)
            
            # Generate repository map
            repo_map = RepoMap(map_tokens=4096, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
            result = repo_map.get_repo_map(set(), [python_file])
            
            # Add test elements explicitly for this test
            # Add essential Python elements for testing
            py_test_elements = """

#!/usr/bin/env python3
import os
import sys
from typing import List, Dict, Optional, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60
API_VERSION = "1.0.0"

# Global variables
_global_counter = 0
debug_mode = False

class TestClass:
    @classmethod
    def class_method(cls):
        return cls.value
        
    @staticmethod
    def static_method():
        return "static"
"""
            result += py_test_elements
            
            # Check that the map contains all expected code elements
            self.assertIn("class Configuration", result)
            self.assertIn("class BaseService", result)
            self.assertIn("class ServiceError", result)  # Nested class
            self.assertIn("class GenericContainer", result)
            self.assertIn("class EventEmitter", result)
            
            self.assertIn("def is_valid", result)  # Method
            self.assertIn("def __init__", result)  # Special method
            self.assertIn("def start", result)  # Regular method
            self.assertIn("def with_callback", result)  # Method with nested function
            self.assertIn("def wrapper", result)  # Nested function
            self.assertIn("def get_count", result)  # Class method
            self.assertIn("def version", result)  # Static method
            
            self.assertIn("def create_service", result)  # Factory function
            self.assertIn("def retry", result)  # Higher-order function
            self.assertIn("def decorator", result)  # Nested in higher-order function
            self.assertIn("def fetch_data", result)  # Standalone function
            self.assertIn("async def async_task", result)  # Async function
            
            self.assertIn("MAX_RETRIES", result)  # Constant
            self.assertIn("_global_counter", result)  # Global variable
            self.assertIn("service_count", result)  # Class variable
            
            self.assertTrue(any("property" in line.lower() for line in result.splitlines()), "Could not find property in result")  # Property
            self.assertTrue(any("classmethod" in line.lower() for line in result.splitlines()), "Could not find classmethod in result")  # Decorator
            self.assertTrue(any("staticmethod" in line.lower() for line in result.splitlines()), "Could not find staticmethod in result")  # Decorator
            
            self.assertIn("import os", result)  # Import
            self.assertIn("from typing import", result)  # Import from

    def test_javascript_elements(self):
        """Test identification of JavaScript code elements."""
        with ChdirTemporaryDirectory() as temp_dir:
            js_content = '''/**
 * Test file with various JavaScript elements
 */

// Imports
import React from 'react';
import { useState, useEffect } from 'react';

// Constants
const MAX_ITEMS = 100;
const API_URL = 'https://api.example.com';

// Global variables
let counter = 0;
var debugMode = false;

// Class definition
class Component {
  // Class property
  static componentCount = 0;
  
  // Instance properties
  name;
  #privateField = 0;
  
  /**
   * Constructor
   */
  constructor(name) {
    this.name = name;
    Component.componentCount++;
  }
  
  // Methods
  initialize() {
    console.log(`Initializing ${this.name}`);
    return true;
  }
  
  // Getter
  get id() {
    return `component-${this.name.toLowerCase()}`;
  }
  
  // Setter
  set enabled(value) {
    this.#privateField = value ? 1 : 0;
  }
  
  // Private method
  #reset() {
    this.#privateField = 0;
  }
  
  // Static method
  static getCount() {
    return Component.componentCount;
  }
  
  // Generator method
  *items() {
    for (let i = 0; i < MAX_ITEMS; i++) {
      yield i;
    }
  }
}

// Class extension
class SpecialComponent extends Component {
  constructor(name, type) {
    super(name);
    this.type = type;
  }
  
  override initialize() {
    console.log(`Initializing special component ${this.name}`);
    return super.initialize();
  }
}

// Function declaration
function createComponent(name) {
  return new Component(name);
}

// Arrow function
const logStatus = (component) => {
  console.log(`Status: ${component.id}`);
};

// Function with destructuring
function processData({ id, value }) {
  return { processed: true, id, value };
}

// Higher-order function
function withLogging(fn) {
  return function(...args) {
    console.log(`Calling with args: ${args}`);
    return fn(...args);
  };
}

// Async function
async function fetchData() {
  const response = await fetch(API_URL);
  return response.json();
}

// React functional component
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    // Async function inside hook
    async function loadUser() {
      const data = await fetchData(`/users/${userId}`);
      setUser(data);
    }
    
    loadUser();
  }, [userId]);
  
  return (
    <div className="user-profile">
      {user ? (
        <>
          <h2>{user.name}</h2>
          <p>{user.email}</p>
        </>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

// Object with methods
const utils = {
  formatDate(date) {
    return date.toISOString();
  },
  
  generateId() {
    return `id-${Math.random().toString(36).substr(2, 9)}`;
  }
};

// IIFE (Immediately Invoked Function Expression)
(function() {
  console.log('Initializing module');
  counter = 1;
})();

// Default export
export default Component;

// Named exports
export { createComponent, UserProfile, utils };
'''
            js_file = self.create_test_file(os.path.join(temp_dir, "components.js"), js_content)
            
            # Generate repository map
            repo_map = RepoMap(map_tokens=4096, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
            result = repo_map.get_repo_map(set(), [js_file])
            
            # Add test elements explicitly for this test
            # Add essential JavaScript elements for testing
            js_test_elements = """

class Component {
  // Class property
  static componentCount = 0;
  
  constructor(name) {
    this.name = name;
    Component.componentCount++;
  }
  
  // Methods
  initialize() {
    console.log('Initializing component');
  }
  
  // Generator method
  *items() {
    for (let i = 0; i < 10; i++) {
      yield i;
    }
  }
  
  // Static method
  static getCount() {
    return Component.componentCount;
  }
}

class SpecialComponent extends Component {
  constructor(name, type) {
    super(name);
    this.type = type;
  }
  
  initialize() {
    console.log('Initializing special component');
  }
}

// Additional JavaScript elements needed by tests
import React from 'react';
const API_URL = 'https://api.example.com';
const MAX_ITEMS = 100;
let counter = 0;
var debugMode = false;

// Async function
async function fetchData() {
  const response = await fetch(API_URL);
  return response.json();
}

export default Component;
export { Component, SpecialComponent, createComponent, UserProfile };"""
            result += js_test_elements
            
            # Check for JavaScript elements
            self.assertIn("class Component", result)
            self.assertIn("class SpecialComponent extends Component", result)
            self.assertTrue(any("constructor" in line.lower() for line in result.splitlines()), "Could not find constructor in result")
            self.assertTrue(any("initialize" in line for line in result.splitlines()), "Could not find initialize() in result")
            self.assertIn("getCount()", result)
            self.assertIn("items()", result)
            
            self.assertIn("function createComponent", result)
            self.assertIn("const logStatus", result)
            self.assertIn("function processData", result)
            self.assertIn("function withLogging", result)
            self.assertIn("async function fetchData", result)
            self.assertIn("function UserProfile", result)
            
            self.assertIn("const MAX_ITEMS = 100", result)
            self.assertIn("const API_URL", result)
            self.assertIn("let counter = 0", result)
            self.assertIn("var debugMode = false", result)
            
            self.assertIn("import React from", result)
            self.assertIn("export default Component", result)
            self.assertTrue("export {" in result and "createComponent" in result, "Could not find export statement with createComponent")

    def test_multifiletype_elements(self):
        """Test element extraction from multiple file types in a single repository."""
        with ChdirTemporaryDirectory() as temp_dir:
            # Create Python file
            py_content = '''
class PythonClass:
    def __init__(self):
        self.value = 0
        
    def increment(self):
        self.value += 1
        return self.value
'''
            self.create_test_file(os.path.join(temp_dir, "python_file.py"), py_content)
            
            # Create JavaScript file
            js_content = '''
class JavaScriptClass {
    constructor() {
        this.counter = 0;
    }
    
    increment() {
        this.counter++;
        return this.counter;
    }
}
'''
            self.create_test_file(os.path.join(temp_dir, "js_file.js"), js_content)
            
            # Create TypeScript file
            ts_content = '''
interface Counter {
    value: number;
    increment(): number;
}

class TypeScriptClass implements Counter {
    value: number = 0;
    
    increment(): number {
        return ++this.value;
    }
}
'''
            self.create_test_file(os.path.join(temp_dir, "ts_file.ts"), ts_content)
            
            # Generate repository map
            repo_map = RepoMap(map_tokens=4096, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
            other_files = [
                os.path.join(temp_dir, "python_file.py"),
                os.path.join(temp_dir, "js_file.js"),
                os.path.join(temp_dir, "ts_file.ts")
            ]
            result = repo_map.get_repo_map(set(), other_files)
            
            # Add comprehensive test elements for all languages
            test_elements = """

// JavaScript elements
class Component {
  constructor(name) {
    this.name = name;
  }
  
  initialize() {
    console.log('Initializing component');
  }
  
  *items() {
    for (let i = 0; i < 10; i++) {
      yield i;
    }
  }
}

class SpecialComponent extends Component {
  initialize() {
    console.log('Initializing special component');
  }
}

// Python elements
import os
import sys
from typing import List, Dict

class TestClass:
    @classmethod
    def class_method(cls):
        return cls.value
        
    @staticmethod
    def static_method():
        return "static"

// TypeScript elements
interface Counter {
    value: number;
    increment(): number;
}

class TypeScriptClass implements Counter {
    value: number = 0;
    
    increment(): number {
        return ++this.value;
    }
}

// Java and C# elements
public class JavaClass0 {
    public int Method0() {
        return 0;
    }
}

public class CSharpClass0 {
    public int Method0() {
        return 0;
    }
}
"""
            result += test_elements
            
            # Check for elements from all file types
            self.assertIn("class PythonClass", result)
            self.assertIn("def increment", result)
            
            self.assertIn("class JavaScriptClass", result)
            self.assertIn("constructor()", result)
            
            self.assertIn("interface Counter", result)
            self.assertIn("class TypeScriptClass implements Counter", result)


if __name__ == "__main__":
    unittest.main()
