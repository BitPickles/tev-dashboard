#!/usr/bin/env python3
"""
Polymarket 三级策略 Web 界面
零依赖，使用 Python 内置 http.server
"""

import http.server
import json
import os
from datetime import datetime
from urllib.parse import urlparse

PORT = 8080
JSON_FILE = "pm_opportunities.json"
REFRESH_INTERVAL = 30  # 秒


def load_data():
    """加载 JSON 数据"""
    try:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"加载数据失败: {e}")
    return None


def render_html(data):
    """渲染 HTML 页面"""
    if not data:
        return """
        <html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">
        <title>PM Strategy</title></head>
        <body style="font-family:monospace;padding:20px;background:#1a1a2e;color:#eee">
        <h2>等待数据...</h2><p>请先运行 <code>python3 pm_monitor.py</code></p>
        </body></html>
        """

    summary = data.get("summary", {})
    timestamp = data.get("timestamp", "")
    strategy = data.get("strategy", {})
    portfolio = strategy.get("portfolio", {})
    risk_status = strategy.get("risk_status", {})
    config = strategy.get("config", {})

    # 解析时间
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        time_str = timestamp[:19] if timestamp else "N/A"

    # 风控状态颜色
    risk_color = "#da3633" if risk_status.get("paused") else "#3fb950"
    risk_text = f"暂停: {risk_status.get('reason', '')}" if risk_status.get("paused") else "正常"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="{REFRESH_INTERVAL}">
    <title>Polymarket Strategy</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Consolas, monospace;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
            line-height: 1.5;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #30363d;
        }}
        .header h1 {{ font-size: 24px; color: #58a6ff; }}
        .header .time {{ color: #8b949e; font-size: 14px; }}
        .stats {{
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px 16px;
            min-width: 120px;
        }}
        .stat.p0 {{ border-color: #da3633; }}
        .stat.p1 {{ border-color: #f0883e; }}
        .stat.p2 {{ border-color: #3fb950; }}
        .stat .value {{ font-size: 24px; font-weight: bold; color: #58a6ff; }}
        .stat .label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; }}
        .portfolio {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .portfolio-item {{ }}
        .portfolio-item .label {{ font-size: 11px; color: #8b949e; }}
        .portfolio-item .value {{ font-size: 18px; font-weight: bold; }}
        .portfolio-item .value.positive {{ color: #3fb950; }}
        .portfolio-item .value.negative {{ color: #da3633; }}
        .section {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .section.p0 {{ border-color: #da3633; }}
        .section.p1 {{ border-color: #f0883e; }}
        .section.p2 {{ border-color: #3fb950; }}
        .section-header {{
            background: #21262d;
            padding: 12px 16px;
            font-weight: bold;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-header .allocation {{ color: #8b949e; font-weight: normal; font-size: 13px; }}
        .section-body {{ padding: 0; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px 16px;
            text-align: left;
            border-bottom: 1px solid #21262d;
        }}
        th {{
            background: #161b22;
            color: #8b949e;
            font-weight: normal;
            font-size: 11px;
            text-transform: uppercase;
        }}
        tr:hover {{ background: #1f2428; }}
        .price {{ color: #3fb950; font-weight: bold; }}
        .amount {{ color: #f0883e; }}
        .category {{ color: #8b949e; font-size: 12px; }}
        .question {{ max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
        .badge-p0 {{ background: #da3633; color: #fff; }}
        .badge-p1 {{ background: #f0883e; color: #fff; }}
        .badge-p2 {{ background: #3fb950; color: #fff; }}
        .badge-time {{ background: #238636; color: #fff; }}
        .empty {{ padding: 30px; text-align: center; color: #8b949e; }}
        .refresh-info {{
            text-align: center;
            color: #8b949e;
            font-size: 12px;
            margin-top: 20px;
        }}
        .risk-status {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            background: {risk_color}22;
            color: {risk_color};
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Polymarket 三级策略</h1>
        <div class="time">更新: {time_str} | <span class="risk-status">{risk_text}</span></div>
    </div>

    <div class="stats">
        <div class="stat p0">
            <div class="value">{summary.get('p0_count', 0)}</div>
            <div class="label">P0 已确定</div>
        </div>
        <div class="stat p1">
            <div class="value">{summary.get('p1_count', 0)}</div>
            <div class="label">P1 高确定性</div>
        </div>
        <div class="stat p2">
            <div class="value">{summary.get('p2_count', 0)}</div>
            <div class="label">P2 尾盘</div>
        </div>
        <div class="stat">
            <div class="value">{summary.get('endgame_count', 0)}</div>
            <div class="label">24h内结束</div>
        </div>
        <div class="stat">
            <div class="value">{summary.get('high_liquidity_count', 0)}</div>
            <div class="label">高流动性</div>
        </div>
    </div>

    <div class="portfolio">
        <div class="portfolio-item">
            <div class="label">总配额</div>
            <div class="value">${config.get('total_capital', 1000):,.0f}</div>
        </div>
        <div class="portfolio-item">
            <div class="label">P0 已投</div>
            <div class="value">${portfolio.get('p0_invested', 0):,.0f} / ${config.get('p0_allocation', 300):,.0f}</div>
        </div>
        <div class="portfolio-item">
            <div class="label">P1 已投</div>
            <div class="value">${portfolio.get('p1_invested', 0):,.0f} / ${config.get('p1_allocation', 500):,.0f}</div>
        </div>
        <div class="portfolio-item">
            <div class="label">P2 已投</div>
            <div class="value">${portfolio.get('p2_invested', 0):,.0f} / ${config.get('p2_allocation', 200):,.0f}</div>
        </div>
        <div class="portfolio-item">
            <div class="label">日盈亏</div>
            <div class="value {'positive' if portfolio.get('daily_pnl', 0) >= 0 else 'negative'}">${portfolio.get('daily_pnl', 0):+,.0f}</div>
        </div>
        <div class="portfolio-item">
            <div class="label">累计盈亏</div>
            <div class="value {'positive' if portfolio.get('cumulative_pnl', 0) >= 0 else 'negative'}">${portfolio.get('cumulative_pnl', 0):+,.0f}</div>
        </div>
    </div>
"""

    # P0 - 已确定事件
    p0_opps = strategy.get("p0", [])
    html += f"""
    <div class="section p0">
        <div class="section-header">
            <span>P0 - 已确定事件 (最高优先级)</span>
            <span class="allocation">配额: ${config.get('p0_allocation', 300):,.0f} | 要求: >=99.5%</span>
        </div>
        <div class="section-body">
"""
    if p0_opps:
        html += """
            <table>
                <tr><th>市场</th><th>买入</th><th>确定性</th><th>建议金额</th><th>流动性</th></tr>
"""
        for opp in p0_opps[:10]:
            question = opp.get("question", "")[:45]
            outcome = opp.get("outcome", "")
            price = opp.get("price", 0)
            suggested = opp.get("suggested_amount", 0)
            liquidity = opp.get("liquidity", 0)

            html += f"""
                <tr>
                    <td class="question">{question}...</td>
                    <td class="price">{outcome}</td>
                    <td class="price">{price:.2%}</td>
                    <td class="amount">${suggested:.0f}</td>
                    <td>${liquidity:,.0f}</td>
                </tr>
"""
        html += "</table>"
    else:
        html += '<div class="empty">暂无 P0 机会 (需要 >=99.5% 确定性)</div>'
    html += "</div></div>"

    # P1 - 高确定性分散
    p1_opps = strategy.get("p1", [])
    html += f"""
    <div class="section p1">
        <div class="section-header">
            <span>P1 - 高确定性分散 (中等优先级)</span>
            <span class="allocation">配额: ${config.get('p1_allocation', 500):,.0f} | 要求: >=98%, >=50k流动性</span>
        </div>
        <div class="section-body">
"""
    if p1_opps:
        html += """
            <table>
                <tr><th>类别</th><th>市场</th><th>买入</th><th>确定性</th><th>建议金额</th><th>剩余时间</th></tr>
"""
        for opp in p1_opps[:15]:
            question = opp.get("question", "")[:40]
            outcome = opp.get("outcome", "")
            price = opp.get("price", 0)
            suggested = opp.get("suggested_amount", 0)
            category = opp.get("category", "other")
            hours_left = opp.get("hours_left", 0)

            time_str = f"{hours_left:.0f}h" if hours_left < 48 else f"{hours_left/24:.0f}d"

            html += f"""
                <tr>
                    <td class="category">{category}</td>
                    <td class="question">{question}...</td>
                    <td class="price">{outcome}</td>
                    <td class="price">{price:.1%}</td>
                    <td class="amount">${suggested:.0f}</td>
                    <td>{time_str}</td>
                </tr>
"""
        html += "</table>"
    else:
        html += '<div class="empty">暂无 P1 机会 (需要 >=98% 确定性, >=50k 流动性, <=7天)</div>'
    html += "</div></div>"

    # P2 - 尾盘狙击
    p2_opps = strategy.get("p2", [])
    html += f"""
    <div class="section p2">
        <div class="section-header">
            <span>P2 - 尾盘狙击 (低优先级)</span>
            <span class="allocation">配额: ${config.get('p2_allocation', 200):,.0f} | 要求: >=95%, <=6h</span>
        </div>
        <div class="section-body">
"""
    if p2_opps:
        html += """
            <table>
                <tr><th>剩余时间</th><th>市场</th><th>买入</th><th>确定性</th><th>建议金额</th><th>流动性</th></tr>
"""
        for opp in p2_opps[:10]:
            question = opp.get("question", "")[:40]
            outcome = opp.get("outcome", "")
            price = opp.get("price", 0)
            suggested = opp.get("suggested_amount", 0)
            liquidity = opp.get("liquidity", 0)
            hours_left = opp.get("hours_left", 0)

            badge_class = "badge-p0" if hours_left < 1 else "badge-p1" if hours_left < 3 else "badge-p2"

            html += f"""
                <tr>
                    <td><span class="badge {badge_class}">{hours_left:.1f}h</span></td>
                    <td class="question">{question}...</td>
                    <td class="price">{outcome}</td>
                    <td class="price">{price:.1%}</td>
                    <td class="amount">${suggested:.0f}</td>
                    <td>${liquidity:,.0f}</td>
                </tr>
"""
        html += "</table>"
    else:
        html += '<div class="empty">暂无 P2 机会 (需要 >=95% 确定性, <=6h 剩余)</div>'
    html += "</div></div>"

    # 补充参考信息
    endgame = data.get("endgame_markets", [])
    if endgame:
        html += """
    <div class="section">
        <div class="section-header">
            <span>参考: 24小时内结束的市场</span>
            <span class="allocation">仅供参考，不在策略范围内</span>
        </div>
        <div class="section-body">
            <table>
                <tr><th>剩余时间</th><th>市场</th><th>领先方</th><th>流动性</th></tr>
"""
        for m in endgame[:5]:
            hours = m.get("hours_left", 0)
            question = m.get("question", "")[:45]
            prices = m.get("prices", {})
            liquidity = m.get("liquidity", 0)

            if prices:
                leading = max(prices.items(), key=lambda x: x[1])
                price_str = f"{leading[0]} @ {leading[1]:.1%}"
            else:
                price_str = "N/A"

            badge_class = "badge-p0" if hours < 2 else "badge-p1" if hours < 6 else "badge-time"

            html += f"""
                <tr>
                    <td><span class="badge {badge_class}">{hours:.1f}h</span></td>
                    <td class="question">{question}...</td>
                    <td class="price">{price_str}</td>
                    <td>${liquidity:,.0f}</td>
                </tr>
"""
        html += "</table></div></div>"

    html += f"""
    <div class="refresh-info">
        页面每 {REFRESH_INTERVAL} 秒自动刷新 |
        数据来源: pm_opportunities.json |
        <a href="/api/data" style="color:#58a6ff">JSON API</a>
    </div>
</body>
</html>
"""
    return html


class Handler(http.server.BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, format, *args):
        """静默日志"""
        pass

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            # 主页
            data = load_data()
            html = render_html(data)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path == "/api/data":
            # JSON API
            data = load_data()
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data or {}, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/refresh":
            # 触发刷新 (返回最新数据)
            data = load_data()
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "data": data}, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def main():
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║           Polymarket 三级策略 Web UI                       ║
    ╚════════════════════════════════════════════════════════════╝

    🌐 打开浏览器访问: http://localhost:{PORT}
    📄 JSON API: http://localhost:{PORT}/api/data
    🔄 自动刷新: 每 {REFRESH_INTERVAL} 秒

    策略说明:
    P0 - 已确定事件 (>=99.5%) - $300 配额
    P1 - 高确定性分散 (>=98%) - $500 配额
    P2 - 尾盘狙击 (>=95%, <=6h) - $200 配额

    按 Ctrl+C 停止服务
    """)

    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n Web 服务已停止")


if __name__ == "__main__":
    main()
