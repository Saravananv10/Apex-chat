#!/usr/bin/env python3
"""
Simple test of the edit functionality
"""

import sys
sys.path.append('/media/blu-bridge007/WET-FILES/rag_web_app/ollama_rag')

from terminal_assistant import edit_file

# Test the edit function
print("Testing edit function...")
result = edit_file("test_file.py", "Add a function that multiplies two numbers and call it in the main section")
print(f"Edit result: {result}")

# Show the file content after edit
print("\nFile content after edit:")
with open("test_file.py", "r") as f:
    print(f.read())