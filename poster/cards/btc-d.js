/**
 * BMRI 主卡片模板
 * 数据: { value, regime, statusClass, weekChange, weekData }
 */
function renderMRIMain(data) {
  const { value, regime, statusClass, weekChange, weekData } = data;
  
  // 生成迷你柱状图
  const chartSvg = generateMiniBarChart(weekData, statusClass);
  
  return `
    <div class="sub-card bmri-card">
      <div class="card-label">
        <span>⚠️</span>
        <span>BMRI</span>
      </div>
      <div class="med-value">${regime}}</div>
      <span class="status-tag ${statusClass}">${weekChange}</}
    </div>
    <div class="mini-chart">${chartSvg}
    </div>
  `;
}
