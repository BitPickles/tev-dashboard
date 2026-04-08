#!/usr/bin/env python3
"""
测试 API 连接 (使用代理)
"""

import aiohttp
import asyncio
import os

async def test_connection():
    proxy = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy", "http://127.0.0.1:7890"))

    print(f"Using proxy: {proxy}")

    # 测试1: 简单的 GET 请求
    print("\n[1] Testing simple GET to gamma-api...")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://gamma-api.polymarket.com/",
            proxy=proxy
        ) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            if "GraphiQL" in text:
                print("✅ GraphiQL playground found!")
            else:
                print(f"Response: {text[:200]}")

    # 测试2: 尝试不同的认证方式
    print("\n[2] Testing with user-agent and referer...")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Origin": "https://polymarket.com",
        "Referer": "https://polymarket.com/"
    }

    query = '{markets(first:3){id question}}'

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://gamma-api.polymarket.com/query",
            proxy=proxy,
            json={"query": query},
            headers=headers
        ) as resp:
            print(f"Status: {resp.status}")
            text = await resp.text()
            print(f"Response: {text[:500]}")

if __name__ == "__main__":
    asyncio.run(test_connection())
