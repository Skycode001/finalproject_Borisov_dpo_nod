import cmd
import shlex
from datetime import datetime

from prettytable import PrettyTable

from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ValutaTradeError,
)
from ..core.usecases import PortfolioManager, RateManager, UserManager
from ..core.utils import CurrencyService, InputValidator


class TradingCLI(cmd.Cmd):
    """Командный интерфейс торговой платформы."""

    intro = "Добро пожаловать в ValutaTrade Hub! Введите 'help' для списка команд\n"
    prompt = "> "

    def __init__(self):
        super().__init__()
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
        self.rate_manager = RateManager()

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====

    def _handle_exception(self, e: Exception) -> None:
        """Обрабатывает исключения и выводит соответствующие сообщения."""
        if isinstance(e, InsufficientFundsError):
            # Печатаем текст ошибки как есть
            print(f"❌ {str(e)}")

        elif isinstance(e, CurrencyNotFoundError):
            # Показываем сообщение и предлагаем помощь
            print(f"❌ {str(e)}")
            print("   Для просмотра списка поддерживаемых валют используйте команду:")
            print("   get-rate --from USD --to <валюта>")
            print("   или проверьте правильность написания кода валюты.")

        elif isinstance(e, ApiRequestError):
            # Предлагаем повторить позже / проверить сеть
            print(f"❌ {str(e)}")
            print("   Пожалуйста, повторите попытку позже.")
            print("   Проверьте подключение к сети и доступность сервиса.")

        elif isinstance(e, ValutaTradeError):
            # Для других пользовательских исключений
            print(f"❌ {str(e)}")

        else:
            # Для неожиданных исключений
            print(f"❌ Непредвиденная ошибка: {type(e).__name__}: {str(e)}")
            print("   Пожалуйста, сообщите об этом разработчику.")

    # ===== ОБЯЗАТЕЛЬНЫЕ КОМАНДЫ =====

    def do_register(self, arg: str) -> None:
        """
        Регистрация нового пользователя.
        Использование: register --username <username> --password <password>
        Пример: register --username alice --password 1234
        """
        args = shlex.split(arg)

        # Парсим аргументы
        username = None
        password = None

        i = 0
        while i < len(args):
            if args[i] == "--username" and i + 1 < len(args):
                username = args[i + 1]
                i += 2
            elif args[i] == "--password" and i + 1 < len(args):
                password = args[i + 1]
                i += 2
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: register --username <username> --password <password>")
                print("Пример: register --username alice --password 1234")
                return

        # Проверяем обязательные аргументы
        if not username or not password:
            print("❌ Ошибка: требуются оба аргумента --username и --password")
            print("Использование: register --username <username> --password <password>")
            return

        # Выполняем регистрацию
        success, message = self.user_manager.register(username, password)

        if success:
            print(f"✅ {message}")
            print(f"   Войдите: login --username {username} --password ****")
        else:
            print(f"❌ {message}")

    def do_login(self, arg: str) -> None:
        """
        Вход в систему.
        Использование: login --username <username> --password <password>
        Пример: login --username alice --password 1234
        """
        args = shlex.split(arg)

        # Парсим аргументы
        username = None
        password = None

        i = 0
        while i < len(args):
            if args[i] == "--username" and i + 1 < len(args):
                username = args[i + 1]
                i += 2
            elif args[i] == "--password" and i + 1 < len(args):
                password = args[i + 1]
                i += 2
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: login --username <username> --password <password>")
                print("Пример: login --username alice --password 1234")
                return

        # Проверяем обязательные аргументы
        if not username or not password:
            print("❌ Ошибка: требуются оба аргумента --username и --password")
            print("Использование: login --username <username> --password <password>")
            return

        # Выполняем вход
        success, message = self.user_manager.login(username, password)

        if success:
            print(f"✅ Вы вошли как '{username}'")
            self.prompt = f"{username}> "
        else:
            print(f"❌ {message}")

    def do_showportfolio(self, arg: str) -> None:
        """
        Показать портфель текущего пользователя.
        Использование: showportfolio [--base <currency_code>]
        Пример: showportfolio
        Пример: showportfolio --base EUR
        """
        # Парсим аргументы
        base_currency = 'USD'  # значение по умолчанию
        args = shlex.split(arg)

        i = 0
        while i < len(args):
            if args[i] == "--base" and i + 1 < len(args):
                base_currency = args[i + 1].upper()
                i += 2
            else:
                # Если есть аргументы, но не --base, это ошибка
                if args:
                    print("❌ Ошибка: неверный формат команды")
                    print("Использование: showportfolio [--base <currency_code>]")
                    print("Пример: showportfolio")
                    print("Пример: showportfolio --base EUR")
                    return

        # Проверяем, что валюта валидна
        if not InputValidator.validate_currency_code(base_currency):
            print(f"❌ Ошибка: неизвестная базовая валюта '{base_currency}'")
            return

        # Получаем данные портфеля
        success, message, portfolio_data = self.portfolio_manager.show_portfolio(base_currency)

        if not success:
            print(f"❌ {message}")
            return

        if not portfolio_data:
            print("❌ Портфель не найден")
            return

        # Получаем информацию о текущем пользователе
        if not self.user_manager.is_logged_in:
            print("❌ Ошибка: сначала выполните login")
            return

        username = self.user_manager.current_user.username

        # Проверяем, есть ли данные в портфеле
        if not portfolio_data["data"]:
            print(f"Портфель пользователя '{username}' пуст")
            return

        # Форматируем вывод
        print(f"\nПортфель пользователя '{username}' (база: {base_currency}):")

        total_value = portfolio_data["total_value"]
        service = CurrencyService()

        for currency, balance in portfolio_data["data"].items():
            # Получаем курс конвертации
            if currency == base_currency:
                converted = balance
            else:
                rate = service.get_exchange_rate(currency, base_currency)
                if not rate:
                    print(f"❌ Ошибка: курс для {currency}/{base_currency} не найден")
                    return
                converted = balance * rate

            # Форматируем вывод для каждой валюты
            print(f"- {currency}: {balance:,.4f}  → {converted:,.2f} {base_currency}")

        print(f"{'-'*40}")
        print(f"ИТОГО: {total_value:,.2f} {base_currency}")

    def do_buy(self, arg: str) -> None:
        """
        Купить валюту.
        Использование: buy --currency <currency_code> --amount <amount>
        Пример: buy --currency BTC --amount 0.05

        Ошибки:
        - CurrencyNotFoundError: "Неизвестная валюта '{code}'"
        - ApiRequestError: "Ошибка при обращении к внешнему API: {reason}"
        """
        # Проверка авторизации
        if not self.user_manager.is_logged_in:
            print("❌ Ошибка: требуется авторизация. Используйте команду login")
            return

        args = shlex.split(arg)

        # Парсим аргументы
        currency_code = None
        amount = None

        i = 0
        while i < len(args):
            if args[i] == "--currency" and i + 1 < len(args):
                currency_code = args[i + 1].upper()
                i += 2
            elif args[i] == "--amount" and i + 1 < len(args):
                try:
                    amount = float(args[i + 1])
                    i += 2
                except ValueError:
                    print("❌ Ошибка: 'amount' должен быть положительным числом")
                    return
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: buy --currency <currency_code> --amount <amount>")
                print("Пример: buy --currency BTC --amount 0.05")
                return

        # Проверяем обязательные аргументы
        if not currency_code or amount is None:
            print("❌ Ошибка: требуются оба аргумента --currency и --amount")
            print("Использование: buy --currency <currency_code> --amount <amount>")
            print("Пример: buy --currency BTC --amount 0.05")
            return

        # Валидация валюты
        if not currency_code or len(currency_code.strip()) < 2:
            print("❌ Ошибка: код валюты должен содержать минимум 2 символа")
            return

        # Валидация суммы
        if amount <= 0:
            print("❌ Ошибка: 'amount' должен быть положительным числом")
            return

        try:
            # Проверяем существование валюты (может выбросить CurrencyNotFoundError)
            try:
                from ..core.currencies import get_currency
                get_currency(currency_code)
            except CurrencyNotFoundError as e:
                self._handle_exception(e)
                return

            # Получаем текущий курс (может выбросить ApiRequestError)
            service = CurrencyService()
            rate = service.get_exchange_rate(currency_code, 'USD')

            if not rate:
                print(f"❌ Ошибка: не удалось получить курс для {currency_code}→USD")
                return

            # Рассчитываем стоимость покупки
            cost_usd = amount * rate

            # Получаем текущий баланс до покупки
            current_balance = self.portfolio_manager.get_wallet_balance(currency_code)
            if current_balance is None:
                current_balance = 0.0

            # Выполняем покупку
            success, message = self.portfolio_manager.buy_currency(currency_code, amount)

            if success:
                # Получаем новый баланс после покупки
                new_balance = self.portfolio_manager.get_wallet_balance(currency_code)
                if new_balance is None:
                    new_balance = current_balance + amount

                print(f"✅ Покупка выполнена: {amount:.4f} {currency_code} по курсу {rate:.2f} USD/{currency_code}")
                print("   Изменения в портфеле:")
                print(f"   - {currency_code}: было {current_balance:.4f} → стало {new_balance:.4f}")
                print(f"   Оценочная стоимость покупки: {cost_usd:,.2f} USD")
            else:
                print(f"❌ {message}")

        except ApiRequestError as e:
            self._handle_exception(e)
        except Exception as e:
            print(f"❌ Непредвиденная ошибка: {e}")

    def do_sell(self, arg: str) -> None:
        """
        Продать валюту.
        Использование: sell --currency <currency_code> --amount <amount>
        Пример: sell --currency BTC --amount 0.01

        Ошибки:
        - InsufficientFundsError: "Недостаточно средств: доступно X.XXXX {code}, требуется X.XXXX {code}"
        """
        # Проверка авторизации
        if not self.user_manager.is_logged_in:
            print("❌ Ошибка: требуется авторизация. Используйте команду login")
            return

        args = shlex.split(arg)

        # Парсим аргументы
        currency_code = None
        amount = None

        i = 0
        while i < len(args):
            if args[i] == "--currency" and i + 1 < len(args):
                currency_code = args[i + 1].upper()
                i += 2
            elif args[i] == "--amount" and i + 1 < len(args):
                try:
                    amount = float(args[i + 1])
                    i += 2
                except ValueError:
                    print("❌ Ошибка: 'amount' должен быть положительным числом")
                    return
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: sell --currency <currency_code> --amount <amount>")
                print("Пример: sell --currency BTC --amount 0.01")
                return

        # Проверяем обязательные аргументы
        if not currency_code or amount is None:
            print("❌ Ошибка: требуются оба аргумента --currency и --amount")
            print("Использование: sell --currency <currency_code> --amount <amount>")
            print("Пример: sell --currency BTC --amount 0.01")
            return

        # Валидация валюты
        if not currency_code or len(currency_code.strip()) < 2:
            print("❌ Ошибка: код валюты должен содержать минимум 2 символа")
            return

        # Валидация суммы
        if amount <= 0:
            print("❌ Ошибка: 'amount' должен быть положительным числом")
            return

        try:
            # Получаем текущий баланс до продажи
            current_balance = self.portfolio_manager.get_wallet_balance(currency_code)

            # Проверяем существование кошелька
            if current_balance is None:
                print(f"❌ Ошибка: у вас нет кошелька '{currency_code}'. Добавьте валюту: она создаётся автоматически при первой покупке.")
                return

            # Получаем текущий курс
            service = CurrencyService()
            rate = service.get_exchange_rate(currency_code, 'USD')

            if not rate:
                print(f"❌ Ошибка: не удалось получить курс для {currency_code}→USD")
                return

            # Рассчитываем выручку от продажи
            revenue_usd = amount * rate

            # Выполняем продажу (может выбросить InsufficientFundsError)
            success, message = self.portfolio_manager.sell_currency(currency_code, amount)

            if success:
                # Получаем новый баланс после продажи
                new_balance = self.portfolio_manager.get_wallet_balance(currency_code)
                if new_balance is None:
                    new_balance = 0.0

                print(f"✅ Продажа выполнена: {amount:.4f} {currency_code} по курсу {rate:.2f} USD/{currency_code}")
                print("   Изменения в портфеле:")
                print(f"   - {currency_code}: было {current_balance:.4f} → стало {new_balance:.4f}")
                print(f"   Оценочная выручка: {revenue_usd:,.2f} USD")
            else:
                print(f"❌ {message}")

        except ValutaTradeError as e:
            self._handle_exception(e)
        except Exception as e:
            print(f"❌ Непредвиденная ошибка: {e}")

    def do_getrate(self, arg: str) -> None:
        """
        Получить курс валюты.
        Использование: getrate --from <currency_code> --to <currency_code>
        Пример: getrate --from USD --to BTC
        Пример: getrate --from EUR --to USD

        Ошибки:
        - CurrencyNotFoundError: "Неизвестная валюта '{code}'"
        - ApiRequestError: "Ошибка при обращении к внешнему API: {reason}"
        """
        # Парсим аргументы
        from_currency = None
        to_currency = None

        args = shlex.split(arg)
        i = 0
        while i < len(args):
            if args[i] == "--from" and i + 1 < len(args):
                from_currency = args[i + 1].upper()
                i += 2
            elif args[i] == "--to" and i + 1 < len(args):
                to_currency = args[i + 1].upper()
                i += 2
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: getrate --from <currency_code> --to <currency_code>")
                print("Пример: getrate --from USD --to BTC")
                print("Пример: getrate --from EUR --to USD")
                return

        # Проверяем обязательные аргументы
        if not from_currency or not to_currency:
            print("❌ Ошибка: требуются оба аргумента --from и --to")
            print("Использование: getrate --from <currency_code> --to <currency_code>")
            print("Пример: getrate --from USD --to BTC")
            return

        try:
            # Проверяем существование валют через get_currency (может выбросить CurrencyNotFoundError)
            try:
                from ..core.currencies import get_currency
                get_currency(from_currency)
                get_currency(to_currency)
            except CurrencyNotFoundError as e:
                self._handle_exception(e)
                return

            # Получаем курс (может выбросить ApiRequestError через CurrencyService)
            success, message, rate, updated_at = self.rate_manager.get_rate(from_currency, to_currency)

            if success and rate is not None:
                # Форматируем время обновления
                time_str = "неизвестно"
                if updated_at:
                    try:
                        dt = datetime.fromisoformat(updated_at)
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        time_str = updated_at

                print(f"✅ {message}: {rate:.8f} (обновлено: {time_str})")

                # Показываем обратный курс если он не бесконечный
                if rate != 0:
                    reverse_rate = 1 / rate
                    print(f"   Обратный курс {to_currency}→{from_currency}: {reverse_rate:.2f}")
            else:
                print(f"❌ {message}")

        except ApiRequestError as e:
            self._handle_exception(e)
        except CurrencyNotFoundError as e:
            self._handle_exception(e)
        except Exception as e:
            print(f"❌ Непредвиденная ошибка: {e}")

    def do_exit(self, _: str) -> None:
        """Выйти из приложения: exit"""
        print("👋 До свидания!")
        return True

    def do_quit(self, arg: str) -> None:
        """Алиас для exit"""
        return self.do_exit(arg)

    # ===== Вспомогательные команды =====
    def do_whoami(self, _: str) -> None:
        """Показать информацию о текущем пользователе: whoami"""
        if self.user_manager.is_logged_in:
            user = self.user_manager.current_user
            user_info = user.get_user_info()
            print("👤 Текущий пользователь:")
            print(f"   ID: {user_info['user_id']}")
            print(f"   Имя: {user_info['username']}")
            print(f"   Дата регистрации: {user_info['registration_date']}")
        else:
            print("❌ Ошибка: вы не авторизованы")

    def do_logout(self, _: str) -> None:
        """Выход из системы: logout"""
        success, message = self.user_manager.logout()
        if success:
            print(f"✅ {message}")
            self.prompt = "> "
        else:
            print(f"❌ {message}")

    # ===== Методы cmd.Cmd =====
    def default(self, line: str) -> None:
        """Обработка неизвестных команд."""
        # Если команда show-portfolio, перенаправляем на showportfolio
        if line.startswith('show-portfolio'):
            new_line = line.replace('show-portfolio', 'showportfolio', 1)
            self.onecmd(new_line)
        # Если команда get-rate, перенаправляем на getrate (без дефиса)
        elif line.startswith('get-rate'):
            new_line = line.replace('get-rate', 'getrate', 1)
            self.onecmd(new_line)
        else:
            print(f"❌ Неизвестная команда: {line}")
            print("   Введите 'help' для списка доступных команд")

    def emptyline(self) -> None:
        """Обработка пустой строки."""
        pass

    def do_help(self, arg: str) -> None:
        """Показать справку по командам: help [command]"""
        if arg:
            super().do_help(arg)
        else:
            print("\n📋 Доступные команды:\n")

            commands_table = PrettyTable()
            commands_table.field_names = ["Команда", "Описание", "Пример", "Возможные ошибки"]
            commands_table.align["Команда"] = "l"
            commands_table.align["Описание"] = "l"
            commands_table.align["Пример"] = "l"
            commands_table.align["Возможные ошибки"] = "l"

            commands = [
                ("register", "Регистрация нового пользователя", "register --username alice --password 1234", "Username занят, пароль короткий"),
                ("login", "Вход в систему", "login --username alice --password 1234", "Пользователь не найден, неверный пароль"),
                ("logout", "Выход из системы", "logout", "-"),
                ("showportfolio / show-portfolio", "Показать портфель", "showportfolio", "Требуется авторизация"),
                ("showportfolio --base EUR", "Портфель в EUR", "showportfolio --base EUR", "Неизвестная базовая валюта"),
                ("buy", "Купить валюту", "buy --currency BTC --amount 0.05", "CurrencyNotFoundError, ApiRequestError"),
                ("sell", "Продать валюту", "sell --currency BTC --amount 0.01", "InsufficientFundsError, ApiRequestError"),
                ("getrate / get-rate", "Получить курс валюты", "getrate --from USD --to BTC", "CurrencyNotFoundError, ApiRequestError"),
                ("whoami", "Инфо о текущем пользователе", "whoami", "-"),
                ("exit/quit", "Выход из приложения", "exit", "-"),
                ("help", "Показать эту справку", "help", "-"),
            ]

            for cmd_name, desc, example, errors in commands:
                commands_table.add_row([cmd_name, desc, example, errors])

            print(commands_table)

            print("\n🛑 Описание ошибок:")
            print("  • CurrencyNotFoundError - неизвестная валюта")
            print("  • InsufficientFundsError - недостаточно средств")
            print("  • ApiRequestError - ошибка внешнего API")
            print("\n💡 Подсказка: используйте getrate --from USD --to <валюта> для проверки доступности валюты")


def run_cli() -> None:
    """Запуск CLI интерфейса."""
    try:
        cli = TradingCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем. До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
