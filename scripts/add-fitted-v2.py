#!/usr/bin/env python3
"""
给 ahr999.json 添加 fitted_price_v2（全量数据重拟合版）
新参数: a=5.5189, b=-15.8993
原版九神参数: a=5.84, b=-17.01
"""
import json, math, datetime
from pathlib import Path

A_NEW = 5.5189
B_NEW = -15.8993
GENESIS = datetime.datetime(2009, 1, 3)

def calc_fitted_v2(date_str):
    d = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    coin_days = (d - GENESIS).days
    if coin_days <= 0:
        return 0
    return round(10 ** (A_NEW * math.log10(coin_days) + B_NEW), 2)

def main():
    path = Path(__file__).parent.parent / 'indicators' / 'data' / 'ahr999.json'
    with open(path) as f:
        data = json.load(f)

    # Update history
    for item in data['history']:
        item['fitted_price_v2'] = calc_fitted_v2(item['date'])

    # Update current
    data['current']['fitted_price_v2'] = calc_fitted_v2(data['current']['date'])

    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    # Verify
    curr = data['current']
    print(f"✅ 已添加 fitted_price_v2 到 {len(data['history'])} 条历史 + current")
    print(f"当前: 九神版 ${curr['fitted_price']:,.0f} → 新版 ${curr['fitted_price_v2']:,.0f}")

if __name__ == '__main__':
    main()
