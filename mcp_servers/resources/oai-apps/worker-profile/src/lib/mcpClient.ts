import type { WorkerProfile } from "../types";

const FALLBACK_WORKER: WorkerProfile = {
  workdayId: "demo-0001",
  workerId: "21482",
  name: "Siva Vasireddy",
  email: "demo.user@contoso.com",
  workerType: "Employee",
  businessTitle: "System Administrator",
  location: "Boston",
  locationId: "BOS",
  country: "United States of America",
  countryCode: "USA",
  supervisoryOrganization: "Global Modern Services",
  jobType: "Primary",
  jobProfile: "System Administrator",
  primaryJobId: "P-00733",
  primaryJobDescriptor: "System Administrator"
};

type AiToolResult = {
  structuredContent?: Record<string, unknown>;
  result?: unknown;
  content?: Array<{ type?: string; text?: string }>;
};

declare global {
  interface Window {
    ai?: {
      tools?: {
        call: (options: { server: string; tool: string; arguments?: Record<string, unknown> }) => Promise<AiToolResult>;
      };
    };
  }
}

const MIME_JSON = ["application/json", "text/json"];

const tryParseJson = (input: string): unknown => {
  try {
    return JSON.parse(input);
  } catch (error) {
    console.warn("Unable to parse tool response as JSON", error);
    return null;
  }
};

const coerceWorkerProfile = (payload: unknown): WorkerProfile => {
  if (payload && typeof payload === "object") {
    const data = payload as Record<string, unknown>;
    return {
      workdayId: String(data.workdayId ?? data.id ?? FALLBACK_WORKER.workdayId),
      workerId: String(data.workerId ?? FALLBACK_WORKER.workerId),
      name: String(data.name ?? "Unknown worker"),
      email: String(data.email ?? ""),
      workerType: String(data.workerType ?? "Unknown"),
      businessTitle: String(data.businessTitle ?? ""),
      location: String(data.location ?? ""),
      locationId: String(data.locationId ?? ""),
      country: String(data.country ?? ""),
      countryCode: String(data.countryCode ?? ""),
      supervisoryOrganization: String(data.supervisoryOrganization ?? ""),
      jobType: String(data.jobType ?? ""),
      jobProfile: String(data.jobProfile ?? ""),
      primaryJobId: String(data.primaryJobId ?? ""),
      primaryJobDescriptor: String(data.primaryJobDescriptor ?? ""),
    };
  }

  return FALLBACK_WORKER;
};

const extractFromContentBlocks = (content?: AiToolResult["content"]): WorkerProfile | null => {
  if (!content) {
    return null;
  }

  for (const block of content) {
    if (!block?.text) {
      continue;
    }
    const maybeProfile = tryParseJson(block.text);
    if (maybeProfile) {
      return coerceWorkerProfile(maybeProfile);
    }
  }

  return null;
};

const invokeMcp = async (): Promise<WorkerProfile | null> => {
  const bridge = window.ai;
  if (!bridge?.tools?.call) {
    return null;
  }

  const response = await bridge.tools.call({
    server: "workday",
    tool: "get_worker",
    arguments: {}
  });

  if (response?.structuredContent?.result) {
    return coerceWorkerProfile(response.structuredContent.result);
  }

  if (response?.result) {
    return coerceWorkerProfile(response.result);
  }

  return extractFromContentBlocks(response?.content);
};

export const fetchWorkerProfile = async (_signal?: AbortSignal): Promise<WorkerProfile> => {
  const worker = await invokeMcp();
  return worker ?? FALLBACK_WORKER;
};
