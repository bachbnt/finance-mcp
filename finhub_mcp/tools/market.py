# Copyright (c) 2026 bachbnt. All rights reserved.

import json
from datetime import datetime

from finhub_mcp.providers import quiet, silent_import
from finhub_mcp.responses import error, success


def register(mcp) -> None:
    @mcp.tool()
    def get_gold_price() -> str:
        """Get the current SJC gold buying and selling prices across branches in Vietnam."""
        try:
            sjc_gold_price = silent_import('vnstock.explorer.misc.gold_price', 'sjc_gold_price')
            df = quiet(sjc_gold_price)
            return success(json.loads(df.to_json(orient='records', force_ascii=False)))
        except Exception as e:
            return error(e)

    @mcp.tool()
    def get_forex() -> str:
        """Get today's foreign exchange rates from Vietcombank."""
        try:
            vcb_exchange_rate = silent_import('vnstock.explorer.misc.exchange_rate', 'vcb_exchange_rate')
            today = datetime.now().strftime('%Y-%m-%d')
            df = quiet(vcb_exchange_rate, today)
            return success(json.loads(df.to_json(orient='records', force_ascii=False)))
        except Exception as e:
            return error(e)

