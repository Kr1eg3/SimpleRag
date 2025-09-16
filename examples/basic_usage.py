"""
Базовый пример использования модульной RAG системы
"""

from pathlib import Path
from rag import RAGManager


def main():
    # Создаем RAG менеджер
    rag = RAGManager()

    # Проверяем есть ли существующая база
    if Path("./chroma_db").exists():
        print("Загружаем существующую базу данных...")
        rag.load_existing_database()
    else:
        print("Создаем новую базу данных из документов...")
        rag.setup_database("./data")

    # Настраиваем цепочку вопрос-ответ
    rag.setup_qa_chain()

    # Проверяем готовность
    if not rag.is_ready():
        print("Система не готова к работе!")
        return

    # Интерактивный режим
    print("\n" + "="*50)
    print("RAG Система готова к работе!")
    print("Команды: 'exit' - выход, 'search: <запрос>' - поиск документов")
    print("="*50 + "\n")

    while True:
        try:
            user_input = input("Ваш вопрос: ").strip()

            if user_input.lower() in ['exit', 'quit']:
                break

            if user_input.startswith('search:'):
                query = user_input[7:].strip()
                results = rag.search_documents(query, k=3)
                print("\nНайденные документы:")
                for i, result in enumerate(results, 1):
                    print(f"{i}. Релевантность: {result['similarity_score']:.3f}")
                    print(f"   {result['content'][:200]}...")
                    print("-" * 40)
                continue

            if not user_input:
                continue

            # Получаем ответ
            response = rag.query(user_input)

            print(f"\nОтвет: {response['answer']}")

            if response['sources']:
                print(f"\nИсточники ({len(response['sources'])}):")
                for i, source in enumerate(response['sources'], 1):
                    print(f"{i}. {source['content'][:150]}...")

        except KeyboardInterrupt:
            print("\nПрограмма прервана")
            break
        except Exception as e:
            print(f"Ошибка: {e}")

    print("До свидания!")


if __name__ == "__main__":
    main()