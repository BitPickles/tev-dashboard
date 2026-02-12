/**
 * Crypto3D Indicators - Chart Utilities
 * 共用图表工具函数
 */

/**
 * 格式化时间为 YYYY/MM/DD
 * 支持多种输入格式：字符串日期、时间戳、对象格式
 * @param {string|number|object} time - 时间值
 * @returns {string} 格式化后的日期字符串
 */
function formatTime(time) {
  if (!time) return '—';
  
  // 字符串格式 "2024-01-15"
  if (typeof time === 'string') {
    const parts = time.split('-');
    if (parts.length === 3) {
      return `${parts[0]}/${parts[1]}/${parts[2]}`;
    }
    return time;
  }
  
  // 时间戳格式 (秒)
  if (typeof time === 'number') {
    const date = new Date(time * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}/${month}/${day}`;
  }
  
  // 对象格式 { year, month, day } (lightweight-charts business day)
  if (time.year !== undefined) {
    const year = time.year;
    const month = String(time.month).padStart(2, '0');
    const day = String(time.day).padStart(2, '0');
    return `${year}/${month}/${day}`;
  }
  
  return '—';
}

/**
 * 格式化数字
 * @param {number} value - 数值
 * @param {number} precision - 小数位数 (默认 2)
 * @param {string} prefix - 前缀 (如 '$')
 * @param {string} suffix - 后缀 (如 '%')
 * @returns {string} 格式化后的数字字符串
 */
function formatNumber(value, precision = 2, prefix = '', suffix = '') {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return prefix + value.toFixed(precision) + suffix;
}

/**
 * 格式化价格 (带千分位)
 * @param {number} value - 价格
 * @param {string} currency - 货币符号 (默认 '$')
 * @returns {string} 格式化后的价格
 */
function formatPrice(value, currency = '$') {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return currency + value.toLocaleString();
}

/**
 * 格式化市值
 * @param {number} value - 市值
 * @returns {string} 格式化后的市值 (如 $1.23T, $456B)
 */
function formatMarketCap(value) {
  if (value === null || value === undefined || isNaN(value)) return '—';
  if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
  if (value >= 1e9) return '$' + (value / 1e9).toFixed(0) + 'B';
  if (value >= 1e6) return '$' + (value / 1e6).toFixed(0) + 'M';
  return '$' + value.toLocaleString();
}

/**
 * 创建图表实例
 * @param {HTMLElement|string} container - 容器元素或选择器
 * @param {object} options - 自定义配置 (可选)
 * @returns {object} lightweight-charts 实例
 */
function createChart(container, options = {}) {
  if (typeof container === 'string') {
    container = document.getElementById(container) || document.querySelector(container);
  }
  
  const defaultOptions = {
    layout: {
      background: { type: 'solid', color: 'transparent' },
      textColor: '#a1a1aa',
      fontFamily: "'Inter', sans-serif",
    },
    grid: {
      vertLines: { color: 'rgba(39, 39, 42, 0.5)' },
      horzLines: { color: 'rgba(39, 39, 42, 0.5)' },
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { 
        color: 'rgba(59, 130, 246, 0.5)', 
        labelBackgroundColor: '#3b82f6' 
      },
      horzLine: { 
        color: 'rgba(59, 130, 246, 0.5)', 
        labelBackgroundColor: '#3b82f6' 
      },
    },
    rightPriceScale: {
      borderColor: '#27272a',
      scaleMargins: { top: 0.05, bottom: 0.05 },
    },
    leftPriceScale: {
      visible: false,
      borderColor: '#27272a',
      scaleMargins: { top: 0.05, bottom: 0.05 },
    },
    timeScale: {
      borderColor: '#27272a',
      timeVisible: false,
      secondsVisible: false,
      minBarSpacing: 0.1,
      fixLeftEdge: true,
      fixRightEdge: false,
      tickMarkFormatter: (time) => {
        if (typeof time === 'string') return time.substring(0, 4);
        if (typeof time === 'number') return new Date(time * 1000).getFullYear().toString();
        if (time.year !== undefined) return time.year.toString();
        return '';
      },
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true },
    handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
  };
  
  // 深度合并配置
  const mergedOptions = deepMerge(defaultOptions, options);
  
  const chart = LightweightCharts.createChart(container, mergedOptions);
  
  // 自动响应容器大小变化
  const resizeObserver = new ResizeObserver(entries => {
    if (entries.length === 0) return;
    const { width, height } = entries[0].contentRect;
    chart.applyOptions({ width, height });
  });
  resizeObserver.observe(container);
  
  // 保存 resizeObserver 以便后续清理
  chart._resizeObserver = resizeObserver;
  
  return chart;
}

/**
 * 配置 Tooltip 交互
 * @param {object} chart - lightweight-charts 实例
 * @param {object} historyData - 历史数据查找表 { date: dataPoint }
 * @param {object} config - Tooltip 配置
 * @param {object} config.seriesVisible - 系列可见性 { seriesName: boolean }
 * @param {Array} config.fields - 字段配置 [{ key, elementId, format }]
 * @param {string} config.dateElementId - 日期显示元素 ID
 */
function setupTooltip(chart, historyData, config) {
  const { seriesVisible, fields, dateElementId = 'tooltip-date' } = config;
  
  chart.subscribeCrosshairMove((param) => {
    const dateEl = document.getElementById(dateElementId);
    
    if (!param.time || !param.point) {
      if (dateEl) dateEl.textContent = '—';
      fields.forEach(field => {
        const container = document.getElementById(field.containerId || `tooltip-${field.key}`);
        if (container) container.style.display = 'none';
      });
      return;
    }
    
    // 显示日期
    if (dateEl) dateEl.textContent = formatTime(param.time);
    
    // 获取数据点
    const dateStr = typeof param.time === 'string' ? param.time : 
      `${param.time.year}-${String(param.time.month).padStart(2, '0')}-${String(param.time.day).padStart(2, '0')}`;
    const dataPoint = historyData[dateStr];
    
    // 更新每个字段
    fields.forEach(field => {
      const container = document.getElementById(field.containerId || `tooltip-${field.key}`);
      const valueEl = document.getElementById(field.valueId || `tooltip-${field.key}-value`);
      
      if (!container || !valueEl) return;
      
      const isVisible = seriesVisible[field.key];
      const hasValue = dataPoint && dataPoint[field.dataKey || field.key] !== undefined;
      
      if (isVisible && hasValue) {
        container.style.display = 'flex';
        const value = dataPoint[field.dataKey || field.key];
        valueEl.textContent = field.format ? field.format(value) : value;
      } else {
        container.style.display = 'none';
      }
    });
  });
}

/**
 * 设置图表默认可视范围
 * @param {object} chart - lightweight-charts 实例
 * @param {string} startDate - 起始日期 (YYYY-MM-DD)
 * @param {string} endDate - 结束日期 (YYYY-MM-DD)
 * @param {number} delay - 延迟毫秒数 (默认 100)
 * @returns {object} 范围对象 { from, to }
 */
function setDefaultRange(chart, startDate, endDate, delay = 100) {
  const fromTs = new Date(startDate + 'T00:00:00Z').getTime() / 1000;
  const toTs = new Date(endDate + 'T00:00:00Z').getTime() / 1000;
  const range = { from: fromTs, to: toTs };
  
  setTimeout(() => {
    chart.timeScale().setVisibleRange(range);
  }, delay);
  
  return range;
}

/**
 * 添加未来空白区域 (用于右侧留白)
 * @param {Array} data - 数据数组 [{ time, value }]
 * @param {string} lastDate - 最后日期 (YYYY-MM-DD)
 * @param {number} days - 空白天数 (默认 180)
 * @returns {Array} 添加空白后的数据数组
 */
function addFutureWhitespace(data, lastDate, days = 180) {
  const result = [...data];
  const lastDateObj = new Date(lastDate);
  
  for (let i = 1; i <= days; i++) {
    const d = new Date(lastDateObj);
    d.setDate(d.getDate() + i);
    result.push({ time: d.toISOString().split('T')[0] });
  }
  
  return result;
}

/**
 * 创建基线区域 (用于显示颜色区间)
 * @param {object} chart - lightweight-charts 实例
 * @param {number} baseValue - 基准值
 * @param {object} colors - 颜色配置
 * @param {string} priceScaleId - 价格轴 ID (默认 'right')
 * @returns {object} baseline series
 */
function createZoneSeries(chart, baseValue, colors, priceScaleId = 'right') {
  const {
    topFill1 = 'transparent',
    topFill2 = 'transparent',
    bottomFill1 = 'transparent',
    bottomFill2 = 'transparent',
  } = colors;
  
  return chart.addBaselineSeries({
    baseValue: { type: 'price', price: baseValue },
    topLineColor: 'transparent',
    topFillColor1: topFill1,
    topFillColor2: topFill2,
    bottomLineColor: 'transparent',
    bottomFillColor1: bottomFill1,
    bottomFillColor2: bottomFill2,
    priceScaleId,
    lastValueVisible: false,
    priceLineVisible: false,
  });
}

/**
 * 创建阈值线
 * @param {object} series - 线系列实例
 * @param {number} price - 阈值价格
 * @param {string} color - 线颜色
 * @param {object} options - 其他配置
 */
function createThresholdLine(series, price, color, options = {}) {
  series.createPriceLine({
    price,
    color,
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: true,
    ...options,
  });
}

/**
 * 切换系列可见性
 * @param {object} series - 系列对象 { name: seriesInstance }
 * @param {object} seriesVisible - 可见性状态 { name: boolean }
 * @param {string} name - 系列名称
 * @param {object} zones - 关联的区域系列 (可选)
 */
function toggleSeriesVisibility(series, seriesVisible, name, zones = null) {
  if (!series[name]) return;
  
  seriesVisible[name] = !seriesVisible[name];
  series[name].applyOptions({ visible: seriesVisible[name] });
  
  // 如果有关联的区域，同步切换
  if (zones && name in zones) {
    Object.values(zones[name] || {}).forEach(zone => {
      if (zone) zone.applyOptions({ visible: seriesVisible[name] });
    });
  }
  
  // 更新图例样式
  const legendItem = document.querySelector(`.legend-item[data-series="${name}"]`);
  if (legendItem) {
    legendItem.classList.toggle('disabled', !seriesVisible[name]);
  }
}

/**
 * 切换价格轴坐标模式 (线性/对数)
 * @param {object} chart - lightweight-charts 实例
 * @param {boolean} isLogScale - 当前是否对数坐标
 * @param {string} labelElementId - 显示标签的元素 ID
 * @param {Array} priceScaleIds - 要切换的价格轴 ID 列表
 * @returns {boolean} 切换后的坐标模式
 */
function toggleScaleMode(chart, isLogScale, labelElementId = 'scale-label', priceScaleIds = ['right']) {
  const newIsLog = !isLogScale;
  const mode = newIsLog 
    ? LightweightCharts.PriceScaleMode.Logarithmic 
    : LightweightCharts.PriceScaleMode.Normal;
  
  priceScaleIds.forEach(id => {
    chart.priceScale(id).applyOptions({ mode });
  });
  
  const labelEl = document.getElementById(labelElementId);
  if (labelEl) {
    labelEl.textContent = newIsLog ? 'Log' : 'Lin';
  }
  
  return newIsLog;
}

/**
 * 构建数据查找表
 * @param {Array} history - 历史数据数组
 * @param {string} dateKey - 日期字段名 (默认 'date')
 * @returns {object} 查找表 { date: dataPoint }
 */
function buildHistoryLookup(history, dateKey = 'date') {
  const lookup = {};
  history.forEach(d => {
    lookup[d[dateKey]] = d;
  });
  return lookup;
}

/**
 * 深度合并对象
 * @param {object} target - 目标对象
 * @param {object} source - 源对象
 * @returns {object} 合并后的对象
 */
function deepMerge(target, source) {
  const result = { ...target };
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = deepMerge(result[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  }
  return result;
}

/**
 * 语言切换工具
 */
const LangUtils = {
  currentLang: 'zh',
  
  /**
   * 初始化语言设置
   */
  init() {
    const saved = localStorage.getItem('lang');
    if (saved) {
      this.currentLang = saved;
      this.update();
    }
  },
  
  /**
   * 切换语言
   */
  toggle() {
    this.currentLang = this.currentLang === 'zh' ? 'en' : 'zh';
    this.update();
  },
  
  /**
   * 更新页面语言
   */
  update() {
    document.getElementById('lang-zh').className = this.currentLang === 'zh' ? 'active' : '';
    document.getElementById('lang-en').className = this.currentLang === 'en' ? 'active' : '';
    document.documentElement.lang = this.currentLang === 'zh' ? 'zh-CN' : 'en';
    
    document.querySelectorAll('[data-zh]').forEach(el => {
      el.textContent = el.getAttribute(`data-${this.currentLang}`);
    });
    
    localStorage.setItem('lang', this.currentLang);
  },
  
  /**
   * 获取当前语言
   * @returns {string} 'zh' 或 'en'
   */
  get() {
    return this.currentLang;
  }
};

// 导出 (兼容 ES modules、Node.js 和浏览器全局变量)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatTime,
    formatNumber,
    formatPrice,
    formatMarketCap,
    createChart,
    setupTooltip,
    setDefaultRange,
    addFutureWhitespace,
    createZoneSeries,
    createThresholdLine,
    toggleSeriesVisibility,
    toggleScaleMode,
    buildHistoryLookup,
    deepMerge,
    LangUtils,
  };
}

// 浏览器环境：确保全局可用
if (typeof window !== 'undefined') {
  window.formatTime = formatTime;
  window.formatNumber = formatNumber;
  window.formatPrice = formatPrice;
  window.formatMarketCap = formatMarketCap;
  window.createChart = createChart;
  window.setupTooltip = setupTooltip;
  window.setDefaultRange = setDefaultRange;
  window.addFutureWhitespace = addFutureWhitespace;
  window.createZoneSeries = createZoneSeries;
  window.createThresholdLine = createThresholdLine;
  window.toggleSeriesVisibility = toggleSeriesVisibility;
  window.toggleScaleMode = toggleScaleMode;
  window.buildHistoryLookup = buildHistoryLookup;
  window.deepMerge = deepMerge;
  window.LangUtils = LangUtils;
}
