from abc import ABC, abstractmethod
from typing import Dict

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс для валют."""

    def __init__(self, name: str, code: str):
        """
        Инициализация валюты.

        Args:
            name: Человекочитаемое имя валюты.
            code: ISO-код или тикер валюты.

        Raises:
            ValueError: Если параметры не проходят валидацию.
        """
        self._validate_name(name)
        self._validate_code(code)

        self._name = name
        self._code = code.upper()

    def _validate_name(self, name: str) -> None:
        """Проверяет корректность имени валюты."""
        if not name or not isinstance(name, str):
            raise ValueError("Имя валюты должно быть непустой строкой")
        if not name.strip():
            raise ValueError("Имя валюты не может состоять только из пробелов")

    def _validate_code(self, code: str) -> None:
        """Проверяет корректность кода валюты."""
        if not code or not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")

        code = code.strip().upper()
        if len(code) < 2 or len(code) > 5:
            raise ValueError("Код валюты должен содержать от 2 до 5 символов")
        if not code.isalnum():
            raise ValueError("Код валюты должен содержать только буквы и цифры")
        if ' ' in code:
            raise ValueError("Код валюты не должен содержать пробелы")

    @property
    def name(self) -> str:
        """Возвращает человекочитаемое имя валюты."""
        return self._name

    @property
    def code(self) -> str:
        """Возвращает код валюты."""
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        """
        Возвращает строковое представление валюты для UI/логов.

        Returns:
            str: Отформатированная информация о валюте.
        """
        pass

    def __str__(self) -> str:
        """Строковое представление валюты."""
        return f"{self.code} - {self.name}"

    def __repr__(self) -> str:
        """Представление для отладки."""
        return f"{self.__class__.__name__}(name='{self.name}', code='{self.code}')"


class FiatCurrency(Currency):
    """Класс, представляющий фиатную валюту."""

    def __init__(self, name: str, code: str, issuing_country: str):
        """
        Инициализация фиатной валюты.

        Args:
            name: Человекочитаемое имя валюты.
            code: ISO-код валюты.
            issuing_country: Страна или зона эмиссии.

        Raises:
            ValueError: Если страна эмиссии не указана.
        """
        super().__init__(name, code)

        if not issuing_country or not isinstance(issuing_country, str):
            raise ValueError("Страна эмиссии должна быть непустой строкой")

        self._issuing_country = issuing_country.strip()

    @property
    def issuing_country(self) -> str:
        """Возвращает страну эмиссии валюты."""
        return self._issuing_country

    def get_display_info(self) -> str:
        """
        Возвращает строковое представление фиатной валюты.

        Returns:
            str: Отформатированная информация о фиатной валюте.
        """
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Класс, представляющий криптовалюту."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        """
        Инициализация криптовалюты.

        Args:
            name: Человекочитаемое имя криптовалюты.
            code: Тикер криптовалюты.
            algorithm: Алгоритм консенсуса/майнинга.
            market_cap: Рыночная капитализация (по умолчанию 0.0).

        Raises:
            ValueError: Если алгоритм не указан или капитализация отрицательная.
        """
        super().__init__(name, code)

        if not algorithm or not isinstance(algorithm, str):
            raise ValueError("Алгоритм должен быть непустой строкой")

        if market_cap < 0:
            raise ValueError("Рыночная капитализация не может быть отрицательной")

        self._algorithm = algorithm.strip()
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        """Возвращает алгоритм криптовалюты."""
        return self._algorithm

    @property
    def market_cap(self) -> float:
        """Возвращает рыночную капитализацию криптовалюты."""
        return self._market_cap

    def get_display_info(self) -> str:
        """
        Возвращает строковое представление криптовалюты.

        Returns:
            str: Отформатированная информация о криптовалюте.
        """
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap >= 1e6 else f"{self.market_cap:,.2f}"
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"


# Реестр валют
_CURRENCY_REGISTRY: Dict[str, Currency] = {}


def _initialize_currency_registry() -> None:
    """Инициализирует реестр валют предопределенными значениями."""
    # Фиатные валюты
    fiats = [
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        FiatCurrency("British Pound", "GBP", "United Kingdom"),
        FiatCurrency("Japanese Yen", "JPY", "Japan"),
        FiatCurrency("Swiss Franc", "CHF", "Switzerland"),
    ]

    # Криптовалюты
    cryptos = [
        CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
        CryptoCurrency("Litecoin", "LTC", "Scrypt", 6.5e9),
        CryptoCurrency("Ripple", "XRP", "XRP Ledger Consensus", 3.0e10),
        CryptoCurrency("Cardano", "ADA", "Ouroboros", 1.5e10),
    ]

    # Добавляем все валюты в реестр
    for currency in fiats + cryptos:
        _CURRENCY_REGISTRY[currency.code] = currency


def get_currency(code: str) -> Currency:
    """
    Возвращает объект валюты по коду.

    Args:
        code: Код валюты.

    Returns:
        Currency: Объект валюты.

    Raises:
        CurrencyNotFoundError: Если валюта с таким кодом не найдена.
    """
    code = code.upper()

    # Инициализируем реестр при первом вызове
    if not _CURRENCY_REGISTRY:
        _initialize_currency_registry()

    if code not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code)  # Изменено здесь

    return _CURRENCY_REGISTRY[code]


def get_all_currencies() -> Dict[str, Currency]:
    """
    Возвращает все доступные валюты.

    Returns:
        Dict[str, Currency]: Словарь код->валюта.
    """
    if not _CURRENCY_REGISTRY:
        _initialize_currency_registry()

    return _CURRENCY_REGISTRY.copy()


def register_currency(currency: Currency) -> None:
    """
    Регистрирует новую валюту в реестре.

    Args:
        currency: Объект валюты для регистрации.

    Raises:
        ValueError: Если валюта с таким кодом уже существует.
    """
    code = currency.code

    if not _CURRENCY_REGISTRY:
        _initialize_currency_registry()

    if code in _CURRENCY_REGISTRY:
        raise ValueError(f"Валюта с кодом '{code}' уже зарегистрирована")

    _CURRENCY_REGISTRY[code] = currency
