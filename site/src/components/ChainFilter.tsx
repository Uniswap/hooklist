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
