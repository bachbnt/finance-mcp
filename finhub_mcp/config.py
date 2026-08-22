# Copyright (c) 2026 bachbnt. All rights reserved.

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG: dict[str, Any] = {
    'vn_quote_sources': ['VCI', 'KBS', 'MSN'],
    'vn_intraday_sources': ['KBS', 'VCI', 'MSN'],
    'vn_listing_sources': ['VCI', 'KBS'],
    'vn_stock_sources': ['VCI', 'KBS'],
    'crypto_exchanges': ['binance', 'okx', 'bybit', 'kucoin', 'gate', 'mexc'],
    'futures_default_types': {
        'binance': 'future',
        'okx': 'swap',
        'bybit': 'swap',
        'kucoin': 'swap',
        'gate': 'swap',
        'mexc': 'swap',
    },
    'alert_store': 'alerts.json',
    'cache_ttl_seconds': {
        'ticker': 10,
        'history': 300,
        'market_overview': 60,
    },
}


class ConfigError(ValueError):
    """Raised when config.json exists but is invalid."""


def config_path() -> Path:
    configured = os.getenv('FINHUB_CONFIG')
    if configured:
        return Path(configured).expanduser()
    return BASE_DIR / 'config.json'


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)
    try:
        with open(path) as f:
            configured = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid config JSON at {path}: {e}") from e
    if not isinstance(configured, dict):
        raise ConfigError(f"Invalid config at {path}: root must be an object")
    return _merge(DEFAULT_CONFIG, configured)


def get_list(name: str) -> tuple[str, ...]:
    value = load_config().get(name)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigError(f"Invalid config value for {name}: expected a non-empty string list")
    return tuple(value)


def get_dict(name: str) -> dict[str, Any]:
    value = load_config().get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"Invalid config value for {name}: expected an object")
    return value


def get_alert_store_path() -> str:
    value = load_config().get('alert_store')
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("Invalid config value for alert_store: expected a non-empty string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)

