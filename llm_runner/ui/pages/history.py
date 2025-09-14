"""
Страница истории запусков
"""
import streamlit as st
import sys
import os
import json

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from llm_runner.db.models import init_database
from llm_runner.db.repo import DatabaseManager


def main():
    st.header("📋 История запусков")
    
    # Инициализируем БД
    init_database()
    db_manager = DatabaseManager()
    
    show_history_interface(db_manager)


def show_history_interface(db_manager: DatabaseManager):
    """Показывает интерфейс истории запусков"""
    
    with db_manager.get_session() as session:
        run_repo = db_manager.get_run_repo(session)
        eval_repo = db_manager.get_evaluation_repo(session)
        task_repo = db_manager.get_task_repo(session)
        
        runs = run_repo.get_all_runs()
    
    if not runs:
        st.info("📊 Запусков пока нет")
        return
    
    # Статистика
    successful_runs = [r for r in runs if not r.error]
    failed_runs = [r for r in runs if r.error]
    evaluated_runs = 0
    
    for run in successful_runs:
        if eval_repo.get_evaluation_by_run_id(run.id):
            evaluated_runs += 1
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Всего запусков", len(runs))
    with col2:
        st.metric("Успешных", len(successful_runs))
    with col3:
        st.metric("С ошибками", len(failed_runs))
    with col4:
        st.metric("Оценено", evaluated_runs)
    
    # Фильтры
    st.markdown("### 🔍 Фильтры")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        models = list(set(run.model for run in runs))
        selected_model = st.selectbox("Модель", ["Все"] + sorted(models))
    with col2:
        statuses = ["Все", "Успешно", "С ошибкой"]
        selected_status = st.selectbox("Статус", statuses)
    with col3:
        eval_statuses = ["Все", "Оценено", "Не оценено"]
        selected_eval_status = st.selectbox("Оценка", eval_statuses)
    with col4:
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
    if selected_eval_status == "Оценено":
        filtered_runs = [r for r in filtered_runs if not r.error and eval_repo.get_evaluation_by_run_id(r.id)]
    elif selected_eval_status == "Не оценено":
        filtered_runs = [r for r in filtered_runs if not r.error and not eval_repo.get_evaluation_by_run_id(r.id)]
    
    st.markdown(f"### 📊 Результаты ({len(filtered_runs)} из {len(runs)})")
    
    # Показываем результаты
    for run in filtered_runs:
        # Получаем задачу
        task = task_repo.get_task_by_id(run.task_id)
        task_name = task.name if task else "Неизвестная задача"
        
        # Получаем оценку
        evaluation = eval_repo.get_evaluation_by_run_id(run.id) if not run.error else None
        
        # Определяем цвет и иконку
        if run.error:
            status_icon = "❌"
            status_color = "red"
        elif evaluation:
            status_icon = f"⭐{evaluation.rating}"
            status_color = "green"
        else:
            status_icon = "⏳"
            status_color = "orange"
        
        with st.expander(
            f"{status_icon} {task_name} - {run.model} - {run.started_at.strftime('%d.%m.%Y %H:%M')}",
            expanded=False
        ):
            # Основная информация
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Задача:** {task_name}")
                st.markdown(f"**Модель:** {run.model}")
                st.markdown(f"**Время:** {run.latency_ms}ms")
                st.markdown(f"**Токены:** {run.total_tokens or 0}")
                st.markdown(f"**Дата:** {run.started_at.strftime('%d.%m.%Y %H:%M:%S')}")
                
                if run.error:
                    st.error(f"**Ошибка:** {run.error}")
                elif evaluation:
                    stars = "⭐" * evaluation.rating + "☆" * (5 - evaluation.rating)
                    st.markdown(f"**Оценка:** {stars} ({evaluation.rating}/5)")
                    if evaluation.comment:
                        st.markdown(f"**Комментарий:** {evaluation.comment}")
                else:
                    st.info("⏳ Ожидает оценки")
            
            with col2:
                # Кнопки действий
                if not run.error:
                    if not evaluation:
                        if st.button("⭐ Оценить", key=f"eval_{run.id}"):
                            st.session_state[f"evaluate_run_{run.id}"] = True
                    else:
                        if st.button("✏️ Редактировать", key=f"edit_{run.id}"):
                            st.session_state[f"edit_run_{run.id}"] = True
                
                if st.button("👁️ Показать детали", key=f"details_{run.id}"):
                    st.session_state[f"show_details_{run.id}"] = True
            
            # Показываем детали если нужно
            if st.session_state.get(f"show_details_{run.id}", False):
                st.markdown("---")
                st.markdown("### 🔍 Детали запуска")
                
                # Параметры
                if run.params_json:
                    st.markdown("**Параметры:**")
                    params = json.loads(run.params_json)
                    st.json(params)
                
                # Сообщения
                if run.messages_json:
                    st.markdown("**Сообщения:**")
                    messages = json.loads(run.messages_json)
                    for i, msg in enumerate(messages):
                        st.markdown(f"**{i+1}. {msg['role']}:**")
                        st.text(msg['content'])
                
                # Ответ
                if run.response_text:
                    st.markdown("**Ответ модели:**")
                    st.markdown(run.response_text)
                
                # Сырой JSON
                if run.response_json:
                    st.markdown("**Сырой JSON ответ:**")
                    st.json(json.loads(run.response_json))
            
            # Форма оценки
            if st.session_state.get(f"evaluate_run_{run.id}", False):
                st.markdown("---")
                with st.form(f"evaluate_{run.id}"):
                    st.markdown("### ⭐ Оцените результат")
                    
                    rating = st.selectbox("Оценка:", [1, 2, 3, 4, 5], key=f"rating_{run.id}")
                    comment = st.text_area("Комментарий:", key=f"comment_{run.id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Сохранить"):
                            with db_manager.get_session() as session:
                                eval_repo = db_manager.get_evaluation_repo(session)
                                eval_repo.create_evaluation(run.id, rating, comment)
                                st.success("✅ Оценка сохранена!")
                                st.session_state[f"evaluate_run_{run.id}"] = False
                                st.rerun()
                    with col2:
                        if st.form_submit_button("❌ Отмена"):
                            st.session_state[f"evaluate_run_{run.id}"] = False
                            st.rerun()
            
            # Форма редактирования оценки
            if st.session_state.get(f"edit_run_{run.id}", False):
                st.markdown("---")
                with st.form(f"edit_{run.id}"):
                    st.markdown("### ✏️ Редактировать оценку")
                    
                    new_rating = st.selectbox("Оценка:", [1, 2, 3, 4, 5], index=evaluation.rating-1, key=f"edit_rating_{run.id}")
                    new_comment = st.text_area("Комментарий:", value=evaluation.comment or "", key=f"edit_comment_{run.id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Сохранить"):
                            with db_manager.get_session() as session:
                                eval_repo = db_manager.get_evaluation_repo(session)
                                eval_repo.update_evaluation(run.id, new_rating, new_comment)
                                st.success("✅ Оценка обновлена!")
                                st.session_state[f"edit_run_{run.id}"] = False
                                st.rerun()
                    with col2:
                        if st.form_submit_button("❌ Отмена"):
                            st.session_state[f"edit_run_{run.id}"] = False
                            st.rerun()