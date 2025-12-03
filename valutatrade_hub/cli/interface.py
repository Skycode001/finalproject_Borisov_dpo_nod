import cmd
import shlex

from prettytable import PrettyTable

from ..core.usecases import PortfolioManager, RateManager, UserManager
from ..core.utils import InputValidator


class TradingCLI(cmd.Cmd):
    """Командный интерфейс торговой платформы (только требуемые команды)."""

    intro = "Добро пожаловать в ValutaTrade Hub! Введите 'help' для списка команд\n"
    prompt = "> "

    def __init__(self):
        super().__init__()
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
        self.rate_manager = RateManager()

    # ===== ОБЯЗАТЕЛЬНЫЕ КОМАНДЫ =====

    def do_register(self, arg: str) -> None:
        """Регистрация нового пользователя: register <username> <password>"""
        args = shlex.split(arg)
        if len(args) != 2:
            print("Использование: register <username> <password>")
            return

        username, password = args
        success, message = self.user_manager.register(username, password)
        print(f"{'[OK]' if success else '[ERROR]'} {message}")

    def do_login(self, arg: str) -> None:
        """Вход в систему: login <username> <password>"""
        args = shlex.split(arg)
        if len(args) != 2:
            print("Использование: login <username> <password>")
            return

        username, password = args
        success, message = self.user_manager.login(username, password)
        print(f"{'[OK]' if success else '[ERROR]'} {message}")

        if success:
            self.prompt = f"{username}> "

    def do_show_portfolio(self, _: str) -> None:
        """Показать портфель: show-portfolio"""
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
            print(f"{'[ERROR]' if not success else '[INFO]'} {message}")

    def do_buy(self, arg: str) -> None:
        """Купить валюту: buy <currency> <amount>"""
        if not self.user_manager.is_logged_in:
            print("[ERROR] Требуется авторизация. Используйте команду login")
            return

        args = shlex.split(arg)
        if len(args) != 2:
            print("Использование: buy <currency_code> <amount>")
            return

        currency_code, amount_str = args
        amount = InputValidator.validate_amount(amount_str)

        if amount is None:
            print("[ERROR] Сумма должна быть положительным числом")
            return

        success, message = self.portfolio_manager.buy_currency(currency_code, amount)
        print(f"{'[OK]' if success else '[ERROR]'} {message}")

    def do_sell(self, arg: str) -> None:
        """Продать валюту: sell <currency> <amount>"""
        if not self.user_manager.is_logged_in:
            print("[ERROR] Требуется авторизация. Используйте команду login")
            return

        args = shlex.split(arg)
        if len(args) != 2:
            print("Использование: sell <currency_code> <amount>")
            return

        currency_code, amount_str = args
        amount = InputValidator.validate_amount(amount_str)

        if amount is None:
            print("[ERROR] Сумма должна быть положительным числом")
            return

        success, message = self.portfolio_manager.sell_currency(currency_code, amount)
        print(f"{'[OK]' if success else '[ERROR]'} {message}")

    def do_get_rate(self, arg: str) -> None:
        """Получить курс: get-rate <currency> [to_currency=USD]"""
        args = shlex.split(arg)

        if len(args) == 0:
            print("Использование: get-rate <currency_code> [target_currency]")
            return

        from_currency = args[0]
        to_currency = args[1] if len(args) > 1 else 'USD'

        success, message, rate = self.rate_manager.get_rate(from_currency, to_currency)

        if success and rate is not None:
            print(f"[OK] {message}: {rate:.6f}")
            print(f"     1 {from_currency.upper()} = {rate:.6f} {to_currency.upper()}")
        else:
            print(f"[ERROR] {message}")

    def do_exit(self, _: str) -> None:
        """Выйти: exit"""
        print("Выход...")
        return True

    def do_quit(self, arg: str) -> None:
        """Выйти: quit"""
        return self.do_exit(arg)

    def do_help(self, arg: str) -> None:
        """Показать справку"""
        if arg:
            super().do_help(arg)
        else:
            print("\nДоступные команды:")
            print("  register <username> <password>  - Регистрация")
            print("  login <username> <password>     - Вход")
            print("  show-portfolio                  - Показать портфель")
            print("  buy <currency> <amount>         - Купить валюту")
            print("  sell <currency> <amount>        - Продать валюту")
            print("  get-rate <currency> [to_curr]   - Получить курс")
            print("  exit / quit                     - Выход")
            print("  help [command]                  - Справка")

    def default(self, line: str) -> None:
        print(f"[ERROR] Неизвестная команда: {line}")
        print("        Введите 'help' для списка команд")

    def emptyline(self) -> None:
        pass


def run_cli() -> None:
    """Запуск CLI"""
    TradingCLI().cmdloop()
