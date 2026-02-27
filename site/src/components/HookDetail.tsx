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
