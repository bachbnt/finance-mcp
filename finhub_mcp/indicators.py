# Copyright (c) 2026 bachbnt. All rights reserved.

import statistics
from typing import Any

SUPPORTED_INDICATORS = ('sma', 'ema', 'rsi', 'macd', 'bollinger')


def parse_indicators(value: str) -> list[str]:
    if value is None or value.strip().lower() in {'auto', 'default', 'all'}:
        return list(SUPPORTED_INDICATORS)
    requested = []
    for item in value.split(','):
        key = item.strip().lower()
        if not key:
            continue
        if key not in SUPPORTED_INDICATORS:
            raise ValueError(f"Unsupported indicator: {item.strip()}. Choose from: {', '.join(SUPPORTED_INDICATORS)}")
        if key not in requested:
            requested.append(key)
    if not requested:
        raise ValueError("No indicators requested")
    return requested


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    multiplier = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append((value - result[-1]) * multiplier + result[-1])
    return result


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return ema_series(values, period)[-1]


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains = []
    losses = []
    for previous, current in zip(values[-period - 1:-1], values[-period:]):
        change = current - previous
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, float | None]:
    if len(values) < slow:
        return {'macd': None, 'signal': None, 'histogram': None}
    fast_series = ema_series(values, fast)
    slow_series = ema_series(values, slow)
    macd_line = [fast_value - slow_value for fast_value, slow_value in zip(fast_series, slow_series)]
    signal_line = ema_series(macd_line, signal)
    current_macd = macd_line[-1]
    current_signal = signal_line[-1] if signal_line else None
    return {
        'macd': current_macd,
        'signal': current_signal,
        'histogram': current_macd - current_signal if current_signal is not None else None,
    }


def bollinger(values: list[float], period: int = 20, stddev: float = 2.0) -> dict[str, float | None]:
    if len(values) < period:
        return {'middle': None, 'upper': None, 'lower': None, 'width_pct': None}
    window = values[-period:]
    middle = sum(window) / period
    deviation = statistics.pstdev(window)
    upper = middle + stddev * deviation
    lower = middle - stddev * deviation
    return {
        'middle': middle,
        'upper': upper,
        'lower': lower,
        'width_pct': ((upper - lower) / middle * 100) if middle else None,
    }


def round_nested(value: Any, digits: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {key: round_nested(item, digits) for key, item in value.items()}
    return value


def calculate_indicators(closes: list[float], indicators: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if 'sma' in indicators:
        data['sma'] = {
            '20': sma(closes, 20),
            '50': sma(closes, 50),
        }
    if 'ema' in indicators:
        data['ema'] = {
            '12': ema(closes, 12),
            '26': ema(closes, 26),
        }
    if 'rsi' in indicators:
        data['rsi'] = {
            '14': rsi(closes, 14),
        }
    if 'macd' in indicators:
        data['macd'] = macd(closes)
    if 'bollinger' in indicators:
        data['bollinger'] = bollinger(closes)
    return round_nested(data)

