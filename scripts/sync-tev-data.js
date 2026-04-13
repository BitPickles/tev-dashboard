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
    tevRatio: null,  // 特殊：固定年度回购预算
    fixedTevUsd: 30000000,
    note: '年度回购 $30M (2026-03 治理投票从 $50M 下调, 99.37% 通过)'
  },
  curve: {
    defillamaSlug: 'curve-dex',
    coingeckoId: 'curve-dao-token',
    cmcSlug: 'curve-dao-token',
    tevRatio: 0.45,
    note: '50% fees → veCRV, 但 10% 归 Treasury (2025-06 治理), 实际 ~45% 到持有人'
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
    tevRatio: 0.25,
    note: '25% 协议收入回购 ETHFI → sETHFI (DAO Proposal #11, 正式治理通过)'
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
    tevRatio: 0.27,
    note: '27% 费用回购分配 (V2), staking 奖励暂停至 GMX>$90 后恢复'
  },
  maple: { 
    defillamaSlug: 'maple', 
    coingeckoId: 'maple',
    cmcSlug: 'maple-finance',
    tevRatio: 0.25,
    note: '25% 协议收入 → SSF 回购 SYRUP (MIP-019 通过, MIP-020 延续至 H1 2026)'
  },
  pancakeswap: { 
    defillamaSlug: 'pancakeswap', 
    coingeckoId: 'pancakeswap-token',
    cmcSlug: 'pancakeswap',
    tevRatio: 0.15,
    note: '15% 收入用于 CAKE 销毁 (veCAKE 已于 2025-04-23 停止, Tokenomics 3.0 转为 100% burn 模式)'
  },
  pendle: {
    defillamaSlug: 'pendle',
    coingeckoId: 'pendle',
    cmcSlug: 'pendle',
    tevRatio: 0.8,
    note: '80% 协议收入回购 → sPENDLE (2026-01 从 vePENDLE 迁移到 sPENDLE, 比例不变)'
  },
  sky: {
    defillamaSlug: 'sky',
    coingeckoId: 'maker',
    cmcSlug: 'sky',
    tevRatio: null,
    fixedTevUsd: 13724000,  // $37,600/天 × 365 = $13.724M (2026-03 治理大幅下调, 原 $30万/天)
    note: 'Smart Burn Engine 日回购 $37,600 (2026-03 治理投票下调 87.5%)'
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
  justlend: {
    defillamaSlug: 'justlend',
    coingeckoId: 'just',
    cmcSlug: 'justlend',
    tevRatio: 0.30,
    note: '30% 平台收入回购烧毁 JST (2025-10 治理通过, $41.42M 储备至 Q4 2026)'
  },
  jito: {
    defillamaSlug: 'jito',
    coingeckoId: 'jito-governance-token',
    cmcSlug: 'jito',
    tevRatio: 0,
    note: 'MEV 收益归 JitoSOL, JTO 纯治理'
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
    const sumSlice = (n) => chart.slice(-n).reduce((s, d) => s + (d[1] || 0), 0);
    return {
      revenue7d:   chart.length >= 7   ? sumSlice(7)   : null,
      revenue30d:  chart.length >= 7   ? sumSlice(30)  : null,
      revenue90d:  chart.length >= 30  ? sumSlice(90)  : null,
      revenue365d: sumSlice(365),
      chartLength: chart.length,
    };
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
    
    // 计算多维度年化 TEV Yield
    const calcYield = (revenue, days) => {
      if (revenue == null || !marketCap) return null;
      const annualized = revenue * (365 / days);
      const tev = config.fixedTevUsd ? config.fixedTevUsd : annualized * (config.tevRatio || 0);
      return Math.round(tev / marketCap * 10000) / 100;
    };

    const tevYield = marketCap > 0 ? (tev365d / marketCap * 100) : 0;
    const tevYield7d  = config.fixedTevUsd ? tevYield : calcYield(revenueData.revenue7d, 7);
    const tevYield30d = config.fixedTevUsd ? tevYield : calcYield(revenueData.revenue30d, 30);
    const tevYield90d = config.fixedTevUsd ? tevYield : calcYield(revenueData.revenue90d, 90);

    // 更新数据
    if (!protocol.metrics) protocol.metrics = {};

    const oldMcap = protocol.market_cap_usd;
    const oldRevenue = protocol.metrics.trailing_365d_revenue_usd;
    const oldTevYield = protocol.tev_yield_percent;

    protocol.market_cap_usd = marketCap;
    protocol.metrics.current_market_cap_usd = marketCap;
    protocol.metrics.trailing_7d_revenue_usd = revenueData.revenue7d;
    protocol.metrics.trailing_30d_revenue_usd = revenueData.revenue30d;
    protocol.metrics.trailing_90d_revenue_usd = revenueData.revenue90d;
    protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
    protocol.metrics.trailing_365d_tev_usd = tev365d;
    protocol.metrics.trailing_30d_tev_usd = tev365d / 12;
    protocol.metrics.tev_yield_7d_ann = tevYield7d;
    protocol.metrics.tev_yield_30d_ann = tevYield30d;
    protocol.metrics.tev_yield_90d_ann = tevYield90d;
    protocol.tev_yield_percent = Math.round(tevYield * 100) / 100;

    // 多维度年化 Earning Yield = annualized revenue / market_cap
    const calcEarningYield = (revenue, days) => {
      if (revenue == null || !marketCap) return null;
      return Math.round(revenue * (365 / days) / marketCap * 10000) / 100;
    };
    protocol.metrics.earning_yield_7d_ann = calcEarningYield(revenueData.revenue7d, 7);
    protocol.metrics.earning_yield_30d_ann = calcEarningYield(revenueData.revenue30d, 30);
    protocol.metrics.earning_yield_90d_ann = calcEarningYield(revenueData.revenue90d, 90);
    protocol.earning_yield_percent = calcEarningYield(revenueData.revenue365d, 365) || protocol.earning_yield_percent;
    
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
