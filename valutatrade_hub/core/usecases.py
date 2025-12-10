import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..decorators import log_action
from ..infra.settings import settings
from ..logging_config import get_logger  # Добавляем импорт логгера
from .currencies import get_currency
from .exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    UserNotAuthenticatedError,
)
from .models import Portfolio, User
from .utils import DataManager, InputValidator

# Создаем логгер для этого модуля
logger = get_logger(__name__)


class UserManager:
    """Менеджер для работы с пользователями."""

    def __init__(self):
        self._current_user: Optional[User] = None
        self._users: List[User] = self._load_users()

    def _load_users(self) -> List[User]:
        """Загружает пользователей из JSON-файла."""
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
        data_dir = settings.get("database.path", "data")
        users_file = settings.get("database.users_file", "users.json")
        file_path = os.path.join(data_dir, users_file)

        users_data = [user.to_dict() for user in self._users]
        return DataManager.save_json(file_path, users_data)

    @log_action(action_name='REGISTER', verbose=True)
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
            # Безопасная операция: чтение → модификация → запись
            user_id = max((user.user_id for user in self._users if user.user_id), default=0) + 1
            new_user = User(username=username, password=password, user_id=user_id)

            self._users.append(new_user)

            if not self._save_users():
                # Откат изменения в памяти
                self._users.remove(new_user)
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

    @log_action(action_name='LOGIN', verbose=True)
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

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Возвращает пользователя по ID."""
        return next((u for u in self._users if u.user_id == user_id), None)


class PortfolioManager:
    """Менеджер для работы с портфелями пользователей."""

    def __init__(self, user_manager: UserManager):
        self._user_manager = user_manager
        self._portfolios: Dict[int, Portfolio] = self._load_portfolios()

    def _load_portfolios(self) -> Dict[int, Portfolio]:
        """Загружает портфели из JSON-файла."""
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
        # Безопасная операция с проверкой существования
        if user_id in self._portfolios:
            return True  # Портфель уже существует

        portfolio = Portfolio(user_id)
        self._portfolios[user_id] = portfolio

        # Сохраняем изменения
        return self._save_portfolios()

    def get_current_portfolio(self) -> Optional[Portfolio]:
        """
        Возвращает портфель текущего пользователя.

        Returns:
            Portfolio или None если пользователь не авторизован.
        """
        if not self._user_manager.is_logged_in:
            raise UserNotAuthenticatedError()

        user_id = self._user_manager.current_user.user_id

        # Если портфеля нет - создаем
        if user_id not in self._portfolios:
            portfolio = Portfolio(user_id)
            self._portfolios[user_id] = portfolio
            self._save_portfolios()

        return self._portfolios[user_id]

    @log_action(action_name='BUY', verbose=True)
    def buy_currency(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        """
        Покупка валюты.

        Args:
            currency_code: Код покупаемой валюты.
            amount: Сумма для покупки.

        Returns:
            Tuple[bool, str]: (успех, сообщение)

        Raises:
            UserNotAuthenticatedError: Если пользователь не авторизован.
            CurrencyNotFoundError: Если валюта не найдена.
            InvalidAmountError: Если сумма некорректна.
            ApiRequestError: Если ошибка при получении курса.
        """
        # Проверка авторизации
        if not self._user_manager.is_logged_in:
            raise UserNotAuthenticatedError()

        # Валидация суммы
        if amount <= 0:
            raise InvalidAmountError(f"Сумма покупки должна быть положительной: {amount}")

        currency_code = currency_code.upper()

        # Валидация валюты через get_currency()
        try:
            get_currency(currency_code)  # Проверяем существование валюты
        except CurrencyNotFoundError as e:
            raise e

        # Проверка минимальной суммы покупки из настроек
        min_trade_amount = settings.get("trading.min_trade_amount", 0.0001)
        if amount < min_trade_amount:
            return False, f"Минимальная сумма покупки: {min_trade_amount}"

        # Получаем портфель
        portfolio = self.get_current_portfolio()
        if not portfolio:
            return False, "Ошибка при получении портфеля"

        # Получаем курс через RateManager (с TTL кешем)
        rate_manager = RateManager()
        success, message, rate, updated_at = rate_manager.get_rate(currency_code, 'USD')

        if not success or rate is None:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→USD: {message}")

        # Рассчитываем стоимость в USD
        cost_usd = amount * rate

        # Применяем комиссию из настроек если есть
        commission_rate = settings.get("trading.commission_rate", 0.0)
        if commission_rate > 0:
            commission = cost_usd * commission_rate
            cost_usd += commission

        try:
            # Безопасная операция: чтение → модификация → запись
            # Проверяем/создаем кошельки
            # USD кошелек (для списания)
            if 'USD' not in portfolio.wallets:
                portfolio.add_currency('USD')

            # Кошелек покупаемой валюты (автосоздание при отсутствии)
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
                # Возвращаем оценочную стоимость
                estimated_cost = amount * rate
                return True, f"Покупка выполнена: {amount:.4f} {currency_code} по курсу {rate:.2f} USD/{currency_code}. Оценочная стоимость: ${estimated_cost:.2f}"
            else:
                # Откат транзакции в случае ошибки сохранения
                usd_wallet.deposit(cost_usd)
                target_wallet.withdraw(amount)
                return False, "Ошибка при сохранении данных"

        except InsufficientFundsError as e:
            raise e
        except Exception as e:
            return False, f"Ошибка при выполнении операции: {str(e)}"

    @log_action(action_name='SELL', verbose=True)
    def sell_currency(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        """
        Продажа валюты.

        Args:
            currency_code: Код продаваемой валюты.
            amount: Сумма для продажи.

        Returns:
            Tuple[bool, str]: (успех, сообщение)

        Raises:
            UserNotAuthenticatedError: Если пользователь не авторизован.
            CurrencyNotFoundError: Если валюта не найдена.
            InvalidAmountError: Если сумма некорректна.
            InsufficientFundsError: Если недостаточно средств.
            ApiRequestError: Если ошибка при получении курса.
        """
        # Проверка авторизации
        if not self._user_manager.is_logged_in:
            raise UserNotAuthenticatedError()

        # Валидация суммы
        if amount <= 0:
            raise InvalidAmountError(f"Сумма продажи должна быть положительной: {amount}")

        currency_code = currency_code.upper()

        # Валидация валюты через get_currency()
        try:
            get_currency(currency_code)  # Проверяем существование валюты
        except CurrencyNotFoundError as e:
            raise e

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

        # Получаем курс через RateManager (с TTL кешем)
        rate_manager = RateManager()
        success, message, rate, updated_at = rate_manager.get_rate(currency_code, 'USD')

        if not success or rate is None:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→USD: {message}")

        # Рассчитываем выручку в USD
        revenue_usd = amount * rate

        # Применяем комиссию из настроек если есть
        commission_rate = settings.get("trading.commission_rate", 0.0)
        if commission_rate > 0:
            commission = revenue_usd * commission_rate
            revenue_usd -= commission

        try:
            # Безопасная операция: чтение → модификация → запись
            # Проверяем/создаем USD кошелек (для зачисления)
            if 'USD' not in portfolio.wallets:
                portfolio.add_currency('USD')

            # Получаем кошельки
            usd_wallet = portfolio.get_wallet('USD')

            # Выполняем транзакцию
            source_wallet.withdraw(amount)
            usd_wallet.deposit(revenue_usd)

            # Сохраняем изменения
            if self._save_portfolios():
                # Возвращаем оценочную выручку
                estimated_revenue = amount * rate
                return True, f"Продажа выполнена: {amount:.4f} {currency_code} по курсу {rate:.2f} USD/{currency_code}. Оценочная выручка: ${estimated_revenue:.2f}"
            else:
                # Откат транзакции в случае ошибки сохранения
                source_wallet.deposit(amount)
                usd_wallet.withdraw(revenue_usd)
                return False, "Ошибка при сохранении данных"

        except InsufficientFundsError as e:
            raise e
        except Exception as e:
            return False, f"Ошибка при выполнении операции: {str(e)}"

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
    """Менеджер для работы с курсами валют с TTL кешем в новом формате."""

    def __init__(self):
        self._rates_data = self._load_rates()
        # Использование TTL из SettingsLoader
        cache_minutes = settings.get("api.rates_cache_duration_minutes", 5)
        self._CACHE_DURATION = timedelta(minutes=cache_minutes)

    def _load_rates(self) -> Dict:
        """Загружает курсы из JSON файла в НОВОМ формате."""
        data_dir = settings.get("database.path", "data")
        rates_file = settings.get("database.rates_file", "rates.json")
        file_path = os.path.join(data_dir, rates_file)

        rates_data = DataManager.load_json(file_path)
        if not rates_data:
            # Если файл пуст, создаем базовую структуру
            rates_data = {
                "pairs": {},
                "last_refresh": None
            }
            DataManager.save_json(file_path, rates_data)

        # Проверяем структуру файла (поддержка старого и нового форматов)
        if "pairs" not in rates_data:
            # Конвертируем старый формат в новый
            converted_data = self._convert_old_format(rates_data)
            if self._save_rates(converted_data):
                rates_data = converted_data

        return rates_data

    def _convert_old_format(self, old_data: Dict) -> Dict:
        """Конвертирует старый формат в новый."""
        new_data = {
            "pairs": {},
            "last_refresh": old_data.get("last_refresh", datetime.now().isoformat() + "Z")
        }

        for key, value in old_data.items():
            if key not in ["source", "last_refresh"]:
                # Это пара валют в старом формате
                new_data["pairs"][key] = {
                    "rate": value.get("rate", 0),
                    "updated_at": value.get("updated_at", datetime.now().isoformat() + "Z"),
                    "source": value.get("source", old_data.get("source", "Unknown"))
                }

        return new_data

    def _save_rates(self, rates_data: Dict) -> bool:
        """Сохраняет курсы в JSON-файл."""
        data_dir = settings.get("database.path", "data")
        rates_file = settings.get("database.rates_file", "rates.json")
        file_path = os.path.join(data_dir, rates_file)

        return DataManager.save_json(file_path, rates_data)

    def _get_rate_from_cache(self, from_currency: str, to_currency: str) -> Tuple[Optional[float], Optional[str]]:
        """Получает курс из кеша в НОВОМ формате."""
        pair_key = f"{from_currency}_{to_currency}"

        if "pairs" in self._rates_data and pair_key in self._rates_data["pairs"]:
            rate_data = self._rates_data["pairs"][pair_key]
            if self._is_rate_fresh(rate_data):
                return rate_data.get("rate"), rate_data.get("updated_at")

        return None, None

    def _is_rate_fresh(self, rate_data: Dict) -> bool:
        """Проверяет свежесть курса по TTL из настроек."""
        if not rate_data or "updated_at" not in rate_data:
            return False

        try:
            updated_str = rate_data["updated_at"]
            
            # Преобразуем время из строки в datetime
            # Удаляем 'Z' и добавляем '+00:00' для парсинга
            if updated_str.endswith('Z'):
                # Формат: 2025-12-10T15:53:26.123040Z
                updated_str = updated_str[:-1]  # Удаляем 'Z'
                if '.' in updated_str:
                    # Есть микросекунды: 2025-12-10T15:53:26.123040
                    updated_str = updated_str.split('.')[0]  # Убираем микросекунды
            
            # Парсим время
            updated_at = datetime.fromisoformat(updated_str)
            age = datetime.now() - updated_at
            
            # Проверяем, что возраст меньше TTL
            return age < self._CACHE_DURATION
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка парсинга времени {rate_data.get('updated_at')}: {e}")
            return False

    def get_rate(self, from_currency: str, to_currency: str = 'USD') -> Tuple[bool, str, Optional[float], Optional[str]]:
        """
        Получает курс между валютами с учетом TTL кеша.

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.

        Returns:
            Tuple[bool, str, Optional[float], Optional[str]]:
            (успех, сообщение, курс, время обновления)

        Raises:
            CurrencyNotFoundError: Если валюта не найдена.
            ApiRequestError: Если не удалось обновить курс.
        """
        # Валидация валют через get_currency()
        try:
            get_currency(from_currency)  # Проверяем исходную валюту
            get_currency(to_currency)    # Проверяем целевую валюту
        except CurrencyNotFoundError as e:
            raise e

        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Пытаемся получить свежий курс из кеша
        rate, updated_at = self._get_rate_from_cache(from_currency, to_currency)

        if rate is not None:
            return True, f"Курс {from_currency}→{to_currency}", rate, updated_at

        # Проверяем, когда было последнее обновление всей базы
        last_refresh = self._rates_data.get("last_refresh")
        if last_refresh:
            try:
                # Парсим время последнего обновления
                refresh_str = last_refresh
                if refresh_str.endswith('Z'):
                    refresh_str = refresh_str[:-1]
                    if '.' in refresh_str:
                        refresh_str = refresh_str.split('.')[0]
                
                last_refresh_time = datetime.fromisoformat(refresh_str)
                time_since_refresh = datetime.now() - last_refresh_time
                
                # Если вся база свежая, но конкретной пары нет - это ошибка данных
                if time_since_refresh < self._CACHE_DURATION:
                    raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен в кеше")
                    
            except (ValueError, TypeError):
                pass  # Если не удалось разобрать время, продолжаем

        # Если кеш устарел или пары нет, обновляем
        logger.info(f"Кеш устарел или пара не найдена, обновление...")
        try:
            success = self.update_rates()
            if not success:
                raise ApiRequestError("Не удалось обновить курсы валют")
        except ApiRequestError as e:
            raise e

        # Пробуем снова после обновления
        rate, updated_at = self._get_rate_from_cache(from_currency, to_currency)

        if rate is not None:
            return True, f"Курс {from_currency}→{to_currency}", rate, updated_at

        # Если курс не найден даже после обновления
        raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен")

    def get_all_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        Возвращает все доступные курсы в новом формате.

        Returns:
            Словарь с курсами валют.
        """
        return self._rates_data.copy()

    def update_rates(self) -> bool:
        """
        Обновляет курсы валют через Parser Service.

        Returns:
            bool: True если успешно, False в противном случае.

        Raises:
            ApiRequestError: Если произошла ошибка при обновлении.
        """
        try:
            # Используем Parser Service для обновления
            from ..parser_service.updater import RatesUpdater

            updater = RatesUpdater()
            result = updater.update_all_rates()

            if result:
                # Принудительно перезагружаем кеш из файла
                return self.reload_rates_cache()
            else:
                raise ApiRequestError("Parser Service не вернул данные")

        except ImportError as e:
            logger.error(f"Ошибка импорта Parser Service: {e}")
            raise ApiRequestError("Parser Service недоступен") from e
        except Exception as e:
            logger.error(f"Ошибка обновления курсов: {e}")
            raise ApiRequestError(f"Ошибка обновления: {str(e)}") from e

    def reload_rates_cache(self) -> bool:
        """
        Принудительно перезагружает кеш курсов из файла.

        Returns:
            bool: True если успешно перезагружено, False в противном случае.
        """
        try:
            old_data = self._rates_data
            self._rates_data = self._load_rates()

            old_count = len(old_data.get("pairs", {}))
            new_count = len(self._rates_data.get("pairs", {}))

            logger.info(f"Кеш курсов перезагружен. Пар было: {old_count}, стало: {new_count}")
            return True
        except Exception as e:
            logger.error(f"Ошибка перезагрузки кеша курсов: {e}")
            return False

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о состоянии кеша.

        Returns:
            Словарь с информацией о кеше.
        """
        pairs_count = len(self._rates_data.get("pairs", {}))
        last_refresh = self._rates_data.get("last_refresh")

        try:
            if last_refresh:
                last_refresh_str = last_refresh.replace('Z', '+00:00')
                last_refresh_time = datetime.fromisoformat(last_refresh_str)
                is_fresh = datetime.now() - last_refresh_time < self._CACHE_DURATION
                time_ago = str(datetime.now() - last_refresh_time)
            else:
                is_fresh = False
                time_ago = "never"
        except (ValueError, TypeError):
            is_fresh = False
            time_ago = "invalid"

        return {
            "pairs_count": pairs_count,
            "last_refresh": last_refresh,
            "is_fresh": is_fresh,
            "time_since_last_refresh": time_ago,
            "cache_duration_minutes": self._CACHE_DURATION.total_seconds() / 60,
            "available_pairs": list(self._rates_data.get("pairs", {}).keys())
        }
