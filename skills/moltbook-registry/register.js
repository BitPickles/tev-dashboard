const { ethers } = require('ethers');

const REGISTRY_ADDRESS = '0x8a11871aCFCb879cac814D02446b2795182a4c07';
const RPC_URL = 'https://mainnet.base.org';
const REGISTRATION_FEE = '0.0001';

const ABI = [
  'function registerAgent(address to, string uri, string endpoints, address agentWallet) payable returns (uint256)'
];

async function register() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(process.env.WALLET_PRIVATE_KEY, provider);
  const contract = new ethers.Contract(REGISTRY_ADDRESS, ABI, wallet);

  const myAddress = wallet.address;
  const metadataUri = `https://moltbook.com/agent/${myAddress}`;
  const endpointsJson = '{}';
  const agentWalletAddress = myAddress;

  console.log('Wallet:', myAddress);
  console.log('Balance:', ethers.formatEther(await provider.getBalance(myAddress)), 'ETH');
  console.log('\nRegistering agent...');

  const fee = ethers.parseEther(REGISTRATION_FEE);
  const tx = await contract.registerAgent(myAddress, metadataUri, endpointsJson, agentWalletAddress, { value: fee });

  console.log('TX Sent:', tx.hash);
  const receipt = await tx.wait();

  console.log('\n✅ Registration successful!');
  console.log('Transaction:', tx.hash);
  console.log('Block:', receipt.blockNumber);
  console.log('Agent ID will be minted as token ID');
}

register().catch(console.error);
