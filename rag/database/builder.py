from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from .loaders import DocumentLoader
from .processors import TextProcessor


class DatabaseBuilder:
    """Гибкий класс для создания и управления векторной базой данных"""

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: str = "./chroma_db"
    ):
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'}
        )
        self.vectorstore = None
        self.documents = []

    def load_documents(self, source_path: str, **kwargs) -> List[Document]:
        """Загрузить документы из источника"""
        loader = DocumentLoader()
        self.documents = loader.load_from_path(source_path, **kwargs)
        return self.documents

    def process_documents(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ) -> List[Document]:
        """Обработать и разделить документы на чанки"""
        processor = TextProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        processed_docs = processor.split_documents(self.documents, **kwargs)
        return processed_docs

    def create_vectorstore(
        self,
        documents: Optional[List[Document]] = None,
        **kwargs
    ) -> Chroma:
        """Создать векторную базу данных"""
        docs_to_process = documents or self.documents

        if not docs_to_process:
            raise ValueError("No documents to process")

        # Обработаем документы если нужно
        processed_docs = self.process_documents(**kwargs)

        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma.from_documents(
            documents=processed_docs,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )

        return self.vectorstore

    def load_vectorstore(self) -> Chroma:
        """Загрузить существующую векторную БД"""
        if not Path(self.persist_directory).exists():
            raise ValueError(f"Directory {self.persist_directory} does not exist")

        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )

        return self.vectorstore

    def get_vectorstore(self) -> Optional[Chroma]:
        """Получить текущую векторную БД"""
        return self.vectorstore