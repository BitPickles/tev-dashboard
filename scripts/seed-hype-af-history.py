#!/usr/bin/env python3
"""
Hyperliquid AF 买入历史 seed 脚本（一次性）。

种子来源：
  1. data/hype-buybacks.json 的 daily_buybacks（429 天，截止 2026-02-28）
  2. 从最后日期补齐到今天：DefiLlama dailyHoldersRevenue API

输出: data/protocols/hype/af-history.json
格式: { seed_at, source, daily: [{date, usd, hype, source}] }

保留在 repo 供审计 / 重跑。每日增量由 update-hype-tev.py 维护。
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HYPE_BUYBACKS = os.path.join(BASE, 'data/hype-buybacks.json')
OUT = os.path.join(BASE, 'data/protocols/hype/af-history.json')
DEFILLAMA_URL = "https://api.llama.fi/summary/fees/hyperliquid?dataType=dailyHoldersRevenue"


def fetch_defillama():
    req = Request(DEFILLAMA_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    # 1. 读现有种子
    with open(HYPE_BUYBACKS) as f:
        hb = json.load(f)
    daily = hb.get('daily_buybacks', [])
    print(f"现有 hype-buybacks.json: {len(daily)} 天，{daily[0]['date']} → {daily[-1]['date']}")

    # 保留关键字段，统一 schema
    records = []
    for d in daily:
        records.append({
            'date': d['date'],
            'usd': round(d.get('usd', 0)),
            'hype': round(d.get('hype', 0), 2),
            'source': 'defillama_holders_revenue_seed',
        })

    # 2. 从 DefiLlama 拉历史，补齐缺口（last+1 到今天）
    last_date = records[-1]['date']
    print(f"\n从 DefiLlama 拉数据补齐 {last_date} 之后...")
    dl = fetch_defillama()
    chart = dl.get('totalDataChart', [])
    print(f"  DefiLlama 总共 {len(chart)} 条")

    added = 0
    for ts, val in chart:
        d_date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        if d_date <= last_date:
            continue
        records.append({
            'date': d_date,
            'usd': round(val or 0),
            'hype': None,  # 不再估算 hype 数量，保持干净
            'source': 'defillama_holders_revenue_fill',
        })
        added += 1

    records.sort(key=lambda r: r['date'])
    print(f"  补齐 {added} 天数据")
    print(f"  完整范围: {records[0]['date']} → {records[-1]['date']} ({len(records)} 天)")

    # 3. 输出
    out = {
        'seeded_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source': 'hype-buybacks.json (DefiLlama holdersRevenue) + DefiLlama fill',
        'note': '每日增量由 update-hype-tev.py 从 Hyperliquid API (spotClearinghouseState) 的 entryNtl delta 追加',
        'daily': records,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 写入 {OUT}")

    # Summary
    total_usd = sum(r['usd'] for r in records)
    print(f"\n📊 累计 USD: ${total_usd/1e9:.2f}B")
    # 最近窗口估算
    import collections
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    for N in [7, 30, 90, 365]:
        last_n = records[-N:] if len(records) >= N else records
        s = sum(r['usd'] for r in last_n)
        print(f"  近 {N} 天 USD: ${s/1e6:.2f}M ({last_n[0]['date']} → {last_n[-1]['date']})")


if __name__ == '__main__':
    sys.exit(main())
