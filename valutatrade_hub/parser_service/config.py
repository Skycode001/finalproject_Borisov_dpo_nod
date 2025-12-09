"""
Конфигурация для Parser Service.
"""

import os

# ===== API КОНФИГУРАЦИЯ =====

# ExchangeRate-API (пока заглушка - позже добавить реальный ключ)
EXCHANGERATE_API_KEY = os.environ.get("EXCHANGERATE_API_KEY", "MOCK_KEY_FOR_NOW")
EXCHANGERATE_API_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/USD"

# CoinGecko API (публичный доступ)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_TIMEOUT = 10  # секунд

# ===== ВАЛЮТЫ ДЛЯ ЗАПРОСА =====

# Фиатные валюты (ISO коды)
FIAT_CURRENCIES = ["EUR", "GBP", "RUB", "JPY", "CHF"]

# Криптовалюты: маппинг тикер -> ID в CoinGecko
CRYPTO_CURRENCIES = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "SOL": "solana",
    "DOT": "polkadot",
}

# ===== НАСТРОЙКИ ОБНОВЛЕНИЯ =====

# Интервал обновления курсов (в секундах)
UPDATE_INTERVAL = 300  # 5 минут

# Максимальное количество попыток при ошибке
MAX_RETRIES = 3

# Задержка между попытками (в секундах)
RETRY_DELAY = 2

# ===== НАСТРОЙКИ ХРАНЕНИЯ =====

# Файл для хранения курсов от Parser Service
EXCHANGE_RATES_FILE = "data/exchange_rates.json"

# Файл кеша для основного сервиса
RATES_CACHE_FILE = "data/rates.json"

# ===== ЛОГИРОВАНИЕ =====

PARSER_LOG_FILE = "logs/parser_service.log"
