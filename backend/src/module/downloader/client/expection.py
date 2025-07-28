class AuthorizationError(Exception):
    """认证错误异常，包含详细的错误信息"""

    def __init__(
        self,
        function_name: str = "",
        message: str = "",
        status_code: int = 0,
        response_text: str = "",
    ):
        self.function_name = function_name
        self.status_code = status_code
        self.response_text = response_text

        if message:
            self.message = message
        elif function_name:
            self.message = f"Authorization failed for function: {function_name}"
        else:
            self.message = "Authorization failed"

        super().__init__(self.message)

    def __str__(self):
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.response_text:
            parts.append(f"Response: {self.response_text}")
        return " | ".join(parts)
