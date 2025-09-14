"""
Репозиторий для работы с базой данных
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import Task, Run, Evaluation, create_engine_and_session


class TaskRepository:
    """Репозиторий для работы с задачами"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_task(self, name: str, prompt_template: str, input_text: str = None) -> Task:
        """Создает новую задачу"""
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            prompt_template=prompt_template,
            input_text=input_text
        )
        self.session.add(task)
        self.session.commit()
        return task
    
    def get_all_tasks(self) -> List[Task]:
        """Получает все задачи"""
        return self.session.query(Task).order_by(desc(Task.created_at)).all()
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Получает задачу по ID"""
        return self.session.query(Task).filter(Task.id == task_id).first()
    
    def delete_task(self, task_id: str) -> bool:
        """Удаляет задачу"""
        task = self.get_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False


class RunRepository:
    """Репозиторий для работы с запусками"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_run(
        self,
        task_id: str,
        provider: str,
        model: str,
        params: Dict[str, Any],
        messages: List[Dict[str, str]],
        response_text: str = None,
        response_json: Dict[str, Any] = None,
        error: str = None,
        latency_ms: int = None,
        usage: Dict[str, int] = None,
        finish_reason: str = None
    ) -> Run:
        """Создает новый запуск"""
        
        run = Run(
            id=str(uuid.uuid4()),
            task_id=task_id,
            provider=provider,
            model=model,
            params_json=json.dumps(params),
            messages_json=json.dumps(messages),
            response_text=response_text,
            response_json=json.dumps(response_json) if response_json else None,
            error=error,
            latency_ms=latency_ms,
            finish_reason=finish_reason
        )
        
        # Заполняем usage если есть
        if usage:
            run.prompt_tokens = usage.get('prompt_tokens', 0)
            run.completion_tokens = usage.get('completion_tokens', 0)
            run.total_tokens = usage.get('total_tokens', 0)
        
        # Завершаем запуск
        run.ended_at = datetime.utcnow()
        
        self.session.add(run)
        self.session.commit()
        return run
    
    def get_runs_by_task(self, task_id: str) -> List[Run]:
        """Получает все запуски для задачи"""
        return self.session.query(Run).filter(Run.task_id == task_id).order_by(desc(Run.started_at)).all()
    
    def get_all_runs(self) -> List[Run]:
        """Получает все запуски"""
        return self.session.query(Run).order_by(desc(Run.started_at)).all()
    
    def get_run_by_id(self, run_id: str) -> Optional[Run]:
        """Получает запуск по ID"""
        return self.session.query(Run).filter(Run.id == run_id).first()


class EvaluationRepository:
    """Репозиторий для работы с оценками"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_evaluation(self, run_id: str, rating: int, comment: str = None) -> Evaluation:
        """Создает новую оценку"""
        evaluation = Evaluation(
            id=str(uuid.uuid4()),
            run_id=run_id,
            rating=rating,
            comment=comment
        )
        self.session.add(evaluation)
        self.session.commit()
        return evaluation
    
    def update_evaluation(self, run_id: str, rating: int, comment: str = None) -> Optional[Evaluation]:
        """Обновляет существующую оценку"""
        evaluation = self.session.query(Evaluation).filter(Evaluation.run_id == run_id).first()
        if evaluation:
            evaluation.rating = rating
            evaluation.comment = comment
            self.session.commit()
            return evaluation
        return None
    
    def get_evaluation_by_run_id(self, run_id: str) -> Optional[Evaluation]:
        """Получает оценку по ID запуска"""
        return self.session.query(Evaluation).filter(Evaluation.run_id == run_id).first()


class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self):
        self.engine, self.SessionLocal = create_engine_and_session()
    
    def get_session(self) -> Session:
        """Получает новую сессию"""
        return self.SessionLocal()
    
    def get_task_repo(self, session: Session = None) -> TaskRepository:
        """Получает репозиторий задач"""
        if session is None:
            session = self.get_session()
        return TaskRepository(session)
    
    def get_run_repo(self, session: Session = None) -> RunRepository:
        """Получает репозиторий запусков"""
        if session is None:
            session = self.get_session()
        return RunRepository(session)
    
    def get_evaluation_repo(self, session: Session = None) -> EvaluationRepository:
        """Получает репозиторий оценок"""
        if session is None:
            session = self.get_session()
        return EvaluationRepository(session)