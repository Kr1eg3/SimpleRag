import os
import sys
from typing import List, Dict, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import (
        TextLoader,
        PyPDFLoader,
        CSVLoader,
        DirectoryLoader
    )
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_anthropic import ChatAnthropic
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите зависимости: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()


class RAGSystem:
    def __init__(self, anthropic_api_key: str = None):
        """
        Инициализация RAG системы

        Args:
            anthropic_api_key: API ключ для Claude (если не указан, берется из .env)
        """
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Необходим ANTHROPIC_API_KEY")

        # Инициализация компонентов
        self.documents = []
        self.vectorstore = None
        self.qa_chain = None

        # Настройка эмбеддингов (используем бесплатную модель)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        # Настройка Claude
        self.llm = ChatAnthropic(
            anthropic_api_key=self.api_key,
            model="claude-3-5-sonnet-20241022",  # Актуальная модель
            temperature=0.3,
            max_tokens=2000
        )

    def load_documents(self, data_path: str, file_type: str = "auto") -> List[Document]:
        """
        Load documents from specified directory or file

        Args:
            data_path: path to data (file or directory)
            file_type: file type ('txt', 'pdf', 'csv', 'auto')

        Returns:
            List[Document]: loaded documents
        """
        data_path = Path(data_path)
        print(f"Loading documents from {data_path}...")

        if data_path.is_file():
            # Load single file
            if file_type == "auto":
                file_type = data_path.suffix[1:]  # remove dot

            loader_map = {
                'txt': lambda p: TextLoader(str(p), encoding='utf-8'),
                'pdf': lambda p: PyPDFLoader(str(p)),
                'csv': lambda p: CSVLoader(str(p), encoding='utf-8')
            }


            if file_type not in loader_map:
                raise ValueError(f"Unsupported file type: {file_type}")

            loader = loader_map[file_type](data_path)
            self.documents = loader.load()
            print(f"Loaded file: {data_path.name}")

        elif data_path.is_dir():
            # Load all files from directory
            self.documents = []

            # Dictionary of extensions and loaders
            loaders = {
                '*.txt': lambda p: TextLoader(str(p), encoding='utf-8'),
                '*.pdf': lambda p: PyPDFLoader(str(p)),
                '*.csv': lambda p: CSVLoader(str(p), encoding='utf-8')
            }

            for pattern, loader_func in loaders.items():
                files = list(data_path.glob(pattern))
                for file_path in files:
                    try:
                        loader = loader_func(file_path)
                        docs = loader.load()
                        self.documents.extend(docs)
                        print(f"Loaded: {file_path.name}")
                    except Exception as e:
                        print(f"Error loading {file_path.name}: {e}")

        else:
            raise ValueError(f"Path {data_path} does not exist")

        print(f"Total documents loaded: {len(self.documents)}")
        return self.documents

    def split_documents(
            self,
            chunk_size: int = 1000,
            chunk_overlap: int = 200
    ) -> List[Document]:
        """
        Split documents into chunks for better search

        Args:
            chunk_size: size of one chunk in characters
            chunk_overlap: overlap between chunks

        Returns:
            List[Document]: split documents
        """
        if not self.documents:
            raise ValueError("Load documents first")

        print("Splitting documents into chunks...")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        split_docs = text_splitter.split_documents(self.documents)
        print(f"Created {len(split_docs)} chunks")
        print(f"Average chunk size: {sum(len(d.page_content) for d in split_docs) / len(split_docs):.0f} characters")

        return split_docs

    def create_vectorstore(
            self,
            persist_directory: str = "./chroma_db",
            chunk_size: int = 1000,
            chunk_overlap: int = 200
    ) -> Chroma:
        """
        Create vector store from documents

        Args:
            persist_directory: directory for saving vectors
            chunk_size: chunk size
            chunk_overlap: chunk overlap

        Returns:
            Chroma: vector store
        """
        if not self.documents:
            raise ValueError("Load documents first")

        print("Creating vector store...")

        # Split documents into chunks
        split_docs = self.split_documents(chunk_size, chunk_overlap)

        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Create vector store
        self.vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )

        print(f"Vector store created in {persist_directory}")
        # Chroma creates multiple vectors per document for optimization

        return self.vectorstore

    def load_vectorstore(self, persist_directory: str = "./chroma_db") -> Chroma:
        """
        Load existing vector store

        Args:
            persist_directory: directory with saved vectors

        Returns:
            Chroma: vector store
        """
        if not Path(persist_directory).exists():
            raise ValueError(f"Directory {persist_directory} does not exist")

        print(f"Loading vector store from {persist_directory}...")

        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )

        print("Vector store loaded successfully")

        return self.vectorstore

    def create_qa_chain(self, k: int = 4, chain_type: str = "stuff") -> RetrievalQA:
        """
        Create question-answer chain using RAG

        Args:
            k: number of relevant documents to retrieve
            chain_type: chain type ('stuff', 'map_reduce', 'refine')

        Returns:
            RetrievalQA: QA chain
        """
        if not self.vectorstore:
            raise ValueError("Create or load vector store first")

        # Setup prompt
        prompt_template = """You are a helpful assistant that answers questions using the provided context.

Instructions:
1. Use ONLY information from the context below to answer
2. If the context doesn't contain the needed information, say so honestly
3. Answer in detail and structured manner
4. Use examples from context if available
5. Maintain factual accuracy

Context:
{context}

Question: {question}

Answer:"""

        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )

        # Create retriever
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": k
            }
        )

        # Create QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type=chain_type,
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )

        print(f"QA chain created (k={k}, type={chain_type})")
        return self.qa_chain

    def query(
            self,
            question: str,
            return_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Ask question to the system

        Args:
            question: user question
            return_sources: whether to return sources

        Returns:
            dict with answer and sources
        """
        if not self.qa_chain:
            raise ValueError("Create QA chain first")

        print(f"\nProcessing question: {question}")

        # Get answer
        result = self.qa_chain.invoke({"query": question})

        # Format result
        response = {
            "question": question,
            "answer": result["result"],
            "sources": []
        }

        # Add source information
        if return_sources and "source_documents" in result:
            seen_content = set()
            for doc in result["source_documents"]:
                # Avoid duplicates
                content_preview = doc.page_content[:200]
                if content_preview not in seen_content:
                    seen_content.add(content_preview)
                    source_info = {
                        "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": getattr(doc, 'score', None)
                    }
                    response["sources"].append(source_info)

        return response

    def search_similar(
            self,
            query: str,
            k: int = 5
    ) -> List[Document]:
        """
        Search similar documents without generating answer

        Args:
            query: search query
            k: number of results

        Returns:
            List[Document]: found documents
        """
        if not self.vectorstore:
            raise ValueError("Create vector store first")

        results = self.vectorstore.similarity_search_with_score(query, k=k)

        print(f"\nFound {len(results)} similar documents for: '{query}'")
        for i, (doc, score) in enumerate(results, 1):
            print(f"{i}. Similarity: {score:.3f} | Page: {doc.metadata.get('page', 'N/A')}")
            print(f"   Content: {doc.page_content[:200]}...")
            print("-" * 40)

        return [doc for doc, _ in results]

    def interactive_mode(self):
        """Interactive mode for asking questions"""
        print("\n" + "=" * 50)
        print("Interactive RAG Mode")
        print("=" * 50)
        print("Commands:")
        print("  'exit' / 'quit' - finish")
        print("  'search: <query>' - find similar documents")
        print("  Any other text - ask question")
        print("=" * 50 + "\n")

        while True:
            try:
                user_input = input("\nYour question: ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\nGoodbye!")
                    break

                if user_input.startswith('search:'):
                    query = user_input[7:].strip()
                    self.search_similar(query, k=3)
                    continue

                if not user_input:
                    continue

                # Get answer
                response = self.query(user_input)

                # Print answer
                print("\n" + "=" * 50)
                print("ANSWER:")
                print("=" * 50)
                print(response["answer"])

                # Print sources
                if response["sources"]:
                    print("\n" + "-" * 50)
                    print("SOURCES:")
                    print("-" * 50)
                    for i, source in enumerate(response["sources"], 1):
                        print(f"\n{i}. {source['content']}")
                        if source['metadata']:
                            print(f"   Metadata: {source['metadata']}")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                print(f"\nError: {e}")
                print("Try again or type 'exit' to finish")


if __name__ == '__main__':
    try:
        rag = RAGSystem()

        # Check if vector store already exists
        chroma_path = "./chroma_db"
        if Path(chroma_path).exists():
            print("Found existing vector store. Use it? (y/n): ", end="")
            if input().lower() == 'y':
                rag.load_vectorstore(chroma_path)
            else:
                rag.load_documents("./data")  # или путь к вашим документам
                rag.create_vectorstore()
        else:
            rag.load_documents("./data")  # или путь к вашим документам
            rag.create_vectorstore()

        rag.create_qa_chain()
        rag.interactive_mode()
        print("End of prog")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()