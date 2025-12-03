import hashlib
from datetime import datetime
from typing import Optional


class User:
    """Класс, представляющий пользователя системы."""

    def __init__(self, username: str, password: str, user_id: Optional[int] = None):
        """
        Инициализация пользователя.

        Args:
            username: Имя пользователя.
            password: Пароль пользователя.
            user_id: Уникальный идентификатор. Если None, будет сгенерирован при сохранении.
        """
        self._user_id = user_id
        self.username = username  # Используем сеттер для проверки
        self._salt = self._generate_salt()
        self.hashed_password = password  # Используем сеттер для хеширования
        self._registration_date = datetime.now()

    # ===== Геттеры =====
    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # ===== Сеттеры с проверками =====
    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value.strip()

    @hashed_password.setter
    def hashed_password(self, plain_password: str):
        if len(plain_password) < 4:
            raise ValueError("Пароль должен содержать не менее 4 символов.")
        self._hashed_password = self._hash_password(plain_password, self._salt)

    # ===== Приватные вспомогательные методы =====
    @staticmethod
    def _generate_salt(length: int = 8) -> str:
        """Генерирует случайную соль."""
        import os
        return os.urandom(length).hex()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Хеширует пароль с использованием соли."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    # ===== Публичные методы =====
    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе (без чувствительных данных)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat()
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        # Сеттер hashed_password выполнит проверку длины и хеширование
        self.hashed_password = new_password
        # При смене пароля можно обновить соль (опционально, для большей безопасности)
        # self._salt = self._generate_salt()
        # self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет, соответствует ли введённый пароль сохранённому хешу."""
        return self._hashed_password == self._hash_password(password, self._salt)

    # ===== Методы для работы с JSON =====
    def to_dict(self) -> dict:
        """Сериализует объект пользователя в словарь для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создает объект User из словаря (при загрузке из JSON)."""
        user = cls.__new__(cls)  # Создаем пустой объект без вызова __init__
        user._user_id = data["user_id"]
        user._username = data["username"]
        user._hashed_password = data["hashed_password"]
        user._salt = data["salt"]
        user._registration_date = datetime.fromisoformat(data["registration_date"])
        return user


class Wallet:
    """Класс, представляющий кошелёк для хранения баланса в конкретной валюте."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """
        Инициализация кошелька.

        Args:
            currency_code: Код валюты (например, "USD", "BTC").
            balance: Начальный баланс. По умолчанию 0.0.
        """
        self.currency_code = currency_code
        self.balance = balance  # Используем сеттер для проверки

    # ===== Геттер и сеттер для balance =====
    @property
    def balance(self) -> float:
        """Возвращает текущий баланс кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float):
        """
        Устанавливает баланс кошелька.

        Args:
            value: Новое значение баланса.

        Raises:
            ValueError: Если значение отрицательное или некорректного типа.
        """
        # Проверка типа
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом (int или float).")

        # Проверка на отрицательное значение
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным.")

        # Приведение к float для единообразия
        self._balance = float(value)

    # ===== Публичные методы =====
    def deposit(self, amount: float) -> None:
        """
        Пополняет баланс кошелька.

        Args:
            amount: Сумма для пополнения.

        Raises:
            ValueError: Если сумма некорректна (не число или отрицательная).
        """
        # Проверка типа и положительности
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма пополнения должна быть числом.")

        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом.")

        # Обновляем баланс через сеттер
        self.balance = self._balance + amount

    def withdraw(self, amount: float) -> bool:
        """
        Снимает средства с кошелька.

        Args:
            amount: Сумма для снятия.

        Returns:
            bool: True если снятие успешно, False если недостаточно средств.

        Raises:
            ValueError: Если сумма некорректна (не число или отрицательная).
        """
        # Проверка типа и положительности
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма снятия должна быть числом.")

        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом.")

        # Проверка достаточности средств
        if amount > self._balance:
            return False

        # Обновляем баланс через сеттер
        self.balance = self._balance - amount
        return True

    def get_balance_info(self) -> dict:
        """
        Возвращает информацию о балансе кошелька.

        Returns:
            dict: Словарь с информацией о кошельке.
        """
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }

    # ===== Методы для работы с JSON =====
    def to_dict(self) -> dict:
        """Сериализует объект кошелька в словарь для сохранения в JSON."""
        return self.get_balance_info()

    @classmethod
    def from_dict(cls, data: dict) -> 'Wallet':
        """Создает объект Wallet из словаря (при загрузке из JSON)."""
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )

class Portfolio:
    """Класс, представляющий портфель всех кошельков одного пользователя."""

    def __init__(self, user_id: int, wallets: dict[str, Wallet] = None):
        """
        Инициализация портфеля пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя.
            wallets: Словарь кошельков. Если None, создается пустой словарь.
        """
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}

    # ===== Геттеры =====
    @property
    def user_id(self) -> int:
        """Возвращает ID пользователя."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    # ===== Публичные методы =====
    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавляет новый кошелёк в портфель.

        Args:
            currency_code: Код валюты для нового кошелька.

        Returns:
            Wallet: Созданный объект кошелька.

        Raises:
            ValueError: Если кошелёк с таким кодом валюты уже существует.
        """
        # Проверка уникальности кода валюты
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк с валютой '{currency_code}' уже существует в портфеле.")

        # Создание нового кошелька и добавление в словарь
        new_wallet = Wallet(currency_code, 0.0)
        self._wallets[currency_code] = new_wallet
        return new_wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """
        Возвращает объект Wallet по коду валюты.

        Args:
            currency_code: Код валюты.

        Returns:
            Wallet: Объект кошелька.

        Raises:
            ValueError: Если кошелёк с таким кодом валюты не найден.
        """
        if currency_code not in self._wallets:
            raise ValueError(f"Кошелёк с валютой '{currency_code}' не найден в портфеле.")
        return self._wallets[currency_code]

    def get_total_value(self, base_currency: str = 'USD') -> float:
        """
        Рассчитывает общую стоимость всех валют в портфеле в базовой валюте.

        Args:
            base_currency: Код базовой валюты для расчета стоимости.

        Returns:
            float: Общая стоимость портфеля в базовой валюте.
        """
        # Фиксированные курсы для упрощения
        exchange_rates = {
            'USD': {'USD': 1.0, 'EUR': 0.92, 'BTC': 0.000025, 'RUB': 95.0, 'ETH': 0.00027},
            'EUR': {'USD': 1.08, 'EUR': 1.0, 'BTC': 0.000027, 'RUB': 102.0, 'ETH': 0.00029},
            'BTC': {'USD': 40000.0, 'EUR': 37000.0, 'BTC': 1.0, 'RUB': 3800000.0, 'ETH': 10.5},
            'RUB': {'USD': 0.0105, 'EUR': 0.0098, 'BTC': 0.00000026, 'RUB': 1.0, 'ETH': 0.0000028},
            'ETH': {'USD': 3720.0, 'EUR': 3400.0, 'BTC': 0.093, 'RUB': 350000.0, 'ETH': 1.0}
        }

        # Приводим к верхнему регистру
        base_currency = base_currency.upper()

        # Если базовая валюта не поддерживается, используем USD
        if base_currency not in exchange_rates:
            base_currency = 'USD'

        total_value = 0.0

        for currency_code, wallet in self._wallets.items():
            currency_code = currency_code.upper()

            if currency_code in exchange_rates and base_currency in exchange_rates[currency_code]:
                # Конвертируем напрямую
                rate = exchange_rates[currency_code][base_currency]
                total_value += wallet.balance * rate
            elif currency_code == base_currency:
                # Та же валюта
                total_value += wallet.balance
            else:
                # Пытаемся конвертировать через USD как промежуточную
                if currency_code in exchange_rates and 'USD' in exchange_rates[currency_code]:
                    to_usd = wallet.balance * exchange_rates[currency_code]['USD']
                    if base_currency in exchange_rates['USD']:
                        total_value += to_usd * exchange_rates['USD'][base_currency]
                    else:
                        total_value += to_usd

        return round(total_value, 2)

    # ===== Методы для работы с JSON =====
    def to_dict(self) -> dict:
        """Сериализует объект портфеля в словарь для сохранения в JSON."""
        wallets_dict = {}
        for currency_code, wallet in self._wallets.items():
            wallets_dict[currency_code] = wallet.to_dict()

        return {
            "user_id": self._user_id,
            "wallets": wallets_dict
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        """Создает объект Portfolio из словаря (при загрузке из JSON)."""
        wallets = {}
        for currency_code, wallet_data in data["wallets"].items():
            wallets[currency_code] = Wallet.from_dict(wallet_data)

        return cls(
            user_id=data["user_id"],
            wallets=wallets
        )
