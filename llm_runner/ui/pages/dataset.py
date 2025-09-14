"""
Страница управления датасетом задач
"""
import streamlit as st
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from llm_runner.db.models import init_database
from llm_runner.db.repo import DatabaseManager


def main():
    st.header("📊 Управление датасетом")
    
    # Инициализируем БД
    init_database()
    db_manager = DatabaseManager()
    
    # Создаем вкладки
    tab1, tab2 = st.tabs(["📋 Список задач", "➕ Добавить задачу"])
    
    with tab1:
        show_tasks_list(db_manager)
    
    with tab2:
        show_add_task_form(db_manager)


def show_tasks_list(db_manager: DatabaseManager):
    """Показывает список задач"""
    st.subheader("Список задач")
    
    with db_manager.get_session() as session:
        task_repo = db_manager.get_task_repo(session)
        tasks = task_repo.get_all_tasks()
    
    if not tasks:
        st.info("📝 Задач пока нет. Добавьте первую задачу во вкладке 'Добавить задачу'")
        return
    
    # Показываем задачи в виде карточек
    for task in tasks:
        with st.expander(f"📝 {task.name}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**ID:** `{task.id}`")
                st.markdown(f"**Создано:** {task.created_at.strftime('%d.%m.%Y %H:%M')}")
                
                if task.input_text:
                    st.markdown("**Входной текст:**")
                    st.text(task.input_text)
                
                st.markdown("**Шаблон промпта:**")
                st.code(task.prompt_template, language="text")
            
            with col2:
                # Кнопка удаления
                if st.button("🗑️ Удалить", key=f"delete_{task.id}", type="secondary"):
                    with db_manager.get_session() as session:
                        task_repo = db_manager.get_task_repo(session)
                        if task_repo.delete_task(task.id):
                            st.success("✅ Задача удалена")
                            st.rerun()
                        else:
                            st.error("❌ Ошибка удаления задачи")


def show_add_task_form(db_manager: DatabaseManager):
    """Показывает форму добавления задачи"""
    st.subheader("Добавить новую задачу")
    
    with st.form("add_task_form"):
        name = st.text_input("Название задачи", placeholder="Например: Тест на понимание контекста")
        
        prompt_template = st.text_area(
            "Шаблон промпта",
            placeholder="Введите шаблон промпта. Можно использовать переменные в фигурных скобках: {variable}",
            height=150
        )
        
        input_text = st.text_area(
            "Входной текст (опционально)",
            placeholder="Дополнительный текст для подстановки в промпт",
            height=100
        )
        
        submitted = st.form_submit_button("➕ Добавить задачу", type="primary")
        
        if submitted:
            if not name or not prompt_template:
                st.error("❌ Заполните название и шаблон промпта")
            else:
                try:
                    with db_manager.get_session() as session:
                        task_repo = db_manager.get_task_repo(session)
                        task = task_repo.create_task(name, prompt_template, input_text)
                        st.success(f"✅ Задача '{task.name}' создана с ID: `{task.id}`")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка создания задачи: {e}")
    
    # Показываем пример
    st.markdown("---")
    st.markdown("### 💡 Пример")
    st.code("""
Название: Тест на понимание контекста
Шаблон: Проанализируй следующий текст и ответь на вопрос: {question}
Входной текст: Текст для анализа: {text}
""", language="text")