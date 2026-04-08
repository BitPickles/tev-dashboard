#!/usr/bin/env python3
"""
调试 - 检查 HTML 中的字段名称
"""

import subprocess
import re

# 获取 HTML
print("📡 Fetching HTML...")
result = subprocess.run(
    ["curl", "-s", "https://polymarket.com/"],
    capture_output=True,
    text=True,
    timeout=30
)
html = result.stdout
print(f"✅ Fetched {len(html)} bytes\n")

# 查找前 10 个 ID
id_pattern = r'"id":"(\d+)"'
ids = re.findall(id_pattern, html)
print(f"🆔 Found {len(ids)} IDs")
print("First 10 IDs:")
for i, pid in enumerate(ids[:10], 1):
    print(f"  {i}. {pid}\n")

# 对于第一个 ID，查找其周围的字段
if ids:
    first_id = ids[0]
    print(f"\n🔍 Analyzing market with ID: {first_id}\n")

    # 找到这个 ID 在 HTML 中的位置
    id_match = re.search(f'"id":"{first_id}"', html)
    if id_match:
        # 获取该位置前后的 2000 个字符
        context = html[max(0, id_match.start()-1000):id_match.start()+1000]

        print("Fields found around this ID:")
        print("=" * 60)

        # 查找各种字段
        fields = [
            "volume", "volumeNum", "volume_num",
            "liquidity", "liquidityNum", "liquidity_num",
            "endDate", "endTimestamp", "end_time",
            "price", "outcomePrices", "outcome_prices",
            "question", "question",
            "closed", "active",
            "slug"
        ]

        found_fields = []
        for field in fields:
            if f'"{field}"' in context or f'"{field}":' in context:
                # 检查字段名
                field_pattern = rf'"{field}"\s*:\s*'
                match = re.search(field_pattern, context)
                if match:
                    value_context = context[match.end():match.end()+50]
                    found_fields.append((field, value_context[:50]))

        # 按 ID 显示找到的字段
        for field, value in found_fields:
            print(f"  📌 {field}: {value}")

        # 查找该 ID 周围的所有键
        print("\n🔑 All keys found in context:")
        keys_pattern = r'"([^"]+)"\s*:'
        keys = re.findall(keys_pattern, context)
        unique_keys = list(set(keys))
        for key in sorted(unique_keys):
            if len(key) > 2:  # 忽略太短的键
                print(f"  - {key}")
