import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import ApiRequestError, InsufficientFundsError
from ..infra.settings import settings   # Импорт синглтона настроек
from .models import Portfolio, User
from .utils import CurrencyService, DataManager, InputValidator


class UserManager:
    """Менеджер для работы с пользователями."""

    def __init__(self):
        self._current_user: Optional[User] = None
        self._users: List[User] = self._load_users()

    def _load_users(self) -> List[User]:
        """Загружает пользователей из JSON-файла."""
        # Использование настроек для получения пути к файлу
        data_dir = settings.get("database.path", "data")
        users_file = settings.get("database.users_file", "users.json")
        file_path = os.path.join(data_dir, users_file)

        users_data = DataManager.load_json(file_path)
        users = []
        for user_data in users_data:
            try:
                user = User.from_dict(user_data)
                users.append(user)
            except Exception:
                continue
        return users

    def _save_users(self) -> bool:
        """Сохраняет пользователей в JSON-файл."""
        # Использование настроек для получения пути к файлу
        data_dir = settings.get("database.path", "data")
        users_file = settings.get("database.users_file", "users.json")
        file_path = os.path.join(data_dir, users_file)

        users_data = [user.to_dict() for user in self._users]
        return DataManager.save_json(file_path, users_data)

    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Регистрирует нового пользователя.

        Args:
            username: Имя пользователя.
            password: Пароль.

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Валидация с использованием настроек
        min_username_length = 3  # Можно вынести в настройки
        max_username_length = 20  # Можно вынести в настройки

        if not InputValidator.validate_username(username):
            return False, f"Имя пользователя должно содержать {min_username_length}-{max_username_length} буквенно-цифровых символов"

        if not InputValidator.validate_password(password):
            return False, "Пароль должен быть не короче 4 символов"

        # Проверка уникальности
        if any(user.username == username for user in self._users):
            return False, f"Имя пользователя '{username}' уже занято"

        try:
            # Создание нового пользователя
            user_id = max((user.user_id for user in self._users if user.user_id), default=0) + 1
            new_user = User(username=username, password=password, user_id=user_id)

            # Добавление и сохранение пользователя
            self._users.append(new_user)
            if not self._save_users():
                return False, "Ошибка при сохранении данных пользователя"

            # Создаем пустой портфель для нового пользователя
            portfolio_manager = PortfolioManager(self)
            if not portfolio_manager.create_portfolio_for_user(user_id):
                # Откатываем создание пользователя, если не удалось создать портфель
                self._users.remove(new_user)
                self._save_users()
                return False, "Ошибка при создании портфеля"

            return True, f"Пользователь '{username}' зарегистрирован (id={user_id}). Войдите: login --username {username} --password ****"
        except ValueError as e:
            return False, str(e)

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Выполняет вход пользователя.

        Args:
            username: Имя пользователя.
            password: Пароль.

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Поиск пользователя
        user = next((u for u in self._users if u.username == username), None)

        if not user:
            return False, f"Пользователь '{username}' не найден"

        # Проверка пароля
        if user.verify_password(password):
            self._current_user = user
            return True, f"Вы вошли как '{username}'"
        else:
            return False, "Неверный пароль"

    def logout(self) -> Tuple[bool, str]:
        """Выход текущего пользователя."""
        if self._current_user:
            username = self._current_user.username
            self._current_user = None
            return True, f"Пользователь '{username}' вышел из системы"
        return False, "Нет активного пользователя"

    @property
    def current_user(self) -> Optional[User]:
        """Возвращает текущего пользователя."""
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        """Проверяет, выполнен ли вход."""
        return self._current_user is not None


class PortfolioManager:
    """Менеджер для работы с портфелями пользователей."""

    def __init__(self, user_manager: UserManager):
        self._user_manager = user_manager
        self._portfolios: Dict[int, Portfolio] = self._load_portfolios()

    def _load_portfolios(self) -> Dict[int, Portfolio]:
        """Загружает портфели из JSON-файла."""
        # Использование настроек для получения пути к файлу
        data_dir = settings.get("database.path", "data")
        portfolios_file = settings.get("database.portfolios_file", "portfolios.json")
        file_path = os.path.join(data_dir, portfolios_file)

        portfolios_data = DataManager.load_json(file_path)
        portfolios = {}

        for portfolio_data in portfolios_data:
            try:
                portfolio = Portfolio.from_dict(portfolio_data)
                portfolios[portfolio.user_id] = portfolio
            except Exception:
                continue

        return portfolios

    def _save_portfolios(self) -> bool:
        """Сохраняет портфели в JSON-файл."""
        # Использование настроек для получения пути к файлу
        data_dir = settings.get("database.path", "data")
        portfolios_file = settings.get("database.portfolios_file", "portfolios.json")
        file_path = os.path.join(data_dir, portfolios_file)

        portfolios_data = [portfolio.to_dict() for portfolio in self._portfolios.values()]
        return DataManager.save_json(file_path, portfolios_data)

    def create_portfolio_for_user(self, user_id: int) -> bool:
        """
        Создает пустой портфель для пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            bool: True если успешно создан, False в противном случае.
        """
        if user_id in self._portfolios:
            return True  # Портфель уже существует

        portfolio = Portfolio(user_id)
        self._portfolios[user_id] = portfolio
        return self._save_portfolios()

    def get_current_portfolio(self) -> Optional[Portfolio]:
        """
        Возвращает портфель текущего пользователя.

        Returns:
            Portfolio или None если пользователь не авторизован.
        """
        if not self._user_manager.is_logged_in:
            return None

        user_id = self._user_manager.current_user.user_id

        # Если портфеля нет - создаем (для уже существующих пользователей)
        if user_id not in self._portfolios:
            portfolio = Portfolio(user_id)
            self._portfolios[user_id] = portfolio
            self._save_portfolios()

        return self._portfolios[user_id]

    def buy_currency(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        """
        Покупка валюты.

        Args:
            currency_code: Код покупаемой валюты.
            amount: Сумма для покупки.

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Проверка авторизации
        if not self._user_manager.is_logged_in:
            return False, "Требуется авторизация"

        # Валидация
        if not InputValidator.validate_currency_code(currency_code):
            return False, "Неверный код валюты"

        validated_amount = InputValidator.validate_amount(str(amount))
        if validated_amount is None:
            return False, "'amount' должен быть положительным числом"

        currency_code = currency_code.upper()
        amount = validated_amount

        # Проверка минимальной суммы покупки из настроек
        min_trade_amount = settings.get("trading.min_trade_amount", 0.0001)
        if amount < min_trade_amount:
            return False, f"Минимальная сумма покупки: {min_trade_amount}"

        # Получаем портфель
        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Ошибка при получении портфеля"

        # Получаем курс
        service = CurrencyService()
        try:
            rate = service.get_exchange_rate(currency_code, 'USD')
        except ApiRequestError:
            return False, f"Ошибка при получении курса для {currency_code}→USD"

        if not rate:
            return False, f"Не удалось получить курс для {currency_code}→USD"

        # Рассчитываем стоимость в USD
        cost_usd = amount * rate

        # Применяем комиссию из настроек если есть
        commission_rate = settings.get("trading.commission_rate", 0.0)
        if commission_rate > 0:
            commission = cost_usd * commission_rate
            cost_usd += commission

        try:
            # Проверяем/создаем кошельки
            # USD кошелек (для списания)
            if 'USD' not in portfolio.wallets:
                portfolio.add_currency('USD')

            # Кошелек покупаемой валюты
            if currency_code not in portfolio.wallets:
                portfolio.add_currency(currency_code)

            # Получаем кошельки
            usd_wallet = portfolio.get_wallet('USD')
            target_wallet = portfolio.get_wallet(currency_code)

            # Проверяем достаточно ли средств в USD
            if usd_wallet.balance < cost_usd:
                return False, f"Недостаточно средств. Нужно: ${cost_usd:.2f}, доступно: ${usd_wallet.balance:.2f}"

            # Выполняем транзакцию
            usd_wallet.withdraw(cost_usd)
            target_wallet.deposit(amount)

            # Сохраняем изменения
            if self._save_portfolios():
                return True, f"Успешно куплено {amount:.4f} {currency_code}"
            else:
                return False, "Ошибка при сохранении данных"

        except InsufficientFundsError as e:
            # Перебрасываем исключение дальше для обработки в CLI
            raise e
        except ValueError as e:
            return False, str(e)

    def sell_currency(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        """
        Продажа валюты.

        Args:
            currency_code: Код продаваемой валюты.
            amount: Сумма для продажи.

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Проверка авторизации
        if not self._user_manager.is_logged_in:
            return False, "Требуется авторизация"

        # Валидация
        if not InputValidator.validate_currency_code(currency_code):
            return False, "Неверный код валюты"

        validated_amount = InputValidator.validate_amount(str(amount))
        if validated_amount is None:
            return False, "'amount' должен быть положительным числом"

        currency_code = currency_code.upper()
        amount = validated_amount

        # Проверка минимальной суммы продажи из настроек
        min_trade_amount = settings.get("trading.min_trade_amount", 0.0001)
        if amount < min_trade_amount:
            return False, f"Минимальная сумма продажи: {min_trade_amount}"

        # Получаем портфель
        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Ошибка при получении портфеля"

        # Проверяем наличие кошелька
        if currency_code not in portfolio.wallets:
            return False, f"У вас нет кошелька '{currency_code}'. Добавьте валюту: она создаётся автоматически при первой покупке."

        # Получаем текущий баланс до продажи
        try:
            source_wallet = portfolio.get_wallet(currency_code)
            current_balance = source_wallet.balance
        except ValueError:
            return False, f"Кошелёк с валютой '{currency_code}' не найден"

        # Проверяем достаточно ли валюты для продажи
        if current_balance < amount:
            raise InsufficientFundsError(current_balance, amount, currency_code)

        # Получаем курс
        service = CurrencyService()
        try:
            rate = service.get_exchange_rate(currency_code, 'USD')
        except ApiRequestError:
            return False, f"Ошибка при получении курса для {currency_code}→USD"

        if not rate:
            return False, f"Не удалось получить курс для {currency_code}→USD"

        # Рассчитываем выручку в USD
        revenue_usd = amount * rate

        # Применяем комиссию из настроек если есть
        commission_rate = settings.get("trading.commission_rate", 0.0)
        if commission_rate > 0:
            commission = revenue_usd * commission_rate
            revenue_usd -= commission

        try:
            # Проверяем/создаем USD кошелек (для зачисления)
            if 'USD' not in portfolio.wallets:
                portfolio.add_currency('USD')

            # Получаем кошельки
            usd_wallet = portfolio.get_wallet('USD')

            # Выполняем транзакцию
            source_wallet.withdraw(amount)  # Может выбросить InsufficientFundsError
            usd_wallet.deposit(revenue_usd)

            # Сохраняем изменения
            if self._save_portfolios():
                return True, f"Успешно продано {amount:.4f} {currency_code}"
            else:
                return False, "Ошибка при сохранении данных"

        except InsufficientFundsError as e:
            # Перебрасываем исключение дальше для обработки в CLI
            raise e
        except ValueError as e:
            return False, str(e)

    def show_portfolio(self, base_currency: str = 'USD') -> Tuple[bool, str, Optional[Dict]]:
        """
        Показывает портфель текущего пользователя.

        Args:
            base_currency: Базовая валюта для расчета стоимости.

        Returns:
            Tuple[bool, str, Optional[Dict]]: (успех, сообщение, данные портфеля)
        """
        if not self._user_manager.is_logged_in:
            return False, "Сначала выполните login", None

        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Портфель не найден", None

        # Используем базовую валюту из настроек если не указана
        if not base_currency or base_currency == 'USD':
            base_currency = settings.get("trading.default_base_currency", "USD")

        # Проверяем, есть ли кошельки
        if not portfolio.wallets:
            return True, "Портфель пуст", {"data": {}, "total_value": 0.0}

        # Получаем данные портфеля
        portfolio_data = {}
        total_value = portfolio.get_total_value(base_currency)

        for currency_code, wallet in portfolio.wallets.items():
            portfolio_data[currency_code] = wallet.balance

        return True, "Портфель загружен", {
            "data": portfolio_data,
            "total_value": total_value
        }

    def get_wallet_balance(self, currency_code: str) -> Optional[float]:
        """
        Возвращает баланс кошелька текущего пользователя.

        Args:
            currency_code: Код валюты.

        Returns:
            Баланс или None если кошелек не найден.
        """
        if not self._user_manager.is_logged_in:
            return None

        portfolio = self.get_current_portfolio()
        if not portfolio or currency_code not in portfolio.wallets:
            return None

        return portfolio.get_wallet(currency_code).balance


class RateManager:
    """Менеджер для работы с курсами валют."""

    def __init__(self):
        self._rates_data = self._load_rates()
        # Использование настроек для TTL кеша курсов
        cache_minutes = settings.get("api.rates_cache_duration_minutes", 5)
        self._CACHE_DURATION = timedelta(minutes=cache_minutes)

        # Настройки API из конфигурации
        self._max_retries = settings.get("api.max_retries", 3)
        self._timeout_seconds = settings.get("api.timeout_seconds", 10)

    def _load_rates(self) -> Dict:
        """Загружает курсы из JSON-файла."""
        # Использование настроек для получения пути к файлу
        data_dir = settings.get("database.path", "data")
        rates_file = settings.get("database.rates_file", "rates.json")
        file_path = os.path.join(data_dir, rates_file)

        rates_data = DataManager.load_json(file_path)
        if not rates_data:
            # Если файл пуст, создаем заглушку
            try:
                rates_data = CurrencyService.get_all_rates()
                DataManager.save_json(file_path, rates_data)
            except ApiRequestError:
                # Если API недоступно, используем пустые данные
                rates_data = {}
        return rates_data

    def _save_rates(self) -> bool:
        """Сохраняет курсы в JSON-файл."""
        # Использование настроек для получения пути к файлу
        data_dir = settings.get("database.path", "data")
        rates_file = settings.get("database.rates_file", "rates.json")
        file_path = os.path.join(data_dir, rates_file)

        return DataManager.save_json(file_path, self._rates_data)

    def _is_rate_fresh(self, rate_data: Dict) -> bool:
        """Проверяет свежесть курса."""
        if not rate_data or "updated_at" not in rate_data:
            return False

        try:
            updated_at = datetime.fromisoformat(rate_data["updated_at"])
            return datetime.now() - updated_at < self._CACHE_DURATION
        except (ValueError, TypeError):
            return False

    def _get_rate_from_cache(self, from_currency: str, to_currency: str) -> Tuple[Optional[float], Optional[str]]:
        """Получает курс из кеша."""
        # Формируем ключ в формате EUR_USD
        pair_key = f"{from_currency}_{to_currency}"

        if pair_key in self._rates_data:
            rate_data = self._rates_data[pair_key]
            if self._is_rate_fresh(rate_data):
                return rate_data.get("rate"), rate_data.get("updated_at")

        return None, None

    def get_rate(self, from_currency: str, to_currency: str = 'USD') -> Tuple[bool, str, Optional[float], Optional[str]]:
        """
        Получает курс между валютами.

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.

        Returns:
            Tuple[bool, str, Optional[float], Optional[str]]: (успех, сообщение, курс, время обновления)
        """
        # Валидация
        if not InputValidator.validate_currency_code(from_currency):
            return False, f"Неверный код исходной валюты '{from_currency}'", None, None

        if not InputValidator.validate_currency_code(to_currency):
            return False, f"Неверный код целевой валюты '{to_currency}'", None, None

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Пытаемся получить свежий курс из кеша
        rate, updated_at = self._get_rate_from_cache(from_currency, to_currency)

        if rate is not None:
            return True, f"Курс {from_currency}→{to_currency}", rate, updated_at

        # Если курс устарел или отсутствует, обновляем
        success, message = self.update_rates()
        if not success:
            return False, f"Курс {from_currency}→{to_currency} недоступен. Повторите попытку позже.", None, None

        # Пробуем снова после обновления
        rate, updated_at = self._get_rate_from_cache(from_currency, to_currency)

        if rate is not None:
            return True, f"Курс {from_currency}→{to_currency}", rate, updated_at

        # Если курс не найден даже после обновления
        return False, f"Курс {from_currency}→{to_currency} недоступен. Повторите попытку позже.", None, None

    def get_all_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        Возвращает все доступные курсы.

        Returns:
            Словарь с курсами валют.
        """
        return self._rates_data.copy()

    def update_rates(self) -> Tuple[bool, str]:
        """
        Обновляет курсы валют.

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        try:
            self._rates_data = CurrencyService.get_all_rates()
            if self._save_rates():
                return True, "Курсы успешно обновлены"
            else:
                return False, "Ошибка при сохранении курсов"
        except ApiRequestError as e:
            return False, f"Ошибка при обновлении курсов: {str(e)}"
        except Exception as e:
            return False, f"Неожиданная ошибка при обновлении курсов: {str(e)}"
