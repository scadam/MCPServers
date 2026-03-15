import { useState } from "react";
import type { IncidentFormData } from "../types";
import {
  CATEGORIES,
  URGENCY_OPTIONS,
  IMPACT_OPTIONS,
  CONTACT_TYPES,
} from "../types";

interface Props {
  /** Pre-populated values from the LLM / conversation context. */
  initial?: Partial<IncidentFormData>;
  /** Called when the user clicks Submit. */
  onSubmit: (data: IncidentFormData) => void;
  /** True while the MCP call is in flight. */
  submitting?: boolean;
}

/* ── Tiny helpers ─────────────────────────────────────────────── */

const Select = ({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: ReadonlyArray<{ value: string; label: string }>;
}) => (
  <div className="field">
    <label htmlFor={id}>{label}</label>
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  </div>
);

const Input = ({
  id,
  label,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) => (
  <div className="field">
    <label htmlFor={id}>{label}</label>
    <input
      id={id}
      type="text"
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  </div>
);

const TextArea = ({
  id,
  label,
  value,
  onChange,
  placeholder,
  rows,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) => (
  <div className="field full-width">
    <label htmlFor={id}>{label}</label>
    <textarea
      id={id}
      value={value}
      rows={rows ?? 3}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  </div>
);

/* ── Form component ──────────────────────────────────────────── */

export const IncidentForm = ({ initial = {}, onSubmit, submitting }: Props) => {
  const [shortDesc, setShortDesc] = useState(initial.short_description ?? "");
  const [description, setDescription] = useState(initial.description ?? "");
  const [category, setCategory] = useState(initial.category ?? "");
  const [subcategory, setSubcategory] = useState(initial.subcategory ?? "");
  const [urgency, setUrgency] = useState(initial.urgency ?? "");
  const [caller, setCaller] = useState(initial.caller ?? "");
  const [comments, setComments] = useState(initial.comments ?? "");

  // Service-desk expansion
  const [impact, setImpact] = useState(initial.impact ?? "");
  const [assignmentGroup, setAssignmentGroup] = useState(
    initial.assignment_group ?? ""
  );
  const [assignedTo, setAssignedTo] = useState(initial.assigned_to ?? "");
  const [contactType, setContactType] = useState(initial.contact_type ?? "");
  const [service, setService] = useState(initial.service ?? "");
  const [serviceOffering, setServiceOffering] = useState(
    initial.service_offering ?? ""
  );
  const [configItem, setConfigItem] = useState(
    initial.configuration_item ?? ""
  );

  const [expanded, setExpanded] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      short_description: shortDesc,
      caller: caller,
      description: description || undefined,
      category: category || undefined,
      subcategory: subcategory || undefined,
      urgency: urgency || undefined,
      comments: comments || undefined,
      impact: impact || undefined,
      assignment_group: assignmentGroup || undefined,
      assigned_to: assignedTo || undefined,
      contact_type: contactType || undefined,
      service: service || undefined,
      service_offering: serviceOffering || undefined,
      configuration_item: configItem || undefined,
    });
  };

  return (
    <form className="incident-form" onSubmit={handleSubmit}>
      {/* ── Self-service section ─────────────────────────── */}
      <fieldset>
        <legend>Incident details</legend>

        <div className="form-grid two-col">
          <Input
            id="caller"
            label="Caller *"
            value={caller}
            onChange={setCaller}
            placeholder="e.g. System Administrator"
          />
          <Select
            id="urgency"
            label="Urgency"
            value={urgency}
            onChange={setUrgency}
            options={[...URGENCY_OPTIONS]}
          />
          <Select
            id="category"
            label="Category"
            value={category}
            onChange={setCategory}
            options={[...CATEGORIES]}
          />
          <Input
            id="subcategory"
            label="Subcategory"
            value={subcategory}
            onChange={setSubcategory}
          />
        </div>

        <TextArea
          id="short_description"
          label="Short description *"
          value={shortDesc}
          onChange={setShortDesc}
          placeholder="Brief summary of the issue"
          rows={1}
        />

        <TextArea
          id="description"
          label="Description"
          value={description}
          onChange={setDescription}
          placeholder="Provide more detail about the issue"
          rows={3}
        />

        <TextArea
          id="comments"
          label="Comments (Customer visible)"
          value={comments}
          onChange={setComments}
          rows={2}
        />
      </fieldset>

      {/* ── Service-desk expansion ───────────────────────── */}
      <details
        className="service-desk"
        open={expanded}
        onToggle={(e) =>
          setExpanded((e.target as HTMLDetailsElement).open)
        }
      >
        <summary>Service Desk fields</summary>
        <fieldset>
          <div className="form-grid two-col">
            <Select
              id="impact"
              label="Impact"
              value={impact}
              onChange={setImpact}
              options={[...IMPACT_OPTIONS]}
            />
            <Select
              id="contact_type"
              label="Channel"
              value={contactType}
              onChange={setContactType}
              options={[...CONTACT_TYPES]}
            />
            <Input
              id="assignment_group"
              label="Assignment group"
              value={assignmentGroup}
              onChange={setAssignmentGroup}
            />
            <Input
              id="assigned_to"
              label="Assigned to"
              value={assignedTo}
              onChange={setAssignedTo}
            />
            <Input
              id="service"
              label="Service"
              value={service}
              onChange={setService}
            />
            <Input
              id="service_offering"
              label="Service offering"
              value={serviceOffering}
              onChange={setServiceOffering}
            />
            <Input
              id="configuration_item"
              label="Configuration item"
              value={configItem}
              onChange={setConfigItem}
            />
          </div>
        </fieldset>
      </details>

      <div className="actions">
        <button type="submit" disabled={!shortDesc.trim() || !caller.trim() || submitting}>
          {submitting ? "Creating…" : "Submit"}
        </button>
      </div>
    </form>
  );
};
