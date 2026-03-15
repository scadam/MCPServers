import { useWorkerProfile } from "./hooks/useWorkerProfile";
import { WorkerProfileCard } from "./components/WorkerProfileCard";
import "./App.css";

function App() {
  const { data, isLoading, error, refetch, isFetching } = useWorkerProfile();

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">Workday</p>
          <h1>Worker profile</h1>
          <p>
            This OpenAI App calls the <code>workday/get_worker</code> tool and renders the signed-in worker's profile.
            Use the refresh button to re-run the tool with the current MCP session headers.
          </p>
        </div>
        <button onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "Refreshing…" : "Refresh data"}
        </button>
      </header>

      {isLoading && <div className="loading">Loading worker details…</div>}
      {error && (
        <div role="alert" className="error">
          {error.message || "Unable to load worker details"}
        </div>
      )}
      {!isLoading && !error && !data && <div className="empty-state">No worker details returned.</div>}
      {data && <WorkerProfileCard worker={data} />}

      <footer>
        Powered by <span>workday/get_worker</span> via MCP.
      </footer>
    </main>
  );
}

export default App;
