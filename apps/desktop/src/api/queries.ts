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

export interface BrowserSessionRecord {
  id: string;
  bot_id: string;
  status: "active" | "closed" | "failed";
  current_url: string;
  title: string;
  allowed_domains: string[];
  viewport_width: number;
  viewport_height: number;
  created_at: string;
  updated_at: string;
}

export interface BrowserSnapshot {
  session_id: string;
  url: string;
  title: string;
  viewport_width: number;
  viewport_height: number;
  screenshot_base64: string;
  elements: Array<{
    role: string;
    name: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
}

export type BrowserAction =
  | { kind: "navigate"; url: string }
  | { kind: "click"; x: number; y: number }
  | { kind: "type"; text: string }
  | { kind: "press"; key: string }
  | { kind: "scroll"; delta_x?: number; delta_y?: number }
  | { kind: "back" | "forward" | "reload" };

export interface BrowserSessionState {
  session: BrowserSessionRecord;
  snapshot: BrowserSnapshot;
}

export const queryKeys = {
  bots: ["bots"] as const,
  approvals: ["approvals"] as const,
  models: ["models"] as const,
  routines: ["routines"] as const,
  workers: ["workers"] as const,
  browserSessions: (botId: string | undefined) => ["browser-sessions", botId] as const,
  browserSnapshot: (sessionId: string | undefined) => ["browser-snapshot", sessionId] as const,
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

export function useBrowserSessions(client: ApiClient, botId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.browserSessions(botId),
    queryFn: ({ signal }) => client.get<BrowserSessionRecord[]>(`/browser/sessions?bot_id=${botId}`, { signal }),
    enabled: Boolean(botId),
    refetchInterval: 10_000,
  });
}

export function useBrowserSnapshot(client: ApiClient, sessionId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.browserSnapshot(sessionId),
    queryFn: ({ signal }) => client.get<BrowserSnapshot>(`/browser/sessions/${sessionId}/snapshot`, { signal }),
    enabled: Boolean(sessionId),
    retry: false,
  });
}

export function useCreateBrowserSession(client: ApiClient, botId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (startUrl: string) => {
      if (!botId) throw new Error("请先选择 Bot");
      return client.post<BrowserSessionState>("/browser/sessions", {
        bot_id: botId,
        start_url: startUrl,
        allowed_domains: [],
        viewport_width: 1280,
        viewport_height: 720,
      });
    },
    onSuccess: ({ session, snapshot }) => {
      queryClient.setQueryData<BrowserSessionRecord[]>(
        queryKeys.browserSessions(botId),
        (current = []) => [...current.filter((item) => item.id !== session.id), session],
      );
      queryClient.setQueryData(queryKeys.browserSnapshot(session.id), snapshot);
    },
  });
}

export function useBrowserAction(client: ApiClient, sessionId: string | undefined, botId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (action: BrowserAction) => {
      if (!sessionId) throw new Error("没有活动的浏览器会话");
      return client.post<BrowserSnapshot>(`/browser/sessions/${sessionId}/actions`, action);
    },
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKeys.browserSnapshot(sessionId), snapshot);
      void queryClient.invalidateQueries({ queryKey: queryKeys.browserSessions(botId) });
    },
  });
}

export function useCloseBrowserSession(client: ApiClient, botId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => client.delete<void>(`/browser/sessions/${sessionId}`),
    onSuccess: (_, sessionId) => {
      queryClient.setQueryData<BrowserSessionRecord[]>(
        queryKeys.browserSessions(botId),
        (current = []) => current.filter((session) => session.id !== sessionId),
      );
      queryClient.removeQueries({ queryKey: queryKeys.browserSnapshot(sessionId) });
    },
  });
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
