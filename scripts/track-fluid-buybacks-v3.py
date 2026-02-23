#!/usr/bin/env python3
"""
Fluid Buyback Tracker - 完整版
追踪 Treasury/Team Multisig 的 FLUID 转账，分析是否为 Buyback
"""

import subprocess
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# -----------------------------
# Config: addresses (official)
# -----------------------------
TREASURY = "0x28849D2b63fA8D361e5fc15cB8aBB13019884d09".lower()
TEAM_MULTISIG = "0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e".lower()
WATCH_WALLETS = {
    "treasury": TREASURY,
    "team_multisig": TEAM_MULTISIG,
}

# -----------------------------
# Token contracts (Ethereum mainnet)
# -----------------------------
TOKENS = {
    # FLUID token (Instadapp rebrand)
    "FLUID": "0x6f40d4a6237c257fff2db00fa0510deeedc303eb".lower(),
    # Common payment assets
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".lower(),
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower(),
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7".lower(),
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F".lower(),
}

PAY_TOKENS = {"WETH", "USDC", "USDT", "DAI"}  # tokens used to buy/sell FLUID

# ERC-20 Transfer topic0 keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# A small allowlist of typical routers/aggregators (optional signal)
ROUTERS = {
    "UniswapV3Router": "0xE592427A0AEce92De3Edee1F18E0157C05861564".lower(),
    "UniswapUniversalRouter": "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B".lower(),
    "1inchV5": "0x1111111254EEB25477B68fb85Ed929f73A960582".lower(),
    "0xExchangeProxy": "0xdef1c0ded9bec7f1a1670819833240f027b25eff".lower(),
    "ParaswapV5": "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57".lower(),
}

# -----------------------------
# Time window
# -----------------------------
START_DATE = "2025-10-01"
START_TS = int(datetime.fromisoformat(START_DATE).replace(tzinfo=timezone.utc).timestamp())

# -----------------------------
# Helpers
# -----------------------------
def etherscan_get(params):
    """Etherscan API GET request"""
    params["apikey"] = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"
    params_str = "&".join([f"{k}={v}" for k, v in params.items()])
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", f"https://api.etherscan.io/api?{params_str}"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

def fetch_fluid_tokentx(wallet):
    """
    Use Etherscan 'tokentx' for FLUID contract, filtered by address.
    Handles pagination.
    """
    results = []
    page = 1
    offset = 1000  # max per page

    while True:
        data = etherscan_get({
            "module": "account",
            "action": "tokentx",
            "contractaddress": TOKENS["FLUID"],
            "address": wallet,
            "page": page,
            "offset": offset,
            "sort": "asc",
        })

        if data.get("status") != "1":
            break

        chunk = data.get("result", [])
        if not chunk:
            break

        results.extend(chunk)

        if len(chunk) < offset:
            break

        page += 1
        time.sleep(0.22)

    # Filter by start timestamp
    filtered = [t for t in results if int(t.get("timeStamp", "0")) >= START_TS]
    return filtered

def get_tx_by_hash(txhash):
    """Get transaction by hash"""
    data = etherscan_get({
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": txhash,
    })
    return data.get("result")

def get_tx_receipt(txhash):
    """Get transaction receipt with logs"""
    data = etherscan_get({
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
        "txhash": txhash,
    })
    return data.get("result")

def get_internal_txs(txhash):
    """Internal txs to detect ETH moved out (buying via ETH, or paying fees to router)"""
    data = etherscan_get({
        "module": "account",
        "action": "txlistinternal",
        "txhash": txhash,
    })
    if data.get("status") != "1":
        return []
    return data.get("result", [])

def hex_to_int(x):
    if x is None:
        return 0
    return int(x, 16) if isinstance(x, str) and x.startswith("0x") else int(x)

def topic_to_address(topic):
    # topic is 32-byte hex, last 20 bytes are address
    return "0x" + topic[-40:].lower()

def decode_transfer_log(log):
    """ Returns dict with from,to,amount,token_contract """
    topics = log.get("topics", [])
    if len(topics) < 3:
        return None

    if topics[0].lower() != TRANSFER_TOPIC0:
        return None

    from_addr = topic_to_address(topics[1])
    to_addr = topic_to_address(topics[2])
    amount = hex_to_int(log.get("data", "0x0"))
    token = log.get("address", "").lower()

    return {"from": from_addr, "to": to_addr, "amount": amount, "token": token}

def label_router(to_addr):
    if not to_addr:
        return ""
    to_addr = to_addr.lower()
    for name, addr in ROUTERS.items():
        if addr == to_addr:
            return name
    return ""

# -----------------------------
# Core: fetch FLUID token transfers involving wallet(s)
# -----------------------------
def build_candidates():
    """
    Build a set of txhashes from FLUID transfers involving watch wallets after START_DATE.
    """
    txs = []
    for label, addr in WATCH_WALLETS.items():
        tokentx = fetch_fluid_tokentx(addr)
        for t in tokentx:
            txs.append({
                "watch_label": label,
                "watch_wallet": addr,
                "txhash": t["hash"].lower(),
                "direction": "IN" if t["to"].lower() == addr else "OUT",
                "counterparty": (t["from"] if t["to"].lower() == addr else t["to"]).lower(),
                "blockNumber": int(t["blockNumber"]),
                "timeStamp": int(t["timeStamp"]),
                "tokenDecimal": int(t["tokenDecimal"]),
                "fluid_amount": hex_to_int(t["value"]) / (10 ** int(t["tokenDecimal"])),
            })

    # unique by txhash + watch_wallet (same tx can include multiple transfers)
    dedup = {}
    for r in txs:
        key = (r["txhash"], r["watch_wallet"])
        if key not in dedup:
            dedup[key] = r
        else:
            # if multiple FLUID transfers in same tx, sum
            dedup[key]["fluid_amount"] += r["fluid_amount"]
            # if any IN, keep IN
            if r["direction"] == "IN":
                dedup[key]["direction"] = "IN"

    return list(dedup.values())

def analyze_tx(candidate):
    """
    For a candidate txhash involving wallet, pull receipt logs and internal txs to decide if it looks like a buyback:
    - wallet receives FLUID (direction IN)
    - and wallet sends out payment token OR ETH internal outflow
    """
    txhash = candidate["txhash"]
    wallet = candidate["watch_wallet"]

    tx = get_tx_by_hash(txhash)
    receipt = get_tx_receipt(txhash)

    if not receipt:
        return None

    to_addr = (tx.get("to") if tx else "") or ""
    to_addr = to_addr.lower() if to_addr else ""
    router_label = label_router(to_addr)

    # Parse ERC20 transfers from logs
    transfers = []
    for log in receipt.get("logs", []):
        decoded = decode_transfer_log(log)
        if decoded:
            transfers.append(decoded)

    # Summarize token flows for wallet
    token_in = {}
    token_out = {}

    def add_flow(d, token, amt):
        d[token] = d.get(token, 0) + amt

    for tr in transfers:
        token = tr["token"]
        amt = tr["amount"]
        if tr["to"] == wallet:
            add_flow(token_in, token, amt)
        if tr["from"] == wallet:
            add_flow(token_out, token, amt)

    # Internal txs to catch ETH outflow (value sent to router/aggregator/other)
    internal = get_internal_txs(txhash)
    eth_out_wei = 0
    eth_in_wei = 0

    for itx in internal:
        if itx.get("from", "").lower() == wallet:
            eth_out_wei += hex_to_int(itx.get("value", "0"))
        if itx.get("to", "").lower() == wallet:
            eth_in_wei += hex_to_int(itx.get("value", "0"))

    # Determine signals
    fluid_in = token_in.get(TOKENS["FLUID"], 0)
    fluid_out = token_out.get(TOKENS["FLUID"], 0)

    pay_out = 0
    pay_tokens_out = []
    for sym in PAY_TOKENS:
        addr = TOKENS[sym]
        amt = token_out.get(addr, 0)
        if amt > 0:
            pay_out += amt
            pay_tokens_out.append(sym)

    # Buyback heuristic:
    # - wallet receives FLUID (fluid_in > 0)
    # - and wallet spends ETH (internal eth_out_wei>0) OR spends pay token (pay_out>0)
    # - plus optional router signal (to is router) increases confidence
    is_candidate_buy = (fluid_in > 0) and ((eth_out_wei > 0) or (pay_out > 0))

    # If wallet sends out FLUID and receives pay tokens/ETH, that's a sell, not buyback.
    # (we still record it, but label as SELL-like)
    pay_in = 0
    pay_tokens_in = []
    for sym in PAY_TOKENS:
        addr = TOKENS[sym]
        amt = token_in.get(addr, 0)
        if amt > 0:
            pay_in += amt
            pay_tokens_in.append(sym)

    is_sell_like = (fluid_out > 0) and ((eth_in_wei > 0) or (pay_in > 0))

    # Build row
    ts = candidate["timeStamp"]
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    # Convert selected token amounts to human readable using decimals (hardcode common)
    DECIMALS = {
        TOKENS["FLUID"]: 18,
        TOKENS["WETH"]: 18,
        TOKENS["DAI"]: 18,
        TOKENS["USDC"]: 6,
        TOKENS["USDT"]: 6,
    }

    def human(token_addr, raw_amt):
        dec = DECIMALS.get(token_addr, 18)
        return raw_amt / (10 ** dec)

    details = {
        "datetime_utc": dt,
        "txhash": txhash,
        "watch_wallet": wallet,
        "watch_label": candidate["watch_label"],
        "to_contract": to_addr,
        "router_label": router_label,
        "direction_fluid_transfer": candidate["direction"],
        "fluid_in": human(TOKENS["FLUID"], fluid_in),
        "fluid_out": human(TOKENS["FLUID"], fluid_out),
        "eth_out": eth_out_wei / 1e18,
        "eth_in": eth_in_wei / 1e18,
        "pay_tokens_out": ",".join(pay_tokens_out),
        "usdc_out": human(TOKENS["USDC"], token_out.get(TOKENS["USDC"], 0)),
        "usdt_out": human(TOKENS["USDT"], token_out.get(TOKENS["USDT"], 0)),
        "dai_out": human(TOKENS["DAI"], token_out.get(TOKENS["DAI"], 0)),
        "weth_out": human(TOKENS["WETH"], token_out.get(TOKENS["WETH"], 0)),
        "pay_tokens_in": ",".join(pay_tokens_in),
        "usdc_in": human(TOKENS["USDC"], token_in.get(TOKENS["USDC"], 0)),
        "usdt_in": human(TOKENS["USDT"], token_in.get(TOKENS["USDT"], 0)),
        "dai_in": human(TOKENS["DAI"], token_in.get(TOKENS["DAI"], 0)),
        "weth_in": human(TOKENS["WETH"], token_in.get(TOKENS["WETH"], 0)),
        "is_buyback_candidate": "YES" if is_candidate_buy else "NO",
        "is_sell_like": "YES" if is_sell_like else "NO",
        "blockNumber": candidate["blockNumber"],
    }
    return details

def main():
    import time
    import csv

    candidates = build_candidates()
    print(f"Loaded candidates (wallet FLUID transfers since {START_DATE}): {len(candidates)}")

    out_rows = []
    for i, c in enumerate(sorted(candidates, key=lambda x: x["timeStamp"])):
        if i % 25 == 0:
            print(f"Processing {i}/{len(candidates)} ...")

        try:
            row = analyze_tx(c)
            if row:
                out_rows.append(row)
        except Exception as e:
            print(f"[WARN] Failed tx {c['txhash']}: {e}")
        time.sleep(0.22)  # be nice to Etherscan

    # Write CSV
    filename = "buyback_candidates.csv"
    fields = [
        "datetime_utc", "txhash", "watch_label", "watch_wallet",
        "router_label", "to_contract",
        "fluid_in", "fluid_out",
        "eth_out", "eth_in",
        "pay_tokens_out",
        "usdc_out", "usdt_out", "dai_out", "weth_out",
        "pay_tokens_in",
        "usdc_in", "usdt_in", "dai_in", "weth_in",
        "is_buyback_candidate", "is_sell_like",
        "direction_fluid_transfer",
        "blockNumber",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, "") for k in fields})

    print(f"Saved {len(out_rows)} rows to {filename}")

    # Print quick summary
    buys = [r for r in out_rows if r["is_buyback_candidate"] == "YES"]
    sells = [r for r in out_rows if r["is_sell_like"] == "YES"]
    print(f"Buyback candidates: {len(buys)}")
    print(f"Sell-like txs: {len(sells)}")

    # Also output JSON for website
    if buys:
        # Group by date
        by_date = defaultdict(list)
        for b in buys:
            date = b["datetime_utc"][:10]
            by_date[date].append(b)

        daily = []
        total_usd = 0
        total_fluid = 0
        eth_price = 2000

        for date in sorted(by_date.keys()):
            daily_fluid = sum(b["fluid_in"] for b in by_date[date])
            daily_eth = sum(b["eth_out"] for b in by_date[date])
            daily_usd = daily_eth * eth_price
            total_usd += daily_usd
            total_fluid += daily_fluid

            daily.append({
                "date": date,
                "usd": round(daily_usd, 2),
                "fluid": round(daily_fluid, 0),
                "stage": "onchain",
                "dataType": "onchain",
                "source": "Etherscan"
            })

        output = {
            "protocol": "fluid",
            "ticker": "FLUID",
            "total_supply": 100000000,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_buyback_fluid": round(total_fluid, 0),
                "total_buyback_usd": round(total_usd, 2),
                "total_days": len(by_date),
                "first_date": min(by_date.keys()) if by_date else None,
                "last_date": max(by_date.keys()) if by_date else None,
                "note": "Etherscan 链上追踪（Treasury 收到 FLUID + ETH 支出）"
            },
            "daily_buybacks": daily
        }

        with open("data/fluid-buybacks.json", "w") as f:
            json.dump(output, f, indent=2)

        print(f"\nTotal Buyback FLUID: {total_fluid:,.0f}")
        print(f"Total Buyback USD: ${total_usd:,.0f}")
        print(f"Saved to: data/fluid-buybacks.json")

if __name__ == "__main__":
    main()
