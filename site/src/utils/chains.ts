export interface ChainInfo {
  chainId: number;
  displayName: string;
  color: string;
  explorerBaseUrl: string;
}

export const CHAINS: Record<string, ChainInfo> = {
  arbitrum: {
    chainId: 42161,
    displayName: "Arbitrum",
    color: "#28a0f0",
    explorerBaseUrl: "https://arbiscan.io",
  },
  avalanche: {
    chainId: 43114,
    displayName: "Avalanche",
    color: "#e84142",
    explorerBaseUrl: "https://snowscan.xyz",
  },
  base: {
    chainId: 8453,
    displayName: "Base",
    color: "#0052ff",
    explorerBaseUrl: "https://basescan.org",
  },
  blast: {
    chainId: 81457,
    displayName: "Blast",
    color: "#fcfc03",
    explorerBaseUrl: "https://blastscan.io",
  },
  bnb: {
    chainId: 56,
    displayName: "BNB Chain",
    color: "#f0b90b",
    explorerBaseUrl: "https://bscscan.com",
  },
  celo: {
    chainId: 42220,
    displayName: "Celo",
    color: "#35d07f",
    explorerBaseUrl: "https://celoscan.io",
  },
  ethereum: {
    chainId: 1,
    displayName: "Ethereum",
    color: "#627eea",
    explorerBaseUrl: "https://etherscan.io",
  },
  ink: {
    chainId: 57073,
    displayName: "Ink",
    color: "#7c3aed",
    explorerBaseUrl: "https://explorer.inkonchain.com",
  },
  optimism: {
    chainId: 10,
    displayName: "Optimism",
    color: "#ff0420",
    explorerBaseUrl: "https://optimistic.etherscan.io",
  },
  polygon: {
    chainId: 137,
    displayName: "Polygon",
    color: "#8247e5",
    explorerBaseUrl: "https://polygonscan.com",
  },
  soneium: {
    chainId: 1868,
    displayName: "Soneium",
    color: "#1a1a2e",
    explorerBaseUrl: "https://soneium.blockscout.com",
  },
  unichain: {
    chainId: 130,
    displayName: "Unichain",
    color: "#ff007a",
    explorerBaseUrl: "https://uniscan.xyz",
  },
  worldchain: {
    chainId: 480,
    displayName: "World Chain",
    color: "#000000",
    explorerBaseUrl: "https://worldscan.org",
  },
  zora: {
    chainId: 7777777,
    displayName: "Zora",
    color: "#5b5bd6",
    explorerBaseUrl: "https://explorer.zora.energy",
  },
};

export function getExplorerUrl(chain: string, address: string): string {
  const info = CHAINS[chain];
  if (!info) return "#";
  return `${info.explorerBaseUrl}/address/${address}`;
}
