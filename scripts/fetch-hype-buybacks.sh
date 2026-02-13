#!/bin/bash
# Fetch Hyperliquid Assistance Fund buyback data

AF_ADDRESS="0xfefefefefefefefefefefefefefefefefefefefe"
OUTPUT_DIR="data"
FILLS_FILE="$OUTPUT_DIR/hype-fills-raw.json"

echo "=== Hyperliquid Assistance Fund Buybacks ==="
echo ""

# 1. 获取当前余额
echo "📊 获取当前 HYPE 余额..."
BALANCE_JSON=$(curl -s https://api.hyperliquid.xyz/info \
  -H 'Content-Type: application/json' \
  -d '{"type":"spotClearinghouseState","user":"'"$AF_ADDRESS"'"}')

HYPE_BALANCE=$(echo "$BALANCE_JSON" | jq -r '.balances[] | select(.coin=="HYPE") | .total')
HYPE_COST=$(echo "$BALANCE_JSON" | jq -r '.balances[] | select(.coin=="HYPE") | .entryNtl')

echo "   当前余额: $HYPE_BALANCE HYPE"
echo "   累计成本: \$$(echo "$HYPE_COST" | cut -d'.' -f1)"
echo ""

# 2. 获取所有 fills（API 限制 2000 条/次，只保留最近 10000 条）
echo "📈 获取成交记录..."
curl -s https://api.hyperliquid.xyz/info \
  -H 'Content-Type: application/json' \
  -d '{"type":"userFills","user":"'"$AF_ADDRESS"'"}' > "$FILLS_FILE"

FILLS_COUNT=$(jq 'length' "$FILLS_FILE")
echo "   获取 $FILLS_COUNT 条成交记录"

# 3. 筛选 HYPE 买入（@107）并按日聚合
echo ""
echo "📊 按日聚合..."
python3 << 'PYTHON'
import json
from collections import defaultdict
from datetime import datetime

with open("data/hype-fills-raw.json") as f:
    fills = json.load(f)

# 筛选 HYPE 买入 (@107, side=B)
hype_buys = [f for f in fills if f.get("coin") == "@107" and f.get("side") == "B"]
print(f"   HYPE 买入: {len(hype_buys)} 笔")

# 按日聚合
daily = defaultdict(lambda: {"hype": 0.0, "usd": 0.0, "txs": 0})

for f in hype_buys:
    ts = f["time"] / 1000  # 毫秒转秒
    date = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    sz = float(f["sz"])
    px = float(f["px"])
    
    daily[date]["hype"] += sz
    daily[date]["usd"] += sz * px
    daily[date]["txs"] += 1

# 排序输出
result = []
for date in sorted(daily.keys()):
    d = daily[date]
    result.append({
        "date": date,
        "hype": round(d["hype"], 2),
        "usd": round(d["usd"], 2),
        "avg_price": round(d["usd"] / d["hype"], 4) if d["hype"] > 0 else 0,
        "txs": d["txs"],
        "data_type": "onchain",
        "source": "hyperliquid_api"
    })

# 保存
with open("data/hype-onchain.json", "w") as f:
    json.dump(result, f, indent=2)

# 汇总
total_hype = sum(r["hype"] for r in result)
total_usd = sum(r["usd"] for r in result)
avg_price = total_usd / total_hype if total_hype > 0 else 0

print(f"\n=== API 数据汇总 (最近 10000 fills) ===")
print(f"天数: {len(result)}")
print(f"HYPE: {total_hype:,.0f}")
print(f"USD: ${total_usd:,.0f}")
print(f"均价: ${avg_price:.2f}")
if result:
    print(f"范围: {result[0]['date']} ~ {result[-1]['date']}")
PYTHON

echo ""
echo "✅ 已保存到 data/hype-onchain.json"
