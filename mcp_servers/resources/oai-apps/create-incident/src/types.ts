/** Fields for incident creation — self-service subset + service-desk expansion. */
export interface IncidentFormData {
  // ── Self-service fields ──────────────────────
  short_description: string;
  caller: string;
  description?: string;
  category?: string;
  subcategory?: string;
  urgency?: string;
  comments?: string;

  // ── Service-desk fields ──────────────────────
  impact?: string;
  assignment_group?: string;
  assigned_to?: string;
  contact_type?: string;
  service?: string;
  service_offering?: string;
  configuration_item?: string;
}

/** Concise response from the create_incident MCP tool. */
export interface IncidentCreatedResult {
  created: boolean;
  number?: string;
  sys_id?: string;
  short_description?: string;
  caller?: string;
  state?: string;
  priority?: string;
  urgency?: string;
  impact?: string;
  category?: string;
  assigned_to?: string;
  assignment_group?: string;
  opened_at?: string;
  link?: string;
}

/** The default categories available in ServiceNow. */
export const CATEGORIES = [
  { value: "", label: "-- None --" },
  { value: "inquiry", label: "Inquiry / Help" },
  { value: "software", label: "Software" },
  { value: "hardware", label: "Hardware" },
  { value: "network", label: "Network" },
  { value: "database", label: "Database" },
] as const;

export const URGENCY_OPTIONS = [
  { value: "", label: "-- Default --" },
  { value: "1", label: "1 - High" },
  { value: "2", label: "2 - Medium" },
  { value: "3", label: "3 - Low" },
] as const;

export const IMPACT_OPTIONS = [
  { value: "", label: "-- Default --" },
  { value: "1", label: "1 - High" },
  { value: "2", label: "2 - Medium" },
  { value: "3", label: "3 - Low" },
] as const;

export const CONTACT_TYPES = [
  { value: "", label: "-- None --" },
  { value: "phone", label: "Phone" },
  { value: "email", label: "Email" },
  { value: "self-service", label: "Self-service" },
  { value: "walk-in", label: "Walk-in" },
] as const;
