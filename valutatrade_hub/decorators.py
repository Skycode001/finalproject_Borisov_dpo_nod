import functools
import logging
from typing import Any, Callable


def log_action(action_name: str = None, verbose: bool = False):
    """
    Декоратор для логирования доменных операций.

    Логирует операции в формате:
    timestamp (ISO), action (BUY/SELL/REGISTER/LOGIN),
    username (или user_id), currency_code, amount,
    rate и base (если применимо),
    result (OK/ERROR), error_type/error_message при исключениях.

    Args:
        action_name: Название действия в верхнем регистре (BUY/SELL/REGISTER/LOGIN).
        verbose: Дополнительно логировать контекст (например, состояние кошелька).

    Returns:
        Декоратор функции.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Получаем логгер
            logger = logging.getLogger(func.__module__)

            # Определяем действие
            action = action_name or func.__name__.upper()

            # Извлекаем данные из аргументов
            username = None
            user_id = None
            currency_code = None
            amount = None
            rate = None
            base = 'USD'  # По умолчанию
            extra_context = {}

            try:
                # Для методов usecases первый аргумент - self
                if args and hasattr(args[0], '_user_manager'):
                    # Это метод usecases (buy_currency, sell_currency и т.д.)
                    self_instance = args[0]

                    # Получаем текущего пользователя если есть
                    if hasattr(self_instance, '_user_manager'):
                        user_manager = self_instance._user_manager
                        if user_manager.is_logged_in and user_manager.current_user:
                            user = user_manager.current_user
                            username = user.username
                            user_id = user.user_id

                    # Извлекаем параметры из аргументов
                    if len(args) > 1:
                        currency_code = args[1] if len(args) > 1 else None
                        amount = args[2] if len(args) > 2 else None

                    # Или из kwargs
                    currency_code = kwargs.get('currency_code', currency_code)
                    amount = kwargs.get('amount', amount)

                    # Для verbose режима получаем дополнительный контекст
                    if verbose and hasattr(self_instance, '_portfolio_manager'):
                        portfolio_manager = self_instance._portfolio_manager
                        if currency_code and user_id:
                            wallet_balance = portfolio_manager.get_wallet_balance(currency_code)
                            if wallet_balance is not None:
                                extra_context['wallet_balance_before'] = wallet_balance

                # Основное выполнение
                result = func(*args, **kwargs)

                # Определяем результат
                success = False
                if isinstance(result, tuple) and len(result) > 0:
                    success = result[0] if isinstance(result[0], bool) else True
                elif result is not None:
                    success = True

                # Логируем успешное выполнение
                log_record = logger.makeRecord(
                    name=logger.name,
                    level=logging.INFO,
                    fn='',
                    lno=0,
                    msg=f"{action} операция выполнена",
                    args=(),
                    exc_info=None,
                    extra={
                        'action': action,
                        'username': username or 'anonymous',
                        'user_id': user_id,
                        'currency_code': currency_code or 'N/A',
                        'amount': float(amount) if amount is not None else 0.0,
                        'rate': rate or 0.0,
                        'base': base,
                        'result': 'OK' if success else 'ERROR',
                        **extra_context
                    }
                )
                logger.handle(log_record)

                # Для verbose режима логируем дополнительную информацию
                if verbose and extra_context:
                    logger.info(f"Контекст операции {action}: {extra_context}")

                return result

            except Exception as e:
                # Логируем ошибку
                log_record = logger.makeRecord(
                    name=logger.name,
                    level=logging.ERROR,
                    fn='',
                    lno=0,
                    msg=f"{action} операция завершилась ошибкой",
                    args=(),
                    exc_info=(type(e), e, e.__traceback__),
                    extra={
                        'action': action,
                        'username': username or 'anonymous',
                        'user_id': user_id,
                        'currency_code': currency_code or 'N/A',
                        'amount': float(amount) if amount is not None else 0.0,
                        'rate': rate or 0.0,
                        'base': base,
                        'result': 'ERROR',
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        **extra_context
                    }
                )
                logger.handle(log_record)

                # Пробрасываем исключение дальше
                raise

        return wrapper
    return decorator


# Специальные декораторы для конкретных действий
def log_buy(verbose: bool = False):
    """Декоратор для логирования операций покупки."""
    return log_action(action_name='BUY', verbose=verbose)


def log_sell(verbose: bool = False):
    """Декоратор для логирования операций продажи."""
    return log_action(action_name='SELL', verbose=verbose)


def log_register(verbose: bool = False):
    """Декоратор для логирования регистрации."""
    return log_action(action_name='REGISTER', verbose=verbose)


def log_login(verbose: bool = False):
    """Декоратор для логирования входа."""
    return log_action(action_name='LOGIN', verbose=verbose)
