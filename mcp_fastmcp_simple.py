#!/usr/bin/env python3
"""
Simple FastMCP Server with User Selection via Environment Variable
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP
from mcp.types import Tool, TextContent

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag import RAGManager, Config
from update_user_api_key import UserAPIKeyUpdater


class SimpleRAGServer:
    def __init__(self):
        self.rag_manager: Optional[RAGManager] = None
        self.config: Optional[Config] = None
        self.current_user: Optional[str] = None
        self.user_info: Optional[Dict] = None
        self.initialized = False

        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

    def set_user(self, username: str) -> bool:
        """Set current user from database"""
        try:
            updater = UserAPIKeyUpdater()
            user_info = updater.get_user_info(username)

            if not user_info:
                return False

            self.current_user = username
            self.user_info = user_info

            # Reset RAG manager when user changes
            self.rag_manager = None
            self.initialized = False

            print(f"✅ Current user set to: {username}")
            return True

        except Exception as e:
            print(f"❌ Error setting user: {e}")
            return False

    def get_or_create_rag_manager(self) -> Optional[RAGManager]:
        """Get or create RAG manager for current user"""
        if not self.current_user or not self.user_info:
            return None

        if self.rag_manager:
            return self.rag_manager

        try:
            config = Config()

            # Set user-specific configuration
            user_persist_dir = f"./rag_data/{self.current_user}"
            config.set("persist_directory", user_persist_dir)

            # Set LLM configuration based on user preferences
            if self.user_info["llm_provider"] == "anthropic" and self.user_info["anthropic_api_key"]:
                config.set("anthropic_api_key", self.user_info["anthropic_api_key"])
                config.set("model", self.user_info["model"])
                config.set("llm_provider", "anthropic")
            elif self.user_info["llm_provider"] == "openai" and self.user_info["openai_api_key"]:
                config.set("openai_api_key", self.user_info["openai_api_key"])
                config.set("model", self.user_info["model"])
                config.set("llm_provider", "openai")
            else:
                return None  # No valid API key

            config.set("temperature", self.user_info["temperature"])

            # Create RAG manager
            self.rag_manager = RAGManager(config)
            self.config = config

            return self.rag_manager

        except Exception as e:
            print(f"❌ Error creating RAG manager: {e}")
            return None

    async def initialize_rag(self, data_path: str = "./data", load_existing: bool = True,
                           chunk_size: int = 1000, chunk_overlap: int = 200) -> List[TextContent]:
        """Initialize RAG system for current user"""
        if not self.current_user:
            raise ValueError("No user selected. Set MCP_USER environment variable.")

        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager:
            raise ValueError("Failed to create RAG manager. Check user configuration.")

        try:
            # Setup database
            data_path_obj = Path(data_path)
            user_persist_dir = Path(f"./rag_data/{self.current_user}")

            if load_existing and (user_persist_dir / "chroma.sqlite3").exists():
                rag_manager.load_existing_database()
                message = f"Loaded existing database for user {self.current_user}"
            else:
                if not data_path_obj.exists():
                    raise ValueError(f"Data path does not exist: {data_path}")

                rag_manager.setup_database(
                    str(data_path_obj),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                message = f"Created new database for user {self.current_user} from {data_path}"

            # Setup QA chain
            rag_manager.setup_qa_chain()
            self.initialized = True

            return [TextContent(
                type="text",
                text=f"✅ RAG system initialized for user {self.current_user}!\n\n{message}\n\nConfiguration:\n- Chunk size: {chunk_size}\n- Chunk overlap: {chunk_overlap}\n- LLM Provider: {self.user_info['llm_provider']}\n- Model: {self.user_info['model']}"
            )]

        except Exception as e:
            raise ValueError(f"Failed to initialize RAG system: {str(e)}")

    async def query_rag(self, question: str, return_sources: bool = True) -> List[TextContent]:
        """Query RAG system for current user"""
        if not self.current_user:
            raise ValueError("No user selected. Set MCP_USER environment variable.")

        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager or not rag_manager.is_ready():
            raise ValueError("RAG system not initialized. Call initialize_rag first.")

        try:
            result = rag_manager.query(question, return_sources=return_sources)

            # Format response
            content = [TextContent(
                type="text",
                text=f"**User:** {self.current_user}\n**Question:** {result['question']}\n\n**Answer:** {result['answer']}"
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
        """Search for similar documents for current user"""
        if not self.current_user:
            raise ValueError("No user selected. Set MCP_USER environment variable.")

        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager or not rag_manager.retriever:
            raise ValueError("RAG system not initialized.")

        try:
            results = rag_manager.search_documents(query, k=k)

            content_text = f"**User:** {self.current_user}\n**Search Results for:** {query}\n\n"
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

    async def get_user_status(self) -> List[TextContent]:
        """Get current user status"""
        if not self.current_user:
            return [TextContent(type="text", text="❌ No user selected. Set MCP_USER environment variable.")]

        rag_manager = self.get_or_create_rag_manager()

        status_text = f"**User Status for {self.current_user}:**\n\n"
        status_text += f"✅ **LLM Provider:** {self.user_info['llm_provider']}\n"
        status_text += f"✅ **Model:** {self.user_info['model']}\n"
        status_text += f"✅ **Temperature:** {self.user_info['temperature']}\n"

        if rag_manager:
            status_text += f"✅ **RAG Manager:** Initialized\n"
            status_text += f"{'✅' if rag_manager.retriever else '❌'} **Retriever:** {'Ready' if rag_manager.retriever else 'Not initialized'}\n"
            status_text += f"{'✅' if rag_manager.qa_chain else '❌'} **QA Chain:** {'Ready' if rag_manager.qa_chain else 'Not initialized'}\n"
        else:
            status_text += f"❌ **RAG Manager:** Not initialized\n"

        return [TextContent(type="text", text=status_text)]

    async def switch_user(self, username: str) -> List[TextContent]:
        """Switch to different user"""
        if self.set_user(username):
            return [TextContent(type="text", text=f"✅ Switched to user: {username}")]
        else:
            return [TextContent(type="text", text=f"❌ Failed to switch to user: {username}")]


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Simple RAG FastMCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8007, help="Port to bind to")
    parser.add_argument("--user", help="Default user to use")

    args = parser.parse_args()

    # Create server
    rag_server = SimpleRAGServer()

    # Set default user
    default_user = args.user or os.getenv("MCP_USER", "alice")
    if not rag_server.set_user(default_user):
        print(f"❌ Failed to set default user: {default_user}")
        return

    # Create FastMCP server
    mcp = FastMCP(
        name="rag-simple-fastmcp",
        host=args.host,
        port=args.port,
        debug=True
    )

    # Register tools
    @mcp.tool()
    async def initialize_rag(
        data_path: str = "./data",
        load_existing: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[TextContent]:
        """Initialize RAG system with documents for current user"""
        return await rag_server.initialize_rag(data_path, load_existing, chunk_size, chunk_overlap)

    @mcp.tool()
    async def query_rag(
        question: str,
        return_sources: bool = True
    ) -> List[TextContent]:
        """Query the RAG system for current user"""
        return await rag_server.query_rag(question, return_sources)

    @mcp.tool()
    async def search_similar(
        query: str,
        k: int = 5
    ) -> List[TextContent]:
        """Search for similar documents for current user"""
        return await rag_server.search_similar(query, k)

    @mcp.tool()
    async def get_user_status() -> List[TextContent]:
        """Get current user system status"""
        return await rag_server.get_user_status()

    @mcp.tool()
    async def switch_user(username: str) -> List[TextContent]:
        """Switch to different user"""
        return await rag_server.switch_user(username)

    print(f"🚀 Starting Simple RAG FastMCP Server on http://{args.host}:{args.port}")
    print(f"📋 MCP endpoint: http://{args.host}:{args.port}/mcp")
    print(f"🔄 SSE endpoint: http://{args.host}:{args.port}/sse")
    print(f"👤 Current user: {rag_server.current_user}")

    # Run the HTTP server
    asyncio.run(mcp.run_streamable_http_async())


if __name__ == "__main__":
    main()