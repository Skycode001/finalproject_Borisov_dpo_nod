class ValutaTradeError(Exception):
    """Базовый класс для всех исключений проекта."""
    pass


class CurrencyNotFoundError(ValutaTradeError):
    """Исключение, возникающее когда валюта не найдена."""
    pass


class InsufficientFundsError(ValutaTradeError):
    """Исключение, возникающее когда недостаточно средств."""
    pass


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
