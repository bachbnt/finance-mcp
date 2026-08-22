# Copyright (c) 2026 bachbnt. All rights reserved.

import json
from typing import Any

from finhub_mcp.config import ConfigError
from finhub_mcp.exceptions import ProviderFallbackError


def success(data: Any, **meta: Any) -> str:
    """Return a successful MCP response as a JSON string."""
    payload = {'ok': True, 'data': data}
    if meta:
        payload['meta'] = meta
    return json.dumps(payload, ensure_ascii=False, indent=2)


def error(message: Any, **meta: Any) -> str:
    """Return an error MCP response as a JSON string."""
    if isinstance(message, ProviderFallbackError):
        meta.setdefault('error_type', 'provider_failure')
        meta.setdefault('retryable', message.retryable)
        meta.setdefault('provider_errors', message.provider_errors)
    elif isinstance(message, ConfigError):
        meta.setdefault('error_type', 'config')
        meta.setdefault('retryable', False)
    elif isinstance(message, ValueError):
        meta.setdefault('error_type', 'validation')
        meta.setdefault('retryable', False)

    payload = {'ok': False, 'error': str(message)}
    if meta:
        payload['meta'] = meta
    return json.dumps(payload, ensure_ascii=False, indent=2)


def invalid(message: str) -> str:
    """Return a validation error response."""
    return error(message, error_type='validation')
