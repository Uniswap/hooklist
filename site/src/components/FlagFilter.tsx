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
            className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-medium transition-all cursor-pointer ${
              active
                ? "bg-uni-pink text-white shadow-sm"
                : "glass text-uni-text-secondary hover:text-uni-text hover:bg-uni-surface-hover"
            }`}
            style={
              active
                ? { boxShadow: "0 2px 10px rgba(252, 114, 255, 0.35)" }
                : undefined
            }
          >
            {LABELS[flag]}
          </button>
        );
      })}
    </div>
  );
}
