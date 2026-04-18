#!/usr/bin/env python3
"""
把 Dune 导出的 BEP-95 种子 CSV 转成 JSON 时间序列。
一次性脚本，保留在 repo 以便审计 + 未来可重新 seed。

输入: data/protocols/bnb/bep95-dune-seed.csv
输出: data/protocols/bnb/bep95-history.json

同时扫描 auto_burn 列的非零值，与 burn-history.json 比对，缺失的季度 burn 会列出。
"""

import csv
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, 'data/protocols/bnb/bep95-dune-seed.csv')
JSON_OUT = os.path.join(BASE, 'data/protocols/bnb/bep95-history.json')
BURN_HIST = os.path.join(BASE, 'data/protocols/bnb/burn-history.json')

rows = []
auto_burn_events = []
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for r in reader:
        day = r['day'].strip()
        bep95 = float(r['bep95_bnb'])
        ab = float(r['auto_burn_bnb'])
        tx = int(r['bep95_tx_count'])
        rows.append({'date': day, 'bnb': round(bep95, 6), 'tx_count': tx})
        if ab > 0:
            auto_burn_events.append({'date': day, 'bnb_burned': round(ab, 3)})

rows.sort(key=lambda r: r['date'])

out = {
    'source': 'Dune Analytics (bnb.traces, dead address incoming, value < 100k BNB)',
    'seeded_at': datetime.utcnow().isoformat() + 'Z',
    'seed_range': {'start': rows[0]['date'], 'end': rows[-1]['date'], 'days': len(rows)},
    'daily': rows,
}

os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
with open(JSON_OUT, 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(f"✅ Wrote {JSON_OUT}")
print(f"   {len(rows)} daily records, range: {rows[0]['date']} → {rows[-1]['date']}")

# 验证 auto_burn 事件 vs burn-history.json
with open(BURN_HIST) as f:
    bh = json.load(f)
known_dates = {b['date'] for b in bh.get('quarterly_burns', [])}
print(f"\n📋 检测到 {len(auto_burn_events)} 次 Auto-Burn 事件（从 CSV 提取）:")
for ev in auto_burn_events:
    marker = '✓ 已记录' if ev['date'] in known_dates else '⚠ 未记录（需补）'
    print(f"   {ev['date']}  {ev['bnb_burned']:>15,.0f} BNB   {marker}")
