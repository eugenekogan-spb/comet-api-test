"""
Страница запуска задач на моделях
"""
import streamlit as st
import sys
import os
import json
from datetime import datetime

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from llm_runner.db.models import init_database
from llm_runner.db.repo import DatabaseManager
from llm_runner.core.providers.comet import CometProvider


def main():
    st.header("🚀 Запуск задач")
    
    # Инициализируем БД
    init_database()
    db_manager = DatabaseManager()
    
    # Проверяем настройки Comet API
    if not os.getenv("COMET_API_KEY"):
        st.error("⚠️ COMET_API_KEY не найден в .env файле")
        st.info("Перейдите в Settings для настройки API ключа")
        return
    
    # Создаем вкладки
    tab1, tab2 = st.tabs(["🎯 Запустить задачу", "📊 Результаты"])
    
    with tab1:
        show_run_form(db_manager)
    
    with tab2:
        show_results(db_manager)


def show_run_form(db_manager: DatabaseManager):
    """Показывает форму запуска задачи"""
    st.subheader("Запустить задачу на модели")
    
    with db_manager.get_session() as session:
        task_repo = db_manager.get_task_repo(session)
        tasks = task_repo.get_all_tasks()
    
    if not tasks:
        st.warning("📝 Сначала создайте задачи в разделе Dataset")
        return
    
    with st.form("run_task_form"):
        # Выбор задачи
        task_options = {f"{task.name} (ID: {task.id[:8]}...)": task for task in tasks}
        selected_task_name = st.selectbox("Выберите задачу:", list(task_options.keys()))
        selected_task = task_options[selected_task_name]
        
        # Показываем детали задачи
        with st.expander("📋 Детали задачи", expanded=False):
            st.markdown(f"**Название:** {selected_task.name}")
            st.markdown(f"**ID:** `{selected_task.id}`")
            st.markdown("**Шаблон промпта:**")
            st.code(selected_task.prompt_template, language="text")
            if selected_task.input_text:
                st.markdown("**Входной текст:**")
                st.text(selected_task.input_text)
        
        # Настройки модели
        st.markdown("### 🤖 Настройки модели")
        
        col1, col2 = st.columns(2)
        with col1:
            model = st.text_input("Модель", value="comet-7b", help="Название модели Comet")
        with col2:
            temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
        
        col3, col4 = st.columns(2)
        with col3:
            max_tokens = st.number_input("Max tokens", 1, 4000, 1000)
        with col4:
            top_p = st.slider("Top P", 0.0, 1.0, 0.9, 0.1)
        
        # Дополнительные параметры
        with st.expander("⚙️ Дополнительные параметры"):
            stop = st.text_input("Stop sequences", placeholder="Разделите запятыми")
            seed = st.number_input("Seed (опционально)", value=None, min_value=1)
        
        # Формирование промпта
        st.markdown("### 📝 Формирование промпта")
        
        # Простая подстановка переменных
        final_prompt = selected_task.prompt_template
        if selected_task.input_text:
            final_prompt += "\n\n" + selected_task.input_text
        
        st.markdown("**Финальный промпт:**")
        st.code(final_prompt, language="text")
        
        # Кнопка запуска
        submitted = st.form_submit_button("🚀 Запустить", type="primary")
        
        if submitted:
            run_task(
                db_manager, 
                selected_task, 
                model, 
                final_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop.split(',') if stop else None,
                seed=seed
            )


def run_task(db_manager: DatabaseManager, task, model: str, prompt: str, **params):
    """Запускает задачу на модели"""
    
    # Показываем прогресс
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Инициализируем провайдер
        status_text.text("🔧 Инициализация Comet API...")
        progress_bar.progress(20)
        
        provider = CometProvider()
        
        # Проверяем модель
        status_text.text("🔍 Проверка доступности модели...")
        progress_bar.progress(40)
        
        if not provider.validate_model(model):
            st.error(f"❌ Модель '{model}' недоступна или неверное название")
            return
        
        # Формируем сообщения
        messages = [{"role": "user", "content": prompt}]
        
        # Запускаем генерацию
        status_text.text("🚀 Отправка запроса к модели...")
        progress_bar.progress(60)
        
        result = provider.generate(messages, model, **params)
        
        progress_bar.progress(80)
        
        # Сохраняем результат
        status_text.text("💾 Сохранение результата...")
        
        with db_manager.get_session() as session:
            run_repo = db_manager.get_run_repo(session)
            run = run_repo.create_run(
                task_id=task.id,
                provider="comet",
                model=model,
                params=params,
                messages=messages,
                response_text=result.text,
                response_json=result.raw,
                error=result.error,
                latency_ms=result.latency_ms,
                usage=result.usage,
                finish_reason=result.finish_reason
            )
        
        progress_bar.progress(100)
        status_text.text("✅ Готово!")
        
        # Показываем результат
        if result.error:
            st.error(f"❌ Ошибка: {result.error}")
        else:
            st.success("✅ Запрос выполнен успешно!")
            
            # Показываем метрики
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Время", f"{result.latency_ms}ms")
            with col2:
                st.metric("Токены", result.usage.get('total_tokens', 0))
            with col3:
                st.metric("Промпт токены", result.usage.get('prompt_tokens', 0))
            with col4:
                st.metric("Завершение", result.finish_reason or "N/A")
            
            # Показываем ответ
            st.markdown("### 📄 Ответ модели:")
            st.markdown(result.text)
            
            # Показываем сырой JSON
            with st.expander("🔍 Сырой JSON ответ"):
                st.json(result.raw)
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Неожиданная ошибка: {e}")
        progress_bar.progress(0)
        status_text.text("")


def show_results(db_manager: DatabaseManager):
    """Показывает результаты запусков"""
    st.subheader("Результаты запусков")
    
    with db_manager.get_session() as session:
        run_repo = db_manager.get_run_repo(session)
        runs = run_repo.get_all_runs()
    
    if not runs:
        st.info("📊 Запусков пока нет")
        return
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        models = list(set(run.model for run in runs))
        selected_model = st.selectbox("Модель", ["Все"] + models)
    with col2:
        statuses = ["Все", "Успешно", "С ошибкой"]
        selected_status = st.selectbox("Статус", statuses)
    with col3:
        if st.button("🔄 Обновить"):
            st.rerun()
    
    # Фильтруем результаты
    filtered_runs = runs
    if selected_model != "Все":
        filtered_runs = [r for r in filtered_runs if r.model == selected_model]
    if selected_status == "Успешно":
        filtered_runs = [r for r in filtered_runs if not r.error]
    elif selected_status == "С ошибкой":
        filtered_runs = [r for r in filtered_runs if r.error]
    
    # Показываем результаты
    for run in filtered_runs:
        with st.expander(f"🚀 {run.model} - {run.started_at.strftime('%d.%m.%Y %H:%M')}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**ID:** `{run.id}`")
                st.markdown(f"**Модель:** {run.model}")
                st.markdown(f"**Время:** {run.latency_ms}ms")
                st.markdown(f"**Токены:** {run.total_tokens or 0}")
                
                if run.error:
                    st.error(f"❌ Ошибка: {run.error}")
                else:
                    st.markdown("**Ответ:**")
                    st.text(run.response_text[:200] + "..." if len(run.response_text or "") > 200 else run.response_text)
            
            with col2:
                if not run.error:
                    if st.button("⭐ Оценить", key=f"eval_{run.id}"):
                        st.session_state[f"evaluate_run_{run.id}"] = True
                
                if st.session_state.get(f"evaluate_run_{run.id}", False):
                    with st.form(f"eval_form_{run.id}"):
                        rating = st.selectbox("Оценка", [1, 2, 3, 4, 5], key=f"rating_{run.id}")
                        comment = st.text_area("Комментарий", key=f"comment_{run.id}")
                        
                        if st.form_submit_button("💾 Сохранить оценку"):
                            with db_manager.get_session() as session:
                                eval_repo = db_manager.get_evaluation_repo(session)
                                eval_repo.create_evaluation(run.id, rating, comment)
                                st.success("✅ Оценка сохранена")
                                st.session_state[f"evaluate_run_{run.id}"] = False
                                st.rerun()