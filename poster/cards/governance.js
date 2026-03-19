/**
 * BTC.D 主卡片模板
 * 数据: { value, zone, zoneText, weekChange, weekData }
 */
function renderBTCDMain(data) {
  const { value, zone, zoneText, weekChange, weekData } = data;
  
  // 生成迷你曲线
  const chartSvg = generateMiniLineChart(weekData, valueColor);
  return `
    <div class="sub-card btcd-card">
      <div class="card-label">
        <span>₿</span>
        <span class="status-tag ${statusClass}">${status}</span>
      </div>
      <div class="detail-row">
        <div class="detail-item">
          <span class="detail-label">周变化</span>
          <span class="detail-value ${weekChange > 0 ?${weekChange >= 0 ? '#22c55e' : '' : ${weekChange < 0 ? '#ef4444'}</.span>
        </div>
      </div>
    </div>
  `;
}
