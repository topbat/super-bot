import { StrictMode } from "react";
import type { ComponentProps } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { App } from "./App";
import { ApiClient } from "./api/client";
import {
  useApprovalDecision,
  useApprovals,
  useBots,
  useModels,
  useRoutines,
  useSendMessage,
  useWorkers,
} from "./api/queries";
import "./styles.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const api = new ApiClient(window.superbot?.apiBaseUrl ?? "http://127.0.0.1:8420/api/v1");

function watchTask(
  taskId: string,
  onEvent: Parameters<NonNullable<ComponentProps<typeof App>["watchTask"]>>[1],
) {
  const controller = new AbortController();
  void api.stream(`/tasks/${taskId}/events`, {
    signal: controller.signal,
    onEvent,
  }).catch((error) => {
    if (!controller.signal.aborted) console.error("task event stream failed", error);
  });
  return () => controller.abort();
}

function DesktopControl() {
  const bots = useBots(api);
  const approvals = useApprovals(api);
  const models = useModels(api);
  const routines = useRoutines(api);
  const workers = useWorkers(api);
  const send = useSendMessage(api, bots.data?.[0]?.id);
  const decision = useApprovalDecision(api);

  if (bots.isPending) return <App state={{ kind: "loading" }} />;
  if (bots.isError) return <App state={{ kind: "error", message: bots.error.message }} onRetry={() => void bots.refetch()} />;
  return (
    <App
      state={{
        kind: "ready",
        bots: bots.data,
        approvals: approvals.data,
        models: models.data,
        routines: routines.data,
        workers: workers.data,
      }}
      sendMessage={(content, idempotencyKey) => send.mutateAsync({ content, idempotencyKey })}
      watchTask={watchTask}
      decideApproval={(id, selectedDecision) => decision.mutate({ id, decision: selectedDecision })}
    />
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <DesktopControl />
    </QueryClientProvider>
  </StrictMode>,
);
