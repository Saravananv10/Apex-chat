#!/usr/bin/env python3
"""
Debug version of the terminal assistant
"""

import os
import sys
import json
import requests

# Ollama configuration
API_HOST = os.getenv("OLLAMA_API_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")

def stream_ollama_debug(messages):
    """Debug version of stream_ollama"""
    url = f"{API_HOST}/api/chat"
    headers = {"bypass-tunnel-reminder": "true"}
    body = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.3, "num_predict": 4096}
    }
    print(f"DEBUG: Sending request to {url}")
    print(f"DEBUG: Body: {json.dumps(body, indent=2)}")
    
    try:
        with requests.post(url, json=body, stream=True, timeout=30) as resp:
            print(f"DEBUG: Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"DEBUG: Error response: {resp.text}")
                yield json.dumps({"error": f"Ollama Error {resp.status_code}"}) + "\n"
                return
            
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    print(f"DEBUG: Received line: {line[:100]}...")
                if not line: 
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield json.dumps({"token": chunk}) + "\n"
                    if data.get("done"): 
                        break
                except Exception as e:
                    print(f"DEBUG: Error parsing line: {e}")
                    continue
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        yield json.dumps({"error": str(e)}) + "\n"

def get_ollama_response_debug(prompt: str, system_message: str = "You are a helpful assistant."):
    """Debug version of get_ollama_response"""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    print(f"DEBUG: Getting response for prompt: {prompt[:100]}...")
    full_response = ""
    for chunk_str in stream_ollama_debug(messages):
        try:
            data = json.loads(chunk_str)
            if "token" in data:
                token = data["token"]
                full_response += token
                print(f"DEBUG: Received token: {repr(token)}")
        except Exception as e:
            print(f"DEBUG: Error parsing chunk: {e}")
            print(f"DEBUG: Chunk content: {chunk_str}")
            pass
    print(f"DEBUG: Full response: {repr(full_response)}")
    return full_response

# Test the debug version
if __name__ == "__main__":
    print("Testing debug version...")
    response = get_ollama_response_debug("Say hello in one word", "You are a helpful assistant.")
    print(f"Final response: {response}")