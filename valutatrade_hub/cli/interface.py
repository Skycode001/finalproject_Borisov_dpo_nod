import cmd
import shlex

from prettytable import PrettyTable

from ..core.usecases import PortfolioManager, RateManager, UserManager
from ..core.utils import InputValidator


class TradingCLI(cmd.Cmd):
    """Командный интерфейс торговой платформы."""

    intro = "Добро пожаловать в ValutaTrade Hub! Введите 'help' для списка команд\n"
    prompt = "> "

    def __init__(self):
        super().__init__()
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
        self.rate_manager = RateManager()

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

    def do_show_portfolio(self, _: str) -> None:
        """
        Показать портфель текущего пользователя.
        Использование: show-portfolio
        """
        success, message, portfolio_data = self.portfolio_manager.show_portfolio()

        if success and portfolio_data:
            print("\n📊 Ваш портфель:")
            table = PrettyTable()
            table.field_names = ["Валюта", "Баланс", "Стоимость в USD"]

            for currency, balance in portfolio_data["data"].items():
                table.add_row([currency, f"{balance:.4f}", f"${balance * 100:.2f}"])  # Упрощенный расчет

            print(table)
            print(f"💰 Общая стоимость: ${portfolio_data['total_value']:.2f}")
        else:
            print(f"❌ {message}")

    def do_buy(self, arg: str) -> None:
        """
        Купить валюту.
        Использование: buy <currency_code> <amount>
        Пример: buy BTC 0.5
        """
        if not self.user_manager.is_logged_in:
            print("❌ Ошибка: требуется авторизация. Используйте команду login")
            return

        args = shlex.split(arg)
        if len(args) != 2:
            print("Использование: buy <currency_code> <amount>")
            print("Пример: buy BTC 0.5")
            return

        currency_code, amount_str = args
        amount = InputValidator.validate_amount(amount_str)

        if amount is None:
            print("❌ Ошибка: сумма должна быть положительным числом")
            return

        success, message = self.portfolio_manager.buy_currency(currency_code, amount)
        print(f"{'✅' if success else '❌'} {message}")

    def do_sell(self, arg: str) -> None:
        """
        Продать валюту.
        Использование: sell <currency_code> <amount>
        Пример: sell BTC 0.1
        """
        if not self.user_manager.is_logged_in:
            print("❌ Ошибка: требуется авторизация. Используйте команду login")
            return

        args = shlex.split(arg)
        if len(args) != 2:
            print("Использование: sell <currency_code> <amount>")
            print("Пример: sell BTC 0.1")
            return

        currency_code, amount_str = args
        amount = InputValidator.validate_amount(amount_str)

        if amount is None:
            print("❌ Ошибка: сумма должна быть положительным числом")
            return

        success, message = self.portfolio_manager.sell_currency(currency_code, amount)
        print(f"{'✅' if success else '❌'} {message}")

    def do_get_rate(self, arg: str) -> None:
        """
        Получить курс валюты.
        Использование: get-rate <currency_code> [target_currency]
        Пример: get-rate BTC USD
        Пример: get-rate EUR (по умолчанию к USD)
        """
        args = shlex.split(arg)

        if len(args) == 0:
            print("Использование: get-rate <currency_code> [target_currency]")
            print("Пример: get-rate BTC USD")
            print("Пример: get-rate EUR (по умолчанию к USD)")
            return

        from_currency = args[0]
        to_currency = args[1] if len(args) > 1 else 'USD'

        success, message, rate = self.rate_manager.get_rate(from_currency, to_currency)

        if success and rate is not None:
            print(f"✅ {message}: {rate:.6f}")
            print(f"   1 {from_currency.upper()} = {rate:.6f} {to_currency.upper()}")
        else:
            print(f"❌ {message}")

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
            commands_table.field_names = ["Команда", "Описание", "Пример"]
            commands_table.align["Команда"] = "l"
            commands_table.align["Описание"] = "l"
            commands_table.align["Пример"] = "l"

            commands = [
                ("register", "Регистрация нового пользователя", "register --username alice --password 1234"),
                ("login", "Вход в систему", "login --username alice --password 1234"),
                ("logout", "Выход из системы", "logout"),
                ("show-portfolio", "Показать портфель", "show-portfolio"),
                ("buy", "Купить валюту", "buy BTC 0.5"),
                ("sell", "Продать валюту", "sell BTC 0.1"),
                ("get-rate", "Получить курс валюты", "get-rate EUR USD"),
                ("whoami", "Инфо о текущем пользователе", "whoami"),
                ("exit/quit", "Выход из приложения", "exit"),
                ("help", "Показать эту справку", "help"),
            ]

            for cmd_name, desc, example in commands:
                commands_table.add_row([cmd_name, desc, example])

            print(commands_table)


def run_cli() -> None:
    """Запуск CLI интерфейса."""
    try:
        cli = TradingCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем. До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
