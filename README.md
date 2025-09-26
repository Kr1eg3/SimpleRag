# SimpleRAG - Hybrid Go MCP + Python RAG System

A hybrid architecture combining Go MCP (Model Context Protocol) server with Python RAG (Retrieval-Augmented Generation) HTTP API for intelligent document search and context management.

## 🏗️ Architecture

```
Claude Code ←→ Go MCP Server ←→ Python RAG HTTP API ←→ ChromaDB
            (Port 8009)      (Port 8008)
```

## ✨ Features

- **Hybrid Architecture**: Go for fast MCP protocol handling, Python for ML/RAG processing
- **Smart Session Management**: Tracks user sessions and avoids duplicate content
- **PDF Document Support**: Index and search PDF files with vector embeddings
- **Claude Agent Integration**: No API keys required - uses Claude directly
- **HTTP/SSE Transport**: Remote MCP connection support
- **ChromaDB Vector Storage**: Efficient similarity search with embeddings

## 🚀 Quick Start

### Prerequisites

- Go 1.19+
- Python 3.12+
- Claude Code CLI

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install fastapi uvicorn chromadb langchain langchain-anthropic sentence-transformers pypdf python-dotenv
```

### 2. Start Python RAG API

```bash
python rag_http_server.py --host 127.0.0.1 --port 8008
```

### 3. Build and Start Go MCP Server

**Option A: Using Makefile (Recommended)**
```bash
make build    # Build binary
make run      # Build and run server
```

**Option B: Manual Build**
```bash
cd server && go build -o ../simplerag-mcp.exe .
./simplerag-mcp.exe
```

### 4. Connect to Claude Code

```bash
claude mcp add -t http go-mcp http://127.0.0.1:8009/sse
```

## 📁 Project Structure

```
SimpleRag/
├── server/                    # Go MCP server
│   ├── main.go               # Main server application
│   ├── oauth.go              # OAuth handling
│   └── session_manager.go    # Session management logic
├── rag/                      # Python RAG modules
│   ├── database/             # Database components
│   │   └── builder.py        # Database builder
│   ├── retrieval/            # Retrieval components
│   │   └── retriever.py      # Document retriever
│   └── rag_manager.py        # Main RAG manager
├── rag_http_server.py         # Python RAG HTTP API
├── main.py                   # Legacy main application
├── mcp_fastmcp_claude_agent.py # FastMCP Claude agent
├── Makefile                   # Build automation
├── requirements.txt           # Python dependencies
├── go.mod, go.sum            # Go dependencies
├── data/                     # Documents for indexing
├── rag_data/                 # ChromaDB storage
├── sessions.db               # Session database
├── examples/                 # Example files
├── minds/                    # Mind models
└── build/                    # Build artifacts
```

## 🛠️ Available MCP Tools

- **`initialize_rag`** - Initialize RAG system with documents
- **`search_documents`** - Vector search in documents
- **`query_with_claude_agent`** - Smart search with context preparation
- **`get_system_status`** - Check system health
- **`session_management`** - Manage user sessions

## 📖 Usage Examples

### Initialize with Documents
```python
# Add documents to ./data/ folder
# Then initialize
await initialize_rag(data_path="./data", load_existing=False)
```

### Search Documents
```python
results = await search_documents(query="LCEVC upsampler", k=5)
```

### Smart Query with Session
```python
context = await query_with_claude_agent(
    question="Explain L-1 filter",
    k=3,
    session_id="user123",
    use_history=True
)
```

## 🔨 Make Commands

The project includes a comprehensive Makefile for easy development and deployment:

### Build Commands
```bash
make build          # Build for current platform
make build-windows  # Build for Windows x64
make build-linux    # Build for Linux x64
make build-macos    # Build for macOS (x64 + ARM64)
make build-all      # Build for all platforms
make release        # Optimized release build
```

### Development Commands
```bash
make dev-setup      # Setup development environment
make dev-start      # Start both Python and Go servers
make dev-stop       # Stop development servers
make run            # Build and run Go server
```

### Quality Commands
```bash
make test           # Run tests
make test-race      # Run tests with race detection
make fmt            # Format code
make lint           # Lint code (requires golangci-lint)
make vet            # Vet code
make check          # Run all quality checks
```

### Utility Commands
```bash
make deps           # Install dependencies
make clean          # Clean build artifacts
make info           # Show build information
make help           # Show all available commands
```

## ⚙️ Configuration

### Environment Variables
```env
PYTHON_RAG_URL=http://127.0.0.1:8008
GO_MCP_HOST=127.0.0.1
GO_MCP_PORT=8009
```

### RAG Parameters
- **Chunk size**: 1000 characters
- **Chunk overlap**: 200 characters
- **Max sessions**: 100
- **Session TTL**: 24 hours

## 🧠 Session Management

The system includes intelligent session management:
- **Deduplication**: Avoids showing same content repeatedly
- **Context History**: Maintains conversation context
- **Smart Filtering**: Shows only new relevant information
- **Session Persistence**: 24-hour session lifetime

## 🐛 Troubleshooting

### Common Issues

1. **Connection refused**
   - Ensure both servers are running
   - Check port availability (8008, 8009)

2. **No search results**
   - Run `initialize_rag` first
   - Check if documents are in `./data` folder

3. **MCP connection failed**
   - Verify Claude Code version
   - Check endpoint: `http://127.0.0.1:8009/sse`

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 🔗 Related Projects

- [Claude Code](https://claude.ai/code) - AI-powered development environment
- [Model Context Protocol](https://modelcontextprotocol.io/) - Standard for AI-application integration
- [FastMCP](https://github.com/jlowin/fastmcp) - Fast MCP server implementation
- [ChromaDB](https://www.trychroma.com/) - Vector database for embeddings
- [LangChain](https://langchain.com/) - Framework for LLM applications
- [Anthropic API](https://www.anthropic.com/) - Claude AI API

---

**Status**: ✅ Ready for production use
**Last Updated**: September 2025