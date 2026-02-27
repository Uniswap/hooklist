import { Header } from "./components/Header";
import { useHooks } from "./hooks/useHooks";

function App() {
  const { hooks, totalCount, loading, error } = useHooks();

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Header />
      <main className="p-8">
        {loading && <p className="text-gray-500">Loading hooks...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        {!loading && !error && (
          <p className="text-gray-500">
            {hooks.length} of {totalCount} hooks
          </p>
        )}
      </main>
    </div>
  );
}

export default App;
