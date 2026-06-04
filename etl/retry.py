from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import Config


def with_io_retry(func):
    return retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((IOError, ConnectionError, TimeoutError))
    )(func)
