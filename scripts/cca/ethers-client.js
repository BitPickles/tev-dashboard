let ethersPkg = null;
try {
  ethersPkg = require("ethers");
} catch {
  ethersPkg = null;
}

if (ethersPkg?.ethers) {
  module.exports = { ethers: ethersPkg.ethers, usingFallback: false };
  return;
}

function isHexAddress(value) {
  return typeof value === "string" && /^0x[a-fA-F0-9]{40}$/.test(value);
}

class Interface {
  constructor(abi) {
    this.abi = abi || [];
    this.functionSigs = new Set();
    this.eventNames = new Set();
    for (const item of this.abi) {
      const fnMatch = /^function\s+([A-Za-z0-9_]+\(.*\))/.exec(item);
      if (fnMatch) this.functionSigs.add(fnMatch[1]);
      const eventMatch = /^event\s+([A-Za-z0-9_]+)\(/.exec(item);
      if (eventMatch) this.eventNames.add(eventMatch[1]);
    }
  }

  hasFunction(signature) {
    return this.functionSigs.has(signature);
  }

  getEvent(name) {
    if (!this.eventNames.has(name)) {
      throw new Error(`unknown event ${name}`);
    }
    return { topicHash: null };
  }

  parseLog() {
    throw new Error("parseLog unavailable in fallback mode");
  }
}

class JsonRpcProvider {
  constructor(url) {
    this.url = url;
  }

  async getBlockNumber() {
    return 0;
  }

  async getLogs() {
    return [];
  }
}

class Contract {
  constructor(address, abi) {
    this.target = address;
    this.interface = new Interface(abi);
    for (const signature of this.interface.functionSigs) {
      const name = signature.split("(")[0];
      this[name] = async () => {
        throw new Error("ethers dependency unavailable in offline fallback mode");
      };
    }
  }
}

function getAddress(value) {
  if (!isHexAddress(value)) throw new Error("invalid address");
  return `0x${value.slice(2).toLowerCase()}`;
}

const ethers = { Interface, JsonRpcProvider, Contract, getAddress };

module.exports = {
  ethers,
  usingFallback: true,
};
