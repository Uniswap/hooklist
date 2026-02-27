import { PROPERTY_NAMES, type PropertyName } from "../types";

interface Props {
  selected: PropertyName[];
  onChange: (properties: PropertyName[]) => void;
}

const LABELS: Record<PropertyName, string> = {
  dynamicFee: "Dynamic Fee",
  upgradeable: "Upgradeable",
  requiresCustomSwapData: "Custom Swap Data",
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
    <div className="flex flex-wrap gap-2">
      {PROPERTY_NAMES.map((prop) => {
        const active = selected.includes(prop);
        return (
          <button
            key={prop}
            onClick={() => toggle(prop)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
              active
                ? "bg-pink-600 text-white border-pink-600"
                : "text-gray-600 border-gray-300 hover:border-gray-400"
            }`}
          >
            {LABELS[prop]}
          </button>
        );
      })}
    </div>
  );
}
