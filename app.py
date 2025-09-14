"""
LLM Runner - MVP приложение для сравнения LLM моделей
"""
import streamlit as st
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка страницы
st.set_page_config(
    page_title="LLM Runner",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🤖 LLM Runner")
    st.markdown("**MVP приложение для сравнения LLM моделей**")
    
    # Проверяем настройки
    if not os.getenv("COMET_API_KEY"):
        st.error("⚠️ COMET_API_KEY не найден в .env файле")
        st.info("Создайте .env файл на основе .env.example и добавьте ваш API ключ")
        return
    
    # Навигация по страницам
    pages = {
        "📊 Dataset": "llm_runner.ui.pages.dataset",
        "🚀 Runs": "llm_runner.ui.pages.runs", 
        "⭐ Evaluate": "llm_runner.ui.pages.evaluate",
        "📋 History": "llm_runner.ui.pages.history",
        "⚙️ Settings": "llm_runner.ui.pages.settings"
    }
    
    selected_page = st.sidebar.selectbox("Выберите страницу:", list(pages.keys()))
    
    # Импортируем и запускаем выбранную страницу
    try:
        module_name = pages[selected_page]
        module = __import__(module_name, fromlist=['main'])
        module.main()
    except ImportError as e:
        st.error(f"Ошибка загрузки страницы: {e}")
        st.info("Страница еще не реализована")

if __name__ == "__main__":
    main()