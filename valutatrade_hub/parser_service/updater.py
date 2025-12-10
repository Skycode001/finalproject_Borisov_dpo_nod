"""
Модуль для обновления курсов валют.
Координирует весь процесс: получение данных от всех клиентов, их объединение и сохранение.
Обновлен для соответствия требованиям задачи 5.
"""

from datetime import datetime
from typing import Dict, Optional

from ..logging_config import get_logger
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .config import config
from .storage import ExchangeRatesStorage

logger = get_logger(__name__)


class RatesUpdater:
    """
    Координатор обновления курсов валют.
    Точка входа для логики парсинга.
    """

    def __init__(
        self,
        crypto_client: Optional[CoinGeckoClient] = None,
        fiat_client: Optional[ExchangeRateApiClient] = None,
        storage: Optional[ExchangeRatesStorage] = None
    ):
        """
        Инициализация RatesUpdater.

        Args:
            crypto_client: Клиент для получения курсов криптовалют.
            fiat_client: Клиент для получения курсов фиатных валют.
            storage: Хранилище для сохранения данных.
        """
        self.crypto_client = crypto_client or CoinGeckoClient()
        self.fiat_client = fiat_client or ExchangeRateApiClient()
        self.storage = storage or ExchangeRatesStorage()
        self.last_update_time: Optional[datetime] = None

    def run_update(self) -> Dict:
        """
        Основной метод обновления курсов.

        Последовательность действий:
        1. Вызывает fetch_rates() у каждого клиента
        2. Объединяет полученные словари с курсами в один
        3. Добавляет метаданные: source, last_refresh
        4. Передает итоговый объект в storage для сохранения
        5. Ведет подробное логирование каждого шага

        Returns:
            Dict: Итоговый объект с курсами в формате для data/rates.json

        Raises:
            Exception: При критической ошибке обновления.
        """
        logger.info("=" * 50)
        logger.info("🚀 Начало обновления курсов валют")
        logger.info("=" * 50)

        # Словарь для хранения всех курсов в формате {currency: rate_info}
        all_raw_rates = {}
        update_start = datetime.now()
        total_successful = 0
        total_failed = 0

        try:
            # 1. Получение курсов криптовалют
            logger.info("📈 Шаг 1: Получение курсов криптовалют...")
            crypto_rates = self._fetch_crypto_rates_safe()
            total_successful += 1 if crypto_rates else 0
            total_failed += 0 if crypto_rates else 1

            if crypto_rates:
                logger.info(f"✅ Получено {len(crypto_rates)} курсов криптовалют")
                all_raw_rates.update(crypto_rates)
            else:
                logger.warning("❌ Не удалось получить курсы криптовалют")

            # 2. Получение курсов фиатных валют
            logger.info("💵 Шаг 2: Получение курсов фиатных валют...")
            fiat_rates = self._fetch_fiat_rates_safe()
            total_successful += 1 if fiat_rates else 0
            total_failed += 0 if fiat_rates else 1

            if fiat_rates:
                logger.info(f"✅ Получено {len(fiat_rates)} курсов фиатных валют")
                all_raw_rates.update(fiat_rates)
            else:
                logger.warning("❌ Не удалось получить курсы фиатных валют")

            # 3. Добавление базовой валюты
            logger.info("💰 Шаг 3: Добавление базовой валюты...")
            all_raw_rates[config.BASE_CURRENCY] = {
                "rate": 1.0,
                "timestamp": update_start.isoformat() + "Z",
                "source": "System"
            }
            logger.info(f"✅ Базовая валюта {config.BASE_CURRENCY} добавлена")

            # 4. Сохранение в исторические данные (должно быть ДО добавления метаданных)
            logger.info("💾 Шаг 4: Сохранение исторических данных...")
            historical_saved = self._save_historical_data(all_raw_rates)
            if historical_saved:
                logger.info(f"✅ Исторические данные сохранены: {historical_saved} записей")
            else:
                logger.warning("⚠️ Не удалось сохранить исторические данные")

            # 5. Добавление метаданных и создание финального формата для кеша
            logger.info("📊 Шаг 5: Добавление метаданных и создание финального формата...")
            final_rates = self._add_metadata(all_raw_rates, update_start)
            logger.info("✅ Метаданные добавлены")

            # 6. Обновление кеша для основного сервиса
            logger.info("🔄 Шаг 6: Обновление кеша основного сервиса...")
            cache_updated = self.storage.update_rates_cache(all_raw_rates)
            if cache_updated:
                logger.info("✅ Кеш основного сервиса обновлен")
            else:
                logger.error("❌ Не удалось обновить кеш основного сервиса")

            # 7. Обновление времени последнего обновления
            self.last_update_time = update_start

            # 8. Итоговое логирование
            self._log_final_stats(
                final_rates,
                update_start,
                total_successful,
                total_failed,
                historical_saved or 0,
                cache_updated
            )

            return final_rates

        except Exception as e:
            logger.error(f"💥 Критическая ошибка при обновлении курсов: {e}", exc_info=True)
            raise

    def _fetch_crypto_rates_safe(self) -> Dict:
        """
        Безопасное получение курсов криптовалют.

        Возвращает:
            Dict: Словарь с курсами криптовалют в формате {currency: rate_info}
        """
        try:
            logger.debug("Запрос к CoinGecko API...")
            # Используем новый метод fetch_rates() для получения стандартизированного формата
            crypto_rates_raw = self.crypto_client.fetch_rates()

            if not crypto_rates_raw:
                logger.warning("CoinGecko API вернул пустой ответ")
                return {}

            # Преобразуем в формат, совместимый с нашим приложением
            crypto_rates = {}
            timestamp = datetime.now().isoformat() + "Z"

            for pair_key, rate in crypto_rates_raw.items():
                # Извлекаем код валюты из пары (например, из "BTC_USD" берем "BTC")
                parts = pair_key.split('_')
                if len(parts) >= 2:
                    currency_code = parts[0]
                    crypto_rates[currency_code] = {
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": "CoinGecko",
                        "raw_id": config.CRYPTO_ID_MAP.get(currency_code, currency_code.lower())
                    }

            return crypto_rates

        except Exception as e:
            logger.error(f"Ошибка при получении курсов криптовалют: {e}")
            return {}

    def _fetch_fiat_rates_safe(self) -> Dict:
        """
        Безопасное получение курсов фиатных валют.

        Возвращает:
            Dict: Словарь с курсами фиатных валют в формате {currency: rate_info}
        """
        try:
            logger.debug("Запрос к ExchangeRate-API...")
            # Используем новый метод fetch_rates() для получения стандартизированного формата
            fiat_rates_raw = self.fiat_client.fetch_rates()

            if not fiat_rates_raw:
                logger.warning("ExchangeRate-API вернул пустой ответ")
                return {}

            # Преобразуем в формат, совместимый с нашим приложением
            fiat_rates = {}
            timestamp = datetime.now().isoformat() + "Z"

            for pair_key, rate in fiat_rates_raw.items():
                # Извлекаем код валюты из пары (например, из "EUR_USD" берем "EUR")
                parts = pair_key.split('_')
                if len(parts) >= 2:
                    currency_code = parts[0]
                    # Пропускаем пару с самой собой (USD_USD)
                    if currency_code != config.BASE_CURRENCY:
                        fiat_rates[currency_code] = {
                            "rate": rate,
                            "timestamp": timestamp,
                            "source": "ExchangeRate-API" if not self.fiat_client.is_mock_mode
                                      else "ExchangeRate-API (mock)"
                        }

            return fiat_rates

        except Exception as e:
            logger.error(f"Ошибка при получении курсов фиатных валют: {e}")
            return {}

    def _add_metadata(self, raw_rates: Dict, update_time: datetime) -> Dict:
        """
        Добавляет метаданные к курсам и создает финальный формат для кеша.

        Args:
            raw_rates: Словарь с курсами валют в формате {currency: rate_info}
            update_time: Время обновления.

        Returns:
            Dict: Курсы в финальном формате для data/rates.json
        """
        # Формируем данные в формате, который ожидает Core Service
        result = {
            "pairs": {},
            "source": "ParserService",
            "last_refresh": update_time.isoformat() + "Z"
        }

        # Преобразуем raw_rates в формат пар
        for currency, rate_info in raw_rates.items():
            if currency != config.BASE_CURRENCY:
                pair_key = f"{currency}_{config.BASE_CURRENCY}"
                result["pairs"][pair_key] = {
                    "rate": rate_info["rate"],
                    "updated_at": rate_info.get("timestamp", rate_info.get("updated_at", update_time.isoformat() + "Z")),
                    "source": rate_info.get("source", "Unknown")
                }

        # Добавляем пару для базовой валюты
        base_pair = f"{config.BASE_CURRENCY}_{config.BASE_CURRENCY}"
        result["pairs"][base_pair] = {
            "rate": 1.0,
            "updated_at": update_time.isoformat() + "Z",
            "source": "System"
        }

        return result

    def _save_historical_data(self, raw_rates: Dict) -> int:
        """
        Сохраняет курсы в исторические данные.

        Args:
            raw_rates: Словарь с курсами валют в формате {currency: rate_info}

        Returns:
            int: Количество успешно сохраненных записей.
        """
        saved_count = 0
        failed_count = 0

        for currency, rate_info in raw_rates.items():
            try:
                # Создаем запись для исторических данных
                record = self.storage.create_exchange_rate_record(
                    from_currency=currency,
                    to_currency=config.BASE_CURRENCY,
                    rate=rate_info["rate"],
                    source=rate_info.get("source", "Unknown"),
                    meta={
                        "raw_id": rate_info.get("raw_id", ""),
                        "request_ms": rate_info.get("request_ms", 0),
                        "status_code": rate_info.get("status_code", 200)
                    }
                )

                # Сохраняем запись
                if self.storage.save_exchange_rate_record(record):
                    saved_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Не удалось сохранить историческую запись для {currency}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Ошибка при создании записи для {currency}: {e}")

        if failed_count > 0:
            logger.warning(f"Не удалось сохранить {failed_count} исторических записей")

        return saved_count

    def _log_final_stats(
        self,
        final_rates: Dict,
        start_time: datetime,
        successful_clients: int,
        failed_clients: int,
        historical_saved: int,
        cache_updated: bool
    ) -> None:
        """
        Логирует итоговую статистику обновления.
        """
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("=" * 50)
        logger.info("📊 ОБНОВЛЕНИЕ КУРСОВ ЗАВЕРШЕНО")
        logger.info("=" * 50)
        logger.info(f"📅 Время начала: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"⏱️  Продолжительность: {duration:.2f} секунд")
        logger.info(f"✅ Успешных клиентов: {successful_clients}")
        logger.info(f"❌ Неудачных клиентов: {failed_clients}")
        logger.info(f"💾 Сохранено исторических записей: {historical_saved}")
        logger.info(f"🔄 Кеш обновлен: {'Да' if cache_updated else 'Нет'}")

        # Информация о курсах
        pairs_count = len(final_rates.get("pairs", {}))
        logger.info(f"📈 Пар курсов в кеше: {pairs_count}")

        # Список доступных валют
        if "pairs" in final_rates:
            currencies = [pair.split('_')[0] for pair in final_rates["pairs"].keys()
                         if pair.split('_')[0] != config.BASE_CURRENCY]
            logger.info(f"💰 Доступные валюты: {', '.join(sorted(set(currencies)))}")

        logger.info("=" * 50)

    # ===== Методы для обратной совместимости =====

    def update_all_rates(self) -> Dict:
        """
        Старый метод для обратной совместимости.
        Вызывает run_update() и возвращает результат.

        Returns:
            Dict: Все обновленные курсы.
        """
        logger.warning("Метод update_all_rates() устарел. Используйте run_update()")
        return self.run_update()

    def force_update(self) -> Dict:
        """
        Принудительное обновление курсов.

        Returns:
            Dict: Все обновленные курсы.
        """
        logger.info("Выполняется принудительное обновление курсов")
        return self.run_update()

    def get_update_status(self) -> Dict:
        """
        Возвращает статус последнего обновления.

        Returns:
            Dict: Статус обновления.
        """
        latest_rates = self.storage.get_latest_rates()

        # Получаем статистику по историческим данным
        historical_data = self.storage.load_exchange_rates()

        status = {
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "latest_currencies": len(latest_rates),
            "total_records": len(historical_data),  # Добавлено для исправления ошибки
            "currencies": list(latest_rates.keys()),
            "sources": set(info.get("source", "Unknown") for info in latest_rates.values()),
            "formats": {
                "exchange_rates": "новый формат с уникальными ID",
                "rates_cache": "совместимый формат для основного сервиса"
            }
        }

        return status

    def get_historical_stats(self) -> Dict:
        """
        Возвращает статистику по историческим данным.

        Returns:
            Dict: Статистика исторических данных.
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


def create_updater() -> RatesUpdater:
    """
    Фабричная функция для создания RatesUpdater.

    Returns:
        RatesUpdater: Экземпляр RatesUpdater.
    """
    return RatesUpdater()
