export function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
      <div className="flex items-center gap-2">
        <span className="text-xl font-bold tracking-tight">Hooklist</span>
      </div>
      <a
        href="https://github.com/uniswapfoundation/hooklist"
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
      >
        GitHub
      </a>
    </header>
  );
}
