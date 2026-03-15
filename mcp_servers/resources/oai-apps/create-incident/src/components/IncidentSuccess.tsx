import type { IncidentCreatedResult } from "../types";

export const IncidentSuccess = ({
  result,
}: {
  result: IncidentCreatedResult;
}) => (
  <article className="success-card">
    <div className="check-icon" aria-hidden>
      ✓
    </div>
    <h2>Incident created</h2>
    <p className="incident-number">{result.number}</p>

    <div className="summary-grid">
      {result.short_description && (
        <SummaryField label="Summary" value={result.short_description} />
      )}
      {result.category && (
        <SummaryField label="Category" value={result.category} />
      )}
      {result.priority && (
        <SummaryField label="Priority" value={result.priority} />
      )}
      {result.urgency && (
        <SummaryField label="Urgency" value={result.urgency} />
      )}
      {result.impact && (
        <SummaryField label="Impact" value={result.impact} />
      )}
      {result.state && <SummaryField label="State" value={result.state} />}
      {result.assigned_to && (
        <SummaryField label="Assigned to" value={result.assigned_to} />
      )}
      {result.assignment_group && (
        <SummaryField label="Assignment group" value={result.assignment_group} />
      )}
      {result.opened_at && (
        <SummaryField label="Opened" value={result.opened_at} />
      )}
    </div>

    {result.link && (
      <a href={result.link} target="_blank" rel="noopener noreferrer" className="sn-link">
        Open in ServiceNow ↗
      </a>
    )}
  </article>
);

const SummaryField = ({ label, value }: { label: string; value: string }) => (
  <div className="summary-field">
    <span className="label">{label}</span>
    <span className="value">{value}</span>
  </div>
);
