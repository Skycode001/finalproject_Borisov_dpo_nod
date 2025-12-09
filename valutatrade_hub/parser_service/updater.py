"""
Основной модуль для обновления курсов валют.
"""

from datetime import datetime
from typing import Dict, Optional

from ..logging_config import get_logger
from .api_clients import CoinGeckoClient, ExchangeRateClient
from .storage import ExchangeRatesStorage

logger = get_logger(__name__)


class RatesUpdater:
    """Класс для управления обновлением курсов валют."""

    def __init__(self):
        self.coingecko_client = CoinGeckoClient()
        self.exchangerate_client = ExchangeRateClient()
        self.storage = ExchangeRatesStorage()
        self.last_update_time: Optional[datetime] = None

    def update_all_rates(self) -> Dict:
        """
        Обновляет все курсы валют (крипто и фиат).

        Returns:
            Словарь со всеми обновленными курсами.

        Raises:
            Exception: При критической ошибке обновления.
        """
        logger.info("Начало обновления курсов валют")

        all_rates = {}
        update_start = datetime.now()

        try:
            # 1. Получаем курсы криптовалют
            logger.info("Получение курсов криптовалют от CoinGecko...")
            crypto_rates = self._get_crypto_rates()
            all_rates.update(crypto_rates)
            logger.info(f"Получено {len(crypto_rates)} курсов криптовалют")

            # 2. Получаем курсы фиатных валют
            logger.info("Получение курсов фиатных валют...")
            fiat_rates = self._get_fiat_rates()
            all_rates.update(fiat_rates)
            logger.info(f"Получено {len(fiat_rates)} курсов фиатных валют")

            # 3. Добавляем USD как базовую валюту
            all_rates["USD"] = {
                "rate": 1.0,
                "updated_at": update_start.isoformat(),
                "source": "System"
            }

            # 4. Сохраняем исторические данные
            logger.info("Сохранение исторических данных...")
            if self.storage.save_exchange_rates(all_rates):
                logger.info("Исторические данные сохранены")
            else:
                logger.warning("Не удалось сохранить исторические данные")

            # 5. Обновляем кеш для основного сервиса
            logger.info("Обновление кеша для основного сервиса...")
            if self.storage.update_rates_cache(all_rates):
                logger.info("Кеш обновлен")
            else:
                logger.warning("Не удалось обновить кеш")

            # 6. Обновляем время последнего обновления
            self.last_update_time = update_start

            # 7. Логируем результат
            total_currencies = len(all_rates)
            logger.info(f"Обновление завершено успешно. Всего валют: {total_currencies}")

            return all_rates

        except Exception as e:
            logger.error(f"Критическая ошибка при обновлении курсов: {e}")
            raise

    def _get_crypto_rates(self) -> Dict:
        """Получает курсы криптовалют."""
        try:
            return self.coingecko_client.get_crypto_rates()
        except Exception as e:
            logger.error(f"Ошибка получения курсов криптовалют: {e}")
            # Возвращаем пустой словарь в случае ошибки
            return {}

    def _get_fiat_rates(self) -> Dict:
        """Получает курсы фиатных валют."""
        try:
            return self.exchangerate_client.get_fiat_rates()
        except Exception as e:
            logger.error(f"Ошибка получения курсов фиатных валют: {e}")
            # Возвращаем пустой словарь в случае ошибки
            return {}

    def get_update_status(self) -> Dict:
        """
        Возвращает статус последнего обновления.

        Returns:
            Словарь со статусом обновления.
        """
        latest_rates = self.storage.get_latest_rates()

        status = {
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "total_currencies": len(latest_rates),
            "currencies": list(latest_rates.keys()),
            "sources": set(info["source"] for info in latest_rates.values())
        }

        return status

    def force_update(self) -> Dict:
        """
        Принудительное обновление курсов, игнорируя любые кеши.

        Returns:
            Словарь с обновленными курсами.
        """
        logger.warning("Выполняется принудительное обновление курсов")
        return self.update_all_rates()
