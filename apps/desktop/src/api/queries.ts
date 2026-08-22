import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Approval, Bot, Task } from "@superbot/contracts";

import type { ApiClient } from "./client";

export interface CatalogModel {
  id: string;
  display_name: string;
  provider: string;
  capability: {
    vision: boolean;
    tool_calling: boolean;
    structured_output: boolean;
    thinking: boolean;
    context_window: number;
  };
}

export const queryKeys = {
  bots: ["bots"] as const,
  approvals: ["approvals"] as const,
  models: ["models"] as const,
  routines: ["routines"] as const,
  workers: ["workers"] as const,
};

export function useBots(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.bots, queryFn: ({ signal }) => client.get<Bot[]>("/bots", { signal }) });
}

export function useApprovals(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.approvals, queryFn: ({ signal }) => client.get<Approval[]>("/approvals", { signal }) });
}

export function useModels(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.models, queryFn: ({ signal }) => client.get<CatalogModel[]>("/models", { signal }), staleTime: 5 * 60_000 });
}

export function useRoutines(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.routines, queryFn: ({ signal }) => client.get<Record<string, unknown>[]>("/routines", { signal }) });
}

export function useWorkers(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.workers, queryFn: ({ signal }) => client.get<Record<string, unknown>[]>("/workers", { signal }), refetchInterval: 10_000 });
}

export function useSendMessage(client: ApiClient, botId: string | undefined) {
  return useMutation({
    mutationFn: ({ content, idempotencyKey }: { content: string; idempotencyKey: string }) => {
      if (!botId) throw new Error("请先选择 Bot");
      return client.post<Task>(`/bots/${botId}/messages`, { content }, { idempotencyKey });
    },
  });
}

export function useApprovalDecision(client: ApiClient) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "approved" | "denied" }) =>
      client.post<Approval>(`/approvals/${id}/decision`, { decision, decided_by: "desktop-user" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.approvals }),
  });
}
