#!/usr/bin/env python3
"""Crypto3D Daily Poster - 手机优化版"""
import json
import asyncio
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None


def load_all():
    data = {}

    ahr999 = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr999:
        c = ahr999["current"]
        h = ahr999.get("history", [])
        data["ahr999"] = {
            "value": c["value"],
            "status": c["status"],
            "price": c["price"],
            "cost_200d": c["cost_200d"],
            "fitted": c.get("fitted_price", 0),
            "prices": [x["close"] for x in h[-7:]],
        }

    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c = mvrv["current"]
        h = mvrv.get("history", [])
        data["mvrv"] = {
            "value": c["value"],
            "status": c["status"],
            "week": [x["mvrv"] for x in h[-7:]],
        }

    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri:
        c = bmri["1m"]["current"]
        h = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": c["value"],
            "regime": c["regime"],
            "week": [x["bmri"] for x in h[-7:]],
        }

    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c = btcd["current"]
        h = btcd.get("history", [])
        data["btcd"] = {
            "value": c["value"],
            "zone": c["zone"],
            "week": [x["value"] for x in h[-7:]],
        }

    return data


def select_focus(data):
    a = data.get("ahr999", {}).get("value", 1)
    m = data.get("mvrv", {}).get("value", 1)
    b = data.get("bmri", {}).get("value", 50)
    if a < 0.5:
        return "ahr999"
    if m > 3:
        return "mvrv"
    if b < 30 or b > 70:
        return "bmri"
    wd = datetime.now().weekday()
    return ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"][wd]


def sparkline(vals, color, w=120, h=28):
    if not vals or len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h - 8)) - 4
        pts.append(f"{x:.0f},{y:.0f}")
    ly = h - ((vals[-1] - mn) / rng * (h - 8)) - 4
    pts_str = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block">'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{pts_str}"/>'
        f'<circle cx="{w}" cy="{ly:.0f}" r="4" fill="{color}"/>'
        f'</svg>'
    )


def area_chart(vals, color, w=900, h=120):
    if not vals or len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h - 20)) - 10
        pts.append(f"{x:.0f},{y:.0f}")
    fill_pts = pts + [f"{w},{h}", f"0,{h}"]
    pts_str = " ".join(pts)
    fill_str = " ".join(fill_pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:{h}px">'
        f'<defs>'
        f'<linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<polygon fill="url(#ag)" points="{fill_str}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="3.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{pts_str}"/>'
        f'</svg>'
    )


def gauge_bar(value, min_v, max_v, zones, w=800):
    rng = max_v - min_v
    pos = (value - min_v) / rng * w
    pos = max(12, min(pos, w - 12))

    zone_rects = ""
    for z in zones:
        x1 = (z["from"] - min_v) / rng * w
        x2 = (z["to"] - min_v) / rng * w
        zone_rects += (
            f'<rect x="{x1:.0f}" y="0" width="{x2-x1:.0f}" height="12" '
            f'rx="6" fill="{z["color"]}" opacity="0.2"/>'
        )

    zone_labels = ""
    for z in zones:
        x = ((z["from"] + z["to"]) / 2 - min_v) / rng * w
        zone_labels += (
            f'<text x="{x:.0f}" y="38" text-anchor="middle" '
            f'font-size="18" fill="#71717a" font-family="DM Sans,sans-serif">{z["label"]}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} 48" style="display:block;width:100%;height:48px">'
        f'{zone_rects}'
        f'<circle cx="{pos:.0f}" cy="6" r="9" fill="#fafafa"/>'
        f'<circle cx="{pos:.0f}" cy="6" r="4" fill="#09090b"/>'
        f'{zone_labels}'
        f'</svg>'
    )


def get_color(status):
    s = str(status).lower()
    if any(k in s for k in ["抄底", "合理", "neutral", "balanced", "low", "fair"]):
        return "#4ade80"
    if any(k in s for k in ["过热", "high", "extreme", "danger"]):
        return "#f87171"
    return "#60a5fa"


def render(focus, data):
    today = datetime.now().strftime("%Y.%m.%d")

    # === BTC ===
    ahr = data.get("ahr999", {})
    prices = ahr.get("prices", [])
    btc_price = ahr.get("price", 0)
    btc_area = area_chart(prices, "#f59e0b", 900, 120)

    btc_chg = ""
    if len(prices) >= 2:
        ch = ((prices[-1] - prices[0]) / prices[0]) * 100
        chg_color = "#4ade80" if ch > 0 else "#f87171"
        chg_sign = "+" if ch > 0 else ""
        btc_chg = f'<span class="chg" style="color:{chg_color}">{chg_sign}{ch:.1f}%</span>'

    # === 主卡 ===
    fd = data.get(focus, {})
    fval = fd.get("value", 0)
    fstatus = fd.get("status", fd.get("regime", ""))
    fcolor = get_color(fstatus)

    if focus == "ahr999":
        cost = ahr.get("cost_200d", 1)
        ratio = int(btc_price / cost * 100) if cost else 0
        gauge = gauge_bar(fval, 0, 1.5, [
            {"from": 0, "to": 0.45, "color": "#4ade80", "label": "抄底"},
            {"from": 0.45, "to": 1.2, "color": "#facc15", "label": "定投"},
            {"from": 1.2, "to": 1.5, "color": "#f87171", "label": "观望"},
        ])
        insight = f'价格 = 200日成本的 <strong>{ratio}%</strong> · 定投成本 ${cost:,.0f}'
        main_html = f'''
    <div class="card">
      <div class="card-top">
        <div class="card-label">🔥 AHR999</div>
        <div class="card-st" style="color:{fcolor}">{fstatus}</div>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.2f}</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">{insight}</div>
    </div>'''

    elif focus == "mvrv":
        gauge = gauge_bar(fval, 0, 4, [
            {"from": 0, "to": 1, "color": "#4ade80", "label": "低估"},
            {"from": 1, "to": 3, "color": "#facc15", "label": "合理"},
            {"from": 3, "to": 4, "color": "#f87171", "label": "过热"},
        ])
        pnl = int((fval - 1) * 100)
        insight = f'持币者整体盈利 <strong>{pnl}%</strong> · MVRV&lt;1 为历史底部'
        main_html = f'''
    <div class="card">
      <div class="card-top">
        <div class="card-label">📈 MVRV</div>
        <div class="card-st" style="color:{fcolor}">{fstatus}</div>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.2f}</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">{insight}</div>
    </div>'''

    elif focus == "bmri":
        risk = "低风险" if fval < 30 else "高风险" if fval > 70 else "中性"
        gauge = gauge_bar(fval, 0, 100, [
            {"from": 0, "to": 30, "color": "#4ade80", "label": "低风险"},
            {"from": 30, "to": 70, "color": "#facc15", "label": "中性"},
            {"from": 70, "to": 100, "color": "#f87171", "label": "高风险"},
        ])
        insight = '综合流动性、利率、市场风险多维评估'
        main_html = f'''
    <div class="card">
      <div class="card-top">
        <div class="card-label">⚠️ BMRI</div>
        <div class="card-st" style="color:{fcolor}">{risk}</div>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.1f}</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">{insight}</div>
    </div>'''

    else:
        zone = fd.get("zone", "BALANCED")
        zt = "BTC主导" if zone == "BTC_DOMINANT" else "山寨季" if zone == "ALT_SEASON" else "平衡"
        gauge = gauge_bar(fval, 40, 70, [
            {"from": 40, "to": 50, "color": "#4ade80", "label": "山寨季"},
            {"from": 50, "to": 60, "color": "#facc15", "label": "平衡"},
            {"from": 60, "to": 70, "color": "#f87171", "label": "BTC主导"},
        ])
        insight = 'BTC 市值占加密总市值比例'
        main_html = f'''
    <div class="card">
      <div class="card-top">
        <div class="card-label">₿ BTC.D</div>
        <div class="card-st" style="color:{fcolor}">{zt}</div>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.1f}%</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">{insight}</div>
    </div>'''

    # === 副指标 ===
    sub_order = {
        "ahr999": ["mvrv", "bmri", "btcd"],
        "mvrv": ["ahr999", "bmri", "btcd"],
        "bmri": ["ahr999", "mvrv", "btcd"],
        "btcd": ["ahr999", "mvrv", "bmri"],
    }
    rows = []
    for name in sub_order.get(focus, ["mvrv", "bmri", "btcd"]):
        d = data.get(name, {})
        v = d.get("value", 0)
        st = d.get("status", d.get("regime", d.get("zone", "")))
        c = get_color(st)
        wk = d.get("week", [])
        sp = sparkline(wk, c, 120, 28)

        if name == "ahr999":
            lb, vs, stx = "AHR999", f"{v:.2f}", d.get("status", "")
        elif name == "mvrv":
            lb, vs, stx = "MVRV", f"{v:.2f}", d.get("status", "")
        elif name == "bmri":
            lb, vs = "BMRI", f"{v:.1f}"
            stx = "低风险" if v < 30 else "高风险" if v > 70 else "中性"
        else:
            lb, vs = "BTC.D", f"{v:.1f}%"
            z = d.get("zone", "BALANCED")
            stx = "BTC主导" if z == "BTC_DOMINANT" else "山寨季" if z == "ALT_SEASON" else "平衡"

        rows.append(f'''
      <div class="row">
        <span class="r-lb">{lb}</span>
        <span class="r-val" style="color:{c}">{vs}</span>
        <span class="r-sp">{sp}</span>
        <span class="r-st" style="color:{c}">{stx}</span>
      </div>''')

    subs_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'DM Sans', sans-serif;
  background: #09090b;
  color: #fafafa;
  width: 1080px;
  height: 1350px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}

/* Header */
.hdr {{
  padding: 52px 72px 0;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}}
.brand {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 36px;
  font-weight: 700;
}}
.date {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 22px;
  color: #52525b;
}}

/* BTC */
.btc {{
  padding: 36px 72px 0;
}}
.btc-row {{
  display: flex;
  align-items: baseline;
  gap: 20px;
  margin-bottom: 20px;
}}
.btc-lb {{
  font-size: 18px;
  color: #52525b;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-weight: 500;
}}
.btc-p {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 52px;
  font-weight: 700;
}}
.chg {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 22px;
  font-weight: 600;
}}
.btc-area {{
  margin: 0 -72px;
  padding: 0 72px;
}}

/* Divider */
.div {{
  margin: 36px 72px;
  height: 1px;
  background: #27272a;
}}

/* Card */
.card {{
  margin: 0 72px;
  background: linear-gradient(160deg, #141416 0%, #0c0c0e 100%);
  border: 1px solid #1e1e22;
  border-radius: 28px;
  padding: 40px 48px;
}}
.card-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}}
.card-label {{
  font-size: 22px;
  color: #71717a;
  font-weight: 500;
}}
.card-st {{
  font-size: 22px;
  font-weight: 700;
}}
.card-num {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 96px;
  font-weight: 700;
  letter-spacing: -3px;
  margin: 4px 0 20px;
}}
.card-gauge {{
  margin-bottom: 24px;
}}
.card-insight {{
  font-size: 20px;
  color: #a1a1aa;
  line-height: 1.6;
  border-top: 1px solid #27272a;
  padding-top: 20px;
}}
.card-insight strong {{
  color: #fafafa;
  font-weight: 700;
}}

/* Subs */
.subs {{
  padding: 0 72px;
}}
.row {{
  display: grid;
  grid-template-columns: 100px 100px 140px 1fr;
  align-items: center;
  gap: 20px;
  padding: 20px 0;
  border-bottom: 1px solid #1a1a1d;
}}
.row:last-child {{ border-bottom: none; }}
.r-lb {{
  font-size: 18px;
  color: #71717a;
  font-weight: 600;
}}
.r-val {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 26px;
  font-weight: 700;
}}
.r-sp {{
  height: 28px;
}}
.r-st {{
  font-size: 18px;
  font-weight: 600;
  text-align: right;
}}

/* Footer */
.ftr {{
  margin-top: auto;
  padding: 36px 72px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  color: #3f3f46;
}}
.ftr-link {{
  color: #3b82f6;
  font-weight: 600;
  font-size: 20px;
}}
</style>
</head>
<body>

<div class="hdr">
  <div class="brand">Crypto3D</div>
  <div class="date">{today}</div>
</div>

<div class="btc">
  <div class="btc-row">
    <span class="btc-lb">Bitcoin</span>
    <span class="btc-p">${btc_price:,}</span>
    {btc_chg}
  </div>
  <div class="btc-area">{btc_area}</div>
</div>

<div class="div"></div>

{main_html}

<div class="div"></div>

<div class="subs">
{subs_html}
</div>

<div class="ftr">
  <span>Daily Market Snapshot</span>
  <span class="ftr-link">crypto3d.pro</span>
</div>

</body>
</html>"""


async def generate():
    print("[1/4] 加载数据...")
    data = load_all()

    print("[2/4] 选择焦点...")
    focus = select_focus(data)
    print(f"  焦点: {focus.upper()}")

    print("[3/4] 渲染...")
    html = render(focus, data)

    today_str = datetime.now().strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{today_str}.html"
    with open(html_path, "w") as f:
        f.write(html)

    print("[4/4] 截图...")
    png_path = OUTPUT_DIR / f"{today_str}.png"

    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()

    print(f"[OK] {png_path}")
    return png_path


if __name__ == "__main__":
    asyncio.run(generate())
