#!/usr/bin/env python3
"""
ValutaTrade Hub - Торговая платформа для виртуального портфеля валют.
Основная точка входа в приложение.
"""

import sys

from valutatrade_hub.cli.interface import run_cli


def main() -> None:
    """Основная функция приложения."""
    print("🚀 Запуск ValutaTrade Hub...")

    try:
        run_cli()
    except Exception as e:
        print(f"❌ Ошибка при запуске приложения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
