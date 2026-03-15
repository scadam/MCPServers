import type { IncidentFormData, IncidentCreatedResult } from "../types";

type AiToolResult = {
  structuredContent?: Record<string, unknown>;
  result?: unknown;
  content?: Array<{ type?: string; text?: string }>;
};

declare global {
  interface Window {
    ai?: {
      tools?: {
        call: (options: {
          server: string;
          tool: string;
          arguments?: Record<string, unknown>;
        }) => Promise<AiToolResult>;
      };
    };
  }
}

const tryParseJson = (input: string): unknown => {
  try {
    return JSON.parse(input);
  } catch {
    return null;
  }
};

const coerceResult = (payload: unknown): IncidentCreatedResult => {
  if (payload && typeof payload === "object") {
    return payload as IncidentCreatedResult;
  }
  return { created: false };
};

const extractFromContent = (
  content?: AiToolResult["content"]
): IncidentCreatedResult | null => {
  if (!content) return null;
  for (const block of content) {
    if (!block?.text) continue;
    const parsed = tryParseJson(block.text);
    if (parsed) return coerceResult(parsed);
  }
  return null;
};

/**
 * Submit the incident creation form by calling the MCP tool.
 * Strips empty optional fields so the API only receives populated values.
 */
export const submitIncident = async (
  form: IncidentFormData
): Promise<IncidentCreatedResult> => {
  // Strip empty string values — only send fields the user/LLM populated
  const args: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(form)) {
    if (value !== undefined && value !== "") {
      args[key] = value;
    }
  }

  const bridge = window.ai;
  if (!bridge?.tools?.call) {
    throw new Error(
      "OpenAI Apps bridge not available. Run this app inside an AI host."
    );
  }

  const response = await bridge.tools.call({
    server: "servicenow",
    tool: "create_incident",
    arguments: args,
  });

  if (response?.structuredContent?.result) {
    return coerceResult(response.structuredContent.result);
  }
  if (response?.result) {
    return coerceResult(response.result);
  }
  const fromContent = extractFromContent(response?.content);
  if (fromContent) return fromContent;

  return { created: false };
};
