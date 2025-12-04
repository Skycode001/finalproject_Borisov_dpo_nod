import functools
import logging
from datetime import datetime
from typing import Any, Callable


def log_action(action_name: str = None, log_args: bool = True, log_result: bool = True):
    """
    Декоратор для логирования действий.

    Args:
        action_name: Название действия (если None, используется имя функции).
        log_args: Логировать ли аргументы функции.
        log_result: Логировать ли результат функции.

    Returns:
        Декоратор функции.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger(func.__module__)
            action = action_name or func.__name__

            # Логируем начало действия
            start_time = datetime.now()
            log_message = f"Начало действия: {action}"

            if log_args and (args or kwargs):
                args_str = ", ".join([str(arg) for arg in args[1:]])  # Пропускаем self
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                all_args = ", ".join(filter(None, [args_str, kwargs_str]))
                if all_args:
                    log_message += f" | Аргументы: {all_args}"

            logger.info(log_message)

            try:
                # Выполняем функцию
                result = func(*args, **kwargs)

                # Логируем успешное завершение
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                success_message = f"Завершено действие: {action} | Время: {duration:.3f} сек"

                if log_result and result is not None:
                    result_str = str(result)
                    if len(result_str) > 100:  # Обрезаем длинные результаты
                        result_str = result_str[:97] + "..."
                    success_message += f" | Результат: {result_str}"

                logger.info(success_message)

                return result

            except Exception as e:
                # Логируем ошибку
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                error_message = (
                    f"Ошибка в действии: {action} | "
                    f"Время: {duration:.3f} сек | "
                    f"Ошибка: {type(e).__name__}: {str(e)}"
                )

                logger.error(error_message, exc_info=True)
                raise

        return wrapper
    return decorator


def confirm_action(prompt: str = None):
    """
    Декоратор для запроса подтверждения действия.

    Args:
        prompt: Сообщение для подтверждения.

    Returns:
        Декоратор функции.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Для CLI команд проверяем, есть ли self и является ли он CLI объектом
            if args and hasattr(args[0], 'user_manager'):
                # Это команда CLI, пропускаем подтверждение
                return func(*args, **kwargs)

            # Для остальных случаев - запрашиваем подтверждение
            if prompt:
                print(f"\n{prompt}")
            else:
                print(f"\nПодтвердите действие: {func.__name__}")

            response = input("Продолжить? (y/n): ").strip().lower()

            if response not in ['y', 'yes', 'да', 'д']:
                print("Действие отменено.")
                return None

            return func(*args, **kwargs)

        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 300):
    """
    Декоратор для кэширования результатов функций.

    Args:
        ttl_seconds: Время жизни кэша в секундах.

    Returns:
        Декоратор функции.
    """
    def decorator(func: Callable) -> Callable:
        cache = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Создаем ключ кэша на основе аргументов
            key = (args, tuple(sorted(kwargs.items())))

            current_time = datetime.now().timestamp()

            # Проверяем, есть ли результат в кэше и не устарел ли он
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    logging.getLogger(func.__module__).debug(
                        f"Кэшированный результат для {func.__name__}"
                    )
                    return result

            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)

            return result

        return wrapper
    return decorator
