#!/usr/bin/env node
const fs = require("node:fs/promises");
const path = require("node:path");
const { ethers, usingFallback } = require("./ethers-client");
const { CHAIN_CONFIG, FACTORY_ABI } = require("./config");

const chainKey = process.argv[2] || process.env.CHAIN || "ethereum";
const chain = CHAIN_CONFIG[chainKey];

if (!chain) {
  console.error(`Unsupported chain "${chainKey}". Available: ${Object.keys(CHAIN_CONFIG).join(", ")}`);
  process.exit(1);
}

const iface = new ethers.Interface(FACTORY_ABI);

function safeAddress(value) {
  if (!value) return null;
  try {
    return ethers.getAddress(value);
  } catch {
    return null;
  }
}

async function readCount(contract) {
  const countMethods = ["auctionCount", "auctionsLength", "numAuctions", "getAuctionsCount"];
  for (const method of countMethods) {
    if (!contract.interface.hasFunction(`${method}()`)) continue;
    try {
      const count = await contract[method]();
      return Number(count);
    } catch {
      continue;
    }
  }
  return null;
}

async function readAuctionByIndex(contract, i) {
  const indexMethods = ["auctions", "allAuctions", "getAuction"];
  for (const method of indexMethods) {
    if (!contract.interface.hasFunction(`${method}(uint256)`)) continue;
    try {
      const value = await contract[method](i);
      const auction = safeAddress(value);
      if (auction) return auction;
    } catch {
      continue;
    }
  }
  return null;
}

function addressFromLog(log) {
  const parsed = iface.parseLog(log);
  const event = parsed?.name;
  if (!event) return null;
  if (event === "AuctionCreated") {
    return {
      address: safeAddress(parsed.args.auction),
      token: safeAddress(parsed.args.token),
      discoveredVia: "event:AuctionCreated",
    };
  }
  if (event === "DistributionInitialized") {
    return {
      address: safeAddress(parsed.args.auction),
      token: safeAddress(parsed.args.token),
      discoveredVia: "event:DistributionInitialized",
    };
  }
  return null;
}

async function discoverFromEvents(provider, factoryAddress, fromBlock, toBlock) {
  const auctions = new Map();
  const topicCandidates = ["AuctionCreated", "DistributionInitialized"]
    .map((name) => {
      try {
        return iface.getEvent(name).topicHash;
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  const chunkSize = 30_000;
  for (let start = fromBlock; start <= toBlock; start += chunkSize + 1) {
    const end = Math.min(start + chunkSize, toBlock);
    const logs = await provider.getLogs({
      address: factoryAddress,
      topics: [topicCandidates],
      fromBlock: start,
      toBlock: end,
    });
    for (const log of logs) {
      try {
        const info = addressFromLog(log);
        if (!info?.address) continue;
        const existing = auctions.get(info.address) || {};
        auctions.set(info.address, {
          address: info.address,
          token: info.token || existing.token || null,
          factoryAddress,
          chain: chainKey,
          discoveredVia: existing.discoveredVia || info.discoveredVia,
          creationBlock: existing.creationBlock || log.blockNumber,
          creationTxHash: existing.creationTxHash || log.transactionHash,
        });
      } catch {
        continue;
      }
    }
  }

  return auctions;
}

async function main() {
  if (usingFallback) {
    console.warn("Warning: running in fallback mode (ethers not installed). Output will be empty until dependencies are installed.");
  }
  const provider = new ethers.JsonRpcProvider(chain.rpcUrl);
  const toBlock = await provider.getBlockNumber();
  const fromBlock = Number(process.env.START_BLOCK || chain.startBlock || 0);

  const discovered = new Map();
  const errors = [];

  for (const factoryAddress of Object.values(chain.factoryAddresses)) {
    const contract = new ethers.Contract(factoryAddress, FACTORY_ABI, provider);
    let foundFromMethods = false;

    try {
      const count = await readCount(contract);
      if (count !== null && Number.isFinite(count) && count >= 0) {
        foundFromMethods = true;
        for (let i = 0; i < count; i += 1) {
          const auction = await readAuctionByIndex(contract, i);
          if (!auction) continue;
          discovered.set(auction, {
            address: auction,
            token: null,
            factoryAddress,
            chain: chainKey,
            discoveredVia: "factory-index",
            creationBlock: null,
            creationTxHash: null,
          });
        }
      }
    } catch (error) {
      errors.push(`factory method discovery failed for ${factoryAddress}: ${error.message}`);
    }

    if (!foundFromMethods) {
      try {
        const fromEvents = await discoverFromEvents(provider, factoryAddress, fromBlock, toBlock);
        for (const [address, info] of fromEvents.entries()) discovered.set(address, info);
      } catch (error) {
        errors.push(`factory event discovery failed for ${factoryAddress}: ${error.message}`);
      }
    }
  }

  const output = {
    generatedAt: new Date().toISOString(),
    chain: chainKey,
    rpcUrl: chain.rpcUrl,
    fromBlock,
    toBlock,
    auctions: Array.from(discovered.values()).sort((a, b) => a.address.localeCompare(b.address)),
    errors,
  };

  const outputPath = path.resolve("data", "cca", "auctions.json");
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, JSON.stringify(output, null, 2));

  console.log(`Discovered ${output.auctions.length} auctions -> ${outputPath}`);
  if (errors.length > 0) {
    console.log(`Completed with ${errors.length} non-fatal warnings.`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
