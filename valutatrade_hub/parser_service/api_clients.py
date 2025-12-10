"""
Модуль для работы с внешними API (CoinGecko и ExchangeRate-API).
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlencode

from ..logging_config import get_logger
from .config import config

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
    """Клиент для работы с CoinGecko API."""

    def __init__(self):
        self.base_url = config.COINGECKO_URL
        self.timeout = config.COINGECKO_TIMEOUT
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY

    def _make_request(self, params: Dict) -> Optional[Dict]:
        """
        Выполняет HTTP-запрос с повторными попытками.

        Args:
            params: Параметры запроса.

        Returns:
            Ответ API или None при ошибке.

        Raises:
            RateLimitExceededError: При превышении лимита запросов.
            NetworkError: При сетевых ошибках.
        """
        for attempt in range(self.max_retries):
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
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise NetworkError(f"HTTP ошибка: {e.code} {e.reason}") from e

            except urllib.error.URLError as e:
                logger.warning(f"Ошибка URL при запросе к CoinGecko (попытка {attempt + 1}): {e.reason}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise NetworkError(f"Ошибка подключения: {e.reason}") from e

            except TimeoutError:
                logger.warning(f"Таймаут при запросе к CoinGecko (попытка {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise NetworkError("Таймаут при подключении к CoinGecko API") from None

            except RateLimitExceededError as e:
                raise e

            except Exception as e:
                logger.error(f"Ошибка при запросе к CoinGecko: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise NetworkError(f"Ошибка API: {str(e)}") from e

        return None

    def get_crypto_rates(self) -> Dict[str, Dict]:
        """
        Получает курсы криптовалют.

        Returns:
            Словарь с курсами криптовалют.

        Raises:
            ApiError: При ошибке получения данных.
        """
        try:
            # Формируем список ID криптовалют для запроса
            crypto_ids = [config.CRYPTO_ID_MAP[currency] for currency in config.CRYPTO_CURRENCIES]
            crypto_ids_param = ",".join(crypto_ids)

            # Параметры запроса
            params = {
                "ids": crypto_ids_param,
                "vs_currencies": config.BASE_CURRENCY.lower()
            }

            # Выполняем запрос
            data = self._make_request(params)
            if not data:
                raise ApiError("Не удалось получить данные от CoinGecko")

            # Преобразуем данные в нужный формат
            rates = {}
            now = datetime.now().isoformat()

            for ticker in config.CRYPTO_CURRENCIES:
                coin_id = config.CRYPTO_ID_MAP[ticker]
                if coin_id in data and config.BASE_CURRENCY.lower() in data[coin_id]:
                    rate = data[coin_id][config.BASE_CURRENCY.lower()]
                    rates[ticker] = {
                        "rate": rate,
                        "updated_at": now,
                        "source": "CoinGecko",
                        "raw_id": coin_id
                    }
                else:
                    logger.warning(f"Курс для {ticker} ({coin_id}) не найден в ответе")

            logger.info(f"Получено {len(rates)} курсов криптовалют от CoinGecko")
            return rates

        except Exception as e:
            logger.error(f"Ошибка получения курсов криптовалют: {e}")
            raise ApiError(f"Ошибка CoinGecko API: {str(e)}") from e


class ExchangeRateClient:
    """Клиент для работы с ExchangeRate-API."""

    def __init__(self):
        self.api_key = config.EXCHANGERATE_API_KEY
        self.base_url = config.exchangerate_full_url
        self.timeout = config.REQUEST_TIMEOUT
        self.is_mock_mode = config.is_mock_mode
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY

    def get_fiat_rates(self) -> Dict[str, Dict]:
        """
        Получает курсы фиатных валют.

        Returns:
            Словарь с курсами фиатных валют.
        """
        now = datetime.now().isoformat()

        if self.is_mock_mode:
            logger.info("Используется заглушка для ExchangeRate-API (режим разработки)")

            # Фиктивные курсы для разработки
            mock_rates = {}
            for currency in config.FIAT_CURRENCIES:
                # Простые фиктивные курсы (можно заменить на более реалистичные)
                mock_rate = {
                    "EUR": 0.92,
                    "GBP": 0.79,
                    "RUB": 95.0,
                    "JPY": 150.0,
                    "CHF": 0.88,
                }.get(currency, 1.0)

                mock_rates[currency] = {
                    "rate": mock_rate,
                    "updated_at": now,
                    "source": "ExchangeRate-API (mock)"
                }

            return mock_rates

        else:
            # Реальный запрос к ExchangeRate-API
            logger.info(f"Реальный запрос к ExchangeRate-API для {len(config.FIAT_CURRENCIES)} валют")

            try:
                for attempt in range(self.max_retries):
                    try:
                        req = urllib.request.Request(
                            self.base_url,
                            headers={
                                'User-Agent': 'ValutaTradeHub/1.0',
                                'Accept': 'application/json'
                            }
                        )

                        response = urllib.request.urlopen(req, timeout=self.timeout)
                        data = response.read()
                        encoding = response.info().get_content_charset('utf-8')
                        decoded_data = data.decode(encoding)
                        json_data = json.loads(decoded_data)

                        if json_data.get("result") != "success":
                            error_type = json_data.get('error-type', 'Unknown error')
                            raise ApiError(f"Ошибка ExchangeRate-API: {error_type}")

                        rates = {}
                        for currency in config.FIAT_CURRENCIES:
                            if currency in json_data.get("rates", {}):
                                rates[currency] = {
                                    "rate": json_data["rates"][currency],
                                    "updated_at": now,
                                    "source": "ExchangeRate-API"
                                }

                        logger.info(f"Получено {len(rates)} курсов фиатных валют от ExchangeRate-API")
                        return rates

                    except Exception as e:
                        if attempt < self.max_retries - 1:
                            logger.warning(f"Ошибка ExchangeRate-API (попытка {attempt + 1}): {e}")
                            time.sleep(self.retry_delay)
                        else:
                            raise

            except Exception as e:
                logger.error(f"Ошибка ExchangeRate-API после {self.max_retries} попыток: {e}")
                # В случае ошибки возвращаем заглушку
                return self._get_fallback_rates(now)

    def _get_fallback_rates(self, timestamp: str) -> Dict[str, Dict]:
        """Резервные курсы на случай ошибки API."""
        logger.warning("Используются резервные курсы ExchangeRate-API")

        fallback_rates = {}
        for currency in config.FIAT_CURRENCIES:
            # Простые фиктивные курсы как резерв
            fallback_rate = {
                "EUR": 0.92,
                "GBP": 0.79,
                "RUB": 95.0,
                "JPY": 150.0,
                "CHF": 0.88,
            }.get(currency, 1.0)

            fallback_rates[currency] = {
                "rate": fallback_rate,
                "updated_at": timestamp,
                "source": "ExchangeRate-API (fallback)"
            }

        return fallback_rates
