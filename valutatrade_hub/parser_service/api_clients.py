"""
Модуль для работы с внешними API (CoinGecko и ExchangeRate-API).
Реализует абстрактный базовый класс BaseApiClient с единым интерфейсом.
"""

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlencode

from ..core.exceptions import ApiRequestError
from ..logging_config import get_logger
from .config import config

logger = get_logger(__name__)


class BaseApiClient(ABC):
    """Абстрактный базовый класс для клиентов внешних API."""

    def __init__(self, timeout: int = 10, max_retries: int = 3, retry_delay: int = 2):
        """
        Инициализация базового клиента.

        Args:
            timeout: Таймаут запроса в секундах.
            max_retries: Максимальное количество повторных попыток.
            retry_delay: Задержка между попытками в секундах.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы валют от API.

        Returns:
            Словарь с курсами в формате {currency_pair: rate}.
            Пример: {"BTC_USD": 59337.21, "EUR_USD": 1.0786}

        Raises:
            ApiRequestError: При ошибке запроса к API.
        """
        pass

    def _make_request(self, url: str, headers: Optional[Dict] = None) -> Dict:
        """
        Выполняет HTTP-запрос с повторными попытками и обработкой ошибок.

        Args:
            url: URL для запроса.
            headers: Заголовки HTTP-запроса.

        Returns:
            Ответ API в виде словаря.

        Raises:
            ApiRequestError: При ошибке запроса.
        """
        if headers is None:
            headers = {
                'User-Agent': 'ValutaTradeHub/1.0',
                'Accept': 'application/json'
            }

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Запрос к API (попытка {attempt + 1}): {url}")

                req = urllib.request.Request(url, headers=headers)
                response = urllib.request.urlopen(req, timeout=self.timeout)

                # Проверка статуса ответа
                if response.status == 429:  # Too Many Requests
                    raise ApiRequestError("Превышен лимит запросов к API")

                if response.status != 200:
                    raise ApiRequestError(f"API вернул статус {response.status}")

                # Чтение и декодирование ответа
                data = response.read()
                encoding = response.info().get_content_charset('utf-8')
                decoded_data = data.decode(encoding)

                return json.loads(decoded_data)

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    raise ApiRequestError(f"Превышен лимит запросов: {e.reason}") from e
                elif e.code == 401:
                    raise ApiRequestError(f"Неверный API ключ: {e.reason}") from e
                elif e.code == 403:
                    raise ApiRequestError(f"Доступ запрещен: {e.reason}") from e
                elif 400 <= e.code < 500:
                    raise ApiRequestError(f"Ошибка клиента {e.code}: {e.reason}") from e
                elif 500 <= e.code < 600:
                    logger.warning(f"Серверная ошибка {e.code} (попытка {attempt + 1}): {e.reason}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    raise ApiRequestError(f"Серверная ошибка {e.code}: {e.reason}") from e
                else:
                    raise ApiRequestError(f"HTTP ошибка {e.code}: {e.reason}") from e

            except urllib.error.URLError as e:
                logger.warning(f"Ошибка сети (попытка {attempt + 1}): {e.reason}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise ApiRequestError(f"Ошибка сети: {e.reason}") from e

            except TimeoutError as e:
                logger.warning(f"Таймаут (попытка {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise ApiRequestError("Таймаут при подключении к API") from e

            except json.JSONDecodeError as e:
                raise ApiRequestError(f"Ошибка декодирования JSON ответа: {e}") from e

            except Exception as e:
                logger.error(f"Неизвестная ошибка (попытка {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise ApiRequestError(f"Неизвестная ошибка: {str(e)}") from e

        raise ApiRequestError(f"Не удалось выполнить запрос после {self.max_retries} попыток")


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API."""

    def __init__(self):
        super().__init__(
            timeout=config.COINGECKO_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        self.base_url = config.COINGECKO_URL

    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы криптовалют от CoinGecko API.

        Returns:
            Словарь с курсами в формате {crypto_USD: rate}.

        Raises:
            ApiRequestError: При ошибке запроса к CoinGecko API.
        """
        try:
            logger.info("Получение курсов криптовалют от CoinGecko...")

            # Формируем список ID криптовалют для запроса
            crypto_ids = [config.CRYPTO_ID_MAP[currency] for currency in config.CRYPTO_CURRENCIES]
            crypto_ids_param = ",".join(crypto_ids)

            # Формируем URL с параметрами
            params = {
                "ids": crypto_ids_param,
                "vs_currencies": config.BASE_CURRENCY.lower()
            }

            query_string = urlencode(params)
            url = f"{self.base_url}?{query_string}"

            # Выполняем запрос через базовый класс
            response_data = self._make_request(url)

            # Преобразуем данные в стандартизированный формат
            rates = {}

            for ticker in config.CRYPTO_CURRENCIES:
                coin_id = config.CRYPTO_ID_MAP[ticker]

                if coin_id in response_data:
                    currency_data = response_data[coin_id]
                    if config.BASE_CURRENCY.lower() in currency_data:
                        rate = currency_data[config.BASE_CURRENCY.lower()]
                        pair_key = f"{ticker}_{config.BASE_CURRENCY}"
                        rates[pair_key] = float(rate)
                    else:
                        logger.warning(f"Курс {config.BASE_CURRENCY} для {ticker} ({coin_id}) не найден")
                else:
                    logger.warning(f"Данные для {ticker} ({coin_id}) не найдены в ответе")

            logger.info(f"Получено {len(rates)} курсов криптовалют от CoinGecko")
            return rates

        except ApiRequestError:
            raise  # Пробрасываем уже обработанные ошибки
        except Exception as e:
            logger.error(f"Ошибка получения курсов от CoinGecko: {e}")
            raise ApiRequestError(f"Ошибка CoinGecko API: {str(e)}") from e

    def get_crypto_rates(self) -> Dict[str, Dict]:
        """
        Старый метод для обратной совместимости.
        Получает курсы криптовалют с дополнительными метаданными.

        Returns:
            Словарь с курсами криптовалют и метаданными.
        """
        try:
            # Получаем курсы через новый метод
            rates = self.fetch_rates()

            # Преобразуем в старый формат
            result = {}
            now = datetime.now().isoformat()

            for pair, rate in rates.items():
                # Извлекаем код валюты из пары (например, из "BTC_USD" берем "BTC")
                currency_code = pair.split('_')[0]
                coin_id = config.CRYPTO_ID_MAP.get(currency_code, currency_code.lower())

                result[currency_code] = {
                    "rate": rate,
                    "updated_at": now,
                    "source": "CoinGecko",
                    "raw_id": coin_id
                }

            return result

        except Exception as e:
            logger.error(f"Ошибка в get_crypto_rates: {e}")
            raise


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API."""

    def __init__(self):
        super().__init__(
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        self.api_key = config.EXCHANGERATE_API_KEY
        self.base_url = config.EXCHANGERATE_API_URL
        self.is_mock_mode = config.is_mock_mode

    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы фиатных валют от ExchangeRate-API.

        Returns:
            Словарь с курсами в формате {fiat_USD: rate}.

        Raises:
            ApiRequestError: При ошибке запроса к ExchangeRate-API.
        """
        # Если режим заглушки, возвращаем фиктивные данные
        if self.is_mock_mode:
            logger.info("Используется заглушка для ExchangeRate-API (режим разработки)")
            return self._get_mock_rates()

        try:
            logger.info("Получение курсов фиатных валют от ExchangeRate-API...")

            # Формируем URL
            url = f"{self.base_url}/{self.api_key}/latest/{config.BASE_CURRENCY}"

            # Выполняем запрос через базовый класс
            response_data = self._make_request(url)

            # Проверяем успешность ответа
            if response_data.get("result") != "success":
                error_type = response_data.get("error-type", "unknown_error")
                raise ApiRequestError(f"ExchangeRate-API ошибка: {error_type}")

            # Извлекаем курсы из ответа
            raw_rates = response_data.get("rates", {})

            # Преобразуем данные в стандартизированный формат
            rates = {}

            for currency in config.FIAT_CURRENCIES:
                if currency in raw_rates:
                    rate = raw_rates[currency]
                    pair_key = f"{currency}_{config.BASE_CURRENCY}"
                    rates[pair_key] = float(rate)
                else:
                    logger.warning(f"Курс для {currency} не найден в ответе")

            # Добавляем базовую валюту (USD_USD = 1.0)
            base_pair = f"{config.BASE_CURRENCY}_{config.BASE_CURRENCY}"
            rates[base_pair] = 1.0

            logger.info(f"Получено {len(rates)} курсов фиатных валют от ExchangeRate-API")
            return rates

        except ApiRequestError:
            raise  # Пробрасываем уже обработанные ошибки
        except Exception as e:
            logger.error(f"Ошибка получения курсов от ExchangeRate-API: {e}")
            # В случае ошибки возвращаем резервные данные
            return self._get_fallback_rates()

    def _get_mock_rates(self) -> Dict[str, float]:
        """Возвращает фиктивные курсы для режима разработки."""
        mock_rates = {
            # EUR к USD
            "EUR_USD": 1.0786,
            # GBP к USD
            "GBP_USD": 1.2598,
            # RUB к USD (обратный курс: 1 USD = 98.45 RUB, значит 1 RUB = 0.01016 USD)
            "RUB_USD": 0.01016,
            # JPY к USD (пример: 1 USD = 150 JPY, значит 1 JPY = 0.00667 USD)
            "JPY_USD": 0.00667,
            # CHF к USD
            "CHF_USD": 1.1350,
            # Базовая валюта
            "USD_USD": 1.0
        }
        return mock_rates

    def _get_fallback_rates(self) -> Dict[str, float]:
        """Возвращает резервные курсы на случай ошибки API."""
        logger.warning("Используются резервные курсы ExchangeRate-API")
        return self._get_mock_rates()

    def get_fiat_rates(self) -> Dict[str, Dict]:
        """
        Старый метод для обратной совместимости.
        Получает курсы фиатных валют с дополнительными метаданными.

        Returns:
            Словарь с курсами фиатных валют и метаданными.
        """
        try:
            # Получаем курсы через новый метод
            rates = self.fetch_rates()

            # Преобразуем в старый формат
            result = {}
            now = datetime.now().isoformat()

            for pair, rate in rates.items():
                # Извлекаем код валюты из пары (например, из "EUR_USD" берем "EUR")
                if pair == "USD_USD":
                    continue  # Пропускаем пару с самой собой

                currency_code = pair.split('_')[0]

                # Определяем источник
                if self.is_mock_mode:
                    source = "ExchangeRate-API (mock)"
                else:
                    source = "ExchangeRate-API"

                result[currency_code] = {
                    "rate": rate,
                    "updated_at": now,
                    "source": source
                }

            return result

        except Exception as e:
            logger.error(f"Ошибка в get_fiat_rates: {e}")
            raise


# Алиасы для обратной совместимости
ExchangeRateClient = ExchangeRateApiClient
