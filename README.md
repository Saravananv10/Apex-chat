# Apex RAG: Local AI Assistant with Web Search

Apex RAG is a powerful, lightweight Retrieval-Augmented Generation (RAG) application. It combines the power of local LLMs (via Ollama) with real-time web search (via Tavily) and local document intelligence to provide a professional, Claude-like chat experience.

## 🚀 Features

- **Local Inference:** Powered by Ollama (defaulting to `gpt-oss:20b`).
- **Web-Augmented Answers:** Real-time search integration with Tavily API.
- **Document Intelligence:** Upload PDFs to chat with your local documents using ChromaDB.
- **Modern UI:** Responsive, dark-mode interface with professional Markdown and LaTeX rendering (KaTeX).
- **Persistent History:** SQLite-backed conversation management with chat renaming and deletion.
- **Streaming Responses:** Real-time token-by-token generation for a fluid chat experience.

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** Vanilla JS, Marked.js (Markdown), KaTeX (Math), Highlight.js (Code)
- **AI Orchestration:** LangChain
- **Vector Store:** ChromaDB
- **Embeddings:** HuggingFace Cloud-Lite (all-MiniLM-L6-v2)

## 📋 Prerequisites

- **Ollama:** [Install Ollama](https://ollama.com/) and run `ollama pull gpt-oss:20b` (or your preferred model).
- **Tavily API Key:** Required for web search. [Get one here](https://tavily.com/).
- **Python 3.10+**

## 🔧 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Saravananv10/Apex-chat
   cd ollama_rag
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (create a `.env` file):
   ```env
   TAVILY_API_KEY=your_key_here
   OLLAMA_MODEL=gpt-oss:20b
   ```

## 🏃 Running the Application

1. Start the backend:
   ```bash
   python3 app_local_llama.py
   ```

2. Access the interface:
   - Locally: `http://localhost:8080`
   - Via tunnel: Use LocalTunnel or Ngrok if deploying remotely.

## 📁 Project Structure

- `app_local_llama.py`: Main Flask application server.
- `index.html`: Optimized single-page frontend.
- `vector_db/`: Persistent storage for document embeddings.
- `history.db`: SQLite database for chat history and users.
- `archives/`: Legacy scripts and debugging tools.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
*Developed with ❤️ by the Apex AI Team.*
