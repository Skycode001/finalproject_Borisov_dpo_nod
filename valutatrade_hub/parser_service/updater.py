"""
Основной модуль для обновления курсов валют.
Обновлен для работы с новым форматом exchange_rates.json.
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
        Сохраняет каждую запись в новом формате exchange_rates.json.

        Returns:
            Словарь со всеми обновленными курсами.

        Raises:
            Exception: При критической ошибке обновления.
        """
        logger.info("Начало обновления курсов валют с новым форматом хранения")

        all_rates = {}
        update_start = datetime.now()
        successful_records = 0
        failed_records = 0

        try:
            # 1. Получаем курсы криптовалют
            logger.info("Получение курсов криптовалют от CoinGecko...")
            crypto_rates = self._get_crypto_rates()

            # Сохраняем каждую запись криптовалюты
            for currency, rate_info in crypto_rates.items():
                try:
                    record = self.storage.create_exchange_rate_record(
                        from_currency=currency,
                        to_currency="USD",
                        rate=rate_info["rate"],
                        source=rate_info.get("source", "CoinGecko"),
                        meta={
                            "raw_id": rate_info.get("raw_id", ""),
                            "request_ms": rate_info.get("request_ms", 0),
                            "status_code": rate_info.get("status_code", 200)
                        }
                    )

                    if self.storage.save_exchange_rate_record(record):
                        all_rates[currency] = rate_info
                        successful_records += 1
                    else:
                        failed_records += 1
                        logger.error(f"Не удалось сохранить запись для {currency}")

                except Exception as e:
                    failed_records += 1
                    logger.error(f"Ошибка при обработке {currency}: {e}")

            logger.info(f"Обработано криптовалют: {len(crypto_rates)} (успешно: {successful_records}, ошибок: {failed_records})")

            # 2. Получаем курсы фиатных валют
            logger.info("Получение курсов фиатных валют...")
            successful_fiat = 0
            failed_fiat = 0

            fiat_rates = self._get_fiat_rates()
            for currency, rate_info in fiat_rates.items():
                try:
                    record = self.storage.create_exchange_rate_record(
                        from_currency=currency,
                        to_currency="USD",
                        rate=rate_info["rate"],
                        source=rate_info.get("source", "ExchangeRate-API"),
                        meta={
                            "request_ms": rate_info.get("request_ms", 0),
                            "status_code": rate_info.get("status_code", 200)
                        }
                    )

                    if self.storage.save_exchange_rate_record(record):
                        all_rates[currency] = rate_info
                        successful_fiat += 1
                    else:
                        failed_fiat += 1
                        logger.error(f"Не удалось сохранить запись для {currency}")

                except Exception as e:
                    failed_fiat += 1
                    logger.error(f"Ошибка при обработке {currency}: {e}")

            logger.info(f"Обработано фиатных валют: {len(fiat_rates)} (успешно: {successful_fiat}, ошибок: {failed_fiat})")

            # 3. Добавляем USD как базовую валюту
            usd_record = self.storage.create_exchange_rate_record(
                from_currency="USD",
                to_currency="USD",
                rate=1.0,
                source="System",
                meta={"note": "Базовая валюта"}
            )

            if self.storage.save_exchange_rate_record(usd_record):
                all_rates["USD"] = {
                    "rate": 1.0,
                    "timestamp": update_start.isoformat() + "Z",
                    "source": "System"
                }
                successful_records += 1
            else:
                failed_records += 1
                logger.error("Не удалось сохранить запись для USD")

            # 4. Обновляем кеш для основного сервиса
            logger.info("Обновление кеша для основного сервиса...")
            if self.storage.update_rates_cache(all_rates):
                logger.info("Кеш успешно обновлен")
            else:
                logger.warning("Не удалось обновить кеш")

            # 5. Обновляем время последнего обновления
            self.last_update_time = update_start

            # 6. Логируем итоговый результат
            total_records = successful_records + successful_fiat
            total_errors = failed_records + failed_fiat

            logger.info("Обновление завершено:")
            logger.info(f"  • Всего обработано записей: {total_records}")
            logger.info(f"  • Ошибок при обработке: {total_errors}")
            logger.info(f"  • Всего валют в кеше: {len(all_rates)}")

            return all_rates

        except Exception as e:
            logger.error(f"Критическая ошибка при обновлении курсов: {e}")
            raise

    def _get_crypto_rates(self) -> Dict:
        """Получает курсы криптовалют с метаданными."""
        try:
            # Предполагаем, что CoinGeckoClient теперь возвращает метаданные
            rates = self.coingecko_client.get_crypto_rates()

            # Добавляем временную метку для каждой записи
            timestamp = datetime.now().isoformat() + "Z"
            for currency in rates:
                rates[currency]["timestamp"] = timestamp

            return rates
        except Exception as e:
            logger.error(f"Ошибка получения курсов криптовалют: {e}")
            return {}

    def _get_fiat_rates(self) -> Dict:
        """Получает курсы фиатных валют с метаданными."""
        try:
            rates = self.exchangerate_client.get_fiat_rates()

            # Добавляем временную метку для каждой записи
            timestamp = datetime.now().isoformat() + "Z"
            for currency in rates:
                rates[currency]["timestamp"] = timestamp

            return rates
        except Exception as e:
            logger.error(f"Ошибка получения курсов фиатных валют: {e}")
            return {}

    def get_update_status(self) -> Dict:
        """
        Возвращает статус последнего обновления.

        Returns:
            Словарь со статусом обновления.
        """
        latest_rates = self.storage.get_latest_rates()

        # Получаем статистику по историческим данным
        historical_data = self.storage.load_exchange_rates()

        status = {
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "total_records": len(historical_data),
            "latest_currencies": len(latest_rates),
            "sources": set(info["source"] for info in latest_rates.values()),
            "currencies": list(latest_rates.keys()),
            "formats": {
                "exchange_rates": "новый формат с уникальными ID",
                "rates_cache": "совместимый формат для основного сервиса"
            }
        }

        return status

    def force_update(self) -> Dict:
        """
        Принудительное обновление курсов.

        Returns:
            Словарь с обновленными курсами.
        """
        logger.warning("Выполняется принудительное обновление курсов")
        return self.update_all_rates()

    def get_historical_stats(self) -> Dict:
        """
        Возвращает статистику по историческим данным.

        Returns:
            Словарь со статистикой.
        """
        historical_data = self.storage.load_exchange_rates()

        if not historical_data:
            return {"message": "Нет исторических данных"}

        # Группируем по валютам
        currencies = {}
        for _record_id, record in historical_data.items():
            currency = record['from_currency']
            if currency not in currencies:
                currencies[currency] = []
            currencies[currency].append(record)

        # Рассчитываем статистику для каждой валюты
        stats = {}
        for currency, records in currencies.items():
            rates = [r['rate'] for r in records]
            times = [datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) for r in records]

            if rates:
                stats[currency] = {
                    "record_count": len(records),
                    "min_rate": min(rates),
                    "max_rate": max(rates),
                    "avg_rate": sum(rates) / len(rates),
                    "first_record": min(times).isoformat(),
                    "last_record": max(times).isoformat(),
                    "sources": set(r['source'] for r in records)
                }

        return {
            "total_records": len(historical_data),
            "unique_currencies": len(stats),
            "currency_stats": stats
        }
