#!/usr/bin/env python3
"""
测试解析 Polymarket HTML
"""
import re
import json

# 读取 HTML
with open("polymarket_20260126_142833.html", "r") as f:
    html = f.read()

# 方法1: 查找单个完整的市场对象
# 先找到一个市场对象作为示例
print("="*70)
print("Method 1: Find individual market")
print("="*70)

single_market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'
matches = re.findall(single_market_pattern, html, re.DOTALL)

print(f"\nFound {len(matches)} potential markets with all fields\n")

for i, match in enumerate(matches[:5]):  # 只显示前5个
    market_id, question, prices_str, liquidity = match
    print(f"\n--- Market {i+1} ---")
    print(f"ID: {market_id}")
    print(f"Question: {question[:60]}...")
    print(f"Prices: {prices_str}")
    print(f"Liquidity: ${liquidity}")

    try:
        prices = json.loads(prices_str)
        liq_float = float(liquidity)
        if liq_float >= 100:
            print(f"✅ VALID: Liquidity >= $100")
        else:
            print(f"❌ SKIP: Liquidity < $100")
    except Exception as e:
        print(f"Error parsing: {e}")

# 方法2: 从 __NEXT_DATA__ 提取完整 JSON
print("\n" + "="*70)
print("Method 2: Extract from __NEXT_DATA__")
print("="*70)

data_pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
data_match = re.search(data_pattern, html, re.DOTALL)

if data_match:
    try:
        json_str = data_match.group(1)
        data = json.loads(json_str)

        # 导航到 events 数组
        if "pageProps" in data and "events" in data["pageProps"]:
            events = data["pageProps"]["events"]
            print(f"\nFound {len(events)} events")

            # 只看第一个事件
            if events and "markets" in events[0]:
                markets = events[0]["markets"]
                print(f"First event has {len(markets)} markets\n")

                # 检查前几个市场
                for i, m in enumerate(markets[:5]):
                    print(f"\n--- Market {i+1} ---")
                    print(f"ID: {m.get('id')}")
                    print(f"Question: {(m.get('question') or '')[:60]}...")
                    print(f"Prices: {m.get('outcomePrices')}")
                    print(f"Liquidity: {m.get('liquidity')}")
                    print(f"Volume: {m.get('volume')}")

                    liq = m.get('liquidity')
                    if liq and float(liq) >= 100:
                        print(f"✅ VALID: Liquidity >= $100")
                    else:
                        print(f"❌ SKIP: Liquidity = {liq}")

    except Exception as e:
        print(f"Error parsing JSON: {e}")
        import traceback
        traceback.print_exc()
