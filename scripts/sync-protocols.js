#!/usr/bin/env node
/**
 * 从各协议的 config.json 同步数据到 all-protocols.json
 * 用法: node scripts/sync-protocols.js
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const PROTOCOLS_DIR = path.join(DATA_DIR, 'protocols');
const OUTPUT_FILE = path.join(DATA_DIR, 'all-protocols.json');

// 从 config.json 提取 all-protocols.json 需要的字段
function extractProtocolData(config) {
  const data = {
    name: config.name,
    ticker: config.ticker,
    icon: config.icon,
    category: config.category,
    confidence: config.confidence || 'medium'
  };

  // TEV 状态
  if (config.tev_data?.has_tev) {
    data.tevStatus = 'active';
  } else if (config.tev_summary?.burns === 'ACTIVE' || config.tev_summary?.buybacks === 'ACTIVE') {
    data.tevStatus = 'partial';
  } else {
    data.tevStatus = config.tev_summary?.tevStatus || 'none';
  }

  // TEV Yield
  if (config.tev_data?.tev_yield_percent) {
    data.tev_yield_percent = config.tev_data.tev_yield_percent;
  } else if (config.calculated_tev?.tev_yield_percent) {
    data.tev_yield_percent = config.calculated_tev.tev_yield_percent;
  } else {
    data.tev_yield_percent = 0;
  }

  // 市值
  if (config.market_data?.circulating_market_cap) {
    data.market_cap_usd = config.market_data.circulating_market_cap;
  } else if (config.tev_data?.market_cap_usd) {
    data.market_cap_usd = config.tev_data.market_cap_usd;
  } else {
    data.market_cap_usd = 0;
  }

  // TVL
  if (config.tvl) {
    data.tvl = config.tvl;
  } else if (config.market_data?.tvl) {
    data.tvl = config.market_data.tvl;
  } else {
    data.tvl = 0;
  }

  // TEV Ratio
  if (config.tev_summary?.tevRatio !== undefined) {
    data.tevRatio = config.tev_summary.tevRatio;
  }

  // 备注
  if (config.tev_data?.validation) {
    data.validation = config.tev_data.validation;
  }
  if (config.tev_summary?.primary_value_accrual) {
    data.tevRatioNote = config.tev_summary.primary_value_accrual;
  }

  return data;
}

function main() {
  console.log('Syncing protocol data...\n');

  // 读取现有的 all-protocols.json
  let existing = { protocols: {} };
  if (fs.existsSync(OUTPUT_FILE)) {
    existing = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf8'));
  }

  // 扫描 protocols 目录
  const protocolDirs = fs.readdirSync(PROTOCOLS_DIR).filter(d => {
    const configPath = path.join(PROTOCOLS_DIR, d, 'config.json');
    return fs.existsSync(configPath);
  });

  console.log(`Found ${protocolDirs.length} protocol configs\n`);

  const protocols = {};
  for (const dir of protocolDirs) {
    const configPath = path.join(PROTOCOLS_DIR, dir, 'config.json');
    try {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      const data = extractProtocolData(config);
      
      // 保留现有数据中的某些字段（如 metrics）
      if (existing.protocols[dir]?.metrics) {
        data.metrics = existing.protocols[dir].metrics;
      }

      protocols[dir] = data;
      console.log(`✓ ${dir}: ${data.name} (TEV Yield: ${data.tev_yield_percent}%)`);
    } catch (e) {
      console.error(`✗ ${dir}: ${e.message}`);
    }
  }

  // 写入 all-protocols.json
  const output = {
    generated_at: new Date().toISOString(),
    protocols
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`\n✓ Written to ${OUTPUT_FILE}`);
  console.log(`  Total protocols: ${Object.keys(protocols).length}`);
}

main();
