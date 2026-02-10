class TransientError(Exception):
    """
    Exception raised when a temporary error occurs. The message will be requeued.
    """
    pass

class FatalError(Exception):
    """
    Exception raised when a fatal error occurs. The message will be dropped.
    """
    pass

class ExpectedRetry(Exception):
    """
    Exception raised when we intentionally want to retry the message.
    """
    pass