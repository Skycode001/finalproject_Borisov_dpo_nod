#!/usr/bin/env python3
"""
ValutaTrade Hub - Торговая платформа для виртуального портфеля валют.
Основная точка входа в приложение.
"""

import sys

from valutatrade_hub.cli.interface import run_cli
from valutatrade_hub.logging_config import setup_logging


def main() -> None:
    """Основная функция приложения."""
    print("🚀 Запуск ValutaTrade Hub...")

    # Показать информацию о Parser Service
    print("📡 Parser Service: получение курсов с внешних API")
    print("   • CoinGecko API: криптовалюты (BTC, ETH, LTC, XRP, ADA, SOL, DOT)")
    print("   • ExchangeRate-API: фиатные валюты (EUR, GBP, RUB, JPY, CHF) - режим заглушки")
    print("   • Для реальных данных зарегистрируйтесь на exchangerate-api.com")
    print()

    # Инициализация системы логирования
    setup_logging(log_level="INFO", log_dir="logs", json_format=False)
    print("📝 Система логирования инициализирована")

    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем. До свидания!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Ошибка при запуске приложения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
