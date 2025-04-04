#!/usr/bin/env python3
"""
Performance tests for RepoMap
"""

import os
import sys
import time
import unittest
import tempfile
import shutil
from pathlib import Path

# Make sure we can import the main package
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap import RepoMap


class SimpleIO:
    """Simple IO class with performance tracking"""

    def __init__(self):
        self.warnings = []
        self.outputs = []
        self.errors = []
        self.file_reads = 0
        self.total_bytes_read = 0

    def tool_warning(self, message):
        self.warnings.append(message)

    def tool_output(self, message):
        self.outputs.append(message)

    def tool_error(self, message):
        self.errors.append(message)

    def read_text(self, fname):
        try:
            with open(fname, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                self.file_reads += 1
                self.total_bytes_read += len(content)
                return content
        except Exception as e:
            self.tool_error(f"Failed to read {fname}: {e}")
            return None

    def confirm_ask(self, message, default="y", subject=None):
        return True


class MockModel:
    """Mock model for token counting with performance metrics"""

    def __init__(self):
        self.tokens_counted = 0
        self.token_requests = 0

    def token_count(self, text):
        """Simple token count estimate: 1 token per 4 characters"""
        tokens = len(text) // 4
        self.tokens_counted += tokens
        self.token_requests += 1
        return tokens


class TestPerformance(unittest.TestCase):
    """Performance tests for RepoMap"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for the test repository
        self.repo_dir = tempfile.mkdtemp()

        # Create a deeper directory structure with many files
        self.create_test_repo(self.repo_dir)

        self.io = SimpleIO()
        self.model = MockModel()

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'repo_dir') and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)

    def create_test_repo(self, base_dir):
        """Create a test repository with a realistic structure and many files"""
        # Create a nested structure
        # project/
        #   src/
        #     main/
        #       java/
        #         com/
        #           example/
        #             Main.java, Utils.java, ...
        #     test/
        #       java/
        #         com/
        #           example/
        #             MainTest.java, ...
        #   docs/
        #     index.md, api.md, ...
        #   scripts/
        #     build.sh, deploy.sh, ...
        #   README.md, pom.xml, ...

        # Create main structure
        dirs = [
            "src/main/java/com/example",
            "src/main/resources",
            "src/test/java/com/example",
            "src/test/resources",
            "docs",
            "scripts",
            "config",
        ]

        for d in dirs:
            os.makedirs(os.path.join(base_dir, d), exist_ok=True)

        # Create Java source files
        java_src_dir = os.path.join(base_dir, "src/main/java/com/example")
        java_classes = [
            "Main", "Utils", "Config", "Logger", "Database",
            "ApiClient", "UserService", "ProductService", "SecurityManager",
            "FileHandler", "JsonParser", "XmlParser", "CsvParser",
            "HttpClient", "WebSocket", "Cache", "MemoryCache", "DiskCache",
            "Validator", "StringUtils", "DateUtils", "NumberUtils",
            "Encryption", "Compression", "ImageProcessor", "AudioProcessor",
            "EventBus", "MessageQueue", "ThreadPool", "TaskScheduler",
            "DataSource", "Connection", "Transaction", "QueryBuilder",
        ]

        # Create Java files with realistic content
        for cls in java_classes:
            with open(os.path.join(java_src_dir, f"{cls}.java"), "w") as f:
                f.write(f"""package com.example;

/**
 * {cls} class for handling {cls.lower()} functionality
 */
public class {cls} {{
    private String name;
    private int id;

    /**
     * Constructor
     */
    public {cls}(String name, int id) {{
        this.name = name;
        this.id = id;
    }}

    /**
     * Get name
     */
    public String getName() {{
        return name;
    }}

    /**
     * Set name
     */
    public void setName(String name) {{
        this.name = name;
    }}

    /**
     * Get ID
     */
    public int getId() {{
        return id;
    }}

    /**
     * Set ID
     */
    public void setId(int id) {{
        this.id = id;
    }}

    /**
     * Process data
     */
    public void process(String data) {{
        System.out.println("Processing: " + data);
    }}

    /**
     * Main method for testing
     */
    public static void main(String[] args) {{
        {cls} instance = new {cls}("Test", 123);
        instance.process("Sample data");
    }}
}}
""")

        # Create test files
        java_test_dir = os.path.join(base_dir, "src/test/java/com/example")
        for cls in java_classes[:10]:  # Only create tests for the first 10 classes
            with open(os.path.join(java_test_dir, f"{cls}Test.java"), "w") as f:
                f.write(f"""package com.example;

import org.junit.Test;
import static org.junit.Assert.*;

/**
 * Test for {cls}
 */
public class {cls}Test {{

    @Test
    public void testConstructor() {{
        {cls} instance = new {cls}("Test", 123);
        assertEquals("Test", instance.getName());
        assertEquals(123, instance.getId());
    }}

    @Test
    public void testSetName() {{
        {cls} instance = new {cls}("Test", 123);
        instance.setName("New Name");
        assertEquals("New Name", instance.getName());
    }}

    @Test
    public void testSetId() {{
        {cls} instance = new {cls}("Test", 123);
        instance.setId(456);
        assertEquals(456, instance.getId());
    }}
}}
""")

        # Create configuration files
        config_dir = os.path.join(base_dir, "config")
        config_files = ["application.properties", "log4j.properties", "database.properties"]
        for cfg in config_files:
            with open(os.path.join(config_dir, cfg), "w") as f:
                f.write(f"""# {cfg.split('.')[0]} Configuration
app.name=TestApp
app.version=1.0.0
log.level=INFO
debug.mode=false
database.url=jdbc:mysql://localhost:3306/testdb
database.username=testuser
database.password=testpass
""")

        # Create documentation
        docs_dir = os.path.join(base_dir, "docs")
        doc_files = ["index.md", "api.md", "configuration.md", "deployment.md"]
        for doc in doc_files:
            with open(os.path.join(docs_dir, doc), "w") as f:
                f.write(f"""# {doc.split('.')[0].title()} Documentation

## Overview

This is the {doc.split('.')[0]} documentation for the sample project.

## Usage

```java
import com.example.Main;

public class Example {{
    public static void main(String[] args) {{
        Main.main(args);
    }}
}}
```

## Configuration

See [configuration.md](configuration.md) for details.

## API Reference

See [api.md](api.md) for the complete API reference.
""")

        # Create build and deployment scripts
        scripts_dir = os.path.join(base_dir, "scripts")
        script_files = ["build.sh", "deploy.sh", "clean.sh", "test.sh"]
        for script in script_files:
            with open(os.path.join(scripts_dir, script), "w") as f:
                f.write(f"""#!/bin/bash

# {script.split('.')[0].title()} script

echo "Running {script.split('.')[0]}..."

# Set variables
PROJECT_DIR=$(pwd)
SRC_DIR="$PROJECT_DIR/src"
TARGET_DIR="$PROJECT_DIR/target"

# Create target directory if it doesn't exist
mkdir -p $TARGET_DIR

# Perform {script.split('.')[0]} operation
echo "Completed {script.split('.')[0]}"
""")

        # Create root files
        with open(os.path.join(base_dir, "README.md"), "w") as f:
            f.write("""# Sample Project

A sample project for testing RepoMap performance.

## Overview

This project contains a sample Java application with the following structure:
- src/main/java: Java source files
- src/test/java: Java test files
- docs: Documentation
- scripts: Build and deployment scripts
- config: Configuration files

## Building

```bash
./scripts/build.sh
```

## Testing

```bash
./scripts/test.sh
```

## Deployment

```bash
./scripts/deploy.sh
```
""")

        with open(os.path.join(base_dir, "pom.xml"), "w") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>sample-project</artifactId>
    <version>1.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>

    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
""")

    def test_performance_large_repo(self):
        """Test performance on a large repository"""
        # Count the files in our test repo
        file_count = 0
        for root, _, files in os.walk(self.repo_dir):
            file_count += len(files)

        self.assertGreater(file_count, 30, "Test repository should have at least 30 files")

        # Initialize RepoMap
        rm = RepoMap(
            root=self.repo_dir,
            io=self.io,
            main_model=self.model,
            verbose=True
        )

        # Find all files
        all_files = []
        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                all_files.append(os.path.join(root, file))

        # Measure time to generate map
        start_time = time.time()
        repo_map = rm.get_ranked_tags_map_uncached(all_files, [])
        end_time = time.time()

        duration = end_time - start_time

        # Verify the map was generated
        self.assertIsNotNone(repo_map)

        # Log performance metrics
        print("\nPerformance test results:")
        print(f"Files processed: {file_count}")
        print(f"Time taken: {duration:.2f} seconds")
        print(f"Files per second: {file_count / duration:.2f}")
        print(f"File reads: {self.io.file_reads}")
        print(f"Total bytes read: {self.io.total_bytes_read}")
        print(f"Token requests: {self.model.token_requests}")
        print(f"Tokens counted: {self.model.tokens_counted}")

        # Verify the map contains expected elements
        self.assertIn("Main.java", repo_map)
        self.assertIn("pom.xml", repo_map)
        self.assertIn("README.md", repo_map)

    def test_cache_performance(self):
        """Test the performance impact of caching"""
        # Find java files
        java_files = []
        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(os.path.join(root, file))

        # Initialize RepoMap
        rm = RepoMap(
            root=self.repo_dir,
            io=self.io,
            main_model=self.model,
            verbose=True
        )

        # First run (cold cache)
        first_io = SimpleIO()
        first_model = MockModel()
        rm.io = first_io
        rm.main_model = first_model

        start_time = time.time()
        repo_map1 = rm.get_ranked_tags_map(java_files, [])
        first_duration = time.time() - start_time

        # Second run (warm cache)
        second_io = SimpleIO()
        second_model = MockModel()
        rm.io = second_io
        rm.main_model = second_model

        start_time = time.time()
        repo_map2 = rm.get_ranked_tags_map(java_files, [])
        second_duration = time.time() - start_time

        # Log cache performance
        print("\nCache performance test results:")
        print(f"Files processed: {len(java_files)}")
        print(f"First run (cold cache): {first_duration:.2f} seconds")
        print(f"Second run (warm cache): {second_duration:.2f} seconds")
        print(f"Speed improvement: {first_duration / second_duration:.2f}x")
        print(f"First run file reads: {first_io.file_reads}")
        print(f"Second run file reads: {second_io.file_reads}")

        # The second run should generally be faster due to caching
        # But we can't assert this as it's not guaranteed in all environments
        # self.assertLess(second_duration, first_duration)

        # Both runs should produce similar results
        self.assertEqual(bool(repo_map1), bool(repo_map2))


if __name__ == '__main__':
    unittest.main()
