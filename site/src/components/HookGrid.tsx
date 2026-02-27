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
