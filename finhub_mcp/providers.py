# Copyright (c) 2026 bachbnt. All rights reserved.

import contextlib
import importlib
import io
import logging
from datetime import datetime, timezone

from finhub_mcp.config import get_dict, get_list
from finhub_mcp.exceptions import ProviderFallbackError

VN_QUOTE_SOURCES = get_list('vn_quote_sources')
VN_INTRADAY_SOURCES = get_list('vn_intraday_sources')
VN_LISTING_SOURCES = get_list('vn_listing_sources')
VN_STOCK_SOURCES = get_list('vn_stock_sources')
SUPPORTED_EXCHANGES = get_list('crypto_exchanges')
FUTURES_DEFAULT_TYPES = get_dict('futures_default_types')


def quiet(fn, *args, **kwargs):
    """Call fn while suppressing stdout/stderr noise from upstream libraries."""
    buf = io.StringIO()
    previous_disable = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            return fn(*args, **kwargs)
    finally:
        logging.disable(previous_disable)


def silent_import(module: str, name: str):
    """Import a symbol without leaking banners to MCP stdout."""
    buf = io.StringIO()
    previous_disable = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            module_obj = importlib.import_module(module)
        return getattr(module_obj, name)
    finally:
        logging.disable(previous_disable)


def provider_order(value: str, defaults: tuple[str, ...], label: str) -> list[str]:
    """Build a provider fallback order from 'auto' or a comma-separated list."""
    if value is None or value.strip().lower() in {'auto', 'fallback', 'any'}:
        parts = defaults
    else:
        parts = tuple(part.strip() for part in value.split(',') if part.strip())

    allowed = {item.lower(): item for item in defaults}
    order = []
    for part in parts:
        key = part.lower()
        if key not in allowed:
            raise ValueError(f"Unsupported {label}: {part}. Choose from: auto, {', '.join(defaults)}")
        canonical = allowed[key]
        if canonical not in order:
            order.append(canonical)
    if not order:
        raise ValueError(f"No {label} providers configured")
    return order


def first_success(providers: list[str], fn, empty_msg: str = 'no data'):
    """Run fn(provider) until one provider returns a non-empty result."""
    errors = {}
    for provider in providers:
        try:
            result = fn(provider)
            is_empty = getattr(result, 'empty', None)
            if is_empty is True or (is_empty is None and hasattr(result, '__len__') and len(result) == 0):
                errors[provider] = empty_msg
                continue
            return provider, result
        except Exception as e:
            errors[provider] = str(e)
    details = '; '.join(f"{provider}: {message}" for provider, message in errors.items())
    raise ProviderFallbackError(f"All providers failed ({details})", errors)


def fallback_used(provider: str, providers: list[str]) -> bool:
    return len(providers) > 1 and provider != providers[0]


def vn_quote(symbol: str, source: str = 'VCI'):
    Quote = silent_import('vnstock.api.quote', 'Quote')
    return quiet(Quote, symbol=symbol.upper(), source=source)


def vn_stock(symbol: str, source: str = 'VCI'):
    buf = io.StringIO()
    previous_disable = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            from vnstock import Vnstock
            return Vnstock().stock(symbol=symbol.upper(), source=source)
    finally:
        logging.disable(previous_disable)


def vn_listing(source: str):
    Listing = silent_import('vnstock.api.listing', 'Listing')
    return quiet(Listing, source=source)


def get_exchange(name: str):
    import ccxt
    if name.lower() not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange. Choose from: {', '.join(sorted(SUPPORTED_EXCHANGES))}")
    return getattr(ccxt, name.lower())({'enableRateLimit': True})


def get_futures_exchange(name: str):
    import ccxt
    if name.lower() not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange. Choose from: {', '.join(sorted(SUPPORTED_EXCHANGES))}")
    default_type = FUTURES_DEFAULT_TYPES.get(name.lower(), 'swap')
    return getattr(ccxt, name.lower())({'enableRateLimit': True, 'options': {'defaultType': default_type}})


def crypto_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if '/' not in symbol:
        return f"{symbol}/USDT"
    return symbol


def ts_to_utc(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')


def timeframe_to_ms(timeframe: str) -> int:
    unit = timeframe[-1]
    try:
        value = int(timeframe[:-1])
    except ValueError as e:
        raise ValueError("Invalid timeframe. Use values like 1m, 5m, 15m, 1h, 4h.") from e
    multipliers = {
        's': 1000,
        'm': 60 * 1000,
        'h': 60 * 60 * 1000,
        'd': 24 * 60 * 60 * 1000,
        'w': 7 * 24 * 60 * 60 * 1000,
    }
    if unit not in multipliers:
        raise ValueError("Invalid timeframe. Use values like 1m, 5m, 15m, 1h, 4h.")
    return value * multipliers[unit]
