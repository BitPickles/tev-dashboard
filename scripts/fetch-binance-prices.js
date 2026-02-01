#!/usr/bin/env node
/**
 * Fetch historical prices from Binance API (no key required)
 * Updates daily JSON files with price data
 */

const fs = require('fs');
const path = require('path');

const PROTOCOLS = [
  { id: 'uniswap', symbol: 'UNIUSDT' },
  { id: 'aave', symbol: 'AAVEUSDT' },
  { id: 'pendle', symbol: 'PENDLEUSDT' },
  { id: 'sky', symbol: 'MKRUSDT' }, // Sky = MakerDAO
];

const DATA_DIR = path.join(__dirname, '../docs/data/daily');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchBinanceKlines(symbol, startTime, endTime) {
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1d&startTime=${startTime}&endTime=${endTime}&limit=1000`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function fetchAllPrices(symbol) {
  console.log(`  Fetching Binance prices for ${symbol}...`);
  
  const prices = new Map();
  let endTime = Date.now();
  const minTime = new Date('2019-01-01').getTime();
  
  while (endTime > minTime) {
    const startTime = endTime - (1000 * 24 * 60 * 60 * 1000); // 1000 days back
    
    try {
      const klines = await fetchBinanceKlines(symbol, startTime, endTime);
      
      if (klines.length === 0) break;
      
      for (const k of klines) {
        const date = new Date(k[0]).toISOString().split('T')[0];
        const closePrice = parseFloat(k[4]);
        prices.set(date, closePrice);
      }
      
      // Move window back
      endTime = klines[0][0] - 1;
      await sleep(100); // Rate limit
    } catch (err) {
      console.log(`    Error at ${new Date(endTime).toISOString()}: ${err.message}`);
      break;
    }
  }
  
  console.log(`    Got ${prices.size} days of prices`);
  return prices;
}

function updateDailyFiles(protocolId, prices) {
  const protocolDir = path.join(DATA_DIR, protocolId);
  if (!fs.existsSync(protocolDir)) return 0;
  
  const files = fs.readdirSync(protocolDir).filter(f => f.match(/^\d{4}-\d{2}\.json$/));
  let updated = 0;
  
  for (const file of files) {
    const filePath = path.join(protocolDir, file);
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    
    let changed = false;
    for (const rec of data.records || []) {
      const price = prices.get(rec.date);
      if (price && (!rec.price_usd || rec.price_usd === null)) {
        rec.price_usd = price;
        changed = true;
      }
      // Also update if we have a price and want to refresh
      if (price) {
        rec.price_usd = price;
        changed = true;
      }
    }
    
    if (changed) {
      data.fetched_at = new Date().toISOString();
      data.source = 'defillama+binance';
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
      updated++;
    }
  }
  
  return updated;
}

async function main() {
  console.log('=== Binance Price Fetcher ===\n');
  
  for (const protocol of PROTOCOLS) {
    console.log(`\n=== ${protocol.id} (${protocol.symbol}) ===`);
    
    try {
      const prices = await fetchAllPrices(protocol.symbol);
      const updated = updateDailyFiles(protocol.id, prices);
      console.log(`  Updated ${updated} files`);
    } catch (err) {
      console.error(`  Error: ${err.message}`);
    }
    
    await sleep(500);
  }
  
  console.log('\n=== Done ===');
}

main().catch(console.error);
