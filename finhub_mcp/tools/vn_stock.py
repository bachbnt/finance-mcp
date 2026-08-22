# Copyright (c) 2026 bachbnt. All rights reserved.

import json
from datetime import datetime, timedelta

from finhub_mcp.indicators import calculate_indicators, parse_indicators
from finhub_mcp.providers import (
    VN_INTRADAY_SOURCES,
    VN_LISTING_SOURCES,
    VN_QUOTE_SOURCES,
    VN_STOCK_SOURCES,
    fallback_used,
    first_success,
    provider_order,
    quiet,
    vn_listing,
    vn_quote,
    vn_stock,
)
from finhub_mcp.responses import error, invalid, success


def register(mcp) -> None:
    @mcp.tool()
    def get_vn_stock_price(symbol: str, source: str = 'auto') -> str:
        """Get the latest price snapshot for a Vietnam-listed stock."""
        try:
            sources = provider_order(source, VN_QUOTE_SOURCES, 'VN quote source')
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
            used_source, df = first_success(
                sources,
                lambda src: quiet(vn_quote(symbol, src).history, start=start, end=end, interval='1D'),
                f"no data found for {symbol.upper()}",
            )
            row = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else row
            change = float(row['close']) - float(prev['close'])
            data = {
                'symbol': symbol.upper(),
                'date': row['time'].strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'change': round(change, 2),
                'change_pct': round((change / float(prev['close'])) * 100, 2),
                'volume': int(row['volume']),
                'source': used_source,
                'fallback_used': fallback_used(used_source, sources),
            }
            return success(data)
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_vn_stock_history(symbol: str, days: int = 30, source: str = 'auto') -> str:
        """Get historical daily OHLCV data for a Vietnam-listed stock."""
        try:
            sources = provider_order(source, VN_QUOTE_SOURCES, 'VN quote source')
            days = min(max(days, 1), 365)
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            used_source, df = first_success(
                sources,
                lambda src: quiet(vn_quote(symbol, src).history, start=start, end=end, interval='1D'),
                f"no data found for {symbol.upper()}",
            )
            df['date'] = df['time'].dt.strftime('%Y-%m-%d')
            data = df[['date', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient='records')
            for item in data:
                item['source'] = used_source
                item['fallback_used'] = fallback_used(used_source, sources)
            return success(data)
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_vn_stock_intraday(
        symbol: str,
        period: str = 'latest',
        limit: int = 100,
        page_size: int = 100,
        pages: int = 5,
        source: str = 'auto',
    ) -> str:
        """Get intraday matched trades for a Vietnam-listed stock."""
        try:
            sources = provider_order(source, VN_INTRADAY_SOURCES, 'VN intraday source')
            period = period.lower()
            if period not in {'latest', 'today'}:
                return invalid("Invalid period. Choose from: latest, today")
            limit = min(max(limit, 1), 1000)
            page_size = min(max(page_size, 10), 1000)
            pages = min(max(pages, 1), 20)

            def fetch(src: str):
                frames = []
                quote = vn_quote(symbol, src)
                for page in range(1, pages + 1):
                    df = quiet(quote.intraday, page_size=page_size, page=page)
                    if getattr(df, 'empty', True):
                        break
                    frames.append(df)
                records = []
                for df in frames:
                    records.extend(df.to_dict(orient='records'))
                return records

            used_source, records = first_success(
                sources,
                fetch,
                f"no intraday data found for {symbol.upper()}",
            )
            today = datetime.now().date()
            normalized = []
            for row in records:
                ts = row.get('time')
                if hasattr(ts, 'to_pydatetime'):
                    dt = ts.to_pydatetime()
                elif isinstance(ts, datetime):
                    dt = ts
                else:
                    dt = datetime.fromisoformat(str(ts))
                if period == 'today' and dt.date() != today:
                    continue
                normalized.append({
                    'symbol': symbol.upper(),
                    'time': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': float(row['price']) if row.get('price') is not None else None,
                    'volume': int(row['volume']) if row.get('volume') is not None else None,
                    'match_type': row.get('match_type'),
                    'id': row.get('id'),
                    'source': used_source,
                    'fallback_used': fallback_used(used_source, sources),
                })

            normalized.sort(key=lambda item: item['time'], reverse=True)
            return success(normalized[:limit])
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_vn_market_overview(source: str = 'auto') -> str:
        """Get a snapshot of the main Vietnam market indices."""
        try:
            results = {}
            errors = {}
            sources = provider_order(source, VN_QUOTE_SOURCES, 'VN quote source')
            for idx in ['VNINDEX', 'VN30', 'HNXINDEX']:
                try:
                    end = datetime.now().strftime('%Y-%m-%d')
                    start = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
                    used_source, df = first_success(
                        sources,
                        lambda src: quiet(vn_quote(idx, src).history, start=start, end=end, interval='1D'),
                        f"no data found for {idx}",
                    )
                    row = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) >= 2 else row
                    change = float(row['close']) - float(prev['close'])
                    results[idx] = {
                        'close': float(row['close']),
                        'change': round(change, 2),
                        'change_pct': round((change / float(prev['close'])) * 100, 2),
                        'volume': int(row['volume']),
                        'date': row['time'].strftime('%Y-%m-%d'),
                        'source': used_source,
                        'fallback_used': fallback_used(used_source, sources),
                    }
                except Exception as e:
                    errors[idx] = str(e)
            if not results and errors:
                details = '; '.join(f'{idx}: {err}' for idx, err in errors.items())
                return error(f"all market indices failed ({details})")
            return success(results, warnings=errors or None)
        except Exception as e:
            return error(e)

    @mcp.tool()
    def search_vn_stock(query: str, source: str = 'auto') -> str:
        """Search for Vietnam stock tickers by symbol or company name."""
        try:
            sources = provider_order(source, VN_LISTING_SOURCES, 'VN listing source')
            used_source, listing = first_success(
                sources,
                lambda src: quiet(vn_listing(src).all_symbols),
                'no symbols found',
            )
            q = query.lower()
            mask = listing['symbol'].str.lower().str.contains(q, na=False)
            if 'organ_name' in listing.columns:
                mask |= listing['organ_name'].str.lower().str.contains(q, na=False)
            matches = listing[mask].head(20).copy()
            matches['source'] = used_source
            matches['fallback_used'] = fallback_used(used_source, sources)
            return success(json.loads(matches.to_json(orient='records', force_ascii=False)))
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_company_overview(symbol: str, source: str = 'auto') -> str:
        """Get company profile information for a Vietnam-listed stock."""
        try:
            sources = provider_order(source, VN_STOCK_SOURCES, 'VN stock source')
            used_source, df = first_success(
                sources,
                lambda src: quiet(vn_stock(symbol, src).company.overview),
                f"no company overview found for {symbol.upper()}",
            )
            df = df.copy()
            df['source'] = used_source
            df['fallback_used'] = fallback_used(used_source, sources)
            return success(json.loads(df.to_json(orient='records', force_ascii=False)))
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_financials(symbol: str, statement: str = 'income_statement', period: str = 'year', source: str = 'auto') -> str:
        """Get financial statements for a Vietnam-listed stock."""
        try:
            valid_statements = {'income_statement', 'balance_sheet', 'cash_flow', 'ratio'}
            if statement not in valid_statements:
                return invalid(f"Invalid statement. Choose from: {', '.join(sorted(valid_statements))}")
            sources = provider_order(source, VN_STOCK_SOURCES, 'VN stock source')

            def fetch(src: str):
                stock = vn_stock(symbol, src)
                fn_map = {
                    'income_statement': lambda: stock.finance.income_statement(period=period),
                    'balance_sheet': lambda: stock.finance.balance_sheet(period=period),
                    'cash_flow': lambda: stock.finance.cash_flow(period=period),
                    'ratio': lambda: stock.finance.ratio(lang='vi'),
                }
                return quiet(fn_map[statement])

            used_source, df = first_success(sources, fetch, f"no financials found for {symbol.upper()}")
            df = df.copy()
            df['source'] = used_source
            df['fallback_used'] = fallback_used(used_source, sources)
            return success(json.loads(df.to_json(orient='records', force_ascii=False)))
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_vn_stock_indicators(
        symbol: str,
        days: int = 180,
        indicators: str = 'sma,ema,rsi,macd,bollinger',
        source: str = 'auto',
    ) -> str:
        """Calculate technical indicators from Vietnam stock daily history."""
        try:
            requested = parse_indicators(indicators)
            sources = provider_order(source, VN_QUOTE_SOURCES, 'VN quote source')
            days = min(max(days, 30), 365)
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            used_source, df = first_success(
                sources,
                lambda src: quiet(vn_quote(symbol, src).history, start=start, end=end, interval='1D'),
                f"no data found for {symbol.upper()}",
            )
            closes = [float(value) for value in df['close'].tolist() if value is not None]
            data = {
                'symbol': symbol.upper(),
                'days': days,
                'candles': len(closes),
                'last_close': closes[-1] if closes else None,
                'source': used_source,
                'fallback_used': fallback_used(used_source, sources),
                'indicators': calculate_indicators(closes, requested),
            }
            return success(data)
        except Exception as e:
            return error(e)
