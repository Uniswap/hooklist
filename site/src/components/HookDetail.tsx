import { useEffect } from "react";
import type { HookEntry, FlagName } from "../types";
import { FLAG_NAMES } from "../types";
import { CHAINS, getExplorerUrl } from "../utils/chains";

interface Props {
  hook: HookEntry;
  onClose: () => void;
}

function truncateAddress(addr: string) {
  return `${addr.slice(0, 6)}\u2026${addr.slice(-4)}`;
}

export function HookDetail({ hook, onClose }: Props) {
  const chain = CHAINS[hook.hook.chain];
  const explorerUrl = getExplorerUrl(hook.hook.chain, hook.hook.address);

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
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-md glass-strong shadow-2xl overflow-y-auto animate-slide-in">
        <div className="p-6">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full flex items-center justify-center text-uni-text-tertiary hover:text-uni-text hover:bg-black/5 transition-all cursor-pointer"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>

          {/* Chain badge */}
          <span
            className="inline-block px-2.5 py-1 rounded-lg text-xs font-bold text-white mb-4 tracking-wide uppercase"
            style={{ backgroundColor: chain?.color ?? "#6b7280" }}
          >
            {chain?.displayName ?? hook.hook.chain}
          </span>

          {/* Name */}
          <h2 className="text-xl font-extrabold text-uni-text mb-2 tracking-tight">
            {hook.hook.name}
          </h2>

          {/* Description */}
          {hook.hook.description && (
            <p className="text-sm text-uni-text-secondary leading-relaxed mb-6">
              {hook.hook.description}
            </p>
          )}

          {/* Address */}
          <div className="mb-6">
            <h3 className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest mb-1.5">
              Address
            </h3>
            <div className="flex items-center gap-2">
              <code className="text-sm text-uni-text font-mono bg-black/5 px-3 py-1.5 rounded-xl">
                {truncateAddress(hook.hook.address)}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(hook.hook.address)}
                className="text-xs font-semibold text-uni-pink hover:text-uni-pink-dark transition-colors cursor-pointer"
              >
                Copy
              </button>
              <a
                href={explorerUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-semibold text-uni-pink hover:text-uni-pink-dark transition-colors"
              >
                Explorer &rarr;
              </a>
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="glass rounded-xl p-3">
              <span className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest">
                Source
              </span>
              <p
                className={`text-sm font-semibold mt-0.5 ${hook.hook.verifiedSource ? "text-emerald-500" : "text-uni-text-tertiary"}`}
              >
                {hook.hook.verifiedSource ? "Verified" : "Unverified"}
              </p>
            </div>
            <div className="glass rounded-xl p-3">
              <span className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest">
                Chain ID
              </span>
              <p className="text-sm font-semibold text-uni-text mt-0.5">
                {hook.hook.chainId}
              </p>
            </div>
            {hook.hook.deployer && (
              <div className="col-span-2 glass rounded-xl p-3">
                <span className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest">
                  Deployer
                </span>
                <p className="text-sm font-mono text-uni-text mt-0.5">
                  {truncateAddress(hook.hook.deployer)}
                </p>
              </div>
            )}
            {hook.hook.auditUrl && (
              <div className="col-span-2 glass rounded-xl p-3">
                <span className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest">
                  Audit
                </span>
                <p className="mt-0.5">
                  <a
                    href={hook.hook.auditUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-uni-pink hover:text-uni-pink-dark transition-colors"
                  >
                    View Report &rarr;
                  </a>
                </p>
              </div>
            )}
          </div>

          {/* Flags */}
          <div className="mb-6">
            <h3 className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest mb-3">
              Flags
            </h3>
            <div className="grid grid-cols-2 gap-1.5">
              {FLAG_NAMES.map((flag: FlagName) => (
                <div
                  key={flag}
                  className={`flex items-center gap-2 py-1.5 px-2.5 rounded-xl text-xs font-mono ${
                    hook.flags[flag]
                      ? "bg-uni-pink/8 text-uni-text"
                      : "text-uni-text-tertiary"
                  }`}
                >
                  <span
                    className={`w-4 h-4 rounded-md flex items-center justify-center text-[10px] font-bold ${
                      hook.flags[flag]
                        ? "bg-uni-pink text-white"
                        : "bg-black/5 text-uni-text-tertiary"
                    }`}
                  >
                    {hook.flags[flag] ? "\u2713" : "\u2717"}
                  </span>
                  {flag}
                </div>
              ))}
            </div>
          </div>

          {/* Properties */}
          <div>
            <h3 className="text-[10px] font-bold text-uni-text-tertiary uppercase tracking-widest mb-3">
              Properties
            </h3>
            <div className="flex flex-col gap-2">
              {(
                [
                  {
                    key: "dynamicFee" as const,
                    label: "Dynamic Fee",
                    color: "#3b82f6",
                  },
                  {
                    key: "upgradeable" as const,
                    label: "Upgradeable",
                    color: "#f59e0b",
                  },
                  {
                    key: "requiresCustomSwapData" as const,
                    label: "Custom Swap Data",
                    color: "#8b5cf6",
                  },
                ] as const
              ).map(({ key, label, color }) => (
                <div
                  key={key}
                  className={`flex items-center gap-2.5 py-1.5 px-3 rounded-xl text-sm font-medium ${
                    hook.properties[key]
                      ? "glass"
                      : "text-uni-text-tertiary"
                  }`}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{
                      backgroundColor: hook.properties[key]
                        ? color
                        : "rgba(0,0,0,0.1)",
                    }}
                  />
                  {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
