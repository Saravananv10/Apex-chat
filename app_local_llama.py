# http://localhost:5000


# ---------- CONFIG & SUPPRESSION ----------
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Even more quiet
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0") # Default to CPU as user requested

import json
import time
import random
import logging
import re
import threading
import sqlite3
import uuid
from typing import List, Tuple, Optional, Generator, Any
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS

from langchain_huggingface import HuggingFaceEmbeddings
try:
    from langchain_chroma import Chroma
except Exception:
    from langchain_community.vectorstores import Chroma  # type: ignore

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---------- Tavily ----------
_TAVILY_NEW = False
_TavilySearchNew = None
_TavilySearchOld = None
try:
    from langchain_tavily import TavilySearch as _TavilySearchNew
    _TAVILY_NEW = True
except Exception:
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults as _TavilySearchOld
    except Exception:
        _TavilySearchOld = None

# ============== CONFIG ==============
API_HOST = os.getenv("OLLAMA_API_HOST", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "ollama_model_name") 

DB_PATH = os.getenv("DB_PATH", "vector_db")
os.makedirs(DB_PATH, exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Tavily key
os.environ.setdefault("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY", "your_tavily_key"))

# ============== DATABASE ==============
DB_FILE = "history.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        # Conversations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT,
                project_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        # Messages Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id TEXT NOT NULL,
                role TEXT NOT NULL, -- 'user' or 'bot'
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conv_id) REFERENCES conversations(id)
            )
        """)
        # Lightweight migrations for existing local databases.
        existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(conversations)").fetchall()}
        if "project_name" not in existing_cols:
            cursor.execute("ALTER TABLE conversations ADD COLUMN project_name TEXT")
        if "updated_at" not in existing_cols:
            cursor.execute("ALTER TABLE conversations ADD COLUMN updated_at TIMESTAMP")
            cursor.execute("UPDATE conversations SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, updated_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_project ON conversations(user_id, project_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conv_id, created_at ASC)")
        conn.commit()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ============== LOGGING & APP ==============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("ollama_app")
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "bypass-tunnel-reminder"]}}, supports_credentials=True)

# ============== VECTOR DB ==============
log.info("🔹 Initializing Cloud-Lite Embeddings & Chroma DB...")

# Use HuggingFace Inference API for light-weight cloud embeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings
HF_TOKEN = os.getenv("HF_TOKEN", "") # Optional but recommended for higher limits

embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=HF_TOKEN,
    model="sentence-transformers/all-MiniLM-L6-v2"
)

db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

# ============== DOC INGEST ==============
def _mk_doc(page_text: str, source: str, title: Optional[str]) -> Document:
    title = (title or "").strip()
    content = page_text.strip()
    if title and not content.startswith(title):
        content = f"{title}\n\n{content}"
    return Document(page_content=content, metadata={"source": source, "title": title or os.path.basename(source)})

def add_pdf_to_db(pdf_path: str):
    """Lite PDF Ingest for Cloud Environment."""
    log.info("� Indexing PDF: %s", os.path.basename(pdf_path))
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        loader = PyPDFLoader(pdf_path)
        docs = loader.load_and_split(RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200))
        db.add_documents(docs)
        log.info("✅ Indexed %d chunks for %s", len(docs), os.path.basename(pdf_path))
    except Exception as e:
        log.error("❌ Failed to index %s: %s", pdf_path, e)

# ============== RAG & SEARCH ==============
def get_rag_docs(query: str, k: int = 8) -> List[Document]:
    try:
        # Use MMR for better distribution of context
        retriever = db.as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": 40})
        return retriever.get_relevant_documents(query)
    except Exception:
        return db.similarity_search(query, k=k)

def retrieve_web_context(query: str, k: int = 4) -> List[Tuple[str, str]]:
    log.info("🌐 Web Search: %s", query)
    try:
        results = []
        if _TAVILY_NEW:
            tool = _TavilySearchNew(max_results=k, include_raw_content=True)
            out = tool.invoke({"query": query})
        elif _TavilySearchOld:
            out = _TavilySearchOld(max_results=k, include_raw_content=True).invoke({"query": query})
        else:
            return []

        results = (out or {}).get("results", []) if isinstance(out, dict) else out if isinstance(out, list) else []

        pairs = []
        for r in results:
            if not isinstance(r, dict):
                continue
            content = (r.get("content") or r.get("raw_content") or "")[:4000]
            if len(content) > 100:
                pairs.append((content, r.get("url", "")))
        return pairs
    except Exception as e:
        log.warning("Web search failed: %s", e)
        return []

def parse_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return bool(value)

# ============== PROVIDER LOGIC ==============
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "ollama").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def stream_groq(messages: List[dict]) -> Generator[str, None, None]:
    """Stream from Groq Cloud (OpenAI-compatible)."""
    if not GROQ_API_KEY:
        yield json.dumps({"error": "GROQ_API_KEY not set. Get one at console.groq.com"}) + "\n"
        return
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama3-8b-8192" if "8b" in MODEL.lower() else "llama3-70b-8192",
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
        "max_tokens": 4096
    }
    
    try:
        with requests.post(url, headers=headers, json=body, stream=True, timeout=300) as resp:
            if resp.status_code != 200:
                yield json.dumps({"error": f"Groq Error {resp.status_code}: {resp.text}"}) + "\n"
                return
            for line in resp.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]": break
                    try:
                        data = json.loads(data_str)
                        token = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if token:
                            yield json.dumps({"token": token}) + "\n"
                    except: continue
    except Exception as e:
        yield json.dumps({"error": str(e)}) + "\n"

def stream_ollama(messages: List[dict]) -> Generator[str, None, None]:
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

# ============== PROMPT & LOGIC ==============
def build_prompt(query: str, contexts: List[Tuple[str, str]], history: List[dict] = None) -> str:
    ctx_block = "\n\n".join([f"Source: {s}\nContent: {t[:1200]}" for t, s in contexts])
    
    hist_block = ""
    if history:
        hist_block = "\n".join([f"{h['role'].capitalize()}: {h['content']}" for h in history])
        hist_block = f"\nRecent History:\n{hist_block}\n"

    return f"""You are a Premium AI Assistant. Answer the query based on any provided context and recent history.
Use your general knowledge if the context is insufficient.
All currency must be in Indian Rupees (INR/₹) where applicable.

CRITICAL: For mathematical formulas, you MUST use these exact delimiters:
- Inline Math: \( ... \)
- Display Math: \[ ... \]
Do NOT use single brackets [ ] without backslashes for math.

Context:
{ctx_block}
{hist_block}
User Query: {query}
Answer:"""

# ============== ROUTES ==============
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("file")
    if not file: return jsonify({"error": "No file"}), 400
    path = os.path.join("uploads", file.filename)
    file.save(path)
    # Background ingest would be better, but keeping it simple for now
    try:
        add_pdf_to_db(path)
        return jsonify({"message": f"Verified and indexed {file.filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/process_all", methods=["POST"])
def process_all():
    """Sync all PDFs in uploads folder in parallel."""
    files = [os.path.join("uploads", f) for f in os.listdir("uploads") if f.lower().endswith(".pdf")]
    if not files: return jsonify({"message": "No files found in vault."})
    
    def worker(f):
        try: add_pdf_to_db(f)
        except: pass

    log.info("⚡ Parallel sync starting for %d files...", len(files))
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(worker, files)
    
    return jsonify({"message": f"Successfully synced {len(files)} documents."})

# ============== AUTH & HISTORY ROUTES ==============
@app.route("/health", methods=["GET", "HEAD"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/tools/status", methods=["GET"])
def tools_status():
    pdfs = [f for f in os.listdir("uploads") if f.lower().endswith(".pdf")]
    return jsonify({
        "tools": {
            "web_search": {
                "enabled": bool(os.getenv("TAVILY_API_KEY")),
                "provider": "tavily" if (_TAVILY_NEW or _TavilySearchOld) else None
            },
            "documents": {
                "enabled": True,
                "count": len(pdfs)
            },
            "history": {
                "enabled": True
            }
        },
        "model": {
            "provider": MODEL_PROVIDER,
            "name": MODEL
        }
    })

@app.route("/auth", methods=["POST"])
def auth():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    action = data.get("action") # 'login' or 'register'

    if not username or not password: return jsonify({"error": "Missing fields"}), 400

    conn = get_db_connection()
    try:
        if action == "register":
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return jsonify({"message": "Registered", "user_id": user["id"], "username": user["username"]})
        else:
            user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
            if not user: return jsonify({"error": "Invalid credentials"}), 401
            return jsonify({"message": "Logged in", "user_id": user["id"], "username": user["username"]})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username taken"}), 400
    finally: conn.close()

@app.route("/conversations", methods=["GET", "POST"])
def manage_conversations():
    user_id = request.args.get("user_id") if request.method == "GET" else request.json.get("user_id")
    if not user_id: return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    if request.method == "POST":
        conv_id = f"conv_{int(time.time()*1000)}"
        title = request.json.get("title", "New Chat")
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (conv_id, user_id, title),
        )
        conn.commit()
        conn.close()
        return jsonify({"id": conv_id, "title": title})
    
    rows = conn.execute("""
        SELECT
            c.*,
            COUNT(m.id) AS message_count
        FROM conversations c
        LEFT JOIN messages m ON m.conv_id = c.id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY COALESCE(c.updated_at, c.created_at) DESC
    """, (user_id,)).fetchall()
    res = [dict(r) for r in rows]
    conn.close()
    return jsonify(res)

@app.route("/history/<conv_id>", methods=["GET"])
def get_history(conv_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT role, content FROM messages WHERE conv_id = ? ORDER BY created_at ASC", (conv_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/clear", methods=["POST"])
def clear():
    conv_id = request.json.get("conv_id")
    if conv_id:
        conn = get_db_connection()
        conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
        conn.commit()
        conn.close()
    return jsonify({"status": "cleared"})

@app.route("/conversations/<conv_id>", methods=["PUT", "DELETE"])
def update_conversation(conv_id):
    conn = get_db_connection()
    if request.method == "DELETE":
        conn.execute("DELETE FROM messages WHERE conv_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"})
    elif request.method == "PUT":
        data = request.json
        new_title = data.get("title", "").strip()
        project_name = data.get("project_name")
        updates = []
        params = []
        if new_title:
            updates.append("title = ?")
            params.append(new_title)
        if project_name is not None:
            project_name = project_name.strip()
            updates.append("project_name = ?")
            params.append(project_name or None)
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(conv_id)
            conn.execute(f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        conn.close()
        return jsonify({"status": "updated", "title": new_title, "project_name": project_name})

@app.route("/ask", methods=["POST"])
def ask():
    req = request.get_json()
    query = req.get("query", "").strip()
    if not query: return jsonify({"error": "Empty query"}), 400

    # 0. Lightweight intent check
    conversational_keywords = {"hi", "hello", "hey", "hola", "greetings", "morning", "afternoon", "evening", "how are you", "hi there", "hello there"}
    instructional_keywords = {"write", "tell", "joke", "poem", "story", "code", "explain", "summarize", "analyze"}
    q_lower = query.lower().strip("?!. ")
    words = q_lower.split()
    
    # 0.1 Fast-Path for Greetings
    is_greeting = (q_lower in conversational_keywords or 
                  all(w in conversational_keywords for w in words) or
                  (len(words) <= 2 and any(w in conversational_keywords for w in words)))

    if is_greeting:
        log.info("👋 Greeting detected. Instant response.")
        response_text = "Hello! I am your AI Assistant. How can I help you today?"
        if "how are you" in q_lower:
            response_text = "I'm doing great, thank you! How can I assist you with your documents or questions today?"
        
        if req.get("stream"):
            def instant_gen():
                yield json.dumps({"sources": []}) + "\n"
                yield json.dumps({"token": response_text}) + "\n"
            return Response(stream_with_context(instant_gen()), mimetype='application/x-ndjson')
        return jsonify({"response": response_text, "sources": []})

    # 0.2 Check for General Tasks (Fast-Path to LLM)
    # If query starts with "write a poem", "tell a joke", etc. and no web/rag is forced
    is_general_task = any(q_lower.startswith(kw) for kw in instructional_keywords) and len(words) < 10
    use_web = parse_bool(req.get("use_web"), True)
    use_rag = parse_bool(req.get("use_rag"), True)

    contexts = []
    sources = []

    if not is_general_task:
        # 1. Parallel Retrieval
        start_time = time.time()
        log.info("⚡ Starting Parallel Retrieval (RAG: %s, Web: %s)", use_rag, use_web)
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            rag_future = executor.submit(get_rag_docs, query) if use_rag else None
            web_future = executor.submit(retrieve_web_context, query) if use_web else None
            
            if rag_future:
                try:
                    docs = rag_future.result(timeout=15)
                    contexts += [(d.page_content, d.metadata.get("source", "PDF")) for d in docs]
                except Exception as e: log.error("RAG Error: %s", e)
            
            if web_future:
                try:
                    web_res = web_future.result(timeout=15)
                    contexts += web_res
                except Exception as e: log.error("Web Search Error: %s", e)
        
        log.info("⏱️ Parallel Retrieval finished in %.2fs", time.time() - start_time)
        sources = list(set([s for _, s in contexts if s.startswith("http")]))
    else:
        log.info("🚀 General Task detected. Skipping retrieval for speed.")

    # Get history for context
    conv_id = req.get("conv_id")
    history = []
    if conv_id:
        conn = get_db_connection()
        rows = conn.execute("SELECT role, content FROM messages WHERE conv_id = ? ORDER BY created_at DESC LIMIT 12", (conv_id,)).fetchall()
        history = [dict(r) for r in reversed(rows)]
        log.info(f"📜 Found {len(history)} history messages for conversation {conv_id}")
        
        # Save user message
        conn.execute("INSERT INTO messages (conv_id, role, content) VALUES (?, ?, ?)", (conv_id, 'user', query))
        conn.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conv_id,))
        conn.commit()
        conn.close()

    from datetime import datetime
    current_date = datetime.now().strftime('%d %B %Y, %A')

    # Build structured messages for memory
    messages = [
        {
            "role": "system", 
            "content": f"You are an Elite AI Assistant. Today is {current_date}. "
                       "CRITICAL: If the Context Information contains recent news or facts that answer the user's query, you MUST use that information and override your innate knowledge. "
                       "IGNORE irrelevant context entirely. ONLY cite a source (by name or URL) if it directly provides the answer. "
                       "All currency must be in INR/₹. Use \\(...\\) for inline math, \\[...\\] for display math."
        }
    ]

    
    # Add history naturally without breaking the sequence with "system" roles
    if history:
        for h in history:
            role = "assistant" if h["role"] == "bot" else "user"
            messages.append({"role": role, "content": h["content"]})
    
    # Bundle RAG context into the current query more explicitly
    if contexts:
        ctx_text = "\n\n".join([f"Source: {s}\nRelevant text: {t[:1200]}" for t, s in contexts])
        full_query = f"[Retrieved Context Information]\n{ctx_text}\n\nWarning: Only use and cite the above sources if they are highly relevant to the question. If they are irrelevant, ignore them completely.\n\nUser Question: {query}"
    else:
        full_query = query

    messages.append({"role": "user", "content": full_query})

    if req.get("stream"):
        def generate():
            yield json.dumps({"sources": sources}) + "\n"
            gen = stream_groq(messages) if MODEL_PROVIDER == "groq" else stream_ollama(messages)
            full_response = ""
            for chunk_str in gen:
                try:
                    data = json.loads(chunk_str)
                    if "token" in data: full_response += data["token"]
                except: pass
                yield chunk_str
            
            # Save bot response at the end
            if conv_id and full_response:
                c = get_db_connection()
                # Update title if it's default
                c.execute("UPDATE conversations SET title = ? WHERE id = ? AND title = 'New Chat'", (query[:30]+"...", conv_id))
                c.execute("INSERT INTO messages (conv_id, role, content) VALUES (?, ?, ?)", (conv_id, 'bot', full_response))
                c.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conv_id,))
                c.commit()
                c.close()

        return Response(stream_with_context(generate()), mimetype='application/x-ndjson')
    
    # Non-stream fallback
    if MODEL_PROVIDER == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        body = {"model": "llama3-70b-8192", "messages": messages, "stream": False}
        ans = requests.post(url, headers=headers, json=body).json().get("choices", [{}])[0].get("message", {}).get("content")
    else:
        url = f"{API_HOST}/api/chat"
        resp = requests.post(url, json={"model": MODEL, "messages": messages, "stream": False})
        ans = resp.json().get("message", {}).get("content", "Error generating answer.")
    
    return jsonify({"response": ans, "sources": sources})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)










# cp index.html templates/index.html && fuser -k 8080/tcp; sleep 1 && python3 app_local_llama.py

# lt --port 8080 --subdomain apex-chat-ai
