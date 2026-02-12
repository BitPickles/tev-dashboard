#!/usr/bin/env node
const fs = require("node:fs/promises");
const path = require("node:path");
const { ethers, usingFallback } = require("./ethers-client");
const { CHAIN_CONFIG, AUCTION_ABI } = require("./config");

const chainKey = process.argv[2] || process.env.CHAIN || "ethereum";
const chain = CHAIN_CONFIG[chainKey];

if (!chain) {
  console.error(`Unsupported chain "${chainKey}". Available: ${Object.keys(CHAIN_CONFIG).join(", ")}`);
  process.exit(1);
}

const AUCTIONS_FILE = path.resolve("data", "cca", "auctions.json");
const OUTPUT_DIR = path.resolve("data", "cca", "auctions");

function normalizeValue(value) {
  if (value === undefined || value === null) return null;
  if (typeof value === "bigint") return value.toString();
  if (Array.isArray(value)) return value.map(normalizeValue);
  if (typeof value === "object") {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (String(Number(k)) === k) continue;
      out[k] = normalizeValue(v);
    }
    return out;
  }
  return value;
}

function safeAddress(value) {
  if (!value) return null;
  try {
    return ethers.getAddress(value);
  } catch {
    return null;
  }
}

async function callFirst(contract, calls, errors, label) {
  for (const signature of calls) {
    const fn = signature.split("(")[0];
    if (!contract.interface.hasFunction(signature)) continue;
    try {
      const value = await contract[fn]();
      return { fn, value };
    } catch (error) {
      errors.push(`${label}:${fn} failed (${error.message})`);
    }
  }
  return { fn: null, value: null };
}

async function readUniqueBidders(provider, contract, fromBlock) {
  const bidderEvents = [
    "event BidSubmitted(address indexed bidder,uint256 indexed bidId,uint256 maxPrice,uint256 amount)",
    "event BidPlaced(address indexed bidder,uint256 indexed bidId,uint256 maxPrice,uint256 amount)",
  ];
  const iface = new ethers.Interface(bidderEvents);
  const topics = [];
  for (const eventName of ["BidSubmitted", "BidPlaced"]) {
    try {
      topics.push(iface.getEvent(eventName).topicHash);
    } catch {
      continue;
    }
  }
  if (topics.length === 0) return 0;

  const latest = await provider.getBlockNumber();
  const seen = new Set();
  const chunkSize = 30_000;
  for (let start = fromBlock; start <= latest; start += chunkSize + 1) {
    const end = Math.min(start + chunkSize, latest);
    const logs = await provider.getLogs({
      address: contract.target,
      topics: [topics],
      fromBlock: start,
      toBlock: end,
    });
    for (const log of logs) {
      try {
        const parsed = iface.parseLog(log);
        const bidder = safeAddress(parsed?.args?.bidder);
        if (bidder) seen.add(bidder);
      } catch {
        continue;
      }
    }
  }
  return seen.size;
}

async function main() {
  if (usingFallback) {
    console.warn("Warning: running in fallback mode (ethers not installed). Outputs will contain limited/null data.");
  }
  const provider = new ethers.JsonRpcProvider(chain.rpcUrl);
  let auctionsData;
  try {
    const auctionsRaw = await fs.readFile(AUCTIONS_FILE, "utf8");
    auctionsData = JSON.parse(auctionsRaw);
  } catch (error) {
    if (error?.code === "ENOENT") {
      await fs.mkdir(path.dirname(AUCTIONS_FILE), { recursive: true });
      auctionsData = {
        generatedAt: new Date().toISOString(),
        chain: chainKey,
        rpcUrl: chain.rpcUrl,
        fromBlock: chain.startBlock || 0,
        toBlock: null,
        auctions: [],
        errors: ["No discovery file found. Run `npm run discover` to populate auctions."],
      };
      await fs.writeFile(AUCTIONS_FILE, JSON.stringify(auctionsData, null, 2));
      console.log(`No auctions file found. Created empty discovery file at ${AUCTIONS_FILE}`);
    } else {
      throw error;
    }
  }
  const auctions = auctionsData.auctions || [];

  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  for (const auctionInfo of auctions) {
    const auctionAddress = safeAddress(auctionInfo.address);
    if (!auctionAddress) continue;

    const errors = [];
    const contract = new ethers.Contract(auctionAddress, AUCTION_ABI, provider);

    const [graduated, checkpoint, clearingPrice, totalRaised, bidCount, token] = await Promise.all([
      callFirst(contract, ["isGraduated()"], errors, "status"),
      callFirst(contract, ["checkpoint()"], errors, "checkpoint"),
      callFirst(contract, ["clearingPrice()", "lastClearingPrice()", "currentPrice()"], errors, "price"),
      callFirst(contract, ["totalRaised()", "totalCurrencyRaised()"], errors, "raised"),
      callFirst(contract, ["bidCount()", "getBidCount()", "totalBids()"], errors, "bids"),
      callFirst(contract, ["token()", "saleToken()"], errors, "token"),
    ]);

    let bidderCount = normalizeValue(bidCount.value);
    if (bidderCount === null) {
      try {
        bidderCount = await readUniqueBidders(
          provider,
          contract,
          Number(process.env.AUCTION_LOG_START_BLOCK || auctionsData.fromBlock || chain.startBlock || 0)
        );
      } catch (error) {
        errors.push(`bids:log scan failed (${error.message})`);
      }
    }

    const output = {
      generatedAt: new Date().toISOString(),
      chain: chainKey,
      auctionAddress,
      factoryAddress: auctionInfo.factoryAddress || null,
      source: auctionInfo,
      status: {
        isGraduated: normalizeValue(graduated.value),
        method: graduated.fn,
      },
      pricing: {
        clearingPrice: normalizeValue(clearingPrice.value),
        method: clearingPrice.fn,
        checkpoint: normalizeValue(checkpoint.value),
        checkpointMethod: checkpoint.fn,
      },
      totals: {
        totalRaised: normalizeValue(totalRaised.value),
        totalRaisedMethod: totalRaised.fn,
        bidderCount: normalizeValue(bidderCount),
        bidderCountMethod: bidCount.fn || "event-log-unique-bidders",
      },
      token: {
        address: safeAddress(token.value),
        method: token.fn,
      },
      errors,
    };

    const fileName = `${auctionAddress.toLowerCase()}.json`;
    const outPath = path.join(OUTPUT_DIR, fileName);
    await fs.writeFile(outPath, JSON.stringify(output, null, 2));
    console.log(`Fetched ${auctionAddress} -> ${outPath}`);
  }

  console.log(`Fetched ${auctions.length} auctions`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
