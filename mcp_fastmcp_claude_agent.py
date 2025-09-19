#!/usr/bin/env python3
"""
FastMCP Server with Claude Agent Integration (No API keys required)
Uses Claude Code as the LLM for answer generation
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


class ClaudeAgentRAGServer:
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
        """Get or create RAG manager for current user (without LLM)"""
        if not self.current_user or not self.user_info:
            return None

        if self.rag_manager:
            return self.rag_manager

        try:
            config = Config()

            # Set user-specific configuration
            user_persist_dir = f"./rag_data/{self.current_user}"
            config.set("persist_directory", user_persist_dir)

            # No LLM configuration - we'll use Claude Agent instead
            config.set("llm_provider", "claude_agent")

            # Create RAG manager without LLM
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

            # Don't setup QA chain - we'll use Claude Agent
            self.initialized = True

            return [TextContent(
                type="text",
                text=f"✅ RAG system initialized for user {self.current_user}!\n\n{message}\n\nConfiguration:\n- Chunk size: {chunk_size}\n- Chunk overlap: {chunk_overlap}\n- LLM Provider: Claude Agent (no API key required)\n- Vector search ready for queries"
            )]

        except Exception as e:
            raise ValueError(f"Failed to initialize RAG system: {str(e)}")

    async def search_documents(self, query: str, k: int = 5) -> List[TextContent]:
        """Search for similar documents and return raw results"""
        if not self.current_user:
            raise ValueError("No user selected. Set MCP_USER environment variable.")

        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager or not rag_manager.retriever:
            raise ValueError("RAG system not initialized.")

        try:
            results = rag_manager.search_documents(query, k=k)

            content_text = f"**User:** {self.current_user}\n**Search Results for:** {query}\n\n"

            sources_data = []
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                source_info = f"{i}. "
                if 'source' in metadata:
                    source_info += f"**File:** {metadata['source']}"
                if 'page' in metadata:
                    source_info += f" (Page {metadata['page']})"
                source_info += f" (Similarity: {result['similarity_score']:.3f})"
                source_info += f"\n   *Content:* {result['content']}\n\n"
                content_text += source_info

                # Store for Claude Agent
                sources_data.append({
                    "file": metadata.get('source', 'unknown'),
                    "content": result['content'],
                    "similarity": result['similarity_score']
                })

            return [TextContent(type="text", text=content_text)]

        except Exception as e:
            raise ValueError(f"Search failed: {str(e)}")

    async def query_with_claude_agent(self, question: str, k: int = 5) -> List[TextContent]:
        """Search documents and ask Claude Agent to generate answer"""
        if not self.current_user:
            raise ValueError("No user selected. Set MCP_USER environment variable.")

        rag_manager = self.get_or_create_rag_manager()
        if not rag_manager or not rag_manager.retriever:
            raise ValueError("RAG system not initialized.")

        try:
            # Get relevant documents
            results = rag_manager.search_documents(question, k=k)

            if not results:
                return [TextContent(
                    type="text",
                    text=f"**User:** {self.current_user}\n**Question:** {question}\n\n**Answer:** No relevant documents found for this question."
                )]

            # Prepare context for Claude Agent
            context_text = "Based on the following documents, please answer the question:\n\n"
            context_text += f"**Question:** {question}\n\n"
            context_text += "**Relevant Documents:**\n\n"

            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                source_name = metadata.get('source', f'Document {i}')
                context_text += f"{i}. **Source:** {source_name}\n"
                context_text += f"   **Content:** {result['content']}\n\n"

            context_text += "\nPlease provide a comprehensive answer based on the information above. If the documents don't contain enough information to answer the question, please say so."

            # Return the context for Claude Agent to process
            return [TextContent(
                type="text",
                text=f"**User:** {self.current_user}\n**Question:** {question}\n\n**Retrieved Context:**\n\n{context_text}\n\n**Note:** Claude Agent will now process this context to generate an answer."
            )]

        except Exception as e:
            raise ValueError(f"Query failed: {str(e)}")

    async def get_user_status(self) -> List[TextContent]:
        """Get current user status"""
        if not self.current_user:
            return [TextContent(type="text", text="❌ No user selected. Set MCP_USER environment variable.")]

        rag_manager = self.get_or_create_rag_manager()

        status_text = f"**User Status for {self.current_user}:**\n\n"
        status_text += f"✅ **LLM Provider:** Claude Agent (no API key required)\n"
        status_text += f"✅ **Vector Search:** Available\n"

        if rag_manager:
            status_text += f"✅ **RAG Manager:** Initialized\n"
            status_text += f"{'✅' if rag_manager.retriever else '❌'} **Retriever:** {'Ready' if rag_manager.retriever else 'Not initialized'}\n"
            status_text += f"✅ **Claude Agent Integration:** Ready\n"
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
    parser = argparse.ArgumentParser(description="Claude Agent RAG FastMCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8008, help="Port to bind to")
    parser.add_argument("--user", help="Default user to use")

    args = parser.parse_args()

    # Create server
    rag_server = ClaudeAgentRAGServer()

    # Set default user
    default_user = args.user or os.getenv("MCP_USER", "alice")
    if not rag_server.set_user(default_user):
        print(f"❌ Failed to set default user: {default_user}")
        return

    # Create FastMCP server
    mcp = FastMCP(
        name="rag-claude-agent",
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
    async def search_documents(
        query: str,
        k: int = 5
    ) -> List[TextContent]:
        """Search for similar documents (vector search only)"""
        return await rag_server.search_documents(query, k)

    @mcp.tool()
    async def query_with_claude_agent(
        question: str,
        k: int = 5
    ) -> List[TextContent]:
        """Search documents and prepare context for Claude Agent to answer"""
        return await rag_server.query_with_claude_agent(question, k)

    @mcp.tool()
    async def get_user_status() -> List[TextContent]:
        """Get current user system status"""
        return await rag_server.get_user_status()

    @mcp.tool()
    async def switch_user(username: str) -> List[TextContent]:
        """Switch to different user"""
        return await rag_server.switch_user(username)

    print(f"🚀 Starting Claude Agent RAG FastMCP Server on http://{args.host}:{args.port}")
    print(f"📋 MCP endpoint: http://{args.host}:{args.port}/mcp")
    print(f"🔄 SSE endpoint: http://{args.host}:{args.port}/sse")
    print(f"👤 Current user: {rag_server.current_user}")
    print(f"🤖 LLM: Claude Agent (no API key required)")

    # Run the HTTP server
    asyncio.run(mcp.run_streamable_http_async())


if __name__ == "__main__":
    main()