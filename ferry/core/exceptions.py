class InternalServerError(Exception):
    """Internal Server Error."""

    def __init__(self, message: str) -> None:
        self.message = message


class ConflictError(Exception):
    """Conflicting data."""

    def __init__(self, message: str) -> None:
        self.message = message
