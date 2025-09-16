from typing import List, Dict, Callable
from pathlib import Path
from langchain.schema import Document
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader
)


class DocumentLoader:
    """Загрузчик документов различных форматов"""

    def __init__(self):
        self.loaders: Dict[str, Callable] = {
            '.txt': lambda p: TextLoader(str(p), encoding='utf-8'),
            '.pdf': lambda p: PyPDFLoader(str(p)),
            '.csv': lambda p: CSVLoader(str(p), encoding='utf-8')
        }

    def add_loader(self, extension: str, loader_func: Callable):
        """Добавить новый загрузчик для расширения файла"""
        self.loaders[extension] = loader_func

    def load_from_path(self, source_path: str, **kwargs) -> List[Document]:
        """Загрузить документы из файла или папки"""
        path = Path(source_path)
        documents = []

        if path.is_file():
            documents = self._load_single_file(path)
        elif path.is_dir():
            documents = self._load_directory(path)
        else:
            raise ValueError(f"Path {source_path} does not exist")

        return documents

    def _load_single_file(self, file_path: Path) -> List[Document]:
        """Загрузить один файл"""
        extension = file_path.suffix.lower()

        if extension not in self.loaders:
            raise ValueError(f"Unsupported file type: {extension}")

        loader = self.loaders[extension](file_path)
        return loader.load()

    def _load_directory(self, dir_path: Path) -> List[Document]:
        """Загрузить все поддерживаемые файлы из папки"""
        documents = []

        for extension, loader_func in self.loaders.items():
            files = list(dir_path.glob(f"*{extension}"))
            for file_path in files:
                try:
                    loader = loader_func(file_path)
                    docs = loader.load()
                    documents.extend(docs)
                except Exception as e:
                    print(f"Error loading {file_path.name}: {e}")

        return documents