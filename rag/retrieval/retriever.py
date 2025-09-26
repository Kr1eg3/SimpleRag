from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_chroma import Chroma


class Retriever:
    """Класс для поиска и извлечения релевантных документов"""

    def __init__(self, vectorstore: Chroma):
        self.vectorstore = vectorstore
        self.default_k = 4

    def search(
        self,
        query: str,
        k: Optional[int] = None,
        search_type: str = "similarity",
        **kwargs
    ) -> List[Document]:
        """Базовый поиск документов"""
        k = k or self.default_k

        if search_type == "similarity":
            return self.vectorstore.similarity_search(query, k=k, **kwargs)
        elif search_type == "similarity_with_score":
            results = self.vectorstore.similarity_search_with_score(query, k=k, **kwargs)
            return [doc for doc, score in results]
        else:
            raise ValueError(f"Unknown search type: {search_type}")

    def search_with_scores(
        self,
        query: str,
        k: Optional[int] = None,
        **kwargs
    ) -> List[tuple]:
        """Поиск с оценками релевантности"""
        k = k or self.default_k
        return self.vectorstore.similarity_search_with_score(query, k=k, **kwargs)

    def search_with_scores_and_ids(
        self,
        query: str,
        k: Optional[int] = None,
        **kwargs
    ) -> List[Dict]:
        """Поиск с оценками релевантности и ID чанков"""
        k = k or self.default_k

        # Получаем результаты с score и ids
        results_with_scores = self.vectorstore.similarity_search_with_score(query, k=k, **kwargs)

        formatted_results = []
        for doc, score in results_with_scores:
            # ChromaDB автоматически генерирует ID для каждого документа
            chunk_id = getattr(doc, 'id', None) or doc.metadata.get('chunk_id', 'unknown')

            formatted_results.append({
                "id": chunk_id,
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": score
            })

        return formatted_results

    def search_with_metadata_filter(
        self,
        query: str,
        metadata_filter: Dict[str, Any],
        k: Optional[int] = None,
        **kwargs
    ) -> List[Document]:
        """Поиск с фильтрацией по метаданным"""
        k = k or self.default_k
        return self.vectorstore.similarity_search(
            query,
            k=k,
            filter=metadata_filter,
            **kwargs
        )

    def get_retriever(self, **kwargs):
        """Получить LangChain retriever объект"""
        return self.vectorstore.as_retriever(
            search_kwargs={"k": self.default_k, **kwargs}
        )

    def set_default_k(self, k: int):
        """Установить количество документов по умолчанию"""
        self.default_k = k