class InternalServerError(Exception):
    """Internal Server Error."""

    def __init__(self, message: str) -> None:
        self.message = message


class ConflictError(Exception):
    """Conflicting data."""

    def __init__(self, message: str) -> None:
        self.message = message


class ForbiddenError(Exception):
    """Forbidden action."""

    def __init__(self, message: str = "You don't have permission to perform that action") -> None:
        self.message = message
