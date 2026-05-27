#!/usr/bin/env python3
"""
Direct test of the edit function without the REPL
"""

import os
import sys
sys.path.append('/media/blu-bridge007/WET-FILES/rag_web_app/ollama_rag')

# Import the fixed version
from terminal_assistant_fixed import edit_file, get_ollama_response

# First test if we can get a response from Ollama
print("Testing Ollama connection...")
test_response = get_ollama_response("Say 'test'", "You are a helpful assistant.")
print(f"Ollama test response: '{test_response}'")

# Now test the edit function on a simple file
test_file_path = "/media/blu-bridge007/WET-FILES/rag_web_app/ollama_rag/simple_test.py"

# Create a simple test file
with open(test_file_path, "w") as f:
    f.write("# This is a test file\nprint('Hello')\n")

print(f"\nOriginal file content:")
with open(test_file_path, "r") as f:
    print(f.read())

# Now try to edit it
print("\nAttempting to edit file...")
result = edit_file(test_file_path, "Add a function that returns the sum of two numbers")
print(f"Edit result: {result}")

print(f"\nFile content after edit:")
with open(test_file_path, "r") as f:
    print(f.read())