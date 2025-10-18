"""Retry configuration and exponential backoff utilities.

Provides configurable retry strategies with exponential backoff for error recovery.
"""

import random
from dataclasses import dataclass, field
from typing import Callable, Type


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay_ms: Initial delay in milliseconds (default: 1000)
        max_delay_ms: Maximum delay cap in milliseconds (default: 60000)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        jitter_factor: Jitter range as fraction of delay (default: 0.1 = ±10%)
        retry_on: Exception types to retry on (default: TimeoutError, ConnectionError)
        skip_on: Exception types to never retry (default: ValidationError)

    Example:
        ```python
        config = RetryConfig(
            max_attempts=3,
            initial_delay_ms=1000,
            backoff_multiplier=2.0
        )

        for attempt in range(1, config.max_attempts + 1):
            try:
                result = await execute_task()
                break
            except TimeoutError:
                if attempt < config.max_attempts:
                    delay = calculate_retry_delay(attempt, config)
                    await asyncio.sleep(delay / 1000)
        ```
    """

    max_attempts: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1

    # Error type filtering
    retry_on: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (TimeoutError, ConnectionError)
    )
    skip_on: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (ValueError, AssertionError)
    )


@dataclass
class ErrorRecoveryConfig:
    """Global error recovery configuration.

    Attributes:
        tool_execution_timeout_s: Timeout for tool execution (default: 30s)
        api_call_timeout_s: Timeout for API calls (default: 30s)
        enable_auto_recovery: Enable automatic recovery attempts (default: True)
        log_all_errors: Log all errors encountered (default: True)
        log_retry_attempts: Log retry attempts (default: True)

    Example:
        ```python
        config = ErrorRecoveryConfig.from_env()
        config.tool_execution_timeout_s = 60  # Override for this session
        ```
    """

    max_attempts: int = 3
    initial_backoff_ms: int = 1000
    max_backoff_ms: int = 60000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1

    # Error type settings
    retry_on_timeout: bool = True
    retry_on_ratelimit: bool = True
    retry_on_connection_error: bool = True

    # Timeout settings
    tool_execution_timeout_s: int = 30
    api_call_timeout_s: int = 30

    # Recovery strategies
    enable_auto_recovery: bool = True
    enable_user_confirmation: bool = False

    # Logging
    log_all_errors: bool = True
    log_retry_attempts: bool = True

    @classmethod
    def from_env(cls) -> "ErrorRecoveryConfig":
        """Load configuration from environment variables.

        Environment variables:
        - RETRY_MAX_ATTEMPTS: Max retry attempts (default: 3)
        - RETRY_INITIAL_MS: Initial backoff in ms (default: 1000)
        - RETRY_MAX_MS: Max backoff in ms (default: 60000)
        - RETRY_MULTIPLIER: Backoff multiplier (default: 2.0)
        - TOOL_TIMEOUT_S: Tool execution timeout (default: 30)
        - API_TIMEOUT_S: API call timeout (default: 30)
        - ENABLE_AUTO_RECOVERY: Auto recovery enabled (default: true)

        Returns:
            ErrorRecoveryConfig with environment settings
        """
        import os

        def get_bool(key: str, default: bool) -> bool:
            val = os.getenv(key, "").lower()
            if val in ("true", "1", "yes"):
                return True
            if val in ("false", "0", "no"):
                return False
            return default

        return cls(
            max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            initial_backoff_ms=int(os.getenv("RETRY_INITIAL_MS", "1000")),
            max_backoff_ms=int(os.getenv("RETRY_MAX_MS", "60000")),
            backoff_multiplier=float(os.getenv("RETRY_MULTIPLIER", "2.0")),
            tool_execution_timeout_s=int(os.getenv("TOOL_TIMEOUT_S", "30")),
            api_call_timeout_s=int(os.getenv("API_TIMEOUT_S", "30")),
            enable_auto_recovery=get_bool("ENABLE_AUTO_RECOVERY", True),
        )


def calculate_retry_delay(
    attempt: int,
    config: RetryConfig | ErrorRecoveryConfig,
) -> int:
    """Calculate delay in milliseconds for retry attempt.

    Uses exponential backoff with jitter to prevent thundering herd:
    - Base delay = initial_delay_ms * (multiplier ^ (attempt - 1))
    - Jitter = ±(delay * jitter_factor)
    - Result = max(initial_delay, min(max_delay, base_delay + jitter))

    Args:
        attempt: 1-based attempt number
        config: RetryConfig or ErrorRecoveryConfig

    Returns:
        Delay in milliseconds

    Example:
        ```python
        config = RetryConfig(initial_delay_ms=1000, backoff_multiplier=2.0)

        calculate_retry_delay(1, config)  # ~1000ms
        calculate_retry_delay(2, config)  # ~2000ms ±200ms
        calculate_retry_delay(3, config)  # ~4000ms ±400ms
        calculate_retry_delay(4, config)  # ~8000ms ±800ms (capped)
        ```
    """
    # Get config values
    initial_delay = (
        config.initial_delay_ms
        if isinstance(config, RetryConfig)
        else config.initial_backoff_ms
    )
    max_delay = (
        config.max_delay_ms
        if isinstance(config, RetryConfig)
        else config.max_backoff_ms
    )
    multiplier = config.backoff_multiplier
    jitter = config.jitter_factor

    # Exponential calculation
    delay = initial_delay * (multiplier ** (attempt - 1))

    # Cap at maximum
    delay = min(delay, max_delay)

    # Add jitter (±percentage)
    jitter_range = delay * jitter
    jitter_value = random.uniform(-jitter_range, jitter_range)
    delay = max(initial_delay, delay + jitter_value)

    return int(delay)


def should_retry(
    error: Exception,
    config: RetryConfig,
) -> bool:
    """Determine if error should trigger retry.

    Checks error type against retry and skip lists:
    1. If error type in skip_on tuple → always False (never retry)
    2. If error type in retry_on tuple → True (should retry)
    3. Otherwise → False (don't retry unknown errors)

    Args:
        error: Exception instance to check
        config: RetryConfig with type filters

    Returns:
        True if should retry, False otherwise

    Example:
        ```python
        config = RetryConfig(
            retry_on=(TimeoutError, ConnectionError),
            skip_on=(ValueError, ValidationError)
        )

        should_retry(TimeoutError("..."), config)      # True
        should_retry(ConnectionError("..."), config)   # True
        should_retry(ValueError("..."), config)        # False
        should_retry(RuntimeError("..."), config)      # False
        ```
    """
    # Never retry configured skip types
    if isinstance(error, config.skip_on):
        return False

    # Retry configured types
    if isinstance(error, config.retry_on):
        return True

    # Default: don't retry unknown errors
    return False


def get_retry_after_ms(error: Exception) -> int | None:
    """Extract retry-after hint from error if available.

    Some APIs (like OpenAI) include retry-after information in errors.
    This function attempts to extract and parse that information.

    Args:
        error: Exception that may contain retry-after info

    Returns:
        Milliseconds to wait before retry, or None if not available

    Example:
        ```python
        try:
            await openai_call()
        except RateLimitError as e:
            delay = get_retry_after_ms(e)  # e.g., 5000
            if delay:
                await asyncio.sleep(delay / 1000)
        ```
    """
    # Check for retry_after_ms attribute (custom)
    if hasattr(error, "retry_after_ms"):
        return int(error.retry_after_ms)

    # Check for retry_after seconds (standard HTTP)
    if hasattr(error, "retry_after"):
        return int(error.retry_after * 1000)

    # Check for x_request_id or similar (may be in response)
    if hasattr(error, "response") and hasattr(error.response, "headers"):
        retry_after = error.response.headers.get("retry-after")
        if retry_after:
            try:
                # Could be seconds or HTTP date
                return int(float(retry_after) * 1000)
            except (ValueError, TypeError):
                pass

    return None


# Predefined retry configurations for common scenarios

FAST_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay_ms=100,
    max_delay_ms=1000,
    backoff_multiplier=2.0,
)
"""Fast retry for quick operations (e.g., network glitches)."""

STANDARD_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay_ms=1000,
    max_delay_ms=30000,
    backoff_multiplier=2.0,
)
"""Standard retry for typical operations."""

SLOW_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay_ms=2000,
    max_delay_ms=120000,
    backoff_multiplier=2.0,
)
"""Slow retry for long-running operations."""

RATELIMIT_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay_ms=5000,
    max_delay_ms=60000,
    backoff_multiplier=3.0,
)
"""Special config for rate limit errors (longer waits)."""
