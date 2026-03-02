#!/usr/bin/env node
/**
 * sync-tev-data.js - TEV 数据自动同步脚本
 * 
 * 功能：
 * 1. 从 DefiLlama 获取 Revenue 数据
 * 2. 从 CMC 获取市值数据（CoinGecko 备用）
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
const { execSync } = require('child_process');

// CMC 数据更新脚本路径
const CMC_UPDATE_SCRIPT = '/Users/aibot/.openclaw/workspace-researcher/scripts/update_cmc_daily.py';
const BTCD_SYNC_SCRIPT = path.join(__dirname, 'sync-btcd.py');

// 协议配置：DefiLlama slug, CoinGecko id, CMC slug, tevRatio
const PROTOCOL_CONFIG = {
  aave: { 
    defillamaSlug: 'aave', 
    coingeckoId: 'aave',
    cmcSlug: 'aave',
    tevRatio: null,  // 特殊：固定回购 + holdersRevenue
    fixedTevUsd: 50000000,
    addHoldersRevenue: true,  // 额外加上 DefiLlama holdersRevenue（Safety Module 质押奖励）
    note: '年度回购 $50M + Safety Module 质押奖励'
  },
  curve: { 
    defillamaSlug: 'curve-dex', 
    coingeckoId: 'curve-dao-token',
    cmcSlug: 'curve-dao-token',
    tevRatio: null,
    useHoldersRevenue: true,
    note: 'veCRV 分红，直接用 DefiLlama holdersRevenue'
  },
  dydx: { 
    defillamaSlug: 'dydx', 
    coingeckoId: 'dydx-chain',
    cmcSlug: 'dydx-chain',
    tevRatio: 0.90,
    note: '90% TEV (75% 回购 + 15% 质押)'
  },
  etherfi: { 
    defillamaSlug: 'ether.fi', 
    coingeckoId: 'ether-fi',
    cmcSlug: 'ether-fi',
    tevRatio: null,  // 从 TEV Yield 反推
    note: '提现收入回购'
  },
  fluid: {
    defillamaSlug: 'fluid',
    coingeckoId: 'fluid',
    cmcSlug: 'instadapp',
    tevRatio: 0.35,
    note: '35% Revenue 用于 Treasury 回购'
  },
  gmx: { 
    defillamaSlug: 'gmx', 
    coingeckoId: 'gmx',
    cmcSlug: 'gmx',
    tevRatio: null,
    useHoldersRevenue: true,
    note: '27% 平台总费用分红，直接用 DefiLlama holdersRevenue'
  },
  maple: { 
    defillamaSlug: 'maple', 
    coingeckoId: 'maple',
    cmcSlug: 'maple-finance',
    tevRatio: 0.25,
    note: '25% 协议收入回购 SYRUP (MIP-018)'
  },
  pancakeswap: { 
    defillamaSlug: 'pancakeswap', 
    coingeckoId: 'pancakeswap-token',
    cmcSlug: 'pancakeswap',
    tevRatio: null,
    useHoldersRevenue: true,
    note: 'Tokenomics 3.0 回购销毁，直接用 DefiLlama holdersRevenue'
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
    cmcSlug: 'sky',
    tevRatio: 0.5,
    note: '50% Smart Burn Engine 回购销毁'
  },
  // 以下协议无 TEV (tevStatus=none)，仅获取市值
  compound: {
    defillamaSlug: 'compound-v3',
    coingeckoId: 'compound-governance-token',
    cmcSlug: 'compound',
    tevRatio: 0,
    note: '纯治理代币'
  },
  eigenlayer: {
    defillamaSlug: 'eigenlayer',
    coingeckoId: 'eigenlayer',
    cmcSlug: 'eigenlayer',
    tevRatio: 0,
    note: '纯治理代币'
  },
  ethena: {
    defillamaSlug: 'ethena',
    coingeckoId: 'ethena',
    cmcSlug: 'ethena',
    tevRatio: 0,
    note: '纯治理代币'
  },
  jito: {
    defillamaSlug: 'jito',
    coingeckoId: 'jito-governance-token',
    cmcSlug: 'jito',
    tevRatio: 0,
    note: '纯治理代币'
  },
  kamino: {
    defillamaSlug: 'kamino',
    coingeckoId: 'kamino',
    cmcSlug: 'kamino-finance',
    tevRatio: 0,
    note: '纯治理代币'
  },
  lido: {
    defillamaSlug: 'lido',
    coingeckoId: 'lido-dao',
    cmcSlug: 'lido-dao',
    tevRatio: 0,
    note: '纯治理代币'
  },
  morpho: {
    defillamaSlug: 'morpho',
    coingeckoId: 'morpho',
    cmcSlug: 'morpho',
    tevRatio: 0,
    note: '纯治理代币'
  },
  spark: {
    defillamaSlug: 'spark',
    coingeckoId: 'spark',
    cmcSlug: 'spark',
    tevRatio: 0,
    note: '收入归 Sky DAO'
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

// 获取 DefiLlama HoldersRevenue（质押奖励/分红等）
async function getDefillamaHoldersRevenue(slug) {
  try {
    const data = await fetchJson(`https://api.llama.fi/summary/fees/${slug}?dataType=dailyHoldersRevenue`);
    const chart = data.totalDataChart || [];
    const last365 = chart.slice(-365);
    const total365 = last365.reduce((sum, d) => sum + (d[1] || 0), 0);
    const total30 = chart.slice(-30).reduce((sum, d) => sum + (d[1] || 0), 0);
    return { holdersRevenue365d: total365, holdersRevenue30d: total30 };
  } catch (e) {
    console.warn(`  ⚠️ DefiLlama holdersRevenue ${slug}: ${e.message}`);
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

// 获取 CMC 市值（主数据源）
async function getCmcMarketCap(slug) {
  try {
    // 使用 CMC 公开 API
    const data = await fetchJson(`https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?slug=${slug}`);
    const mcap = data?.data?.statistics?.marketCap || 0;
    if (mcap > 0) {
      return mcap;
    }
  } catch (e) {
    console.warn(`  ⚠️ CMC ${slug}: ${e.message}`);
  }
  return null;
}

// 获取市值（CMC 优先，CoinGecko 备用）
async function getMarketCap(coingeckoId, cmcSlug) {
  // 先尝试 CMC
  if (cmcSlug) {
    let mcap = await getCmcMarketCap(cmcSlug);
    if (mcap && mcap > 0) return mcap;
  }
  
  // CMC 失败，尝试 CoinGecko
  console.log(`  → 切换到 CoinGecko...`);
  let mcap = await getCoingeckoMarketCap(coingeckoId);
  if (mcap && mcap > 0) return mcap;
  
  return null;
}

// 更新 CMC 数据并同步 BTC.D
function updateCmcAndBtcd() {
  console.log('📈 更新 CMC 市值数据...');
  try {
    // 更新 CMC CSV
    if (fs.existsSync(CMC_UPDATE_SCRIPT)) {
      const output = execSync(`python3 "${CMC_UPDATE_SCRIPT}"`, {
        encoding: 'utf8',
        timeout: 60000
      });
      const match = output.match(/Added (\d+) new records/);
      if (match && match[1] !== '0') {
        console.log(`  ✅ CMC: +${match[1]} 条数据`);
      } else {
        console.log(`  ✅ CMC: 已是最新`);
      }
    }
    
    // 同步 BTC.D
    if (fs.existsSync(BTCD_SYNC_SCRIPT)) {
      const output = execSync(`python3 "${BTCD_SYNC_SCRIPT}"`, {
        encoding: 'utf8',
        timeout: 30000,
        cwd: __dirname
      });
      const match = output.match(/最新: ([\d-]+), BTC\.D: ([\d.]+)%/);
      if (match) {
        console.log(`  ✅ BTC.D: ${match[1]} ${match[2]}%`);
      } else if (output.includes('没有新数据')) {
        console.log(`  ✅ BTC.D: 已是最新`);
      }
    }
  } catch (e) {
    console.log(`  ⚠️ CMC/BTC.D 更新失败: ${e.message}`);
  }
  console.log('');
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const targetProtocols = args.filter(a => !a.startsWith('--'));
  
  console.log('=== TEV 数据同步 ===\n');
  if (dryRun) console.log('🔍 预览模式（不写入）\n');
  
  // 先更新 CMC/BTC.D（如果是完整同步）
  if (!dryRun && targetProtocols.length === 0) {
    updateCmcAndBtcd();
  }
  
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
    
    // 获取 holdersRevenue（如需要）
    let holdersRevenueData = null;
    if (config.addHoldersRevenue || config.useHoldersRevenue) {
      holdersRevenueData = await getDefillamaHoldersRevenue(config.defillamaSlug);
      if (holdersRevenueData) {
        console.log(`  HoldersRevenue 365d: $${(holdersRevenueData.holdersRevenue365d/1e6).toFixed(2)}M`);
      }
    }
    
    // 计算 TEV
    let tev365d;
    if (config.fixedTevUsd) {
      // 固定 TEV + holdersRevenue（如 Aave: $50M 回购 + 质押奖励）
      tev365d = config.fixedTevUsd;
      if (config.addHoldersRevenue && holdersRevenueData) {
        tev365d += holdersRevenueData.holdersRevenue365d;
      }
    } else if (config.useHoldersRevenue && holdersRevenueData) {
      // 直接使用 DefiLlama holdersRevenue 作为 TEV
      tev365d = holdersRevenueData.holdersRevenue365d;
      console.log(`  TEV = holdersRevenue: ${(tev365d/1e6).toFixed(2)}M`);
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
    if (holdersRevenueData) {
      protocol.metrics.trailing_365d_holders_revenue_usd = holdersRevenueData.holdersRevenue365d;
      protocol.metrics.trailing_30d_holders_revenue_usd = holdersRevenueData.holdersRevenue30d;
    }
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
