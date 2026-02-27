import { FLAG_NAMES, type FlagName } from "../types";

interface Props {
  selected: FlagName[];
  onChange: (flags: FlagName[]) => void;
}

const LABELS: Record<FlagName, string> = {
  beforeInitialize: "beforeInitialize",
  afterInitialize: "afterInitialize",
  beforeAddLiquidity: "beforeAddLiquidity",
  afterAddLiquidity: "afterAddLiquidity",
  beforeRemoveLiquidity: "beforeRemoveLiquidity",
  afterRemoveLiquidity: "afterRemoveLiquidity",
  beforeSwap: "beforeSwap",
  afterSwap: "afterSwap",
  beforeDonate: "beforeDonate",
  afterDonate: "afterDonate",
  beforeSwapReturnsDelta: "beforeSwapReturnsDelta",
  afterSwapReturnsDelta: "afterSwapReturnsDelta",
  afterAddLiquidityReturnsDelta: "afterAddLiqReturnsDelta",
  afterRemoveLiquidityReturnsDelta: "afterRemLiqReturnsDelta",
};

export function FlagFilter({ selected, onChange }: Props) {
  function toggle(flag: FlagName) {
    if (selected.includes(flag)) {
      onChange(selected.filter((f) => f !== flag));
    } else {
      onChange([...selected, flag]);
    }
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {FLAG_NAMES.map((flag) => {
        const active = selected.includes(flag);
        return (
          <button
            key={flag}
            onClick={() => toggle(flag)}
            className={`px-2 py-0.5 rounded text-xs font-mono transition-colors cursor-pointer ${
              active
                ? "bg-pink-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {LABELS[flag]}
          </button>
        );
      })}
    </div>
  );
}
