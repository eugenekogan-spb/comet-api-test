"""
Страница оценки результатов
"""
import streamlit as st
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from llm_runner.db.models import init_database
from llm_runner.db.repo import DatabaseManager


def main():
    st.header("⭐ Оценка результатов")
    
    # Инициализируем БД
    init_database()
    db_manager = DatabaseManager()
    
    show_evaluation_interface(db_manager)


def show_evaluation_interface(db_manager: DatabaseManager):
    """Показывает интерфейс для оценки результатов"""
    
    with db_manager.get_session() as session:
        run_repo = db_manager.get_run_repo(session)
        eval_repo = db_manager.get_evaluation_repo(session)
        
        # Получаем все запуски без ошибок
        all_runs = run_repo.get_all_runs()
        successful_runs = [r for r in all_runs if not r.error]
        
        # Получаем уже оцененные запуски
        evaluated_run_ids = set()
        for run in successful_runs:
            eval_obj = eval_repo.get_evaluation_by_run_id(run.id)
            if eval_obj:
                evaluated_run_ids.add(run.id)
        
        # Фильтруем неоцененные
        unevaluated_runs = [r for r in successful_runs if r.id not in evaluated_run_ids]
    
    if not successful_runs:
        st.info("📊 Нет успешных запусков для оценки")
        return
    
    # Статистика
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего запусков", len(successful_runs))
    with col2:
        st.metric("Оценено", len(evaluated_run_ids))
    with col3:
        st.metric("Осталось", len(unevaluated_runs))
    
    # Переключатель режима
    mode = st.radio(
        "Режим оценки:",
        ["🎯 Оценить новые", "📊 Просмотреть все", "✏️ Редактировать оценки"],
        horizontal=True
    )
    
    if mode == "🎯 Оценить новые":
        show_unevaluated_runs(db_manager, unevaluated_runs)
    elif mode == "📊 Просмотреть все":
        show_all_evaluations(db_manager, successful_runs)
    else:
        show_edit_evaluations(db_manager, successful_runs)


def show_unevaluated_runs(db_manager: DatabaseManager, runs):
    """Показывает неоцененные запуски"""
    if not runs:
        st.success("🎉 Все запуски оценены!")
        return
    
    st.subheader(f"Оценить новые ({len(runs)} запусков)")
    
    # Показываем первый неоцененный запуск
    run = runs[0]
    
    with st.container():
        st.markdown("---")
        
        # Информация о запуске
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Модель:** {run.model}")
            st.markdown(f"**Время:** {run.latency_ms}ms")
            st.markdown(f"**Токены:** {run.total_tokens or 0}")
            st.markdown(f"**Дата:** {run.started_at.strftime('%d.%m.%Y %H:%M')}")
        with col2:
            st.markdown(f"**Прогресс:** {len(runs)} осталось")
        
        # Показываем промпт
        with st.expander("📝 Промпт", expanded=False):
            messages = eval(run.messages_json) if run.messages_json else []
            for msg in messages:
                st.markdown(f"**{msg['role']}:** {msg['content']}")
        
        # Показываем ответ
        st.markdown("### 📄 Ответ модели:")
        st.markdown(run.response_text)
        
        # Форма оценки
        st.markdown("---")
        with st.form(f"evaluate_{run.id}"):
            st.markdown("### ⭐ Оцените качество ответа:")
            
            col1, col2 = st.columns(2)
            with col1:
                rating = st.selectbox(
                    "Оценка (1-5):",
                    [1, 2, 3, 4, 5],
                    format_func=lambda x: f"{x} - {'Плохо' if x == 1 else 'Отлично' if x == 5 else 'Средне'}",
                    key=f"rating_{run.id}"
                )
            
            with col2:
                # Быстрые кнопки
                st.markdown("**Быстрая оценка:**")
                if st.form_submit_button("1️⃣", help="Плохо"):
                    rating = 1
                if st.form_submit_button("2️⃣", help="Ниже среднего"):
                    rating = 2
                if st.form_submit_button("3️⃣", help="Средне"):
                    rating = 3
                if st.form_submit_button("4️⃣", help="Хорошо"):
                    rating = 4
                if st.form_submit_button("5️⃣", help="Отлично"):
                    rating = 5
            
            comment = st.text_area(
                "Комментарий (опционально):",
                placeholder="Опишите, что понравилось или не понравилось в ответе...",
                key=f"comment_{run.id}"
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                submit_eval = st.form_submit_button("💾 Сохранить оценку", type="primary")
            with col2:
                skip = st.form_submit_button("⏭️ Пропустить")
            with col3:
                if st.form_submit_button("🔄 Обновить"):
                    st.rerun()
            
            if submit_eval:
                with db_manager.get_session() as session:
                    eval_repo = db_manager.get_evaluation_repo(session)
                    eval_repo.create_evaluation(run.id, rating, comment)
                    st.success("✅ Оценка сохранена!")
                    st.rerun()
            
            if skip:
                st.info("⏭️ Запуск пропущен")
                st.rerun()


def show_all_evaluations(db_manager: DatabaseManager, runs):
    """Показывает все оценки"""
    st.subheader("Все оценки")
    
    with db_manager.get_session() as session:
        eval_repo = db_manager.get_evaluation_repo(session)
        
        # Получаем оценки
        evaluations = []
        for run in runs:
            eval_obj = eval_repo.get_evaluation_by_run_id(run.id)
            if eval_obj:
                evaluations.append((run, eval_obj))
    
    if not evaluations:
        st.info("📊 Оценок пока нет")
        return
    
    # Сортируем по дате оценки
    evaluations.sort(key=lambda x: x[1].created_at, reverse=True)
    
    # Статистика
    ratings = [eval_obj.rating for _, eval_obj in evaluations]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Средняя оценка", f"{avg_rating:.1f}")
    with col2:
        st.metric("Всего оценок", len(evaluations))
    with col3:
        st.metric("Оценка 5", ratings.count(5))
    with col4:
        st.metric("Оценка 1", ratings.count(1))
    
    # Показываем оценки
    for run, eval_obj in evaluations:
        with st.expander(f"⭐ {eval_obj.rating}/5 - {run.model} - {eval_obj.created_at.strftime('%d.%m.%Y %H:%M')}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Модель:** {run.model}")
                st.markdown(f"**Время:** {run.latency_ms}ms")
                st.markdown(f"**Токены:** {run.total_tokens or 0}")
                
                if eval_obj.comment:
                    st.markdown("**Комментарий:**")
                    st.text(eval_obj.comment)
                
                # Показываем ответ
                st.markdown("**Ответ:**")
                st.text(run.response_text[:300] + "..." if len(run.response_text or "") > 300 else run.response_text)
            
            with col2:
                # Показываем звездочки
                stars = "⭐" * eval_obj.rating + "☆" * (5 - eval_obj.rating)
                st.markdown(f"**Оценка:** {stars}")
                st.markdown(f"**Дата оценки:** {eval_obj.created_at.strftime('%d.%m.%Y %H:%M')}")


def show_edit_evaluations(db_manager: DatabaseManager, runs):
    """Показывает интерфейс редактирования оценок"""
    st.subheader("Редактировать оценки")
    
    with db_manager.get_session() as session:
        eval_repo = db_manager.get_evaluation_repo(session)
        
        # Получаем оценки
        evaluations = []
        for run in runs:
            eval_obj = eval_repo.get_evaluation_by_run_id(run.id)
            if eval_obj:
                evaluations.append((run, eval_obj))
    
    if not evaluations:
        st.info("📊 Оценок для редактирования нет")
        return
    
    # Выбор оценки для редактирования
    eval_options = {f"{run.model} - {eval_obj.rating}/5 - {eval_obj.created_at.strftime('%d.%m.%Y')}": (run, eval_obj) for run, eval_obj in evaluations}
    selected_eval_name = st.selectbox("Выберите оценку для редактирования:", list(eval_options.keys()))
    selected_run, selected_eval = eval_options[selected_eval_name]
    
    # Форма редактирования
    with st.form("edit_evaluation"):
        st.markdown("### ✏️ Редактировать оценку")
        
        new_rating = st.selectbox(
            "Новая оценка:",
            [1, 2, 3, 4, 5],
            index=selected_eval.rating - 1
        )
        
        new_comment = st.text_area(
            "Новый комментарий:",
            value=selected_eval.comment or ""
        )
        
        if st.form_submit_button("💾 Сохранить изменения", type="primary"):
            with db_manager.get_session() as session:
                eval_repo = db_manager.get_evaluation_repo(session)
                eval_repo.update_evaluation(selected_run.id, new_rating, new_comment)
                st.success("✅ Оценка обновлена!")
                st.rerun()