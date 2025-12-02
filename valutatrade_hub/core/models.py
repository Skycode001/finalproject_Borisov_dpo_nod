import hashlib
from datetime import datetime
import json
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