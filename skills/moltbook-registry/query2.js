const { ethers } = require('ethers');

const REGISTRY_ADDRESS = '0x8a11871aCFCb879cac814D02446b2795182a4c07';
const RPC_URL = 'https://mainnet.base.org';

async function query() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);

  // Get transaction receipt to find the minted token ID
  const txHash = '0x75c558e011c522afb7d1dbfb7895681cfbdc66712b86ac099c2733476d22d784';
  const receipt = await provider.getTransactionReceipt(txHash);

  // Look for Transfer event (ERC721 mint)
  const TransferInterface = new ethers.Interface([
    'event Transfer(address indexed from, address indexed to, uint256 indexed tokenId)'
  ]);

  console.log('Transaction hash:', txHash);
  console.log('Logs:', receipt.logs.length);

  for (const log of receipt.logs) {
    if (log.address.toLowerCase() === REGISTRY_ADDRESS.toLowerCase()) {
      try {
        const parsed = TransferInterface.parseLog(log);
        if (parsed && parsed.name === 'Transfer') {
          console.log('\n✅ Agent Found!');
          console.log('Agent ID:', parsed.args.tokenId.toString());
          console.log('Owner:', parsed.args.to);

          // Claim link
          console.log('\n🔗 Claim Link:');
          console.log(`https://moltbook.com/agent/${parsed.args.tokenId.toString()}`);
          return;
        }
      } catch (e) {
        continue;
      }
    }
  }
}

query().catch(console.error);
