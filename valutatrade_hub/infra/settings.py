import json
import os
from typing import Any, Dict

from ..logging_config import get_logger


class SettingsLoader:
    """
    Singleton класс для загрузки конфигурации.
    """

    _instance = None
    _settings = None

    def __new__(cls):
        """Обеспечивает создание только одного экземпляра класса."""
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Инициализирует загрузчик настроек."""
        self.logger = get_logger(__name__)
        self._settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """
        Загружает настройки из файла или использует значения по умолчанию.

        Returns:
            Dict[str, Any]: Словарь с настройками.
        """
        default_settings = {
            "app": {
                "name": "ValutaTrade Hub",
                "version": "1.0.0",
                "debug": False
            },
            "database": {
                "path": "data",
                "users_file": "users.json",
                "portfolios_file": "portfolios.json",
                "rates_file": "rates.json",
                "backup_enabled": True,
                "backup_dir": "backups"
            },
            "logging": {
                "level": "INFO",
                "directory": "logs",
                "max_file_size_mb": 10,
                "backup_count": 7
            },
            "trading": {
                "default_base_currency": "USD",
                "commission_rate": 0.001,  # 0.1%
                "min_trade_amount": 0.0001,
                "supported_currencies": ["USD", "EUR", "RUB", "BTC", "ETH"]
            },
            "api": {
                "rates_cache_duration_minutes": 5,
                "max_retries": 3,
                "timeout_seconds": 10
            }
        }

        # Пробуем загрузить настройки из файла
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_settings = json.load(f)

                # Рекурсивное обновление настроек
                self._deep_update(default_settings, file_settings)
                self.logger.info(f"Настройки загружены из файла: {config_file}")

            except Exception as e:
                self.logger.warning(f"Ошибка загрузки настроек из файла: {e}. Используются значения по умолчанию.")
        else:
            self.logger.info("Файл конфигурации не найден. Используются значения по умолчанию.")

        return default_settings

    def _deep_update(self, base: Dict, update: Dict) -> None:
        """
        Рекурсивно обновляет словарь.

        Args:
            base: Базовый словарь для обновления.
            update: Словарь с обновлениями.
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение настройки по ключу.

        Args:
            key: Ключ настройки в формате 'section.subsection.key'.
            default: Значение по умолчанию если ключ не найден.

        Returns:
            Any: Значение настройки.
        """
        keys = key.split('.')
        value = self._settings

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            self.logger.debug(f"Настройка '{key}' не найдена. Используется значение по умолчанию: {default}")
            return default

    def get_all(self) -> Dict[str, Any]:
        """
        Возвращает все настройки.

        Returns:
            Dict[str, Any]: Все настройки.
        """
        return self._settings.copy()

    def reload(self) -> None:
        """Перезагружает настройки из файла."""
        self._settings = self._load_settings()
        self.logger.info("Настройки перезагружены")


# Глобальный экземпляр настроек - гарантирует единую точку доступа
settings = SettingsLoader()
