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
    <div className="flex flex-wrap gap-1.5">
      {available.map((chain) => {
        const active = selected.includes(chain);
        const info = CHAINS[chain];
        return (
          <button
            key={chain}
            onClick={() => toggle(chain)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              active
                ? "text-white shadow-md"
                : "glass text-uni-text-secondary hover:text-uni-text hover:bg-uni-surface-hover"
            }`}
            style={
              active
                ? {
                    background: info?.color ?? "#6b7280",
                    boxShadow: `0 4px 14px ${info?.color ?? "#6b7280"}40`,
                  }
                : undefined
            }
          >
            {info?.displayName ?? chain}
          </button>
        );
      })}
    </div>
  );
}
