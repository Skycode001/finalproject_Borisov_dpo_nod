"""
Модуль для работы с хранилищем курсов валют.
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from ..logging_config import get_logger
from .config import EXCHANGE_RATES_FILE, RATES_CACHE_FILE

logger = get_logger(__name__)


class ExchangeRatesStorage:
    """Класс для работы с хранилищем курсов валют."""

    def __init__(self):
        self.exchange_rates_file = EXCHANGE_RATES_FILE
        self.rates_cache_file = RATES_CACHE_FILE
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Создает необходимые директории, если они не существуют."""
        os.makedirs(os.path.dirname(self.exchange_rates_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.rates_cache_file), exist_ok=True)
        os.makedirs("logs", exist_ok=True)

    def load_exchange_rates(self) -> Dict:
        """
        Загружает исторические курсы из файла.

        Returns:
            Словарь с историческими курсами.
        """
        try:
            if os.path.exists(self.exchange_rates_file):
                with open(self.exchange_rates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"Загружены исторические курсы из {self.exchange_rates_file}")
                return data
            else:
                logger.debug(f"Файл исторических курсов не найден: {self.exchange_rates_file}")
                return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка загрузки исторических курсов: {e}")
            return {}

    def save_exchange_rates(self, rates_data: Dict) -> bool:
        """
        Сохраняет исторические курсы в файл.

        Args:
            rates_data: Данные курсов для сохранения.

        Returns:
            True если сохранение успешно, False в противном случае.
        """
        try:
            # Загружаем существующие данные
            existing_data = self.load_exchange_rates()

            # Обновляем или добавляем новые курсы
            for currency, rate_info in rates_data.items():
                if currency not in existing_data:
                    existing_data[currency] = []

                # Добавляем новую запись в историю
                existing_data[currency].append({
                    "rate": rate_info["rate"],
                    "updated_at": rate_info["updated_at"],
                    "source": rate_info.get("source", "unknown")
                })

                # Ограничиваем историю последними 100 записями для каждой валюты
                if len(existing_data[currency]) > 100:
                    existing_data[currency] = existing_data[currency][-100:]

            # Сохраняем обновленные данные
            with open(self.exchange_rates_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Исторические курсы сохранены в {self.exchange_rates_file}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения исторических курсов: {e}")
            return False

    def update_rates_cache(self, rates_data: Dict) -> bool:
        """
        Обновляет кеш курсов для основного сервиса.

        Args:
            rates_data: Актуальные курсы валют.

        Returns:
            True если обновление успешно, False в противном случае.
        """
        try:
            # Формируем данные для кеша в формате rates.json
            cache_data = {
                "source": "ParserService",
                "last_refresh": datetime.now().isoformat()
            }

            # Добавляем курсы в формате пар валют
            for currency, rate_info in rates_data.items():
                if currency != "USD":  # Пропускаем USD, так как он базовая валюта
                    pair_key = f"{currency}_USD"
                    cache_data[pair_key] = {
                        "rate": rate_info["rate"],
                        "updated_at": rate_info["updated_at"]
                    }

            # Сохраняем кеш
            with open(self.rates_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Кеш курсов обновлен в {self.rates_cache_file}")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления кеша курсов: {e}")
            return False

    def get_latest_rates(self) -> Dict:
        """
        Возвращает последние курсы из исторических данных.

        Returns:
            Словарь с последними курсами для каждой валюты.
        """
        try:
            historical_data = self.load_exchange_rates()
            latest_rates = {}

            for currency, history in historical_data.items():
                if history:  # Если есть история
                    # Берем последнюю запись
                    latest = history[-1]
                    latest_rates[currency] = {
                        "rate": latest["rate"],
                        "updated_at": latest["updated_at"],
                        "source": latest.get("source", "unknown")
                    }

            return latest_rates

        except Exception as e:
            logger.error(f"Ошибка получения последних курсов: {e}")
            return {}

    def get_rate_history(self, currency: str, limit: int = 10) -> List[Dict]:
        """
        Возвращает историю курсов для указанной валюты.

        Args:
            currency: Код валюты.
            limit: Максимальное количество записей.

        Returns:
            Список исторических записей курса.
        """
        try:
            historical_data = self.load_exchange_rates()

            if currency in historical_data:
                history = historical_data[currency]
                # Возвращаем последние limit записей
                return history[-limit:]
            else:
                return []

        except Exception as e:
            logger.error(f"Ошибка получения истории курса для {currency}: {e}")
            return []
