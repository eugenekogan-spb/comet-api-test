"""
Базовый интерфейс для провайдеров LLM
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


@dataclass
class ProviderResult:
    """Результат выполнения запроса к провайдеру"""
    text: Optional[str]
    usage: Dict[str, int]
    finish_reason: Optional[str]
    raw: Dict[str, Any]
    latency_ms: int
    error: Optional[str] = None


class Provider(ABC):
    """Базовый класс для всех провайдеров LLM"""
    
    @abstractmethod
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> ProviderResult:
        """
        Генерирует ответ от LLM модели
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            model: Название модели
            **params: Дополнительные параметры (temperature, max_tokens, etc.)
            
        Returns:
            ProviderResult с результатом генерации
        """
        raise NotImplementedError
    
    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """
        Проверяет доступность модели
        
        Args:
            model: Название модели
            
        Returns:
            True если модель доступна, False иначе
        """
        raise NotImplementedError