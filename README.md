# SimpleRAG - Hybrid Go MCP + Python RAG System

**This readme file was created by Claude Code, it is not optimized and may be reworked.**
**OAuth currently doesn't work directly from Claude Code; this functionality has been removed in the new version of the VSCode extension. Use the X-User-ID header for sessions.**
```
claude mcp add -t http go-mcp http://127.0.0.1:8009/sse --header "X-User-ID: user"
```

A production-ready hybrid architecture combining Go MCP (Model Context Protocol) server with Python RAG (Retrieval-Augmented Generation) HTTP API for intelligent document search, OAuth 2.1 authentication, and smart context management.

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌──────────────────┐
│ Claude Code │ ◄─SSE──►│ Go MCP Server    │ ◄─HTTP─►│ Python RAG API   │
│   (Client)  │         │   Port: 8009     │         │   Port: 8008     │
└─────────────┘         │ • OAuth 2.1      │         │ • Vector Search  │
                        │ • Session Mgmt   │         │ • Embeddings     │
                        │ • Deduplication  │         │ • Document Load  │
                        └────────┬─────────┘         └────────┬─────────┘
                                 │                            │
                        ┌────────▼─────────┐         ┌────────▼─────────┐
                        │   SQLite DB      │         │    ChromaDB      │
                        │ • user_chunks    │         │ • Vector Store   │
                        │ • search_logs    │         │ • Embeddings     │
                        └──────────────────┘         └──────────────────┘
```

## ✨ Features

### Core Features
- **🏗️ Hybrid Architecture**: Go for fast MCP protocol handling, Python for ML/RAG processing
- **🔐 OAuth 2.1 Authentication**: Full MCP-compliant OAuth implementation with PKCE
- **🧠 Smart Session Management**: Per-user chunk deduplication and context tracking
- **📄 Multi-Format Support**: Index and search txt, pdf, csv, and markdown files
- **🔍 Vector Search**: ChromaDB with HuggingFace embeddings (all-MiniLM-L6-v2)
- **📊 Search Logging**: Complete audit trail of all searches and responses
- **🚀 HTTP/SSE Transport**: Remote MCP connection support

### Advanced Features
- **Chunk Deduplication**: Automatically filters out previously shown content per user
- **Search History**: Full logging of queries, RAG responses, and MCP responses
- **Auto-Initialization**: Python server auto-loads existing database on startup
- **Session Statistics**: Track unique users, total chunks, search patterns
- **OAuth Discovery**: Full `.well-known` endpoints for MCP clients

## 🚀 Quick Start

### Prerequisites

**Option A: Docker (Recommended)**
- Docker & Docker Compose
- Claude Code CLI

**Option B: Native**
- Go 1.19+
- Python 3.12+
- Claude Code CLI

## 🐳 Docker Setup (Recommended)

### 1. Quick Start with Docker
```bash
# Build and start all services
make -f Makefile.docker docker-setup

# Or manually:
docker-compose up -d
```

### 2. Connect to Claude Code
```bash
claude mcp add -t http go-mcp http://127.0.0.1:8009/sse
```

### 3. Useful Docker Commands
```bash
make -f Makefile.docker docker-logs     # View logs
make -f Makefile.docker docker-status   # Check status
make -f Makefile.docker docker-down     # Stop services
make -f Makefile.docker docker-help     # See all commands
```

### 4. Development Mode (with debugging)
```bash
make -f Makefile.docker docker-dev      # Start with hot reload
```

## 🔧 Native Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Python RAG API
```bash
python rag_http_server.py --host 127.0.0.1 --port 8008
```

### 3. Build and Start Go MCP Server
```bash
make build && make run
# Or: cd server && go run .
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

### Core Tools
- **`initialize_rag`** - Initialize RAG system with documents from a directory
  - Parameters: `data_path`, `load_existing`, `chunk_size`, `chunk_overlap`
  - Creates vector database from txt, pdf, csv, md files

- **`search_documents`** - Vector similarity search with automatic deduplication
  - Parameters: `query`, `k` (number of results)
  - Filters out previously shown chunks per user
  - Logs all searches to database

- **`get_system_status`** - Get system health and statistics
  - Returns RAG system status, vectorstore readiness
  - Session management statistics (users, chunks)

- **`session_management`** - Manage user session data
  - Actions: `clear_history` (reset user's seen chunks), `stats` (get statistics)

### HTTP Endpoints (Go MCP Server - Port 8009)
- `GET /sse` - MCP SSE endpoint for Claude Code
- `GET /.well-known/oauth-authorization-server` - OAuth discovery metadata
- `GET /.well-known/oauth-protected-resource` - Protected resource metadata
- `GET /oauth/authorize` - OAuth authorization endpoint
- `POST /oauth/token` - OAuth token exchange endpoint
- `POST /register` - Dynamic client registration
- `GET /search-logs` - Get search logs (query params: `user_id`, `limit`)

### HTTP API Endpoints (Python Server - Port 8008)
- `POST /initialize` - Initialize RAG system (JSON: `data_path`, `load_existing`, `chunk_size`, `chunk_overlap`)
- `POST /search` - Search documents (JSON: `query`, `k`)
- `POST /status` - Get system status
- `GET /health` - Health check endpoint

## 📖 Usage Examples

### 1. Initialize RAG System
```bash
# Via MCP tool in Claude Code
initialize_rag(data_path="./data", load_existing=false, chunk_size=1000, chunk_overlap=200)

# Or via HTTP API
curl -X POST http://127.0.0.1:8008/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "./data",
    "load_existing": false,
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'
```

### 2. Search Documents
```bash
# Via MCP tool in Claude Code (with authentication)
search_documents(query="How does the system work?", k=5)

# Or via HTTP API
curl -X POST http://127.0.0.1:8008/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the system work?",
    "k": 5
  }'
```

### 3. View Search Logs
```bash
# Get all search logs
curl http://127.0.0.1:8009/search-logs

# Get logs for specific user (limited to 10)
curl "http://127.0.0.1:8009/search-logs?user_id=test_user&limit=10"
```

### 4. Manage User Sessions
```bash
# Clear user's search history (via MCP)
session_management(action="clear_history")  # Requires authentication

# Get session statistics
session_management(action="stats")
```

### 5. OAuth Authentication Flow
```bash
# 1. Get OAuth metadata
curl http://127.0.0.1:8009/.well-known/oauth-authorization-server

# 2. Get authorization code (opens in browser)
# Navigate to: http://127.0.0.1:8009/oauth/authorize?client_id=simplerag-mcp&response_type=code&redirect_uri=...

# 3. Exchange code for access token
curl -X POST http://127.0.0.1:8009/oauth/token \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_AUTH_CODE" \
  -d "client_id=simplerag-mcp"

# 4. Use access token in requests
curl -X POST http://127.0.0.1:8009/sse \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
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

### Environment Variables (.env file)
```env
# Go MCP Server Configuration
PYTHON_RAG_URL=http://127.0.0.1:8008
GO_MCP_HOST=0.0.0.0                    # Bind to all interfaces
GO_MCP_PORT=8009
GO_MCP_EXTERNAL_HOST=127.0.0.1        # External address for OAuth callbacks

# OAuth Configuration (optional - defaults provided)
OAUTH_CLIENT_ID=simplerag-mcp
OAUTH_CLIENT_SECRET=your-client-secret

# Database Paths (optional)
SESSIONS_DB_PATH=./sessions.db
CHROMA_DB_PATH=./rag_data
```

### RAG System Parameters
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Chunk Size**: 1000 characters (configurable)
- **Chunk Overlap**: 200 characters (configurable)
- **Default Search K**: 5 documents
- **Vector Distance**: Cosine similarity

### Session Management Settings
- **Database**: SQLite (`./sessions.db`)
- **Tables**:
  - `user_chunks` - Tracks user's seen chunk IDs
  - `search_logs` - Logs all search queries and responses
- **Deduplication**: Per-user chunk tracking
- **Token Expiration**: 3600 seconds (1 hour)

## 🧠 Session Management

The system includes production-ready session management with SQLite:

### Chunk Deduplication
- **Per-User Tracking**: Each user has their own set of seen chunk IDs
- **Automatic Filtering**: New searches only return chunks not previously shown
- **Persistent Storage**: SQLite database survives server restarts
- **Memory Efficient**: Only stores chunk IDs, not full content

### Search Logging
- **Complete Audit Trail**: All searches logged with timestamps
- **RAG Response Tracking**: Original vector search results stored
- **MCP Response Tracking**: Final formatted response stored
- **User Attribution**: Each log entry tagged with user_id
- **Query Analytics**: Retrieve logs by user, with pagination support

### Statistics
- Track unique users across sessions
- Count total chunks served per user
- Monitor search patterns and frequency

## 🐛 Troubleshooting

### Common Issues

#### 1. Connection Refused
**Symptoms**: Can't connect to MCP server or Python API
**Solutions**:
```bash
# Check if servers are running
netstat -an | grep 8008  # Python server
netstat -an | grep 8009  # Go MCP server

# Restart servers
make dev-stop && make dev-start

# Check logs
docker-compose logs -f  # If using Docker
```

#### 2. No Search Results
**Symptoms**: Search returns empty or "No relevant documents found"
**Solutions**:
```bash
# 1. Check if RAG system is initialized
curl http://127.0.0.1:8008/status

# 2. Verify documents exist
ls -la ./data/

# 3. Re-initialize with documents
curl -X POST http://127.0.0.1:8008/initialize \
  -H "Content-Type: application/json" \
  -d '{"data_path": "./data", "load_existing": false}'

# 4. Check ChromaDB directory
ls -la ./rag_data/
```

#### 3. OAuth Authentication Issues
**Symptoms**: 401 Unauthorized or token validation errors
**Solutions**:
```bash
# Get fresh OAuth metadata
curl http://127.0.0.1:8009/.well-known/oauth-authorization-server

# Test without authentication (if supported)
curl -H "X-User-ID: test_user" http://127.0.0.1:8009/sse

# Check token expiration (tokens expire after 1 hour)
# Re-authenticate through OAuth flow
```

#### 4. MCP Connection Failed
**Symptoms**: Claude Code can't connect to MCP server
**Solutions**:
```bash
# Verify endpoint
curl http://127.0.0.1:8009/sse

# Check Claude Code MCP configuration
claude mcp list

# Remove and re-add MCP server
claude mcp remove go-mcp
claude mcp add -t http go-mcp http://127.0.0.1:8009/sse

# Check server logs
tail -f logs/go-mcp.log  # If logging configured
```

#### 5. All Chunks Already Seen
**Symptoms**: "All relevant information has already been provided"
**Solutions**:
```bash
# Clear user's search history
# Via MCP tool (requires authentication):
session_management(action="clear_history")

# Or via HTTP (with user_id header):
curl -X POST http://127.0.0.1:8009/sse \
  -H "X-User-ID: your_user_id" \
  -d '{"action": "clear_history"}'

# Check session stats
curl http://127.0.0.1:8009/search-logs?user_id=your_user_id
```

#### 6. Python Dependencies Issues
**Symptoms**: Import errors or missing modules
**Solutions**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or use virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### 7. Database Locked Errors
**Symptoms**: "database is locked" when accessing sessions.db
**Solutions**:
```bash
# Check for multiple server instances
ps aux | grep "go run\|rag_http_server"

# Kill duplicate processes
killall -9 go

# Restart servers
make dev-start
```

### Debug Mode

Enable verbose logging:
```bash
# Go server with verbose output
cd server && go run . -v

# Python server with debug mode
python rag_http_server.py --host 127.0.0.1 --port 8008 --reload

# Check system status
curl http://127.0.0.1:8008/status
curl http://127.0.0.1:8009/search-logs?limit=5
```

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
- [Go MCP SDK](https://github.com/modelcontextprotocol/go-sdk) - Official Go SDK for MCP
- [ChromaDB](https://www.trychroma.com/) - Vector database for embeddings
- [LangChain](https://www.langchain.com/) - Framework for LLM applications
- [HuggingFace Transformers](https://huggingface.co/transformers/) - Embedding models
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework

## 🏆 Key Technical Features

### Architecture Highlights
- **Language Separation**: Go for I/O-intensive MCP handling, Python for ML workloads
- **HTTP Bridge**: Clean separation via REST API between Go and Python
- **Stateful Sessions**: SQLite for persistent user state across server restarts
- **OAuth 2.1 Compliant**: Full RFC implementation with PKCE support

### Performance Optimizations
- **Connection Pooling**: HTTP client reuse in Go
- **Vector Search**: Cosine similarity with HNSW index (ChromaDB)
- **Lazy Loading**: Database initialized on first request or startup
- **Concurrent Safe**: Mutex-protected session management

### Security Features
- **OAuth 2.1**: Secure authentication with authorization code flow
- **Token Management**: Automatic expiration and validation
- **User Isolation**: Per-user chunk tracking prevents data leakage
- **Input Validation**: Request validation at both Go and Python layers

## 📊 Database Schema

### SQLite Database (sessions.db)

#### user_chunks table
```sql
CREATE TABLE user_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, chunk_id)
);
CREATE INDEX idx_user_chunks_user_id ON user_chunks(user_id);
CREATE INDEX idx_user_chunks_chunk_id ON user_chunks(chunk_id);
```

#### search_logs table
```sql
CREATE TABLE search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    rag_response TEXT,
    mcp_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX idx_search_logs_timestamp ON search_logs(timestamp);
```

### ChromaDB (rag_data/)
- **Collection**: Document chunks with embeddings
- **Metadata**: source, chunk_id, file_type, etc.
- **Dimension**: 384 (all-MiniLM-L6-v2)
- **Distance**: Cosine similarity

---

**Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: October 2025
**License**: MIT

## 📈 Roadmap

- [ ] Multi-tenant support with database isolation
- [ ] Advanced caching layer (Redis)
- [ ] Prometheus metrics and monitoring
- [ ] Streaming responses for large documents
- [ ] Support for more embedding models
- [ ] Web UI for administration
- [ ] Docker Compose for production deployment