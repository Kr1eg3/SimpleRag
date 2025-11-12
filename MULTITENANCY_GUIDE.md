# Multi-Database Support Guide

## Overview

The SimpleRAG system now supports multiple vector databases, allowing different users to switch between different document collections. Each database is stored in a separate directory under `rag_data/`.

## Architecture

```
rag_data/
  ├── default/          # Default database
  │   └── chroma.sqlite3
  ├── medical/          # Medical documents database
  │   └── chroma.sqlite3
  └── legal/            # Legal documents database
      └── chroma.sqlite3
```

## How It Works

### 1. User Database Mapping

- Each user has an **active database** stored in SQLite (`sessions.db`)
- When a user searches, the system automatically uses their active database
- Users can switch between databases using MCP tools

### 2. Database Discovery

- On startup, the Python RAG server automatically discovers all databases in `rag_data/`
- Databases are loaded **lazily** (only when first accessed)
- The Go MCP server tracks which database each user is currently using

### 3. Session Management

New table in `sessions.db`:
```sql
CREATE TABLE user_active_database (
    user_id TEXT PRIMARY KEY,
    database_name TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## New MCP Tools

### `list_databases`
Lists all available vector databases.

**Usage:**
```python
list_databases()
```

**Returns:**
```json
{
  "databases": [
    {
      "name": "default",
      "path": "./rag_data/default",
      "size": 2048000,
      "created": 1698765432.0,
      "loaded": true
    },
    {
      "name": "medical",
      "path": "./rag_data/medical",
      "size": 3145728,
      "created": 1698765500.0,
      "loaded": false
    }
  ],
  "count": 2
}
```

### `switch_database`
Switch the active database for the current user.

**Usage:**
```python
switch_database(database_name="medical")
```

**Returns:**
```json
{
  "message": "Successfully switched to database 'medical'",
  "database_name": "medical"
}
```

**Requirements:**
- User must be authenticated (via OAuth or X-User-ID header)
- Database must exist

### Modified: `search_documents`
Now automatically uses the user's active database.

**Usage:**
```python
# User searches - automatically uses their active database
search_documents(query="diabetes symptoms", k=5)
```

**Behavior:**
1. Extracts `user_id` from context (OAuth token or X-User-ID header)
2. Queries `user_active_database` table to get the user's active database
3. If no active database is set, uses "default"
4. Sends search request to Python RAG server with `database_name` parameter

## Creating New Databases

### Method 1: Using `initialize_rag` (Recommended)

```python
initialize_rag(
    data_path="./data/medical",
    database_name="medical",
    load_existing=false,
    chunk_size=1000,
    chunk_overlap=200
)
```

This will:
1. Create directory `./rag_data/medical/`
2. Load documents from `./data/medical/`
3. Create vector embeddings
4. Save to ChromaDB

### Method 2: Manual Creation

1. Create directory structure:
```bash
mkdir -p rag_data/my_database
```

2. Place your ChromaDB files in the directory:
```bash
# Copy existing database or initialize new one
cp -r existing_db/chroma.sqlite3 rag_data/my_database/
```

3. Restart Python RAG server - it will auto-discover the new database

## Python RAG Server API Changes

### Updated Endpoints

#### `POST /initialize`
Now accepts `database_name` parameter:
```json
{
  "data_path": "./data/medical",
  "database_name": "medical",
  "load_existing": false,
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

#### `POST /search`
Now accepts `database_name` parameter:
```json
{
  "query": "diabetes treatment",
  "k": 5,
  "database_name": "medical"
}
```

#### `GET /list_databases` (NEW)
Returns all available databases:
```bash
curl http://127.0.0.1:8008/list_databases
```

## Usage Examples

### Example 1: Switch Between Databases

```python
# List available databases
result = list_databases()
# Output: {"databases": [{"name": "default"}, {"name": "medical"}], "count": 2}

# Switch to medical database
switch_database(database_name="medical")
# Output: {"message": "Successfully switched to database 'medical'", ...}

# Search now uses medical database
search_documents(query="diabetes symptoms", k=5)
```

### Example 2: Create and Use New Database

```python
# Create new database from documents
initialize_rag(
    data_path="./data/legal",
    database_name="legal",
    load_existing=false
)

# Switch to the new database
switch_database(database_name="legal")

# Search in legal documents
search_documents(query="contract law", k=5)
```

### Example 3: Multiple Users

```bash
# User Alice (via X-User-ID header)
curl -X POST http://127.0.0.1:8009/sse \
  -H "X-User-ID: alice" \
  -d '{"tool": "switch_database", "database_name": "medical"}'

# User Bob (via X-User-ID header)
curl -X POST http://127.0.0.1:8009/sse \
  -H "X-User-ID: bob" \
  -d '{"tool": "switch_database", "database_name": "legal"}'

# Alice searches in medical database
# Bob searches in legal database
```

## Migration from Old Structure

If you have an existing database in the old format (`rag_data/chroma.sqlite3`), migrate it:

```bash
# Create default database directory
mkdir -p rag_data/default

# Move existing database
mv rag_data/chroma.sqlite3 rag_data/default/
mv rag_data/e8ffa0ca-* rag_data/default/ 2>/dev/null || true

# Restart servers
```

## Code Changes Summary

### Go MCP Server Changes

**New Structures:**
- `SwitchDatabaseInput` / `SwitchDatabaseOutput`
- `ListDatabasesInput` / `ListDatabasesOutput`
- `SearchRequest` now includes `DatabaseName string`

**New Methods:**
- `SessionManager.GetUserActiveDatabase(userID) -> (databaseName, error)`
- `SessionManager.SetUserActiveDatabase(userID, databaseName) -> error`
- `RAGClient.ListDatabases() -> (*RAGResponse, error)`
- `RAGClient.SearchDocuments(query, k, databaseName) -> (*RAGResponse, error)` (updated)

**New MCP Tools:**
- `switch_database` - Switch user's active database
- `list_databases` - List all available databases

### Python RAG Server Changes

**Modified Classes:**
- `RAGHTTPServer.__init__()` - Now uses `Dict[str, RAGManager]` for multiple managers
- `RAGHTTPServer.get_or_create_rag_manager(database_name)` - Lazy loading per database
- `RAGHTTPServer._discover_and_initialize_databases()` - Auto-discovery on startup

**Modified Request Models:**
- `SearchRequest` - Added `database_name: str = "default"`
- `InitializeRAGRequest` - Added `database_name: str = "default"`

**New Methods:**
- `RAGHTTPServer.list_databases()` - List all databases

**New Endpoints:**
- `GET /list_databases` - List available databases

## Testing

### Test 1: Database Discovery

```bash
# Start Python RAG server
python rag_http_server.py

# Check logs - should show discovered databases
# Output: "📁 Discovered database: default"
```

### Test 2: List Databases via HTTP

```bash
curl http://127.0.0.1:8008/list_databases
```

### Test 3: Search in Specific Database

```bash
curl -X POST http://127.0.0.1:8008/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test query",
    "k": 5,
    "database_name": "default"
  }'
```

### Test 4: MCP Tools

```bash
# Start both servers
python rag_http_server.py &
./build/go-mcp.exe &

# Connect via Claude Code
claude mcp add -t http go-mcp http://127.0.0.1:8009/sse --header "X-User-ID: testuser"

# Use tools:
# - list_databases()
# - switch_database(database_name="medical")
# - search_documents(query="test", k=5)
```

## Troubleshooting

### Database Not Found

**Error:** `Database 'xyz' not found or not initialized`

**Solutions:**
1. Check if directory exists: `ls rag_data/xyz/`
2. Verify `chroma.sqlite3` exists: `ls rag_data/xyz/chroma.sqlite3`
3. Create database using `initialize_rag`

### User Not Authenticated

**Error:** `user not authenticated`

**Solutions:**
1. Use X-User-ID header: `--header "X-User-ID: youruser"`
2. Or use OAuth flow

### Database Size

To check database sizes:
```bash
du -sh rag_data/*/
```

## Performance Considerations

- **Lazy Loading:** Databases are loaded only when first accessed
- **Memory:** Each loaded database consumes memory for embeddings model
- **Recommendation:** Keep number of databases reasonable (<10 for typical setups)

## Security Notes

- Users can only switch to databases that exist
- Database names are validated before switching
- Each user's active database is tracked independently
- No cross-user database access (isolation by user_id)

## Future Enhancements

Potential future features:
- Database permissions (read/write access control)
- Shared databases (multiple users, one database)
- Database quotas (size limits per user)
- Database aliases (friendly names)
- Database metadata (description, tags)
