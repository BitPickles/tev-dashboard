#!/usr/bin/env python3
"""
Fluid TEV 数据同步脚本
从 DefiLlama 获取 Holders Revenue 历史数据
"""

import subprocess
import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'fluid-buybacks.json')

def fetch_defillama_data():
    """从 DefiLlama 获取 Fluid holders revenue 数据"""
    url = "https://api.llama.fi/summary/fees/fluid?dataType=dailyHoldersRevenue"
    result = subprocess.run(["curl", "-s", "--max-time", "30", url], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"curl failed: {result.stderr}")
        return None
    return json.loads(result.stdout)

def parse_daily_data(data):
    """解析每日数据，合并所有链和产品"""
    chart = data.get('totalDataChart', [])
    daily = []
    
    for entry in chart:
        ts = entry[0]  # timestamp
        values = entry[1]  # dict of chains -> products -> values
        
        # 合并所有值
        total = 0
        if isinstance(values, dict):
            for chain, products in values.items():
                if isinstance(products, dict):
                    for product, val in products.items():
                        if isinstance(val, (int, float)):
                            total += val
                elif isinstance(products, (int, float)):
                    total += products
        elif isinstance(values, (int, float)):
            total = values
        
        if total > 0:  # 只保留有数据的日期
            date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
            daily.append({
                'date': date,
                'usd': round(total, 2),
                'source': 'DefiLlama'
            })
    
    return daily

def main():
    print(f"[{datetime.now().isoformat()}] Fluid TEV sync started")
    
    # 获取数据
    data = fetch_defillama_data()
    if not data:
        print("Failed to fetch data")
        return
    
    # 解析每日数据
    daily = parse_daily_data(data)
    print(f"Found {len(daily)} days with TEV data")
    
    # 计算累计
    cumulative = 0
    for d in daily:
        cumulative += d['usd']
        d['cumulative'] = round(cumulative, 2)
    
    # 统计
    total_30d = sum(d['usd'] for d in daily[-30:]) if len(daily) >= 30 else sum(d['usd'] for d in daily)
    total_all = cumulative
    
    # 构建输出（匹配 loadBuybackData 预期格式）
    # 转换为 daily_buybacks 格式
    daily_buybacks = []
    for d in daily:
        # Fluid 用 usd 字段作为图表数值（而不是 token 数量）
        daily_buybacks.append({
            'date': d['date'],
            'fluid': round(d['usd'], 2),  # USD 值（直接用于图表）
            'usd': d['usd'],
            'stage': 'defillama',  # 标记为 DefiLlama 数据
            'data_type': 'estimated',  # DefiLlama 是聚合数据，非直接链上
            'source': 'DefiLlama Holders Revenue'
        })
    
    output = {
        'protocol': 'fluid',
        'ticker': 'FLUID',
        'total_supply': 100000000,  # 100M FLUID
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'summary': {
            'total_buyback_fluid': round(total_all, 2),  # USD 值（用于图表）
            'total_buyback_usd': round(total_all, 2),
            'tev_30d_usd': round(total_30d, 2),
            'total_days': len(daily_buybacks),
            'avg_daily': round(total_30d / min(30, len(daily_buybacks)), 2) if daily_buybacks else 0,
            'note': 'Holders Revenue from DefiLlama (Treasury buybacks)'
        },
        'daily_buybacks': daily_buybacks
    }
    
    # 写入文件
    with open(DATA_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Saved to {DATA_FILE}")
    print(f"   Total TEV: ${total_all:,.0f}")
    print(f"   Last 30d: ${total_30d:,.0f}")
    print(f"   Latest date: {daily[-1]['date'] if daily else 'N/A'}")

if __name__ == '__main__':
    main()
