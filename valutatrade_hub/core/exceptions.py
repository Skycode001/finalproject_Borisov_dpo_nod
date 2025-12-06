class ValutaTradeError(Exception):
    """Базовый класс для всех исключений проекта."""
    pass


class CurrencyNotFoundError(ValutaTradeError):
    """Исключение, возникающее когда валюта не найдена."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(ValutaTradeError):
    """Исключение, возникающее когда недостаточно средств."""

    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(f"Недостаточно средств: доступно {available:.4f} {code}, требуется {required:.4f} {code}")


class ApiRequestError(ValutaTradeError):
    """Исключение, возникающее при ошибке внешнего API."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class InvalidCurrencyError(ValutaTradeError):
    """Исключение, возникающее при невалидной валюте."""
    pass


class InvalidAmountError(ValutaTradeError):
    """Исключение, возникающее при невалидной сумме."""
    pass


class UserNotAuthenticatedError(ValutaTradeError):
    """Исключение, возникающее когда пользователь не аутентифицирован."""
    pass


class PortfolioNotFoundError(ValutaTradeError):
    """Исключение, возникающее когда портфель не найден."""
    pass


class RateUnavailableError(ValutaTradeError):
    """Исключение, возникающее когда курс недоступен."""
    pass


class DatabaseError(ValutaTradeError):
    """Исключение, возникающее при ошибках базы данных."""
    pass


class ValidationError(ValutaTradeError):
    """Исключение, возникающее при ошибках валидации."""
    pass
