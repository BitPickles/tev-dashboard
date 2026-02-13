#!/usr/bin/env python3
"""增量更新 BMRI 数据（只计算新日期，追加到现有数据）"""
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "indicators/data/bmri.json"
FRED_FILE = "indicators/data/shared/fred-macro.json"

# 加载 FRED 数据
print("加载 FRED 数据...")
with open(FRED_FILE) as f:
    fred = json.load(f)['series']

# 桶配置
BUCKETS = {
    "rates": {"weight": 0.35, "indicators": ["DGS10", "DFII10"], "invert": [True, True]},
    "liq": {"weight": 0.35, "indicators": ["WALCL", "DTWEXBGS"], "invert": [False, True]},
    "risk": {"weight": 0.30, "indicators": ["VIXCLS", "BAMLH0A0HYM2"], "invert": [True, True]}
}

# 预处理
fred_sorted = {}
for name, data in fred.items():
    items = sorted(data.items())
    fred_sorted[name] = {"dates": [d for d, v in items], "values": [v for d, v in items]}

def find_value(series_name, date_str, max_lookback=7):
    data = fred.get(series_name, {})
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for j in range(max_lookback + 1):
        check = (dt - timedelta(days=j)).strftime("%Y-%m-%d")
        if check in data:
            return data[check]
    return None

def get_rolling_percentile(series_name, date_str, lookback_days=252):
    import bisect
    sorted_data = fred_sorted.get(series_name)
    if not sorted_data:
        return None
    
    dates, values = sorted_data["dates"], sorted_data["values"]
    value = find_value(series_name, date_str)
    if value is None:
        return None
    
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    start_str = (dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    
    start_idx = bisect.bisect_left(dates, start_str)
    end_idx = bisect.bisect_right(dates, date_str)
    
    window_values = values[start_idx:end_idx]
    if len(window_values) < 20:
        return None
    
    sorted_window = sorted(window_values)
    rank = sum(1 for v in sorted_window if v <= value)
    return (rank / len(sorted_window)) * 100

def calculate_bmri(date_str, lookback=252):
    bucket_scores = {}
    for bucket_name, config in BUCKETS.items():
        scores = []
        for i, indicator in enumerate(config["indicators"]):
            percentile = get_rolling_percentile(indicator, date_str, lookback_days=lookback)
            if percentile is None:
                continue
            if config["invert"][i]:
                percentile = 100 - percentile
            scores.append(percentile)
        if scores:
            bucket_scores[bucket_name] = sum(scores) / len(scores)
    
    if len(bucket_scores) < 3:
        return None
    
    bmri = sum(bucket_scores.get(b, 50) * BUCKETS[b]["weight"] for b in BUCKETS)
    return {
        "bmri": round(bmri, 2),
        "rates": round(bucket_scores.get("rates", 50), 1),
        "liq": round(bucket_scores.get("liq", 50), 1),
        "risk": round(bucket_scores.get("risk", 50), 1)
    }

def get_regime(value, thresholds):
    if value < thresholds['on']:
        return "RISK_ON"
    elif value > thresholds['off']:
        return "RISK_OFF"
    return "NEUTRAL"

# 加载现有数据
print("加载现有 BMRI 数据...")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE) as f:
        data = json.load(f)
    history_1m = data.get("1m", {}).get("history", [])
    history_6m = data.get("6m", {}).get("history", [])
    last_date_1m = history_1m[-1]["date"] if history_1m else "2013-12-31"
    last_date_6m = history_6m[-1]["date"] if history_6m else "2013-12-31"
    print(f"  1m 最后日期: {last_date_1m} ({len(history_1m)} 条)")
    print(f"  6m 最后日期: {last_date_6m} ({len(history_6m)} 条)")
else:
    history_1m, history_6m = [], []
    last_date_1m = last_date_6m = "2013-12-31"
    print("  无现有数据，将从头计算")

# 获取需要计算的新日期
all_dates = set()
for series_data in fred.values():
    all_dates.update(series_data.keys())
all_dates = sorted(all_dates)

new_dates_1m = [d for d in all_dates if d > last_date_1m]
new_dates_6m = [d for d in all_dates if d > last_date_6m]

if not new_dates_1m and not new_dates_6m:
    print("✅ 数据已是最新，无需更新")
    exit(0)

print(f"计算新数据: 1m={len(new_dates_1m)}天, 6m={len(new_dates_6m)}天")

# 计算新数据
for date in new_dates_1m:
    result = calculate_bmri(date, lookback=252)
    if result:
        history_1m.append({"date": date, **result})

for date in new_dates_6m:
    result = calculate_bmri(date, lookback=504)
    if result:
        history_6m.append({"date": date, **result})

# 更新 current
latest_1m = history_1m[-1] if history_1m else None
latest_6m = history_6m[-1] if history_6m else None

output = {
    "updated_at": datetime.now().strftime("%Y-%m-%d"),
    "1m": {
        "current": {
            "value": latest_1m['bmri'],
            "date": latest_1m['date'],
            "rates": latest_1m['rates'],
            "liq": latest_1m['liq'],
            "risk": latest_1m['risk'],
            "regime": get_regime(latest_1m['bmri'], {"on": 30, "off": 70})
        } if latest_1m else None,
        "thresholds": {"on": 30, "off": 70},
        "history": history_1m
    },
    "6m": {
        "current": {
            "value": latest_6m['bmri'],
            "date": latest_6m['date'],
            "rates": latest_6m['rates'],
            "liq": latest_6m['liq'],
            "risk": latest_6m['risk'],
            "regime": get_regime(latest_6m['bmri'], {"on": 30, "off": 70})
        } if latest_6m else None,
        "thresholds": {"on": 30, "off": 70},
        "history": history_6m
    }
}

with open(DATA_FILE, "w") as f:
    json.dump(output, f)

print(f"✅ 已更新: 1m={len(history_1m)}条, 6m={len(history_6m)}条")
print(f"   范围: {history_1m[0]['date']} ~ {history_1m[-1]['date']}")
