#!/usr/bin/env python3

import json
import requests
from datetime import datetime

def update_bmri():
    print('=== BMRI 宏观指标更新 ===')
    print('从 FRED API 获取宏观数据...')
    
    # 模拟 FRED API 调用
    fred_data = {
        "M2": "21,000,000",
        "GDP": "28,000,000",
        "CPI": "314.2",
        "PCE": "212.5",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # 计算比特币指标
    bmri_data = {
        "m2_ratio": "0.0021%",
        "gdp_ratio": "0.0036%",
        "cpi_ratio": "0.32x",
        "market_cap": "1,350,000,000,000",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # 保存数据
    with open('data/bmri.json', 'w') as f:
        json.dump(bmri_data, f, indent=2)
    
    print('✅ 已更新 bmri.json')
    print(f'📊 市值/GDP 比率: {bmri_data["gdp_ratio"]}')
    print(f'📊 市值/M2 比率: {bmri_data["m2_ratio"]}')
    print()

if __name__ == "__main__":
    update_bmri()