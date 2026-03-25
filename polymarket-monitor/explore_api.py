#!/usr/bin/env python3
"""
Polymarket API 探索器 - 查找可用的 API 端点
"""

import aiohttp
import asyncio
import json
from datetime import datetime
import os

async def test_api():
    # 使用系统代理
    proxy = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy"))
    print(f"Using proxy: {proxy}\n")

    # 测试不同的 API 端点
    endpoints = [
        "https://gamma-api.polymarket.com/events?limit=50",
        "https://gamma-api.polymarket.com/markets?limit=50",
        "https://clob.polymarket.com/markets?limit=50",
        "https://strapi-mirror.polymarket.com/events",
        "https://api.polymarket.com/events",
    ]

    async with aiohttp.ClientSession() as session:
        for url in endpoints:
            print(f"\n🔍 Testing: {url}")
            try:
                kwargs = {"timeout": aiohttp.ClientTimeout(total=10)}
                if proxy:
                    kwargs["proxy"] = proxy
                async with session.get(url, **kwargs) as resp:
                    print(f"   Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            print(f"   ✅ Got {len(data)} items")
                            if data:
                                item = data[0]
                                if 'question' in item:
                                    print(f"   Sample question: {item.get('question', '')[:60]}...")
                                    if 'endDate' in item:
                                        print(f"   End date: {item.get('endDate')}")
                                    if 'closed' in item:
                                        print(f"   Closed: {item.get('closed')}")
                                elif 'title' in item:
                                    print(f"   Sample title: {item.get('title', '')[:60]}...")
                        elif isinstance(data, dict):
                            if 'data' in data:
                                print(f"   ✅ Got {len(data['data'])} items in data field")
                            else:
                                print(f"   Dict keys: {list(data.keys())[:10]}")
                    else:
                        text = await resp.text()
                        print(f"   ❌ {text[:100]}")
            except Exception as e:
                print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
