"""
Parser Service - микросервис для получения и обновления курсов валют.
"""

from .api_clients import ApiError, CoinGeckoClient, ExchangeRateClient
from .config import (  # <-- ИЗМЕНЕНИЕ: удалите старые константы
    ParserConfig,
    config,
    reload_config,
)
from .scheduler import RatesScheduler
from .storage import ExchangeRatesStorage
from .updater import RatesUpdater

__all__ = [
    # Конфигурация
    'config',
    'ParserConfig',
    'reload_config',

    # API клиенты
    'CoinGeckoClient',
    'ExchangeRateClient',
    'ApiError',

    # Хранилище
    'ExchangeRatesStorage',

    # Обновление
    'RatesUpdater',

    # Планировщик
    'RatesScheduler',
]
