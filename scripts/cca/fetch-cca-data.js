#!/usr/bin/env node
/**
 * CCA 数据获取脚本
 * 使用 Etherscan API v2 获取 Uniswap CCA 拍卖数据
 */

const https = require('https');
const fs = require('fs/promises');
const path = require('path');

// 配置
const CONFIG = {
  apiKey: 'BUWR46PIP7JVZK98IP7YRQARRSABIP3V92',
  chainId: 1,
  // 所有 CCA Factory 合约地址（按部署时间排序）
  factoryAddresses: [
    '0x0000ccadf55c911a2fbc0bb9d2942aa77c6faa1d', // v1 - 44 auctions (包含 Aztec)
    '0xcca110c1136b93eb113cceae3c25e52e180b32c9', // v2 - 4 auctions
    '0xCCccCcCAE7503Cac057829BF2811De42E16e0bD5', // v3 - 1 auction (最新)
  ],
  auctionCreatedTopic: '0x7ede475fad18ccf0039f2b956c4d43a8b4ed0853de4daaa8ae25299f331ae3b9',
  outputDir: path.resolve(__dirname, '../../data/cca'),
  // 函数选择器
  selectors: {
    clearingPrice: '0x32a0f2d7',
    currencyRaised: '0x998ba4fc',
    isGraduated: '0x9e5f2602',
    nextBidId: '0xdc269049',
    totalCleared: '0x3e9d9174',
    totalSupply: '0x18160ddd',
    startBlock: '0x48cd4cb1',
    endBlock: '0x083c6323',
    floorPrice: '0x9363c812',
    token: '0xfc0c546a',
    currency: '0xe5a6b10f',
    claimBlock: '0x37dfbc4b',
    fundsRecipient: '0x59355965',
    tokensRecipient: '0x17c7a459',
  }
};

// Q96 常量
const Q96 = 2n ** 96n;

// HTTP 请求封装
function fetch(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error(`JSON parse error: ${data.slice(0, 200)}`));
        }
      });
    }).on('error', reject);
  });
}

// 延迟函数
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Etherscan API 调用
async function etherscanApi(params) {
  await sleep(200); // 200ms 延迟避免速率限制
  const url = `https://api.etherscan.io/v2/api?chainid=${CONFIG.chainId}&apikey=${CONFIG.apiKey}&${new URLSearchParams(params)}`;
  const result = await fetch(url);
  
  // eth_call 返回 jsonrpc 格式
  if (result.jsonrpc) {
    if (result.error) {
      throw new Error(`RPC error: ${result.error.message}`);
    }
    return result.result;
  }
  
  // logs/其他 API 返回 status 格式
  if (result.status === '0' && result.message === 'No records found') {
    return []; // 空结果不是错误
  }
  if (result.status !== '1') {
    throw new Error(`API error: ${result.message || JSON.stringify(result)}`);
  }
  return result.result;
}

// 合约调用
async function callContract(address, selector) {
  const result = await etherscanApi({
    module: 'proxy',
    action: 'eth_call',
    to: address,
    data: selector,
    tag: 'latest'
  });
  return result;
}

// 解析 hex 为 BigInt
function hexToBigInt(hex) {
  if (!hex || hex === '0x') return 0n;
  return BigInt(hex);
}

// 解析 hex 为地址
function hexToAddress(hex) {
  if (!hex || hex.length < 42) return null;
  return '0x' + hex.slice(-40).toLowerCase();
}

// Q96 价格转可读格式 (考虑代币精度)
function q96ToHuman(priceQ96, tokenDecimals = 18, currencyDecimals = 6) {
  if (priceQ96 === 0n) return '0';
  // 价格 = priceQ96 / 2^96 * 10^(tokenDecimals - currencyDecimals)
  const decimalAdjust = BigInt(10) ** BigInt(tokenDecimals - currencyDecimals);
  const priceScaled = priceQ96 * decimalAdjust;
  const human = Number(priceScaled) / Number(Q96);
  return human.toFixed(8);
}

// 格式化货币金额
function formatCurrency(amount, decimals = 6) {
  const value = Number(amount) / Math.pow(10, decimals);
  return value.toFixed(2);
}

// 格式化代币数量
function formatTokens(amount, decimals = 18) {
  const value = Number(amount) / Math.pow(10, decimals);
  if (value >= 1e9) return (value / 1e9).toFixed(2) + 'B';
  if (value >= 1e6) return (value / 1e6).toFixed(2) + 'M';
  if (value >= 1e3) return (value / 1e3).toFixed(2) + 'K';
  return value.toFixed(2);
}

// 获取 ERC20 代币信息（使用已知代币列表，避免 Pro API）
async function getTokenInfo(address) {
  const addr = address.toLowerCase();
  
  // 已知代币列表
  const knownTokens = {
    '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': { symbol: 'USDC', name: 'USD Coin', decimals: 6 },
    '0xdac17f958d2ee523a2206206994597c13d831ec7': { symbol: 'USDT', name: 'Tether USD', decimals: 6 },
    '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': { symbol: 'WETH', name: 'Wrapped Ether', decimals: 18 },
    '0xcccc87d42db3d35018ecae712a0bc53e79d9cccc': { symbol: 'rCAP', name: 'CAP Redeemable Receipt Token', decimals: 18 },
    '0x6b175474e89094c44da98b954eedeac495271d0f': { symbol: 'DAI', name: 'Dai Stablecoin', decimals: 18 },
    '0xa27ec0006e59f245217ff08cd52a7e8b169e62d2': { symbol: 'AZTEC', name: 'Aztec', decimals: 18 },
  };
  
  if (knownTokens[addr]) {
    return { address, ...knownTokens[addr] };
  }
  
  // 未知代币：返回默认值，避免 API 调用
  console.log(`  ℹ️ 未知代币: ${address}`);
  return { address, symbol: 'TOKEN', name: 'Unknown Token', decimals: 18 };
}

// 获取事件日志
async function getLogs(address, topic0 = null, fromBlock = 0) {
  const params = {
    module: 'logs',
    action: 'getLogs',
    address: address,
    fromBlock: fromBlock,
    toBlock: 'latest'
  };
  if (topic0) params.topic0 = topic0;
  return await etherscanApi(params);
}

// 发现所有拍卖（扫描所有 Factory 合约）
async function discoverAuctions() {
  console.log('🔍 发现拍卖（扫描所有 Factory 合约）...');
  
  const auctions = [];
  
  for (const factoryAddress of CONFIG.factoryAddresses) {
    console.log(`  📦 扫描 Factory: ${factoryAddress}`);
    
    try {
      const logs = await getLogs(factoryAddress, CONFIG.auctionCreatedTopic);
      
      for (const log of logs) {
        // 解析 AuctionCreated 事件
        // topics[1] = auction address, topics[2] = token address
        const auctionAddress = hexToAddress(log.topics[1]);
        const tokenAddress = hexToAddress(log.topics[2]);
        const creatorAddress = log.topics[3] ? hexToAddress(log.topics[3]) : null;
        
        auctions.push({
          address: auctionAddress,
          tokenAddress,
          creatorAddress,
          factoryAddress: factoryAddress.toLowerCase(),
          blockNumber: parseInt(log.blockNumber, 16),
          transactionHash: log.transactionHash,
          timestamp: parseInt(log.timeStamp, 16)
        });
        
        console.log(`    ✓ 发现拍卖: ${auctionAddress}`);
      }
      
      console.log(`    共 ${logs.length} 个拍卖`);
    } catch (e) {
      console.error(`    ❌ 扫描失败: ${e.message}`);
    }
  }
  
  // 按时间排序（最新的在前）
  auctions.sort((a, b) => b.timestamp - a.timestamp);
  
  return auctions;
}

// 获取单个拍卖详情
async function fetchAuctionDetails(auctionInfo) {
  console.log(`📊 获取拍卖详情: ${auctionInfo.address}`);
  
  const address = auctionInfo.address;
  const errors = [];
  
  // 批量调用合约函数
  const calls = {};
  for (const [name, selector] of Object.entries(CONFIG.selectors)) {
    try {
      calls[name] = await callContract(address, selector);
    } catch (e) {
      errors.push(`${name}: ${e.message}`);
      calls[name] = null;
    }
  }
  
  // 解析数据
  const clearingPriceQ96 = hexToBigInt(calls.clearingPrice);
  const currencyRaised = hexToBigInt(calls.currencyRaised);
  const floorPriceQ96 = hexToBigInt(calls.floorPrice);
  const totalSupply = hexToBigInt(calls.totalSupply);
  const totalCleared = hexToBigInt(calls.totalCleared);
  const nextBidId = hexToBigInt(calls.nextBidId);
  const isGraduated = hexToBigInt(calls.isGraduated) === 1n;
  const startBlock = parseInt(calls.startBlock, 16) || 0;
  const endBlock = parseInt(calls.endBlock, 16) || 0;
  const claimBlock = parseInt(calls.claimBlock, 16) || 0;
  const tokenAddress = hexToAddress(calls.token);
  const currencyAddress = hexToAddress(calls.currency);
  
  // 获取代币信息
  const tokenInfo = await getTokenInfo(tokenAddress);
  const currencyInfo = await getTokenInfo(currencyAddress);
  
  // 获取事件日志
  console.log(`  📝 获取事件...`);
  let allLogs = [];
  try {
    allLogs = await getLogs(address, null, auctionInfo.blockNumber);
  } catch (e) {
    console.warn(`  ⚠️ 获取事件失败: ${e.message}`);
  }
  
  // BidSubmitted event signature (keccak256)
  // 已知的事件 topic0:
  // 0x30adbe996d7a69a21fdebcc1f8a46270bf6c22d505a7d872c1ab4767aa707609 - CheckpointUpdated
  const CHECKPOINT_TOPIC = '0x30adbe996d7a69a21fdebcc1f8a46270bf6c22d505a7d872c1ab4767aa707609';
  
  const bids = [];
  const bidders = new Set();
  const checkpoints = [];
  
  for (const log of allLogs) {
    const topic0 = log.topics[0];
    
    // 解析 CheckpointUpdated 事件
    if (topic0 === CHECKPOINT_TOPIC && log.data) {
      const blockNum = hexToBigInt('0x' + log.data.slice(2, 66));
      const price = hexToBigInt('0x' + log.data.slice(66, 130));
      checkpoints.push({
        blockNumber: Number(blockNum),
        clearingPriceQ96: price.toString(),
        clearingPriceHuman: q96ToHuman(price, tokenInfo.decimals, currencyInfo.decimals),
        timestamp: parseInt(log.timeStamp, 16)
      });
    }
    
    // 解析可能的 BidSubmitted 事件 (有 indexed bidder 和 bidId)
    if (log.topics.length >= 3 && log.data && log.data.length >= 130) {
      const bidder = hexToAddress(log.topics[1]);
      const bidId = parseInt(log.topics[2], 16);
      
      // 跳过零地址
      if (!bidder || bidder === '0x0000000000000000000000000000000000000000') continue;
      
      bidders.add(bidder);
      
      const maxPrice = hexToBigInt('0x' + log.data.slice(2, 66));
      const amount = hexToBigInt('0x' + log.data.slice(66, 130));
      
      // 验证数据合理性
      if (maxPrice > 0n && amount > 0n) {
        bids.push({
          bidder,
          bidId,
          maxPriceQ96: maxPrice.toString(),
          maxPriceHuman: q96ToHuman(maxPrice, tokenInfo.decimals, currencyInfo.decimals),
          amount: amount.toString(),
          amountHuman: formatCurrency(amount, currencyInfo.decimals),
          blockNumber: parseInt(log.blockNumber, 16),
          timestamp: parseInt(log.timeStamp, 16),
          transactionHash: log.transactionHash
        });
      }
    }
  }
  
  console.log(`  ✓ 找到 ${bids.length} 个出价, ${checkpoints.length} 个检查点`);
  
  // 获取当前区块
  let currentBlockNum;
  try {
    const currentBlock = await etherscanApi({
      module: 'proxy',
      action: 'eth_blockNumber'
    });
    currentBlockNum = parseInt(currentBlock, 16);
  } catch (e) {
    console.warn(`  ⚠️ 获取区块高度失败: ${e.message}`);
    currentBlockNum = endBlock + 1; // 假设已结束
  }
  
  // 计算状态
  let status = 'unknown';
  if (currentBlockNum < startBlock) {
    status = 'upcoming';
  } else if (currentBlockNum >= startBlock && currentBlockNum < endBlock) {
    status = 'active';
  } else if (currentBlockNum >= endBlock) {
    status = isGraduated ? 'graduated' : 'ended';
  }
  
  // 计算进度
  const progress = currentBlockNum >= endBlock ? 100 :
    currentBlockNum < startBlock ? 0 :
    Math.round((currentBlockNum - startBlock) / (endBlock - startBlock) * 100);
  
  // 构建输出
  const auction = {
    id: address,
    name: tokenInfo.symbol + ' CCA',
    status,
    
    token: {
      address: tokenAddress,
      symbol: tokenInfo.symbol,
      name: tokenInfo.name,
      decimals: tokenInfo.decimals,
      totalSupply: totalSupply.toString(),
      totalSupplyHuman: formatTokens(totalSupply, tokenInfo.decimals)
    },
    
    currency: {
      address: currencyAddress,
      symbol: currencyInfo.symbol,
      name: currencyInfo.name,
      decimals: currencyInfo.decimals
    },
    
    config: {
      startBlock,
      endBlock,
      claimBlock,
      floorPriceQ96: floorPriceQ96.toString(),
      floorPriceHuman: q96ToHuman(floorPriceQ96, tokenInfo.decimals, currencyInfo.decimals)
    },
    
    metrics: {
      clearingPriceQ96: clearingPriceQ96.toString(),
      clearingPriceHuman: q96ToHuman(clearingPriceQ96, tokenInfo.decimals, currencyInfo.decimals),
      currencyRaised: currencyRaised.toString(),
      currencyRaisedHuman: formatCurrency(currencyRaised, currencyInfo.decimals),
      raisedUsd: parseFloat(formatCurrency(currencyRaised, currencyInfo.decimals)), // USDC = USD
      totalCleared: totalCleared.toString(),
      totalClearedHuman: formatTokens(totalCleared, tokenInfo.decimals),
      bidCount: Number(nextBidId),
      bidders: bidders.size,
      isGraduated
    },
    
    progress: {
      currentBlock: currentBlockNum,
      progressPercent: progress
    },
    
    bids: bids.slice(0, 100), // 最多 100 条
    checkpoints: checkpoints, // 价格历史
    
    timestamps: {
      createdAt: new Date(auctionInfo.timestamp * 1000).toISOString(),
      createdBlock: auctionInfo.blockNumber
    },
    
    errors
  };
  
  return auction;
}

// 主函数
async function main() {
  console.log('🚀 CCA 数据获取开始\n');
  
  // 确保输出目录存在
  await fs.mkdir(CONFIG.outputDir, { recursive: true });
  await fs.mkdir(path.join(CONFIG.outputDir, 'auctions'), { recursive: true });
  
  // 发现拍卖
  const auctionInfos = await discoverAuctions();
  console.log(`\n📋 发现 ${auctionInfos.length} 个拍卖\n`);
  
  // 获取详情
  const auctions = [];
  for (const info of auctionInfos) {
    try {
      const auction = await fetchAuctionDetails(info);
      auctions.push(auction);
      
      // 保存单个拍卖详情
      const detailPath = path.join(CONFIG.outputDir, 'auctions', `${auction.id.toLowerCase()}.json`);
      await fs.writeFile(detailPath, JSON.stringify(auction, null, 2));
      console.log(`  💾 保存: ${detailPath}\n`);
    } catch (e) {
      console.error(`  ❌ 获取失败: ${info.address}`, e.message);
    }
  }
  
  // 汇总数据
  const summary = {
    generatedAt: new Date().toISOString(),
    chain: 'ethereum',
    chainId: CONFIG.chainId,
    factory: CONFIG.factoryAddress,
    totalAuctions: auctions.length,
    activeAuctions: auctions.filter(a => a.status === 'active').length,
    totalRaised: auctions.reduce((sum, a) => sum + a.metrics.raisedUsd, 0),
    auctions: auctions.map(a => ({
      id: a.id,
      name: a.name,
      status: a.status,
      raisedUsd: a.metrics.raisedUsd,
      clearingPriceUsd: parseFloat(a.metrics.clearingPriceHuman),
      floorPriceUsd: parseFloat(a.config.floorPriceHuman),
      bidders: a.metrics.bidders,
      bidCount: a.metrics.bidCount,
      token: a.token.symbol,
      currency: a.currency.symbol,
      progress: a.progress
    }))
  };
  
  // 保存汇总
  const summaryPath = path.join(CONFIG.outputDir, 'auctions.json');
  await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2));
  console.log(`\n✅ 汇总保存: ${summaryPath}`);
  
  console.log('\n🎉 数据获取完成!');
  console.log(`   总拍卖数: ${summary.totalAuctions}`);
  console.log(`   活跃拍卖: ${summary.activeAuctions}`);
  console.log(`   总募资: $${summary.totalRaised.toLocaleString()}`);
}

main().catch(e => {
  console.error('❌ 错误:', e);
  process.exit(1);
});
