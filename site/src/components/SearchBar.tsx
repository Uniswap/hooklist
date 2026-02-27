interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: Props) {
  return (
    <div className="relative">
      <svg
        className="absolute left-3.5 top-1/2 -translate-y-1/2 text-uni-text-tertiary"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search hooks..."
        className="w-full pl-10 pr-4 py-2.5 rounded-2xl glass text-sm placeholder:text-uni-text-tertiary focus:outline-none focus:ring-2 focus:ring-uni-pink/30 focus:border-uni-pink/40 transition-all"
      />
    </div>
  );
}
