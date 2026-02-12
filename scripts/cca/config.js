const CHAIN_CONFIG = {
  ethereum: {
    chainId: 1,
    name: "Ethereum Mainnet",
    rpcUrl: process.env.ETH_RPC_URL || "https://eth.llamarpc.com",
    factoryAddresses: {
      v110: "0xCCccCcCAE7503Cac057829BF2811De42E16e0bD5",
      v100Candidate: "0x0000ccaDF55C911a2FbC0BB9d2942Aa77c6FAa1D",
    },
    startBlock: 0,
  },
};

const FACTORY_ABI = [
  "event AuctionCreated(address indexed auction,address indexed token,address indexed creator)",
  "event DistributionInitialized(address indexed token,address indexed auction,address indexed caller,uint256 amount,bytes configData)",
  "function auctionCount() view returns (uint256)",
  "function auctionsLength() view returns (uint256)",
  "function numAuctions() view returns (uint256)",
  "function getAuctionsCount() view returns (uint256)",
  "function auctions(uint256) view returns (address)",
  "function allAuctions(uint256) view returns (address)",
  "function getAuction(uint256) view returns (address)",
];

const AUCTION_ABI = [
  "event CheckpointUpdated(uint256 indexed checkpointId,uint256 clearingPrice,uint256 totalRaised)",
  "event BidSubmitted(address indexed bidder,uint256 indexed bidId,uint256 maxPrice,uint256 amount)",
  "event BidExited(address indexed bidder,uint256 indexed bidId,uint256 returnedAmount)",
  "event TokensClaimed(address indexed bidder,uint256 indexed bidId,uint256 amount)",
  "function isGraduated() view returns (bool)",
  "function checkpoint() view returns (tuple(uint256 blockNumber,uint256 clearingPrice,uint256 totalRaised,uint256 soldAmount))",
  "function clearingPrice() view returns (uint256)",
  "function lastClearingPrice() view returns (uint256)",
  "function currentPrice() view returns (uint256)",
  "function totalRaised() view returns (uint256)",
  "function totalCurrencyRaised() view returns (uint256)",
  "function bidCount() view returns (uint256)",
  "function getBidCount() view returns (uint256)",
  "function totalBids() view returns (uint256)",
  "function token() view returns (address)",
  "function saleToken() view returns (address)",
];

module.exports = {
  CHAIN_CONFIG,
  FACTORY_ABI,
  AUCTION_ABI,
};
