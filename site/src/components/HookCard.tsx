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
