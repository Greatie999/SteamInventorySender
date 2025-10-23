from tenacity import RetryCallState


class SteamParseError(Exception):
    pass


def handle_retry_error(retry_state: RetryCallState):
    exception = retry_state.outcome.exception()
    raise SteamParseError(
        f"SteamParse request failed after {retry_state.attempt_number} attempts"
    ) from exception


def error_retry_policy(retry_state: RetryCallState) -> bool:
    exc = retry_state.outcome.exception()
    if exc is None or isinstance(exc, SteamParseError):
        return False
    return True
