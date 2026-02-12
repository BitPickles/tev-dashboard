# 组件说明

## 共享文件

### common.css
位置: `indicators/css/common.css`

包含所有页面共用的样式：
- CSS 变量（颜色、字体）
- 布局工具类
- 卡片样式
- 图表容器
- 响应式断点

### chart-utils.js
位置: `indicators/js/chart-utils.js`

图表工具函数库：

```javascript
// 创建图表实例
createChart(containerId, options)

// 设置默认显示范围
setDefaultRange(chart, startDate, endDate)

// 创建阈值线
createThresholdLine(series, value, color, options)

// 创建区域填充
createZoneSeries(chart, threshold, colors)

// 切换系列显示
toggleSeriesVisibility(series, visibleState, name, zones)

// 添加未来留白
addFutureWhitespace(data, lastDate, days)

// 构建日期查找表
buildHistoryLookup(history)

// 格式化时间
formatTime(time)

// 格式化市值
formatMarketCap(value)

// 语言工具
LangUtils.init()
LangUtils.get()
LangUtils.toggle()
```

## UI 组件

### 统计卡片 (.stat-card)
```html
<div class="stat-card">
  <div class="stat-label">标签</div>
  <div class="stat-value">数值</div>
  <div class="stat-hint">提示</div>
</div>
```

变体：
- `.stat-card.main` - 主卡片，更大的 padding
- 内联 `style="flex: 1;"` - 弹性宽度

### 进度条 (.bucket-bar)
```html
<div class="bucket-bar">
  <div class="bucket-fill positive" style="width: 60%;"></div>
</div>
```

- `.bucket-fill.positive` - 绿色（好）
- `.bucket-fill.negative` - 红色（差）

### 版本切换 (.version-tabs)
```html
<div class="version-tabs">
  <div class="version-tab active" data-version="6m" onclick="switchVersion('6m')">
    <div>6M 版</div>
    <div class="version-desc">中周期趋势</div>
  </div>
  <div class="version-tab" data-version="1m" onclick="switchVersion('1m')">
    <div>1M 版</div>
    <div class="version-desc">短期冲击</div>
  </div>
</div>
```

### Zone Legend (.zone-legend)
```html
<div class="zone-legend">
  <div class="zone-item">
    <div class="zone-dot risk-on"></div>
    <span>< 25 Risk-On</span>
  </div>
  <div class="zone-item">
    <div class="zone-dot neutral"></div>
    <span>中性区间</span>
  </div>
  <div class="zone-item">
    <div class="zone-dot risk-off"></div>
    <span>> 75 Risk-Off</span>
  </div>
</div>
```

### 图表容器 (.chart-container)
```html
<div class="chart-container">
  <div class="chart-header">
    <div class="chart-title">标题</div>
    <div class="chart-legend">
      <div class="legend-item" onclick="toggleSeries('xxx')">
        <div class="legend-line" style="background: #3b82f6;"></div>
        <span>名称</span>
      </div>
    </div>
  </div>
  <div class="chart-wrapper" id="chart-container"></div>
  <div class="chart-tooltip floating" id="chart-tooltip">...</div>
  <div class="chart-hint">💡 提示文字</div>
</div>
```

### 加载状态 (.loading)
```html
<div id="loading" class="loading">
  <div class="loading-spinner"></div>
  <div>加载中...</div>
</div>
```

### 说明区块 (.info-section)
```html
<div class="info-section">
  <h2 class="info-title">💡 标题</h2>
  <div class="info-text">
    <p>段落内容...</p>
  </div>
</div>
```

## 图表系列颜色

| 系列 | 颜色 |
|------|------|
| 主指标 (BMRI/AHR999) | #3b82f6 (蓝) |
| BTC 价格 | #f7931a (橙) |
| Rates | #06b6d4 (青) |
| Liquidity | #22c55e (绿) |
| Risk | #f59e0b (琥珀) |
| Total MCap | #8b5cf6 (紫) |

## Tooltip 结构
```html
<div class="chart-tooltip floating" id="chart-tooltip">
  <div class="tooltip-date">2026-02-11</div>
  <div class="tooltip-item">
    <div class="tooltip-dot" style="background: #3b82f6;"></div>
    <span class="tooltip-label">BMRI:</span>
    <span class="tooltip-value">59.9</span>
  </div>
</div>
```

## 国际化

使用 `data-zh` 和 `data-en` 属性：
```html
<span data-zh="抄底区" data-en="Bottom Zone">抄底区</span>
```

JS 切换：
```javascript
LangUtils.init();  // 初始化，读取 localStorage
LangUtils.toggle(); // 切换语言
```
