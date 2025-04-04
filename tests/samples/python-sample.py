#!/usr/bin/env python3
"""
Sample Python file for testing RepoMap
"""

import os
import sys
from pathlib import Path


class SampleClass:
    """A sample class for demonstration"""

    def __init__(self, name):
        self.name = name
        self.data = {}

    def process(self, input_data):
        """Process the input data"""
        result = self._transform(input_data)
        self.data[input_data] = result
        return result

    def _transform(self, data):
        """Internal transformation method"""
        return data.upper() if isinstance(data, str) else data


def main():
    """Main function"""
    sample = SampleClass("Test")
    result = sample.process("hello world")
    print(f"Processed: {result}")

    values = calculate_values(10)
    print(f"Values: {values}")


def calculate_values(count):
    """Calculate a list of values"""
    return [i * i for i in range(count)]


if __name__ == "__main__":
    main()
