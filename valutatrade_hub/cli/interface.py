import cmd
import shlex
from datetime import datetime

from prettytable import PrettyTable

from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    UserNotAuthenticatedError,
    ValutaTradeError,
)
from ..core.usecases import PortfolioManager, RateManager, UserManager
from ..core.utils import CurrencyService, InputValidator


class TradingCLI(cmd.Cmd):
    """Командный интерфейс торговой платформы с поддержкой новых ошибок."""

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
            print(f"❌ {str(e)}")
            print("   Проверьте баланс кошелька и введите меньшую сумму.")

        elif isinstance(e, CurrencyNotFoundError):
            print(f"❌ {str(e)}")
            print("   Для просмотра списка поддерживаемых валют используйте команду:")
            print("   list-currencies")

        elif isinstance(e, ApiRequestError):
            print(f"❌ {str(e)}")
            print("   Пожалуйста, повторите попытку позже.")
            print("   Проверьте подключение к сети и доступность сервиса.")

        elif isinstance(e, InvalidAmountError):
            print(f"❌ {str(e)}")
            print("   Введите положительное число больше нуля.")

        elif isinstance(e, UserNotAuthenticatedError):
            print(f"❌ {str(e)}")
            print("   Используйте команду login для входа в систему.")

        elif isinstance(e, ValutaTradeError):
            print(f"❌ {str(e)}")

        else:
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
        print(f"\n📊 Портфель пользователя '{username}' (база: {base_currency}):")

        total_value = portfolio_data["total_value"]
        service = CurrencyService()

        for currency, balance in portfolio_data["data"].items():
            # Получаем курс конвертации
            if currency == base_currency:
                converted = balance
            else:
                try:
                    rate = service.get_exchange_rate(currency, base_currency)
                    if not rate:
                        print(f"❌ Ошибка: курс для {currency}/{base_currency} не найден")
                        return
                    converted = balance * rate
                except ApiRequestError as e:
                    self._handle_exception(e)
                    return

            # Форматируем вывод для каждой валюты
            print(f"  - {currency}: {balance:,.4f}  → {converted:,.2f} {base_currency}")

        print(f"{'='*50}")
        print(f"💎 ИТОГО: {total_value:,.2f} {base_currency}")

    def do_buy(self, arg: str) -> None:
        """
        Купить валюту.
        Использование: buy --currency <currency_code> --amount <amount>
        Пример: buy --currency BTC --amount 0.05

        Ошибки:
        - CurrencyNotFoundError: "Неизвестная валюта '{code}'"
        - ApiRequestError: "Ошибка при обращении к внешнему API: {reason}"
        - InvalidAmountError: "Сумма покупки должна быть положительной"
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
                print("Использование: buy --currency <currency_code> --amount <amount>")
                print("Пример: buy --currency BTC --amount 0.05")
                return

        # Проверяем обязательные аргументы
        if not currency_code or amount is None:
            print("❌ Ошибка: требуются оба аргумента --currency и --amount")
            print("Использование: buy --currency <currency_code> --amount <amount>")
            print("Пример: buy --currency BTC --amount 0.05")
            return

        try:
            # Выполняем покупку (может выбросить различные исключения)
            success, message = self.portfolio_manager.buy_currency(currency_code, amount)

            if success:
                # Разбираем обогащенное сообщение
                lines = message.split(". ")
                for line in lines:
                    if "Покупка выполнена" in line or "Оценочная стоимость" in line:
                        print(f"✅ {line}")
                    else:
                        print(f"   {line}")
                # Дополнительная информация
                print("   📈 Операция записана в журнал действий")
            else:
                print(f"❌ {message}")

        except (CurrencyNotFoundError, ApiRequestError, InvalidAmountError,
                InsufficientFundsError, UserNotAuthenticatedError) as e:
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
        - CurrencyNotFoundError: "Неизвестная валюта '{code}'"
        - ApiRequestError: "Ошибка при обращении к внешнему API: {reason}"
        - InvalidAmountError: "Сумма продажи должна быть положительной"
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

        try:
            # Выполняем продажу (может выбросить различные исключения)
            success, message = self.portfolio_manager.sell_currency(currency_code, amount)

            if success:
                # Разбираем обогащенное сообщение
                lines = message.split(". ")
                for line in lines:
                    if "Продажа выполнена" in line or "Оценочная выручка" in line:
                        print(f"✅ {line}")
                    else:
                        print(f"   {line}")
                # Дополнительная информация
                print("   📈 Операция записана в журнал действий")
            else:
                print(f"❌ {message}")

        except (CurrencyNotFoundError, ApiRequestError, InvalidAmountError,
                InsufficientFundsError, UserNotAuthenticatedError) as e:
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
        - CurrencyNotFoundError: "Неизвестная валюта '{code}'" - точные сообщения
        - ApiRequestError: "Ошибка при обращении к внешнему API: {reason}" - точные сообщения
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
            # Получаем курс (может выбросить CurrencyNotFoundError или ApiRequestError)
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

                print(f"✅ Курс {from_currency}→{to_currency}: {rate:.8f}")
                print(f"   📅 Обновлено: {time_str}")

                # Показываем обратный курс если он не бесконечный
                if rate != 0:
                    reverse_rate = 1 / rate
                    # Форматируем в зависимости от величины
                    if reverse_rate < 0.0001:
                        print(f"   🔄 Обратный курс {to_currency}→{from_currency}: {reverse_rate:.8f}")
                    else:
                        print(f"   🔄 Обратный курс {to_currency}→{from_currency}: {reverse_rate:.6f}")

        except CurrencyNotFoundError as e:
            print(f"❌ {str(e)}")
            print("   Используйте команду 'list-currencies' для просмотра доступных валют")
            print("   Проверьте правильность написания кода валюты (например, USD, EUR, BTC)")
        except ApiRequestError as e:
            print(f"❌ {str(e)}")
            print("   Сервис курсов валют временно недоступен")
            print("   Попробуйте снова через несколько минут")
            print("   Используется кешированное значение (если доступно)")
        except Exception as e:
            print(f"❌ Непредвиденная ошибка: {e}")

    # ===== НОВЫЕ КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ PARSER SERVICE =====

    def do_updaterates(self, arg: str) -> None:
        """
        Запустить немедленное обновление курсов валют.
        Использование: update-rates [--source <coingecko|exchangerate>]
        Пример: update-rates
        Пример: update-rates --source coingecko
        """
        # Парсим аргументы
        args = shlex.split(arg)
        source = None  # По умолчанию - все источники

        i = 0
        while i < len(args):
            if args[i] == "--source" and i + 1 < len(args):
                source = args[i + 1].lower()
                if source not in ["coingecko", "exchangerate"]:
                    print(f"❌ Ошибка: неизвестный источник '{source}'. Используйте 'coingecko' или 'exchangerate'")
                    return
                i += 2
            elif args[i] and not args[i].startswith("--"):
                # Есть аргумент, но не флаг --source
                print("❌ Ошибка: неверный формат команды")
                print("Использование: update-rates [--source <coingecko|exchangerate>]")
                print("Пример: update-rates")
                print("Пример: update-rates --source coingecko")
                return
            else:
                i += 1

        print("🔄 Начало обновления курсов...")

        try:
            # Инициализируем RatesUpdater
            from ..parser_service.updater import RatesUpdater
            updater = RatesUpdater()

            if source == "coingecko":
                print("📈 Обновление данных только от CoinGecko...")
                # Для обновления только от одного источника нужно модифицировать логику
                # Временно используем стандартный run_update и фильтруем логи
                result = updater.run_update()
                # Фильтруем результат для отображения только криптовалют
                crypto_pairs = {k: v for k, v in result.get("pairs", {}).items()
                              if k.split('_')[0] in ["BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT"]}
                updated_count = len(crypto_pairs)
                print(f"✅ CoinGecko: OK ({updated_count} курсов)")

            elif source == "exchangerate":
                print("💵 Обновление данных только от ExchangeRate-API...")
                result = updater.run_update()
                # Фильтруем результат для отображения только фиатных валют
                fiat_currencies = ["EUR", "GBP", "RUB", "JPY", "CHF"]
                fiat_pairs = {k: v for k, v in result.get("pairs", {}).items()
                             if k.split('_')[0] in fiat_currencies}
                updated_count = len(fiat_pairs)
                print(f"✅ ExchangeRate-API: OK ({updated_count} курсов)")

            else:
                # Обновляем все источники
                print("📈 Запрос к CoinGecko...")
                print("💵 Запрос к ExchangeRate-API...")
                result = updater.run_update()

                # Считаем количество курсов по типам
                pairs = result.get("pairs", {})
                crypto_count = len([p for p in pairs.keys()
                                  if p.split('_')[0] in ["BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT"]])
                fiat_count = len([p for p in pairs.keys()
                                if p.split('_')[0] in ["EUR", "GBP", "RUB", "JPY", "CHF"]])

                if crypto_count > 0:
                    print(f"✅ CoinGecko: OK ({crypto_count} курсов)")
                if fiat_count > 0:
                    print(f"✅ ExchangeRate-API: OK ({fiat_count} курсов)")

                updated_count = len(pairs)

            # Выводим информацию о последнем обновлении
            last_refresh = result.get("last_refresh", "неизвестно")
            try:
                dt = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                time_str = last_refresh

            print(f"💾 Запись {updated_count} курсов в data/rates.json...")
            print(f"✅ Обновление успешно. Всего обновлено курсов: {updated_count}. Последнее обновление: {time_str}")

            # Принудительно перезагружаем кеш в RateManager
            self.rate_manager.reload_rates_cache()
            print("🔄 Кеш RateManager перезагружен")

        except ApiRequestError as e:
            print(f"❌ Ошибка при обращении к API: {str(e)}")
            print("ℹ️  Обновление завершено с ошибками. Проверьте logs/parser_service.log для подробностей.")
        except Exception as e:
            print(f"❌ Неизвестная ошибка: {e}")
            print("ℹ️  Проверьте логи для подробностей.")

    def do_showrates(self, arg: str) -> None:
        """
        Показать список актуальных курсов из локального кеша с возможностью фильтрации.
        Использование: show-rates [--currency <code>] [--top <N>] [--base <currency>]
        Пример: show-rates
        Пример: show-rates --currency BTC
        Пример: show-rates --top 2
        Пример: show-rates --base EUR
        """
        # Парсим аргументы
        args = shlex.split(arg)
        currency_filter = None
        top_n = None
        base_currency = 'USD'  # По умолчанию

        i = 0
        while i < len(args):
            if args[i] == "--currency" and i + 1 < len(args):
                currency_filter = args[i + 1].upper()
                i += 2
            elif args[i] == "--top" and i + 1 < len(args):
                try:
                    top_n = int(args[i + 1])
                    if top_n <= 0:
                        print("❌ Ошибка: значение --top должно быть положительным числом")
                        return
                    i += 2
                except ValueError:
                    print("❌ Ошибка: --top должен быть числом")
                    return
            elif args[i] == "--base" and i + 1 < len(args):
                base_currency = args[i + 1].upper()
                i += 2
            elif args[i].startswith("--"):
                print(f"❌ Ошибка: неизвестный флаг '{args[i]}'")
                print("Использование: show-rates [--currency <code>] [--top <N>] [--base <currency>]")
                return
            else:
                i += 1

        try:
            # Получаем данные из кеша RateManager
            rates_data = self.rate_manager.get_all_rates()

            # Проверяем, есть ли данные
            if not rates_data or "pairs" not in rates_data or not rates_data["pairs"]:
                print("❌ Локальный кеш курсов пуст.")
                print("ℹ️  Выполните 'update-rates', чтобы загрузить данные.")
                return

            pairs = rates_data["pairs"]
            last_refresh = rates_data.get("last_refresh", "неизвестно")

            # Форматируем время обновления
            try:
                dt = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                time_str = last_refresh

            print(f"📊 Курсы из кеша (обновлено: {time_str}):")

            # Фильтруем пары по базовой валюте
            if base_currency != 'USD':
                # Нужно конвертировать курсы к новой базовой валюте
                # Для простоты показываем только USD пары и конвертируем
                print(f"⚠️  Отображение курсов к базовой валюте {base_currency} (через USD)...")

                # Находим курс базовой валюты к USD
                base_to_usd_key = f"{base_currency}_USD"
                if base_to_usd_key in pairs:
                    base_rate = pairs[base_to_usd_key]["rate"]
                    print(f"   Курс {base_currency} к USD: {base_rate}")
                    print()

                # Создаем список для сортировки
                rate_list = []
                for pair_key, pair_data in pairs.items():
                    currency = pair_key.split('_')[0]
                    to_currency = pair_key.split('_')[1]

                    # Пропускаем пары, где целевая валюта не USD
                    if to_currency != "USD":
                        continue

                    # Пропускаем саму базовую валюту
                    if currency == base_currency:
                        continue

                    # Конвертируем курс к новой базовой валюте
                    if currency != "USD":
                        rate = pair_data["rate"]
                        if base_currency == "USD":
                            converted_rate = rate
                        else:
                            # Конвертируем через USD
                            converted_rate = rate / base_rate if base_rate != 0 else 0

                        rate_list.append((currency, converted_rate, pair_data.get("updated_at", "неизвестно")))
            else:
                # Используем USD как базовую валюту (по умолчанию)
                rate_list = []
                for pair_key, pair_data in pairs.items():
                    parts = pair_key.split('_')
                    if len(parts) == 2:
                        currency, to_currency = parts
                        if to_currency == "USD" and currency != "USD":
                            rate_list.append((currency, pair_data["rate"],
                                            pair_data.get("updated_at", "неизвестно")))

            # Применяем фильтр по валюте
            if currency_filter:
                filtered_rates = [(c, r, t) for c, r, t in rate_list if c == currency_filter]
                if not filtered_rates:
                    print(f"❌ Курс для '{currency_filter}' не найден в кеше.")
                    print("ℹ️  Проверьте правильность кода валюты или выполните 'update-rates'")
                    return
                rate_list = filtered_rates

            # Сортируем по курсу (по убыванию для криптовалют)
            # Разделяем крипто и фиат для правильной сортировки
            crypto_currencies = ["BTC", "ETH", "LTC", "XRP", "ADA", "SOL", "DOT"]

            crypto_rates = [(c, r, t) for c, r, t in rate_list if c in crypto_currencies]
            fiat_rates = [(c, r, t) for c, r, t in rate_list if c not in crypto_currencies]

            # Сортируем криптовалюты по курсу (убывание)
            crypto_rates.sort(key=lambda x: x[1], reverse=True)

            # Сортируем фиатные валюты по алфавиту
            fiat_rates.sort(key=lambda x: x[0])

            # Объединяем списки
            sorted_rates = crypto_rates + fiat_rates

            # Применяем фильтр --top
            if top_n:
                # Берем только криптовалюты для --top
                top_crypto = crypto_rates[:top_n]
                if top_crypto:
                    print(f"📈 Топ-{top_n} самых дорогих криптовалют:")
                    for currency, rate, _updated_at in top_crypto:
                        pair_key = f"{currency}_{base_currency}"
                        print(f"  • {pair_key}: {rate:,.2f}")
                else:
                    print(f"ℹ️  Нет криптовалют для отображения топ-{top_n}")
                return

            # Выводим все курсы
            if crypto_rates:
                print("📈 Криптовалюты:")
                for currency, rate, updated_at in crypto_rates:
                    pair_key = f"{currency}_{base_currency}"
                    # Форматируем время обновления
                    try:
                        if 'T' in updated_at:
                            time_part = updated_at.split('T')[1][:8]
                            display_time = time_part
                        else:
                            display_time = updated_at[:8]
                    except (IndexError, AttributeError):
                        display_time = updated_at

                    print(f"  • {pair_key}: {rate:,.2f} (обновлено: {display_time})")

            if fiat_rates:
                print("\n💵 Фиатные валюты:")
                for currency, rate, _updated_at in fiat_rates:
                    pair_key = f"{currency}_{base_currency}"
                    # Для фиатных валют с малыми курсами показываем больше знаков
                    if rate < 0.1:
                        rate_str = f"{rate:.6f}"
                    else:
                        rate_str = f"{rate:.4f}"

                    print(f"  • {pair_key}: {rate_str}")

            print(f"\n📊 Всего курсов: {len(sorted_rates)}")

        except Exception as e:
            print(f"❌ Ошибка при получении курсов: {e}")

    # ===== КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ PARSER SERVICE =====

    def do_parser_test(self, _: str) -> None:
        """
        Тестирование Parser Service: получение курсов от CoinGecko.
        Команда: parser-test
        """
        print("🔧 Тестирование Parser Service...")
        try:
            # Импортируем компоненты Parser Service
            from ..parser_service.api_clients import CoinGeckoClient
            from ..parser_service.updater import RatesUpdater

            print("1. Тестирование CoinGeckoClient...")
            client = CoinGeckoClient()

            try:
                rates = client.get_crypto_rates()
                print(f"✅ Получено {len(rates)} курсов криптовалют:")
                for currency, info in rates.items():
                    print(f"   • {currency}: ${info['rate']:.2f} (источник: {info['source']})")

                print("\n2. Тестирование RatesUpdater...")
                updater = RatesUpdater()
                all_rates = updater.update_all_rates()

                print(f"✅ Обновление завершено. Всего валют: {len(all_rates)}")
                # Показать статус
                status = updater.get_update_status()
                print("📊 Статус обновления:")
                print(f"   • Последнее обновление: {status['last_update']}")
                print(f"   • Всего валют: {status['total_currencies']}")
                print(f"   • Источники: {', '.join(status['sources'])}")

            except Exception as e:
                print(f"❌ Ошибка при тестировании: {e}")
                print("   Проверьте подключение к интернету и доступность CoinGecko API")

        except ImportError as e:
            print(f"❌ Ошибка импорта Parser Service: {e}")
            print("   Убедитесь, что файлы Parser Service созданы в valutatrade_hub/parser_service/")

    def do_update_all(self, _: str) -> None:
        """
        Обновить все курсы валют через Parser Service.
        Команда: update-all
        """
        print("🔄 Обновление всех курсов через Parser Service...")
        try:
            from ..parser_service.updater import RatesUpdater

            updater = RatesUpdater()
            # ИСПРАВЛЕНИЕ: используем новый метод run_update() вместо update_all_rates()
            result = updater.run_update()

            print("✅ Обновление завершено!")
            print(f"   • Обновлено пар курсов: {len(result.get('pairs', {}))}")

            # Фильтруем криптовалюты и фиатные
            pairs = result.get('pairs', {})
            crypto_currencies = []
            fiat_currencies = []

            for pair_key in pairs.keys():
                currency = pair_key.split('_')[0]
                if currency in ['BTC', 'ETH', 'LTC', 'XRP', 'ADA', 'SOL', 'DOT']:
                    crypto_currencies.append(currency)
                elif currency not in ['USD']:
                    fiat_currencies.append(currency)

            print(f"   • Криптовалюты: {sorted(set(crypto_currencies))}")
            print(f"   • Фиатные валюты: {sorted(set(fiat_currencies))}")

            # Принудительно перезагружаем кеш в RateManager
            self.rate_manager.reload_rates_cache()
            print("   • Кеш RateManager перезагружен")

            print("\n💡 Теперь используйте команды:")
            print("   • getrate --from BTC --to USD  (проверить обновленный курс)")
            print("   • showportfolio                (если есть портфель)")

        except Exception as e:
            print(f"❌ Ошибка при обновлении: {e}")

    def do_parser_status(self, _: str) -> None:
        """
        Показать статус Parser Service.
        Команда: parser-status
        """
        print("📊 Статус Parser Service:")
        try:
            from ..parser_service.updater import RatesUpdater

            updater = RatesUpdater()
            status = updater.get_update_status()

            print(f"   • Последнее обновление: {status['last_update'] or 'никогда'}")
            print(f"   • Всего валют в кеше: {status['latest_currencies']}")
            # Показываем первые 10 валют
            currencies = status['currencies']
            if currencies:
                display = ', '.join(currencies[:10])
                if len(currencies) > 10:
                    display += f'... (еще {len(currencies) - 10})'
                print(f"   • Доступные валюты: {display}")
            else:
                print("   • Доступные валюты: нет данных")
            print(f"   • Источники данных: {', '.join(status['sources'])}")
            print(f"   • Всего исторических записей: {status['total_records']}")
            print(f"   • Формат данных: {status['formats']['exchange_rates']}")
            # Проверить файлы
            import os
            print("\n📁 Файлы данных:")
            print(f"   • data/rates.json: {'✅ существует' if os.path.exists('data/rates.json') else '❌ отсутствует'}")
            print(f"   • data/exchange_rates.json: {'✅ существует' if os.path.exists('data/exchange_rates.json') else '❌ отсутствует'}")
            # Показать информацию о файлах
            if os.path.exists('data/exchange_rates.json'):
                import json

                try:
                    with open('data/exchange_rates.json', 'r', encoding='utf-8') as f:
                        rates_data = json.load(f)

                    if isinstance(rates_data, dict):
                        print("   • Формат: новый (с уникальными ID)")
                        print(f"   • Всего записей: {len(rates_data)}")
                        # Показать пример записи
                        if rates_data:
                            first_key = next(iter(rates_data))
                            print(f"   • Пример ID записи: {first_key[:50]}...")

                except Exception as e:
                    print(f"   • Ошибка чтения файла: {e}")

        except Exception as e:
            print(f"❌ Ошибка при получении статуса: {e}")

    def do_exit(self, _: str) -> None:
        """Выйти из приложения: exit"""
        print("👋 До свидания!")
        return True

    def do_quit(self, arg: str) -> None:
        """Алиас для exit"""
        return self.do_exit(arg)

    # ===== НОВЫЕ КОМАНДЫ ДЛЯ ИСТОРИЧЕСКИХ ДАННЫХ =====

    def do_exchangestats(self, _: str) -> None:
        """
        Показать статистику по историческим данных в новом формате.
        Команда: exchange-stats
        """
        print("📊 Статистика исторических данных (новый формат):")
        try:
            from ..parser_service.updater import RatesUpdater

            updater = RatesUpdater()
            stats = updater.get_historical_stats()

            if "message" in stats:
                print(f"   ℹ️ {stats['message']}")
                return

            print(f"   • Всего записей: {stats['total_records']}")
            print(f"   • Уникальных валют: {stats['unique_currencies']}")

            if stats.get('currency_stats'):
                print("\n   📈 Статистика по валютам:")
                for currency, currency_stats in stats['currency_stats'].items():
                    print(f"      {currency}:")
                    print(f"        • Записей: {currency_stats['record_count']}")
                    print(f"        • Минимум: {currency_stats['min_rate']:.2f}")
                    print(f"        • Максимум: {currency_stats['max_rate']:.2f}")
                    print(f"        • Среднее: {currency_stats['avg_rate']:.2f}")
                    print(f"        • Источники: {', '.join(currency_stats['sources'])}")

        except Exception as e:
            print(f"❌ Ошибка при получении статистики: {e}")

    def do_viewhistory(self, arg: str) -> None:
        """
        Показать историю курсов для валюты.
        Использование: view-history --currency <code> [--limit N]
        Пример: view-history --currency BTC --limit 5
        """
        args = shlex.split(arg)
        currency = None
        limit = 10

        i = 0
        while i < len(args):
            if args[i] == "--currency" and i + 1 < len(args):
                currency = args[i + 1].upper()
                i += 2
            elif args[i] == "--limit" and i + 1 < len(args):
                try:
                    limit = int(args[i + 1])
                    i += 2
                except ValueError:
                    print("❌ Ошибка: limit должен быть числом")
                    return
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: view-history --currency <code> [--limit N]")
                print("Пример: view-history --currency BTC --limit 5")
                return

        if not currency:
            print("❌ Ошибка: требуется аргумент --currency")
            return

        print(f"📅 История курса {currency}→USD (последние {limit} записей):")

        try:
            from ..parser_service.storage import ExchangeRatesStorage

            storage = ExchangeRatesStorage()
            history = storage.get_rate_history(currency, "USD", limit)

            if not history:
                print(f"   ℹ️ Нет исторических данных для {currency}")
                return

            table = PrettyTable()
            table.field_names = ["Время", "Курс", "Источник", "ID"]
            table.align["Время"] = "l"
            table.align["Курс"] = "r"
            table.align["Источник"] = "l"
            table.align["ID"] = "l"

            for record in history:
                # Обрезаем ID для лучшего отображения
                short_id = record['id'][:20] + "..." if len(record['id']) > 20 else record['id']
                # Форматируем время
                timestamp = record['timestamp']
                if 'T' in timestamp:
                    time_part = timestamp.split('T')[1].split('.')[0]
                    date_part = timestamp.split('T')[0]
                    display_time = f"{date_part} {time_part}"
                else:
                    display_time = timestamp
                table.add_row([
                    display_time,
                    f"{record['rate']:.6f}" if record['rate'] < 1 else f"{record['rate']:.2f}",
                    record['source'],
                    short_id
                ])

            print(table)
            print(f"   Всего записей: {len(history)}")

        except Exception as e:
            print(f"❌ Ошибка при получении истории: {e}")

    def do_cleanuphistory(self, arg: str) -> None:
        """
        Очистить старые записи из истории.
        Использование: cleanup-history [--days N]
        Пример: cleanup-history --days 30
        """
        args = shlex.split(arg)
        days = 30

        i = 0
        while i < len(args):
            if args[i] == "--days" and i + 1 < len(args):
                try:
                    days = int(args[i + 1])
                    i += 2
                except ValueError:
                    print("❌ Ошибка: days должен быть числом")
                    return
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: cleanup-history [--days N]")
                print("Пример: cleanup-history --days 30")
                return

        print(f"🧹 Очистка исторических данных старше {days} дней...")

        try:
            from ..parser_service.storage import ExchangeRatesStorage

            storage = ExchangeRatesStorage()
            deleted_count = storage.cleanup_old_records(days)

            print(f"✅ Удалено {deleted_count} старых записей")

        except Exception as e:
            print(f"❌ Ошибка при очистке истории: {e}")

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
            print("   Статус: активен")
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

    def do_listcurrencies(self, _: str) -> None:
        """
        Показать список поддерживаемых валют: list-currencies
        """
        try:
            from ..core.currencies import get_all_currencies
            currencies = get_all_currencies()

            if not currencies:
                print("❌ Список валют пуст")
                return

            print("📋 Доступные валюты:")
            table = PrettyTable()
            table.field_names = ["Код", "Название", "Тип", "Доп. информация"]
            table.align["Код"] = "l"
            table.align["Название"] = "l"
            table.align["Тип"] = "l"
            table.align["Доп. информация"] = "l"

            for code, currency in currencies.items():
                currency_type = "FIAT" if "FIAT" in currency.get_display_info() else "CRYPTO"
                if currency_type == "FIAT":
                    info = f"Страна: {currency.issuing_country}"
                else:
                    info = f"Алгоритм: {currency.algorithm}"
                table.add_row([code, currency.name, currency_type, info])

            print(table)
            print(f"\nВсего валют: {len(currencies)}")

        except Exception as e:
            print(f"❌ Ошибка при получении списка валют: {e}")

    def do_updaterates_old(self, _: str) -> None:
        """
        Обновить курсы валют вручную: update-rates (старая версия)
        """
        try:
            print("🔄 Обновление курсов валют (старая версия)...")
            success, message = self.rate_manager.update_rates()

            if success:
                print(f"✅ {message}")
                # Показываем информацию о последнем обновлении
                if "last_refresh" in self.rate_manager._rates_data:
                    last_refresh = self.rate_manager._rates_data["last_refresh"]
                    try:
                        dt = datetime.fromisoformat(last_refresh)
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"   📅 Время обновления: {time_str}")
                    except (ValueError, TypeError):
                        pass
                print(f"   📊 Источник: {self.rate_manager._rates_data.get('source', 'неизвестен')}")
            else:
                print(f"❌ {message}")

        except Exception as e:
            print(f"❌ Ошибка при обновлении курсов: {e}")

    def do_viewlogs(self, arg: str) -> None:
        """
        Показать последние записи логов: view-logs [--lines N]
        Пример: view-logs
        Пример: view-logs --lines 10
        """
        import os

        args = shlex.split(arg)
        lines = 5  # по умолчанию

        i = 0
        while i < len(args):
            if args[i] == "--lines" and i + 1 < len(args):
                try:
                    lines = int(args[i + 1])
                    i += 2
                except ValueError:
                    print("❌ Ошибка: количество строк должно быть числом")
                    return
            else:
                print("❌ Ошибка: неверный формат команды")
                print("Использование: view-logs [--lines N]")
                print("Пример: view-logs --lines 10")
                return

        log_file = "logs/actions.log"

        if not os.path.exists(log_file):
            print(f"❌ Файл логов не найден: {log_file}")
            return

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            if not all_lines:
                print("📝 Логи пусты")
                return

            print(f"📝 Последние {min(lines, len(all_lines))} записей логов:")
            print("-" * 60)

            for line in all_lines[-lines:]:
                print(line.rstrip())

        except Exception as e:
            print(f"❌ Ошибка при чтении логов: {e}")

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
        # Если команда update-rates (новая команда)
        elif line.startswith('update-rates'):
            self.do_updaterates(line.replace('update-rates', '', 1).strip())
        # Если команда show-rates (новая команда)
        elif line.startswith('show-rates'):
            self.do_showrates(line.replace('show-rates', '', 1).strip())
        # Если команда list-currencies
        elif line.startswith('list-currencies'):
            self.do_listcurrencies("")
        # Если команда view-logs
        elif line.startswith('view-logs'):
            new_line = line.replace('view-logs', 'viewlogs', 1)
            self.onecmd(new_line)
        # Если команда parser-test
        elif line.startswith('parser-test'):
            self.do_parser_test("")
        # Если команда update-all
        elif line.startswith('update-all'):
            self.do_update_all("")
        # Если команда parser-status
        elif line.startswith('parser-status'):
            self.do_parser_status("")
        # Если команда exchange-stats
        elif line.startswith('exchange-stats'):
            self.do_exchangestats("")
        # Если команда view-history
        elif line.startswith('view-history'):
            new_line = line.replace('view-history', 'viewhistory', 1)
            self.onecmd(new_line)
        # Если команда cleanup-history
        elif line.startswith('cleanup-history'):
            new_line = line.replace('cleanup-history', 'cleanuphistory', 1)
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
                # Основные команды пользователя
                ("register", "Регистрация нового пользователя", "register --username alice --password 1234", "Username занят, пароль короткий"),
                ("login", "Вход в систему", "login --username alice --password 1234", "Пользователь не найден, неверный пароль"),
                ("logout", "Выход из системы", "logout", "-"),
                ("whoami", "Инфо о текущем пользователе", "whoami", "-"),

                # Работа с портфелем
                ("showportfolio", "Показать портфель в USD", "showportfolio", "Требуется авторизация"),
                ("showportfolio --base EUR", "Портфель в EUR", "showportfolio --base EUR", "Неизвестная базовая валюта"),
                ("buy", "Купить валюту", "buy --currency BTC --amount 0.05", "Недостаточно средств, неизвестная валюта, неверная сумма"),
                ("sell", "Продать валюту", "sell --currency BTC --amount 0.01", "Недостаточно средств, валюта не найдена, неверная сумма"),

                # Курсы валют (старые команды)
                ("getrate", "Получить курс между валютами", "getrate --from USD --to BTC", "Валюта не найдена, ошибка API"),
                ("list-currencies", "Список поддерживаемых валют", "list-currencies", "-"),

                # Курсы валют (новые команды)
                ("update-rates", "Обновить все курсы", "update-rates", "Ошибка API"),
                ("update-rates --source coingecko", "Обновить только криптовалюты", "update-rates --source coingecko", "Неизвестный источник"),
                ("update-rates --source exchangerate", "Обновить только фиатные валюты", "update-rates --source exchangerate", "Неизвестный источник"),
                ("show-rates", "Показать все курсы из кеша", "show-rates", "Кеш пуст"),
                ("show-rates --currency BTC", "Курс конкретной валюты", "show-rates --currency BTC", "Валюта не найдена в кеше"),
                ("show-rates --top 3", "Топ-3 криптовалют", "show-rates --top 3", "Нет криптовалют в кеше"),
                ("show-rates --base EUR", "Курсы в EUR", "show-rates --base EUR", "Нет курса для базовой валюты"),

                # Parser Service
                ("update-all", "Обновить все курсы (старая команда)", "update-all", "-"),
                ("parser-test", "Тест Parser Service", "parser-test", "-"),
                ("parser-status", "Статус Parser Service", "parser-status", "-"),
                ("exchange-stats", "Статистика исторических данных", "exchange-stats", "-"),
                ("view-history", "История курса валюты", "view-history --currency BTC --limit 5", "-"),
                ("cleanup-history", "Очистка старых записей", "cleanup-history --days 30", "-"),

                # Логи и отладка
                ("view-logs", "Просмотр логов", "view-logs --lines 10", "Файл логов не найден"),

                # Выход
                ("exit/quit", "Выход из приложения", "exit", "-"),
                ("help", "Показать эту справку", "help", "-"),
            ]

            for cmd_name, desc, example, errors in commands:
                commands_table.add_row([cmd_name, desc, example, errors])

            print(commands_table)

            print("\n🛑 Описание ошибок:")
            print("  • InsufficientFundsError - недостаточно средств для операции")
            print("  • CurrencyNotFoundError - неизвестная валюта (используйте list-currencies)")
            print("  • ApiRequestError - ошибка при обращении к внешнему API")
            print("  • InvalidAmountError - некорректная сумма (должна быть > 0)")
            print("  • UserNotAuthenticatedError - требуется авторизация")

            print("\n💡 Подсказки:")
            print("  • Используйте list-currencies для просмотра доступных валют")
            print("  • При ошибке ApiRequestError проверьте подключение к сети")
            print("  • Логи операций сохраняются в папке logs/")
            print("  • update-rates обновляет курсы через Parser Service")
            print("  • show-rates показывает курсы из локального кеша")
            print("  • Для реальных фиатных курсов нужен ключ ExchangeRate-API")


def run_cli() -> None:
    """Запуск CLI интерфейса."""
    try:
        cli = TradingCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем. До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
