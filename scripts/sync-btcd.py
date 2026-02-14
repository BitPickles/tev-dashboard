#!/usr/bin/env python3
"""
同步 CMC 数据到 btc-dominance.json
包含数据清洗（过滤异常值）
"""

import json
import csv
import os
from pathlib import Path

# 路径
REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = Path.home() / '.openclaw/workspace-researcher/data/cmc_marketcap_history.csv'
JSON_PATH = REPO_ROOT / 'indicators/data/btc-dominance.json'

def sync_btcd():
    if not CSV_PATH.exists():
        print(f"CSV 文件不存在: {CSV_PATH}")
        return False
    
    # 读取现有 JSON
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
    
    existing_dates = {h['date'] for h in data['history']}
    
    # 读取 CSV 并添加新数据（带清洗）
    new_records = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row['date']
            if date not in existing_dates:
                try:
                    btc_d = float(row['btc_dominance'])
                    # 数据清洗：过滤异常值
                    if btc_d <= 0 or btc_d > 100 or btc_d < 30:
                        print(f"跳过异常值: {date} = {btc_d}")
                        continue
                    new_records.append({'date': date, 'value': round(btc_d, 4)})
                except (ValueError, KeyError):
                    continue
    
    if not new_records:
        print("没有新数据")
        return True
    
    # 添加并排序
    data['history'].extend(new_records)
    data['history'].sort(key=lambda x: x['date'])
    
    # 更新 current
    latest = data['history'][-1]
    data['current'] = {
        'value': latest['value'],
        'zone': 'BALANCED' if 50 < latest['value'] < 70 else ('HIGH' if latest['value'] >= 70 else 'LOW'),
        'date': latest['date']
    }
    data['updated_at'] = latest['date']
    
    # 保存
    with open(JSON_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    
    print(f"添加了 {len(new_records)} 条新数据")
    print(f"最新: {latest['date']}, BTC.D: {latest['value']:.2f}%")
    return True

if __name__ == '__main__':
    sync_btcd()
