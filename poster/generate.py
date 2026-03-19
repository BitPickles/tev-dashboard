#!/usr/bin/env python3
"""
Crypto3D 推特日报生成器 - 模块化版本

功能：
1. 加载指标数据
2. LLM 选焦点 + 决定布局
3. 拼接卡片模板生成 HTML
4. Playwright 截图生成 PNG
"""

import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 路径配置
SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
DATA_DIR = TEV_DIR / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ==================== 数据加载 ====================

def load_json(path: Path) -> Optional[Dict]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 加载 {path} 失败: {e}")
        return None

def load_all_indicators() -> Dict[str, Any]:
    """加载所有指标数据"""
    data = {}
    
    # AHR999
    ahr999 = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr999:
        current = ahr999.get("current", {})
        history = ahr999.get("history", [])
        data["ahr999"] = {
            "value": current.get("value", 0),
            "status": current.get("status", ""),
            "price": current.get("price", 0),
            "cost_200d": current.get("cost_200d", 0),
            "date": current.get("date", ""),
            "week_data": [h.get("ahr999", h.get("value", 0)) for h in history[-7:]] if history else []
        }
    
    # MVRV
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        current = mvrv.get("current", {})
        history = mvrv.get("history", [])
        data["mvrv"] = {
            "value": current.get("value", 0),
            "status": current.get("status", ""),
            "date": current.get("date", ""),
            "week_data": [h.get("mvrv", h.get("value", 0)) for h in history[-7:]] if history else []
        }
    
    # BMRI
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri:
        current = bmri["1m"].get("current", {})
        history = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": current.get("value", 0),
            "regime": current.get("regime", "NEUTRAL"),
            "rates": current.get("rates", 0),
            "liq": current.get("liq", 0),
            "risk": current.get("risk", 0),
            "date": current.get("date", ""),
            "week_data": [h.get("bmri", h.get("value", 0)) for h in history[-7:]] if history else []
        }
    
    # BTC.D
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        current = btcd.get("current", {})
        history = btcd.get("history", [])
        data["btcd"] = {
            "value": current.get("value", 0),
            "zone": current.get("zone", "BALANCED"),
            "date": current.get("date", ""),
            "week_data": [h.get("value", 0) for h in history[-7:]] if history else []
        }
    
    return data

def load_governance() -> List[Dict]:
    """加载治理动态"""
    gov = load_json(DATA_DIR / "governance.json")
    if not gov or "proposals" not in gov:
        return []
    
    tev_related = []
    for p in gov["proposals"]:
        if p.get("is_tev_related") or p.get("isTEV"):
            tev_related.append({
                "protocol": p.get("protocol", ""),
                "title": p.get("title", ""),
                "status": p.get("status", ""),
                "isTEV": True
            })
    return tev_related

# ==================== 选题逻辑 ====================

def select_focus(indicators: Dict, governance: List[Dict]) -> Dict:
    """
    选择最有话题性的焦点
    返回: { focus_type, focus_data, sub_cards: [] }
    """
    # 优先级判断
    ahr999 = indicators.get("ahr999", {})
    mvrv = indicators.get("mvrv", {})
    bmri = indicators.get("bmri", {})
    btcd = indicators.get("btcd", {})
    
    # 1. AHR999 进入抄底区 (< 0.5)
    if ahr999.get("value", 1) < 0.5:
        return {
            "focus_type": "ahr999",
            "focus_data": ahr999,
            "sub_cards": ["mvrv", "bmri"]
        }
    
    # 2. MVRV 过热 (> 3)
    if mvrv.get("value", 0) > 3:
        return {
            "focus_type": "mvrv",
            "focus_data": mvrv,
            "sub_cards": ["ahr999", "btcd"]
        }
    
    # 3. BMRI 极端 (< 30 或 > 70)
    bmri_val = bmri.get("value", 50)
    if bmri_val < 30 or bmri_val > 70:
        return {
            "focus_type": "bmri",
            "focus_data": bmri,
            "sub_cards": ["ahr999", "mvrv"]
        }
    
    # 4. 有 TEV 相关治理动态
    if governance:
        return {
            "focus_type": "governance",
            "focus_data": governance[0],
            "sub_cards": ["ahr999", "mvrv"]
        }
    
    # 5. 默认：按周几轮换
    weekday = datetime.now().weekday()
    rotation = ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"]
    focus = rotation[weekday]
    
    sub_map = {
        "ahr999": ["mvrv", "bmri"],
        "mvrv": ["ahr999", "btcd"],
        "bmri": ["ahr999", "mvrv"],
        "btcd": ["ahr999", "mvrv"]
    }
    
    return {
        "focus_type": focus,
        "focus_data": indicators.get(focus, {}),
        "sub_cards": sub_map.get(focus, ["mvrv", "bmri"])
    }

# ==================== SVG 图表生成 ====================

def generate_line_chart_svg(data: List[float], color: str = "#22c55e", height: int = 50) -> str:
    """生成迷你折线图 SVG"""
    if not data or len(data) < 2:
        return ""
    
    # 归一化数据到 0-height
    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val if max_val != min_val else 1
    
    points = []
    width = 200
    step = width / (len(data) - 1)
    
    for i, val in enumerate(data):
        x = i * step
        y = height - ((val - min_val) / range_val) * (height - 10) - 5
        points.append(f"{x:.1f},{y:.1f}")
    
    return f'''<svg viewBox="0 0 200 {height}" preserveAspectRatio="none">
      <polyline fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="{" ".join(points)}"/>
      <circle cx="{width}" cy="{points[-1].split(',')[1]}" r="3" fill="{color}"/>
    </svg>'''

# ==================== 卡片渲染 ====================

def get_status_class(status: str) -> str:
    """根据状态返回 CSS 类名"""
    positive_keywords = ["抄底", "合理", "NEUTRAL", "BALANCED", "LOW", "FAIR", "低估"]
    negative_keywords = ["过热", "HIGH", "EXTREME", "DANGER", "高估"]
    
    status_lower = status.lower()
    for kw in positive_keywords:
        if kw.lower() in status_lower:
            return "positive"
    for kw in negative_keywords:
        if kw.lower() in status_lower:
            return "negative"
    return "neutral"

def get_change_tag(week_data: List[float]) -> str:
    """计算周变化"""
    if len(week_data) < 2:
        return "+0.0%", "neutral"
    
    first, last = week_data[0], week_data[-1]
    if first == 0:
        return "+0.0%", "neutral"
    
    change = ((last - first) / first) * 100
    if change > 0:
        return f"+{change:.1f}%", "positive"
    elif change < 0:
        return f"{change:.1f}%", "negative"
    return "+0.0%", "neutral"

def render_ahr999_main(data: Dict) -> str:
    """渲染 AHR999 主卡片"""
    value = data.get("value", 0)
    status = data.get("status", "")
    status_class = get_status_class(status)
    price = data.get("price", 0)
    cost_200d = data.get("cost_200d", 0)
    week_data = data.get("week_data", [])
    
    change_tag, change_class = get_change_tag(week_data)
    chart_svg = generate_line_chart_svg(week_data, "#22c55e" if status_class == "positive" else "#3b82f6")
    
    return f'''
    <div class="main-card">
      <div class="card-label">
        <span class="emoji">🔥</span>
        <span>AHR999 指数</span>
      </div>
      <div class="big-value {status_class}">{value:.2f}</div>
      <div class="status-tag {status_class}">{status}</div>
      <div class="detail-row">
        <div class="detail-item">
          <div class="detail-label">BTC</div>
          <div class="detail-value">${price:,.0f}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">200日成本</div>
          <div class="detail-value">${cost_200d:,.0f}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">周变化</div>
          <div class="detail-value {change_class}">{change_tag}</div>
        </div>
      </div>
      <div class="mini-chart">{chart_svg}</div>
    </div>'''

def render_mvrv_sub(data: Dict) -> str:
    """渲染 MVRV 副卡片"""
    value = data.get("value", 0)
    status = data.get("status", "")
    status_class = get_status_class(status)
    week_data = data.get("week_data", [])
    
    change_tag, change_class = get_change_tag(week_data)
    chart_svg = generate_line_chart_svg(week_data, "#22c55e" if status_class == "positive" else "#3b82f6", 40)
    
    return f'''
    <div class="sub-card">
      <div class="sub-header">
        <span class="card-label"><span class="emoji">📈</span> MVRV</span>
        <span class="change-tag {change_class}">{change_tag}</span>
      </div>
      <div class="med-value {status_class}">{value:.2f}</div>
      <span class="status-tag {status_class} small">{status}</span>
      <div class="mini-chart small">{chart_svg}</div>
    </div>'''

def render_bmri_sub(data: Dict) -> str:
    """渲染 BMRI 副卡片"""
    value = data.get("value", 0)
    regime = data.get("regime", "NEUTRAL")
    status_class = "positive" if value < 30 else "negative" if value > 70 else "neutral"
    week_data = data.get("week_data", [])
    
    change_tag, change_class = get_change_tag(week_data)
    chart_svg = generate_line_chart_svg(week_data, "#3b82f6", 40)
    
    status_text = "低风险" if value < 30 else "高风险" if value > 70 else "中性"
    
    return f'''
    <div class="sub-card">
      <div class="sub-header">
        <span class="card-label"><span class="emoji">⚠️</span> BMRI</span>
        <span class="change-tag {change_class}">{change_tag}</span>
      </div>
      <div class="med-value {status_class}">{value:.1f}</div>
      <span class="status-tag {status_class} small">{status_text}</span>
      <div class="mini-chart small">{chart_svg}</div>
    </div>'''

def render_btcd_sub(data: Dict) -> str:
    """渲染 BTC.D 副卡片"""
    value = data.get("value", 0)
    zone = data.get("zone", "BALANCED")
    week_data = data.get("week_data", [])
    
    zone_text = "BTC主导" if zone == "BTC_DOMINANT" else "山寨季" if zone == "ALT_SEASON" else "平衡"
    status_class = "neutral"
    change_tag, change_class = get_change_tag(week_data)
    chart_svg = generate_line_chart_svg(week_data, "#3b82f6", 40)
    
    return f'''
    <div class="sub-card">
      <div class="sub-header">
        <span class="card-label"><span class="emoji">₿</span> BTC.D</span>
        <span class="change-tag {change_class}">{change_tag}</span>
      </div>
      <div class="med-value {status_class}">{value:.1f}%</div>
      <span class="status-tag {status_class} small">{zone_text}</span>
      <div class="mini-chart small">{chart_svg}</div>
    </div>'''

# ==================== 主模板 ====================

def render_poster(focus_type: str, focus_data: Dict, sub_cards: List[str], indicators: Dict) -> str:
    """渲染完整海报"""
    today = datetime.now().strftime("%b %d, %Y")
    
    # 渲染主卡片
    if focus_type == "ahr999":
        main_card_html = render_ahr999_main(focus_data)
    else:
        # 默认用 AHR999
        main_card_html = render_ahr999_main(indicators.get("ahr999", {}))
    
    # 渲染副卡片
    sub_cards_html = ""
    card_renderers = {
        "mvrv": render_mvrv_sub,
        "bmri": render_bmri_sub,
        "btcd": render_btcd_sub,
        "ahr999": lambda d: render_ahr999_main(d).replace("main-card", "sub-card").replace("big-value", "med-value")
    }
    
    for card_type in sub_cards[:2]:  # 最多2个副卡
        card_data = indicators.get(card_type, {})
        renderer = card_renderers.get(card_type)
        if renderer:
            sub_cards_html += renderer(card_data)
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>Crypto3D Daily</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
    
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    
    body {{
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      background: #0a0a0b;
      color: #fafafa;
      width: 1080px;
      height: 1350px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    
    /* Header */
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 30px 50px;
      border-bottom: 1px solid #27272a;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 15px;
      font-size: 26px;
      font-weight: 700;
    }}
    .logo-icon {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #3b82f6, #22c55e);
      border-radius: 11px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
    }}
    .date {{ color: #71717a; font-size: 18px; }}
    
    /* Main */
    .main {{
      flex: 1;
      padding: 40px 50px;
      display: flex;
      flex-direction: column;
      gap: 30px;
    }}
    
    /* 主卡片 */
    .main-card {{
      background: linear-gradient(145deg, #18181b 0%, #0f0f11 100%);
      border-radius: 24px;
      padding: 40px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    
    /* 副卡片容器 */
    .sub-cards {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}
    
    /* 副卡片 */
    .sub-card {{
      background: linear-gradient(145deg, #18181b 0%, #0f0f11 100%);
      border-radius: 16px;
      padding: 24px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .sub-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    
    /* 卡片标签 */
    .card-label {{
      font-size: 15px;
      color: #71717a;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .emoji {{ font-size: 18px; }}
    
    /* 数值 */
    .big-value {{
      font-size: 80px;
      font-weight: 700;
      letter-spacing: -3px;
      margin: 20px 0 16px;
    }}
    .med-value {{
      font-size: 36px;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    
    /* 状态颜色 */
    .positive {{ color: #22c55e; }}
    .negative {{ color: #ef4444; }}
    .neutral {{ color: #3b82f6; }}
    
    /* 状态标签 */
    .status-tag {{
      display: inline-block;
      padding: 8px 18px;
      border-radius: 20px;
      font-size: 16px;
      font-weight: 600;
    }}
    .status-tag.positive {{ background: rgba(34, 197, 94, 0.15); }}
    .status-tag.negative {{ background: rgba(239, 68, 68, 0.15); }}
    .status-tag.neutral {{ background: rgba(59, 130, 246, 0.15); }}
    .status-tag.small {{ font-size: 12px; padding: 4px 10px; }}
    
    /* 变化标签 */
    .change-tag {{
      font-size: 12px;
      font-weight: 600;
      padding: 4px 8px;
      border-radius: 6px;
    }}
    .change-tag.positive {{ background: rgba(34, 197, 94, 0.15); color: #22c55e; }}
    .change-tag.negative {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; }}
    
    /* 详情行 */
    .detail-row {{
      display: flex;
      justify-content: space-around;
      margin-top: 30px;
    }}
    .detail-item {{ text-align: center; }}
    .detail-label {{
      font-size: 13px;
      color: #52525b;
      margin-bottom: 6px;
    }}
    .detail-value {{
      font-size: 20px;
      font-weight: 600;
      color: #fafafa;
    }}
    
    /* 迷你图表 */
    .mini-chart {{ height: 50px; margin-top: 20px; }}
    .mini-chart.small {{ height: 40px; margin-top: 12px; }}
    .mini-chart svg {{
      width: 100%;
      height: 100%;
    }}
    
    /* Footer */
    .footer {{
      padding: 25px 50px;
      border-top: 1px solid #27272a;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 16px;
      color: #71717a;
    }}
    .footer-link {{
      color: #3b82f6;
      font-weight: 600;
      font-size: 18px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="logo">
      <div class="logo-icon">📊</div>
      Crypto3D Daily
    </div>
    <div class="date">{today}</div>
  </div>
  
  <div class="main">
    {main_card_html}
    
    <div class="sub-cards">
      {sub_cards_html}
    </div>
  </div>
  
  <div class="footer">
    <span>每日加密市场晴雨表</span>
    <span class="footer-link">crypto3d.pro</span>
  </div>
</body>
</html>'''

# ==================== 主函数 ====================

async def generate_poster(headless: bool = True) -> Path:
    """生成海报"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请安装 playwright: pip install playwright && playwright install chromium")
        return None
    
    # 1. 加载数据
    print("[1/4] 加载数据...")
    indicators = load_all_indicators()
    governance = load_governance()
    
    # 2. 选焦点
    print("[2/4] 选择焦点...")
    focus_info = select_focus(indicators, governance)
    print(f"  焦点: {focus_info['focus_type'].upper()}")
    print(f"  副卡: {focus_info['sub_cards']}")
    
    # 3. 渲染 HTML
    print("[3/4] 渲染海报...")
    html = render_poster(
        focus_info["focus_type"],
        focus_info["focus_data"],
        focus_info["sub_cards"],
        indicators
    )
    
    # 保存 HTML
    today = datetime.now().strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{today}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # 4. 截图
    print("[4/4] 截图生成 PNG...")
    png_path = OUTPUT_DIR / f"{today}.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()
    
    print(f"[OK] 海报已生成: {png_path}")
    return png_path

if __name__ == "__main__":
    import sys
    headless = "--no-headless" not in sys.argv
    asyncio.run(generate_poster(headless))
