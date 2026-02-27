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
