import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Настраивает систему логирования.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Директория для хранения логов.
    """
    # Создаем директорию для логов если её нет
    os.makedirs(log_dir, exist_ok=True)

    # Формат логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Базовый уровень логирования
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Настройка root логгера
    logger = logging.getLogger()
    logger.setLevel(level)

    # Очищаем существующие обработчики
    logger.handlers.clear()

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик с ротацией по дням
    log_file = os.path.join(log_dir, f"valutatrade_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Отдельный обработчик для ошибок
    error_file = os.path.join(log_dir, "errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(log_format, date_format)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Логируем начало сессии
    logging.info("=== Начало сессии логирования ===")
    logging.info(f"Уровень логирования: {log_level}")
    logging.info(f"Директория логов: {os.path.abspath(log_dir)}")


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.

    Args:
        name: Имя логгера (обычно __name__ модуля).

    Returns:
        logging.Logger: Сконфигурированный логгер.
    """
    return logging.getLogger(name)
