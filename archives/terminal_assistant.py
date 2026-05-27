#!/usr/bin/env python3
"""
Terminal-based AI assistant for code editing and execution using local Ollama model.
"""

import os
import sys
import json
import subprocess
import threading
import time
from typing import List, Dict, Generator, Any

# Ollama configuration
API_HOST = os.getenv("OLLAMA_API_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")

def stream_ollama(messages: List[Dict]) -> Generator[str, None, None]:
    """Stream response from Local Ollama."""
    url = f"{API_HOST}/api/chat"
    headers = {"bypass-tunnel-reminder": "true"}
    body = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.3, "num_predict": 4096}
    }
    try:
        with requests.post(url, json=body, stream=True, timeout=300) as resp:
            if resp.status_code != 200:
                yield json.dumps({"error": f"Ollama Error {resp.status_code}"}) + "\n"
                return
            for line in resp.iter_lines(decode_unicode=True):
                if not line: continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield json.dumps({"token": chunk}) + "\n"
                    if data.get("done"): break
                except: continue
    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"

def get_ollama_response(prompt: str, system_message: str = "You are a helpful assistant.") -> str:
    """Get a complete response from Ollama (non-streaming)."""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    full_response = ""
    for chunk_str in stream_ollama(messages):
        try:
            data = json.loads(chunk_str)
            if "token" in data:
                full_response += data["token"]
        except:
            pass
    return full_response

def edit_file(file_path: str, instruction: str) -> bool:
    """Edit a file based on natural language instruction using AI."""
    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Construct prompt for editing
        edit_prompt = f"""You are an expert programmer. Edit the following file according to the instruction:
        
INSTRUCTION: {instruction}

FILE CONTENT:
{content}

Return ONLY the edited file content. Do not include any explanations, markdown formatting, or additional text.
If you cannot make the edit, return the original content unchanged."""
        
        # Get AI response
        system_msg = "You are an expert programmer focused on making precise code edits."
        edited_content = get_ollama_response(edit_prompt, system_msg)
        
        # Basic validation - check if response looks like code
        if len(edited_content.strip()) == 0:
            print("Error: AI returned empty response")
            return False
            
        # Write the edited content back to file
        with open(file_path, 'w') as f:
            f.write(edited_content)
        
        print(f"✅ Successfully edited {file_path}")
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: File {file_path} not found")
        return False
    except Exception as e:
        print(f"❌ Error editing file: {str(e)}")
        return False

def run_file(file_path: str) -> None:
    """Run a Python file and display output."""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ Error: File {file_path} not found")
            return
            
        # Run the file
        print(f"🚀 Running {file_path}...")
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Display output
        if result.stdout:
            print("📤 Output:")
            print(result.stdout)
        if result.stderr:
            print("📥 Errors:")
            print(result.stderr)
        if result.returncode != 0:
            print(f"⚠️  Process exited with code {result.returncode}")
        else:
            print("✅ Execution completed successfully")
            
    except subprocess.TimeoutExpired:
        print("⏰ Error: Execution timed out (30s limit)")
    except Exception as e:
        print(f"❌ Error running file: {str(e)}")

def chat_mode() -> None:
    """Interactive chat mode with the AI."""
    print("💬 Chat mode activated. Type 'exit' or 'quit' to return to main menu.")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                print("👋 Exiting chat mode")
                break
            if not user_input:
                continue
                
            print("AI: ", end="", flush=True)
            # Stream the response
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": user_input}
            ]
            
            for chunk_str in stream_ollama(messages):
                try:
                    data = json.loads(chunk_str)
                    if "token" in data:
                        print(data["token"], end="", flush=True)
                except:
                    pass
            print()  # New line after response
            
        except KeyboardInterrupt:
            print("\n👋 Exiting chat mode")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

def main() -> None:
    """Main REPL loop."""
    print("🤖 Ollama Terminal Assistant")
    print("=" * 40)
    print(f"Model: {MODEL}")
    print(f"API Host: {API_HOST}")
    print("=" * 40)
    print("Available commands:")
    print("  edit <file> <instruction> - Edit file with AI assistance")
    print("  run <file> - Run a Python file")
    print("  chat - Enter interactive chat mode")
    print("  help - Show this help")
    print("  exit/quit - Exit the program")
    print("=" * 40)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue
                
            parts = user_input.split()
            command = parts[0].lower()
            
            if command in ['exit', 'quit']:
                print("👋 Goodbye!")
                break
                
            elif command == 'help':
                print("\nAvailable commands:")
                print("  edit <file> <instruction> - Edit file with AI assistance")
                print("  run <file> - Run a Python file")
                print("  chat - Enter interactive chat mode")
                print("  help - Show this help")
                print("  exit/quit - Exit the program")
                
            elif command == 'edit':
                if len(parts) < 3:
                    print("❌ Usage: edit <file> <instruction>")
                    print("   Example: edit myfile.py \"Add a function to calculate factorial\"")
                    continue
                file_path = parts[1]
                instruction = " ".join(parts[2:])
                edit_file(file_path, instruction)
                
            elif command == 'run':
                if len(parts) < 2:
                    print("❌ Usage: run <file>")
                    print("   Example: run myfile.py")
                    continue
                file_path = parts[1]
                run_file(file_path)
                
            elif command == 'chat':
                chat_mode()
                
            else:
                print(f"❌ Unknown command: {command}")
                print("   Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    # Import requests here to avoid issues if not installed
    try:
        import requests
    except ImportError:
        print("❌ Error: 'requests' library not installed.")
        print("   Please install it with: pip install requests")
        sys.exit(1)
        
    main()