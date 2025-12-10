"""
Конфигурация для Parser Service.
Использует dataclass для структурированного хранения настроек.
Чувствительные данные (API-ключи) загружаются из переменных окружения.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class ParserConfig:
    """
    Конфигурация Parser Service.

    Атрибуты:
        EXCHANGERATE_API_KEY: Ключ для ExchangeRate-API (из переменной окружения)
        COINGECKO_URL: URL API CoinGecko
        EXCHANGERATE_API_URL: Базовый URL ExchangeRate-API
        BASE_CURRENCY: Базовая валюта для запросов
        FIAT_CURRENCIES: Список отслеживаемых фиатных валют
        CRYPTO_CURRENCIES: Список отслеживаемых криптовалют
        CRYPTO_ID_MAP: Сопоставление кодов валют с ID CoinGecko
        RATES_FILE_PATH: Путь к файлу кеша курсов
        HISTORY_FILE_PATH: Путь к файлу исторических данных
        REQUEST_TIMEOUT: Таймаут запросов в секундах
        UPDATE_INTERVAL: Интервал обновления в секундах
        MAX_RETRIES: Максимальное количество повторных попыток
        RETRY_DELAY: Задержка между попытками в секундах
        RATES_CACHE_TTL_MINUTES: TTL кеша курсов в минутах
    """

    # ===== API КЛЮЧИ (из переменных окружения) =====
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv(
            "EXCHANGERATE_API_KEY",
            "MOCK_KEY_FOR_NOW"  # Значение по умолчанию для разработки
        )
    )

    # ===== ЭНДПОИНТЫ API =====
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # ===== ВАЛЮТЫ И КОДИРОВКИ =====
    BASE_CURRENCY: str = "USD"

    # Фиатные валюты для отслеживания
    FIAT_CURRENCIES: Tuple[str, ...] = ("EUR", "GBP", "RUB", "JPY", "CHF")

    # Криптовалюты для отслеживания
    CRYPTO_CURRENCIES: Tuple[str, ...] = ("BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT")

    # Сопоставление кодов валют с ID CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "LTC": "litecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "SOL": "solana",
        "DOT": "polkadot",
    })

    # ===== ПУТИ К ФАЙЛАМ =====
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"
    PARSER_LOG_FILE: str = "logs/parser_service.log"

    # ===== ПАРАМЕТРЫ ЗАПРОСОВ =====
    REQUEST_TIMEOUT: int = 10  # секунд
    COINGECKO_TIMEOUT: int = 10  # секунд

    # ===== НАСТРОЙКИ ОБНОВЛЕНИЯ =====
    UPDATE_INTERVAL: int = 300  # 5 минут в секундах
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2  # секунд

    # ===== НАСТРОЙКИ КЕША =====
    RATES_CACHE_TTL_MINUTES: int = 5
    MAX_CACHE_PAIRS: int = 100

    # ===== МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ПОЛНЫХ URL =====

    @property
    def exchangerate_full_url(self) -> str:
        """
        Возвращает полный URL для запроса к ExchangeRate-API.

        Returns:
            str: Полный URL с подставленным API ключом
        """
        return f"{self.EXCHANGERATE_API_URL}/{self.EXCHANGERATE_API_KEY}/latest/{self.BASE_CURRENCY}"

    @property
    def is_mock_mode(self) -> bool:
        """
        Проверяет, используется ли режим заглушки для ExchangeRate-API.

        Returns:
            bool: True если используется заглушка, False если реальный ключ
        """
        return self.EXCHANGERATE_API_KEY == "MOCK_KEY_FOR_NOW"

    def validate_config(self) -> None:
        """
        Проверяет корректность конфигурации.

        Raises:
            ValueError: Если конфигурация некорректна
        """
        # Проверка обязательных параметров
        if not self.EXCHANGERATE_API_KEY:
            raise ValueError("EXCHANGERATE_API_KEY не задан")

        if not self.BASE_CURRENCY:
            raise ValueError("BASE_CURRENCY не задан")

        if not self.FIAT_CURRENCIES:
            raise ValueError("FIAT_CURRENCIES не заданы")

        if not self.CRYPTO_CURRENCIES:
            raise ValueError("CRYPTO_CURRENCIES не заданы")

        # Проверка соответствия CRYPTO_CURRENCIES и CRYPTO_ID_MAP
        for currency in self.CRYPTO_CURRENCIES:
            if currency not in self.CRYPTO_ID_MAP:
                raise ValueError(f"Валюта {currency} отсутствует в CRYPTO_ID_MAP")

        # Проверка параметров времени
        if self.REQUEST_TIMEOUT <= 0:
            raise ValueError("REQUEST_TIMEOUT должен быть положительным числом")

        if self.UPDATE_INTERVAL <= 0:
            raise ValueError("UPDATE_INTERVAL должен быть положительным числом")

        if self.MAX_RETRIES < 0:
            raise ValueError("MAX_RETRIES не может быть отрицательным")


# Создаем глобальный экземпляр конфигурации
config = ParserConfig()


def reload_config() -> ParserConfig:
    """
    Перезагружает конфигурацию из переменных окружения.

    Returns:
        ParserConfig: Обновленная конфигурация
    """
    global config
    config = ParserConfig()
    config.validate_config()
    return config
