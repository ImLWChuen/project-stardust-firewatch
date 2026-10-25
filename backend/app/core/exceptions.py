class StardustException(Exception):
    """Base exception for all Project Stardust application errors."""
    pass

class ResourceNotFoundError(StardustException):
    """Raised when a requested resource cannot be found."""
    pass
