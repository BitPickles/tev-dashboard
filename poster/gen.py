#!/usr/bin/env python3
"""Crypto3D Daily Poster - Final Design"""
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
        with open(path) as f: return json.load(f)
    except: return None


def load_all():
    data = {}
    ahr = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr:
        c, h = ahr["current"], ahr.get("history", [])
        data["ahr999"] = dict(value=c["value"], status=c["status"], price=c["price"],
            cost_200d=c["cost_200d"], fitted=c.get("fitted_price",0),
            prices=[x["close"] for x in h[-7:]])
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c, h = mvrv["current"], mvrv.get("history", [])
        data["mvrv"] = dict(value=c["value"], status=c["status"], week=[x["mvrv"] for x in h[-7:]])
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri:
        c, h = bmri["1m"]["current"], bmri["1m"].get("history", [])
        data["bmri"] = dict(value=c["value"], regime=c["regime"], week=[x["bmri"] for x in h[-7:]])
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c, h = btcd["current"], btcd.get("history", [])
        data["btcd"] = dict(value=c["value"], zone=c["zone"], week=[x["value"] for x in h[-7:]])
    return data


def select_focus(data):
    a = data.get("ahr999",{}).get("value",1)
    m = data.get("mvrv",{}).get("value",1)
    b = data.get("bmri",{}).get("value",50)
    if a < 0.5: return "ahr999"
    if m > 3: return "mvrv"
    if b < 30 or b > 70: return "bmri"
    return ["ahr999","btcd","mvrv","bmri","ahr999","ahr999","ahr999"][datetime.now().weekday()]


def color_for(status):
    s = str(status).lower()
    if any(k in s for k in ["抄底","合理","neutral","balanced","low","fair"]): return "#34d399"
    if any(k in s for k in ["过热","high","extreme","danger"]): return "#fb7185"
    return "#60a5fa"


def svg_area(vals, color, w, h):
    """面积图"""
    if not vals or len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h * 0.7)) - h * 0.15
        pts.append((x, y))
    line = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    fill = line + f" {w},{h} 0,{h}"
    return (
        f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="display:block;width:100%;height:100%">'
        f'<defs><linearGradient id="af" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.4"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<polygon fill="url(#af)" points="{fill}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="{line}"/>'
        f'</svg>'
    )


def svg_spark(vals, color, w, h):
    """迷你折线"""
    if not vals or len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * (h * 0.7)) - h * 0.15
        pts.append((x, y))
    line = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    lx, ly = pts[-1]
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:100%">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="{line}"/>'
        f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="4" fill="{color}"/>'
        f'</svg>'
    )


def svg_gauge(val, lo, hi, zones):
    """标尺"""
    w = 100  # percent based
    rng = hi - lo
    pct = max(1, min((val - lo) / rng * 100, 99))

    segs = ""
    for z in zones:
        x1 = (z["fr"] - lo) / rng * 100
        x2 = (z["to"] - lo) / rng * 100
        segs += f'<div style="position:absolute;left:{x1}%;width:{x2-x1}%;height:100%;background:{z["c"]};opacity:0.12;border-radius:5px"></div>'

    # active fill
    active_c = zones[0]["c"]
    for z in zones:
        if z["fr"] <= val <= z["to"]:
            active_c = z["c"]
    segs += f'<div style="position:absolute;left:0;width:{pct}%;height:100%;background:linear-gradient(90deg,{active_c}00,{active_c});opacity:0.35;border-radius:5px"></div>'

    # pointer
    segs += f'<div style="position:absolute;left:{pct}%;top:50%;transform:translate(-50%,-50%);width:16px;height:16px;border-radius:50%;background:{active_c};box-shadow:0 0 12px {active_c}80"></div>'
    segs += f'<div style="position:absolute;left:{pct}%;top:50%;transform:translate(-50%,-50%);width:8px;height:8px;border-radius:50%;background:#fff"></div>'

    labels = ""
    for z in zones:
        x = ((z["fr"] + z["to"]) / 2 - lo) / rng * 100
        labels += f'<span style="position:absolute;left:{x}%;transform:translateX(-50%);font-size:16px;color:#52525b;font-weight:500">{z["lb"]}</span>'

    return f'''<div style="position:relative;height:10px;border-radius:5px;background:#1a1a1f">{segs}</div>
    <div style="position:relative;height:28px;margin-top:8px">{labels}</div>'''


def render(focus, data):
    now = datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    weekday = ["MON","TUE","WED","THU","FRI","SAT","SUN"][now.weekday()]

    ahr = data.get("ahr999", {})
    prices = ahr.get("prices", [])
    btc_price = ahr.get("price", 0)

    # BTC change
    btc_chg_html = ""
    if len(prices) >= 2:
        ch = ((prices[-1] - prices[0]) / prices[0]) * 100
        cc = "#34d399" if ch > 0 else "#fb7185"
        btc_chg_html = f'<span style="color:{cc}">{"+" if ch>0 else ""}{ch:.1f}%</span>'

    btc_chart = svg_area(prices, "#f59e0b", 1000, 160)

    # Main card
    fd = data.get(focus, {})
    fval = fd.get("value", 0)
    fst = fd.get("status", fd.get("regime", ""))
    fc = color_for(fst)

    if focus == "ahr999":
        cost = ahr.get("cost_200d", 1)
        ratio = int(btc_price / cost * 100) if cost else 0
        g = svg_gauge(fval, 0, 1.5, [
            {"fr":0,"to":0.45,"c":"#34d399","lb":"抄底"},
            {"fr":0.45,"to":1.2,"c":"#fbbf24","lb":"定投"},
            {"fr":1.2,"to":1.5,"c":"#fb7185","lb":"观望"},
        ])
        card_body = f'''
        <div class="c-val" style="color:{fc}">{fval:.2f}</div>
        <div class="c-badge" style="background:{fc}20;color:{fc}">{fst}</div>
        <div class="c-gauge">{g}</div>
        <div class="c-detail">
          <div class="c-d-item"><span class="c-d-label">BTC 价格</span><span class="c-d-val">${btc_price:,}</span></div>
          <div class="c-d-item"><span class="c-d-label">200日成本</span><span class="c-d-val">${cost:,.0f}</span></div>
          <div class="c-d-item"><span class="c-d-label">价格/成本</span><span class="c-d-val" style="color:{fc}">{ratio}%</span></div>
        </div>'''
        card_title = "🔥 AHR999"

    elif focus == "mvrv":
        pnl = int((fval-1)*100)
        g = svg_gauge(fval, 0, 4, [
            {"fr":0,"to":1,"c":"#34d399","lb":"低估"},
            {"fr":1,"to":3,"c":"#fbbf24","lb":"合理"},
            {"fr":3,"to":4,"c":"#fb7185","lb":"过热"},
        ])
        card_body = f'''
        <div class="c-val" style="color:{fc}">{fval:.2f}</div>
        <div class="c-badge" style="background:{fc}20;color:{fc}">{fst}</div>
        <div class="c-gauge">{g}</div>
        <div class="c-detail">
          <div class="c-d-item"><span class="c-d-label">持币盈利</span><span class="c-d-val" style="color:{fc}">{pnl}%</span></div>
        </div>'''
        card_title = "📈 MVRV"

    elif focus == "bmri":
        risk = "低风险" if fval<30 else "高风险" if fval>70 else "中性"
        g = svg_gauge(fval, 0, 100, [
            {"fr":0,"to":30,"c":"#34d399","lb":"低风险"},
            {"fr":30,"to":70,"c":"#fbbf24","lb":"中性"},
            {"fr":70,"to":100,"c":"#fb7185","lb":"高风险"},
        ])
        card_body = f'''
        <div class="c-val" style="color:{fc}">{fval:.1f}</div>
        <div class="c-badge" style="background:{fc}20;color:{fc}">{risk}</div>
        <div class="c-gauge">{g}</div>'''
        card_title = "⚠️ BMRI"

    else:
        z = fd.get("zone","BALANCED")
        zt = "BTC主导" if z=="BTC_DOMINANT" else "山寨季" if z=="ALT_SEASON" else "平衡"
        g = svg_gauge(fval, 40, 70, [
            {"fr":40,"to":50,"c":"#34d399","lb":"山寨季"},
            {"fr":50,"to":60,"c":"#fbbf24","lb":"平衡"},
            {"fr":60,"to":70,"c":"#fb7185","lb":"BTC主导"},
        ])
        card_body = f'''
        <div class="c-val" style="color:{fc}">{fval:.1f}%</div>
        <div class="c-badge" style="background:{fc}20;color:{fc}">{zt}</div>
        <div class="c-gauge">{g}</div>'''
        card_title = "₿ BTC Dominance"

    # Sub indicators
    sub_map = {"ahr999":["mvrv","bmri","btcd"],"mvrv":["ahr999","bmri","btcd"],
               "bmri":["ahr999","mvrv","btcd"],"btcd":["ahr999","mvrv","bmri"]}
    sub_rows = ""
    for nm in sub_map.get(focus, ["mvrv","bmri","btcd"]):
        d = data.get(nm, {})
        v = d.get("value", 0)
        st = d.get("status", d.get("regime", d.get("zone", "")))
        c = color_for(st)
        wk = d.get("week", [])
        sp = svg_spark(wk, c, 100, 32)
        if nm == "ahr999": lb,vs,sx = "AHR999",f"{v:.2f}",d.get("status","")
        elif nm == "mvrv": lb,vs,sx = "MVRV",f"{v:.2f}",d.get("status","")
        elif nm == "bmri":
            lb, vs = "BMRI", f"{v:.1f}"
            sx = "低风险" if v<30 else "高风险" if v>70 else "中性"
        else:
            lb, vs = "BTC.D", f"{v:.1f}%"
            zz = d.get("zone","BALANCED")
            sx = "BTC主导" if zz=="BTC_DOMINANT" else "山寨季" if zz=="ALT_SEASON" else "平衡"
        sub_rows += f'''
        <div class="s-item">
          <div class="s-left">
            <div class="s-name">{lb}</div>
            <div class="s-num" style="color:{c}">{vs}</div>
          </div>
          <div class="s-chart">{sp}</div>
          <div class="s-status" style="color:{c}">{sx}</div>
        </div>'''

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: 'Inter', -apple-system, sans-serif;
  width: 1080px;
  height: 1350px;
  overflow: hidden;
  color: #e4e4e7;
  background: #08080c;
  background-image:
    radial-gradient(ellipse 100% 50% at 50% 0%, #13131a 0%, transparent 70%),
    radial-gradient(circle at 80% 80%, #0f0f18 0%, transparent 50%);
}}

/* === HEADER === */
.header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 44px 56px 36px;
}}
.h-brand {{
  font-size: 40px;
  font-weight: 800;
  letter-spacing: -1px;
  color: #fafafa;
}}
.h-date {{
  font-size: 18px;
  font-weight: 600;
  color: #3f3f46;
  letter-spacing: 1px;
}}

/* === BTC SECTION === */
.btc-section {{
  padding: 0 56px;
}}
.btc-top {{
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 8px;
}}
.btc-label {{
  font-size: 15px;
  font-weight: 600;
  color: #52525b;
  text-transform: uppercase;
  letter-spacing: 2px;
}}
.btc-price {{
  font-size: 56px;
  font-weight: 800;
  color: #fafafa;
  letter-spacing: -2px;
}}
.btc-chg {{
  font-size: 22px;
  font-weight: 700;
}}
.btc-chart {{
  height: 160px;
  margin: 0 -56px;
  padding: 0 56px;
  overflow: hidden;
}}

/* === MAIN CARD === */
.card {{
  margin: 24px 56px;
  padding: 36px 40px 32px;
  background: linear-gradient(145deg, #111115 0%, #0a0a0e 100%);
  border: 1px solid #1c1c22;
  border-radius: 20px;
}}
.c-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}}
.c-title {{
  font-size: 18px;
  font-weight: 600;
  color: #71717a;
}}
.c-val {{
  font-size: 80px;
  font-weight: 800;
  letter-spacing: -3px;
  line-height: 1;
  margin-bottom: 16px;
}}
.c-badge {{
  display: inline-block;
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 24px;
}}
.c-gauge {{
  margin-bottom: 24px;
}}
.c-detail {{
  display: flex;
  gap: 32px;
  padding-top: 20px;
  border-top: 1px solid #1c1c22;
}}
.c-d-item {{
  display: flex;
  flex-direction: column;
  gap: 4px;
}}
.c-d-label {{
  font-size: 13px;
  font-weight: 500;
  color: #52525b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}
.c-d-val {{
  font-size: 22px;
  font-weight: 700;
  color: #d4d4d8;
}}

/* === SUB INDICATORS === */
.subs {{
  padding: 0 56px;
  display: flex;
  flex-direction: column;
  gap: 0;
}}
.s-item {{
  display: flex;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #1418;
}}
.s-item:last-child {{ border-bottom: none; }}
.s-left {{
  width: 160px;
}}
.s-name {{
  font-size: 14px;
  font-weight: 600;
  color: #52525b;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}}
.s-num {{
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
}}
.s-chart {{
  flex: 1;
  height: 32px;
  padding: 0 24px;
}}
.s-status {{
  width: 80px;
  text-align: right;
  font-size: 15px;
  font-weight: 600;
}}

/* === FOOTER === */
.footer {{
  margin-top: auto;
  padding: 28px 56px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.f-tag {{
  font-size: 13px;
  font-weight: 500;
  color: #27272a;
  text-transform: uppercase;
  letter-spacing: 2px;
}}
.f-link {{
  font-size: 18px;
  font-weight: 700;
  color: #3b82f6;
}}
</style>
</head>
<body>

<div class="header">
  <div class="h-brand">Crypto3D</div>
  <div class="h-date">{weekday} · {date_str}</div>
</div>

<div class="btc-section">
  <div class="btc-top">
    <span class="btc-label">Bitcoin</span>
    <span class="btc-price">${btc_price:,}</span>
    <span class="btc-chg">{btc_chg_html}</span>
  </div>
  <div class="btc-chart">{btc_chart}</div>
</div>

<div class="card">
  <div class="c-top">
    <span class="c-title">{card_title}</span>
  </div>
  {card_body}
</div>

<div class="subs">
  {sub_rows}
</div>

<div class="footer">
  <span class="f-tag">Daily Market Snapshot</span>
  <span class="f-link">crypto3d.pro</span>
</div>

</body>
</html>"""


async def generate():
    data = load_all()
    focus = select_focus(data)
    print(f"焦点: {focus.upper()}")
    html = render(focus, data)
    today_str = datetime.now().strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{today_str}.html"
    png_path = OUTPUT_DIR / f"{today_str}.png"
    with open(html_path, "w") as f:
        f.write(html)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width":1080,"height":1350})
        await pg.goto(f"file://{html_path}")
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=str(png_path), type="png")
        await b.close()
    print(f"OK → {png_path}")

if __name__ == "__main__":
    asyncio.run(generate())
