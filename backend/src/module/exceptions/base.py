"""Base exception classes for Auto_Bangumi."""


class AutoBangumiError(Exception):
    """Base exception for all Auto_Bangumi errors."""

    def __init__(self, message: str = "", **kwargs):
        self.message = message
        self.extra_info = kwargs
        super().__init__(self.message)

    def __str__(self):
        if self.extra_info:
            extra = ", ".join(f"{k}={v}" for k, v in self.extra_info.items())
            return f"{self.message} ({extra})"
        return self.message
