class DefaultPrompts:
    """Коллекция готовых промптов"""

    @staticmethod
    def get_qa_template() -> str:
        """Стандартный промпт для вопрос-ответ"""
        return """You are a helpful assistant that answers questions using the provided context.

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

    @staticmethod
    def get_summary_template() -> str:
        """Промпт для суммаризации"""
        return """Summarize the following text concisely:

Text:
{context}

Summary:"""