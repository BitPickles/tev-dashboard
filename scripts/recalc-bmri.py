#!/usr/bin/env python3
"""重新计算 BMRI 历史数据（从 2013 年开始）"""
import json
from datetime import datetime, timedelta

# 加载 FRED 数据
print("加载 FRED 数据...")
with open("indicators/data/shared/fred-macro.json") as f:
    fred = json.load(f)['series']

# 桶配置 - 简化版本
BUCKETS = {
    "rates": {
        "weight": 0.35,
        "indicators": ["DGS10", "DFII10"],
        "invert": [True, True]
    },
    "liq": {
        "weight": 0.35, 
        "indicators": ["WALCL", "DTWEXBGS"],
        "invert": [False, True]
    },
    "risk": {
        "weight": 0.30,
        "indicators": ["VIXCLS", "BAMLH0A0HYM2"],
        "invert": [True, True]
    }
}

def get_percentile(value, all_values):
    if not all_values:
        return 50
    sorted_vals = sorted(all_values)
    rank = sum(1 for v in sorted_vals if v <= value)
    return (rank / len(sorted_vals)) * 100

def calculate_bmri_for_date(date, lookback=252):
    bucket_scores = {}
    
    for bucket_name, config in BUCKETS.items():
        scores = []
        for i, indicator in enumerate(config["indicators"]):
            if indicator not in fred:
                continue
            
            data = fred[indicator]
            
            # 找值（允许向前回溯7天）
            value = None
            dt = datetime.strptime(date, "%Y-%m-%d")
            for j in range(8):
                check_date = (dt - timedelta(days=j)).strftime("%Y-%m-%d")
                if check_date in data:
                    value = data[check_date]
                    break
            
            if value is None:
                continue
            
            # 计算百分位
            window_values = []
            for d, v in data.items():
                d_dt = datetime.strptime(d, "%Y-%m-%d")
                if (dt - timedelta(days=lookback)) <= d_dt <= dt:
                    window_values.append(v)
            
            if not window_values:
                continue
            
            percentile = get_percentile(value, window_values)
            if config["invert"][i]:
                percentile = 100 - percentile
            
            scores.append(percentile)
        
        if scores:
            bucket_scores[bucket_name] = sum(scores) / len(scores)
    
    if not bucket_scores:
        return None, None, None, None
    
    bmri = sum(bucket_scores.get(b, 50) * BUCKETS[b]["weight"] for b in BUCKETS)
    
    return (
        round(bmri, 2),
        round(bucket_scores.get("rates", 50), 1),
        round(bucket_scores.get("liq", 50), 1),
        round(bucket_scores.get("risk", 50), 1)
    )

# 获取所有日期
all_dates = set()
for series_data in fred.values():
    all_dates.update(series_data.keys())
all_dates = sorted([d for d in all_dates if d >= "2013-01-01"])

print(f"计算 BMRI ({len(all_dates)} 天)...")

history_1m = []
history_6m = []

for i, date in enumerate(all_dates):
    bmri, rates, liq, risk = calculate_bmri_for_date(date)
    
    if bmri is not None:
        entry = {"date": date, "bmri": bmri, "rates": rates, "liq": liq, "risk": risk}
        history_1m.append(entry)
        
        dt = datetime.strptime(date, "%Y-%m-%d")
        if dt.weekday() == 5 or date == all_dates[-1]:
            history_6m.append(entry)
    
    if (i + 1) % 1000 == 0:
        print(f"  {i+1}/{len(all_dates)}...")

print(f"1M: {len(history_1m)}, 6M: {len(history_6m)}")

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
            "regime": get_regime(latest['bmri'], {"on": 25, "off": 75})
        } if latest else None,
        "thresholds": {"on": 25, "off": 75},
        "history": history_1m
    },
    "6m": {
        "current": {
            "value": latest['bmri'],
            "date": latest['date'],
            "rates": latest['rates'],
            "liq": latest['liq'],
            "risk": latest['risk'],
            "regime": get_regime(latest['bmri'], {"on": 20, "off": 80})
        } if latest else None,
        "thresholds": {"on": 20, "off": 80},
        "history": history_6m
    }
}

with open("indicators/data/bmri.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"✅ 已保存: {history_1m[0]['date']} ~ {history_1m[-1]['date']}")
