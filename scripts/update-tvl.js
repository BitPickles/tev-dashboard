#!/usr/bin/env node
/**
 * 从 DefiLlama 获取 TVL 数据并更新到 config.json
 * 用法: node scripts/update-tvl.js
 */

const fs = require('fs');
const path = require('path');

const PROTOCOLS_DIR = path.join(__dirname, '../data/protocols');

// 协议 ID 映射 (本地目录名 -> DefiLlama protocol slug)
const DEFILLAMA_MAPPING = {
  'aave': 'aave',
  'aster': 'asterdex',
  'compound': 'compound-finance',
  'curve': 'curve-dex',
  'dydx': 'dydx',
  'eigenlayer': 'eigenlayer',
  'ethena': 'ethena',
  'etherfi': 'ether.fi',
  'gmx': 'gmx',
  'hype': 'hyperliquid',
  'hyperliquid': 'hyperliquid',
  'jito': 'jito',
  'justlend': 'justlend',
  'kamino': 'kamino',
  'lido': 'lido',
  'maple': 'maple',
  'morpho': 'morpho',
  'pancakeswap': 'pancakeswap',
  'pendle': 'pendle',
  'sky': 'makerdao',
  'spark': 'spark',
  'uniswap': 'uniswap',
  // CEX tokens - 部分有特殊 TVL 来源
  'bgb': null,        // Bitget - 无 TVL
  'bnb': 'chain:BSC', // BNB - 使用 BNB Chain 整条链的 TVL
  'mnt': null,        // Mantle - 无 TVL (L2 token)
  'okb': null,        // OKB - 无 TVL
};

// 链 TVL API 端点
const CHAIN_TVL_ENDPOINT = 'https://api.llama.fi/v2/chains';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// 缓存链 TVL 数据
let chainTvlCache = null;

async function fetchChainTvl(chainName) {
  if (!chainTvlCache) {
    const res = await fetch(CHAIN_TVL_ENDPOINT);
    if (!res.ok) {
      console.error(`  ✗ Failed to fetch chain TVL data: HTTP ${res.status}`);
      return null;
    }
    chainTvlCache = await res.json();
  }
  const chain = chainTvlCache.find(c => c.name === chainName);
  return chain ? chain.tvl : null;
}

async function fetchTVL(defillamaId) {
  // 处理链 TVL (格式: chain:CHAIN_NAME)
  if (defillamaId.startsWith('chain:')) {
    const chainName = defillamaId.replace('chain:', '');
    return fetchChainTvl(chainName);
  }
  
  // 普通协议 TVL
  const url = `https://api.llama.fi/tvl/${defillamaId}`;
  const res = await fetch(url);
  if (!res.ok) {
    console.error(`  ✗ Failed to fetch TVL for ${defillamaId}: HTTP ${res.status}`);
    return null;
  }
  const tvl = await res.json();
  return typeof tvl === 'number' ? tvl : null;
}

async function main() {
  console.log('Updating TVL data from DefiLlama...\n');

  // 获取所有协议目录
  const protocolDirs = fs.readdirSync(PROTOCOLS_DIR).filter(d => {
    const configPath = path.join(PROTOCOLS_DIR, d, 'config.json');
    return fs.existsSync(configPath);
  });

  let updated = 0;
  let skipped = 0;

  for (const dir of protocolDirs) {
    const configPath = path.join(PROTOCOLS_DIR, dir, 'config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    
    const defillamaId = DEFILLAMA_MAPPING[dir];
    
    if (defillamaId === null) {
      console.log(`⏭ ${dir}: No TVL source configured`);
      skipped++;
      continue;
    }
    
    if (!defillamaId) {
      console.log(`⏭ ${dir}: No DefiLlama mapping`);
      skipped++;
      continue;
    }

    const tvl = await fetchTVL(defillamaId);
    
    if (tvl !== null) {
      // 更新 config.json
      if (!config.market_data) config.market_data = {};
      config.market_data.tvl = tvl;
      config.market_data.tvl_updated = new Date().toISOString();
      
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
      console.log(`✓ ${dir}: TVL = $${(tvl / 1e9).toFixed(2)}B`);
      updated++;
    } else {
      console.log(`✗ ${dir}: Failed to fetch TVL`);
    }

    // 避免 rate limit
    await sleep(300);
  }

  console.log(`\n完成: ${updated} 个协议更新, ${skipped} 个跳过`);
  console.log('\n运行 sync-protocols.js 同步到 all-protocols.json:');
  console.log('  node scripts/sync-protocols.js');
}

main().catch(console.error);
