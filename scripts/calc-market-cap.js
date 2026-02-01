#!/usr/bin/env node
/**
 * Calculate market cap from price × circulating supply
 * Handles historical supply changes
 */

const fs = require('fs');
const path = require('path');

// Supply history (simplified - major changes only)
const SUPPLY_HISTORY = {
  uniswap: [
    { until: '2025-12-27', supply: 830000000 },  // Before burn
    { until: '9999-12-31', supply: 730000000 },  // After 100M burn
  ],
  aave: [
    { until: '9999-12-31', supply: 15300000 },   // Relatively stable
  ],
  pendle: [
    { until: '2023-06-30', supply: 150000000 },
    { until: '2024-06-30', supply: 160000000 },
    { until: '9999-12-31', supply: 168500000 },  // Current
  ],
  sky: [
    // Note: MKR → SKY migration happened late 2024
    // We track MKR price, so use MKR supply for market cap
    { until: '2024-09-17', supply: 880000 },     // MKR supply (pre-migration)
    { until: '9999-12-31', supply: 920000 },     // Post small mint
  ],
};

const DATA_DIR = path.join(__dirname, '../docs/data/daily');

function getSupply(protocol, date) {
  const history = SUPPLY_HISTORY[protocol];
  if (!history) return null;
  
  for (const period of history) {
    if (date <= period.until) {
      return period.supply;
    }
  }
  return history[history.length - 1].supply;
}

function processProtocol(protocolId) {
  console.log(`\n=== ${protocolId} ===`);
  
  const protocolDir = path.join(DATA_DIR, protocolId);
  if (!fs.existsSync(protocolDir)) {
    console.log('  Directory not found');
    return;
  }
  
  const files = fs.readdirSync(protocolDir).filter(f => f.match(/^\d{4}-\d{2}\.json$/));
  let updated = 0;
  let totalRecords = 0;
  
  for (const file of files) {
    const filePath = path.join(protocolDir, file);
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    
    let changed = false;
    for (const rec of data.records || []) {
      if (rec.price_usd) {
        const supply = getSupply(protocolId, rec.date);
        if (supply) {
          const newMarketCap = rec.price_usd * supply;
          rec.market_cap_usd = Math.round(newMarketCap);
          rec.circulating_supply = supply;
          changed = true;
          totalRecords++;
        }
      }
    }
    
    if (changed) {
      data.fetched_at = new Date().toISOString();
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
      updated++;
    }
  }
  
  console.log(`  Updated ${updated} files, ${totalRecords} records`);
}

function main() {
  console.log('=== Market Cap Calculator ===');
  
  for (const protocol of Object.keys(SUPPLY_HISTORY)) {
    processProtocol(protocol);
  }
  
  console.log('\n=== Done ===');
}

main();
