#!/usr/bin/env python3
"""快速重算 BMRI 历史数据（优化版）"""
import json
from datetime import datetime, timedelta
from collections import defaultdict

# 加载 FRED 数据
print("加载 FRED 数据...")
with open("indicators/data/shared/fred-macro.json") as f:
    fred = json.load(f)['series']

# 桶配置
BUCKETS = {
    "rates": {"weight": 0.35, "indicators": ["DGS10", "DFII10"], "invert": [True, True]},
    "liq": {"weight": 0.35, "indicators": ["WALCL", "DTWEXBGS"], "invert": [False, True]},
    "risk": {"weight": 0.30, "indicators": ["VIXCLS", "BAMLH0A0HYM2"], "invert": [True, True]}
}

# 预处理：为每个序列构建排序后的日期列表
print("预处理数据...")
fred_sorted = {}
for name, data in fred.items():
    items = sorted(data.items())
    fred_sorted[name] = {"dates": [d for d, v in items], "values": [v for d, v in items]}

def find_value(series_name, date_str, max_lookback=7):
    """快速查找值（允许向前回溯）"""
    data = fred.get(series_name, {})
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for j in range(max_lookback + 1):
        check = (dt - timedelta(days=j)).strftime("%Y-%m-%d")
        if check in data:
            return data[check]
    return None

def get_rolling_percentile(series_name, date_str, lookback_days=252):
    """计算滚动百分位（优化版）"""
    import bisect
    
    sorted_data = fred_sorted.get(series_name)
    if not sorted_data:
        return None
    
    dates = sorted_data["dates"]
    values = sorted_data["values"]
    
    # 找当前值
    value = find_value(series_name, date_str)
    if value is None:
        return None
    
    # 找窗口范围
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = dt - timedelta(days=lookback_days)
    start_str = start_dt.strftime("%Y-%m-%d")
    
    # 二分查找
    start_idx = bisect.bisect_left(dates, start_str)
    end_idx = bisect.bisect_right(dates, date_str)
    
    window_values = values[start_idx:end_idx]
    if len(window_values) < 20:  # 至少需要20个点
        return None
    
    # 计算百分位
    sorted_window = sorted(window_values)
    rank = sum(1 for v in sorted_window if v <= value)
    return (rank / len(sorted_window)) * 100

def calculate_bmri(date_str):
    """计算单日 BMRI"""
    bucket_scores = {}
    
    for bucket_name, config in BUCKETS.items():
        scores = []
        for i, indicator in enumerate(config["indicators"]):
            percentile = get_rolling_percentile(indicator, date_str)
            if percentile is None:
                continue
            
            if config["invert"][i]:
                percentile = 100 - percentile
            scores.append(percentile)
        
        if scores:
            bucket_scores[bucket_name] = sum(scores) / len(scores)
    
    if len(bucket_scores) < 3:  # 需要所有三个桶
        return None
    
    bmri = sum(bucket_scores.get(b, 50) * BUCKETS[b]["weight"] for b in BUCKETS)
    
    return {
        "bmri": round(bmri, 2),
        "rates": round(bucket_scores.get("rates", 50), 1),
        "liq": round(bucket_scores.get("liq", 50), 1),
        "risk": round(bucket_scores.get("risk", 50), 1)
    }

# 获取所有日期（从 2014-01-01 开始，需要1年 lookback）
all_dates = set()
for series_data in fred.values():
    all_dates.update(series_data.keys())
all_dates = sorted([d for d in all_dates if d >= "2014-01-01"])

print(f"计算 BMRI ({len(all_dates)} 天)...")

history_1m = []
history_6m = []

for i, date in enumerate(all_dates):
    result = calculate_bmri(date)
    
    if result:
        entry = {"date": date, **result}
        history_1m.append(entry)
        
        dt = datetime.strptime(date, "%Y-%m-%d")
        if dt.weekday() == 5 or date == all_dates[-1]:
            history_6m.append(entry)
    
    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{len(all_dates)}... (有效: {len(history_1m)})")

print(f"\n1M: {len(history_1m)}, 6M: {len(history_6m)}")

if history_1m:
    print(f"范围: {history_1m[0]['date']} ~ {history_1m[-1]['date']}")

latest = history_1m[-1] if history_1m else None

def get_regime(value, thresholds):
    if value < thresholds['on']:
        return "RISK_ON"
    elif value > thresholds['off']:
        return "RISK_OFF"
    return "NEUTRAL"

output = {
    "updated_at": datetime.now().strftime("%Y-%m-%d"),
    "1m": {
        "current": {
            "value": latest['bmri'],
            "date": latest['date'],
            "rates": latest['rates'],
            "liq": latest['liq'],
            "risk": latest['risk'],
            "regime": get_regime(latest['bmri'], {"on": 30, "off": 70})
        } if latest else None,
        "thresholds": {"on": 30, "off": 70},
        "history": history_1m
    },
    "6m": {
        "current": {
            "value": latest['bmri'],
            "date": latest['date'],
            "rates": latest['rates'],
            "liq": latest['liq'],
            "risk": latest['risk'],
            "regime": get_regime(latest['bmri'], {"on": 30, "off": 70})
        } if latest else None,
        "thresholds": {"on": 30, "off": 70},
        "history": history_6m
    }
}

with open("indicators/data/bmri.json", "w") as f:
    json.dump(output, f)

print(f"✅ 已保存 bmri.json")
