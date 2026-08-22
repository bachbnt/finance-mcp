# Copyright (c) 2026 bachbnt. All rights reserved.

import json
import os
import unittest

import server


@unittest.skipUnless(os.getenv('RUN_LIVE_TESTS') == '1', 'set RUN_LIVE_TESTS=1 to run provider smoke tests')
class LiveSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def call_tool_payload(self, name: str, arguments: dict):
        result = await server.mcp.call_tool(name, arguments)
        return json.loads(result[1]['result'])

    async def test_crypto_price_smoke(self):
        payload = await self.call_tool_payload('get_crypto_price', {'symbol': 'BTC', 'exchange': 'auto'})
        self.assertTrue(payload['ok'], payload)
        self.assertGreater(payload['data']['last'], 0)

    async def test_vn_stock_price_smoke(self):
        payload = await self.call_tool_payload('get_vn_stock_price', {'symbol': 'FPT', 'source': 'auto'})
        self.assertTrue(payload['ok'], payload)
        self.assertGreater(payload['data']['close'], 0)

    async def test_forex_smoke(self):
        payload = await self.call_tool_payload('get_forex', {})
        self.assertTrue(payload['ok'], payload)
        self.assertIsInstance(payload['data'], list)

