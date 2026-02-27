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
    <div className="min-h-screen bg-uni-bg text-uni-text relative overflow-x-hidden">
      {/* Floating gradient orbs */}
      <div className="orb orb-pink" />
      <div className="orb orb-blue" />
      <div className="orb orb-magenta" />

      <div className="relative z-10">
        <Header />

        <div className="flex flex-col lg:flex-row max-w-[1440px] mx-auto">
          {/* Left: Hero + Filters */}
          <aside className="lg:w-80 xl:w-96 lg:min-h-[calc(100vh-52px)] p-6 flex-shrink-0">
            <div className="mb-8">
              <h1 className="text-2xl font-extrabold tracking-tight mb-2 text-uni-text">
                Uniswap v4 Hook Registry
              </h1>
              <p className="text-sm text-uni-text-secondary leading-relaxed mb-4">
                Browse {totalCount} hook deployments across{" "}
                {availableChains.length} chains. Filter by chain, flags, and
                properties to find the hooks you need.
              </p>
              <div className="flex flex-col gap-1 text-sm">
                <a
                  href="https://github.com/uniswap/hooklist/issues/new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-uni-pink-dark hover:text-uni-pink font-semibold transition-colors"
                >
                  &rarr; Submit a hook
                </a>
                <a
                  href="https://github.com/uniswap/hooklist"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-uni-pink-dark hover:text-uni-pink font-semibold transition-colors"
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
                <h3 className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest mb-2">
                  Chains
                </h3>
                <ChainFilter
                  available={availableChains}
                  selected={filters.chains}
                  onChange={(chains) => setFilters((f) => ({ ...f, chains }))}
                />
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest mb-2">
                  Flags
                </h3>
                <FlagFilter
                  selected={filters.flags}
                  onChange={(flags) => setFilters((f) => ({ ...f, flags }))}
                />
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest mb-2">
                  Properties
                </h3>
                <PropertyFilter
                  selected={filters.properties}
                  onChange={(properties) =>
                    setFilters((f) => ({ ...f, properties }))
                  }
                />
              </div>
            </div>
          </aside>

          {/* Right: Results */}
          <main className="flex-1 p-6">
            {loading && (
              <div className="flex items-center justify-center py-16">
                <div className="w-8 h-8 border-3 border-uni-pink/20 border-t-uni-pink rounded-full animate-spin" />
              </div>
            )}
            {error && (
              <p className="text-red-500 text-sm glass rounded-2xl p-4">
                Error: {error}
              </p>
            )}
            {!loading && !error && (
              <>
                <p className="text-xs text-uni-text-tertiary mb-4 font-medium">
                  Showing {hooks.length} of {totalCount} hooks
                </p>
                <HookGrid hooks={hooks} onSelect={setSelected} />
              </>
            )}
          </main>
        </div>
      </div>

      {/* Detail modal */}
      {selected && (
        <HookDetail hook={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

export default App;
