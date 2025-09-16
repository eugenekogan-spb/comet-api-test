"""
Страница настроек
"""
import streamlit as st
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from llm_runner.core.providers.comet import CometProvider


def main():
    st.header("⚙️ Настройки")
    
    show_settings_interface()


def show_settings_interface():
    """Показывает интерфейс настроек"""
    
    # Создаем вкладки
    tab1, tab2, tab3 = st.tabs(["🔑 API Ключи", "🤖 Модели", "ℹ️ О приложении"])
    
    with tab1:
        show_api_settings()
    
    with tab2:
        show_model_settings()
    
    with tab3:
        show_about()


def show_api_settings():
    """Показывает настройки API"""
    st.subheader("🔑 Настройки API")
    
    st.markdown("### Comet API")
    
    # Проверяем текущие настройки
    current_key = os.getenv("COMET_API_KEY")
    current_url = os.getenv("COMET_BASE_URL", "https://api.cometapi.com")
    
    if current_key:
        st.success("✅ COMET_API_KEY настроен")
        st.code(f"Ключ: {current_key[:8]}...{current_key[-4:]}")
    else:
        st.error("❌ COMET_API_KEY не найден")
    
    st.info(f"🌐 Base URL: {current_url}")
    
    # Инструкции по настройке
    st.markdown("### 📝 Инструкции по настройке")
    
    st.markdown("""
    1. **Создайте файл `.env`** в корне проекта (если его нет)
    2. **Добавьте ваш API ключ Comet:**
       ```
       COMET_API_KEY=your_actual_api_key_here
       COMET_BASE_URL=https://api.cometapi.com
       ```
    3. **Перезапустите приложение**
    
    ⚠️ **Важно:** Никогда не добавляйте API ключи в код или в Git!
    """)
    
    # Тест подключения
    st.markdown("### 🧪 Тест подключения")
    
    if st.button("🔍 Проверить подключение к Comet API"):
        if not current_key:
            st.error("❌ Сначала настройте COMET_API_KEY в .env файле")
        else:
            try:
                provider = CometProvider()
                # Тестируем с простой моделью
                test_result = provider.generate(
                    messages=[{"role": "user", "content": "Hi"}],
                    model="comet-7b",
                    max_tokens=5
                )
                
                if test_result.error:
                    st.error(f"❌ Ошибка подключения: {test_result.error}")
                else:
                    st.success("✅ Подключение к Comet API работает!")
                    st.info(f"Тестовый ответ: {test_result.text}")
                    
            except Exception as e:
                st.error(f"❌ Ошибка: {e}")


def show_model_settings():
    """Показывает настройки моделей"""
    st.subheader("🤖 Настройки моделей")
    
    st.markdown("### Доступные модели")
    
    # Список популярных моделей
    models_info = {
        "gpt-3.5-turbo": {
            "name": "GPT-3.5 Turbo",
            "description": "Быстрая и эффективная модель OpenAI",
            "max_tokens": 4000,
            "recommended_temp": 0.7
        },
        "gpt-4": {
            "name": "GPT-4", 
            "description": "Мощная модель OpenAI с улучшенными возможностями",
            "max_tokens": 4000,
            "recommended_temp": 0.7
        },
        "gpt-4-turbo": {
            "name": "GPT-4 Turbo",
            "description": "Быстрая версия GPT-4 с увеличенным контекстом",
            "max_tokens": 4000,
            "recommended_temp": 0.7
        }
    }
    
    for model_id, info in models_info.items():
        with st.expander(f"🤖 {info['name']} ({model_id})"):
            st.markdown(f"**Описание:** {info['description']}")
            st.markdown(f"**Максимум токенов:** {info['max_tokens']}")
            st.markdown(f"**Рекомендуемая температура:** {info['recommended_temp']}")
            
            # Тест модели
            if st.button(f"🧪 Тестировать {model_id}", key=f"test_{model_id}"):
                if not os.getenv("COMET_API_KEY"):
                    st.error("❌ Сначала настройте COMET_API_KEY")
                else:
                    try:
                        provider = CometProvider()
                        result = provider.generate(
                            messages=[{"role": "user", "content": "Привет! Как дела?"}],
                            model=model_id,
                            max_tokens=50,
                            temperature=info['recommended_temp']
                        )
                        
                        if result.error:
                            st.error(f"❌ Модель недоступна: {result.error}")
                        else:
                            st.success("✅ Модель работает!")
                            st.info(f"Ответ: {result.text}")
                            st.metric("Время ответа", f"{result.latency_ms}ms")
                            
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")
    
    # Рекомендации по параметрам
    st.markdown("### 💡 Рекомендации по параметрам")
    
    st.markdown("""
    **Temperature (0.0 - 2.0):**
    - `0.0-0.3`: Детерминированные, точные ответы
    - `0.4-0.7`: Сбалансированная креативность (рекомендуется)
    - `0.8-1.2`: Креативные, разнообразные ответы
    - `1.3-2.0`: Очень креативные, непредсказуемые ответы
    
    **Max Tokens:**
    - `100-500`: Короткие ответы
    - `500-1500`: Средние ответы (рекомендуется)
    - `1500-4000`: Длинные, подробные ответы
    
    **Top P (0.0 - 1.0):**
    - `0.1-0.3`: Фокус на наиболее вероятных токенах
    - `0.4-0.7`: Сбалансированный выбор (рекомендуется)
    - `0.8-1.0`: Широкий выбор токенов
    """)


def show_about():
    """Показывает информацию о приложении"""
    st.subheader("ℹ️ О приложении")
    
    st.markdown("""
    ## 🤖 LLM Runner MVP
    
    **Версия:** 0.1.0
    
    **Описание:** MVP приложение для сравнения LLM моделей через Comet API.
    
    ### 🚀 Возможности:
    - ✅ Создание и управление задачами (промптами)
    - ✅ Запуск задач на моделях Comet
    - ✅ Оценка качества ответов (1-5)
    - ✅ Просмотр истории запусков
    - ✅ Обработка ошибок и валидация моделей
    
    ### 🛠️ Технологии:
    - **Frontend:** Streamlit
    - **Backend:** Python 3.11+
    - **База данных:** SQLite + SQLAlchemy
    - **API:** Comet API (api.cometapi.com)
    - **HTTP клиент:** httpx
    
    ### 📁 Структура проекта:
    ```
    llm_runner/
    ├── core/providers/     # Провайдеры LLM
    ├── db/                 # Модели и репозитории БД
    ├── ui/pages/          # Страницы Streamlit
    └── app.py             # Главный файл приложения
    ```
    
    ### 🔧 Настройка:
    1. Установите зависимости: `pip install -r requirements.txt`
    2. Создайте `.env` файл с вашим `COMET_API_KEY`
    3. Запустите: `streamlit run app.py`
    
    ### 📞 Поддержка:
    - GitHub: [eugenekogan-spb/comet-api-test](https://github.com/eugenekogan-spb/comet-api-test)
    - Comet API: [api.cometapi.com](https://api.cometapi.com)
    """)
    
    # Статистика приложения
    st.markdown("### 📊 Статистика")
    
    try:
        from llm_runner.db.models import init_database
        from llm_runner.db.repo import DatabaseManager
        
        init_database()
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            task_repo = db_manager.get_task_repo(session)
            run_repo = db_manager.get_run_repo(session)
            eval_repo = db_manager.get_evaluation_repo(session)
            
            tasks_count = len(task_repo.get_all_tasks())
            runs_count = len(run_repo.get_all_runs())
            successful_runs = len([r for r in run_repo.get_all_runs() if not r.error])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Задач", tasks_count)
            with col2:
                st.metric("Запусков", runs_count)
            with col3:
                st.metric("Успешных", successful_runs)
                
    except Exception as e:
        st.warning(f"Не удалось загрузить статистику: {e}")