import json
import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_dir: str = "logs", json_format: bool = False) -> None:
    """
    Настраивает систему логирования.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Директория для хранения логов.
        json_format: Использовать ли JSON формат для логов действий.
    """
    # Создаем директорию для логов если её нет
    os.makedirs(log_dir, exist_ok=True)

    # Базовый уровень логирования
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Настройка root логгера
    logger = logging.getLogger()
    logger.setLevel(level)

    # Очищаем существующие обработчики
    logger.handlers.clear()

    # 1. КОНСОЛЬНЫЙ обработчик (простой формат для вывода в терминал)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. ОБЩИЙ файловый обработчик (простой формат для всех логов)
    log_file = os.path.join(log_dir, f"valutatrade_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 3. ОБРАБОТЧИК ДЛЯ АКТИВНОСТЕЙ (специальный формат только для действий)
    actions_file = os.path.join(log_dir, "actions.log")
    actions_handler = logging.handlers.RotatingFileHandler(
        actions_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    actions_handler.setLevel(logging.INFO)

    if json_format:
        # JSON формат для структурированных логов действий
        class JsonActionsFormatter(logging.Formatter):
            def format(self, record):
                # Пропускаем записи без действия
                if not hasattr(record, 'action'):
                    return ""

                log_data = {
                    "timestamp": datetime.now().isoformat(),
                    "level": record.levelname,
                    "action": getattr(record, 'action', 'UNKNOWN'),
                    "username": getattr(record, 'username', 'anonymous'),
                    "user_id": getattr(record, 'user_id', None),
                    "currency_code": getattr(record, 'currency_code', 'N/A'),
                    "amount": getattr(record, 'amount', 0.0),
                    "rate": getattr(record, 'rate', 0.0),
                    "base": getattr(record, 'base', 'USD'),
                    "result": getattr(record, 'result', 'INFO'),
                    "error_type": getattr(record, 'error_type', ''),
                    "error_message": getattr(record, 'error_message', ''),
                    "message": record.getMessage(),
                }

                # Добавляем исключения если есть
                if record.exc_info:
                    log_data['exception'] = self.formatException(record.exc_info)

                return json.dumps(log_data, ensure_ascii=False)

        actions_formatter = JsonActionsFormatter()
    else:
        # Текстовый формат для действий с безопасной обработкой полей
        class TextActionsFormatter(logging.Formatter):
            def __init__(self):
                super().__init__(
                    fmt="%(levelname)s %(asctime)s action=%(action)s user=%(username)s "
                        "currency=%(currency_code)s amount=%(amount).4f rate=%(rate).2f "
                        "base=%(base)s result=%(result)s%(error_info)s",
                    datefmt="%Y-%m-%dT%H:%M:%S"
                )

            def format(self, record):
                # Пропускаем записи без действия
                if not hasattr(record, 'action'):
                    return ""

                # Устанавливаем значения по умолчанию для отсутствующих полей
                defaults = {
                    'username': 'anonymous',
                    'currency_code': 'N/A',
                    'amount': 0.0,
                    'rate': 0.0,
                    'base': 'USD',
                    'result': 'INFO',
                    'error_type': '',
                    'error_message': ''
                }

                for field, default in defaults.items():
                    if not hasattr(record, field):
                        setattr(record, field, default)

                # Формируем строку с ошибками если есть
                error_info = ""
                error_type = getattr(record, 'error_type', '')
                error_message = getattr(record, 'error_message', '')

                if error_type:
                    error_info = f" error_type={error_type}"
                if error_message:
                    error_info += f" error_message='{error_message}'"

                record.error_info = error_info

                return super().format(record)

        actions_formatter = TextActionsFormatter()

    actions_handler.setFormatter(actions_formatter)
    # Только логи с действиями (с полем 'action')
    actions_handler.addFilter(lambda record: hasattr(record, 'action') and getattr(record, 'action', ''))
    logger.addHandler(actions_handler)

    # 4. ОБРАБОТЧИК ДЛЯ ОШИБОК
    error_file = os.path.join(log_dir, "errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Логируем начало сессии (пойдут в общие логи, НЕ в actions.log)
    logging.info("=== Начало сессии логирования ===")
    logging.info(f"Уровень логирования: {log_level}")
    logging.info(f"Директория логов: {os.path.abspath(log_dir)}")
    logging.info(f"Формат логов действий: {'JSON' if json_format else 'Текстовый'}")


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.

    Args:
        name: Имя логгера (обычно __name__ модуля).

    Returns:
        logging.Logger: Сконфигурированный логгер.
    """
    return logging.getLogger(name)
