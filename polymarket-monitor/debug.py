#!/usr/bin/env python3
"""
调试版本 - 保存 HTML 并检查数据结构
"""

import subprocess
import re
import json

# 获取 HTML
print("📡 Fetching HTML...")
result = subprocess.run(
    ["curl", "-s", "https://polymarket.com/"],
    capture_output=True,
    text=True,
    timeout=30
)
html = result.stdout
print(f"✅ Fetched {len(html)} bytes")

# 保存 HTML
with open("polymarket_page.html", "w") as f:
    f.write(html)
print("💾 Saved HTML to polymarket_page.html")

# 查找价格模式
price_pattern = r'"outcomePrices":\s*\[\s*([0-9.]+(?:\.[0-9]+)?\s*,?\s*)+\]'
prices = re.findall(price_pattern, html)
print(f"\n📊 Found {len(prices)} outcomePrices patterns")
print("First 5 price matches:")
for p in prices[:5]:
    print(f"  - {p}")

# 查找问题模式
question_pattern = r'"question":"([^"]+)"'
questions = re.findall(question_pattern, html)
print(f"\n📝 Found {len(questions)} questions")
print("First 5 questions:")
for q in questions[:5]:
    print(f"  - {q}")

# 查找ID
id_pattern = r'"id":"(\d+)"'
ids = re.findall(id_pattern, html)
print(f"\n🆔 Found {len(ids)} IDs")
print("First 10 IDs:")
for i in ids[:10]:
    print(f"  - {i}")

# 查找包含完整结构的 JSON
json_pattern = r'\{[^{}]*"id"\s*:\s*"(\d+)"[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*"outcomePrices"\s*:\s*(\[[^\]]+\])'
json_objs = re.findall(json_pattern, html)
print(f"\n📦 Found {len(json_objs)} complete JSON objects")
print("First 5 objects:")
for i, obj in enumerate(json_objs[:5], 1):
    print(f"  {i}. id={obj[0]}, question={obj[1][:50]}..., prices={obj[2][:30]}...")

# 尝试直接解析一个完整对象
if json_objs:
    sample = json_objs[0]
    print(f"\n🔍 Sample object full match: {sample}")
