#!/usr/bin/env python3
"""
Demo script showing the capabilities of the Ollama Terminal Assistant
"""

import os
import sys
import subprocess

def run_command(cmd):
    """Run a command and return its output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1

def main():
    print("🤖 Ollama Terminal Assistant Demo")
    print("=" * 50)
    
    # Check if we're in the right directory
    script_dir = "/media/blu-bridge007/WET-FILES/rag_web_app/ollama_rag"
    if not os.path.exists(script_dir):
        print(f"❌ Error: Directory {script_dir} not found")
        return 1
    
    os.chdir(script_dir)
    print(f"Working in: {os.getcwd()}")
    
    # Check if Ollama is running
    print("\n1. Checking Ollama connection...")
    stdout, stderr, rc = run_command("curl -s http://127.0.0.1:11434/api/tags | head -1")
    if rc == 0 and '"models"' in stdout:
        print("   ✅ Ollama is running")
        # Show available models
        if '"gpt-oss:20b"' in stdout:
            print("   ✅ gpt-oss:20b model is available")
    else:
        print(f"   ❌ Ollama connection failed: {stderr}")
        return 1
    
    # Check if our assistant script exists
    print("\n2. Checking terminal assistant...")
    if os.path.exists("terminal_assistant_fixed.py"):
        print("   ✅ terminal_assistant_fixed.py found")
    else:
        print("   ❌ terminal_assistant_fixed.py not found")
        return 1
    
    # Create a demo file
    print("\n3. Creating demo file...")
    demo_file = "demo_calculator.py"
    with open(demo_file, "w") as f:
        f.write("""# Simple calculator
def add(a, b):
    return a + b

# TODO: Add subtract, multiply, divide functions
""")
    print(f"   ✅ Created {demo_file}")
    
    # Show the demo file
    print(f"\n   Content of {demo_file}:")
    with open(demo_file, "r") as f:
        for i, line in enumerate(f.readlines(), 1):
            print(f"   {i:2}: {line.rstrip()}")
    
    # Demonstrate the edit capability
    print("\n4. Demonstrating AI-powered editing...")
    print("   Instruction: 'Add subtract, multiply, and divide functions, and create a main menu'")
    
    # Import and use our edit function
    sys.path.append(".")
    from terminal_assistant_fixed import edit_file
    
    success = edit_file(demo_file, "Add subtract, multiply, and divide functions, and create a main menu that lets user choose operations")
    
    if success:
        print("   ✅ Edit successful!")
        print(f"\n   Updated content of {demo_file}:")
        with open(demo_file, "r") as f:
            for i, line in enumerate(f.readlines(), 1):
                print(f"   {i:2}: {line.rstrip()}")
    else:
        print("   ❌ Edit failed")
    
    # Demonstrate running the file
    print("\n5. Demonstrating code execution...")
    print("   Running the updated calculator...")
    stdout, stderr, rc = run_command(f"python3 {demo_file}")
    if stdout:
        print("   Output:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"     {line}")
    if stderr and "Error" not in stderr and "Traceback" not in stderr:
        print("   Info:")
        for line in stderr.split('\n'):
            if line.strip():
                print(f"     {line}")
    if rc == 0:
        print("   ✅ Execution completed")
    else:
        print(f"   ⚠️  Execution finished with return code {rc}")
    
    # Clean up
    print("\n6. Cleaning up...")
    try:
        os.remove(demo_file)
        print(f"   ✅ Removed {demo_file}")
    except:
        print(f"   ⚠️  Could not remove {demo_file}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\nTo use the terminal assistant manually:")
    print("   cd /media/blu-bridge007/WET-FILES/rag_web_app/ollama_rag")
    print("   python3 terminal_assistant_fixed.py")
    print("\nAvailable commands:")
    print("   edit <file> <instruction> - Edit file with AI assistance")
    print("   run <file> - Run a Python file")
    print("   chat - Enter interactive chat mode")
    print("   help - Show help")
    print("   exit/quit - Exit")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())