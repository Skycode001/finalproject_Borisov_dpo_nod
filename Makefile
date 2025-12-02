# Создание виртуального окружения
install:
	python3 -m venv .venv
	@echo "Виртуальное окружение создано. Для активации выполните:"
	@echo "source .venv/bin/activate"
	@echo "Затем установите зависимости:"
	@echo "pip install poetry"
	@echo "poetry install"

# Запуск проекта
project:
	python3 -m main

# Альтернативная команда database (как в задании)
database:
	python3 -m main

# Запуск тестов (будет позже)
test:
	python3 -m pytest tests/ -v

# Проверка кода Ruff
lint:
	ruff check .

# Автоисправление ошибок
lint-fix:
	ruff check --fix .

# Форматирование кода
format:
	ruff format .

# Команды для сборки (если понадобятся)
build:
	python3 setup.py sdist bdist_wheel

publish:
	twine check dist/*

package-install:
	pip install dist/*.whl

# Очистка
clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf valutatrade_hub/__pycache__
	rm -rf valutatrade_hub/core/__pycache__
	rm -rf valutatrade_hub/cli/__pycache__
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf *.log

# Умная активация venv
activate:
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		echo "Виртуальное окружение уже активировано: $$VIRTUAL_ENV"; \
	else \
		echo "Для активации виртуального окружения выполните:"; \
		echo "source .venv/bin/activate"; \
		echo "Или:"; \
		echo "make activate-now"; \
	fi

# Справка
help:
	@echo "Доступные команды:"
	@echo "  make install   - Создать виртуальное окружение"
	@echo "  make project   - Запустить проект (main.py)"
	@echo "  make database  - Запустить проект (альтернативная команда)"
	@echo "  make test      - Запустить тесты"
	@echo "  make lint      - Проверить код на ошибки"
	@echo "  make lint-fix  - Автоисправление ошибок"
	@echo "  make format    - Отформатировать код"
	@echo "  make build     - Собрать пакет"
	@echo "  make publish   - Проверить пакет перед публикацией"
	@echo "  make package-install - Установить локальный пакет"
	@echo "  make clean     - Полная очистка"
	@echo "  make activate  - Помощь по активации venv"
	@echo "  make help      - Показать эту справку"