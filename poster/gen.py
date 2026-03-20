#!/usr/bin/env python3
"""Crypto3D Daily Poster - 信息图版"""
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


def sparkline(vals, color, w=80, h=20):
    """生成迷你折线 SVG"""
    if not vals or len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h - 6)) - 3
        pts.append(f"{x:.0f},{y:.0f}")
    ly = h - ((vals[-1] - mn) / rng * (h - 6)) - 3
    pts_str = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{pts_str}"/>'
        f'<circle cx="{w}" cy="{ly:.0f}" r="2.5" fill="{color}"/>'
        f'</svg>'
    )


def area_chart(vals, color, w=900, h=80):
    """生成面积图 SVG"""
    if not vals or len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h - 16)) - 8
        pts.append(f"{x:.0f},{y:.0f}")
    # 闭合路径做面积
    fill_pts = pts + [f"{w},{h}", f"0,{h}"]
    pts_str = " ".join(pts)
    fill_str = " ".join(fill_pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:{h}px">'
        f'<defs>'
        f'<linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<polygon fill="url(#ag)" points="{fill_str}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{pts_str}"/>'
        f'</svg>'
    )


def gauge_bar(value, min_v, max_v, zones, w=800):
    """生成标尺条 SVG"""
    rng = max_v - min_v
    pos = (value - min_v) / rng * w
    pos = max(8, min(pos, w - 8))

    zone_rects = ""
    for z in zones:
        x1 = (z["from"] - min_v) / rng * w
        x2 = (z["to"] - min_v) / rng * w
        zone_rects += (
            f'<rect x="{x1:.0f}" y="0" width="{x2-x1:.0f}" height="8" '
            f'rx="4" fill="{z["color"]}" opacity="0.25"/>'
        )

    zone_labels = ""
    for z in zones:
        x = ((z["from"] + z["to"]) / 2 - min_v) / rng * w
        zone_labels += (
            f'<text x="{x:.0f}" y="28" text-anchor="middle" '
            f'font-size="11" fill="#71717a" font-family="DM Sans">{z["label"]}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} 36" style="display:block;width:100%;height:36px">'
        f'{zone_rects}'
        f'<circle cx="{pos:.0f}" cy="4" r="6" fill="#fafafa"/>'
        f'<circle cx="{pos:.0f}" cy="4" r="3" fill="#09090b"/>'
        f'{zone_labels}'
        f'</svg>'
    )


def get_color(status):
    s = str(status).lower()
    if any(k in s for k in ["抄底", "合理", "neutral", "balanced", "low", "fair"]):
        return "#22c55e"
    if any(k in s for k in ["过热", "high", "extreme", "danger"]):
        return "#ef4444"
    return "#3b82f6"


def render(focus, data):
    today = datetime.now().strftime("%Y.%m.%d")

    # === BTC 价格 ===
    ahr = data.get("ahr999", {})
    prices = ahr.get("prices", [])
    btc_price = ahr.get("price", 0)
    btc_area = area_chart(prices, "#f59e0b", 900, 80)

    btc_chg = ""
    if len(prices) >= 2:
        ch = ((prices[-1] - prices[0]) / prices[0]) * 100
        chg_color = "#22c55e" if ch > 0 else "#ef4444"
        chg_sign = "+" if ch > 0 else ""
        btc_chg = f'<span class="btc-chg" style="color:{chg_color}">7d {chg_sign}{ch:.1f}%</span>'

    # === 主卡片 ===
    fd = data.get(focus, {})
    fval = fd.get("value", 0)
    fstatus = fd.get("status", fd.get("regime", ""))
    fcolor = get_color(fstatus)

    if focus == "ahr999":
        cost = ahr.get("cost_200d", 1)
        ratio = int(btc_price / cost * 100) if cost else 0
        gauge = gauge_bar(fval, 0, 1.5, [
            {"from": 0, "to": 0.45, "color": "#22c55e", "label": "抄底"},
            {"from": 0.45, "to": 1.2, "color": "#eab308", "label": "定投"},
            {"from": 1.2, "to": 1.5, "color": "#ef4444", "label": "观望"},
        ])
        main_html = f'''
    <div class="card">
      <div class="card-hd">
        <span class="card-icon">🔥</span>
        <span class="card-name">AHR999</span>
        <span class="card-status" style="color:{fcolor}">{fstatus}</span>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.2f}</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">
        BTC 价格仅为 200 日定投成本的 <strong>{ratio}%</strong><br>
        当前定投成本 ${cost:,.0f}，拟合价值 ${ahr.get("fitted", 0):,.0f}
      </div>
    </div>'''

    elif focus == "mvrv":
        gauge = gauge_bar(fval, 0, 4, [
            {"from": 0, "to": 1, "color": "#22c55e", "label": "低估"},
            {"from": 1, "to": 3, "color": "#eab308", "label": "合理"},
            {"from": 3, "to": 4, "color": "#ef4444", "label": "过热"},
        ])
        main_html = f'''
    <div class="card">
      <div class="card-hd">
        <span class="card-icon">📈</span>
        <span class="card-name">MVRV</span>
        <span class="card-status" style="color:{fcolor}">{fstatus}</span>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.2f}</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">
        市场整体持币者盈利 <strong>{int((fval-1)*100)}%</strong><br>
        MVRV &lt; 1 为历史底部区域
      </div>
    </div>'''

    elif focus == "bmri":
        risk_text = "低风险" if fval < 30 else "高风险" if fval > 70 else "中性"
        gauge = gauge_bar(fval, 0, 100, [
            {"from": 0, "to": 30, "color": "#22c55e", "label": "低风险"},
            {"from": 30, "to": 70, "color": "#eab308", "label": "中性"},
            {"from": 70, "to": 100, "color": "#ef4444", "label": "高风险"},
        ])
        main_html = f'''
    <div class="card">
      <div class="card-hd">
        <span class="card-icon">⚠️</span>
        <span class="card-name">BMRI</span>
        <span class="card-status" style="color:{fcolor}">{risk_text}</span>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.1f}</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">
        综合流动性、利率、市场风险多维度评估
      </div>
    </div>'''

    else:  # btcd
        zone = fd.get("zone", "BALANCED")
        zt = "BTC主导" if zone == "BTC_DOMINANT" else "山寨季" if zone == "ALT_SEASON" else "平衡"
        gauge = gauge_bar(fval, 40, 70, [
            {"from": 40, "to": 50, "color": "#22c55e", "label": "山寨季"},
            {"from": 50, "to": 60, "color": "#eab308", "label": "平衡"},
            {"from": 60, "to": 70, "color": "#ef4444", "label": "BTC主导"},
        ])
        main_html = f'''
    <div class="card">
      <div class="card-hd">
        <span class="card-icon">₿</span>
        <span class="card-name">BTC.D</span>
        <span class="card-status" style="color:{fcolor}">{zt}</span>
      </div>
      <div class="card-num" style="color:{fcolor}">{fval:.1f}%</div>
      <div class="card-gauge">{gauge}</div>
      <div class="card-insight">
        BTC 市值占加密总市值的比例
      </div>
    </div>'''

    # === 副指标行 ===
    sub_items = []
    sub_order = {
        "ahr999": ["mvrv", "bmri", "btcd"],
        "mvrv": ["ahr999", "bmri", "btcd"],
        "bmri": ["ahr999", "mvrv", "btcd"],
        "btcd": ["ahr999", "mvrv", "bmri"],
    }
    for name in sub_order.get(focus, ["mvrv", "bmri", "btcd"]):
        d = data.get(name, {})
        v = d.get("value", 0)
        st = d.get("status", d.get("regime", d.get("zone", "")))
        c = get_color(st)
        wk = d.get("week", d.get("week_data", []))
        sp = sparkline(wk, c, 80, 18)

        if name == "ahr999":
            label = "AHR999"
            vstr = f"{v:.2f}"
            st_text = d.get("status", "")
        elif name == "mvrv":
            label = "MVRV"
            vstr = f"{v:.2f}"
            st_text = d.get("status", "")
        elif name == "bmri":
            label = "BMRI"
            vstr = f"{v:.1f}"
            st_text = "低" if v < 30 else "高" if v > 70 else "中性"
        else:
            label = "BTC.D"
            vstr = f"{v:.1f}%"
            z = d.get("zone", "BALANCED")
            st_text = "BTC主导" if z == "BTC_DOMINANT" else "山寨季" if z == "ALT_SEASON" else "平衡"

        sub_items.append(f'''
      <div class="row">
        <span class="row-name">{label}</span>
        <span class="row-val" style="color:{c}">{vstr}</span>
        <span class="row-chart">{sp}</span>
        <span class="row-st" style="color:{c}">{st_text}</span>
      </div>''')

    subs_html = "\n".join(sub_items)

    # === 完整 HTML ===
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

/* ── Header ── */
.hdr {{
  padding: 56px 72px 0;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}}
.brand {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}}
.date {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 16px;
  color: #52525b;
  font-weight: 500;
}}

/* ── BTC Section ── */
.btc {{
  padding: 40px 72px 0;
}}
.btc-top {{
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 16px;
}}
.btc-label {{
  font-size: 13px;
  color: #52525b;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 500;
}}
.btc-price {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 40px;
  font-weight: 700;
  color: #fafafa;
}}
.btc-chg {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 16px;
  font-weight: 500;
}}
.btc-chart {{
  margin: 0 -72px;
  padding: 0 72px;
}}

/* ── Divider ── */
.divider {{
  margin: 40px 72px;
  height: 1px;
  background: #27272a;
}}

/* ── Main Card ── */
.card {{
  margin: 0 72px;
  background: linear-gradient(160deg, #141416 0%, #0c0c0e 100%);
  border: 1px solid #1e1e22;
  border-radius: 24px;
  padding: 40px 44px;
}}
.card-hd {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}}
.card-icon {{ font-size: 24px; }}
.card-name {{
  font-size: 14px;
  color: #52525b;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 500;
}}
.card-status {{
  margin-left: auto;
  font-size: 14px;
  font-weight: 700;
}}
.card-num {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 72px;
  font-weight: 700;
  letter-spacing: -2px;
  margin: 8px 0 24px;
}}
.card-gauge {{
  margin-bottom: 24px;
}}
.card-insight {{
  font-size: 15px;
  color: #a1a1aa;
  line-height: 1.7;
  border-top: 1px solid #27272a;
  padding-top: 20px;
}}
.card-insight strong {{
  color: #fafafa;
}}

/* ── Sub Rows ── */
.subs {{
  padding: 0 72px;
  display: flex;
  flex-direction: column;
  gap: 0;
}}
.row {{
  display: grid;
  grid-template-columns: 80px 80px 100px 1fr;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid #1a1a1d;
}}
.row:last-child {{ border-bottom: none; }}
.row-name {{
  font-size: 13px;
  color: #52525b;
  font-weight: 500;
  letter-spacing: 0.5px;
}}
.row-val {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 18px;
  font-weight: 700;
}}
.row-chart {{
  height: 18px;
}}
.row-st {{
  font-size: 13px;
  font-weight: 500;
  text-align: right;
}}

/* ── Footer ── */
.ftr {{
  margin-top: auto;
  padding: 32px 72px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #3f3f46;
}}
.ftr a {{
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
}}
</style>
</head>
<body>

<div class="hdr">
  <div class="brand">Crypto3D</div>
  <div class="date">{today}</div>
</div>

<div class="btc">
  <div class="btc-top">
    <span class="btc-label">Bitcoin</span>
    <span class="btc-price">${btc_price:,}</span>
    {btc_chg}
  </div>
  <div class="btc-chart">{btc_area}</div>
</div>

<div class="divider"></div>

{main_html}

<div class="divider"></div>

<div class="subs">
{subs_html}
</div>

<div class="ftr">
  <span>Daily Market Snapshot</span>
  <a href="https://crypto3d.pro">crypto3d.pro</a>
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
