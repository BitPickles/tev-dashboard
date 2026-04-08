const { ethers } = require('ethers');

const REGISTRY_ADDRESS = '0x8a11871aCFCb879cac814D02446b2795182a4c07';
const RPC_URL = 'https://mainnet.base.org';

const ABI = [
  'function ownerOf(uint256 tokenId) view returns (address)',
  'function agents(uint256 tokenId) view returns (string endpoints, address wallet, bool isVerified)',
  'function totalSupply() view returns (uint256)'
];

async function query() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const contract = new ethers.Contract(REGISTRY_ADDRESS, ABI, provider);

  const myAddress = '0x3Fc530D3Ad7E39d238E33FA8F7182a693eC905Fd';
  const totalSupply = await contract.totalSupply();

  console.log('Total Agents:', totalSupply.toString());
  console.log('Searching for your agent...');

  for (let i = 0; i <= totalSupply; i++) {
    try {
      const owner = await contract.ownerOf(i);
      if (owner.toLowerCase() === myAddress.toLowerCase()) {
        const agent = await contract.agents(i);
        console.log('\n✅ Found your agent!');
        console.log('Agent ID:', i);
        console.log('Wallet:', agent.wallet);
        console.log('Verified:', agent.isVerified);
        console.log('Endpoints:', agent.endpoints || '(none)');

        // Claim link
        console.log('\n🔗 Claim Link:');
        console.log(`https://moltbook.com/agent/${i}`);
        return;
      }
    } catch (e) {
      continue;
    }
  }
}

query().catch(console.error);
