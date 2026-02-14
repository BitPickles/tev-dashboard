#!/usr/bin/env node
/**
 * sync-tev-data.js - TEV 数据自动同步脚本
 * 
 * 功能：
 * 1. 从 DefiLlama 获取 Revenue 数据
 * 2. 从 CoinGecko 获取市值数据
 * 3. 根据 tevRatio 计算 TEV
 * 4. 更新 all-protocols.json
 * 
 * 用法：
 *   node scripts/sync-tev-data.js           # 更新所有协议
 *   node scripts/sync-tev-data.js aave gmx  # 只更新指定协议
 *   node scripts/sync-tev-data.js --dry-run # 预览不写入
 */

const fs = require('fs');
const path = require('path');

// 协议配置：DefiLlama slug, CoinGecko id, CMC slug, tevRatio
const PROTOCOL_CONFIG = {
  aave: { 
    defillamaSlug: 'aave', 
    coingeckoId: 'aave',
    cmcSlug: 'aave',
    tevRatio: null,  // 特殊：固定年度回购 $50M
    fixedTevUsd: 50000000,
    note: '年度回购 $50M + Safety Module'
  },
  curve: { 
    defillamaSlug: 'curve-dex', 
    coingeckoId: 'curve-dao-token',
    cmcSlug: 'curve-dao-token',
    tevRatio: 0.5,
    note: 'veCRV 分红 50%'
  },
  dydx: { 
    defillamaSlug: 'dydx', 
    coingeckoId: 'dydx-chain',
    cmcSlug: 'dydx',
    tevRatio: 0.75,
    note: '75% 净协议费用回购'
  },
  etherfi: { 
    defillamaSlug: 'ether.fi', 
    coingeckoId: 'ether-fi',
    cmcSlug: 'ether-fi',
    tevRatio: null,  // 从 TEV Yield 反推
    note: '提现收入回购'
  },
  gmx: { 
    defillamaSlug: 'gmx', 
    coingeckoId: 'gmx',
    cmcSlug: 'gmx',
    tevRatio: 0.3,
    note: '30% 费用分红'
  },
  maple: { 
    defillamaSlug: 'maple', 
    coingeckoId: 'maple',
    cmcSlug: 'syrup',
    tevRatio: 0.2,
    note: '20% 协议收入回购 SYRUP'
  },
  pancakeswap: { 
    defillamaSlug: 'pancakeswap', 
    coingeckoId: 'pancakeswap-token',
    cmcSlug: 'pancakeswap',
    tevRatio: null,  // 从 TEV Yield 反推
    note: 'CAKE 回购销毁'
  },
  pendle: { 
    defillamaSlug: 'pendle', 
    coingeckoId: 'pendle',
    cmcSlug: 'pendle',
    tevRatio: 0.8,
    note: '80% 协议收入回购分配'
  },
  sky: { 
    defillamaSlug: 'sky', 
    coingeckoId: 'maker',
    cmcSlug: 'maker',
    tevRatio: null,  // 从 TEV Yield 反推
    note: 'Smart Burn Engine'
  },
};

// 不自动更新的协议
const SKIP_PROTOCOLS = ['aster', 'hype', 'hyperliquid', 'bnb', 'uniswap', 'bgb', 'okb'];

const DATA_FILE = path.join(__dirname, '../data/all-protocols.json');

// API 请求封装
async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// 获取 DefiLlama Revenue
async function getDefillamaRevenue(slug) {
  try {
    const data = await fetchJson(`https://api.llama.fi/summary/fees/${slug}?dataType=dailyRevenue`);
    const chart = data.totalDataChart || [];
    const last365 = chart.slice(-365);
    const total365 = last365.reduce((sum, d) => sum + (d[1] || 0), 0);
    const total30 = chart.slice(-30).reduce((sum, d) => sum + (d[1] || 0), 0);
    return { revenue365d: total365, revenue30d: total30 };
  } catch (e) {
    console.warn(`  ⚠️ DefiLlama ${slug}: ${e.message}`);
    return null;
  }
}

// 获取 CoinGecko 市值（带重试）
async function getCoingeckoMarketCap(id, retries = 2) {
  for (let i = 0; i < retries; i++) {
    try {
      if (i > 0) {
        console.log(`  ⏳ CoinGecko 重试 ${i + 1}/${retries}...`);
        await new Promise(r => setTimeout(r, 3000 * i));
      }
      const data = await fetchJson(`https://api.coingecko.com/api/v3/simple/price?ids=${id}&vs_currencies=usd&include_market_cap=true`);
      const mcap = data[id]?.usd_market_cap || 0;
      if (mcap > 0) return mcap;
    } catch (e) {
      if (i === retries - 1) {
        console.warn(`  ⚠️ CoinGecko ${id}: ${e.message}`);
      }
    }
  }
  return null;
}

// 获取 CMC 市值（备用源）
async function getCmcMarketCap(slug) {
  try {
    // 使用 CMC 公开 API
    const data = await fetchJson(`https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?slug=${slug}`);
    const mcap = data?.data?.statistics?.marketCap || 0;
    if (mcap > 0) {
      console.log(`  ✓ CMC 备用成功`);
      return mcap;
    }
  } catch (e) {
    console.warn(`  ⚠️ CMC ${slug}: ${e.message}`);
  }
  return null;
}

// 获取市值（CoinGecko 优先，CMC 备用）
async function getMarketCap(coingeckoId, cmcSlug) {
  // 先尝试 CoinGecko
  let mcap = await getCoingeckoMarketCap(coingeckoId);
  if (mcap && mcap > 0) return mcap;
  
  // CoinGecko 失败，尝试 CMC
  if (cmcSlug) {
    console.log(`  → 切换到 CMC...`);
    mcap = await getCmcMarketCap(cmcSlug);
    if (mcap && mcap > 0) return mcap;
  }
  
  return null;
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const targetProtocols = args.filter(a => !a.startsWith('--'));
  
  console.log('=== TEV 数据同步 ===\n');
  if (dryRun) console.log('🔍 预览模式（不写入）\n');
  
  // 读取现有数据
  const allData = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  const protocols = allData.protocols;
  
  let updated = 0;
  let errors = 0;
  
  for (const [key, config] of Object.entries(PROTOCOL_CONFIG)) {
    // 跳过未指定的协议
    if (targetProtocols.length > 0 && !targetProtocols.includes(key)) continue;
    
    // 跳过特殊协议
    if (SKIP_PROTOCOLS.includes(key)) {
      console.log(`⏭️  ${key}: 跳过（需手动更新）`);
      continue;
    }
    
    console.log(`📊 ${key}...`);
    
    const protocol = protocols[key];
    if (!protocol) {
      console.log(`  ❌ 协议不存在`);
      errors++;
      continue;
    }
    
    // 获取 Revenue
    const revenueData = await getDefillamaRevenue(config.defillamaSlug);
    if (!revenueData) {
      errors++;
      continue;
    }
    
    // 获取市值（CoinGecko + CMC 双源）
    const marketCap = await getMarketCap(config.coingeckoId, config.cmcSlug);
    if (!marketCap) {
      errors++;
      continue;
    }
    
    // 计算 TEV
    let tev365d;
    if (config.fixedTevUsd) {
      // 固定 TEV（如 Aave）
      tev365d = config.fixedTevUsd;
    } else if (config.tevRatio) {
      // 按比例计算
      tev365d = revenueData.revenue365d * config.tevRatio;
    } else {
      // 从现有 TEV Yield 反推
      const tevYield = protocol.tev_yield_percent || 0;
      tev365d = tevYield * marketCap / 100;
    }
    
    // 计算 TEV Yield
    const tevYield = marketCap > 0 ? (tev365d / marketCap * 100) : 0;
    
    // 更新数据
    if (!protocol.metrics) protocol.metrics = {};
    
    const oldMcap = protocol.market_cap_usd;
    const oldRevenue = protocol.metrics.trailing_365d_revenue_usd;
    const oldTevYield = protocol.tev_yield_percent;
    
    protocol.market_cap_usd = marketCap;
    protocol.metrics.current_market_cap_usd = marketCap;
    protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
    protocol.metrics.trailing_30d_revenue_usd = revenueData.revenue30d;
    protocol.metrics.trailing_365d_tev_usd = tev365d;
    protocol.metrics.trailing_30d_tev_usd = tev365d / 12;
    protocol.tev_yield_percent = Math.round(tevYield * 100) / 100;
    
    // 输出变化
    console.log(`  市值: $${(oldMcap/1e6).toFixed(1)}M → $${(marketCap/1e6).toFixed(1)}M`);
    console.log(`  Revenue: $${((oldRevenue||0)/1e6).toFixed(1)}M → $${(revenueData.revenue365d/1e6).toFixed(1)}M`);
    console.log(`  TEV Yield: ${oldTevYield||0}% → ${tevYield.toFixed(2)}%`);
    
    updated++;
    
    // CoinGecko 限流 - 增加间隔
    await new Promise(r => setTimeout(r, 3000));
  }
  
  // 写入文件
  if (!dryRun && updated > 0) {
    allData.generated_at = new Date().toISOString();
    fs.writeFileSync(DATA_FILE, JSON.stringify(allData, null, 2));
    console.log(`\n✅ 已更新 ${updated} 个协议`);
  } else if (dryRun) {
    console.log(`\n🔍 预览完成，${updated} 个协议将被更新`);
  }
  
  if (errors > 0) {
    console.log(`⚠️ ${errors} 个错误`);
  }
}

main().catch(console.error);
