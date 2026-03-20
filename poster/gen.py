#!/usr/bin/env python3
"""Crypto3D Daily Poster - Premium Edition"""
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
            "value": c["value"], "status": c["status"],
            "price": c["price"], "cost_200d": c["cost_200d"],
            "fitted": c.get("fitted_price", 0),
            "prices": [x["close"] for x in h[-7:]],
        }
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c = mvrv["current"]
        h = mvrv.get("history", [])
        data["mvrv"] = {"value": c["value"], "status": c["status"],
                        "week": [x["mvrv"] for x in h[-7:]]}
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri:
        c = bmri["1m"]["current"]
        h = bmri["1m"].get("history", [])
        data["bmri"] = {"value": c["value"], "regime": c["regime"],
                        "week": [x["bmri"] for x in h[-7:]]}
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c = btcd["current"]
        h = btcd.get("history", [])
        data["btcd"] = {"value": c["value"], "zone": c["zone"],
                        "week": [x["value"] for x in h[-7:]]}
    return data


def select_focus(data):
    a = data.get("ahr999", {}).get("value", 1)
    m = data.get("mvrv", {}).get("value", 1)
    b = data.get("bmri", {}).get("value", 50)
    if a < 0.5: return "ahr999"
    if m > 3: return "mvrv"
    if b < 30 or b > 70: return "bmri"
    wd = datetime.now().weekday()
    return ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"][wd]


def get_color(status):
    s = str(status).lower()
    if any(k in s for k in ["抄底", "合理", "neutral", "balanced", "low", "fair"]):
        return "#4ade80"
    if any(k in s for k in ["过热", "high", "extreme", "danger"]):
        return "#f87171"
    return "#60a5fa"


def sparkline(vals, color, w=120, h=28):
    if not vals or len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h - 8)) - 4
        pts.append(f"{x:.0f},{y:.0f}")
    ly = h - ((vals[-1] - mn) / rng * (h - 8)) - 4
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{" ".join(pts)}"/>'
        f'<circle cx="{w}" cy="{ly:.0f}" r="3.5" fill="{color}"/>'
        f'</svg>'
    )


def area_chart(vals, color, w=940, h=130):
    if not vals or len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h - 24)) - 12
        pts.append(f"{x:.0f},{y:.0f}")
    fill_pts = pts + [f"{w},{h}", f"0,{h}"]
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%">'
        f'<defs>'
        f'<linearGradient id="agrad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<polygon fill="url(#agrad)" points="{" ".join(fill_pts)}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{" ".join(pts)}"/>'
        f'</svg>'
    )


def gauge(value, min_v, max_v, zones):
    """精致标尺"""
    w = 840
    rng = max_v - min_v
    pos = max(10, min((value - min_v) / rng * w, w - 10))

    # 渐变轨道
    colors = "|".join([f"{z['color']} {(z['from']-min_v)/rng*100:.0f}%,{z['color']} {(z['to']-min_v)/rng*100:.0f}%" for z in zones])

    track = ""
    for z in zones:
        x1 = (z["from"] - min_v) / rng * w
        x2 = (z["to"] - min_v) / rng * w
        track += f'<rect x="{x1:.0f}" y="8" width="{x2-x1:.0f}" height="6" fill="{z["color"]}" opacity="0.15" rx="3"/>'

    # 高亮到当前位置
    active_color = zones[0]["color"]
    for z in zones:
        if z["from"] <= value <= z["to"]:
            active_color = z["color"]
            break
    track += f'<rect x="0" y="8" width="{pos:.0f}" height="6" fill="{active_color}" opacity="0.5" rx="3"/>'

    labels = ""
    for z in zones:
        x = ((z["from"] + z["to"]) / 2 - min_v) / rng * w
        labels += f'<text x="{x:.0f}" y="40" text-anchor="middle" font-size="16" fill="#52525b" font-family="DM Sans,sans-serif" font-weight="500">{z["label"]}</text>'

    return (
        f'<svg viewBox="0 0 {w} 48" style="display:block;width:100%">'
        f'{track}'
        f'<circle cx="{pos:.0f}" cy="11" r="8" fill="{active_color}" opacity="0.3"/>'
        f'<circle cx="{pos:.0f}" cy="11" r="5" fill="#fafafa"/>'
        f'<circle cx="{pos:.0f}" cy="11" r="2.5" fill="{active_color}"/>'
        f'{labels}'
        f'</svg>'
    )


def render(focus, data):
    today_fmt = datetime.now().strftime("%Y.%m.%d")
    weekday_cn = ["周一","周二","周三","周四","周五","周六","周日"][datetime.now().weekday()]

    # BTC
    ahr = data.get("ahr999", {})
    prices = ahr.get("prices", [])
    btc_price = ahr.get("price", 0)
    btc_area = area_chart(prices, "#f59e0b")

    btc_chg = ""
    if len(prices) >= 2:
        ch = ((prices[-1] - prices[0]) / prices[0]) * 100
        cc = "#4ade80" if ch > 0 else "#f87171"
        btc_chg = f'<span style="color:{cc};font-family:Space Grotesk;font-size:20px;font-weight:600">{"+" if ch>0 else ""}{ch:.1f}%</span>'

    # 主卡
    fd = data.get(focus, {})
    fval = fd.get("value", 0)
    fst = fd.get("status", fd.get("regime", ""))
    fc = get_color(fst)

    if focus == "ahr999":
        cost = ahr.get("cost_200d", 1)
        ratio = int(btc_price / cost * 100) if cost else 0
        g = gauge(fval, 0, 1.5, [
            {"from":0,"to":0.45,"color":"#4ade80","label":"抄底"},
            {"from":0.45,"to":1.2,"color":"#facc15","label":"定投"},
            {"from":1.2,"to":1.5,"color":"#f87171","label":"观望"},
        ])
        main = f'''
<div class="card">
  <div class="c-top"><div class="c-lb">🔥 AHR999</div><div class="c-st" style="color:{fc}">{fst}</div></div>
  <div class="c-num" style="color:{fc};text-shadow:0 0 80px {fc}40">{fval:.2f}</div>
  <div class="c-gauge">{g}</div>
  <div class="c-ins">价格 = 200日成本的 <b>{ratio}%</b> · 定投成本 ${cost:,.0f}</div>
</div>'''

    elif focus == "mvrv":
        pnl = int((fval-1)*100)
        g = gauge(fval, 0, 4, [
            {"from":0,"to":1,"color":"#4ade80","label":"低估"},
            {"from":1,"to":3,"color":"#facc15","label":"合理"},
            {"from":3,"to":4,"color":"#f87171","label":"过热"},
        ])
        main = f'''
<div class="card">
  <div class="c-top"><div class="c-lb">📈 MVRV</div><div class="c-st" style="color:{fc}">{fst}</div></div>
  <div class="c-num" style="color:{fc};text-shadow:0 0 80px {fc}40">{fval:.2f}</div>
  <div class="c-gauge">{g}</div>
  <div class="c-ins">持币者整体盈利 <b>{pnl}%</b> · MVRV&lt;1 为历史底部</div>
</div>'''

    elif focus == "bmri":
        risk = "低风险" if fval < 30 else "高风险" if fval > 70 else "中性"
        g = gauge(fval, 0, 100, [
            {"from":0,"to":30,"color":"#4ade80","label":"低风险"},
            {"from":30,"to":70,"color":"#facc15","label":"中性"},
            {"from":70,"to":100,"color":"#f87171","label":"高风险"},
        ])
        main = f'''
<div class="card">
  <div class="c-top"><div class="c-lb">⚠️ BMRI</div><div class="c-st" style="color:{fc}">{risk}</div></div>
  <div class="c-num" style="color:{fc};text-shadow:0 0 80px {fc}40">{fval:.1f}</div>
  <div class="c-gauge">{g}</div>
  <div class="c-ins">综合流动性、利率、市场风险多维评估</div>
</div>'''

    else:
        zone = fd.get("zone","BALANCED")
        zt = "BTC主导" if zone=="BTC_DOMINANT" else "山寨季" if zone=="ALT_SEASON" else "平衡"
        g = gauge(fval, 40, 70, [
            {"from":40,"to":50,"color":"#4ade80","label":"山寨季"},
            {"from":50,"to":60,"color":"#facc15","label":"平衡"},
            {"from":60,"to":70,"color":"#f87171","label":"BTC主导"},
        ])
        main = f'''
<div class="card">
  <div class="c-top"><div class="c-lb">₿ BTC.D</div><div class="c-st" style="color:{fc}">{zt}</div></div>
  <div class="c-num" style="color:{fc};text-shadow:0 0 80px {fc}40">{fval:.1f}%</div>
  <div class="c-gauge">{g}</div>
  <div class="c-ins">BTC 市值占加密总市值比例</div>
</div>'''

    # 副指标
    sub_order = {"ahr999":["mvrv","bmri","btcd"],"mvrv":["ahr999","bmri","btcd"],
                 "bmri":["ahr999","mvrv","btcd"],"btcd":["ahr999","mvrv","bmri"]}
    rows = []
    for nm in sub_order.get(focus, ["mvrv","bmri","btcd"]):
        d = data.get(nm, {})
        v = d.get("value", 0)
        st = d.get("status", d.get("regime", d.get("zone", "")))
        c = get_color(st)
        wk = d.get("week", [])
        sp = sparkline(wk, c)
        if nm=="ahr999": lb,vs,sx = "AHR999",f"{v:.2f}",d.get("status","")
        elif nm=="mvrv": lb,vs,sx = "MVRV",f"{v:.2f}",d.get("status","")
        elif nm=="bmri": lb,vs,sx = "BMRI",f"{v:.1f}",("低风险" if v<30 else "高风险" if v>70 else "中性")
        else:
            lb,vs = "BTC.D",f"{v:.1f}%"
            z = d.get("zone","BALANCED")
            sx = "BTC主导" if z=="BTC_DOMINANT" else "山寨季" if z=="ALT_SEASON" else "平衡"
        rows.append(f'''
  <div class="row"><span class="r-lb">{lb}</span><span class="r-v" style="color:{c}">{vs}</span><span class="r-sp">{sp}</span><span class="r-s" style="color:{c}">{sx}</span></div>''')
    subs = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
  font-family:'DM Sans',sans-serif;
  color:#fafafa;
  width:1080px;
  height:1350px;
  overflow:hidden;
  display:flex;
  flex-direction:column;
  background:#07070a;
  background-image:radial-gradient(ellipse 80% 60% at 50% 30%, #12121a 0%, #07070a 100%);
}}

/* Header */
.hdr{{
  padding:52px 72px 0;
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
}}
.brand{{font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:700;letter-spacing:-0.5px}}
.sub-brand{{font-size:13px;color:#3f3f46;letter-spacing:2px;text-transform:uppercase;margin-top:6px}}
.dt{{text-align:right}}
.dt-date{{font-family:'Space Grotesk',sans-serif;font-size:20px;color:#52525b;font-weight:500}}
.dt-day{{font-size:13px;color:#3f3f46;margin-top:4px}}

/* BTC */
.btc{{padding:36px 72px 0}}
.btc-r{{display:flex;align-items:baseline;gap:20px;margin-bottom:16px}}
.btc-lb{{font-size:16px;color:#52525b;text-transform:uppercase;letter-spacing:2px;font-weight:500}}
.btc-p{{font-family:'Space Grotesk',sans-serif;font-size:48px;font-weight:700;color:#fafafa}}

/* Divider */
.dv{{margin:32px 72px;height:1px;background:linear-gradient(90deg,transparent,#27272a 20%,#27272a 80%,transparent)}}

/* Card */
.card{{margin:0 72px;background:linear-gradient(160deg,rgba(20,20,24,0.8),rgba(12,12,14,0.9));border:1px solid rgba(255,255,255,0.04);border-radius:24px;padding:36px 44px;backdrop-filter:blur(10px)}}
.c-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.c-lb{{font-size:20px;color:#71717a;font-weight:500}}
.c-st{{font-size:20px;font-weight:700}}
.c-num{{font-family:'Space Grotesk',sans-serif;font-size:88px;font-weight:700;letter-spacing:-3px;margin:4px 0 20px}}
.c-gauge{{margin-bottom:20px}}
.c-ins{{font-size:18px;color:#71717a;line-height:1.6;border-top:1px solid rgba(255,255,255,0.06);padding-top:18px}}
.c-ins b{{color:#d4d4d8;font-weight:700}}

/* Subs */
.subs{{padding:0 72px}}
.row{{display:grid;grid-template-columns:100px 100px 140px 1fr;align-items:center;gap:16px;padding:18px 0;border-bottom:1px solid rgba(255,255,255,0.04)}}
.row:last-child{{border-bottom:none}}
.r-lb{{font-size:17px;color:#52525b;font-weight:600}}
.r-v{{font-family:'Space Grotesk',sans-serif;font-size:24px;font-weight:700}}
.r-sp{{height:28px}}
.r-s{{font-size:16px;font-weight:600;text-align:right}}

/* Footer */
.ftr{{
  margin-top:auto;
  padding:32px 72px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  font-size:14px;
  color:#27272a;
}}
.ftr-l{{color:#3b82f6;font-weight:600;font-size:18px}}
</style>
</head>
<body>

<div class="hdr">
  <div>
    <div class="brand">Crypto3D</div>
    <div class="sub-brand">Market Intelligence</div>
  </div>
  <div class="dt">
    <div class="dt-date">{today_fmt}</div>
    <div class="dt-day">{weekday_cn}</div>
  </div>
</div>

<div class="btc">
  <div class="btc-r">
    <span class="btc-lb">Bitcoin</span>
    <span class="btc-p">${btc_price:,}</span>
    {btc_chg}
  </div>
  {btc_area}
</div>

<div class="dv"></div>

{main}

<div class="dv"></div>

<div class="subs">
{subs}
</div>

<div class="ftr">
  <span>Daily Market Snapshot</span>
  <span class="ftr-l">crypto3d.pro</span>
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
