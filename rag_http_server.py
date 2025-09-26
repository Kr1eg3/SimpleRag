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
    load_existing: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200


class SearchRequest(BaseModel):
    query: str
    k: int = 5




# Response model
class RAGResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class RAGHTTPServer:
    def __init__(self):
        self.rag_manager: Optional[RAGManager] = None
        self.config: Optional[Config] = None
        self.initialized = False

        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Auto-initialize on startup
        self._auto_initialize()

    def get_or_create_rag_manager(self) -> Optional[RAGManager]:
        """Get or create RAG manager (without LLM)"""
        if self.rag_manager:
            return self.rag_manager

        try:
            config = Config()

            # Set default configuration
            persist_dir = "./rag_data"
            config.set("persist_directory", persist_dir)

            # No LLM configuration - we'll use Claude Agent instead
            config.set("llm_provider", "claude_agent")

            # Create RAG manager without LLM
            self.rag_manager = RAGManager(config)
            self.config = config

            return self.rag_manager

        except Exception as e:
            print(f"❌ Error creating RAG manager: {e}")
            return None

    def _auto_initialize(self):
        """Auto-initialize RAG system on startup"""
        try:
            print("🚀 Auto-initializing RAG system...")
            data_path = Path("./data")
            persist_dir = Path("./rag_data")

            # Get or create RAG manager
            rag_manager = self.get_or_create_rag_manager()
            if not rag_manager:
                print("❌ Failed to create RAG manager during auto-initialization")
                return

            # Check if we should load existing database or create new one
            if (persist_dir / "chroma.sqlite3").exists():
                rag_manager.load_existing_database()
                print("✅ Auto-initialization: Loaded existing database")
            elif data_path.exists():
                rag_manager.setup_database(
                    str(data_path),
                    chunk_size=1000,
                    chunk_overlap=200
                )
                print("✅ Auto-initialization: Created new database from ./data")
            else:
                print("⚠️  Auto-initialization: No data directory found, RAG system ready but empty")

            self.initialized = True
            print("✅ RAG system auto-initialized successfully!")

        except Exception as e:
            print(f"❌ Auto-initialization failed: {e}")
            print("💡 You can manually initialize using POST /initialize")

    async def initialize_rag(self, request: InitializeRAGRequest) -> RAGResponse:
        """Initialize RAG system"""
        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager:
            return RAGResponse(
                success=False,
                message="Failed to create RAG manager",
                error="Failed to create RAG manager"
            )

        try:
            # Setup database
            data_path_obj = Path(request.data_path)
            persist_dir = Path("./rag_data")

            if request.load_existing and (persist_dir / "chroma.sqlite3").exists():
                rag_manager.load_existing_database()
                message = "Loaded existing database"
            else:
                if not data_path_obj.exists():
                    return RAGResponse(
                        success=False,
                        message=f"Data path does not exist: {request.data_path}",
                        error=f"Data path does not exist: {request.data_path}"
                    )

                rag_manager.setup_database(
                    str(data_path_obj),
                    chunk_size=request.chunk_size,
                    chunk_overlap=request.chunk_overlap
                )
                message = f"Created new database from {request.data_path}"

            # Don't setup QA chain - we'll use Claude Agent
            self.initialized = True

            initialization_data = {
                "action": "created_new" if not request.load_existing or not (persist_dir / "chroma.sqlite3").exists() else "loaded_existing",
                "data_path": request.data_path,
                "chunk_size": request.chunk_size,
                "chunk_overlap": request.chunk_overlap,
                "llm_provider": "claude_agent",
                "vector_search_ready": True
            }

            return RAGResponse(
                success=True,
                message="RAG system initialized successfully",
                data=initialization_data
            )

        except Exception as e:
            return RAGResponse(
                success=False,
                message=f"Failed to initialize RAG system: {str(e)}",
                error=str(e)
            )

    async def search_documents(self, request: SearchRequest) -> RAGResponse:
        """Search for similar documents and return raw results"""
        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager or not rag_manager.retriever:
            return RAGResponse(
                success=False,
                message="RAG system not initialized",
                error="RAG system not initialized"
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
                message="Search completed successfully",
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
        rag_manager = self.get_or_create_rag_manager()

        status_data = {
            "llm_provider": "claude_agent",
            "vector_search_available": True,
            "rag_manager_initialized": rag_manager is not None,
            "retriever_ready": rag_manager.retriever is not None if rag_manager else False,
            "system_ready": self.initialized
        }

        return RAGResponse(
            success=True,
            message="System status retrieved successfully",
            data=status_data
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