"""
Parser Service - микросервис для получения и обновления курсов валют.
"""

from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig, config, reload_config
from .scheduler import RatesScheduler
from .storage import ExchangeRatesStorage
from .updater import RatesUpdater, create_updater  # ДОБАВЛЕНО create_updater

# Алиасы для обратной совместимости
ExchangeRateClient = ExchangeRateApiClient
ApiError = Exception  # Для обратной совместимости

__all__ = [
    # Конфигурация
    'config',
    'ParserConfig',
    'reload_config',

    # API клиенты
    'CoinGeckoClient',
    'ExchangeRateApiClient',
    'ExchangeRateClient',  # Алиас для обратной совместимости
    'ApiError',

    # Хранилище
    'ExchangeRatesStorage',

    # Обновление
    'RatesUpdater',
    'create_updater',

    # Планировщик
    'RatesScheduler',
]
