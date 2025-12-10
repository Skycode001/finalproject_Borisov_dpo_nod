"""
Модуль для планирования периодического обновления курсов.
"""

import threading
import time
from typing import Dict

from ..logging_config import get_logger
from .config import config  # <-- ИЗМЕНЕНИЕ: импортируем config
from .updater import RatesUpdater

logger = get_logger(__name__)


class RatesScheduler:
    """Планировщик периодического обновления курсов."""

    def __init__(self):
        self.updater = RatesUpdater()
        self.update_interval = config.UPDATE_INTERVAL  # <-- ИЗМЕНЕНИЕ: используем config
        self._scheduler_thread = None
        self._stop_event = threading.Event()
        self.is_running = False

    def start(self) -> None:
        """
        Запускает планировщик в отдельном потоке.
        """
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return

        logger.info(f"Запуск планировщика с интервалом {self.update_interval} секунд")

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        self.is_running = True

        logger.info("Планировщик запущен")

    def stop(self) -> None:
        """
        Останавливает планировщик.
        """
        if not self.is_running:
            logger.warning("Планировщик не запущен")
            return

        logger.info("Остановка планировщика...")
        self._stop_event.set()

        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

        self.is_running = False
        logger.info("Планировщик остановлен")

    def _run_scheduler(self) -> None:
        """
        Основной цикл планировщика.
        """
        logger.info("Цикл планировщика начат")

        while not self._stop_event.is_set():
            try:
                # Выполняем обновление
                self._perform_update()

                # Ждем указанный интервал или сигнал остановки
                logger.debug(f"Ожидание {self.update_interval} секунд до следующего обновления")
                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                # Ждем перед повторной попыткой
                time.sleep(min(60, self.update_interval))

    def _perform_update(self) -> None:
        """
        Выполняет одно обновление курсов.
        """
        try:
            logger.info("Запланированное обновление курсов...")
            self.updater.update_all_rates()
            logger.info("Запланированное обновление завершено")

        except Exception as e:
            logger.error(f"Ошибка при запланированном обновлении: {e}")

    def get_status(self) -> Dict:
        """
        Возвращает статус планировщика.

        Returns:
            Словарь со статусом.
        """
        return {
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "last_update": self.updater.last_update_time.isoformat()
                if self.updater.last_update_time else None,
            "thread_alive": self._scheduler_thread.is_alive()
                if self._scheduler_thread else False
        }

    def manual_update(self) -> Dict:
        """
        Выполняет ручное обновление вне расписания.

        Returns:
            Словарь с результатом обновления.
        """
        logger.info("Ручное обновление по запросу")
        return self.updater.update_all_rates()
