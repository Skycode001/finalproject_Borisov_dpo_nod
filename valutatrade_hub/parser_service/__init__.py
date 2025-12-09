"""
Parser Service - микросервис для получения и обновления курсов валют.
"""

from .api_clients import ApiError, CoinGeckoClient, ExchangeRateClient
from .config import (
    CRYPTO_CURRENCIES,
    EXCHANGE_RATES_FILE,
    FIAT_CURRENCIES,
    RATES_CACHE_FILE,
    UPDATE_INTERVAL,
)
from .scheduler import RatesScheduler
from .storage import ExchangeRatesStorage
from .updater import RatesUpdater

__all__ = [
    # Конфигурация
    'EXCHANGE_RATES_FILE',
    'RATES_CACHE_FILE',
    'UPDATE_INTERVAL',
    'FIAT_CURRENCIES',
    'CRYPTO_CURRENCIES',

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
