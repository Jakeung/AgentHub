class BusinessError(Exception):
    """Base business error exception."""

    def __init__(self, code: int = -1, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(message)


class ValidationError(BusinessError):
    """Validation error (code 400)."""

    def __init__(self, message: str):
        super().__init__(code=400, message=message)


class AuthenticationError(BusinessError):
    """Authentication error (code 401)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(code=401, message=message)


class PermissionError(BusinessError):
    """Permission denied error (code 403)."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(code=403, message=message)


class NotFoundError(BusinessError):
    """Resource not found error (code 404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(code=404, message=message)


class ConflictError(BusinessError):
    """Conflict error (code 409)."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(code=409, message=message)
