# RAG System Architecture - UML Diagrams

## Общая архитектура системы

```mermaid
graph TB
    subgraph Client["Client Layer"]
        CLAUDE[Claude Code<br/>MCP Client]
        USER[User/API Client]
    end

    subgraph GoMCP["Go MCP Server :8009"]
        MCP[MCP Handler<br/>/sse]
        OAUTH[OAuth Manager<br/>Authorization]
        SESS[Session Manager<br/>Chunk Deduplication]
        TOOLS[MCP Tools<br/>initialize_rag<br/>search_documents<br/>get_system_status<br/>session_management]
        LOGS[Search Logs<br/>/search-logs]
    end

    subgraph Python["Python HTTP Server :8008"]
        FAST[FastAPI Server<br/>/initialize<br/>/search<br/>/status]
        RM[RAG Manager]

        subgraph DB["Database Layer"]
            DBB[Database Builder]
            DL[Document Loader]
            TP[Text Processor]
        end

        subgraph Search["Search Layer"]
            RET[Retriever]
        end
    end

    subgraph Storage["Storage Layer"]
        VDB[(ChromaDB<br/>./rag_data/)]
        SDB[(SQLite<br/>./sessions.db)]
        FILES[(Documents<br/>./data/)]
    end

    subgraph External["External Services"]
        EMB[HuggingFace<br/>Embeddings<br/>all-MiniLM-L6-v2]
    end

    CLAUDE -->|SSE/HTTP| MCP
    USER -->|HTTP| FAST

    MCP --> TOOLS
    MCP --> OAUTH
    TOOLS --> SESS

    TOOLS -->|HTTP| FAST

    FAST --> RM
    RM --> DBB
    RM --> RET

    DBB --> DL
    DBB --> TP
    DBB --> VDB
    DBB --> EMB

    DL --> FILES
    RET --> VDB

    SESS --> SDB
    TOOLS --> LOGS
    LOGS --> SDB

    style CLAUDE fill:#e1f5ff
    style MCP fill:#ffeb99
    style FAST fill:#b3e5b3
    style RM fill:#fff4e1
    style VDB fill:#f0f0f0
    style SDB fill:#f0f0f0
    style EMB fill:#ffe1e1
```

## Component Class Diagram

```mermaid
classDiagram
    %% Go MCP Server Components
    class RAGClient {
        -string baseURL
        -http.Client httpClient
        +InitializeRAG(dataPath, loadExisting, chunkSize, chunkOverlap) RAGResponse
        +SearchDocuments(query, k) RAGResponse
        +GetStatus() RAGResponse
        -makeRequest(endpoint, payload) RAGResponse
    }

    class SimpleSessionManager {
        -sql.DB db
        -sync.RWMutex mutex
        +SaveChunkIDs(userID, chunkIDs) error
        +GetUserChunkIDs(userID) []string
        +FilterNewChunks(userID, chunkIDs) []string
        +ClearUserHistory(userID) error
        +SaveSearchLog(userID, query, ragResponse, mcpResponse) error
        +GetSearchLogs(userID, limit) []SearchLog
        +GetStats() map[string]int
    }

    class SimpleOAuthManager {
        -OAuthConfig config
        -map tokens
        -map states
        -string serverAddr
        +authorizeHandler(w, r)
        +tokenHandler(w, r)
        +metadataHandler(w, r)
        +registerHandler(w, r)
        +authMiddleware(next) Handler
    }

    class MCPServer {
        +Name string
        +Version string
        +tools []Tool
        +HandleSSE()
    }

    %% Python Components
    class RAGHTTPServer {
        -RAGManager rag_manager
        -Config config
        -bool initialized
        +initialize_rag(request) RAGResponse
        +search_documents(request) RAGResponse
        +get_system_status() RAGResponse
        -get_or_create_rag_manager() RAGManager
        -_auto_initialize()
    }

    class RAGManager {
        -Config config
        -DatabaseBuilder db_builder
        -Retriever retriever
        +setup_database(data_path, chunk_size, chunk_overlap)
        +load_existing_database()
        +search_documents(query, k, include_ids) List~Dict~
    }

    class DatabaseBuilder {
        -str persist_directory
        -HuggingFaceEmbeddings embeddings
        -Chroma vectorstore
        -List~Document~ documents
        +load_documents(source_path) List~Document~
        +process_documents(chunk_size, chunk_overlap) List~Document~
        +create_vectorstore(documents) Chroma
        +load_vectorstore() Chroma
    }

    class DocumentLoader {
        -Dict loaders
        +load_from_path(source_path) List~Document~
        -_load_single_file(file_path) List~Document~
        -_load_directory(dir_path) List~Document~
    }

    class TextProcessor {
        -int chunk_size
        -int chunk_overlap
        -RecursiveCharacterTextSplitter splitter
        +split_documents(documents) List~Document~
    }

    class Retriever {
        -Chroma vectorstore
        -int default_k
        +search(query, k) List~Document~
        +search_with_scores(query, k) List~tuple~
        +search_with_scores_and_ids(query, k) List~Dict~
        +search_with_metadata_filter(query, filter, k) List~Document~
    }

    class Config {
        -Dict _config
        +get(key, default) Any
        +set(key, value)
    }

    %% Relationships
    MCPServer *-- RAGClient
    MCPServer *-- SimpleSessionManager
    MCPServer *-- SimpleOAuthManager

    RAGHTTPServer *-- RAGManager
    RAGHTTPServer *-- Config

    RAGManager *-- DatabaseBuilder
    RAGManager *-- Retriever
    RAGManager *-- Config

    DatabaseBuilder *-- DocumentLoader
    DatabaseBuilder *-- TextProcessor

    %% Dependencies
    RAGClient ..> RAGHTTPServer : HTTP calls
    SimpleSessionManager ..> SQLite : stores
    DatabaseBuilder ..> ChromaDB : stores
    DatabaseBuilder ..> HuggingFaceEmbeddings : uses
    Retriever ..> ChromaDB : queries
```

## Sequence Diagram - Full Search Flow with Session Management

```mermaid
sequenceDiagram
    actor User as Claude Code
    participant MCP as Go MCP Server
    participant OAuth as OAuth Manager
    participant Session as Session Manager
    participant HTTP as Python HTTP API
    participant RM as RAG Manager
    participant RT as Retriever
    participant VDB as ChromaDB
    participant DB as SQLite DB

    Note over User,MCP: Authentication Phase (Optional)
    User->>MCP: Request with Bearer Token
    MCP->>OAuth: Validate Token
    OAuth-->>MCP: user_id

    Note over User,VDB: Search Phase
    User->>MCP: search_documents(query, k=5)
    MCP->>HTTP: POST /search {query, k}
    HTTP->>RM: search_documents(query, k)
    RM->>RT: search_with_scores_and_ids(query, k)
    RT->>VDB: similarity_search_with_score(query, k)
    VDB-->>RT: [(doc, score), ...]
    RT-->>RM: [{id, content, metadata, score}, ...]
    RM-->>HTTP: raw_results[]
    HTTP-->>MCP: RAGResponse {data: results[]}

    Note over MCP,DB: Deduplication Phase
    MCP->>Session: GetUserChunkIDs(user_id)
    Session->>DB: SELECT chunk_id FROM user_chunks WHERE user_id=?
    DB-->>Session: seen_chunk_ids[]
    Session-->>MCP: seen_chunk_ids[]

    MCP->>MCP: Filter out seen chunks

    alt Has new chunks
        MCP->>Session: SaveChunkIDs(user_id, new_chunk_ids)
        Session->>DB: INSERT INTO user_chunks
        DB-->>Session: OK
    end

    Note over MCP,DB: Logging Phase
    MCP->>Session: SaveSearchLog(user_id, query, rag_response, mcp_response)
    Session->>DB: INSERT INTO search_logs
    DB-->>Session: OK

    MCP->>MCP: Format response with new chunks
    MCP-->>User: Formatted response with context
```

## Sequence Diagram - Database Initialization

```mermaid
sequenceDiagram
    actor User as Client
    participant MCP as Go MCP Server
    participant HTTP as Python HTTP API
    participant RM as RAG Manager
    participant DB as DatabaseBuilder
    participant DL as DocumentLoader
    participant TP as TextProcessor
    participant EMB as HuggingFace Embeddings
    participant VDB as ChromaDB

    Note over User,HTTP: Option 1: Via MCP Tool
    User->>MCP: initialize_rag(data_path="./data", chunk_size=1000)
    MCP->>HTTP: POST /initialize

    Note over HTTP,VDB: Initialization Process
    HTTP->>RM: setup_database(data_path, chunk_size, chunk_overlap)
    RM->>DB: __init__(embedding_model, persist_dir)
    DB->>EMB: HuggingFaceEmbeddings("all-MiniLM-L6-v2")
    EMB-->>DB: embeddings

    DB->>DL: load_from_path(data_path)
    loop For each file (.txt, .pdf, .csv, .md)
        DL->>DL: _load_single_file(file)
    end
    DL-->>DB: documents[]

    DB->>TP: TextProcessor(chunk_size=1000, overlap=200)
    DB->>TP: split_documents(documents)
    TP->>TP: RecursiveCharacterTextSplitter.split()
    TP-->>DB: chunked_documents[]

    DB->>EMB: embed_documents(texts)
    EMB-->>DB: embeddings[]

    DB->>VDB: Chroma.from_documents(chunks, embeddings, persist_dir)
    VDB->>VDB: persist()
    VDB-->>DB: vectorstore

    DB-->>RM: vectorstore
    RM->>RM: Retriever(vectorstore)
    RM-->>HTTP: success
    HTTP-->>MCP: RAGResponse{success: true}
    MCP-->>User: {message: "initialized", data: {...}}
```

## OAuth 2.1 Flow Diagram

```mermaid
sequenceDiagram
    actor User as Claude Code User
    participant CC as Claude Code
    participant MCP as Go MCP Server
    participant OAuth as OAuth Manager
    participant Browser as Web Browser

    Note over User,OAuth: OAuth Discovery
    CC->>MCP: GET /.well-known/oauth-authorization-server
    MCP->>OAuth: metadataHandler()
    OAuth-->>CC: {authorization_endpoint, token_endpoint, ...}

    Note over User,OAuth: Authorization Flow
    CC->>Browser: Open authorization_endpoint
    Browser->>OAuth: GET /oauth/authorize?client_id=...&redirect_uri=...&state=...
    OAuth-->>Browser: Display login form
    User->>Browser: Enter user_id & password
    Browser->>OAuth: POST /oauth/authorize {user_id, password}
    OAuth->>OAuth: Generate auth_code, store state
    OAuth-->>Browser: Redirect to callback with code
    Browser-->>CC: Authorization code

    Note over CC,OAuth: Token Exchange
    CC->>OAuth: POST /oauth/token {grant_type, code, client_id}
    OAuth->>OAuth: Validate code, generate access_token
    OAuth->>OAuth: Store token with user_id
    OAuth-->>CC: {access_token, token_type, expires_in}

    Note over CC,MCP: Authenticated Requests
    CC->>MCP: Request with Authorization: Bearer <token>
    MCP->>OAuth: Validate token
    OAuth-->>MCP: user_id from token
    MCP->>MCP: Add user_id to context
    MCP-->>CC: Response with user context
```

## Data Flow Diagram

```mermaid
flowchart TB
    Start([User Request]) --> CheckSource{Request Source}

    CheckSource -->|Claude Code| MCPFlow[MCP /sse Endpoint]
    CheckSource -->|Direct HTTP| HTTPFlow[FastAPI Endpoint]

    MCPFlow --> OAuth{Authenticated?}
    OAuth -->|Yes| ExtractUser[Extract user_id from token]
    OAuth -->|No| Anonymous[Anonymous Request]

    ExtractUser --> MCPTool{Tool Type}
    Anonymous --> MCPTool

    MCPTool -->|initialize_rag| InitTool[Initialize RAG Tool]
    MCPTool -->|search_documents| SearchTool[Search Documents Tool]
    MCPTool -->|get_system_status| StatusTool[Status Tool]
    MCPTool -->|session_management| SessionTool[Session Tool]

    InitTool -->|HTTP| HTTPInit[POST /initialize]
    SearchTool -->|HTTP| HTTPSearch[POST /search]
    StatusTool -->|HTTP| HTTPStatus[POST /status]

    HTTPFlow --> HTTPInit
    HTTPFlow --> HTTPSearch
    HTTPFlow --> HTTPStatus

    HTTPInit --> LoadDocs[Load Documents<br/>txt, pdf, csv, md]
    LoadDocs --> SplitDocs[Split into Chunks<br/>size: 1000, overlap: 200]
    SplitDocs --> Embed[Generate Embeddings<br/>all-MiniLM-L6-v2]
    Embed --> StoreVDB[(Store in ChromaDB<br/>./rag_data/)]
    StoreVDB --> InitDone([Initialization Complete])

    HTTPSearch --> VectorSearch[Similarity Search<br/>k=5 by default]
    StoreVDB -.-> VectorSearch
    VectorSearch --> ReturnResults[Return Results<br/>with IDs and scores]

    ReturnResults --> BackToMCP{From MCP?}
    BackToMCP -->|Yes| CheckAuth{Authenticated?}
    BackToMCP -->|No| DirectResponse([Return JSON])

    CheckAuth -->|Yes| GetSeen[Get User's Seen Chunks<br/>FROM user_chunks]
    CheckAuth -->|No| NoFilter[No Filtering]

    GetSeen --> FilterChunks[Filter Out Seen Chunks]
    FilterChunks --> HasNew{New Chunks?}

    HasNew -->|Yes| SaveNew[Save New Chunk IDs<br/>TO user_chunks]
    HasNew -->|No| EmptyMsg[No new info message]

    NoFilter --> FormatResp[Format Response]
    SaveNew --> FormatResp
    EmptyMsg --> FormatResp

    FormatResp --> SaveLog[Save Search Log<br/>TO search_logs]
    SaveLog --> MCPResponse([Return Formatted Response])

    HTTPStatus --> GetRAGStatus[Check RAG Status]
    GetRAGStatus --> GetSessionStats[Get Session Stats<br/>FROM sessions.db]
    GetSessionStats --> StatusResponse([Return Status])

    SessionTool --> SessionAction{Action Type}
    SessionAction -->|clear_history| ClearHist[DELETE FROM user_chunks<br/>WHERE user_id=?]
    SessionAction -->|stats| GetStats[Get Session Statistics]
    ClearHist --> SessionDone([Action Complete])
    GetStats --> SessionDone

    style LoadDocs fill:#bbdefb
    style VectorSearch fill:#c8e6c9
    style OAuth fill:#ffccbc
    style StoreVDB fill:#f0f4c3
    style GetSeen fill:#f0f4c3
    style SaveNew fill:#f0f4c3
    style SaveLog fill:#f0f4c3
```

## State Diagram - System States

```mermaid
stateDiagram-v2
    [*] --> ServerStarting

    state "Go MCP Server" as GoServer {
        ServerStarting --> InitializingOAuth: Load OAuth config
        InitializingOAuth --> InitializingSession: Setup endpoints
        InitializingSession --> WaitingPython: Initialize SQLite DB

        WaitingPython --> Ready: Python server ready
        WaitingPython --> Error: Connection failed

        Ready --> Processing: Request received
        Processing --> Authenticating: Check OAuth token
        Authenticating --> Processing: Valid token
        Authenticating --> Unauthorized: Invalid token
        Processing --> CallingPython: Forward to Python
        CallingPython --> FilteringChunks: Got RAG response
        FilteringChunks --> LoggingSearch: Save chunks
        LoggingSearch --> Ready: Return response

        Unauthorized --> Ready: Return 401
    }

    state "Python HTTP Server" as PythonServer {
        [*] --> PythonStarting
        PythonStarting --> AutoInit: Load config
        AutoInit --> CheckingDB: Check for existing DB

        CheckingDB --> LoadingExisting: Found rag_data/
        CheckingDB --> CheckingData: No existing DB
        CheckingData --> CreatingNew: Found ./data/
        CheckingData --> PythonReady: No data

        LoadingExisting --> PythonReady: DB loaded
        CreatingNew --> LoadingDocs: Processing documents
        LoadingDocs --> Chunking: Documents loaded
        Chunking --> Embedding: Chunks created
        Embedding --> StoringVectors: Embeddings generated
        StoringVectors --> PythonReady: DB created

        PythonReady --> Searching: Search request
        Searching --> PythonReady: Results returned

        PythonReady --> Reinitializing: Manual init request
        Reinitializing --> LoadingDocs: Process new data
    }

    Error --> [*]: Shutdown
```

## Deployment Architecture

```mermaid
graph TB
    subgraph Server["Application Server"]
        subgraph Go["Go Process"]
            MCP_SERVER[Go MCP Server<br/>Port: 8009<br/>Host: 0.0.0.0]
            OAUTH_M[OAuth 2.1 Manager<br/>Authorization Server]
            SESS_M[Session Manager<br/>Chunk Deduplication]
        end

        subgraph Python["Python Process"]
            FAST_SERVER[FastAPI Server<br/>Port: 8008<br/>Host: 127.0.0.1]
            RAG_SYS[RAG System<br/>Core Logic]
        end

        subgraph Data["Local Storage"]
            CHROMA[(ChromaDB<br/>./rag_data/<br/>Vector Database)]
            SQLITE[(SQLite<br/>./sessions.db<br/>user_chunks<br/>search_logs)]
            DOCS[(Documents<br/>./data/<br/>Source Files)]
        end
    end

    subgraph External["External Services"]
        HF[HuggingFace<br/>Embeddings API<br/>all-MiniLM-L6-v2]
    end

    subgraph Clients["Client Applications"]
        CLAUDE_CLIENT[Claude Code<br/>MCP Client<br/>SSE Connection]
        HTTP_CLIENT[HTTP Client<br/>Direct API Access]
    end

    CLAUDE_CLIENT -->|SSE http://host:8009/sse| MCP_SERVER
    HTTP_CLIENT -->|HTTP http://host:8008| FAST_SERVER

    MCP_SERVER --> OAUTH_M
    MCP_SERVER --> SESS_M
    MCP_SERVER -->|HTTP 127.0.0.1:8008| FAST_SERVER

    SESS_M --> SQLITE
    FAST_SERVER --> RAG_SYS
    RAG_SYS --> CHROMA
    RAG_SYS --> DOCS
    RAG_SYS -->|API Calls| HF

    style MCP_SERVER fill:#4fc3f7
    style FAST_SERVER fill:#66bb6a
    style RAG_SYS fill:#fff59d
    style CHROMA fill:#a5d6a7
    style SQLITE fill:#a5d6a7
    style DOCS fill:#e0e0e0
    style HF fill:#ef9a9a
    style OAUTH_M fill:#ffb74d
    style SESS_M fill:#ba68c8
```

## Key Features Overview

### 1. **Dual Server Architecture**
- **Go MCP Server** (Port 8009): MCP protocol handler, OAuth 2.1, session management
- **Python HTTP Server** (Port 8008): RAG system, vector search, document processing

### 2. **OAuth 2.1 Authentication**
- MCP-compliant OAuth 2.1 implementation
- Authorization code flow with PKCE
- OAuth discovery metadata endpoints
- Dynamic client registration

### 3. **Session Management**
- **Chunk Deduplication**: Tracks which chunks user has seen
- **Search Logging**: Records all search queries and responses
- **SQLite Storage**: Persistent storage in `sessions.db`

### 4. **RAG Pipeline**
- **Document Loading**: txt, pdf, csv, md files
- **Text Processing**: 1000-char chunks with 200-char overlap
- **Vector Embeddings**: HuggingFace all-MiniLM-L6-v2
- **Vector Search**: ChromaDB with cosine similarity

### 5. **MCP Tools**
- `initialize_rag`: Setup vector database from documents
- `search_documents`: Search with deduplication and logging
- `get_system_status`: System health and statistics
- `session_management`: Clear history, get stats

### 6. **Data Flow**
1. Claude Code → Go MCP Server (with OAuth)
2. Go validates token, extracts user_id
3. Go → Python HTTP API for RAG search
4. Python returns results with chunk IDs
5. Go filters seen chunks (per user)
6. Go saves new chunks and logs search
7. Go returns formatted response to Claude
