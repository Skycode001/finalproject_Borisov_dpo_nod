"""
Модуль для работы с хранилищем курсов валют.
Теперь с атомарной записью и новым форматом exchange_rates.json.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..logging_config import get_logger
from .config import EXCHANGE_RATES_FILE, RATES_CACHE_FILE

logger = get_logger(__name__)


class ExchangeRatesStorage:
    """Класс для работы с хранилищем курсов валют."""

    def __init__(self):
        self.exchange_rates_file = EXCHANGE_RATES_FILE
        self.rates_cache_file = RATES_CACHE_FILE
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Создает необходимые директории, если они не существуют."""
        os.makedirs(os.path.dirname(self.exchange_rates_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.rates_cache_file), exist_ok=True)
        os.makedirs("logs", exist_ok=True)

    def _generate_id(self, from_currency: str, to_currency: str, timestamp: str) -> str:
        """
        Генерирует уникальный ID для записи курса.

        Формат: <FROM>_<TO>_<ISO-UTC timestamp>
        Пример: BTC_USD_2025-10-10T12:00:00Z

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.
            timestamp: Временная метка в ISO формате.

        Returns:
            Уникальный ID записи.
        """
        # Нормализуем timestamp: заменяем пробелы и приводим к Z в конце если нужно
        normalized_timestamp = timestamp.replace(" ", "T").rstrip("Z") + "Z"

        # Формируем ID согласно требованиям
        return f"{from_currency.upper()}_{to_currency.upper()}_{normalized_timestamp}"

    def _atomic_write(self, file_path: str, data: Dict) -> bool:
        """
        Атомарная запись данных в JSON-файл.

        Создает временный файл, записывает в него данные,
        затем переименовывает в целевой файл.

        Args:
            file_path: Путь к целевому файлу.
            data: Данные для записи.

        Returns:
            True если запись успешна, False в противном случае.
        """
        try:
            # Создаем временный файл в той же директории
            temp_dir = os.path.dirname(file_path) or "."
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                dir=temp_dir,
                delete=False,
                encoding='utf-8'
            )
            temp_path = temp_file.name

            try:
                # Записываем данные во временный файл
                json.dump(data, temp_file, indent=2, ensure_ascii=False, default=str)
                temp_file.close()

                # Атомарно заменяем старый файл новым
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.backup_{uuid.uuid4().hex[:8]}"
                    os.rename(file_path, backup_path)
                    logger.debug(f"Создана резервная копия: {backup_path}")

                os.rename(temp_path, file_path)
                logger.debug(f"Файл {file_path} успешно обновлен атомарно")
                return True

            except Exception as e:
                # Очищаем временный файл в случае ошибки
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e

        except Exception as e:
            logger.error(f"Ошибка атомарной записи в {file_path}: {e}")
            return False

    def load_exchange_rates(self) -> Dict:
        """
        Загружает исторические курсы из файла в новом формате.

        Returns:
            Словарь с историческими курсами в формате {id: record}.
        """
        try:
            if os.path.exists(self.exchange_rates_file):
                with open(self.exchange_rates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"Загружены исторические курсы из {self.exchange_rates_file}")
                return data
            else:
                logger.debug(f"Файл исторических курсов не найден: {self.exchange_rates_file}")
                return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка загрузки исторических курсов: {e}")
            return {}

    def save_exchange_rate_record(self, record: Dict) -> bool:
        """
        Сохраняет одну запись курса в исторические данные.

        Args:
            record: Запись курса в новом формате с обязательным полем 'id'.
                   Пример:
                   {
                     "id": "BTC_USD_2025-10-10T12:00:00Z",
                     "from_currency": "BTC",
                     "to_currency": "USD",
                     "rate": 59337.21,
                     "timestamp": "2025-10-10T12:00:00Z",
                     "source": "CoinGecko",
                     "meta": {...}
                   }

        Returns:
            True если сохранение успешно, False в противном случае.
        """
        try:
            # Проверяем обязательные поля
            required_fields = ['id', 'from_currency', 'to_currency', 'rate', 'timestamp', 'source']
            for field in required_fields:
                if field not in record:
                    raise ValueError(f"Отсутствует обязательное поле: {field}")

            # Загружаем существующие данные
            existing_data = self.load_exchange_rates()

            # Добавляем новую запись (или заменяем существующую с таким же ID)
            record_id = record['id']
            existing_data[record_id] = record

            # Атомарно сохраняем обновленные данные
            return self._atomic_write(self.exchange_rates_file, existing_data)

        except Exception as e:
            logger.error(f"Ошибка сохранения записи курса: {e}")
            return False

    def create_exchange_rate_record(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        source: str,
        meta: Optional[Dict] = None
    ) -> Dict:
        """
        Создает новую запись курса валюты в требуемом формате.

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.
            rate: Курс обмена.
            source: Источник данных (например, "CoinGecko").
            meta: Дополнительные метаданные.

        Returns:
            Словарь с записью курса в новом формате.
        """
        # Валидация валютных кодов
        from_currency = from_currency.upper().strip()
        to_currency = to_currency.upper().strip()

        if not (2 <= len(from_currency) <= 5 and from_currency.isalpha()):
            raise ValueError(f"Некорректный код валюты: {from_currency}")
        if not (2 <= len(to_currency) <= 5 and to_currency.isalpha()):
            raise ValueError(f"Некорректный код валюты: {to_currency}")

        # Валидация курса
        if not isinstance(rate, (int, float)) or rate <= 0:
            raise ValueError(f"Некорректный курс: {rate}")

        # Текущее время в ISO формате UTC
        timestamp = datetime.now().isoformat() + "Z"

        # Генерируем ID
        record_id = self._generate_id(from_currency, to_currency, timestamp)

        # Создаем запись
        record = {
            "id": record_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": float(rate),
            "timestamp": timestamp,
            "source": source,
            "meta": meta or {}
        }

        return record

    def update_rates_cache(self, rates_data: Dict) -> bool:
        """
        Обновляет кеш курсов для основного сервиса.

        Args:
            rates_data: Актуальные курсы валют в формате:
                       {"BTC": {"rate": 50000, "source": "...", ...}, ...}

        Returns:
            True если обновление успешно, False в противном случае.
        """
        try:
            # Формируем данные для кеша в формате rates.json
            cache_data = {
                "source": "ParserService",
                "last_refresh": datetime.now().isoformat() + "Z"
            }

            # Добавляем курсы в формате пар валют
            for currency, rate_info in rates_data.items():
                if currency != "USD":  # Пропускаем USD, так как он базовая валюта
                    pair_key = f"{currency}_USD"
                    cache_data[pair_key] = {
                        "rate": rate_info["rate"],
                        "updated_at": rate_info.get("timestamp", rate_info.get("updated_at", datetime.now().isoformat()))
                    }

            # Атомарно сохраняем кеш
            return self._atomic_write(self.rates_cache_file, cache_data)

        except Exception as e:
            logger.error(f"Ошибка обновления кеша курсов: {e}")
            return False

    def get_latest_rates(self) -> Dict:
        """
        Возвращает последние курсы из исторических данных.

        Returns:
            Словарь с последними курсами для каждой валюты.
        """
        try:
            historical_data = self.load_exchange_rates()
            latest_rates = {}

            # Группируем записи по паре валют
            rates_by_pair = {}
            for _record_id, record in historical_data.items():
                pair_key = f"{record['from_currency']}_{record['to_currency']}"

                # Находим самую свежую запись для каждой пары
                if pair_key not in rates_by_pair:
                    rates_by_pair[pair_key] = record
                else:
                    # Сравниваем временные метки
                    current_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    existing_time = datetime.fromisoformat(rates_by_pair[pair_key]['timestamp'].replace('Z', '+00:00'))

                    if current_time > existing_time:
                        rates_by_pair[pair_key] = record

            # Конвертируем в формат для использования в других модулях
            for _pair_key, record in rates_by_pair.items():
                from_currency = record['from_currency']
                latest_rates[from_currency] = {
                    "rate": record["rate"],
                    "timestamp": record["timestamp"],
                    "source": record["source"],
                    "meta": record.get("meta", {})
                }

            return latest_rates

        except Exception as e:
            logger.error(f"Ошибка получения последних курсов: {e}")
            return {}

    def get_rate_history(
        self,
        from_currency: str,
        to_currency: str = "USD",
        limit: int = 10
    ) -> List[Dict]:
        """
        Возвращает историю курсов для указанной пары валют.

        Args:
            from_currency: Исходная валюта.
            to_currency: Целевая валюта.
            limit: Максимальное количество записей.

        Returns:
            Список исторических записей курса, отсортированных по времени (новые первыми).
        """
        try:
            historical_data = self.load_exchange_rates()
            history = []

            # Фильтруем записи по паре валют
            for _record_id, record in historical_data.items():
                if (record['from_currency'].upper() == from_currency.upper() and
                    record['to_currency'].upper() == to_currency.upper()):
                    history.append(record)

            # Сортируем по времени (новые первыми)
            history.sort(
                key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')),
                reverse=True
            )

            # Ограничиваем количество
            return history[:limit]

        except Exception as e:
            logger.error(f"Ошибка получения истории курса для {from_currency}→{to_currency}: {e}")
            return []

    def cleanup_old_records(self, max_age_days: int = 30) -> int:
        """
        Удаляет старые записи из исторических данных.

        Args:
            max_age_days: Максимальный возраст записей в днях.

        Returns:
            Количество удаленных записей.
        """
        try:
            historical_data = self.load_exchange_rates()
            if not historical_data:
                return 0

            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            deleted_count = 0
            records_to_keep = {}

            for record_id, record in historical_data.items():
                try:
                    record_date = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    if record_date >= cutoff_date:
                        records_to_keep[record_id] = record
                    else:
                        deleted_count += 1
                except (ValueError, KeyError):
                    # Если не удалось разобрать дату, оставляем запись
                    records_to_keep[record_id] = record

            # Сохраняем очищенные данные
            if self._atomic_write(self.exchange_rates_file, records_to_keep):
                logger.info(f"Очистка исторических данных: удалено {deleted_count} старых записей")
                return deleted_count
            else:
                return 0

        except Exception as e:
            logger.error(f"Ошибка очистки старых записей: {e}")
            return 0
