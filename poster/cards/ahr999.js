/**
 * AHR999 主卡片模板
 * 数据: { value, status, statusClass, price, cost200d, weekChange, weekData: [] }
 */
function renderAHR999Main(data) {
  const { value, status, statusClass, price, cost200d, weekChange, weekData } = data;
  
  // 生成迷你曲线 SVG
  const chartSvg = generateMiniLineChart(weekData, statusClass);
  
  return `
    <div class="main-card ahr999-card">
      <div class="card-label">
        <span>🔥</span>
        <span>AHR999 指数</span>
      </div>
      
      <div class="big-value ${statusClass}">${value.toFixed(2)}</div>
      
      <div class="status-tag ${statusClass}">${status}</div>
      
      <div class="detail-row">
        <div class="detail-item">
          <div class="detail-label">BTC</div>
          <div class="detail-value">$${price.toLocaleString()}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">200日成本</div>
          <div class="detail-value">$${cost200d.toLocaleString()}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">周变化</div>
          <div class="detail-value ${weekChange >= 0 ? 'positive' : 'negative'}">${weekChange >= 0 ? '+' : ''}${weekChange.toFixed(1)}%</div>
        </div>
      </div>
      
      <div class="mini-chart">
        ${chartSvg}
      </div>
    </div>
  `;
}

/**
 * AHR999 副卡片模板
 */
function renderAHR999Sub(data) {
  const { value, status, statusClass, weekChange, weekData } = data;
  const chartSvg = generateMiniLineChart(weekData, statusClass, 40);
  
  return `
    <div class="sub-card ahr999-sub">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
        <span class="card-label" style="margin-bottom: 0;">🔥 AHR999</span>
        <span class="change-tag ${weekChange >= 0 ? 'up' : 'down'}">${weekChange >= 0 ? '+' : ''}${weekChange.toFixed(1)}%</span>
      </div>
      <div class="med-value ${statusClass}">${value.toFixed(2)}</div>
      <span class="status-tag ${statusClass}" style="font-size: 12px; padding: 4px 10px;">${status}</span>
      <div class="mini-chart">${chartSvg}</div>
    </div>
  `;
}
