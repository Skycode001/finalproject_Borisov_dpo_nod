import os
from typing import Any, Dict, List, Optional, Tuple

from .models import Portfolio, User
from .utils import CurrencyService, DataManager, InputValidator

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PORTFOLIOS_FILE = os.path.join(DATA_DIR, "portfolios.json")
RATES_FILE = os.path.join(DATA_DIR, "rates.json")


class UserManager:
    """Менеджер для работы с пользователями."""

    def __init__(self):
        self._current_user: Optional[User] = None
        self._users: List[User] = self._load_users()

    def _load_users(self) -> List[User]:
        """Загружает пользователей из JSON-файла."""
        users_data = DataManager.load_json(USERS_FILE)
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
        users_data = [user.to_dict() for user in self._users]
        return DataManager.save_json(USERS_FILE, users_data)

    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Регистрирует нового пользователя.

        Args:
            username: Имя пользователя.
            password: Пароль.

        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Валидация
        if not InputValidator.validate_username(username):
            return False, "Имя пользователя должно содержать 3-20 буквенно-цифровых символов"

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
            return False, "Пользователь не найден"

        # Проверка пароля
        if user.verify_password(password):
            self._current_user = user
            return True, f"Добро пожаловать, {username}!"
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
        portfolios_data = DataManager.load_json(PORTFOLIOS_FILE)
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
        portfolios_data = [portfolio.to_dict() for portfolio in self._portfolios.values()]
        return DataManager.save_json(PORTFOLIOS_FILE, portfolios_data)

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
            return False, "Сумма должна быть положительным числом"

        currency_code = currency_code.upper()
        amount = validated_amount

        # Получаем портфель
        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Ошибка при получении портфеля"

        # Получаем курс
        service = CurrencyService()
        rate = service.get_exchange_rate(currency_code, 'USD')
        if not rate:
            return False, f"Курс для {currency_code} не найден"

        # Рассчитываем стоимость в USD
        cost_usd = amount * rate

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
            if not usd_wallet.withdraw(cost_usd):
                return False, "Ошибка при списании USD"

            target_wallet.deposit(amount)

            # Сохраняем изменения
            if self._save_portfolios():
                return True, (f"Успешно куплено {amount:.4f} {currency_code} "
                              f"за ${cost_usd:.2f} по курсу {rate:.6f}")
            else:
                return False, "Ошибка при сохранении данных"

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
            return False, "Сумма должна быть положительным числом"

        currency_code = currency_code.upper()
        amount = validated_amount

        # Получаем портфель
        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Ошибка при получении портфеля"

        # Проверяем наличие кошелька
        if currency_code not in portfolio.wallets:
            return False, f"У вас нет валюты {currency_code}"

        # Получаем курс
        service = CurrencyService()
        rate = service.get_exchange_rate(currency_code, 'USD')
        if not rate:
            return False, f"Курс для {currency_code} не найден"

        # Рассчитываем выручку в USD
        revenue_usd = amount * rate

        try:
            # Проверяем/создаем USD кошелек (для зачисления)
            if 'USD' not in portfolio.wallets:
                portfolio.add_currency('USD')

            # Получаем кошельки
            source_wallet = portfolio.get_wallet(currency_code)
            usd_wallet = portfolio.get_wallet('USD')

            # Проверяем достаточно ли валюты для продажи
            if source_wallet.balance < amount:
                return False, (f"Недостаточно {currency_code} для продажи. "
                               f"Нужно: {amount:.4f}, доступно: {source_wallet.balance:.4f}")

            # Выполняем транзакцию
            if not source_wallet.withdraw(amount):
                return False, f"Ошибка при списании {currency_code}"

            usd_wallet.deposit(revenue_usd)

            # Сохраняем изменения
            if self._save_portfolios():
                return True, (f"Успешно продано {amount:.4f} {currency_code} "
                              f"за ${revenue_usd:.2f} по курсу {rate:.6f}")
            else:
                return False, "Ошибка при сохранении данных"

        except ValueError as e:
            return False, str(e)

    def show_portfolio(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        Показывает портфель текущего пользователя.

        Returns:
            Tuple[bool, str, Optional[Dict]]: (успех, сообщение, данные портфеля)
        """
        if not self._user_manager.is_logged_in:
            return False, "Требуется авторизация", None

        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Портфель не найден", None

        # Получаем данные портфеля
        portfolio_data = {}
        total_value = portfolio.get_total_value('USD')

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

    def _load_rates(self) -> Dict:
        """Загружает курсы из JSON-файла."""
        rates_data = DataManager.load_json(RATES_FILE)
        if not rates_data:
            # Если файл пуст, создаем заглушку
            rates_data = CurrencyService.get_all_rates()
            DataManager.save_json(RATES_FILE, rates_data)
        return rates_data

    def _save_rates(self) -> bool:
        """Сохраняет курсы в JSON-файл."""
        return DataManager.save_json(RATES_FILE, self._rates_data)

    def get_rate(self, from_currency: str, to_currency: str = 'USD') -> Tuple[bool, str, Optional[float]]:
        """
        Получает курс между валютами.

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.

        Returns:
            Tuple[bool, str, Optional[float]]: (успех, сообщение, курс)
        """
        # Валидация
        if not InputValidator.validate_currency_code(from_currency):
            return False, "Неверный код исходной валюты", None

        if not InputValidator.validate_currency_code(to_currency):
            return False, "Неверный код целевой валюты", None

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Получаем курс
        service = CurrencyService()
        rate = service.get_exchange_rate(from_currency, to_currency)

        if rate:
            return True, f"Курс {from_currency}/{to_currency}", rate
        else:
            return False, f"Курс {from_currency}/{to_currency} не найден", None

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
        except Exception as e:
            return False, f"Ошибка при обновлении курсов: {str(e)}"
