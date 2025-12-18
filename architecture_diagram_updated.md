# RAG System Architecture - Updated UML Diagrams

## 📖 Руководство по чтению диаграмм

### Типы диаграмм в документе:

#### 1. **Graph / Architecture Diagrams (Общая архитектура)**
Показывают структуру системы и связи между компонентами.

**Как читать:**
- **Прямоугольники** = компоненты/сервисы/модули
- **Стрелки** `-->` = направление взаимодействия/вызовов
- **Пунктирные стрелки** `-.->` = слабые связи (создание, использование)
- **Цилиндры** `[(...)]` = хранилища данных (базы данных)
- **Subgraph** = логические группы компонентов
- **Цвета** = категории компонентов (клиенты, серверы, хранилища и т.д.)

**Пример:**
```
CLAUDE -->|SSE/HTTP| MCP
```
Означает: Claude Code отправляет SSE/HTTP запросы к MCP серверу

---

#### 2. **Class Diagrams (Диаграммы классов)**
Показывают структуру классов, их поля, методы и взаимосвязи.

**Обозначения:**
- **+** = публичный метод/поле
- **-** = приватный метод/поле
- **~** = protected метод/поле
- **()** после имени = метод (функция)
- без скобок = поле (переменная)

**Типы связей:**
- `*--` = **композиция** (класс владеет и управляет другим объектом)
- `o--` = **агрегация** (класс содержит ссылку, но не владеет)
- `..>` = **зависимость** (класс использует другой класс)
- `--|>` = **наследование** (класс наследует другой класс)
- `--` = **ассоциация** (классы связаны)

**Пример:**
```
RAGManager *-- DatabaseBuilder
```
Означает: RAGManager владеет экземпляром DatabaseBuilder (при удалении RAGManager, DatabaseBuilder тоже удаляется)

```
RAGClient ..> RAGHTTPServer : HTTP calls
```
Означает: RAGClient зависит от RAGHTTPServer (делает к нему HTTP вызовы)

---

#### 3. **Sequence Diagrams (Диаграммы последовательности)**
Показывают порядок взаимодействия между компонентами во времени (сверху вниз).

**Как читать:**
- **Время течет сверху вниз** (первое действие вверху, последнее внизу)
- **Вертикальные линии** = объекты/компоненты
- **Горизонтальные стрелки** = сообщения/вызовы между объектами
- **Сплошная стрелка** `->` = синхронный вызов (ждет ответа)
- **Пунктирная стрелка** `-->` = ответ/возврат
- **Прямоугольники на линиях** = активация (объект выполняет работу)
- **Note over** = комментарий/пояснение
- **alt/else** = условное ветвление (если-то-иначе)
- **loop** = цикл

**Пример:**
```
User->>MCP: search_documents(query)
MCP->>HTTP: POST /search
HTTP-->>MCP: results
MCP-->>User: formatted response
```
Читается:
1. Пользователь вызывает search_documents у MCP
2. MCP делает POST запрос к HTTP серверу
3. HTTP возвращает результаты MCP
4. MCP возвращает отформатированный ответ пользователю

**alt (условие):**
```
alt Has new chunks
    MCP->>Session: SaveChunkIDs()
else No new chunks
    MCP->>MCP: Skip saving
end
```
Означает: если есть новые чанки - сохранить, иначе - пропустить

---

#### 4. **Flowchart / Data Flow Diagrams (Диаграммы потоков данных)**
Показывают путь данных через систему с точками принятия решений.

**Обозначения:**
- **Прямоугольники** `[ ]` = процессы/операции
- **Ромбы** `{ }` = точки принятия решений (if/else)
- **Скругленные прямоугольники** `([ ])` = начало/конец потока
- **Цилиндры** `[( )]` = операции с базой данных
- **Стрелки** = направление потока данных
- **Подписи на стрелках** = условия ветвления

**Как читать:**
1. Начинаете с узла `Start` или `([...])`
2. Следуете по стрелкам
3. В ромбах (решениях) выбираете путь по условию
4. Доходите до конца `([...])`

**Пример:**
```
CheckAuth{Authenticated?}
CheckAuth -->|Yes| GetUser[Extract user_id]
CheckAuth -->|No| Anonymous[Anonymous request]
```
Означает:
- Проверяем аутентификацию
- Если да → извлекаем user_id
- Если нет → анонимный запрос

---

#### 5. **State Diagrams (Диаграммы состояний)**
Показывают различные состояния системы и переходы между ними.

**Обозначения:**
- **[*]** = начальное/конечное состояние
- **Прямоугольники** = состояния системы
- **Стрелки** = переходы между состояниями
- **Подписи на стрелках** = события, вызывающие переход
- **state "Name" as Alias { }** = вложенные состояния

**Как читать:**
1. Система начинается в `[*]`
2. События вызывают переходы (стрелки)
3. Система переходит в новое состояние
4. Может быть много состояний и путей

**Пример:**
```
[*] --> ServerStarting
ServerStarting --> Ready: Initialization complete
Ready --> Processing: Request received
Processing --> Ready: Response sent
```
Означает:
1. Сервер стартует
2. После инициализации переходит в состояние Ready
3. При получении запроса → Processing
4. После отправки ответа → обратно в Ready

---

#### 6. **ER Diagrams (Entity-Relationship, Диаграммы сущность-связь)**
Показывают структуру базы данных и связи между таблицами.

**Обозначения связей:**
- `||--||` = один к одному (1:1)
- `||--o{` = один ко многим (1:N)
- `}o--o{` = многие ко многим (N:M)
- **PK** = Primary Key (первичный ключ)
- **FK** = Foreign Key (внешний ключ)

**Как читать:**
```
USER_CHUNKS ||--o{ SEARCH_LOGS : "user_id"
```
Означает: Одна запись в USER_CHUNKS связана с множеством записей в SEARCH_LOGS через поле user_id

---

### Цветовая схема в диаграммах:

- 🔵 **Голубой** (#e1f5ff) = клиентские приложения (Claude Code)
- 🟡 **Желтый** (#ffeb99) = Go MCP Server компоненты
- 🟢 **Зеленый** (#b3e5b3) = Python HTTP Server
- 🟠 **Оранжевый** (#fff4e1) = RAG система
- ⚪ **Серый** (#f0f0f0) = базы данных
- 🔴 **Красный** (#ffe1e1) = внешние сервисы
- 🟣 **Фиолетовый** (#e1bee7) = session management

---

### Советы по чтению:

1. **Начинайте с общей архитектуры** - она дает понимание всей системы
2. **Затем изучайте sequence diagrams** - они показывают как компоненты взаимодействуют
3. **Class diagram** используйте как справочник по структуре классов
4. **Data flow** помогает понять путь данных от запроса до ответа
5. **State diagram** показывает жизненный цикл системы

---

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
        SESS[Session Manager<br/>Chunk Deduplication<br/>Active DB Tracking]
        TOOLS[MCP Tools<br/>initialize_rag<br/>search_documents<br/>get_system_status<br/>session_management<br/>switch_database<br/>list_databases]
        LOGS[Search Logs<br/>/search-logs]
    end

    subgraph Python["Python HTTP Server :8008"]
        FAST[FastAPI Server<br/>/initialize<br/>/search<br/>/status<br/>/list_databases]
        DBMGR[Multi-Database Manager<br/>Lazy Loading]

        subgraph RAGInstances["RAG Manager Instances"]
            RM1[RAG Manager<br/>database: default]
            RM2[RAG Manager<br/>database: docs]
            RM3[RAG Manager<br/>database: ...]
        end

        subgraph Components["Shared Components"]
            DBB[Database Builder]
            DL[Document Loader]
            TP[Text Processor]
            RET[Retriever]
        end
    end

    subgraph Storage["Storage Layer"]
        subgraph MultiDB["Multi-Database Storage"]
            VDB1[(ChromaDB<br/>./rag_data/default/)]
            VDB2[(ChromaDB<br/>./rag_data/docs/)]
            VDB3[(ChromaDB<br/>./rag_data/.../)]
        end
        SDB[(SQLite<br/>./sessions.db<br/>user_chunks<br/>search_logs<br/>user_active_database)]
        subgraph DataSources["Data Sources"]
            FILES1[(./data/default/)]
            FILES2[(./data/docs/)]
            FILES3[(./data/.../)]
        end
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

    FAST --> DBMGR
    DBMGR -.->|creates/loads| RM1
    DBMGR -.->|creates/loads| RM2
    DBMGR -.->|creates/loads| RM3

    RM1 --> DBB
    RM1 --> RET
    RM2 --> DBB
    RM2 --> RET
    RM3 --> DBB
    RM3 --> RET

    DBB --> DL
    DBB --> TP
    DBB --> EMB

    DL --> FILES1
    DL --> FILES2
    DL --> FILES3

    RM1 --> VDB1
    RM2 --> VDB2
    RM3 --> VDB3

    RET --> VDB1
    RET --> VDB2
    RET --> VDB3

    SESS --> SDB
    TOOLS --> LOGS
    LOGS --> SDB

    style CLAUDE fill:#e1f5ff
    style MCP fill:#ffeb99
    style FAST fill:#b3e5b3
    style DBMGR fill:#fff4e1
    style VDB1 fill:#f0f0f0
    style VDB2 fill:#f0f0f0
    style VDB3 fill:#f0f0f0
    style SDB fill:#f0f0f0
    style EMB fill:#ffe1e1
    style SESS fill:#e1bee7
```

## Component Class Diagram

```mermaid
classDiagram
    %% Go MCP Server Components
    class RAGClient {
        -string baseURL
        -http.Client httpClient
        +InitializeRAG(dataPath, databaseName, loadExisting, chunkSize, chunkOverlap) RAGResponse
        +SearchDocuments(query, k, databaseName) RAGResponse
        +ListDatabases() RAGResponse
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
        +GetUserActiveDatabase(userID) string
        +SetUserActiveDatabase(userID, databaseName) error
        +GetStats() map[string]int
        -initTables() error
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

    class MCPTools {
        +initialize_rag()
        +search_documents()
        +get_system_status()
        +session_management()
        +switch_database()
        +list_databases()
    }

    %% Python Components
    class RAGHTTPServer {
        -Dict~str,RAGManager~ rag_managers
        -Config config
        -bool initialized
        +initialize_rag(request) RAGResponse
        +search_documents(request) RAGResponse
        +get_system_status() RAGResponse
        +list_databases() RAGResponse
        +get_or_create_rag_manager(database_name) RAGManager
        -_discover_and_initialize_databases()
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

    %% Database Tables
    class UserChunks {
        +int id PK
        +string user_id
        +string chunk_id
        +datetime timestamp
    }

    class SearchLogs {
        +int id PK
        +string user_id
        +string query
        +string rag_response
        +string mcp_response
        +datetime timestamp
    }

    class UserActiveDatabase {
        +string user_id PK
        +string database_name
        +datetime updated_at
    }

    %% Relationships
    MCPServer *-- RAGClient
    MCPServer *-- SimpleSessionManager
    MCPServer *-- SimpleOAuthManager
    MCPServer *-- MCPTools

    RAGHTTPServer *-- "1..*" RAGManager : manages
    RAGHTTPServer *-- Config

    RAGManager *-- DatabaseBuilder
    RAGManager *-- Retriever
    RAGManager *-- Config

    DatabaseBuilder *-- DocumentLoader
    DatabaseBuilder *-- TextProcessor

    SimpleSessionManager ..> UserChunks : stores
    SimpleSessionManager ..> SearchLogs : stores
    SimpleSessionManager ..> UserActiveDatabase : stores

    %% Dependencies
    RAGClient ..> RAGHTTPServer : HTTP calls
    SimpleSessionManager ..> SQLite : stores
    DatabaseBuilder ..> ChromaDB : stores
    DatabaseBuilder ..> HuggingFaceEmbeddings : uses
    Retriever ..> ChromaDB : queries
```

## Sequence Diagram - Full Search Flow with Multi-Database Support

```mermaid
sequenceDiagram
    actor User as Claude Code
    participant MCP as Go MCP Server
    participant OAuth as OAuth Manager
    participant Session as Session Manager
    participant HTTP as Python HTTP API
    participant DBMGR as Database Manager
    participant RM as RAG Manager
    participant RT as Retriever
    participant VDB as ChromaDB
    participant DB as SQLite DB

    Note over User,MCP: Authentication Phase (Optional)
    User->>MCP: Request with Bearer Token
    MCP->>OAuth: Validate Token
    OAuth-->>MCP: user_id

    Note over User,VDB: Database Selection Phase
    MCP->>Session: GetUserActiveDatabase(user_id)
    Session->>DB: SELECT database_name FROM user_active_database WHERE user_id=?
    DB-->>Session: database_name (or "default")
    Session-->>MCP: active_database_name

    Note over User,VDB: Search Phase
    User->>MCP: search_documents(query, k=5)
    MCP->>HTTP: POST /search {query, k, database_name}
    HTTP->>DBMGR: get_or_create_rag_manager(database_name)

    alt Database not loaded
        DBMGR->>DBMGR: Load database from ./rag_data/{db_name}/
        DBMGR->>RM: RAGManager(config)
        RM->>RM: load_existing_database()
        DBMGR->>DBMGR: Cache RAG manager
    end

    DBMGR-->>HTTP: rag_manager
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

## Sequence Diagram - Database Switch Flow

```mermaid
sequenceDiagram
    actor User as Claude Code
    participant MCP as Go MCP Server
    participant OAuth as OAuth Manager
    participant Session as Session Manager
    participant HTTP as Python HTTP API
    participant DB as SQLite DB

    Note over User,MCP: Authentication Required
    User->>MCP: switch_database(database_name="docs")
    MCP->>OAuth: Validate Token
    OAuth-->>MCP: user_id

    Note over MCP,HTTP: Verify Database Exists
    MCP->>HTTP: GET /list_databases
    HTTP->>HTTP: Scan ./rag_data/ for databases
    HTTP-->>MCP: {databases: [{name: "default"}, {name: "docs"}, ...]}

    MCP->>MCP: Check if "docs" exists in list

    alt Database exists
        MCP->>Session: SetUserActiveDatabase(user_id, "docs")
        Session->>DB: INSERT OR UPDATE user_active_database
        DB-->>Session: OK
        Session-->>MCP: Success
        MCP-->>User: {message: "Switched to 'docs'", database_name: "docs"}
    else Database not found
        MCP-->>User: Error: database 'docs' not found
    end
```

## Sequence Diagram - Database Initialization with Multi-DB

```mermaid
sequenceDiagram
    actor User as Client
    participant MCP as Go MCP Server
    participant HTTP as Python HTTP API
    participant DBMGR as Database Manager
    participant RM as RAG Manager
    participant DB as DatabaseBuilder
    participant DL as DocumentLoader
    participant TP as TextProcessor
    participant EMB as HuggingFace Embeddings
    participant VDB as ChromaDB

    Note over User,HTTP: Via MCP Tool
    User->>MCP: initialize_rag(data_path="./data/mydocs", database_name="mydocs")
    MCP->>HTTP: POST /initialize {data_path, database_name, chunk_size, ...}

    Note over HTTP,VDB: Check if database exists
    HTTP->>HTTP: Check ./rag_data/mydocs/chroma.sqlite3

    alt Database exists and load_existing=true
        HTTP->>DBMGR: get_or_create_rag_manager("mydocs")
        DBMGR->>RM: RAGManager(config with persist_dir="./rag_data/mydocs/")
        RM->>DB: load_vectorstore()
        DB->>VDB: Connect to existing database
        VDB-->>DB: vectorstore
        DB-->>RM: vectorstore loaded
        RM-->>DBMGR: rag_manager
        DBMGR-->>HTTP: Cached manager
        HTTP-->>MCP: {success: true, message: "Loaded existing 'mydocs'"}
    else Create new database
        HTTP->>HTTP: mkdir ./rag_data/mydocs/
        HTTP->>RM: RAGManager(config)
        RM->>DB: __init__(embedding_model, persist_dir="./rag_data/mydocs/")
        DB->>EMB: HuggingFaceEmbeddings("all-MiniLM-L6-v2")
        EMB-->>DB: embeddings

        DB->>DL: load_from_path("./data/mydocs/")
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

        DB->>VDB: Chroma.from_documents(chunks, embeddings, "./rag_data/mydocs/")
        VDB->>VDB: persist()
        VDB-->>DB: vectorstore

        DB-->>RM: vectorstore
        RM->>RM: Retriever(vectorstore)
        RM-->>HTTP: success
        HTTP->>DBMGR: Cache rag_manager["mydocs"]
        HTTP-->>MCP: {success: true, message: "Created 'mydocs'"}
    end

    MCP-->>User: Initialization complete
```

## Sequence Diagram - Auto-Discovery on Startup

```mermaid
sequenceDiagram
    participant Start as Server Start
    participant HTTP as Python HTTP Server
    participant FS as File System
    participant DBMGR as Database Manager
    participant RM as RAG Manager

    Note over Start,RM: Server Startup Phase
    Start->>HTTP: __init__()
    HTTP->>HTTP: _discover_and_initialize_databases()

    Note over HTTP,FS: Discover Existing Databases
    HTTP->>FS: Scan ./rag_data/
    FS-->>HTTP: [default/, docs/, manual/, ...]

    loop For each directory
        HTTP->>FS: Check {db_name}/chroma.sqlite3
        alt Database exists
            FS-->>HTTP: Found valid database
            HTTP->>HTTP: Add to discovered_databases set
        end
    end

    HTTP->>HTTP: Log: Discovered N databases (lazy loading)

    Note over HTTP,FS: Check for Missing Databases
    HTTP->>FS: Scan ./data/
    FS-->>HTTP: [default/, docs/, newdb/, ...]

    HTTP->>HTTP: Compare ./data/ with ./rag_data/
    HTTP->>HTTP: Find missing: [newdb/]

    alt Has missing databases
        loop For each missing database
            HTTP->>HTTP: Log: Creating database from ./data/{db_name}/
            HTTP->>FS: mkdir ./rag_data/{db_name}/
            HTTP->>RM: RAGManager(config)
            RM->>RM: setup_database(./data/{db_name}/, ...)
            RM-->>HTTP: database created
            HTTP->>DBMGR: Cache rag_manager[{db_name}]
        end
        HTTP->>HTTP: Log: Created N missing databases
    end

    HTTP->>HTTP: initialized = True
    HTTP-->>Start: Server ready with discovered databases
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
    MCPTool -->|switch_database| SwitchTool[Switch Database Tool]
    MCPTool -->|list_databases| ListTool[List Databases Tool]

    InitTool -->|HTTP| HTTPInit[POST /initialize<br/>database_name param]
    SearchTool --> GetActiveDB[Get User's Active Database<br/>FROM user_active_database]
    GetActiveDB -->|HTTP| HTTPSearch[POST /search<br/>database_name param]
    StatusTool -->|HTTP| HTTPStatus[POST /status]
    ListTool -->|HTTP| HTTPList[GET /list_databases]

    HTTPFlow --> HTTPInit
    HTTPFlow --> HTTPSearch
    HTTPFlow --> HTTPStatus
    HTTPFlow --> HTTPList

    HTTPInit --> SelectDB1{Database Exists?}
    SelectDB1 -->|Yes & load_existing| LoadExisting[Load from ./rag_data/db_name/]
    SelectDB1 -->|No| LoadDocs[Load Documents<br/>from ./data/db_name/]

    LoadDocs --> SplitDocs[Split into Chunks<br/>size: 1000, overlap: 200]
    SplitDocs --> Embed[Generate Embeddings<br/>all-MiniLM-L6-v2]
    Embed --> StoreVDB[(Store in ChromaDB<br/>./rag_data/db_name/)]
    LoadExisting --> CacheManager[Cache RAG Manager<br/>for database]
    StoreVDB --> CacheManager
    CacheManager --> InitDone([Initialization Complete])

    HTTPSearch --> LazyLoad{Manager Cached?}
    LazyLoad -->|No| LoadManager[Load RAG Manager<br/>for database]
    LazyLoad -->|Yes| UseCache[Use Cached Manager]
    LoadManager --> UseCache

    UseCache --> VectorSearch[Similarity Search<br/>in selected database<br/>k=5 by default]
    VectorSearch --> ReturnResults[Return Results<br/>with IDs and scores]

    HTTPList --> ScanDatabases[Scan ./rag_data/<br/>for all databases]
    ScanDatabases --> DatabaseList[Return list with metadata:<br/>name, path, size, loaded status]
    DatabaseList --> ListDone([Return Database List])

    SwitchTool --> VerifyDB[Verify database exists<br/>via list_databases]
    VerifyDB --> UpdateActive[UPDATE user_active_database<br/>SET database_name=?]
    UpdateActive --> SwitchDone([Switch Complete])

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

    HTTPStatus --> GetRAGStatus[Check RAG Status<br/>databases_loaded count]
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
    style GetActiveDB fill:#e1bee7
    style UpdateActive fill:#e1bee7
    style LazyLoad fill:#fff9c4
```

## State Diagram - System States with Multi-Database

```mermaid
stateDiagram-v2
    [*] --> ServerStarting

    state "Go MCP Server" as GoServer {
        ServerStarting --> InitializingOAuth: Load OAuth config
        InitializingOAuth --> InitializingSession: Setup endpoints
        InitializingSession --> WaitingPython: Initialize SQLite DB<br/>(user_chunks, search_logs,<br/>user_active_database)

        WaitingPython --> Ready: Python server ready
        WaitingPython --> Error: Connection failed

        Ready --> Processing: Request received
        Processing --> Authenticating: Check OAuth token
        Authenticating --> Processing: Valid token
        Authenticating --> Unauthorized: Invalid token

        Processing --> GetActiveDB: Get user's active DB
        GetActiveDB --> CallingPython: Forward to Python<br/>with database_name

        CallingPython --> FilteringChunks: Got RAG response
        FilteringChunks --> LoggingSearch: Save chunks
        LoggingSearch --> Ready: Return response

        Processing --> SwitchingDB: switch_database tool
        SwitchingDB --> VerifyingDB: List databases
        VerifyingDB --> UpdatingActiveDB: Database exists
        UpdatingActiveDB --> Ready: Switch complete
        VerifyingDB --> Ready: Database not found (error)

        Unauthorized --> Ready: Return 401
    }

    state "Python HTTP Server" as PythonServer {
        [*] --> PythonStarting
        PythonStarting --> AutoDiscovery: Load config

        state "Auto-Discovery Phase" as Discovery {
            AutoDiscovery --> ScanningRagData: Scan ./rag_data/
            ScanningRagData --> FoundExisting: Found N databases
            ScanningRagData --> NoExisting: No databases

            FoundExisting --> ScanningDataDir: Check ./data/
            NoExisting --> ScanningDataDir

            ScanningDataDir --> FoundMissing: Found missing DBs
            ScanningDataDir --> NoMissing: No missing DBs

            FoundMissing --> CreatingMissing: Create databases<br/>from ./data/{db_name}/
            CreatingMissing --> LoadingDocs: Process documents
            LoadingDocs --> Chunking: Documents loaded
            Chunking --> Embedding: Chunks created
            Embedding --> StoringVectors: Embeddings generated
            StoringVectors --> CachingManagers: Cache managers

            NoMissing --> PythonReady
            CachingManagers --> PythonReady
        }

        PythonReady --> ReceivingRequest: Request received

        ReceivingRequest --> CheckingCache: Get/Create manager

        state "Lazy Loading" as LazyLoad {
            CheckingCache --> ManagerCached: Manager exists
            CheckingCache --> LoadingManager: Manager not cached

            LoadingManager --> CheckingDBExists: Check database file
            CheckingDBExists --> LoadingExistingDB: Database exists
            CheckingDBExists --> ErrorNoDB: Database not found

            LoadingExistingDB --> ConnectingDB: Load vectorstore
            ConnectingDB --> CachingManager: Cache manager
            CachingManager --> ManagerCached

            ManagerCached --> Searching: Execute search
        }

        Searching --> PythonReady: Results returned

        PythonReady --> Reinitializing: Manual init request
        Reinitializing --> LoadingDocs: Process new data

        PythonReady --> ListingDBs: List databases request
        ListingDBs --> ScanningForList: Scan ./rag_data/
        ScanningForList --> PythonReady: Return list

        ErrorNoDB --> PythonReady: Return error
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
            SESS_M[Session Manager<br/>Chunk Deduplication<br/>Active DB Tracking]
        end

        subgraph Python["Python Process"]
            FAST_SERVER[FastAPI Server<br/>Port: 8008<br/>Host: 127.0.0.1]
            DBMGR[Multi-Database Manager<br/>Lazy Loading Cache]
            RAG_SYS[RAG System Instances<br/>Per Database]
        end

        subgraph Data["Local Storage"]
            subgraph MultiDBStorage["Multi-Database Vector Storage"]
                CHROMA1[(ChromaDB: default<br/>./rag_data/default/)]
                CHROMA2[(ChromaDB: docs<br/>./rag_data/docs/)]
                CHROMA3[(ChromaDB: manual<br/>./rag_data/manual/)]
                CHROMAX[(ChromaDB: ...<br/>./rag_data/.../)]
            end

            SQLITE[(SQLite<br/>./sessions.db<br/>Tables:<br/>- user_chunks<br/>- search_logs<br/>- user_active_database)]

            subgraph DataSources["Document Sources"]
                DOCS1[(./data/default/)]
                DOCS2[(./data/docs/)]
                DOCS3[(./data/manual/)]
                DOCSX[(./data/.../)]
            end
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
    FAST_SERVER --> DBMGR
    DBMGR --> RAG_SYS

    RAG_SYS --> CHROMA1
    RAG_SYS --> CHROMA2
    RAG_SYS --> CHROMA3
    RAG_SYS --> CHROMAX

    RAG_SYS --> DOCS1
    RAG_SYS --> DOCS2
    RAG_SYS --> DOCS3
    RAG_SYS --> DOCSX

    RAG_SYS -->|API Calls| HF

    style MCP_SERVER fill:#4fc3f7
    style FAST_SERVER fill:#66bb6a
    style DBMGR fill:#fff59d
    style RAG_SYS fill:#fff59d
    style CHROMA1 fill:#a5d6a7
    style CHROMA2 fill:#a5d6a7
    style CHROMA3 fill:#a5d6a7
    style CHROMAX fill:#a5d6a7
    style SQLITE fill:#ba68c8
    style DOCS1 fill:#e0e0e0
    style DOCS2 fill:#e0e0e0
    style DOCS3 fill:#e0e0e0
    style DOCSX fill:#e0e0e0
    style HF fill:#ef9a9a
    style OAUTH_M fill:#ffb74d
    style SESS_M fill:#ba68c8
```

## Database Schema

```mermaid
erDiagram
    USER_CHUNKS {
        int id PK
        string user_id
        string chunk_id
        datetime timestamp
    }

    SEARCH_LOGS {
        int id PK
        string user_id
        string query
        text rag_response
        text mcp_response
        datetime timestamp
    }

    USER_ACTIVE_DATABASE {
        string user_id PK
        string database_name
        datetime updated_at
    }

    VECTOR_DATABASES {
        string database_name PK
        string persist_directory
        int document_count
        datetime created_at
    }

    USER_CHUNKS ||--o{ SEARCH_LOGS : "user_id"
    USER_ACTIVE_DATABASE ||--|| VECTOR_DATABASES : "database_name"
    USER_CHUNKS }o--|| USER_ACTIVE_DATABASE : "user_id"
```

## Key Features Overview

### 1. **Dual Server Architecture**
- **Go MCP Server** (Port 8009): MCP protocol handler, OAuth 2.1, session management
- **Python HTTP Server** (Port 8008): RAG system, vector search, document processing

### 2. **Multi-Database Support** 🆕
- **Multiple Vector Databases**: Each database stored separately in `./rag_data/{database_name}/`
- **Per-User Active Database**: Each user can switch between databases
- **Lazy Loading**: Databases loaded on-demand to save memory
- **Auto-Discovery**: Automatically discovers existing databases on startup
- **Database Management Tools**:
  - `list_databases`: List all available databases
  - `switch_database`: Switch user's active database

### 3. **Database Structure** 🆕
- **New Structure**: `./data/{database_name}/` → `./rag_data/{database_name}/`
- **Legacy Support**: `./data/` → `./rag_data/default/`
- **Auto-Creation**: Missing databases automatically created from `./data/` on startup

### 4. **OAuth 2.1 Authentication**
- MCP-compliant OAuth 2.1 implementation
- Authorization code flow with PKCE
- OAuth discovery metadata endpoints
- Dynamic client registration

### 5. **Session Management**
- **Chunk Deduplication**: Tracks which chunks user has seen (across all databases)
- **Active Database Tracking**: Stores user's current active database 🆕
- **Search Logging**: Records all search queries and responses
- **SQLite Storage**: Persistent storage in `sessions.db` with 3 tables

### 6. **RAG Pipeline**
- **Document Loading**: txt, pdf, csv, md files
- **Text Processing**: 1000-char chunks with 200-char overlap
- **Vector Embeddings**: HuggingFace all-MiniLM-L6-v2
- **Vector Search**: ChromaDB with cosine similarity

### 7. **MCP Tools**
- `initialize_rag`: Setup vector database from documents (with database_name parameter) 🆕
- `search_documents`: Search with deduplication and logging (uses user's active database) 🆕
- `get_system_status`: System health and statistics (shows loaded databases count) 🆕
- `session_management`: Clear history, get stats
- `switch_database`: Switch user's active database 🆕
- `list_databases`: List all available databases 🆕

### 8. **Data Flow**
1. Claude Code → Go MCP Server (with OAuth)
2. Go validates token, extracts user_id
3. Go gets user's active database from session manager 🆕
4. Go → Python HTTP API for RAG search (with database_name) 🆕
5. Python lazy-loads RAG manager for requested database 🆕
6. Python returns results with chunk IDs
7. Go filters seen chunks (per user, across all databases)
8. Go saves new chunks and logs search
9. Go returns formatted response to Claude

### 9. **Performance Optimizations** 🆕
- **Manager Caching**: RAG managers cached after first load
- **Lazy Loading**: Databases only loaded when accessed
- **Memory Efficiency**: Only active databases kept in memory

## Changes from Previous Version

### Added Features:
1. ✅ Multi-database support with per-user active database
2. ✅ Database auto-discovery on startup
3. ✅ Lazy loading of RAG managers
4. ✅ New MCP tools: `switch_database`, `list_databases`
5. ✅ New SQLite table: `user_active_database`
6. ✅ Database name parameter in all relevant endpoints
7. ✅ Support for both new and legacy data structures

### Updated Components:
1. 🔄 `RAGHTTPServer`: Now manages multiple RAG instances
2. 🔄 `SimpleSessionManager`: Added database tracking methods
3. 🔄 `RAGClient`: Added database_name parameters
4. 🔄 All sequence diagrams to reflect database selection
5. 🔄 Data flow diagram with database routing
6. 🔄 State diagram with auto-discovery and lazy loading states
7. 🔄 Deployment architecture with multi-database storage

### Architecture Improvements:
- Better separation of concerns with Database Manager layer
- Scalable multi-tenant design with per-user database selection
- Efficient resource usage through lazy loading
- Automatic database provisioning from source files
