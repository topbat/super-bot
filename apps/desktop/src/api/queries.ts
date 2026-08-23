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

export interface BotCreateInput {
  name: string;
  role: string;
  description: string;
  model_id: string;
  execution_mode: "local" | "sandbox" | "remote";
  max_steps: number;
  daily_budget_usd: number;
  fallback_model_ids: string[];
}

export interface RoutineRecord {
  id: string;
  bot_id: string;
  name: string;
  cron: string;
  timezone: string;
  prompt: string;
  enabled: boolean;
  next_run_at: string;
  last_run_at: string | null;
}

export interface RoutineCreateInput {
  bot_id: string;
  name: string;
  cron: string;
  timezone: string;
  prompt: string;
  enabled: boolean;
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

export function useCreateBot(client: ApiClient) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (command: BotCreateInput) => client.post<Bot>("/bots", command),
    onSuccess: (created) => {
      queryClient.setQueryData<Bot[]>(queryKeys.bots, (current = []) => [...current, created]);
    },
  });
}

export function useApprovals(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.approvals, queryFn: ({ signal }) => client.get<Approval[]>("/approvals", { signal }) });
}

export function useModels(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.models, queryFn: ({ signal }) => client.get<CatalogModel[]>("/models", { signal }), staleTime: 5 * 60_000 });
}

export function useRoutines(client: ApiClient) {
  return useQuery({ queryKey: queryKeys.routines, queryFn: ({ signal }) => client.get<RoutineRecord[]>("/routines", { signal }) });
}

export function useCreateRoutine(client: ApiClient) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (command: RoutineCreateInput) => client.post<RoutineRecord>("/routines", command),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.routines }),
  });
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
