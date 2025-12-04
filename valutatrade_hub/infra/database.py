import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List

from ..logging_config import get_logger
from .settings import settings


class DatabaseManager:
    """Singleton класс для управления JSON-хранилищем."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Инициализирует менеджер базы данных."""
        self.logger = get_logger(__name__)

        # Получаем настройки базы данных
        self.data_dir = settings.get("database.path", "data")
        self.users_file = os.path.join(self.data_dir, settings.get("database.users_file", "users.json"))
        self.portfolios_file = os.path.join(self.data_dir, settings.get("database.portfolios_file", "portfolios.json"))
        self.rates_file = os.path.join(self.data_dir, settings.get("database.rates_file", "rates.json"))

        self.backup_enabled = settings.get("database.backup_enabled", True)
        self.backup_dir = settings.get("database.backup_dir", "backups")

        # Создаем необходимые директории
        os.makedirs(self.data_dir, exist_ok=True)
        if self.backup_enabled:
            os.makedirs(self.backup_dir, exist_ok=True)

        self.logger.info(f"База данных инициализирована. Директория данных: {self.data_dir}")

    def _create_backup(self, file_path: str) -> None:
        """
        Создает резервную копию файла.

        Args:
            file_path: Путь к файлу для резервного копирования.
        """
        if not self.backup_enabled or not os.path.exists(file_path):
            return

        try:
            # Создаем имя файла резервной копии с timestamp
            filename = os.path.basename(file_path)
            backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(self.backup_dir, backup_name)

            shutil.copy2(file_path, backup_path)
            self.logger.debug(f"Создана резервная копия: {backup_path}")

            # Удаляем старые резервные копии (оставляем последние 5)
            self._cleanup_old_backups(filename)

        except Exception as e:
            self.logger.warning(f"Ошибка создания резервной копии: {e}")

    def _cleanup_old_backups(self, base_filename: str) -> None:
        """
        Удаляет старые резервные копии.

        Args:
            base_filename: Базовое имя файла.
        """
        try:
            # Ищем все резервные копии для этого файла
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith(f"{base_filename}.backup_"):
                    file_path = os.path.join(self.backup_dir, file)
                    backups.append((file_path, os.path.getmtime(file_path)))

            # Сортируем по времени создания (старые первыми)
            backups.sort(key=lambda x: x[1])

            # Удаляем старые копии, оставляем последние 5
            for file_path, _ in backups[:-5]:
                os.remove(file_path)
                self.logger.debug(f"Удалена старая резервная копия: {file_path}")

        except Exception as e:
            self.logger.warning(f"Ошибка очистки старых резервных копий: {e}")

    def load_data(self, file_path: str, default: Any = None) -> Any:
        """
        Загружает данные из JSON-файла.

        Args:
            file_path: Путь к JSON-файлу.
            default: Значение по умолчанию если файл не существует.

        Returns:
            Any: Загруженные данные.
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.logger.debug(f"Данные загружены из: {file_path}")
                return data
            else:
                self.logger.debug(f"Файл не найден: {file_path}. Используется значение по умолчанию.")
                return default if default is not None else []

        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON из {file_path}: {e}")
            # Создаем резервную копию поврежденного файла
            corrupted_backup = f"{file_path}.corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(file_path):
                shutil.move(file_path, corrupted_backup)
                self.logger.warning(f"Поврежденный файл перемещен в: {corrupted_backup}")
            return default if default is not None else []

        except Exception as e:
            self.logger.error(f"Ошибка загрузки данных из {file_path}: {e}")
            return default if default is not None else []

    def save_data(self, file_path: str, data: Any) -> bool:
        """
        Сохраняет данные в JSON-файл.

        Args:
            file_path: Путь к JSON-файлу.
            data: Данные для сохранения.

        Returns:
            bool: True если сохранение успешно, False в противном случае.
        """
        try:
            # Создаем резервную копию перед сохранением
            self._create_backup(file_path)

            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Сохраняем данные
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.debug(f"Данные сохранены в: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных в {file_path}: {e}")
            return False

    def load_users(self) -> List[Dict[str, Any]]:
        """
        Загружает данные пользователей.

        Returns:
            List[Dict[str, Any]]: Список пользователей.
        """
        return self.load_data(self.users_file, [])

    def save_users(self, users_data: List[Dict[str, Any]]) -> bool:
        """
        Сохраняет данные пользователей.

        Args:
            users_data: Данные пользователей.

        Returns:
            bool: True если сохранение успешно, False в противном случае.
        """
        return self.save_data(self.users_file, users_data)

    def load_portfolios(self) -> List[Dict[str, Any]]:
        """
        Загружает данные портфелей.

        Returns:
            List[Dict[str, Any]]: Список портфелей.
        """
        return self.load_data(self.portfolios_file, [])

    def save_portfolios(self, portfolios_data: List[Dict[str, Any]]) -> bool:
        """
        Сохраняет данные портфелей.

        Args:
            portfolios_data: Данные портфелей.

        Returns:
            bool: True если сохранение успешно, False в противном случае.
        """
        return self.save_data(self.portfolios_file, portfolios_data)

    def load_rates(self) -> Dict[str, Any]:
        """
        Загружает данные курсов валют.

        Returns:
            Dict[str, Any]: Данные курсов.
        """
        return self.load_data(self.rates_file, {})

    def save_rates(self, rates_data: Dict[str, Any]) -> bool:
        """
        Сохраняет данные курсов валют.

        Args:
            rates_data: Данные курсов.

        Returns:
            bool: True если сохранение успешно, False в противном случае.
        """
        return self.save_data(self.rates_file, rates_data)

    def clear_all_data(self) -> bool:
        """
        Очищает все данные (использовать с осторожностью!).

        Returns:
            bool: True если очистка успешна, False в противном случае.
        """
        try:
            files = [self.users_file, self.portfolios_file, self.rates_file]
            success = True

            for file_path in files:
                if os.path.exists(file_path):
                    # Создаем резервную копию перед удалением
                    self._create_backup(file_path)
                    os.remove(file_path)
                    self.logger.warning(f"Файл удален: {file_path}")

            self.logger.warning("Все данные очищены")
            return success

        except Exception as e:
            self.logger.error(f"Ошибка очистки данных: {e}")
            return False


# Глобальный экземпляр менеджера базы данных
db = DatabaseManager()
