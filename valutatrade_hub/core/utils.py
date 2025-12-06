import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from prettytable import PrettyTable

from .exceptions import ApiRequestError  # Добавляем импорт


class DataManager:
    """Класс для управления JSON-файлами данных."""

    @staticmethod
    def load_json(file_path: str) -> Any:
        """
        Загружает данные из JSON  файла.

        Args:
            file_path: Путь к JSON-файлу.

        Returns:
            Загруженные данные.
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            return []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    @staticmethod
    def save_json(file_path: str, data: Any) -> bool:
        """
        Сохраняет данные в JSON-файл.

        Args:
            file_path: Путь к JSON-файлу.
            data: Данные для сохранения.

        Returns:
            True если сохранение успешно, False в противном случае.
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception:
            return False


class InputValidator:
    """Класс для валидации входных данных."""

    @staticmethod
    def validate_currency_code(currency_code: str) -> bool:
        """
        Проверяет корректность кода валюты.

        Args:
            currency_code: Код валюты.

        Returns:
            True если код корректен, False в противном случае.
        """
        if not currency_code or not isinstance(currency_code, str):
            return False
        return currency_code.strip().isalpha() and len(currency_code.strip()) == 3

    @staticmethod
    def validate_amount(amount: str) -> Optional[float]:
        """
        Проверяет и преобразует сумму.

        Args:
            amount: Строка с суммой.

        Returns:
            float значение суммы или None если невалидно.
        """
        try:
            value = float(amount)
            if value <= 0:
                return None
            return value
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Проверяет корректность имени пользователя.

        Args:
            username: Имя пользователя.

        Returns:
            True если имя корректен, False в противном случае.
        """
        if not username or not isinstance(username, str):
            return False
        username = username.strip()
        return 3 <= len(username) <= 20 and username.isalnum()

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        Проверяет корректность пароля.

        Args:
            password: Пароль.

        Returns:
            True если пароль корректен, False в противном случае.
        """
        if not password or not isinstance(password, str):
            return False
        return len(password.strip()) >= 4


class CurrencyService:
    """Сервис для работы с курсами валют (заглушка пока нет Parser Service)."""

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str = 'USD') -> Optional[float]:
        """
        Получает курс обмена между валютами.

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.

        Returns:
            Курс обмена или None если курс не найден.

        Raises:
            ApiRequestError: Если произошла ошибка при обращении к API (заглушка).
        """
        # Для демонстрации ApiRequestError - с вероятностью 10% имитируем сбой API
        import random
        if random.random() < 0.1:  # 10% chance
            raise ApiRequestError("Временная недоступность сервиса курсов")

        # Фиксированные курсы для тестирования
        fixed_rates = {
            'USD': {'USD': 1.0, 'EUR': 0.92, 'BTC': 0.000025, 'RUB': 95.0},
            'EUR': {'USD': 1.08, 'EUR': 1.0, 'BTC': 0.000027, 'RUB': 102.0},
            'BTC': {'USD': 40000.0, 'EUR': 37000.0, 'BTC': 1.0, 'RUB': 3800000.0},
            'RUB': {'USD': 0.0105, 'EUR': 0.0098, 'BTC': 0.00000026, 'RUB': 1.0},
            'ETH': {'USD': 3720.0, 'BTC': 0.093, 'EUR': 3400.0}
        }

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency in fixed_rates and to_currency in fixed_rates[from_currency]:
            return fixed_rates[from_currency][to_currency]

        # Если нет прямого курса, пытаемся через USD
        if from_currency in fixed_rates and 'USD' in fixed_rates[from_currency]:
            if to_currency in fixed_rates['USD']:
                return fixed_rates[from_currency]['USD'] * fixed_rates['USD'][to_currency]

        return None

    @staticmethod
    def get_all_rates() -> Dict[str, Dict[str, Any]]:
        """
        Возвращает все доступные курсы в формате для rates.json.

        Returns:
            Словарь с курсами валют.

        Raises:
            ApiRequestError: Если произошла ошибка при обращении к API.
        """
        # Для демонстрации ApiRequestError - с вероятностью 10% имитируем сбой API
        import random
        if random.random() < 0.1:  # 10% chance
            raise ApiRequestError("Сервис курсов временно недоступен")

        now = datetime.now().isoformat()

        return {
            "EUR_USD": {
                "rate": 1.0786,
                "updated_at": now
            },
            "BTC_USD": {
                "rate": 59337.21,
                "updated_at": now
            },
            "RUB_USD": {
                "rate": 0.01016,
                "updated_at": now
            },
            "ETH_USD": {
                "rate": 3720.00,
                "updated_at": now
            },
            "source": "MockService",
            "last_refresh": now
        }


def format_portfolio_table(portfolio_data: Dict[str, float], total_value: float) -> str:
    """
    Форматирует данные портфеля в таблицу.

    Args:
        portfolio_data: Данные портфеля {валюта: баланс}.
        total_value: Общая стоимость портфеля.

    Returns:
        Отформатированная таблица.
    """
    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", "Курс к USD", "Стоимость в USD"]
    table.align["Валюта"] = "l"
    table.align["Баланс"] = "r"
    table.align["Курс к USD"] = "r"
    table.align["Стоимость в USD"] = "r"

    service = CurrencyService()

    for currency, balance in portfolio_data.items():
        rate = service.get_exchange_rate(currency, 'USD') or 0
        value_usd = balance * rate if rate else 0
        table.add_row([
            currency,
            f"{balance:.4f}",
            f"{rate:.6f}" if rate < 1 else f"{rate:.2f}",
            f"{value_usd:.2f}"
        ])

    return str(table) + f"\nОбщая стоимость: ${total_value:.2f}"


def format_rates_table(rates_data: Dict[str, Dict[str, Any]]) -> str:
    """
    Форматирует данные о курсах в таблицу.

    Args:
        rates_data: Данные о курсах.

    Returns:
        Отформатированная таблица.
    """
    table = PrettyTable()
    table.field_names = ["Пара", "Курс", "Обновлено"]
    table.align["Пара"] = "l"
    table.align["Курс"] = "r"
    table.align["Обновлено"] = "l"

    for pair, data in rates_data.items():
        if pair not in ["source", "last_refresh"]:
            updated_at = data.get("updated_at", "N/A")
            # Обрезаем время до часа:минуты
            if "T" in updated_at:
                updated_at = updated_at.split("T")[1][:5]
            table.add_row([
                pair,
                f"{data['rate']:.6f}" if data['rate'] < 1 else f"{data['rate']:.2f}",
                updated_at
            ])

    return str(table)
