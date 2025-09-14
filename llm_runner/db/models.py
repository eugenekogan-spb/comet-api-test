"""
Модели данных для MVP
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()


class Task(Base):
    """Задача/промпт для тестирования"""
    __tablename__ = 'tasks'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    prompt_template = Column(Text, nullable=False)
    input_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с запусками
    runs = relationship("Run", back_populates="task", cascade="all, delete-orphan")


class Run(Base):
    """Запуск задачи на модели"""
    __tablename__ = 'runs'
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey('tasks.id'), nullable=False)
    provider = Column(String, nullable=False)  # 'comet', 'openai', etc.
    model = Column(String, nullable=False)
    params_json = Column(Text)  # JSON с параметрами
    messages_json = Column(Text)  # JSON с сообщениями
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    latency_ms = Column(Integer)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cost_usd = Column(Float)
    finish_reason = Column(String)
    response_text = Column(Text)
    response_json = Column(Text)  # Полный JSON ответ
    error = Column(Text)  # Ошибка если была
    
    # Связи
    task = relationship("Task", back_populates="runs")
    evaluation = relationship("Evaluation", back_populates="run", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    """Оценка результата запуска"""
    __tablename__ = 'evaluations'
    
    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey('runs.id'), nullable=False)
    rating = Column(Integer)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь
    run = relationship("Run", back_populates="evaluation")


def get_database_url():
    """Получает URL базы данных из переменных окружения"""
    db_path = os.getenv("LLM_RUNNER_DB", "./llm_runner.db")
    return f"sqlite:///{db_path}"


def create_engine_and_session():
    """Создает движок БД и сессию"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def init_database():
    """Инициализирует базу данных"""
    engine, _ = create_engine_and_session()
    Base.metadata.create_all(bind=engine)
    return engine