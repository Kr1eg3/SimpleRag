from typing import Dict, Any, Optional, List
from pathlib import Path

from .database.builder import DatabaseBuilder
from .retrieval.retriever import Retriever
from .generation.llm_manager import LLMManager
from .utils.config import Config


class RAGManager:
    """Главный менеджер RAG системы - объединяет все компоненты"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

        # Инициализация компонентов
        self.db_builder = DatabaseBuilder(
            embedding_model=self.config.get("embedding_model"),
            persist_directory=self.config.get("persist_directory")
        )

        self.retriever = None
        self.llm_manager = None
        self.qa_chain = None

        # Инициализируем LLM если есть API ключ
        api_key = self.config.get("anthropic_api_key")
        if api_key:
            self.llm_manager = LLMManager(
                api_key=api_key,
                model=self.config.get("model"),
                temperature=self.config.get("temperature"),
                max_tokens=self.config.get("max_tokens")
            )

    def setup_database(
        self,
        data_path: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        """Настроить базу данных из документов"""
        chunk_size = chunk_size or self.config.get("chunk_size")
        chunk_overlap = chunk_overlap or self.config.get("chunk_overlap")

        # Загрузить документы
        self.db_builder.load_documents(data_path)

        # Создать векторную БД
        vectorstore = self.db_builder.create_vectorstore(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Инициализировать ретривер
        self.retriever = Retriever(vectorstore)
        self.retriever.set_default_k(self.config.get("default_k"))

    def load_existing_database(self):
        """Загрузить существующую базу данных"""
        vectorstore = self.db_builder.load_vectorstore()
        self.retriever = Retriever(vectorstore)
        self.retriever.set_default_k(self.config.get("default_k"))

    def setup_qa_chain(self, prompt_template: Optional[str] = None):
        """Настроить цепочку вопрос-ответ"""
        if not self.retriever:
            raise ValueError("Database not set up. Call setup_database() first")

        if not self.llm_manager:
            raise ValueError("LLM manager not initialized. Check API key")

        retriever_obj = self.retriever.get_retriever()
        self.qa_chain = self.llm_manager.create_qa_chain(
            retriever=retriever_obj,
            prompt_template=prompt_template
        )

    def query(self, question: str, return_sources: bool = True) -> Dict[str, Any]:
        """Задать вопрос системе"""
        if not self.qa_chain:
            raise ValueError("QA chain not set up. Call setup_qa_chain() first")

        # Получить ответ
        response = self.llm_manager.generate_response(self.qa_chain, question)

        # Форматировать результат
        result = {
            "question": question,
            "answer": response["answer"],
            "sources": []
        }

        # Добавить источники если нужно
        if return_sources and response.get("source_documents"):
            seen_content = set()
            for doc in response["source_documents"]:
                content_preview = doc.page_content[:200]
                if content_preview not in seen_content:
                    seen_content.add(content_preview)
                    source_info = {
                        "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                        "metadata": doc.metadata
                    }
                    result["sources"].append(source_info)

        return result

    def search_documents(self, query: str, k: Optional[int] = None, include_ids: bool = True) -> List[Dict]:
        """Поиск документов без генерации ответа"""
        if not self.retriever:
            raise ValueError("Database not set up")

        if include_ids:
            # Используем новый метод с ID
            return self.retriever.search_with_scores_and_ids(query, k=k)
        else:
            # Старый метод без ID
            results = self.retriever.search_with_scores(query, k=k)
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score
                })
            return formatted_results

    def is_ready(self) -> bool:
        """Проверить готовность системы"""
        return all([
            self.retriever is not None,
            self.llm_manager is not None,
            self.qa_chain is not None
        ])