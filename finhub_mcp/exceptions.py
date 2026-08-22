# Copyright (c) 2026 bachbnt. All rights reserved.


class ProviderFallbackError(RuntimeError):
    """Raised when all fallback providers fail."""

    def __init__(self, message: str, provider_errors: dict[str, str], retryable: bool = True):
        super().__init__(message)
        self.provider_errors = provider_errors
        self.retryable = retryable

