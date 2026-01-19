"""Custom exceptions."""


class BusinessException(Exception):
    """Business logic exception."""
    
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)


class ResourceNotFoundException(Exception):
    """Resource not found exception."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

