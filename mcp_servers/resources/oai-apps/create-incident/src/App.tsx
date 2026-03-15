import { useState } from "react";
import { IncidentForm } from "./components/IncidentForm";
import { IncidentSuccess } from "./components/IncidentSuccess";
import { submitIncident } from "./lib/mcpClient";
import type { IncidentFormData, IncidentCreatedResult } from "./types";
import "./App.css";

/**
 * Parse pre-populated field values from the URL query string.
 * The LLM-driven host can open this app with e.g.
 *   ?short_description=Cannot+login&category=software&urgency=2
 * and the form will be pre-filled.
 */
const parseInitialValues = (): Partial<IncidentFormData> => {
  const params = new URLSearchParams(window.location.search);
  const initial: Record<string, string> = {};
  for (const [key, value] of params.entries()) {
    if (value) initial[key] = value;
  }
  return initial as Partial<IncidentFormData>;
};

function App() {
  const [result, setResult] = useState<IncidentCreatedResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const initial = parseInitialValues();

  const handleSubmit = async (data: IncidentFormData) => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitIncident(data);
      if (res.created) {
        setResult(res);
      } else {
        setError("The incident could not be created. Please try again.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">ServiceNow</p>
          <h1>Create incident</h1>
          <p>
            Fill in the details below to create a new incident. The
            service-desk section can be expanded for additional fields.
          </p>
        </div>
      </header>

      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}

      {result ? (
        <>
          <IncidentSuccess result={result} />
          <div className="actions" style={{ marginTop: "1rem" }}>
            <button onClick={handleReset}>Create another</button>
          </div>
        </>
      ) : (
        <IncidentForm
          initial={initial}
          onSubmit={handleSubmit}
          submitting={submitting}
        />
      )}

      <footer>
        Powered by <span>servicenow/create_incident</span> via MCP.
      </footer>
    </main>
  );
}

export default App;
