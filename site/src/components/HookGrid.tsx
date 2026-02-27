import type { HookEntry } from "../types";
import { HookCard } from "./HookCard";

interface Props {
  hooks: HookEntry[];
  onSelect: (hook: HookEntry) => void;
}

export function HookGrid({ hooks, onSelect }: Props) {
  if (hooks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-uni-text-tertiary mb-3"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <p className="text-sm text-uni-text-tertiary font-medium">
          No hooks match your filters.
        </p>
      </div>
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
