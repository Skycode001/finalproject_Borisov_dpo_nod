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
