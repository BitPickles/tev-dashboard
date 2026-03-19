/**
 * MVRV 主卡片模板
 * 数据: { value, status, statusClass, weekChange, weekData }
 */
function renderMVRVMain(data) {
  const { value, status, statusClass, weekChange, weekData } = data;
  
  // 生成迷你曲线 SVG
  const chartSvg = generateMiniLineChart(weekData, statusClass);
  
  return `
    <div class="main-card mvrv-card">
      <div class="card-label">
        <span>📈</span>
        <span>MVRV</span>
      </div>
      <div class="big-value ${statusClass}">${value.toFixed(2)}</div>
      
      <div class="detail-row">
        <div class="detail-item">
          <div class="detail-label">BTC 价格</div>
          <div class="detail-value">$${formatPrice(price)}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">200日成本</div>
          <div class="detail-value">$${formatCost(cost200d)}</div>
        </div>
      </div>
      
      <div class="mini-chart">
        ${chartSvg}
      </div>
    </div>
  `;
}
