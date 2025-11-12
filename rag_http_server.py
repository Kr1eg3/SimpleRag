#!/usr/bin/env python3
"""
HTTP API wrapper for RAG system to work with Go MCP server
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag import RAGManager, Config


# Request models
class InitializeRAGRequest(BaseModel):
    data_path: str = "./data"
    database_name: str = "default"
    load_existing: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    database_name: str = "default"




# Response model
class RAGResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class RAGHTTPServer:
    def __init__(self):
        self.rag_managers: Dict[str, RAGManager] = {}  # database_name -> RAGManager
        self.config: Optional[Config] = None
        self.initialized = False

        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Auto-discover and initialize databases
        self._discover_and_initialize_databases()

    def get_or_create_rag_manager(self, database_name: str = "default") -> Optional[RAGManager]:
        """Get or create RAG manager for specified database"""
        # Return cached manager if exists
        if database_name in self.rag_managers:
            return self.rag_managers[database_name]

        try:
            config = Config()
            persist_dir = f"./rag_data/{database_name}"

            # Check if database directory exists
            if not Path(persist_dir).exists():
                print(f"⚠️  Database '{database_name}' not found at {persist_dir}")
                return None

            config.set("persist_directory", persist_dir)

            # Create RAG manager
            rag_manager = RAGManager(config)

            # Load existing database
            rag_manager.load_existing_database()

            # Cache the manager
            self.rag_managers[database_name] = rag_manager
            self.config = config

            print(f"✅ Loaded RAG manager for database '{database_name}'")
            return rag_manager

        except Exception as e:
            print(f"❌ Error creating RAG manager for '{database_name}': {e}")
            return None

    def _discover_and_initialize_databases(self):
        """Auto-discover and initialize all existing databases on startup"""
        try:
            print("🔍 Discovering existing databases...")
            rag_data_path = Path("./rag_data")

            if not rag_data_path.exists():
                print("⚠️  No rag_data directory found, creating default structure...")
                rag_data_path.mkdir(parents=True, exist_ok=True)

                # Check if ./data exists and has subdirectories
                data_path = Path("./data")
                if data_path.exists():
                    # Check if ./data has subdirectories (new structure)
                    subdirs = [d for d in data_path.iterdir() if d.is_dir()]

                    if subdirs:
                        # New structure: ./data/database_name/
                        print(f"📁 Found ./data directory with {len(subdirs)} subdirectories")
                        created_count = 0

                        for subdir in subdirs:
                            db_name = subdir.name
                            print(f"📁 Creating database '{db_name}' from ./data/{db_name}/...")

                            db_persist_dir = rag_data_path / db_name
                            db_persist_dir.mkdir(parents=True, exist_ok=True)

                            try:
                                # Initialize database from subdirectory
                                config = Config()
                                config.set("persist_directory", str(db_persist_dir))
                                rag_manager = RAGManager(config)
                                rag_manager.setup_database(
                                    str(subdir),
                                    chunk_size=1000,
                                    chunk_overlap=200
                                )
                                self.rag_managers[db_name] = rag_manager
                                print(f"✅ Created database '{db_name}' from ./data/{db_name}/")
                                created_count += 1
                            except Exception as e:
                                print(f"❌ Failed to create database '{db_name}': {e}")

                        if created_count > 0:
                            print(f"✅ Successfully created {created_count} database(s)")
                        else:
                            print("⚠️  No databases were created")
                    else:
                        # Old structure: ./data/ contains files directly
                        print("📁 Found ./data directory (flat structure), creating 'default' database...")
                        default_persist_dir = rag_data_path / "default"
                        default_persist_dir.mkdir(parents=True, exist_ok=True)

                        # Initialize default database
                        config = Config()
                        config.set("persist_directory", str(default_persist_dir))
                        rag_manager = RAGManager(config)
                        rag_manager.setup_database(
                            str(data_path),
                            chunk_size=1000,
                            chunk_overlap=200
                        )
                        self.rag_managers["default"] = rag_manager
                        print("✅ Created default database from ./data")
                else:
                    print("⚠️  No ./data directory found, skipping default database creation")

                self.initialized = True
                return

            # Discover existing databases
            existing_databases = set()
            for db_dir in rag_data_path.iterdir():
                if db_dir.is_dir() and (db_dir / "chroma.sqlite3").exists():
                    db_name = db_dir.name
                    print(f"📁 Discovered database: {db_name}")
                    existing_databases.add(db_name)

            if existing_databases:
                print(f"✅ Discovered {len(existing_databases)} database(s). They will be loaded on first use (lazy loading).")
            else:
                print("⚠️  No existing databases found in ./rag_data")

            # Check if ./data exists and has subdirectories
            data_path = Path("./data")
            if data_path.exists():
                subdirs = [d for d in data_path.iterdir() if d.is_dir()]

                if subdirs:
                    # Find missing databases (in ./data but not in ./rag_data)
                    data_db_names = {d.name for d in subdirs}
                    missing_databases = data_db_names - existing_databases

                    if missing_databases:
                        print(f"📦 Found {len(missing_databases)} missing database(s): {', '.join(missing_databases)}")
                        print(f"🔨 Creating missing databases...")
                        created_count = 0

                        for db_name in missing_databases:
                            subdir = data_path / db_name
                            print(f"📁 Creating database '{db_name}' from ./data/{db_name}/...")

                            db_persist_dir = rag_data_path / db_name
                            db_persist_dir.mkdir(parents=True, exist_ok=True)

                            try:
                                # Initialize database from subdirectory
                                config = Config()
                                config.set("persist_directory", str(db_persist_dir))
                                rag_manager = RAGManager(config)
                                rag_manager.setup_database(
                                    str(subdir),
                                    chunk_size=1000,
                                    chunk_overlap=200
                                )
                                self.rag_managers[db_name] = rag_manager
                                print(f"✅ Created database '{db_name}' from ./data/{db_name}/")
                                created_count += 1
                            except Exception as e:
                                print(f"❌ Failed to create database '{db_name}': {e}")

                        if created_count > 0:
                            print(f"✅ Successfully created {created_count} missing database(s)")

            self.initialized = True

        except Exception as e:
            print(f"❌ Database discovery failed: {e}")
            print("💡 You can manually initialize using POST /initialize")

    async def initialize_rag(self, request: InitializeRAGRequest) -> RAGResponse:
        """Initialize RAG system for a specific database"""
        try:
            # Setup database path
            data_path_obj = Path(request.data_path)
            persist_dir = Path(f"./rag_data/{request.database_name}")

            # Check if loading existing or creating new
            if request.load_existing and (persist_dir / "chroma.sqlite3").exists():
                # Load existing database
                rag_manager = self.get_or_create_rag_manager(request.database_name)
                if not rag_manager:
                    return RAGResponse(
                        success=False,
                        message=f"Failed to load database '{request.database_name}'",
                        error=f"Failed to load database '{request.database_name}'"
                    )
                message = f"Loaded existing database '{request.database_name}'"
                action = "loaded_existing"
            else:
                # Create new database
                if not data_path_obj.exists():
                    return RAGResponse(
                        success=False,
                        message=f"Data path does not exist: {request.data_path}",
                        error=f"Data path does not exist: {request.data_path}"
                    )

                # Create directory structure
                persist_dir.mkdir(parents=True, exist_ok=True)

                # Create config and RAG manager
                config = Config()
                config.set("persist_directory", str(persist_dir))
                rag_manager = RAGManager(config)

                # Setup database from documents
                rag_manager.setup_database(
                    str(data_path_obj),
                    chunk_size=request.chunk_size,
                    chunk_overlap=request.chunk_overlap
                )

                # Cache the manager
                self.rag_managers[request.database_name] = rag_manager

                message = f"Created new database '{request.database_name}' from {request.data_path}"
                action = "created_new"

            self.initialized = True

            initialization_data = {
                "action": action,
                "database_name": request.database_name,
                "data_path": request.data_path,
                "chunk_size": request.chunk_size,
                "chunk_overlap": request.chunk_overlap,
                "vector_search_ready": True
            }

            return RAGResponse(
                success=True,
                message=message,
                data=initialization_data
            )

        except Exception as e:
            return RAGResponse(
                success=False,
                message=f"Failed to initialize RAG system: {str(e)}",
                error=str(e)
            )

    async def search_documents(self, request: SearchRequest) -> RAGResponse:
        """Search for similar documents in specified database"""
        # Get RAG manager for the specified database
        rag_manager = self.get_or_create_rag_manager(request.database_name)
        if not rag_manager or not rag_manager.retriever:
            return RAGResponse(
                success=False,
                message=f"Database '{request.database_name}' not found or not initialized",
                error=f"Database '{request.database_name}' not found or not initialized"
            )

        try:
            results = rag_manager.search_documents(request.query, k=request.k)

            # Return only raw data without formatting
            raw_results = []
            for result in results:
                metadata = result.get('metadata', {})
                raw_results.append({
                    "id": result.get('id', 'unknown'),
                    "content": result['content'],
                    "metadata": metadata,
                    "similarity_score": result['similarity_score']
                })

            return RAGResponse(
                success=True,
                message=f"Search completed successfully in database '{request.database_name}'",
                data=raw_results
            )

        except Exception as e:
            return RAGResponse(
                success=False,
                message=f"Search failed: {str(e)}",
                error=str(e)
            )


    async def get_system_status(self) -> RAGResponse:
        """Get system status"""
        status_data = {
            "vector_search_available": True,
            "databases_loaded": len(self.rag_managers),
            "database_names": list(self.rag_managers.keys()),
            "system_ready": self.initialized
        }

        return RAGResponse(
            success=True,
            message="System status retrieved successfully",
            data=status_data
        )

    async def list_databases(self) -> RAGResponse:
        """List all available databases"""
        try:
            databases = []
            rag_data_path = Path("./rag_data")

            if not rag_data_path.exists():
                return RAGResponse(
                    success=True,
                    message="No databases found",
                    data={"count": 0, "databases": []}
                )

            for db_dir in rag_data_path.iterdir():
                if db_dir.is_dir() and (db_dir / "chroma.sqlite3").exists():
                    # Get directory stats
                    db_stat = db_dir.stat()
                    db_size = sum(f.stat().st_size for f in db_dir.rglob('*') if f.is_file())

                    db_info = {
                        "name": db_dir.name,
                        "path": str(db_dir),
                        "size": db_size,
                        "created": db_stat.st_ctime,
                        "loaded": db_dir.name in self.rag_managers
                    }
                    databases.append(db_info)

            return RAGResponse(
                success=True,
                message=f"Found {len(databases)} database(s)",
                data={"count": len(databases), "databases": databases}
            )

        except Exception as e:
            return RAGResponse(
                success=False,
                message=f"Failed to list databases: {str(e)}",
                error=str(e)
            )


# Create FastAPI app
app = FastAPI(
    title="RAG HTTP API",
    description="HTTP API wrapper for RAG system to work with Go MCP server",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create RAG server instance
rag_server = RAGHTTPServer()


@app.post("/initialize", response_model=RAGResponse)
async def initialize_rag(request: InitializeRAGRequest):
    """Initialize RAG system with documents"""
    return await rag_server.initialize_rag(request)


@app.post("/search", response_model=RAGResponse)
async def search_documents(request: SearchRequest):
    """Search for similar documents (vector search only)"""
    return await rag_server.search_documents(request)




@app.post("/status", response_model=RAGResponse)
async def get_system_status():
    """Get system status"""
    return await rag_server.get_system_status()


@app.get("/list_databases")
async def list_databases():
    """List all available databases"""
    return await rag_server.list_databases()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "rag-http-api"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG HTTP API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8008, help="Port to bind to")

    args = parser.parse_args()

    print(f"🚀 Starting RAG HTTP API Server on http://{args.host}:{args.port}")
    print(f"📋 Available endpoints:")
    print(f"   POST /initialize - Initialize RAG system (manual)")
    print(f"   POST /search - Search documents")
    print(f"   POST /status - Get system status")
    print(f"   GET /health - Health check")
    print(f"📚 API docs: http://{args.host}:{args.port}/docs")

    uvicorn.run(app, host=args.host, port=args.port)