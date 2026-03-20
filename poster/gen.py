#!/usr/bin/env python3
"""Crypto3D Daily Poster — v9 设计师重构版
设计规范：
- 暗色主题 #08080c，微妙辐射渐变 + 点阵纹理
- 信息图风格，非后台面板
- 所有关键数字 ≥42px，手机端（320px宽）可读
- 模块化焦点卡 + 副指标
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def load_all():
    D = {}
    a = load_json(INDICATORS_DIR / "ahr999.json")
    if a:
        D["ahr999"] = dict(
            v=a["current"]["value"],
            s=a["current"]["status"],
            p=a["current"]["price"],
            c=a["current"]["cost_200d"],
            px=[x["close"] for x in a.get("history", [])[-7:]],
        )
    m = load_json(INDICATORS_DIR / "mvrv.json")
    if m:
        D["mvrv"] = dict(
            v=m["current"]["value"],
            s=m["current"]["status"],
            w=[x["mvrv"] for x in m.get("history", [])[-7:]],
        )
    b = load_json(INDICATORS_DIR / "bmri.json")
    if b:
        D["bmri"] = dict(
            v=b["1m"]["current"]["value"],
            w=[x["bmri"] for x in b["1m"].get("history", [])[-7:]],
        )
    d = load_json(INDICATORS_DIR / "btc-dominance.json")
    if d:
        D["btcd"] = dict(
            v=d["current"]["value"],
            z=d["current"]["zone"],
            w=[x["value"] for x in d.get("history", [])[-7:]],
        )
    return D


def pick(D):
    a = D.get("ahr999", {}).get("v", 1)
    m = D.get("mvrv", {}).get("v", 1)
    b = D.get("bmri", {}).get("v", 50)
    if a < 0.5:
        return "ahr999"
    if m > 3:
        return "mvrv"
    if b < 30 or b > 70:
        return "bmri"
    return ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"][
        datetime.now().weekday()
    ]


# --- Color helpers ---

def status_color(s):
    x = str(s).lower()
    if any(k in x for k in ["抄底", "低估", "低风险", "low", "bottom"]):
        return "#34d399"
    if any(k in x for k in ["过热", "高风险", "extreme", "high", "btc主导"]):
        return "#fb7185"
    if any(k in x for k in ["定投", "合理", "中性", "neutral", "balanced", "fair", "平衡"]):
        return "#fbbf24"
    if any(k in x for k in ["山寨季", "alt"]):
        return "#60a5fa"
    return "#60a5fa"


def color_class(c):
    m = {"#34d399": "green", "#fb7185": "red", "#fbbf24": "yellow", "#60a5fa": "blue"}
    return m.get(c, "blue")


# --- SVG generators ---

def area_svg(vals, color, w=1000, h=120):
    if not vals or len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    r = mx - mn or 1
    pts = [
        (i * w / (len(vals) - 1), h - ((v - mn) / r * h * 0.7) - h * 0.12)
        for i, v in enumerate(vals)
    ]
    line = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    fill = line + f" {w},{h} 0,{h}"
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:100%">'
        f'<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<polygon fill="url(#ag)" points="{fill}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{line}"/>'
        f'</svg>'
    )


def spark_svg(vals, color, w=200, h=52):
    if not vals or len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    r = mx - mn or 1
    pts = [
        (i * w / (len(vals) - 1), h - ((v - mn) / r * h * 0.6) - h * 0.15)
        for i, v in enumerate(vals)
    ]
    line = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    lx, ly = pts[-1]
    # fill area under spark for more visual weight
    fill_pts = line + f" {w},{h} 0,{h}"
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:100%">'
        f'<defs><linearGradient id="sg_{color[1:]}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<polygon fill="url(#sg_{color[1:]})" points="{fill_pts}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{line}"/>'
        f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="5" fill="{color}"/>'
        f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="9" fill="{color}" opacity="0.15"/>'
        f'</svg>'
    )


# --- Gauge ---

def gauge_html(value, lo, hi, zones):
    """zones: list of {fr, to, color, label}"""
    R = hi - lo
    pct = max(3, min((value - lo) / R * 100, 97))
    active_color = zones[0]["color"]
    active_label = zones[0]["label"]
    for z in zones:
        if z["fr"] <= value <= z["to"]:
            active_color = z["color"]
            active_label = z["label"]

    # zone backgrounds
    zone_html = ""
    for z in zones:
        x1 = (z["fr"] - lo) / R * 100
        x2 = (z["to"] - lo) / R * 100
        zone_html += (
            f'<div class="gauge-zone" '
            f'style="left:{x1}%;width:{x2-x1}%;background:{z["color"]}"></div>'
        )

    # fill
    fill_html = (
        f'<div class="gauge-fill" '
        f'style="width:{pct}%;background:linear-gradient(90deg,{active_color}00,{active_color})"></div>'
    )

    # dot
    dot_html = (
        f'<div class="gauge-dot-outer" '
        f'style="left:{pct}%;background:{active_color};box-shadow:0 0 16px {active_color}88"></div>'
        f'<div class="gauge-dot-inner" style="left:{pct}%"></div>'
    )

    bar = f'<div class="gauge-bar">{zone_html}{fill_html}{dot_html}</div>'

    # labels
    labels = ""
    for z in zones:
        is_active = z["fr"] <= value <= z["to"]
        cls = " active" if is_active else ""
        style = f' style="color:{z["color"]}"' if is_active else ""
        labels += f'<span class="gauge-label{cls}"{style}>{z["label"]}</span>'

    return f'{bar}<div class="gauge-labels">{labels}</div>'


# --- Card builders ---

def build_focus_card(focus, D):
    fd = D.get(focus, {})
    fv = fd.get("v", 0)
    fs = fd.get("s", fd.get("z", ""))

    if focus == "ahr999":
        fc = status_color(fs)
        cc = color_class(fc)
        bp, bc = fd.get("p", 0), fd.get("c", 1)
        ratio = int(bp / bc * 100) if bc else 0
        g = gauge_html(fv, 0, 1.5, [
            {"fr": 0, "to": 0.45, "color": "#34d399", "label": "抄底"},
            {"fr": 0.45, "to": 1.2, "color": "#fbbf24", "label": "定投"},
            {"fr": 1.2, "to": 1.5, "color": "#fb7185", "label": "观望"},
        ])
        meta = (
            f'<div class="meta-item"><div class="meta-label">BTC 价格</div>'
            f'<div class="meta-value">${bp:,}</div></div>'
            f'<div class="meta-item"><div class="meta-label">200日成本</div>'
            f'<div class="meta-value">${bc:,.0f}</div></div>'
            f'<div class="meta-item"><div class="meta-label">价格/成本</div>'
            f'<div class="meta-value" style="color:{fc}">{ratio}%</div></div>'
        )
        return "🔥", "AHR999", fs, fv, f"{fv:.2f}", fc, cc, g, meta

    elif focus == "mvrv":
        fc = status_color(fs)
        cc = color_class(fc)
        pnl = int((fv - 1) * 100)
        g = gauge_html(fv, 0, 4, [
            {"fr": 0, "to": 1, "color": "#34d399", "label": "低估"},
            {"fr": 1, "to": 3, "color": "#fbbf24", "label": "合理"},
            {"fr": 3, "to": 4, "color": "#fb7185", "label": "过热"},
        ])
        meta = (
            f'<div class="meta-item"><div class="meta-label">持币盈利</div>'
            f'<div class="meta-value" style="color:{fc}">{"+" if pnl>0 else ""}{pnl}%</div></div>'
        )
        return "📈", "MVRV", fs, fv, f"{fv:.2f}", fc, cc, g, meta

    elif focus == "bmri":
        rx = "低风险" if fv < 30 else "高风险" if fv > 70 else "中性"
        fc = status_color(rx)
        cc = color_class(fc)
        g = gauge_html(fv, 0, 100, [
            {"fr": 0, "to": 30, "color": "#34d399", "label": "低风险"},
            {"fr": 30, "to": 70, "color": "#fbbf24", "label": "中性"},
            {"fr": 70, "to": 100, "color": "#fb7185", "label": "高风险"},
        ])
        return "⚠️", "BMRI", rx, fv, f"{fv:.1f}", fc, cc, g, ""

    else:  # btcd
        zt = (
            "BTC主导" if fd.get("z") == "BTC_DOMINANT"
            else "山寨季" if fd.get("z") == "ALT_SEASON"
            else "平衡"
        )
        fc = status_color(zt)
        cc = color_class(fc)
        g = gauge_html(fv, 40, 70, [
            {"fr": 40, "to": 50, "color": "#60a5fa", "label": "山寨季"},
            {"fr": 50, "to": 60, "color": "#fbbf24", "label": "平衡"},
            {"fr": 60, "to": 70, "color": "#fb7185", "label": "BTC主导"},
        ])
        return "₿", "BTC.D", zt, fv, f"{fv:.1f}%", fc, cc, g, ""


def build_sec_rows(focus, D):
    order = {
        "ahr999": ["mvrv", "bmri", "btcd"],
        "mvrv": ["ahr999", "bmri", "btcd"],
        "bmri": ["ahr999", "mvrv", "btcd"],
        "btcd": ["ahr999", "mvrv", "bmri"],
    }
    rows_html = ""
    for nm in order.get(focus, ["mvrv", "bmri", "btcd"]):
        d = D.get(nm, {})
        v = d.get("v", 0)
        s = d.get("s", d.get("z", ""))
        w = d.get("w", [])

        if nm == "ahr999":
            label, vs, sx = "AHR999", f"{v:.2f}", d.get("s", "")
        elif nm == "mvrv":
            label, vs, sx = "MVRV", f"{v:.2f}", d.get("s", "")
        elif nm == "bmri":
            label, vs, sx = "BMRI", f"{v:.1f}", (
                "低风险" if v < 30 else "高风险" if v > 70 else "中性"
            )
        else:
            label, vs, sx = "BTC.D", f"{v:.1f}%", (
                "BTC主导" if d.get("z") == "BTC_DOMINANT"
                else "山寨季" if d.get("z") == "ALT_SEASON"
                else "平衡"
            )

        c = status_color(sx)
        cc = color_class(c)
        sp = spark_svg(w, c)

        rows_html += f'''
  <div class="sec-row">
    <div class="sec-info">
      <span class="sec-name">{label}</span>
      <span class="sec-value" style="color:{c}">{vs}</span>
    </div>
    <div class="sec-spark">{sp}</div>
    <span class="sec-badge {cc}">{sx}</span>
  </div>'''

    return rows_html


# --- Main render ---

def render(focus, D):
    now = datetime.now()
    ds = now.strftime("%Y.%m.%d")
    wd = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]

    # BTC data
    a = D.get("ahr999", {})
    px = a.get("px", [])
    bp = a.get("p", 0)
    chg_html = ""
    if len(px) >= 2:
        ch = ((px[-1] - px[0]) / px[0]) * 100
        cls = "up" if ch > 0 else "down"
        chg_html = f'<span class="btc-change {cls}">{"+" if ch > 0 else ""}{ch:.1f}%</span>'

    btc_area = area_svg(px, "#f59e0b")

    # Focus card
    icon, name, status, raw_v, val_str, fc, fcc, gauge, meta = build_focus_card(focus, D)

    meta_block = f'<div class="card-meta">{meta}</div>' if meta else ""

    # Secondary rows
    sec_rows = build_sec_rows(focus, D)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  width: 1080px;
  height: 1350px;
  overflow: hidden;
  color: #e4e4e7;
  display: flex;
  flex-direction: column;
  background: #08080c;
  position: relative;
}}

/* Background texture */
body::before {{
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 90% 40% at 50% 0%, rgba(59,130,246,0.05) 0%, transparent 70%),
    radial-gradient(ellipse 60% 30% at 80% 60%, rgba(34,197,94,0.025) 0%, transparent 60%),
    radial-gradient(ellipse 50% 50% at 20% 80%, rgba(245,158,11,0.02) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}}

body::after {{
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.012) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
  z-index: 0;
}}

body > * {{ position: relative; z-index: 1; }}

/* Header */
.header {{
  text-align: center;
  padding: 48px 60px 24px;
}}

.header-title {{
  font-size: 42px;
  font-weight: 900;
  color: #fafafa;
  letter-spacing: -1px;
}}

.header-date {{
  font-size: 26px;
  font-weight: 600;
  color: #71717a;
  letter-spacing: 2px;
  margin-top: 6px;
}}

/* BTC Banner */
.btc-banner {{
  padding: 4px 60px 0;
}}

.btc-row {{
  display: flex;
  align-items: baseline;
  gap: 16px;
}}

.btc-label {{
  font-size: 22px;
  font-weight: 700;
  color: #52525b;
  text-transform: uppercase;
  letter-spacing: 3px;
}}

.btc-price {{
  font-size: 64px;
  font-weight: 900;
  color: #fafafa;
  letter-spacing: -2px;
  font-variant-numeric: tabular-nums;
}}

.btc-change {{
  font-size: 26px;
  font-weight: 800;
  padding: 4px 14px;
  border-radius: 8px;
}}

.btc-change.up {{ color: #34d399; background: rgba(34,197,94,0.1); }}
.btc-change.down {{ color: #fb7185; background: rgba(251,113,133,0.1); }}

.btc-chart {{
  height: 105px;
  margin: -4px -60px 0;
  overflow: hidden;
  opacity: 0.65;
}}

/* Divider */
.divider {{
  margin: 10px 60px;
  height: 1px;
  background: linear-gradient(90deg, transparent, #1e1e28, transparent);
}}

/* Focus Card */
.focus-card {{
  margin: 8px 48px;
  padding: 36px 40px 30px;
  background: linear-gradient(165deg, #111118 0%, #0c0c12 100%);
  border: 1px solid #1a1a24;
  border-radius: 20px;
  position: relative;
  overflow: hidden;
}}

.focus-card::before {{
  content: '';
  position: absolute;
  top: -60px;
  right: -60px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  pointer-events: none;
}}

.focus-card.green::before {{ background: radial-gradient(circle, rgba(34,197,94,0.07), transparent 70%); }}
.focus-card.blue::before {{ background: radial-gradient(circle, rgba(59,130,246,0.07), transparent 70%); }}
.focus-card.red::before {{ background: radial-gradient(circle, rgba(251,113,133,0.07), transparent 70%); }}
.focus-card.yellow::before {{ background: radial-gradient(circle, rgba(251,191,36,0.07), transparent 70%); }}

.card-header {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 6px;
}}

.card-icon {{ font-size: 28px; }}

.card-name {{
  font-size: 24px;
  font-weight: 600;
  color: #71717a;
  letter-spacing: 2px;
  text-transform: uppercase;
  flex: 1;
}}

.card-badge {{
  font-size: 24px;
  font-weight: 800;
  padding: 6px 18px;
  border-radius: 10px;
}}

.card-badge.green {{ color: #34d399; background: rgba(34,197,94,0.12); }}
.card-badge.blue {{ color: #60a5fa; background: rgba(96,165,250,0.12); }}
.card-badge.red {{ color: #fb7185; background: rgba(251,113,133,0.12); }}
.card-badge.yellow {{ color: #fbbf24; background: rgba(251,191,36,0.12); }}

.card-value {{
  font-size: 84px;
  font-weight: 900;
  letter-spacing: -3px;
  line-height: 1;
  margin: 8px 0 24px;
  font-variant-numeric: tabular-nums;
}}

/* Gauge */
.gauge-bar {{
  position: relative;
  height: 14px;
  border-radius: 7px;
  background: #15151c;
  overflow: visible;
}}

.gauge-fill {{
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 7px;
  opacity: 0.35;
}}

.gauge-zone {{
  position: absolute;
  top: 0;
  height: 100%;
  opacity: 0.12;
  border-radius: 7px;
}}

.gauge-dot-outer {{
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 22px;
  height: 22px;
  border-radius: 50%;
}}

.gauge-dot-inner {{
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
}}

.gauge-labels {{
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding: 0 4px;
}}

.gauge-label {{
  font-size: 22px;
  font-weight: 700;
  color: #52525b;
}}

/* Card Meta */
.card-meta {{
  display: flex;
  gap: 0;
  padding-top: 20px;
  border-top: 1px solid #1a1a24;
}}

.meta-item {{
  flex: 1;
  text-align: center;
}}

.meta-item:not(:last-child) {{
  border-right: 1px solid #1a1a24;
}}

.meta-label {{
  font-size: 20px;
  font-weight: 600;
  color: #52525b;
  margin-bottom: 6px;
}}

.meta-value {{
  font-size: 28px;
  font-weight: 800;
  color: #e4e4e7;
  font-variant-numeric: tabular-nums;
}}

/* Secondary */
.secondary {{
  margin: 16px 48px 0;
  padding: 28px 36px;
  background: linear-gradient(165deg, #111118 0%, #0c0c12 100%);
  border: 1px solid #1a1a24;
  border-radius: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}}

.sec-row {{
  display: flex;
  align-items: center;
  padding: 22px 0;
}}

.sec-row:not(:last-child) {{
  border-bottom: 1px solid #15151c;
}}

.sec-info {{
  width: 170px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}}

.sec-name {{
  font-size: 20px;
  font-weight: 600;
  color: #52525b;
  letter-spacing: 1px;
}}

.sec-value {{
  font-size: 42px;
  font-weight: 900;
  letter-spacing: -1px;
  font-variant-numeric: tabular-nums;
}}

.sec-spark {{
  flex: 1;
  height: 52px;
  padding: 0 24px;
}}

.sec-badge {{
  width: 110px;
  text-align: center;
  font-size: 22px;
  font-weight: 800;
  padding: 6px 14px;
  border-radius: 8px;
}}

.sec-badge.green {{ color: #34d399; background: rgba(34,197,94,0.1); }}
.sec-badge.blue {{ color: #60a5fa; background: rgba(96,165,250,0.1); }}
.sec-badge.red {{ color: #fb7185; background: rgba(251,113,133,0.1); }}
.sec-badge.yellow {{ color: #fbbf24; background: rgba(251,191,36,0.1); }}

/* Footer */
.footer {{
  padding: 18px 60px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.footer-tagline {{
  font-size: 20px;
  font-weight: 600;
  color: #27272a;
  letter-spacing: 3px;
  text-transform: uppercase;
}}

.footer-brand {{
  font-size: 24px;
  font-weight: 800;
  color: #a0aec0;
  letter-spacing: 0.5px;
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-title">Crypto3D 数据日报</div>
  <div class="header-date">{wd} · {ds}</div>
</div>

<div class="btc-banner">
  <div class="btc-row">
    <span class="btc-label">Bitcoin</span>
    <span class="btc-price">${bp:,}</span>
    {chg_html}
  </div>
  <div class="btc-chart">{btc_area}</div>
</div>

<div class="divider"></div>

<div class="focus-card {fcc}">
  <div class="card-header">
    <span class="card-icon">{icon}</span>
    <span class="card-name">{name}</span>
    <span class="card-badge {fcc}">{status}</span>
  </div>
  <div class="card-value" style="color:{fc}">{val_str}</div>
  <div style="margin-bottom:24px">{gauge}</div>
  {meta_block}
</div>

<div class="secondary">
{sec_rows}
</div>

<div class="footer">
  <span class="footer-tagline">Daily Market Snapshot</span>
  <span class="footer-brand">crypto3d.pro</span>
</div>

</body>
</html>"""


async def gen():
    D = load_all()
    F = pick(D)
    print(f"焦点: {F.upper()}")
    html = render(F, D)
    ts = datetime.now().strftime("%Y-%m-%d")
    hp = OUTPUT_DIR / f"{ts}.html"
    pp = OUTPUT_DIR / f"{ts}.png"
    open(hp, "w").write(html)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.goto(f"file://{hp}")
        await pg.wait_for_timeout(1000)
        await pg.screenshot(path=str(pp), type="png")
        await b.close()
    print(f"OK → {pp}")


if __name__ == "__main__":
    asyncio.run(gen())
