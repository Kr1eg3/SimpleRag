#!/usr/bin/env python3
"""
FastMCP-based RAG Server
Uses the official FastMCP for HTTP transport
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP
from mcp.types import Tool, TextContent

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag import RAGManager, Config


class RAGFastMCPServer:
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

    async def initialize_rag(self, data_path: str = "./data", load_existing: bool = True,
                           chunk_size: int = 1000, chunk_overlap: int = 200) -> List[TextContent]:
        """Initialize RAG system"""
        try:
            # Create config
            self.config = Config()

            # Initialize RAG manager
            self.rag_manager = RAGManager(self.config)

            # Setup database
            data_path_obj = Path(data_path)
            if load_existing and (Path(self.config.get("persist_directory")) / "chroma.sqlite3").exists():
                self.rag_manager.load_existing_database()
                message = f"Loaded existing database from {self.config.get('persist_directory')}"
            else:
                if not data_path_obj.exists():
                    raise ValueError(f"Data path does not exist: {data_path}")

                self.rag_manager.setup_database(
                    str(data_path_obj),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                message = f"Created new database from {data_path}"

            self.initialized = True

            return [TextContent(
                type="text",
                text=f"✅ RAG system initialized successfully!\n\n{message}\n\nConfiguration:\n- Chunk size: {chunk_size}\n- Chunk overlap: {chunk_overlap}\n- Persist directory: {self.config.get('persist_directory')}"
            )]

        except Exception as e:
            raise ValueError(f"Failed to initialize RAG system: {str(e)}")

    async def configure_rag(self, api_key: str, model: str = "claude-3-5-sonnet-20241022",
                          temperature: float = 0.3) -> List[TextContent]:
        """Configure LLM provider"""
        try:
            if not self.rag_manager:
                raise ValueError("RAG system not initialized. Call initialize_rag first.")

            # Update config with new LLM settings
            self.config.set("anthropic_api_key", api_key)
            self.config.set("model", model)
            self.config.set("temperature", temperature)

            # Reinitialize LLM manager
            from rag.generation.llm_manager import LLMManager
            self.rag_manager.llm_manager = LLMManager(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=self.config.get("max_tokens")
            )

            # Setup QA chain
            self.rag_manager.setup_qa_chain()

            return [TextContent(
                type="text",
                text=f"✅ LLM configured successfully!\n\nConfiguration:\n- Model: {model}\n- Temperature: {temperature}\n- Max tokens: {self.config.get('max_tokens')}"
            )]

        except Exception as e:
            raise ValueError(f"Failed to configure LLM: {str(e)}")

    async def query_rag(self, question: str, return_sources: bool = True) -> List[TextContent]:
        """Query RAG system"""
        try:
            if not self.rag_manager or not self.rag_manager.is_ready():
                raise ValueError("RAG system not ready. Initialize and configure first.")

            result = self.rag_manager.query(question, return_sources=return_sources)

            # Format response
            content = [TextContent(
                type="text",
                text=f"**Question:** {result['question']}\n\n**Answer:** {result['answer']}"
            )]

            if return_sources and result['sources']:
                sources_text = "\n\n**Sources:**\n"
                for i, source in enumerate(result['sources'], 1):
                    metadata = source.get('metadata', {})
                    source_info = f"\n{i}. "
                    if 'source' in metadata:
                        source_info += f"**File:** {metadata['source']}"
                    if 'page' in metadata:
                        source_info += f" (Page {metadata['page']})"
                    source_info += f"\n   *Content:* {source['content'][:300]}{'...' if len(source['content']) > 300 else ''}\n"
                    sources_text += source_info

                content.append(TextContent(type="text", text=sources_text))

            return content

        except Exception as e:
            raise ValueError(f"Query failed: {str(e)}")

    async def search_similar(self, query: str, k: int = 5) -> List[TextContent]:
        """Search for similar documents"""
        try:
            if not self.rag_manager or not self.rag_manager.retriever:
                raise ValueError("RAG system not initialized.")

            results = self.rag_manager.search_documents(query, k=k)

            content_text = f"**Search Results for:** {query}\n\n"
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                source_info = f"{i}. "
                if 'source' in metadata:
                    source_info += f"**File:** {metadata['source']}"
                if 'page' in metadata:
                    source_info += f" (Page {metadata['page']})"
                source_info += f" (Similarity: {result['similarity_score']:.3f})"
                source_info += f"\n   *Content:* {result['content'][:300]}{'...' if len(result['content']) > 300 else ''}\n\n"
                content_text += source_info

            return [TextContent(type="text", text=content_text)]

        except Exception as e:
            raise ValueError(f"Search failed: {str(e)}")

    async def get_system_status(self) -> List[TextContent]:
        """Get system status"""
        status = {
            "initialized": self.initialized,
            "rag_manager": self.rag_manager is not None,
            "retriever": self.rag_manager.retriever is not None if self.rag_manager else False,
            "llm_manager": self.rag_manager.llm_manager is not None if self.rag_manager else False,
            "qa_chain": self.rag_manager.qa_chain is not None if self.rag_manager else False,
            "ready": self.rag_manager.is_ready() if self.rag_manager else False
        }

        status_text = "**RAG System Status:**\n\n"
        for key, value in status.items():
            emoji = "✅" if value else "❌"
            status_text += f"{emoji} **{key.replace('_', ' ').title()}:** {value}\n"

        if self.config:
            status_text += f"\n**Configuration:**\n"
            status_text += f"- Persist directory: {self.config.get('persist_directory')}\n"
            status_text += f"- Embedding model: {self.config.get('embedding_model')}\n"
            status_text += f"- Default k: {self.config.get('default_k')}\n"

        return [TextContent(type="text", text=status_text)]


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="RAG FastMCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8005, help="Port to bind to")

    args = parser.parse_args()

    # Create FastMCP server
    mcp = FastMCP(
        name="rag-fastmcp-server",
        host=args.host,
        port=args.port,
        debug=True
    )

    # Initialize RAG server
    rag_server = RAGFastMCPServer()

    # Register tools
    @mcp.tool()
    async def initialize_rag(
        data_path: str = "./data",
        load_existing: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[TextContent]:
        """Initialize RAG system with documents"""
        return await rag_server.initialize_rag(data_path, load_existing, chunk_size, chunk_overlap)

    @mcp.tool()
    async def configure_rag(
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3
    ) -> List[TextContent]:
        """Configure LLM provider for RAG system"""
        return await rag_server.configure_rag(api_key, model, temperature)

    @mcp.tool()
    async def query_rag(
        question: str,
        return_sources: bool = True
    ) -> List[TextContent]:
        """Query the RAG system"""
        return await rag_server.query_rag(question, return_sources)

    @mcp.tool()
    async def search_similar(
        query: str,
        k: int = 5
    ) -> List[TextContent]:
        """Search for similar documents"""
        return await rag_server.search_similar(query, k)

    @mcp.tool()
    async def get_system_status() -> List[TextContent]:
        """Get RAG system status"""
        return await rag_server.get_system_status()

    print(f"🚀 Starting RAG FastMCP Server on http://{args.host}:{args.port}")
    print(f"📋 MCP endpoint: http://{args.host}:{args.port}/mcp")
    print(f"🔄 SSE endpoint: http://{args.host}:{args.port}/sse")

    # Run the HTTP server
    asyncio.run(mcp.run_streamable_http_async())


if __name__ == "__main__":
    main()