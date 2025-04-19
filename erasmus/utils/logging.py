from loguru import logger
import time
from functools import wraps

def timeit(func):  # pragma: no cover
    """
    Decorator that logs the execution time of the decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__qualname__} executed in {elapsed:.6f}s")
        return result
    return wrapper
