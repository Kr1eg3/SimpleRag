from typing import Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from .prompts import DefaultPrompts


class LLMManager:
    """Менеджер для работы с LLM"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        self.llm = ChatAnthropic(
            anthropic_api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.prompts = DefaultPrompts()

    def create_qa_chain(
        self,
        retriever,
        prompt_template: Optional[str] = None,
        chain_type: str = "stuff"
    ) -> RetrievalQA:
        """Создать цепочку вопрос-ответ"""
        template = prompt_template or self.prompts.get_qa_template()

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type=chain_type,
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )

    def generate_response(self, qa_chain, question: str) -> Dict[str, Any]:
        """Сгенерировать ответ на вопрос"""
        result = qa_chain.invoke({"query": question})

        return {
            "question": question,
            "answer": result["result"],
            "source_documents": result.get("source_documents", [])
        }