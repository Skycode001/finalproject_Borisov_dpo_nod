"""
Модуль для работы с внешними API (CoinGecko и ExchangeRate-API).
Использует только стандартные библиотеки Python.
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlencode

from ..logging_config import get_logger
from .config import (
    COINGECKO_API_URL,
    COINGECKO_TIMEOUT,
    CRYPTO_CURRENCIES,
    EXCHANGERATE_API_KEY,
    EXCHANGERATE_API_URL,
    FIAT_CURRENCIES,
    MAX_RETRIES,
    RETRY_DELAY,
)

logger = get_logger(__name__)


class ApiError(Exception):
    """Базовое исключение для ошибок API."""
    pass


class RateLimitExceededError(ApiError):
    """Исключение при превышении лимита запросов."""
    pass


class NetworkError(ApiError):
    """Исключение при сетевых ошибках."""
    pass


class CoinGeckoClient:
    """Клиент для работы с CoinGecko API (использует только стандартные библиотеки)."""

    def __init__(self):
        self.base_url = COINGECKO_API_URL
        self.timeout = COINGECKO_TIMEOUT

    def _make_request(self, params: Dict) -> Optional[Dict]:
        """
        Выполняет HTTP-запрос с повторными попытками.
        Использует urllib.request (стандартная библиотека).

        Args:
            params: Параметры запроса.

        Returns:
            Ответ API или None при ошибке.

        Raises:
            RateLimitExceededError: При превышении лимита запросов.
            NetworkError: При сетевых ошибках.
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Формируем URL с параметрами
                query_string = urlencode(params)
                url = f"{self.base_url}?{query_string}"

                logger.debug(f"CoinGecko запрос (попытка {attempt + 1}): {url}")

                # Создаем запрос
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'ValutaTradeHub/1.0',
                        'Accept': 'application/json'
                    }
                )

                # Выполняем запрос с таймаутом
                response = urllib.request.urlopen(req, timeout=self.timeout)

                # Проверка статуса
                if response.status == 429:  # Too Many Requests
                    raise RateLimitExceededError("Превышен лимит запросов к CoinGecko API")

                # Читаем и декодируем ответ
                data = response.read()
                encoding = response.info().get_content_charset('utf-8')
                decoded_data = data.decode(encoding)

                return json.loads(decoded_data)

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    raise RateLimitExceededError("Превышен лимит запросов к CoinGecko API") from e
                logger.warning(f"HTTP ошибка {e.code} при запросе к CoinGecko (попытка {attempt + 1}): {e.reason}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise NetworkError(f"HTTP ошибка: {e.code} {e.reason}") from e

            except urllib.error.URLError as e:
                logger.warning(f"Ошибка URL при запросе к CoinGecko (попытка {attempt + 1}): {e.reason}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise NetworkError(f"Ошибка подключения: {e.reason}") from e

            except TimeoutError:
                logger.warning(f"Таймаут при запросе к CoinGecko (попытка {attempt + 1})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise NetworkError("Таймаут при подключении к CoinGecko API") from None

            except RateLimitExceededError as e:
                raise e

            except Exception as e:
                logger.error(f"Ошибка при запросе к CoinGecko: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise NetworkError(f"Ошибка API: {str(e)}") from e

        return None

    def get_crypto_rates(self) -> Dict[str, Dict]:
        """
        Получает курсы криптовалют.

        Returns:
            Словарь с курсами криптовалют.
            Формат: {"BTC": {"rate": 50000.0, "updated_at": "timestamp", "source": "CoinGecko"}, ...}

        Raises:
            ApiError: При ошибке получения данных.
        """
        try:
            # Формируем список ID криптовалют для запроса
            crypto_ids = list(CRYPTO_CURRENCIES.values())
            crypto_ids_param = ",".join(crypto_ids)

            # Параметры запроса
            params = {
                "ids": crypto_ids_param,
                "vs_currencies": "usd"
            }

            # Выполняем запрос
            data = self._make_request(params)
            if not data:
                raise ApiError("Не удалось получить данные от CoinGecko")

            # Преобразуем данные в нужный формат
            rates = {}
            now = datetime.now().isoformat()

            for ticker, coin_id in CRYPTO_CURRENCIES.items():
                if coin_id in data and "usd" in data[coin_id]:
                    rate = data[coin_id]["usd"]
                    rates[ticker] = {
                        "rate": rate,
                        "updated_at": now,
                        "source": "CoinGecko"
                    }
                else:
                    logger.warning(f"Курс для {ticker} ({coin_id}) не найден в ответе")

            logger.info(f"Получено {len(rates)} курсов криптовалют от CoinGecko")
            return rates

        except Exception as e:
            logger.error(f"Ошибка получения курсов криптовалют: {e}")
            raise ApiError(f"Ошибка CoinGecko API: {str(e)}") from e


class ExchangeRateClient:
    """Клиент для работы с ExchangeRate-API (пока заглушка)."""

    def __init__(self):
        self.base_url = EXCHANGERATE_API_URL
        self.api_key = EXCHANGERATE_API_KEY
        self.is_mock_mode = self.api_key == "MOCK_KEY_FOR_NOW"

    def get_fiat_rates(self) -> Dict[str, Dict]:
        """
        Получает курсы фиатных валют.

        В режиме заглушки возвращает фиктивные данные.
        При наличии реального ключа - делает запрос к API.

        Returns:
            Словарь с курсами фиатных валют.
        """
        now = datetime.now().isoformat()

        if self.is_mock_mode:
            logger.info("Используется заглушка для ExchangeRate-API (режим разработки)")

            # Фиктивные курсы для разработки
            mock_rates = {
                "EUR": {"rate": 0.92, "updated_at": now, "source": "ExchangeRate-API (mock)"},
                "GBP": {"rate": 0.79, "updated_at": now, "source": "ExchangeRate-API (mock)"},
                "RUB": {"rate": 95.0, "updated_at": now, "source": "ExchangeRate-API (mock)"},
                "JPY": {"rate": 150.0, "updated_at": now, "source": "ExchangeRate-API (mock)"},
                "CHF": {"rate": 0.88, "updated_at": now, "source": "ExchangeRate-API (mock)"},
            }

            return mock_rates

        else:
            # Реальный запрос с использованием urllib
            logger.info("Реальный запрос к ExchangeRate-API")

            try:
                url = self.base_url.format(key=self.api_key)

                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'ValutaTradeHub/1.0',
                        'Accept': 'application/json'
                    }
                )

                response = urllib.request.urlopen(req, timeout=10)
                data = response.read()
                encoding = response.info().get_content_charset('utf-8')
                decoded_data = data.decode(encoding)
                json_data = json.loads(decoded_data)

                if json_data.get("result") != "success":
                    raise ApiError(f"Ошибка ExchangeRate-API: {json_data.get('error-type', 'Unknown error')}")

                rates = {}
                for currency in FIAT_CURRENCIES:
                    if currency in json_data.get("rates", {}):
                        rates[currency] = {
                            "rate": json_data["rates"][currency],
                            "updated_at": now,
                            "source": "ExchangeRate-API"
                        }

                return rates

            except Exception as e:
                logger.error(f"Ошибка ExchangeRate-API: {e}")
                # В случае ошибки возвращаем заглушку
                return self._get_fallback_rates(now)

    def _get_fallback_rates(self, timestamp: str) -> Dict[str, Dict]:
        """Резервные курсы на случай ошибки API."""
        return {
            "EUR": {"rate": 0.92, "updated_at": timestamp, "source": "ExchangeRate-API (fallback)"},
            "GBP": {"rate": 0.79, "updated_at": timestamp, "source": "ExchangeRate-API (fallback)"},
            "RUB": {"rate": 95.0, "updated_at": timestamp, "source": "ExchangeRate-API (fallback)"},
        }
