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
  // SKIP_PROTOCOLS: 市值/年度TEV由独立脚本维护，但 DefiLlama 收入用于多维度 yield 计算
  aster: {
    defillamaSlug: null,  // DefiLlama 无可用数据
    coingeckoId: 'aster-2',
    cmcSlug: 'aster',
    tevRatio: 0.7,
    note: '70% 交易费回购销毁 (独立链上追踪)'
  },
  bnb: {
    defillamaSlug: 'bsc',
    coingeckoId: 'binancecoin',
    cmcSlug: 'bnb',
    tevRatio: 0,
    note: 'Auto-Burn + BEP-95 + StakeHub (独立链上追踪)'
  },
  hype: {
    defillamaSlug: 'hyperliquid',
    coingeckoId: 'hyperliquid',
    cmcSlug: 'hyperliquid',
    tevRatio: 1.0,
    note: '100% Assistance Fund 回购烧毁 (独立追踪)'
  },
  uniswap: {
    defillamaSlug: 'uniswap',
    coingeckoId: 'uniswap',
    cmcSlug: 'uniswap',
    tevRatio: 1.0,
    note: '100% 协议费 Firepit 烧毁 + Unichain (独立链上追踪)'
  },
};

// 不更新市值/年度TEV的协议（有独立数据源），但仍拉 DefiLlama 收入算多维度 yield
const SKIP_PROTOCOLS = ['aster', 'hype', 'bnb', 'uniswap', 'bgb', 'okb'];

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

// 通用 DefiLlama fees/revenue/holdersRevenue 拉取
async function getDefillamaFees(slug, dataType) {
  try {
    const data = await fetchJson(`https://api.llama.fi/summary/fees/${slug}?dataType=${dataType}`);
    const chart = data.totalDataChart || [];
    const sumSlice = (n) => chart.slice(-n).reduce((s, d) => s + (d[1] || 0), 0);
    return {
      sum7d:   sumSlice(7),
      sum30d:  sumSlice(30),
      sum90d:  sumSlice(90),
      sum365d: sumSlice(365),
      chartLength: chart.length,
    };
  } catch (e) {
    console.warn(`  ⚠️ DefiLlama ${slug}/${dataType}: ${e.message}`);
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
    
    // BNB 专属计算：Auto-Burn（按窗口年化）+ asBNB 固定 APY
    if (key === 'bnb') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 bnb... (专属 TEV 计算)`);
      if (!protocol.metrics) protocol.metrics = {};
      const marketCap = protocol.market_cap_usd || 0;
      const bnbPrice = marketCap / 136357344;  // circulating supply ~136.36M

      // 读取烧毁历史
      const burnHistPath = path.join(__dirname, '../data/protocols/bnb/burn-history.json');
      let burnHist = { quarterly_burns: [], asbnb_apy_percent: 6.87, bep95_weekly_bnb: 720.64 };
      try { burnHist = JSON.parse(fs.readFileSync(burnHistPath, 'utf8')); } catch {}

      // 读取 BEP-95 日时间序列（Dune seed + 后续累积）
      const bep95HistPath = path.join(__dirname, '../data/protocols/bnb/bep95-history.json');
      let bep95Hist = { daily: [] };
      try { bep95Hist = JSON.parse(fs.readFileSync(bep95HistPath, 'utf8')); } catch {}
      const bep95Daily = bep95Hist.daily || [];

      const asbnbApy = burnHist.asbnb_apy_percent || 6.87;
      const burns = burnHist.quarterly_burns || [];

      // BEP-95 按窗口从日时间序列求和（单位：BNB）
      const sumBep95 = (days) => bep95Daily.slice(-days).reduce((s, r) => s + (r.bnb || 0), 0);
      const bep95_7d_bnb   = sumBep95(7);
      const bep95_30d_bnb  = sumBep95(30);
      const bep95_90d_bnb  = sumBep95(90);
      const bep95_365d_bnb = sumBep95(365);
      // 年化 USD（用当前价）
      const bep95_7d_usd   = bep95_7d_bnb   * (365 / 7)   * bnbPrice;
      const bep95_30d_usd  = bep95_30d_bnb  * (365 / 30)  * bnbPrice;
      const bep95_90d_usd  = bep95_90d_bnb  * (365 / 90)  * bnbPrice;
      const bep95_365d_usd = bep95_365d_bnb * bnbPrice;  // 已是 365 天累计

      // Auto-Burn 口径：
      //   - 7d/30d/90d：近 4 季 burn 的 usd_value 累加（每次 burn 公告时的历史 USD）
      //   - 365d：近 4 季 burn BNB 合计 × 当前价（按当前市价重估）
      const recent4Burns = burns.slice(-4);
      const recent4BurnBnb = recent4Burns.reduce((s, b) => s + (b.bnb_burned || 0), 0);
      const recent4BurnUsdHistorical = recent4Burns.reduce((s, b) => s + (b.usd_value || 0), 0);
      const recent4BurnUsdCurrent = recent4BurnBnb * bnbPrice;
      const lastBurn = burns[burns.length - 1] || { bnb_burned: 0, date: null };

      // 各周期 TEV Yield = (Auto-Burn USD + BEP-95 年化 USD) / 市值 + asBNB APY
      const calcYield = (autoBurnUsd, bep95Usd) => marketCap > 0
        ? Math.round((autoBurnUsd + bep95Usd) / marketCap * 10000) / 100
        : 0;

      const burnYield_7d   = calcYield(recent4BurnUsdHistorical, bep95_7d_usd);
      const burnYield_30d  = calcYield(recent4BurnUsdHistorical, bep95_30d_usd);
      const burnYield_90d  = calcYield(recent4BurnUsdHistorical, bep95_90d_usd);
      const burnYield_365d = calcYield(recent4BurnUsdCurrent,    bep95_365d_usd);

      const tevYield_7d   = Math.round((burnYield_7d   + asbnbApy) * 100) / 100;
      const tevYield_30d  = Math.round((burnYield_30d  + asbnbApy) * 100) / 100;
      const tevYield_90d  = Math.round((burnYield_90d  + asbnbApy) * 100) / 100;
      const tevYield_365d = Math.round((burnYield_365d + asbnbApy) * 100) / 100;

      protocol.metrics.tev_yield_7d_ann  = tevYield_7d;
      protocol.metrics.tev_yield_30d_ann = tevYield_30d;
      protocol.metrics.tev_yield_90d_ann = tevYield_90d;
      protocol.tev_yield_percent         = tevYield_365d;
      // BNB 无 fee 分润机制，tevRatio 不适用（前端渲染会显示 '—'）
      protocol.tevRatio = null;

      // Earning Yield = BEP-95（按窗口年化）+ asBNB APY
      // 各周期用对应窗口的 BEP-95 值，与 TEV Yield 的周期口径保持一致
      const bep95Yield = (usd) => marketCap > 0 ? usd / marketCap * 100 : 0;
      const ey_7d   = Math.round((bep95Yield(bep95_7d_usd)   + asbnbApy) * 100) / 100;
      const ey_30d  = Math.round((bep95Yield(bep95_30d_usd)  + asbnbApy) * 100) / 100;
      const ey_90d  = Math.round((bep95Yield(bep95_90d_usd)  + asbnbApy) * 100) / 100;
      const ey_365d = Math.round((bep95Yield(bep95_365d_usd) + asbnbApy) * 100) / 100;
      protocol.earning_yield_percent        = ey_365d;
      protocol.metrics.earning_yield_7d_ann  = ey_7d;
      protocol.metrics.earning_yield_30d_ann = ey_30d;
      protocol.metrics.earning_yield_90d_ann = ey_90d;

      // BNB 的 BEP-95 占 yield 比例极小 (~0.02%)，需用 3 位小数才能看出周期差异
      protocol.display_precision = 3;

      // 同步 validation 字段（各周期独立，反映 BEP-95 波动）
      if (!protocol.validation) protocol.validation = {};
      protocol.validation.method = 'Auto-Burn（短周期=近4季USD累加；365d=近4季BNB×当前价）+ BEP-95（按窗口从日时间序列计算）+ asBNB APY (Aster)';
      protocol.validation.asbnb_apy_percent = asbnbApy;
      protocol.validation.tev_yield_7d_percent   = tevYield_7d;
      protocol.validation.tev_yield_30d_percent  = tevYield_30d;
      protocol.validation.tev_yield_90d_percent  = tevYield_90d;
      protocol.validation.tev_yield_365d_percent = tevYield_365d;
      protocol.validation.bep95_7d_bnb   = Math.round(bep95_7d_bnb   * 100) / 100;
      protocol.validation.bep95_30d_bnb  = Math.round(bep95_30d_bnb  * 100) / 100;
      protocol.validation.bep95_90d_bnb  = Math.round(bep95_90d_bnb  * 100) / 100;
      protocol.validation.bep95_365d_bnb = Math.round(bep95_365d_bnb * 100) / 100;
      protocol.validation.bep95_data_days = bep95Daily.length;
      protocol.validation.bep95_data_range = bep95Daily.length
        ? { start: bep95Daily[0].date, end: bep95Daily[bep95Daily.length - 1].date }
        : null;
      protocol.validation.last_burn_bnb = lastBurn.bnb_burned || 0;
      protocol.validation.last_burn_date = lastBurn.date || null;
      protocol.validation.recent_4q_burn_bnb = Math.round(recent4BurnBnb);
      protocol.validation.recent_4q_burn_usd_historical = Math.round(recent4BurnUsdHistorical);
      protocol.validation.recent_4q_burn_usd_current = Math.round(recent4BurnUsdCurrent);
      protocol.validation.bnb_price_usd = Math.round(bnbPrice * 100) / 100;
      protocol.validation.market_cap_usd = marketCap;
      protocol.validation.burn_source = `Auto-Burn 近4季 ${Math.round(recent4BurnBnb).toLocaleString()} BNB (历史$${(recent4BurnUsdHistorical/1e9).toFixed(2)}B / 当前价$${(recent4BurnUsdCurrent/1e9).toFixed(2)}B); BEP-95 ${bep95Daily.length}天数据, 7/30/90/365d = ${Math.round(bep95_7d_bnb)}/${Math.round(bep95_30d_bnb)}/${Math.round(bep95_90d_bnb)}/${Math.round(bep95_365d_bnb)} BNB`;

      console.log(`  BNB price: $${bnbPrice.toFixed(0)}`);
      console.log(`  BEP-95 series: ${bep95Daily.length} days (${bep95Daily[0]?.date} → ${bep95Daily[bep95Daily.length-1]?.date})`);
      console.log(`  BEP-95 窗口 BNB: 7d=${Math.round(bep95_7d_bnb)} / 30d=${Math.round(bep95_30d_bnb)} / 90d=${Math.round(bep95_90d_bnb)} / 365d=${Math.round(bep95_365d_bnb)}`);
      console.log(`  Auto-Burn USD: 近4季历史累加=$${(recent4BurnUsdHistorical/1e9).toFixed(2)}B / 当前价重估=$${(recent4BurnUsdCurrent/1e9).toFixed(2)}B`);
      console.log(`  asBNB APY: ${asbnbApy}%`);
      console.log(`  TEV Yield: 7d=${tevYield_7d}% 30d=${tevYield_30d}% 90d=${tevYield_90d}% 365d=${tevYield_365d}%`);
      updated++;
      continue;
    }

    // Aave 专属：TEV = 固定年度 Buyback 预算 + Safety Module holders revenue（动态，按窗口）
    // 决策（Boss 2026-04-22 定）：
    //   1. Buyback $30M/年（2026-03 治理从 $50M 下调）——算 TEV，但是 treasury-accumulated 非真 burn
    //   2. Safety Module（Umbrella）按 DefiLlama dailyHoldersRevenue 窗口累加年化（方案 A）
    //   3. 最近 50+ 天 SM = $0 可能是 Umbrella 迁移期，暂信 DefiLlama
    if (key === 'aave') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 aave... (双源：固定 Buyback $30M + 动态 Safety Module holdersRevenue)`);
      const marketCap = protocol.market_cap_usd || 0;
      const fixedBuybackUsd = config.fixedTevUsd || 30_000_000;  // 2026-03 治理后 $30M

      const [holdersData, revenueData] = await Promise.all([
        getDefillamaFees('aave', 'dailyHoldersRevenue'),
        getDefillamaRevenue('aave'),
      ]);

      if (!protocol.metrics) protocol.metrics = {};

      // TEV = buyback + SM annualized，各周期独立
      const calcTev = (smSum, days) => {
        if (!marketCap) return 0;
        const ann = days >= 365 ? 1 : (365 / days);
        const smUsd = (smSum || 0) * ann;
        return Math.round((fixedBuybackUsd + smUsd) / marketCap * 10000) / 100;
      };
      const calcEarn = (revSum, days) => {
        if (!marketCap) return 0;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round((revSum || 0) * ann / marketCap * 10000) / 100;
      };

      if (holdersData && revenueData) {
        const tev_7d   = calcTev(holdersData.sum7d,   7);
        const tev_30d  = calcTev(holdersData.sum30d,  30);
        const tev_90d  = calcTev(holdersData.sum90d,  90);
        const tev_365d = calcTev(holdersData.sum365d, 365);
        const ey_7d   = calcEarn(revenueData.revenue7d,   7);
        const ey_30d  = calcEarn(revenueData.revenue30d,  30);
        const ey_90d  = calcEarn(revenueData.revenue90d,  90);
        const ey_365d = calcEarn(revenueData.revenue365d, 365);

        protocol.metrics.tev_yield_7d_ann  = tev_7d;
        protocol.metrics.tev_yield_30d_ann = tev_30d;
        protocol.metrics.tev_yield_90d_ann = tev_90d;
        protocol.tev_yield_percent         = tev_365d;
        protocol.metrics.earning_yield_7d_ann  = ey_7d;
        protocol.metrics.earning_yield_30d_ann = ey_30d;
        protocol.metrics.earning_yield_90d_ann = ey_90d;
        protocol.earning_yield_percent         = ey_365d;
        protocol.metrics.trailing_7d_revenue_usd   = revenueData.revenue7d;
        protocol.metrics.trailing_30d_revenue_usd  = revenueData.revenue30d;
        protocol.metrics.trailing_90d_revenue_usd  = revenueData.revenue90d;
        protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;

        // tevRatio 按周期
        const calcRatio = (t, e) => (e > 0 ? Math.round(t / e * 10000) / 10000 : null);
        protocol.tevRatio_7d   = calcRatio(tev_7d,   ey_7d);
        protocol.tevRatio_30d  = calcRatio(tev_30d,  ey_30d);
        protocol.tevRatio_90d  = calcRatio(tev_90d,  ey_90d);
        protocol.tevRatio_365d = calcRatio(tev_365d, ey_365d);
        protocol.tevRatio = protocol.tevRatio_365d;

        protocol.validation = protocol.validation || {};
        protocol.validation.method = 'TEV = 固定 Buyback $30M/年（2026-03 治理）+ Safety Module (Umbrella) DefiLlama dailyHoldersRevenue 按窗口年化';
        protocol.validation.fixed_buyback_usd_annual = fixedBuybackUsd;
        protocol.validation.sm_7d_usd   = Math.round(holdersData.sum7d);
        protocol.validation.sm_30d_usd  = Math.round(holdersData.sum30d);
        protocol.validation.sm_90d_usd  = Math.round(holdersData.sum90d);
        protocol.validation.sm_365d_usd = Math.round(holdersData.sum365d);
        protocol.validation.caveats = [
          'Buyback 是 treasury-accumulated，不是真 burn（买入 AAVE → Ecosystem Reserve，治理可 redistribute）',
          'Safety Module 分发是脉冲式（每 1-2 周一次大包），短周期窗口可能为 0',
          '最近 50+ 天 SM = $0，可能 Umbrella 新合约 DefiLlama 追踪滞后，或真的暂停分发',
          '链上 AAVE @ 0xdead 365d = 0.0001 AAVE（没有真销毁，符合 treasury buyback 模式）',
        ];

        console.log(`  marketCap: $${(marketCap/1e9).toFixed(2)}B, 固定 Buyback: $${fixedBuybackUsd/1e6}M`);
        console.log(`  SM holdersRevenue: 7d=$${(holdersData.sum7d/1e6).toFixed(2)}M 30d=$${(holdersData.sum30d/1e6).toFixed(2)}M 90d=$${(holdersData.sum90d/1e6).toFixed(2)}M 365d=$${(holdersData.sum365d/1e6).toFixed(2)}M`);
        console.log(`  Revenue:           7d=$${(revenueData.revenue7d/1e6).toFixed(2)}M 30d=$${(revenueData.revenue30d/1e6).toFixed(2)}M 90d=$${(revenueData.revenue90d/1e6).toFixed(2)}M 365d=$${(revenueData.revenue365d/1e6).toFixed(2)}M`);
        console.log(`  TEV Yield:     7d=${tev_7d}% 30d=${tev_30d}% 90d=${tev_90d}% 365d=${tev_365d}%`);
        console.log(`  Earning:       7d=${ey_7d}% 30d=${ey_30d}% 90d=${ey_90d}% 365d=${ey_365d}%`);
        console.log(`  tevRatio (各周期): 7d=${protocol.tevRatio_7d} 30d=${protocol.tevRatio_30d} 90d=${protocol.tevRatio_90d} 365d=${protocol.tevRatio_365d}`);
      }
      updated++;
      continue;
    }

    // Sky 专属：TEV 用 DefiLlama dailyHoldersRevenue（Splitter 的 burn 部分，即 SBE 真实支出）
    // 原代码使用 fixedTevUsd: $13.724M（治理公告值），但实际每日波动，应动态拉取
    // Splitter 的 farm 部分（给 SKY stakers）不算 TEV（新铸造的 SKY + USDS yield，非市场回购）
    if (key === 'sky') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 sky... (DefiLlama dailyHoldersRevenue 口径)`);
      const marketCap = protocol.market_cap_usd || 0;
      if (!protocol.metrics) protocol.metrics = {};

      // 拉 holdersRevenue（TEV）和 revenue（Earning）两个口径
      const [holdersData, revenueData] = await Promise.all([
        getDefillamaFees('sky', 'dailyHoldersRevenue'),
        getDefillamaRevenue('sky'),
      ]);

      const calcY = (sum, days) => {
        if (sum == null || !marketCap) return null;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round(sum * ann / marketCap * 10000) / 100;
      };

      if (holdersData) {
        protocol.metrics.tev_yield_7d_ann  = calcY(holdersData.sum7d,   7);
        protocol.metrics.tev_yield_30d_ann = calcY(holdersData.sum30d,  30);
        protocol.metrics.tev_yield_90d_ann = calcY(holdersData.sum90d,  90);
        protocol.tev_yield_percent         = calcY(holdersData.sum365d, 365);
      }
      if (revenueData) {
        protocol.metrics.trailing_7d_revenue_usd   = revenueData.revenue7d;
        protocol.metrics.trailing_30d_revenue_usd  = revenueData.revenue30d;
        protocol.metrics.trailing_90d_revenue_usd  = revenueData.revenue90d;
        protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
        protocol.metrics.earning_yield_7d_ann  = calcY(revenueData.revenue7d,  7);
        protocol.metrics.earning_yield_30d_ann = calcY(revenueData.revenue30d, 30);
        protocol.metrics.earning_yield_90d_ann = calcY(revenueData.revenue90d, 90);
        protocol.earning_yield_percent         = calcY(revenueData.revenue365d, 365);
      }

      // tevRatio 动态反映 Splitter 的 burn 比例 —— 按各周期独立算
      if (holdersData && revenueData) {
        const calcRatio = (h, r) => (r > 0 && h != null ? Math.round(h / r * 10000) / 10000 : null);
        protocol.tevRatio_7d   = calcRatio(holdersData.sum7d,   revenueData.revenue7d);
        protocol.tevRatio_30d  = calcRatio(holdersData.sum30d,  revenueData.revenue30d);
        protocol.tevRatio_90d  = calcRatio(holdersData.sum90d,  revenueData.revenue90d);
        protocol.tevRatio_365d = calcRatio(holdersData.sum365d, revenueData.revenue365d);
        protocol.tevRatio = protocol.tevRatio_365d;  // 顶层保持 365d
      }

      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'DefiLlama dailyHoldersRevenue = Splitter burn (SBE 真实支出) / dailyRevenue = 协议总归属';
      protocol.validation.tev_source = 'DefiLlama dailyHoldersRevenue (slug=sky)';
      protocol.validation.earning_source = 'DefiLlama dailyRevenue (slug=sky)';
      if (holdersData) {
        protocol.validation.burn_7d_usd   = Math.round(holdersData.sum7d);
        protocol.validation.burn_30d_usd  = Math.round(holdersData.sum30d);
        protocol.validation.burn_90d_usd  = Math.round(holdersData.sum90d);
        protocol.validation.burn_365d_usd = Math.round(holdersData.sum365d);
      }
      if (holdersData && holdersData.sum30d) {
        protocol.validation.burn_daily_avg_30d_usd = Math.round(holdersData.sum30d / 30);
      }
      protocol.validation.note = '2026-03 Splitter burn 参数大幅下调（日均从 ~$300k 降至 ~$37.6k，-87.5%）。365d 窗口包含下调前高峰，所以短周期 < 365d。';

      console.log(`  marketCap: $${(marketCap/1e9).toFixed(2)}B`);
      if (holdersData) console.log(`  HoldersRevenue: 7d=$${(holdersData.sum7d/1e6).toFixed(2)}M 30d=$${(holdersData.sum30d/1e6).toFixed(2)}M 90d=$${(holdersData.sum90d/1e6).toFixed(2)}M 365d=$${(holdersData.sum365d/1e6).toFixed(2)}M`);
      if (revenueData) console.log(`  Revenue:        7d=$${(revenueData.revenue7d/1e6).toFixed(2)}M 30d=$${(revenueData.revenue30d/1e6).toFixed(2)}M 90d=$${(revenueData.revenue90d/1e6).toFixed(2)}M 365d=$${(revenueData.revenue365d/1e6).toFixed(2)}M`);
      console.log(`  TEV Yield: 7d=${protocol.metrics.tev_yield_7d_ann}% 30d=${protocol.metrics.tev_yield_30d_ann}% 90d=${protocol.metrics.tev_yield_90d_ann}% 365d=${protocol.tev_yield_percent}%`);
      console.log(`  Earning:   7d=${protocol.metrics.earning_yield_7d_ann}% 30d=${protocol.metrics.earning_yield_30d_ann}% 90d=${protocol.metrics.earning_yield_90d_ann}% 365d=${protocol.earning_yield_percent}%`);
      console.log(`  tevRatio (dynamic): ${protocol.tevRatio}`);
      updated++;
      continue;
    }

    // Aster 专属：TEV = Stage5/6 buyback wallet 的 ASTER 累积 × 当前价（类似 Hyperliquid AF）
    // 数据源：data/aster-onchain.json（由 update-aster-tev.py 每日维护，Moralis API）
    if (key === 'aster') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 aster... (Stage5/6 buyback treasury 口径)`);
      const onchainPath = path.join(__dirname, '../data/aster-onchain.json');
      let onchain = [];
      try { onchain = JSON.parse(fs.readFileSync(onchainPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ aster-onchain.json 读取失败: ${e.message}`);
      }
      const marketCap = protocol.market_cap_usd || 0;
      const circulatingSupply = 2_460_000_000;  // Aster 流通量近似
      const asterPrice = marketCap > 0 ? marketCap / circulatingSupply : 0;

      // 按 N 天窗口汇总 ASTER inflow
      const today = new Date();
      const sumAster = (days) => {
        const cutoff = new Date(today.getTime() - days * 86400000).toISOString().slice(0, 10);
        return (onchain || []).filter(r => r.date > cutoff).reduce((s, r) => s + (r.aster || 0), 0);
      };
      const buy7d_aster   = sumAster(7);
      const buy30d_aster  = sumAster(30);
      const buy90d_aster  = sumAster(90);
      const buy365d_aster = sumAster(365);

      const calcYield = (aster_sum, days) => {
        if (!marketCap || !asterPrice) return 0;
        const usd = aster_sum * asterPrice;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round(usd * ann / marketCap * 10000) / 100;
      };
      const tev_7d   = calcYield(buy7d_aster,   7);
      const tev_30d  = calcYield(buy30d_aster,  30);
      const tev_90d  = calcYield(buy90d_aster,  90);
      const tev_365d = calcYield(buy365d_aster, 365);

      if (!protocol.metrics) protocol.metrics = {};
      protocol.metrics.tev_yield_7d_ann  = tev_7d;
      protocol.metrics.tev_yield_30d_ann = tev_30d;
      protocol.metrics.tev_yield_90d_ann = tev_90d;
      protocol.tev_yield_percent         = tev_365d;
      // Aster 的 TEV = Earning（100% 买回 → stage 合约，用 treasury buyback 口径，等同 100% 分润）
      protocol.metrics.earning_yield_7d_ann  = tev_7d;
      protocol.metrics.earning_yield_30d_ann = tev_30d;
      protocol.metrics.earning_yield_90d_ann = tev_90d;
      protocol.earning_yield_percent         = tev_365d;
      protocol.metrics.trailing_7d_revenue_usd   = Math.round(buy7d_aster * asterPrice);
      protocol.metrics.trailing_30d_revenue_usd  = Math.round(buy30d_aster * asterPrice);
      protocol.metrics.trailing_90d_revenue_usd  = Math.round(buy90d_aster * asterPrice);
      protocol.metrics.trailing_365d_revenue_usd = Math.round(buy365d_aster * asterPrice);

      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'A 口径：Stage5/6 buyback wallet 累积 ASTER × 当前价（treasury buyback，非真 burn）';
      protocol.validation.buy_7d_aster   = Math.round(buy7d_aster);
      protocol.validation.buy_30d_aster  = Math.round(buy30d_aster);
      protocol.validation.buy_90d_aster  = Math.round(buy90d_aster);
      protocol.validation.buy_365d_aster = Math.round(buy365d_aster);
      protocol.validation.aster_price_usd = Math.round(asterPrice * 10000) / 10000;
      protocol.validation.data_days = (onchain || []).length;
      protocol.validation.data_range = onchain && onchain.length
        ? { start: onchain[0].date, end: onchain[onchain.length - 1].date }
        : null;
      protocol.validation.caveats = [
        'Stage5/6 是 treasury buyback（wallet 持仓），部分 burn 部分给 community rewards，不全是真销毁',
        '2026-03-30 tokenomics 改革后新增 staking rewards（暂不计入 TEV）',
        'Moralis 免费 tier 可能滞后几天',
      ];

      console.log(`  ASTER price: $${asterPrice.toFixed(4)} (marketCap $${(marketCap/1e9).toFixed(2)}B ÷ ${(circulatingSupply/1e9).toFixed(2)}B supply)`);
      console.log(`  Buyback ASTER: 7d=${Math.round(buy7d_aster).toLocaleString()} / 30d=${Math.round(buy30d_aster).toLocaleString()} / 90d=${Math.round(buy90d_aster).toLocaleString()} / 365d=${Math.round(buy365d_aster).toLocaleString()}`);
      console.log(`  TEV Yield: 7d=${tev_7d}% 30d=${tev_30d}% 90d=${tev_90d}% 365d=${tev_365d}%`);
      updated++;
      continue;
    }

    // Uniswap 专属：TEV 只看链上 UNI 转入 0xdead（A 口径，Boss 2026-04-22 定）
    // 排除 >=10M UNI 的一次性治理事件（如 2025-12-27 Timelock 100M retroactive burn）
    if (key === 'uniswap') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 uniswap... (链上 0xdead burn 口径)`);
      const burnHistPath = path.join(__dirname, '../data/protocols/uniswap/burn-history.json');
      let burnHist = { daily: [], retro_events: [] };
      try { burnHist = JSON.parse(fs.readFileSync(burnHistPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ burn-history.json 读取失败: ${e.message}`);
      }
      const marketCap = protocol.market_cap_usd || 0;
      const circulatingSupply = 633561603;  // CoinGecko circulating，近似值，可后续改为动态
      const uniPrice = marketCap > 0 && circulatingSupply > 0 ? marketCap / circulatingSupply : 0;

      // 按 N 天窗口求和持续 burn（排除 retro）
      const today = new Date();
      const sumBurn = (days) => {
        const cutoff = new Date(today.getTime() - days * 86400000).toISOString().slice(0, 10);
        return (burnHist.daily || []).filter(r => r.date > cutoff).reduce((s, r) => s + (r.uni || 0), 0);
      };
      const burn7d_uni   = sumBurn(7);
      const burn30d_uni  = sumBurn(30);
      const burn90d_uni  = sumBurn(90);
      const burn365d_uni = sumBurn(365);

      const usd = (uni) => uni * uniPrice;
      const calcY = (usdVal, days) => {
        if (!marketCap) return 0;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round(usdVal * ann / marketCap * 10000) / 100;
      };
      const tev_7d   = calcY(usd(burn7d_uni),   7);
      const tev_30d  = calcY(usd(burn30d_uni),  30);
      const tev_90d  = calcY(usd(burn90d_uni),  90);
      const tev_365d = calcY(usd(burn365d_uni), 365);

      if (!protocol.metrics) protocol.metrics = {};
      protocol.metrics.tev_yield_7d_ann  = tev_7d;
      protocol.metrics.tev_yield_30d_ann = tev_30d;
      protocol.metrics.tev_yield_90d_ann = tev_90d;
      protocol.tev_yield_percent         = tev_365d;
      // Earning = TEV for uniswap (tevRatio=1.0，所有 burn 归 token holder)
      protocol.metrics.earning_yield_7d_ann  = tev_7d;
      protocol.metrics.earning_yield_30d_ann = tev_30d;
      protocol.metrics.earning_yield_90d_ann = tev_90d;
      protocol.earning_yield_percent         = tev_365d;
      // revenue 字段用 burn USD 填（反映 token holder 实得）
      protocol.metrics.trailing_7d_revenue_usd   = Math.round(usd(burn7d_uni));
      protocol.metrics.trailing_30d_revenue_usd  = Math.round(usd(burn30d_uni));
      protocol.metrics.trailing_90d_revenue_usd  = Math.round(usd(burn90d_uni));
      protocol.metrics.trailing_365d_revenue_usd = Math.round(usd(burn365d_uni));

      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'A 口径：365d UNI 转入 0xdead（链上）减去 >=10M UNI 一次性事件';
      protocol.validation.burn_7d_uni   = Math.round(burn7d_uni);
      protocol.validation.burn_30d_uni  = Math.round(burn30d_uni);
      protocol.validation.burn_90d_uni  = Math.round(burn90d_uni);
      protocol.validation.burn_365d_uni = Math.round(burn365d_uni);
      protocol.validation.retro_events_count = (burnHist.retro_events || []).length;
      protocol.validation.retro_total_uni = Math.round((burnHist.retro_events || []).reduce((s, r) => s + (r.amount || 0), 0));
      protocol.validation.uni_price_usd = Math.round(uniPrice * 100) / 100;
      protocol.validation.data_days = (burnHist.daily || []).length;
      protocol.validation.data_range = burnHist.daily && burnHist.daily.length
        ? { start: burnHist.daily[0].date, end: burnHist.daily[burnHist.daily.length-1].date }
        : null;

      console.log(`  UNI price: $${uniPrice.toFixed(2)} (marketCap $${(marketCap/1e9).toFixed(2)}B ÷ ${(circulatingSupply/1e6).toFixed(0)}M supply)`);
      console.log(`  Burn UNI: 7d=${Math.round(burn7d_uni).toLocaleString()} / 30d=${Math.round(burn30d_uni).toLocaleString()} / 90d=${Math.round(burn90d_uni).toLocaleString()} / 365d=${Math.round(burn365d_uni).toLocaleString()}`);
      console.log(`  Retro 排除: ${(burnHist.retro_events || []).length} 次, 共 ${Math.round((burnHist.retro_events || []).reduce((s, r) => s + (r.amount || 0), 0)/1e6)}M UNI`);
      console.log(`  TEV Yield: 7d=${tev_7d}% 30d=${tev_30d}% 90d=${tev_90d}% 365d=${tev_365d}%`);
      updated++;
      continue;
    }

    // 其他特殊协议：不更新市值和年度TEV，但拉 DefiLlama 收入计算多维度 yield
    if (SKIP_PROTOCOLS.includes(key)) {
      const protocol = protocols[key];
      if (!protocol) continue;
      if (!config.defillamaSlug) { console.log(`⏭️  ${key}: 跳过（无 DefiLlama slug）`); continue; }
      console.log(`📊 ${key}... (多维度 yield only)`);
      const revenueData = await getDefillamaRevenue(config.defillamaSlug);
      if (revenueData) {
        const marketCap = protocol.market_cap_usd || 0;
        if (!protocol.metrics) protocol.metrics = {};
        protocol.metrics.trailing_7d_revenue_usd = revenueData.revenue7d;
        protocol.metrics.trailing_30d_revenue_usd = revenueData.revenue30d;
        protocol.metrics.trailing_90d_revenue_usd = revenueData.revenue90d;
        protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
        // 多维度年化 TEV Yield（用现有 tevRatio 或从现有 yield 反推）
        const tevRatio = config.tevRatio || (marketCap > 0 && revenueData.revenue365d > 0 ? (protocol.tev_yield_percent / 100 * marketCap) / (revenueData.revenue365d * 365 / 365) / 1 : 0);
        const calcY = (rev, days) => {
          if (rev == null || !marketCap || !tevRatio) return null;
          // 365d 不需要年化（已是 365 天累计）
          const annFactor = days >= 365 ? 1 : (365 / days);
          return Math.round(rev * annFactor * tevRatio / marketCap * 10000) / 100;
        };
        const calcEY = (rev, days) => {
          if (rev == null || !marketCap) return null;
          const annFactor = days >= 365 ? 1 : (365 / days);
          return Math.round(rev * annFactor / marketCap * 10000) / 100;
        };
        protocol.metrics.tev_yield_7d_ann = calcY(revenueData.revenue7d, 7);
        protocol.metrics.tev_yield_30d_ann = calcY(revenueData.revenue30d, 30);
        protocol.metrics.tev_yield_90d_ann = calcY(revenueData.revenue90d, 90);
        protocol.metrics.earning_yield_7d_ann = calcEY(revenueData.revenue7d, 7);
        protocol.metrics.earning_yield_30d_ann = calcEY(revenueData.revenue30d, 30);
        protocol.metrics.earning_yield_90d_ann = calcEY(revenueData.revenue90d, 90);
        // 新增：365d 顶层字段（之前 SKIP 分支漏算，导致 365d yield 停留在手写值）
        const tev365 = calcY(revenueData.revenue365d, 365);
        const earning365 = calcEY(revenueData.revenue365d, 365);
        if (tev365 != null) protocol.tev_yield_percent = tev365;
        if (earning365 != null) protocol.earning_yield_percent = earning365;
        updated++;
        console.log(`  rev 7d=$${((revenueData.revenue7d||0)/1e6).toFixed(2)}M, 365d=$${((revenueData.revenue365d||0)/1e6).toFixed(2)}M`);
        console.log(`  yield 7d=${protocol.metrics.tev_yield_7d_ann}% 30d=${protocol.metrics.tev_yield_30d_ann}% 90d=${protocol.metrics.tev_yield_90d_ann}% 365d=${protocol.tev_yield_percent}%`);
      }
      await new Promise(r => setTimeout(r, 2000));
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
    // fixedTevUsd 协议：TEV Yield 各周期相同（预算固定），但 Earning Yield 仍反映收入波动
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

    // 同步回写每个协议的 config.json，保持首页与详情页数据一致
    for (const [pid, protocol] of Object.entries(allData.protocols)) {
      const configPath = path.join(__dirname, `../data/protocols/${pid}/config.json`);
      if (!fs.existsSync(configPath)) continue;
      try {
        const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        // 同步动态计算字段
        cfg.market_cap_usd = protocol.market_cap_usd;
        cfg.tev_yield_percent = protocol.tev_yield_percent;
        cfg.earning_yield_percent = protocol.earning_yield_percent;
        cfg.tevRatio = protocol.tevRatio;
        if (!cfg.tev_data) cfg.tev_data = {};
        cfg.tev_data.tev_yield_percent = protocol.tev_yield_percent;
        cfg.tev_data.market_cap_usd = protocol.market_cap_usd;
        cfg.tev_data.annual_tev_usd = (protocol.metrics || {}).trailing_365d_tev_usd;
        cfg.tev_data.calculation_date = new Date().toISOString().split('T')[0];
        // 同步 validation 到 tev_data.validation，避免详情页显示旧值
        if (protocol.validation) {
          cfg.tev_data.validation = { ...(cfg.tev_data.validation || {}), ...protocol.validation };
        }
        if (protocol.metrics) {
          cfg.metrics = { ...cfg.metrics, ...protocol.metrics };
        }
        fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2));
      } catch (e) {
        console.warn(`  ⚠️ 回写 ${pid}/config.json 失败: ${e.message}`);
      }
    }
    console.log(`📋 已同步 config.json`);
  } else if (dryRun) {
    console.log(`\n🔍 预览完成，${updated} 个协议将被更新`);
  }
  
  if (errors > 0) {
    console.log(`⚠️ ${errors} 个错误`);
  }
}

main().catch(console.error);
