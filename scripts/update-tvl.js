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
  // CEX tokens 没有 TVL
  'bgb': null,
  'bnb': null,
  'mnt': null,
  'okb': null,
};

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchTVL(defillamaId) {
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
      console.log(`⏭ ${dir}: CEX token, no TVL`);
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
