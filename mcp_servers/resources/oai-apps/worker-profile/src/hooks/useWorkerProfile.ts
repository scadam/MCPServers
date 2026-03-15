import { useQuery } from "@tanstack/react-query";
import { fetchWorkerProfile } from "../lib/mcpClient";
import type { WorkerProfile } from "../types";

export const useWorkerProfile = () =>
  useQuery<WorkerProfile, Error>({
    queryKey: ["worker-profile"],
    queryFn: async ({ signal }) => fetchWorkerProfile(signal),
    refetchOnWindowFocus: false,
    retry: 1
  });
