export interface HookFlags {
  beforeInitialize: boolean;
  afterInitialize: boolean;
  beforeAddLiquidity: boolean;
  afterAddLiquidity: boolean;
  beforeRemoveLiquidity: boolean;
  afterRemoveLiquidity: boolean;
  beforeSwap: boolean;
  afterSwap: boolean;
  beforeDonate: boolean;
  afterDonate: boolean;
  beforeSwapReturnsDelta: boolean;
  afterSwapReturnsDelta: boolean;
  afterAddLiquidityReturnsDelta: boolean;
  afterRemoveLiquidityReturnsDelta: boolean;
}

export interface HookProperties {
  dynamicFee: boolean;
  upgradeable: boolean;
  requiresCustomSwapData: boolean;
  vanillaSwap: boolean;
  swapAccess: "none" | "temporal" | "allowlist" | "governance" | "other";
}

export interface HookMeta {
  address: string;
  chain: string;
  chainId: number;
  name: string;
  description?: string;
  deployer?: string;
  verifiedSource: boolean;
  auditUrl?: string;
}

export interface HookEntry {
  hook: HookMeta;
  flags: HookFlags;
  properties: HookProperties;
}

export type FlagName = keyof HookFlags;
export type PropertyName = "dynamicFee" | "upgradeable" | "requiresCustomSwapData" | "vanillaSwap";

export const FLAG_NAMES: FlagName[] = [
  "beforeInitialize",
  "afterInitialize",
  "beforeAddLiquidity",
  "afterAddLiquidity",
  "beforeRemoveLiquidity",
  "afterRemoveLiquidity",
  "beforeSwap",
  "afterSwap",
  "beforeDonate",
  "afterDonate",
  "beforeSwapReturnsDelta",
  "afterSwapReturnsDelta",
  "afterAddLiquidityReturnsDelta",
  "afterRemoveLiquidityReturnsDelta",
];

export const PROPERTY_NAMES: PropertyName[] = [
  "dynamicFee",
  "upgradeable",
  "requiresCustomSwapData",
  "vanillaSwap",
];
