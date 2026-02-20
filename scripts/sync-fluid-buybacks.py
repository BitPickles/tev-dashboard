#!/usr/bin/env python3
"""
Fluid 回购数据同步脚本 - DefiLlama 链上聚合数据
从 DefiLlama Holders Revenue API 获取每日回购数据
（注：DefiLlama 通过链上数据聚合得出，非直接查询）
"""

import subprocess
import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'fluid-buybacks.json')

def fetch_defillama_daily_holders_revenue():
    """从 DefiLlama 获取每日 Holders Revenue"""
    url = "https://api.llama.fi/summary/fees/fluid?dataType=dailyHoldersRevenue"

    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", url],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ curl failed: {result.stderr}")
        return []

    data = json.loads(result.stdout)
    chart = data.get('totalDataChart', [])
    return chart

def parse_daily_data(chart):
    """解析每日数据"""
    daily = []
    cumulative_usd = 0

    for entry in chart:
        # 过滤非零值
        usd = entry[1]  # Holders Revenue (USD)
        if usd == 0 or usd is None:
            continue

        ts = entry[0]
        date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        cumulative_usd += usd

        daily.append({
            'date': date,
            'usd': round(usd, 2),
            'cumulative': round(cumulative_usd, 2),
            'stage': 'defillama-onchain',
            'dataType': 'onchain',
            'source': 'DefiLlama (chain aggregation)'
        })

    return daily, cumulative_usd

def main():
    print(f"[{datetime.now().isoformat()}] Fluid 链上数据同步 (DefiLlama)")

    # 获取数据
    chart = fetch_defillama_daily_holders_revenue()
    print(f"获取到 {len(chart)} 个数据点")

    # 解析
    daily, total_usd = parse_daily_data(chart)
    print(f"解析到 {len(daily)} 天有效数据")
    print(f"总回购: ${total_usd:,.2f}")

    if not daily:
        print("❌ No valid data found")
        return

    # 构建输出
    output = {
        'protocol': 'fluid',
        'ticker': 'FLUID',
        'total_supply': 100000000,
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'summary': {
            'total_buyback_fluid': None,  # DefiLlama 不提供代币数量
            'total_buyback_usd': round(total_usd, 2),
            'total_days': len(daily),
            'first_date': daily[0]['date'],
            'last_date': daily[-1]['date'],
            'avg_daily': round(total_usd / min(30, len(daily)), 2),
            'note': 'DefiLlama 链上聚合数据（通过 Holders Revenue API）'
        },
        'daily_buybacks': daily
    }

    # 写入文件
    with open(DATA_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✅ Saved to {DATA_FILE}")
    print(f"   Total USD: ${total_usd:,.2f}")
    print(f"   Days: {len(daily)}")
    print(f"   First: {daily[0]['date']}")
    print(f"   Last: {daily[-1]['date']}")

if __name__ == '__main__':
    main()
