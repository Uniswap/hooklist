export function Header() {
  return (
    <header className="sticky top-0 z-40 glass-strong">
      <div className="flex items-center justify-between px-6 py-3 max-w-[1440px] mx-auto">
        <div className="flex items-center gap-2.5">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="url(#hk-grad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 9v6a5 5 0 0 1 -10 0v-4l3 3" />
            <path d="M14 7a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
            <path d="M16 5v-2" />
            <defs>
              <linearGradient id="hk-grad" x1="6" y1="2" x2="20" y2="20" gradientUnits="userSpaceOnUse">
                <stop stopColor="#fc72ff" />
                <stop offset="1" stopColor="#ff007a" />
              </linearGradient>
            </defs>
          </svg>
          <span className="text-lg font-extrabold tracking-tight text-uni-text">
            Hooklist
          </span>
        </div>
        <a
          href="https://github.com/uniswap/hooklist"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium text-uni-text-secondary hover:text-uni-text hover:bg-black/5 transition-all"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          GitHub
        </a>
      </div>
    </header>
  );
}
