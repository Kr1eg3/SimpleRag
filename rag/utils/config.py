import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Конфигурация RAG системы"""

    def __init__(self, config_file: Optional[str] = None):
        load_dotenv()
        self._config = self._load_default_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию по умолчанию"""
        return {
            # API Keys
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),

            # Database settings
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "persist_directory": "./chroma_db",
            "chunk_size": int(os.getenv("CHUNK_SIZE", 1000)),
            "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 200)),

            # LLM settings
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.3,
            "max_tokens": 2000,

            # Retrieval settings
            "default_k": 4,
            "search_type": "similarity"
        }

    def get(self, key: str, default=None):
        """Получить значение конфигурации"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Установить значение конфигурации"""
        self._config[key] = value

    def update(self, config_dict: Dict[str, Any]):
        """Обновить конфигурацию"""
        self._config.update(config_dict)