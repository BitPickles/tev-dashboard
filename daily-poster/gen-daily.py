#!/usr/bin/env python3
"""Crypto3D 每日数据海报生成器（新版浅色 1080×1920）

读取 tev-dashboard 本地数据 → 替换 template.html → Playwright 截图 PNG

数据源：
- indicators/data/ahr999.json
- indicators/data/mvrv.json
- indicators/data/bmri.json
- indicators/data/btc-dominance.json
- indicators/data/shared/fred-macro.json
- data/governance.json
"""
import asyncio
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = SCRIPT_DIR / "template.html"
LOGO_PATH = SCRIPT_DIR / "logo-3d.jpg"
TEV_DIR = Path.home() / ".openclaw" / "workspace-engineer" / "tev-dashboard"
INDICATORS = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Previous cycle MVRV at same point post-halving (~23 months after May 2020 halving = March 2022)
PREV_CYCLE_MVRV = 1.73

TZ = timezone(timedelta(hours=8))
WEEKDAYS_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MONTHS_EN = ["", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
             "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
DAYS_EN = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def load_json(p):
    try:
        return json.load(open(p))
    except Exception as e:
        print(f"[WARN] Failed to load {p}: {e}")
        return None


def collect_data():
    """Collect all data needed for the poster."""
    now = datetime.now(TZ)
    data = {"date": now}

    # --- AHR999 ---
    ahr = load_json(INDICATORS / "ahr999.json")
    if ahr:
        c = ahr["current"]
        h = ahr.get("history", [])
        # 7d price change
        p_now = c["price"]
        p_7d = h[-8]["close"] if len(h) > 7 else h[0]["close"]
        price_chg_7d = (p_now - p_7d) / p_7d * 100
        # 7d ahr change
        a_now = c["value"]
        a_7d = h[-8]["ahr999"] if len(h) > 7 else h[0]["ahr999"]
        ahr_chg_7d = (a_now - a_7d) / a_7d * 100
        # Price deviation from fitted
        deviation = (p_now - c["fitted_price"]) / c["fitted_price"] * 100

        data["btc"] = {
            "price": p_now,
            "price_chg_7d": price_chg_7d,
            "prices_7d": [x["close"] for x in h[-7:]],
        }
        data["ahr999"] = {
            "value": a_now,
            "status": c["status"],
            "cost_200d": c["cost_200d"],
            "fitted_price": c["fitted_price"],
            "deviation": deviation,
            "chg_7d": ahr_chg_7d,
        }

    # --- MVRV ---
    mvrv = load_json(INDICATORS / "mvrv.json")
    if mvrv:
        c = mvrv["current"]
        h = mvrv.get("history", [])
        m_now = c["value"]
        m_7d = h[-8]["mvrv"] if len(h) > 7 else h[0]["mvrv"]
        mvrv_chg_7d = (m_now - m_7d) / m_7d * 100
        # Historical percentile (rough: what % of history is below current)
        all_vals = [x["mvrv"] for x in h]
        percentile = sum(1 for v in all_vals if v < m_now) / len(all_vals) * 100 if all_vals else 50
        # Previous cycle same period MVRV
        # Current halving: April 2024. Previous: May 2020.
        # Compute months since current halving, find same offset in prev cycle
        halving_current = datetime(2024, 4, 20)
        halving_prev = datetime(2020, 5, 11)
        months_since = (now.year - halving_current.year) * 12 + (now.month - halving_current.month)
        target_date = halving_prev + timedelta(days=months_since * 30.44)
        target_str = target_date.strftime("%Y-%m")
        prev_cycle_vals = [x["mvrv"] for x in h if x["date"].startswith(target_str)]
        prev_cycle_mvrv = round(sum(prev_cycle_vals) / len(prev_cycle_vals), 2) if prev_cycle_vals else PREV_CYCLE_MVRV

        data["mvrv"] = {
            "value": m_now,
            "status": c["status"],
            "chg_7d": mvrv_chg_7d,
            "percentile": percentile,
            "prev_cycle": prev_cycle_mvrv,
        }

    # --- BMRI ---
    bmri = load_json(INDICATORS / "bmri.json")
    if bmri:
        c = bmri["1m"]["current"]
        data["bmri"] = {
            "value": c["value"],
            "regime": c["regime"],
            "rates": c.get("rates", 0),
            "liq": c.get("liq", 0),
            "risk": c.get("risk", 0),
        }

    # --- FRED macro for BMRI sub-indicators ---
    fred = load_json(INDICATORS / "shared" / "fred-macro.json")
    if fred and "series" in fred:
        s = fred["series"]
        def last_val(key):
            d = s.get(key)
            if not d:
                return None
            if isinstance(d, str):
                d = eval(d)
            if isinstance(d, dict) and d:
                return list(d.values())[-1]
            return None
        # WALCL is Fed balance sheet in millions; rough M2 proxy
        walcl = last_val("WALCL")
        data["fred"] = {
            "dgs10": last_val("DGS10"),
            "vix": last_val("VIXCLS"),
            "dxy": last_val("DTWEXBGS"),
            "m2": walcl * 1e6 if walcl and walcl > 1000 else None,  # Convert millions to raw
        }

    # --- BTC.D ---
    btcd = load_json(INDICATORS / "btc-dominance.json")
    if btcd:
        c = btcd["current"]
        h = btcd.get("history", [])
        d_now = c["value"]
        d_7d = h[-8]["value"] if len(h) > 7 else h[0]["value"]
        btcd_chg_7d = (d_now - d_7d) / d_7d * 100
        data["btcd"] = {
            "value": d_now,
            "zone": c["zone"],
            "chg_7d": btcd_chg_7d,
        }

    # --- Governance (active + TEV related) ---
    gov = load_json(TEV_DIR / "data" / "governance.json")
    if gov:
        active_tev = [p for p in gov.get("proposals", [])
                      if p.get("status") == "active" and p.get("tev_related")]
        if active_tev:
            # Pick the one with most tev_keywords or first
            best = active_tev[0]
            data["governance"] = {
                "protocol": best.get("protocol", ""),
                "title": best.get("title", ""),
                "summary_zh": best.get("summary_zh", best.get("summary_en", "")),
                "end": best.get("end", ""),
                "status": "进行中",
                "vote_pct": 0,  # We don't have vote data in current JSON
            }

    return data


def fmt_price(v):
    """Format price like $70,759"""
    return f"${v:,.0f}"


def fmt_mcap(v_usd):
    """Format market cap like $1.40T"""
    if v_usd >= 1e12:
        return f"${v_usd/1e12:.2f}T"
    elif v_usd >= 1e9:
        return f"${v_usd/1e9:.1f}B"
    return f"${v_usd/1e6:.0f}M"


def btc_sparkline_svg(prices):
    """Generate BTC sparkline SVG path for background."""
    if not prices or len(prices) < 2:
        return ""
    mn, mx = min(prices), max(prices)
    rng = mx - mn or 1
    w, h = 960, 200
    pts = [(i * w / (len(prices) - 1), h - ((p - mn) / rng * h * 0.7) - h * 0.1)
           for i, p in enumerate(prices)]

    # Build smooth curve path
    path_d = f"M{pts[0][0]:.0f},{pts[0][1]:.0f}"
    for i in range(1, len(pts)):
        cx = (pts[i-1][0] + pts[i][0]) / 2
        path_d += f" C{cx:.0f},{pts[i-1][1]:.0f} {cx:.0f},{pts[i][1]:.0f} {pts[i][0]:.0f},{pts[i][1]:.0f}"
    fill_d = path_d + f" L{w},{h} L0,{h}Z"

    return f'''<svg width="100%" height="100%" viewBox="0 0 {w} {h}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sf" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#18181b" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#18181b" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="lineAlpha" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#18181b" stop-opacity="0"/>
            <stop offset="20%" stop-color="#18181b" stop-opacity="0.12"/>
            <stop offset="100%" stop-color="#18181b" stop-opacity="0.2"/>
          </linearGradient>
        </defs>
        <path d="{fill_d}" fill="url(#sf)"/>
        <path d="{path_d}" stroke="url(#lineAlpha)" stroke-width="2.5" stroke-linecap="round" fill="none"/>
      </svg>'''


def render_html(data):
    """Read template and replace all data placeholders."""
    html = TEMPLATE.read_text(encoding="utf-8")
    now = data["date"]

    # === FIX #4: Logo — convert relative to absolute path ===
    logo_abs = str(LOGO_PATH)
    html = html.replace('src="logo-3d.jpg"', f'src="file://{logo_abs}"')

    # --- Date ---
    day_num = str(now.day)
    month_en = MONTHS_EN[now.month]
    day_en = DAYS_EN[now.weekday()]
    date_line = f"{month_en} {now.year} · {day_en}"

    html = re.sub(r'(<span class="title-day">)\d+(<\/span>)', rf'\g<1>{day_num}\2', html)
    html = re.sub(
        r'(MARCH|JANUARY|FEBRUARY|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4}\s*·\s*\w+DAY',
        date_line, html
    )

    # --- BTC ---
    btc = data.get("btc", {})
    price = btc.get("price", 0)
    chg = btc.get("price_chg_7d", 0)
    chg_cls = "up" if chg >= 0 else "down"
    chg_sign = "+" if chg >= 0 else ""
    prices_7d = btc.get("prices_7d", [])

    # BTC price
    html = re.sub(
        r'(<div class="btc-price"><span class="btc-dollar">\$</span>)[^<]+(</div>)',
        rf'\g<1>{price:,.0f}\2', html
    )
    # BTC change (7d)
    html = re.sub(
        r'<span class="btc-change\s+(up|down)">[^<]+</span>',
        f'<span class="btc-change {chg_cls}">{chg_sign}{chg:.1f}% 7d</span>', html
    )

    # BTC sparkline SVG
    if prices_7d:
        spark_svg = btc_sparkline_svg(prices_7d)
        html = re.sub(
            r'(<div class="btc-spark-bg">)[\s\S]*?(</div>\s*<div style="position:relative;z-index:1;">)',
            rf'\1\n      {spark_svg}\n    \2', html
        )

    # BTC MCap estimate (price × ~19.8M supply)
    btc_supply = 19_800_000
    mcap = price * btc_supply

    # === FIX #2: Vol — we don't have volume data, replace with 7d range ===
    if prices_7d:
        lo7, hi7 = min(prices_7d), max(prices_7d)
        html = re.sub(r'Vol <b>[^<]+</b>', f'7d Low <b>${lo7:,.0f}</b>', html)
    html = re.sub(r'MCap <b>[^<]+</b>', f'MCap <b>{fmt_mcap(mcap)}</b>', html)

    # 24H Range → 7d Range (we only have daily data)
    if prices_7d:
        lo, hi = min(prices_7d), max(prices_7d)
        rng_pct = ((price - lo) / (hi - lo) * 100) if hi > lo else 50
        html = re.sub(
            r'(<div class="range-top">[\s\S]*?<span class="range-val">)\$[\d,]+(</span>[\s\S]*?)<span class="range-tag">24h Range</span>([\s\S]*?<span class="range-val">)\$[\d,]+(</span>)',
            rf'\g<1>${lo:,.0f}\2<span class="range-tag">7D RANGE</span>\3${hi:,.0f}\4', html
        )
        html = re.sub(r'(<div class="range-dot" style="left:)[\d.]+(%)', rf'\g<1>{rng_pct:.1f}\2', html)

    # vs Gold (BTC MCap / Gold MCap ~$17.1T)
    gold_mcap = 17.1e12
    gold_pct = mcap / gold_mcap * 100
    html = re.sub(r'(<div class="gold-fill" style="width:)[\d.]+(%)', rf'\g<1>{gold_pct:.1f}\2', html)
    html = re.sub(r'(<span class="gold-val">)[\d.]+(%)', rf'\g<1>{gold_pct:.1f}\2', html)

    # Total crypto market cap estimate (BTC MCap / BTC.D)
    btcd_val = data.get("btcd", {}).get("value", 58)
    total_mcap = mcap / (btcd_val / 100) if btcd_val > 0 else mcap * 1.7
    html = re.sub(r'(<div class="mcap-val">)\$[\d.]+T(</div>)', rf'\1{fmt_mcap(total_mcap)}\2', html)

    # --- AHR999 ---
    ahr = data.get("ahr999", {})
    ahr_val = ahr.get("value", 0)
    ahr_chg = ahr.get("chg_7d", 0)
    cost_200d = ahr.get("cost_200d", 0)
    fitted = ahr.get("fitted_price", 0)
    deviation = ahr.get("deviation", 0)

    # AHR value
    html = re.sub(
        r'(<div class="ahr-value"[^>]*>)[\d.]+(<\/div>)',
        rf'\g<1>{ahr_val:.2f}\2', html
    )

    # AHR gauge pointer position
    if ahr_val < 0.45:
        needle_in_seg = ahr_val / 0.45
        html = re.sub(
            r'(<div class="zone-seg" style="width:36%;background:rgba\(34,197,94,0\.35\);position:relative;">[\s\S]*?left:)\d+(%)',
            rf'\g<1>{needle_in_seg * 100:.0f}\2', html, count=1
        )

    # AHR extras
    html = re.sub(r'(200D 成本</span>\s*<span class="ahr-extra-val">)\$[\d,]+(</span>)',
                   rf'\g<1>{fmt_price(cost_200d)}\2', html)
    html = re.sub(r'(拟合价格</span>\s*<span class="ahr-extra-val">)\$[\d,]+(</span>)',
                   rf'\g<1>{fmt_price(fitted)}\2', html)

    # === FIX #1: 偏离度 — 加箭头让语义更清晰（↓ 低估=绿=好事，↑ 高估=红） ===
    dev_arrow = "↓" if deviation < 0 else "↑"
    dev_color = "#16a34a" if deviation < 0 else "#dc2626"
    html = re.sub(
        r'(偏离度</span>\s*<span class="ahr-extra-val"[^>]*>)[^<]+(</span>)',
        rf'\g<1>{dev_arrow}{abs(deviation):.1f}%\2', html
    )
    html = re.sub(
        r'(偏离度</span>\s*<span class="ahr-extra-val" style="color:)[^"]+(")',
        rf'\g<1>{dev_color}\2', html
    )

    # AHR 7d change
    ahr_chg_cls = "up" if ahr_chg >= 0 else "down"
    ahr_chg_sign = "+" if ahr_chg >= 0 else ""
    html = re.sub(
        r'(card-ahr[\s\S]*?<span class="card-change )(up|down)(">)[^<]+(</span>)',
        rf'\g<1>{ahr_chg_cls}\3{ahr_chg_sign}{ahr_chg:.1f}% 7d\4', html, count=1
    )

    # --- BMRI ---
    bmri = data.get("bmri", {})
    bmri_val = bmri.get("value", 50)
    fred = data.get("fred", {})

    html = re.sub(r'(<div class="bmri-num"[^>]*>)\d+(<\/div>)', rf'\g<1>{bmri_val:.0f}\2', html)
    html = re.sub(r'(<div class="bmri-gauge-needle" style="left:)\d+(%)', rf'\g<1>{bmri_val:.0f}\2', html)

    # === FIX #7: BMRI sub-factors — use real data, M2 from FRED WALCL ===
    dgs10 = fred.get("dgs10")
    vix = fred.get("vix")
    dxy = fred.get("dxy")
    m2 = fred.get("m2")

    factor_replacements = []
    if dgs10 is not None:
        factor_replacements.append(("10Y", f"{dgs10:.2f}%"))
    if m2 is not None:
        factor_replacements.append(("M2", f"{m2/1e12:.1f}T" if m2 > 1e6 else f"{m2:.1f}T"))
    if vix is not None:
        factor_replacements.append(("VIX", f"{vix:.1f}"))
    if dxy is not None:
        factor_replacements.append(("DXY", f"{dxy:.1f}"))

    for label, new_val in factor_replacements:
        html = re.sub(
            rf'(<div class="bmri-fv">)[^<]+(</div>\s*<div class="bmri-fn">{label}</div>)',
            rf'\g<1>{new_val}\2', html
        )

    # --- MVRV ---
    mvrv = data.get("mvrv", {})
    mvrv_val = mvrv.get("value", 1)
    mvrv_chg = mvrv.get("chg_7d", 0)
    mvrv_pct = mvrv.get("percentile", 50)
    mvrv_prev = mvrv.get("prev_cycle", PREV_CYCLE_MVRV)

    html = re.sub(r'(<div class="mvrv-value">)[\d.]+(<\/div>)', rf'\g<1>{mvrv_val:.2f}\2', html)

    # MVRV percentile
    html = re.sub(
        r'(<div class="mvrv-chip-val">)\d+%(</div>\s*<div class="mvrv-chip-label">历史百分位)',
        rf'\g<1>{mvrv_pct:.0f}%\2', html
    )

    # === FIX #3: MVRV 上轮同期 — use real calculated value ===
    html = re.sub(
        r'(<div class="mvrv-chip-val">)[\d.]+(<\/div>\s*<div class="mvrv-chip-label">上轮同期)',
        rf'\g<1>{mvrv_prev:.2f}\2', html
    )

    # MVRV gauge pointer position
    if mvrv_val <= 1:
        mvrv_needle_pct = (mvrv_val / 1) * 32
    elif mvrv_val <= 3:
        mvrv_needle_pct = 32 + ((mvrv_val - 1) / 2) * 38
    else:
        mvrv_needle_pct = 70 + ((mvrv_val - 3) / 1) * 30
    mvrv_needle_pct = max(2, min(98, mvrv_needle_pct))

    # Replace needle position: it's inside the first zone-seg as absolute positioned div
    # We need to set left instead of right for precise positioning
    html = re.sub(
        r'(card-mvrv[\s\S]*?<div class="zone-seg" style="width:32%;background:rgba\(34,197,94,0\.2\);position:relative;">[\s\S]*?style="position:absolute;)(right:\d+)(;top:-5px)',
        rf'\g<1>left:{mvrv_needle_pct:.0f}%\3', html, count=1
    )

    # MVRV 7d change
    mvrv_chg_cls = "up" if mvrv_chg >= 0 else "down"
    mvrv_chg_sign = "+" if mvrv_chg >= 0 else ""
    html = re.sub(
        r'(card-mvrv[\s\S]*?<span class="card-change )(up|down)(">)[^<]+(</span>)',
        rf'\g<1>{mvrv_chg_cls}\3{mvrv_chg_sign}{mvrv_chg:.1f}% 7d\4', html, count=1
    )

    # --- BTC.D ---
    btcd_data = data.get("btcd", {})
    btcd_v = btcd_data.get("value", 58)
    btcd_chg = btcd_data.get("chg_7d", 0)
    eth_pct = max(1, min(30, 100 - btcd_v - 23))
    alt_pct = max(1, 100 - btcd_v - eth_pct)

    html = re.sub(r'(<span class="btcd-num">)[\d.]+(<\/span>)', rf'\g<1>{btcd_v:.1f}\2', html)

    # BTC.D bars + market caps
    html = re.sub(
        r'(BTC</span>[\s\S]*?<div class="btcd-bar-fill" style="width:)[\d.]+(%)',
        rf'\g<1>{btcd_v:.1f}\2', html, count=1
    )
    html = re.sub(
        r'(BTC</span>[\s\S]*?<span class="btcd-bar-val">)\$[\d.]+T(<\/span>)',
        rf'\g<1>{fmt_mcap(mcap)}\2', html, count=1
    )

    eth_mcap = total_mcap * (eth_pct / 100)
    html = re.sub(
        r'(ETH</span>[\s\S]*?<div class="btcd-bar-fill" style="width:)[\d.]+(%)',
        rf'\g<1>{eth_pct:.0f}\2', html, count=1
    )
    html = re.sub(
        r'(ETH</span>[\s\S]*?<span class="btcd-bar-val">)\$[\d.]+T(<\/span>)',
        rf'\g<1>{fmt_mcap(eth_mcap)}\2', html, count=1
    )

    alt_mcap = total_mcap * (alt_pct / 100)
    html = re.sub(
        r'(ALT</span>[\s\S]*?<div class="btcd-bar-fill" style="width:)[\d.]+(%)',
        rf'\g<1>{alt_pct:.1f}\2', html, count=1
    )
    html = re.sub(
        r'(ALT</span>[\s\S]*?<span class="btcd-bar-val">)\$[\d.]+T(<\/span>)',
        rf'\g<1>{fmt_mcap(alt_mcap)}\2', html, count=1
    )

    # BTC.D 7d change
    btcd_chg_cls = "up" if btcd_chg >= 0 else "down"
    btcd_chg_sign = "+" if btcd_chg >= 0 else ""
    html = re.sub(
        r'(card-btcd[\s\S]*?<span class="card-change )(up|down)(">)[^<]+(</span>)',
        rf'\g<1>{btcd_chg_cls}\3{btcd_chg_sign}{btcd_chg:.1f}% 7d\4', html, count=1
    )

    # --- Governance ---
    gov = data.get("governance")
    if gov:
        # === FIX #8: 治理投票进度 — 无数据时隐藏投票条，只显示状态 ===
        html = re.sub(r'(\[ARFC\] 激活 Aave Buyback 回购机制)', gov["title"], html)
        html = re.sub(
            r'(<div class="gov-desc">)[^<]+(</div>)',
            rf'\g<1>{gov["summary_zh"]}\2', html
        )
        html = re.sub(
            r'(<span class="gov-protocol">)[^<]+(</span>)',
            rf'\g<1>{gov["protocol"]}\2', html
        )
        end_str = gov.get("end", "")
        if end_str:
            try:
                end_dt = datetime.fromisoformat(end_str)
                end_display = f"截止 {end_dt.month}月{end_dt.day}日"
            except Exception:
                end_display = "进行中"
        else:
            end_display = "进行中"
        html = re.sub(
            r'(<span class="gov-detail">)[^<]+(</span>)',
            rf'\g<1>{end_display}\2', html
        )
        # Hide vote bar + label if no vote data (keep gov-status-row structure intact)
        vote_pct = gov.get("vote_pct", 0)
        if not vote_pct:
            html = re.sub(
                r'<div class="gov-vote-inline">[\s\S]*?<div class="gov-vote-label">[^<]*</div>\s*</div>',
                '', html, count=1
            )
    else:
        # No active governance - hide the entire card
        html = re.sub(
            r'(<div class="card card-gov">)',
            r'<div class="card card-gov" style="display:none;">',
            html, count=1
        )

    # === FIX #5: Layout — fill 1920px, no bottom gap ===
    # Fix BMRI: remove flex:1 from the number wrapper div
    html = html.replace(
        'style="display:flex;align-items:center;justify-content:center;flex:1;"',
        'style="display:flex;align-items:center;justify-content:center;padding:8px 0;"'
    )

    # === FIX #5: Scale up entire poster to fill 1920px ===
    # Content naturally takes ~1490px. Scale 1920/1490 ≈ 1.289x
    # Set inner dimensions to 1080/1.289 × 1920/1.289, then CSS zoom up
    SCALE = 1.289
    inner_w = round(1080 / SCALE)  # ~838
    inner_h = round(1920 / SCALE)  # ~1489

    # Replace body dimensions + add zoom
    html = html.replace(
        'width: 1080px;\n  height: 1920px;\n  background: #f5f5f7;',
        f'width: {inner_w}px;\n  height: {inner_h}px;\n  background: #f5f5f7;\n  zoom: {SCALE};'
    )
    # Replace poster dimensions
    html = html.replace(
        'width: 1080px;\n  height: 1920px;\n  padding:',
        f'width: {inner_w}px;\n  height: {inner_h}px;\n  padding:'
    )

    card_fix_css = """
/* === Card alignment fixes === */
.two-col { align-items: stretch !important; }
.two-col > .card { display: flex !important; flex-direction: column !important; }
.card-ahr .card-footer { margin-top: auto; }
.card-bmri .bmri-factors { margin-top: auto; }
.card-mvrv .mvrv-chips { margin-top: auto; }
.card-mvrv .card-footer { margin-top: 8px; }
.card-btcd .card-footer { margin-top: auto; }

/* === BTC bottom row: align the two progress bars horizontally === */
/* range-block: label(15px) + mb(6px) + track(7px) = track starts at ~21px from top
   gold-block:  label(15px) + mb(6px) + row with track = track starts at ~21px from top
   The gold-row has align-items:center with the gold-val (20px text) which pushes
   the 8px track up. Fix: give gold-row explicit top margin to push track down. */
.gold-row {
  margin-top: 3px !important;
}
.range-top {
  margin-bottom: 17px !important;
}
"""
    html = html.replace('</style>', card_fix_css + '</style>')

    return html


async def screenshot(html_path, png_path):
    """Take screenshot with Playwright."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(2000)  # Wait for fonts to load
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()


async def main():
    print("[1/4] Collecting data...")
    data = collect_data()

    # Print summary
    btc = data.get("btc", {})
    print(f"  BTC: {fmt_price(btc.get('price', 0))} ({btc.get('price_chg_7d', 0):+.1f}% 7d)")
    ahr = data.get("ahr999", {})
    print(f"  AHR999: {ahr.get('value', 0):.2f} ({ahr.get('chg_7d', 0):+.1f}% 7d)")
    mvrv = data.get("mvrv", {})
    print(f"  MVRV: {mvrv.get('value', 0):.2f} (P{mvrv.get('percentile', 0):.0f}, prev cycle: {mvrv.get('prev_cycle', 0):.2f})")
    bmri = data.get("bmri", {})
    print(f"  BMRI: {bmri.get('value', 0):.0f} ({bmri.get('regime', '')})")
    btcd = data.get("btcd", {})
    print(f"  BTC.D: {btcd.get('value', 0):.1f}%")
    gov = data.get("governance")
    if gov:
        print(f"  Governance: {gov['protocol']} - {gov['title'][:40]}...")
    else:
        print("  Governance: none active")

    print("\n[2/4] Rendering HTML...")
    html = render_html(data)

    now = data["date"]
    ts = now.strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{ts}.html"
    png_path = OUTPUT_DIR / f"{ts}.png"

    html_path.write_text(html, encoding="utf-8")
    print(f"  → {html_path}")

    print("\n[3/4] Taking screenshot...")
    await screenshot(html_path, png_path)
    print(f"  → {png_path}")

    # Also copy to output.png for quick access
    latest_path = SCRIPT_DIR / "output.png"
    import shutil
    shutil.copy2(png_path, latest_path)
    print(f"  → {latest_path} (latest)")

    print(f"\n[4/4] Done! Poster generated for {ts}")
    return str(png_path)


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nOutput: {result}")
