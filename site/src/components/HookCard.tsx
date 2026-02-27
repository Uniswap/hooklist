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
      className="text-left w-full p-4 rounded-2xl glass hover:bg-uni-surface-hover hover:shadow-lg transition-all cursor-pointer group"
    >
      <div className="flex items-center gap-2 mb-2.5">
        <span
          className="px-2 py-0.5 rounded-lg text-[10px] font-bold text-white tracking-wide uppercase"
          style={{ backgroundColor: chain?.color ?? "#6b7280" }}
        >
          {chain?.displayName ?? hook.hook.chain}
        </span>
        {hook.hook.verifiedSource ? (
          <span className="flex items-center gap-0.5 text-[10px] text-emerald-500 font-semibold">
            <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0zm3.78 4.97a.75.75 0 0 0-1.06 0L7 8.69 5.28 6.97a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.06 0l4.25-4.25a.75.75 0 0 0 0-1.06z" />
            </svg>
            Verified
          </span>
        ) : (
          <span className="text-[10px] text-uni-text-tertiary font-medium">
            Unverified
          </span>
        )}
      </div>

      <h3 className="text-sm font-bold text-uni-text leading-tight mb-1 line-clamp-1 group-hover:text-uni-pink-dark transition-colors">
        {hook.hook.name}
      </h3>

      {hook.hook.description && (
        <p className="text-xs text-uni-text-secondary leading-relaxed mb-3 line-clamp-2">
          {hook.hook.description}
        </p>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] text-uni-text-tertiary font-medium">
          {activeFlags} flag{activeFlags !== 1 ? "s" : ""}
        </span>
        {hook.properties.dynamicFee && (
          <span className="px-1.5 py-0.5 rounded-md bg-blue-500/10 text-blue-600 text-[10px] font-semibold">
            dynamicFee
          </span>
        )}
        {hook.properties.upgradeable && (
          <span className="px-1.5 py-0.5 rounded-md bg-amber-500/10 text-amber-600 text-[10px] font-semibold">
            upgradeable
          </span>
        )}
        {hook.properties.requiresCustomSwapData && (
          <span className="px-1.5 py-0.5 rounded-md bg-purple-500/10 text-purple-600 text-[10px] font-semibold">
            customSwapData
          </span>
        )}
      </div>
    </button>
  );
}
