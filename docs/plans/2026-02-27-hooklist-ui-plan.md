# Hooklist Explorer UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a React SPA that lets developers browse, filter, and inspect all Uniswap v4 hooks in the hooklist registry.

**Architecture:** Static React + TypeScript app in `site/` that fetches `hooklist.json` at runtime. All filtering is client-side. Deployed via GitHub Pages. Split layout inspired by tokenlists.org — hero panel left, searchable card grid right.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS v4

**Design doc:** `docs/plans/2026-02-27-hooklist-ui-design.md`

---

### Task 1: Scaffold Vite + React + TypeScript project

**Files:**
- Create: `site/package.json`
- Create: `site/vite.config.ts`
- Create: `site/tsconfig.json`
- Create: `site/index.html`
- Create: `site/src/main.tsx`
- Create: `site/src/App.tsx`
- Create: `site/.gitignore`

**Step 1: Scaffold project**

```bash
cd /home/toda/dev/hooklist
npm create vite@latest site -- --template react-ts
```

**Step 2: Install Tailwind CSS v4**

```bash
cd site
npm install
npm install tailwindcss @tailwindcss/vite
```

**Step 3: Configure Vite with Tailwind plugin**

Replace `site/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/hooklist/",
});
```

The `base: '/hooklist/'` is needed because GitHub Pages serves this repo at `https://<user>.github.io/hooklist/`.

**Step 4: Set up Tailwind CSS entry point**

Replace `site/src/index.css`:

```css
@import "tailwindcss";
```

**Step 5: Replace App.tsx with minimal shell**

```tsx
function App() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      <h1 className="text-2xl font-bold p-8">Hooklist</h1>
    </div>
  );
}

export default App;
```

**Step 6: Clean up scaffolded files**

Delete these files that Vite scaffolded but we don't need:
- `site/src/App.css`
- `site/src/assets/react.svg`
- `site/public/vite.svg`

Update `site/src/main.tsx` to only import `index.css` (not `App.css`):

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

Update `site/index.html` title to "Hooklist — Uniswap v4 Hook Registry".

Add `site/.gitignore`:

```
node_modules
dist
```

**Step 7: Verify it runs**

```bash
cd site && npx vite --open
```

Expected: Browser opens showing "Hooklist" heading with Tailwind styling applied (white bg, bold text).

**Step 8: Commit**

```bash
cd /home/toda/dev/hooklist
git add site/
git commit -m "feat(site): scaffold Vite + React + Tailwind project"
```

---

### Task 2: Define TypeScript types and chain metadata

**Files:**
- Create: `site/src/types.ts`
- Create: `site/src/utils/chains.ts`

**Step 1: Create types matching schema.json**

Create `site/src/types.ts`:

```ts
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
export type PropertyName = keyof HookProperties;

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
];
```

**Step 2: Create chain metadata utility**

Create `site/src/utils/chains.ts`:

```ts
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
```

**Step 3: Commit**

```bash
git add site/src/types.ts site/src/utils/
git commit -m "feat(site): add TypeScript types and chain metadata"
```

---

### Task 3: Build useHooks data loading and filtering hook

**Files:**
- Create: `site/src/hooks/useHooks.ts`

**Step 1: Create the custom hook**

Create `site/src/hooks/useHooks.ts`:

```ts
import { useState, useEffect, useMemo } from "react";
import type { HookEntry, FlagName, PropertyName } from "../types";

export interface Filters {
  search: string;
  chains: string[];
  flags: FlagName[];
  properties: PropertyName[];
}

const EMPTY_FILTERS: Filters = {
  search: "",
  chains: [],
  flags: [],
  properties: [],
};

function parseFiltersFromUrl(): Filters {
  const params = new URLSearchParams(window.location.search);
  return {
    search: params.get("search") ?? "",
    chains: params.get("chains")?.split(",").filter(Boolean) ?? [],
    flags: (params.get("flags")?.split(",").filter(Boolean) ?? []) as FlagName[],
    properties: (params.get("properties")?.split(",").filter(Boolean) ?? []) as PropertyName[],
  };
}

function writeFiltersToUrl(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.chains.length) params.set("chains", filters.chains.join(","));
  if (filters.flags.length) params.set("flags", filters.flags.join(","));
  if (filters.properties.length) params.set("properties", filters.properties.join(","));
  const qs = params.toString();
  const url = qs ? `?${qs}` : window.location.pathname;
  window.history.replaceState(null, "", url);
}

function matchesFilters(hook: HookEntry, filters: Filters): boolean {
  // Search: match name or description (case-insensitive)
  if (filters.search) {
    const q = filters.search.toLowerCase();
    const name = hook.hook.name.toLowerCase();
    const desc = (hook.hook.description ?? "").toLowerCase();
    if (!name.includes(q) && !desc.includes(q)) return false;
  }

  // Chain filter: hook must be in one of the selected chains
  if (filters.chains.length > 0) {
    if (!filters.chains.includes(hook.hook.chain)) return false;
  }

  // Flag filter: hook must have ALL selected flags enabled
  if (filters.flags.length > 0) {
    for (const flag of filters.flags) {
      if (!hook.flags[flag]) return false;
    }
  }

  // Property filter: hook must have ALL selected properties enabled
  if (filters.properties.length > 0) {
    for (const prop of filters.properties) {
      if (!hook.properties[prop]) return false;
    }
  }

  return true;
}

export function useHooks() {
  const [hooks, setHooks] = useState<HookEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(parseFiltersFromUrl);

  // Load hooklist.json once on mount
  useEffect(() => {
    fetch(import.meta.env.BASE_URL + "hooklist.json")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: HookEntry[]) => {
        setHooks(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Sync filters to URL
  useEffect(() => {
    writeFiltersToUrl(filters);
  }, [filters]);

  // Derived: available chains from actual data
  const availableChains = useMemo(() => {
    const chainSet = new Set(hooks.map((h) => h.hook.chain));
    return [...chainSet].sort();
  }, [hooks]);

  // Derived: filtered hooks
  const filtered = useMemo(
    () => hooks.filter((h) => matchesFilters(h, filters)),
    [hooks, filters]
  );

  return {
    hooks: filtered,
    totalCount: hooks.length,
    loading,
    error,
    filters,
    setFilters,
    availableChains,
  };
}
```

**Step 2: Verify it compiles**

```bash
cd site && npx tsc --noEmit
```

Expected: No type errors.

**Step 3: Commit**

```bash
git add site/src/hooks/
git commit -m "feat(site): add useHooks data loading and filtering hook"
```

---

### Task 4: Build Header component

**Files:**
- Create: `site/src/components/Header.tsx`
- Modify: `site/src/App.tsx`

**Step 1: Create Header.tsx**

```tsx
export function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
      <div className="flex items-center gap-2">
        <span className="text-xl font-bold tracking-tight">Hooklist</span>
      </div>
      <a
        href="https://github.com/uniswapfoundation/hooklist"
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
      >
        GitHub
      </a>
    </header>
  );
}
```

**Step 2: Wire into App.tsx**

Replace `site/src/App.tsx`:

```tsx
import { Header } from "./components/Header";
import { useHooks } from "./hooks/useHooks";

function App() {
  const { hooks, totalCount, loading, error } = useHooks();

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Header />
      <main className="p-8">
        {loading && <p className="text-gray-500">Loading hooks...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        {!loading && !error && (
          <p className="text-gray-500">
            {hooks.length} of {totalCount} hooks
          </p>
        )}
      </main>
    </div>
  );
}

export default App;
```

**Step 3: Copy hooklist.json to public/ for dev server**

```bash
cp /home/toda/dev/hooklist/hooklist.json /home/toda/dev/hooklist/site/public/hooklist.json
```

**Step 4: Verify in browser**

```bash
cd site && npx vite
```

Expected: Header shows "Hooklist" + GitHub link. Below it: "121 of 121 hooks" (or current count).

**Step 5: Commit**

```bash
git add site/src/components/Header.tsx site/src/App.tsx site/public/hooklist.json
git commit -m "feat(site): add Header component and wire up data loading"
```

---

### Task 5: Build filter components (SearchBar, ChainFilter, FlagFilter, PropertyFilter)

**Files:**
- Create: `site/src/components/SearchBar.tsx`
- Create: `site/src/components/ChainFilter.tsx`
- Create: `site/src/components/FlagFilter.tsx`
- Create: `site/src/components/PropertyFilter.tsx`

**Step 1: Create SearchBar.tsx**

```tsx
interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: Props) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search hooks..."
      className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-pink-500/40 focus:border-pink-500 text-sm"
    />
  );
}
```

**Step 2: Create ChainFilter.tsx**

```tsx
import { CHAINS } from "../utils/chains";

interface Props {
  available: string[];
  selected: string[];
  onChange: (chains: string[]) => void;
}

export function ChainFilter({ available, selected, onChange }: Props) {
  function toggle(chain: string) {
    if (selected.includes(chain)) {
      onChange(selected.filter((c) => c !== chain));
    } else {
      onChange([...selected, chain]);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {available.map((chain) => {
        const active = selected.includes(chain);
        const info = CHAINS[chain];
        return (
          <button
            key={chain}
            onClick={() => toggle(chain)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
              active
                ? "text-white border-transparent"
                : "text-gray-600 border-gray-300 hover:border-gray-400"
            }`}
            style={active ? { backgroundColor: info?.color ?? "#6b7280" } : undefined}
          >
            {info?.displayName ?? chain}
          </button>
        );
      })}
    </div>
  );
}
```

**Step 3: Create FlagFilter.tsx**

```tsx
import { FLAG_NAMES, type FlagName } from "../types";

interface Props {
  selected: FlagName[];
  onChange: (flags: FlagName[]) => void;
}

const LABELS: Record<FlagName, string> = {
  beforeInitialize: "beforeInitialize",
  afterInitialize: "afterInitialize",
  beforeAddLiquidity: "beforeAddLiquidity",
  afterAddLiquidity: "afterAddLiquidity",
  beforeRemoveLiquidity: "beforeRemoveLiquidity",
  afterRemoveLiquidity: "afterRemoveLiquidity",
  beforeSwap: "beforeSwap",
  afterSwap: "afterSwap",
  beforeDonate: "beforeDonate",
  afterDonate: "afterDonate",
  beforeSwapReturnsDelta: "beforeSwapReturnsDelta",
  afterSwapReturnsDelta: "afterSwapReturnsDelta",
  afterAddLiquidityReturnsDelta: "afterAddLiqReturnsDelta",
  afterRemoveLiquidityReturnsDelta: "afterRemLiqReturnsDelta",
};

export function FlagFilter({ selected, onChange }: Props) {
  function toggle(flag: FlagName) {
    if (selected.includes(flag)) {
      onChange(selected.filter((f) => f !== flag));
    } else {
      onChange([...selected, flag]);
    }
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {FLAG_NAMES.map((flag) => {
        const active = selected.includes(flag);
        return (
          <button
            key={flag}
            onClick={() => toggle(flag)}
            className={`px-2 py-0.5 rounded text-xs font-mono transition-colors cursor-pointer ${
              active
                ? "bg-pink-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {LABELS[flag]}
          </button>
        );
      })}
    </div>
  );
}
```

**Step 4: Create PropertyFilter.tsx**

```tsx
import { PROPERTY_NAMES, type PropertyName } from "../types";

interface Props {
  selected: PropertyName[];
  onChange: (properties: PropertyName[]) => void;
}

const LABELS: Record<PropertyName, string> = {
  dynamicFee: "Dynamic Fee",
  upgradeable: "Upgradeable",
  requiresCustomSwapData: "Custom Swap Data",
};

export function PropertyFilter({ selected, onChange }: Props) {
  function toggle(prop: PropertyName) {
    if (selected.includes(prop)) {
      onChange(selected.filter((p) => p !== prop));
    } else {
      onChange([...selected, prop]);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {PROPERTY_NAMES.map((prop) => {
        const active = selected.includes(prop);
        return (
          <button
            key={prop}
            onClick={() => toggle(prop)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
              active
                ? "bg-pink-600 text-white border-pink-600"
                : "text-gray-600 border-gray-300 hover:border-gray-400"
            }`}
          >
            {LABELS[prop]}
          </button>
        );
      })}
    </div>
  );
}
```

**Step 5: Commit**

```bash
git add site/src/components/SearchBar.tsx site/src/components/ChainFilter.tsx site/src/components/FlagFilter.tsx site/src/components/PropertyFilter.tsx
git commit -m "feat(site): add filter components (search, chain, flags, properties)"
```

---

### Task 6: Build HookCard and HookGrid components

**Files:**
- Create: `site/src/components/HookCard.tsx`
- Create: `site/src/components/HookGrid.tsx`

**Step 1: Create HookCard.tsx**

```tsx
import type { HookEntry } from "../types";
import { CHAINS } from "../utils/chains";

interface Props {
  hook: HookEntry;
  onClick: () => void;
}

export function HookCard({ hook, onClick }: Props) {
  const chain = CHAINS[hook.hook.chain];
  const activeFlags = Object.values(hook.flags).filter(Boolean).length;

  return (
    <button
      onClick={onClick}
      className="text-left w-full p-4 rounded-lg border border-gray-200 hover:shadow-md hover:border-gray-300 transition-all cursor-pointer"
      style={{ borderLeftWidth: "3px", borderLeftColor: chain?.color ?? "#d1d5db" }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="px-2 py-0.5 rounded-full text-[10px] font-semibold text-white"
          style={{ backgroundColor: chain?.color ?? "#6b7280" }}
        >
          {chain?.displayName ?? hook.hook.chain}
        </span>
        {hook.hook.verifiedSource && (
          <span className="text-[10px] text-green-600 font-medium">Verified</span>
        )}
        {!hook.hook.verifiedSource && (
          <span className="text-[10px] text-gray-400 font-medium">Unverified</span>
        )}
      </div>

      <h3 className="text-sm font-semibold text-gray-900 leading-tight mb-1 line-clamp-1">
        {hook.hook.name}
      </h3>

      {hook.hook.description && (
        <p className="text-xs text-gray-500 leading-relaxed mb-3 line-clamp-2">
          {hook.hook.description}
        </p>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] text-gray-400">
          {activeFlags} flag{activeFlags !== 1 ? "s" : ""}
        </span>
        {hook.properties.dynamicFee && (
          <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 text-[10px] font-medium">
            dynamicFee
          </span>
        )}
        {hook.properties.upgradeable && (
          <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 text-[10px] font-medium">
            upgradeable
          </span>
        )}
        {hook.properties.requiresCustomSwapData && (
          <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 text-[10px] font-medium">
            customSwapData
          </span>
        )}
      </div>
    </button>
  );
}
```

**Step 2: Create HookGrid.tsx**

```tsx
import type { HookEntry } from "../types";
import { HookCard } from "./HookCard";

interface Props {
  hooks: HookEntry[];
  onSelect: (hook: HookEntry) => void;
}

export function HookGrid({ hooks, onSelect }: Props) {
  if (hooks.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-8 text-center">
        No hooks match your filters.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {hooks.map((hook) => (
        <HookCard
          key={`${hook.hook.chain}-${hook.hook.address}`}
          hook={hook}
          onClick={() => onSelect(hook)}
        />
      ))}
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add site/src/components/HookCard.tsx site/src/components/HookGrid.tsx
git commit -m "feat(site): add HookCard and HookGrid components"
```

---

### Task 7: Build HookDetail modal

**Files:**
- Create: `site/src/components/HookDetail.tsx`

**Step 1: Create HookDetail.tsx**

This is a slide-over panel from the right. It shows the full hook details including all 14 flags.

```tsx
import { useEffect } from "react";
import type { HookEntry, FlagName } from "../types";
import { FLAG_NAMES } from "../types";
import { CHAINS, getExplorerUrl } from "../utils/chains";

interface Props {
  hook: HookEntry;
  onClose: () => void;
}

function truncateAddress(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

export function HookDetail({ hook, onClose }: Props) {
  const chain = CHAINS[hook.hook.chain];
  const explorerUrl = getExplorerUrl(hook.hook.chain, hook.hook.address);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-full max-w-md bg-white shadow-xl overflow-y-auto">
        <div className="p-6">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 text-lg cursor-pointer"
          >
            &times;
          </button>

          {/* Chain badge */}
          <span
            className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold text-white mb-3"
            style={{ backgroundColor: chain?.color ?? "#6b7280" }}
          >
            {chain?.displayName ?? hook.hook.chain}
          </span>

          {/* Name */}
          <h2 className="text-lg font-bold text-gray-900 mb-2">{hook.hook.name}</h2>

          {/* Description */}
          {hook.hook.description && (
            <p className="text-sm text-gray-600 leading-relaxed mb-4">
              {hook.hook.description}
            </p>
          )}

          {/* Address */}
          <div className="mb-4">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
              Address
            </h3>
            <div className="flex items-center gap-2">
              <code className="text-sm text-gray-700 bg-gray-50 px-2 py-1 rounded">
                {truncateAddress(hook.hook.address)}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(hook.hook.address)}
                className="text-xs text-pink-600 hover:text-pink-700 cursor-pointer"
              >
                Copy
              </button>
              <a
                href={explorerUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-pink-600 hover:text-pink-700"
              >
                Explorer
              </a>
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-3 mb-6 text-sm">
            <div>
              <span className="text-xs text-gray-400">Verified</span>
              <p className={hook.hook.verifiedSource ? "text-green-600" : "text-gray-400"}>
                {hook.hook.verifiedSource ? "Yes" : "No"}
              </p>
            </div>
            <div>
              <span className="text-xs text-gray-400">Chain ID</span>
              <p className="text-gray-700">{hook.hook.chainId}</p>
            </div>
            {hook.hook.deployer && (
              <div className="col-span-2">
                <span className="text-xs text-gray-400">Deployer</span>
                <p className="text-gray-700 font-mono text-xs">
                  {truncateAddress(hook.hook.deployer)}
                </p>
              </div>
            )}
            {hook.hook.auditUrl && (
              <div className="col-span-2">
                <span className="text-xs text-gray-400">Audit</span>
                <p>
                  <a
                    href={hook.hook.auditUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-pink-600 hover:text-pink-700 text-xs"
                  >
                    View Audit Report
                  </a>
                </p>
              </div>
            )}
          </div>

          {/* Flags */}
          <div className="mb-6">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Flags
            </h3>
            <div className="grid grid-cols-2 gap-1">
              {FLAG_NAMES.map((flag: FlagName) => (
                <div key={flag} className="flex items-center gap-1.5 py-0.5">
                  <span
                    className={`w-4 h-4 rounded flex items-center justify-center text-[10px] ${
                      hook.flags[flag]
                        ? "bg-green-100 text-green-600"
                        : "bg-gray-100 text-gray-300"
                    }`}
                  >
                    {hook.flags[flag] ? "\u2713" : "\u2717"}
                  </span>
                  <span className="text-xs text-gray-700 font-mono">{flag}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Properties */}
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Properties
            </h3>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs ${hook.properties.dynamicFee ? "text-blue-600" : "text-gray-400"}`}
                >
                  {hook.properties.dynamicFee ? "\u2713" : "\u2717"} dynamicFee
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs ${hook.properties.upgradeable ? "text-amber-600" : "text-gray-400"}`}
                >
                  {hook.properties.upgradeable ? "\u2713" : "\u2717"} upgradeable
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs ${hook.properties.requiresCustomSwapData ? "text-purple-600" : "text-gray-400"}`}
                >
                  {hook.properties.requiresCustomSwapData ? "\u2713" : "\u2717"}{" "}
                  requiresCustomSwapData
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add site/src/components/HookDetail.tsx
git commit -m "feat(site): add HookDetail slide-over modal"
```

---

### Task 8: Build the full App layout (hero + filter sidebar + grid)

**Files:**
- Modify: `site/src/App.tsx`

**Step 1: Wire everything together in App.tsx**

Replace `site/src/App.tsx`:

```tsx
import { useState } from "react";
import { Header } from "./components/Header";
import { SearchBar } from "./components/SearchBar";
import { ChainFilter } from "./components/ChainFilter";
import { FlagFilter } from "./components/FlagFilter";
import { PropertyFilter } from "./components/PropertyFilter";
import { HookGrid } from "./components/HookGrid";
import { HookDetail } from "./components/HookDetail";
import { useHooks } from "./hooks/useHooks";
import type { HookEntry } from "./types";

function App() {
  const { hooks, totalCount, loading, error, filters, setFilters, availableChains } =
    useHooks();
  const [selected, setSelected] = useState<HookEntry | null>(null);

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Header />

      <div className="flex flex-col lg:flex-row">
        {/* Left: Hero + Filters */}
        <aside className="lg:w-80 xl:w-96 lg:min-h-[calc(100vh-57px)] lg:border-r border-gray-200 p-6 flex-shrink-0">
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight mb-2">
              Uniswap v4 Hook Registry
            </h1>
            <p className="text-sm text-gray-500 leading-relaxed mb-4">
              Browse {totalCount} hook deployments across {availableChains.length} chains.
              Filter by chain, flags, and properties to find the hooks you need.
            </p>
            <div className="flex flex-col gap-1 text-sm">
              <a
                href="https://github.com/uniswapfoundation/hooklist/issues/new"
                target="_blank"
                rel="noopener noreferrer"
                className="text-pink-600 hover:text-pink-700"
              >
                &rarr; Submit a hook
              </a>
              <a
                href="https://github.com/uniswapfoundation/hooklist"
                target="_blank"
                rel="noopener noreferrer"
                className="text-pink-600 hover:text-pink-700"
              >
                &rarr; GitHub
              </a>
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <SearchBar
                value={filters.search}
                onChange={(search) => setFilters((f) => ({ ...f, search }))}
              />
            </div>

            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Chains
              </h3>
              <ChainFilter
                available={availableChains}
                selected={filters.chains}
                onChange={(chains) => setFilters((f) => ({ ...f, chains }))}
              />
            </div>

            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Flags
              </h3>
              <FlagFilter
                selected={filters.flags}
                onChange={(flags) => setFilters((f) => ({ ...f, flags }))}
              />
            </div>

            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Properties
              </h3>
              <PropertyFilter
                selected={filters.properties}
                onChange={(properties) => setFilters((f) => ({ ...f, properties }))}
              />
            </div>
          </div>
        </aside>

        {/* Right: Results */}
        <main className="flex-1 p-6">
          {loading && <p className="text-gray-500 text-sm">Loading hooks...</p>}
          {error && <p className="text-red-500 text-sm">Error: {error}</p>}
          {!loading && !error && (
            <>
              <p className="text-xs text-gray-400 mb-4">
                Showing {hooks.length} of {totalCount} hooks
              </p>
              <HookGrid hooks={hooks} onSelect={setSelected} />
            </>
          )}
        </main>
      </div>

      {/* Detail modal */}
      {selected && <HookDetail hook={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

export default App;
```

**Step 2: Verify in browser**

```bash
cd site && npx vite
```

Expected: Full layout with hero on left, filters below it, card grid on right. Clicking a card opens the detail panel. All filters work. URL updates with filter state.

**Step 3: Commit**

```bash
git add site/src/App.tsx
git commit -m "feat(site): wire up full layout with hero, filters, grid, and detail modal"
```

---

### Task 9: Add Inter font and final styling polish

**Files:**
- Modify: `site/index.html`
- Modify: `site/src/index.css`

**Step 1: Add Inter font via Google Fonts in index.html**

Add to `<head>` of `site/index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

**Step 2: Apply Inter as default font in index.css**

Update `site/src/index.css`:

```css
@import "tailwindcss";

body {
  font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}
```

**Step 3: Verify font loads in browser**

Expected: Text renders in Inter. Check headings and body text are crisp.

**Step 4: Commit**

```bash
git add site/index.html site/src/index.css
git commit -m "feat(site): add Inter font and base styling"
```

---

### Task 10: Add GitHub Pages deployment workflow

**Files:**
- Create: `.github/workflows/deploy-site.yml`

**Step 1: Create the deployment workflow**

Create `.github/workflows/deploy-site.yml`:

```yaml
name: Deploy Site

on:
  push:
    branches: [main]
    paths:
      - 'site/**'
      - 'hooklist.json'

  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: deploy-site
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: site/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: site

      - name: Copy hooklist.json to public/
        run: cp hooklist.json site/public/hooklist.json

      - name: Build
        run: npm run build
        working-directory: site

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**Step 2: Commit**

```bash
git add .github/workflows/deploy-site.yml
git commit -m "ci: add GitHub Pages deployment workflow for site"
```

---

### Task 11: Final verification and cleanup

**Step 1: Full build check**

```bash
cd site && npm run build
```

Expected: Build succeeds, output in `site/dist/`.

**Step 2: Preview production build**

```bash
cd site && npx vite preview
```

Expected: All features work in production build. Check:
- Hooks load and display in grid
- Search filters by name/description
- Chain pills filter correctly
- Flag toggles filter correctly
- Property toggles filter correctly
- Clicking a card opens the detail panel
- Detail shows all 14 flags, address, explorer link
- Copy button works
- URL updates with filter state
- Responsive layout works (narrow browser = stacked layout)

**Step 3: Clean up any unused files**

Check for leftover Vite boilerplate and remove if present.

**Step 4: Final commit**

```bash
git add -A site/
git commit -m "chore(site): final cleanup and build verification"
```
