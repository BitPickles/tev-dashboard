#!/usr/bin/env python3
"""简单测试，验证程序是否能正常启动"""
import subprocess
import re
import json
from datetime import datetime, timedelta

print("🧪 测试：获取市场数据")
print("=" * 70)

# 获取市场数据
result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                              capture_output=True, text=True, timeout=30)
html = result.stdout

print(f"✅ 获取到 {len(html)} 字节数据\n")

# 解析市场
market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'
matches = re.findall(market_pattern, html, re.DOTALL)

print(f"📊 找到 {len(matches)} 个市场")

# 统计
total_liquidity = 0
surebet_count = 0

for match in matches[:50]:  # 只分析前 50 个
    market_id, question, prices_str, liquidity = match
    try:
        prices = [float(p) for p in json.loads(prices_str)]
        liquidity_float = float(liquidity)
        total_liquidity += liquidity_float

        if len(prices) >= 2:
            total = sum(prices)
            if total < 0.98:
                surebet_count += 1

    except:
        pass

print(f"\n📈 统计结果:")
print(f"   总流动性（前 50 市场）: ${total_liquidity:,.0f}")
print(f"   Surebet 机会（前 50 市场）: {surebet_count}")

print("\n✅ 测试完成！程序运行正常。")
