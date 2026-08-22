# Copyright (c) 2026 bachbnt. All rights reserved.
"""
alert_daemon.py — Price alert background daemon for FinHub.

Runs alongside the MCP server, polling the shared alerts.json store at a
configurable interval. When a price condition is met the daemon sends a
Telegram message and marks the alert as triggered so it is not re-fired.
"""

import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from finhub_mcp import alerts
from finhub_mcp.providers import (
    SUPPORTED_EXCHANGES,
    VN_QUOTE_SOURCES,
    crypto_symbol,
    get_exchange,
    quiet,
    silent_import,
)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))


def get_crypto_price(symbol: str) -> float:
    """Fetch the latest spot price for a cryptocurrency pair with exchange fallback."""
    symbol = crypto_symbol(symbol)
    errors = []
    for exchange in SUPPORTED_EXCHANGES:
        try:
            return get_exchange(exchange).fetch_ticker(symbol)['last']
        except Exception as e:
            errors.append(f"{exchange}: {e}")
    raise RuntimeError(f"All crypto exchanges failed ({'; '.join(errors)})")


def get_vn_stock_price(symbol: str) -> float | None:
    """Fetch the latest closing price for a Vietnam-listed stock."""
    Quote = silent_import('vnstock.api.quote', 'Quote')
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    for source in VN_QUOTE_SOURCES:
        try:
            quote = quiet(Quote, symbol=symbol.upper(), source=source)
            df = quiet(quote.history, start=start, end=end, interval='1D')
            if not df.empty:
                return float(df.iloc[-1]['close'])
        except Exception:
            continue
    return None


def send_telegram(chat_id: str, message: str) -> bool:
    """Send a text message to Telegram, or log only when credentials are absent."""
    if not TELEGRAM_TOKEN:
        print(f"[NO TOKEN] {message}")
        return True
    if not chat_id:
        print(f"[NO CHAT_ID] {message}")
        return True
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def check_alerts() -> None:
    """Run one evaluation pass over all pending alerts."""
    for alert in alerts.load_alerts():
        if alert.get('triggered'):
            continue
        try:
            asset_type = alert.get('asset_type', 'crypto')
            symbol = alert['symbol']
            current = get_crypto_price(symbol) if asset_type == 'crypto' else get_vn_stock_price(symbol)
            if current is None:
                continue

            triggered = (
                (alert['condition'] == 'above' and current >= alert['price']) or
                (alert['condition'] == 'below' and current <= alert['price'])
            )
            if not triggered:
                print(
                    f"{datetime.now().strftime('%H:%M:%S')} "
                    f"{symbol}: {current:,.2f} "
                    f"(target {alert['condition']} {alert['price']:,.2f})"
                )
                continue

            msg = (
                f"[ALERT {alert['id']}] {symbol}\n"
                f"Current price: {current:,.2f}\n"
                f"Condition: {alert['condition']} {alert['price']:,.2f}"
            )
            if not send_telegram(alert.get('telegram_chat_id', ''), msg):
                print(f"{datetime.now().strftime('%H:%M:%S')} Alert {alert['id']} will retry.")
                continue
            print(f"{datetime.now().strftime('%H:%M:%S')} {msg}")
            if not alerts.mark_alert_triggered(alert, current):
                print(f"{datetime.now().strftime('%H:%M:%S')} Alert {alert['id']} changed or was removed.")
        except Exception as e:
            print(f"Error checking alert {alert.get('id')}: {e}")


def main() -> None:
    print(f"Alert daemon started. Checking every {CHECK_INTERVAL}s...")
    while True:
        check_alerts()
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
