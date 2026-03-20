import { PROPERTY_NAMES, type PropertyName } from "../types";

interface Props {
  selected: PropertyName[];
  onChange: (properties: PropertyName[]) => void;
}

const LABELS: Record<PropertyName, string> = {
  dynamicFee: "Dynamic Fee",
  upgradeable: "Upgradeable",
  requiresCustomSwapData: "Custom Swap Data",
  vanillaSwap: "Vanilla Swap",
};

const COLORS: Record<PropertyName, { bg: string; shadow: string }> = {
  dynamicFee: { bg: "#3b82f6", shadow: "rgba(59, 130, 246, 0.35)" },
  upgradeable: { bg: "#f59e0b", shadow: "rgba(245, 158, 11, 0.35)" },
  requiresCustomSwapData: { bg: "#8b5cf6", shadow: "rgba(139, 92, 246, 0.35)" },
  vanillaSwap: { bg: "#10b981", shadow: "rgba(16, 185, 129, 0.35)" },
};

export function PropertyFilter({ selected, onChange }: Props) {
  function toggle(prop: PropertyName) {
    if (selected.includes(prop)) {
      onChange(selected.filter((p) => p !== prop));
    } else {
      onChange([...selected, prop]);
    }
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {PROPERTY_NAMES.map((prop) => {
        const active = selected.includes(prop);
        const color = COLORS[prop];
        return (
          <button
            key={prop}
            onClick={() => toggle(prop)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              active
                ? "text-white shadow-md"
                : "glass text-uni-text-secondary hover:text-uni-text hover:bg-uni-surface-hover"
            }`}
            style={
              active
                ? {
                    background: color.bg,
                    boxShadow: `0 4px 14px ${color.shadow}`,
                  }
                : undefined
            }
          >
            {LABELS[prop]}
          </button>
        );
      })}
    </div>
  );
}
