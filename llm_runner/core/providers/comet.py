"""
Comet API провайдер
"""
import time
import httpx
import os
from typing import Dict, List, Optional, Any
from loguru import logger

from .base import Provider, ProviderResult


class CometProvider(Provider):
    """Провайдер для Comet API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("COMET_API_KEY")
        self.base_url = base_url or os.getenv("COMET_BASE_URL", "https://api.cometapi.com")
        
        if not self.api_key:
            raise ValueError("COMET_API_KEY не найден в переменных окружения")
        
        # Убираем trailing slash если есть
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **params
    ) -> ProviderResult:
        """Генерирует ответ через Comet API"""
        
        url = f"{self.base_url}/v1/chat/completions"
        
        # Подготавливаем payload
        payload = {
            "model": model,
            "messages": messages,
            **params
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        start_time = time.perf_counter()
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload, headers=headers)
                
                # Проверяем статус ответа
                if response.status_code == 401:
                    return ProviderResult(
                        text=None,
                        usage={},
                        finish_reason=None,
                        raw={},
                        latency_ms=int((time.perf_counter() - start_time) * 1000),
                        error="Неверный API ключ"
                    )
                elif response.status_code == 404:
                    return ProviderResult(
                        text=None,
                        usage={},
                        finish_reason=None,
                        raw={},
                        latency_ms=int((time.perf_counter() - start_time) * 1000),
                        error=f"Модель '{model}' не найдена"
                    )
                elif response.status_code == 429:
                    return ProviderResult(
                        text=None,
                        usage={},
                        finish_reason=None,
                        raw={},
                        latency_ms=int((time.perf_counter() - start_time) * 1000),
                        error="Превышен лимит запросов (rate limit)"
                    )
                elif response.status_code >= 500:
                    return ProviderResult(
                        text=None,
                        usage={},
                        finish_reason=None,
                        raw={},
                        latency_ms=int((time.perf_counter() - start_time) * 1000),
                        error=f"Ошибка сервера: {response.status_code}"
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Извлекаем результат
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                text = message.get("content")
                finish_reason = choice.get("finish_reason")
                usage = data.get("usage", {})
                
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                
                logger.info(f"Comet API: модель {model}, токены {usage.get('total_tokens', 0)}, время {latency_ms}ms")
                
                return ProviderResult(
                    text=text,
                    usage=usage,
                    finish_reason=finish_reason,
                    raw=data,
                    latency_ms=latency_ms
                )
                
        except httpx.TimeoutException:
            return ProviderResult(
                text=None,
                usage={},
                finish_reason=None,
                raw={},
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                error="Таймаут запроса (60 секунд)"
            )
        except httpx.RequestError as e:
            return ProviderResult(
                text=None,
                usage={},
                finish_reason=None,
                raw={},
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                error=f"Ошибка сети: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Неожиданная ошибка в CometProvider: {e}")
            return ProviderResult(
                text=None,
                usage={},
                finish_reason=None,
                raw={},
                latency_ms=int((time.perf_counter() - start_time) * 1000),
                error=f"Неожиданная ошибка: {str(e)}"
            )
    
    def validate_model(self, model: str) -> bool:
        """Проверяет доступность модели через тестовый запрос"""
        try:
            # Делаем минимальный тестовый запрос
            test_messages = [{"role": "user", "content": "Hi"}]
            result = self.generate(
                messages=test_messages,
                model=model,
                max_tokens=1
            )
            
            # Если нет ошибки, модель доступна
            return result.error is None
            
        except Exception as e:
            logger.warning(f"Ошибка валидации модели {model}: {e}")
            return False