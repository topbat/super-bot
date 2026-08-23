import { lazy, Suspense, useEffect, useState } from "react";
import { Button } from "@fluentui/react-button";
import { MessageBar, MessageBarBody } from "@fluentui/react-message-bar";
import { FluentProvider } from "@fluentui/react-provider";
import { Spinner } from "@fluentui/react-spinner";
import { Tooltip } from "@fluentui/react-tooltip";
import { Moon } from "@phosphor-icons/react/dist/csr/Moon";
import { SidebarSimple } from "@phosphor-icons/react/dist/csr/SidebarSimple";
import { Sun } from "@phosphor-icons/react/dist/csr/Sun";

import type { Approval, Bot, Task } from "@superbot/contracts";

import type { BrowserAction, BrowserSessionRecord, BrowserSnapshot, CatalogModel } from "./api/queries";
import type { BotCreateInput, RoutineCreateInput, RoutineRecord } from "./api/queries";
import type { ServerEvent } from "./api/client";
import { AppShell } from "./components/AppShell";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { Conversation } from "./features/chat/Conversation";
import { BotCreatePanel } from "./features/bots/BotCreatePanel";
import { darkTheme, lightTheme } from "./theme";

const ApprovalCenter = lazy(() => import("./features/approvals/ApprovalCenter").then((module) => ({ default: module.ApprovalCenter })));
const AuditView = lazy(() => import("./features/audit/AuditView").then((module) => ({ default: module.AuditView })));
const ModelCenter = lazy(() => import("./features/models/ModelCenter").then((module) => ({ default: module.ModelCenter })));
const RoutineCenter = lazy(() => import("./features/routines/RoutineCenter").then((module) => ({ default: module.RoutineCenter })));
const WorkerView = lazy(() => import("./features/workers/WorkerView").then((module) => ({ default: module.WorkerView })));
const BrowserView = lazy(() => import("./features/browser/BrowserView").then((module) => ({ default: module.BrowserView })));

export type AppState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | {
      kind: "ready";
      bots: Bot[];
      approvals?: Approval[];
      models?: CatalogModel[];
      routines?: RoutineRecord[];
      workers?: Record<string, unknown>[];
      browserSessions?: BrowserSessionRecord[];
      browserSnapshot?: BrowserSnapshot;
    };

interface AppProps {
  state: AppState;
  sendMessage?: (content: string, idempotencyKey: string) => Promise<Task>;
  watchTask?: (taskId: string, onEvent: (event: ServerEvent<Record<string, unknown>>) => void) => () => void;
  decideApproval?: (id: string, decision: "approved" | "denied") => void;
  onRetry?: () => void;
  selectedBotId?: string;
  onSelectBot?: (botId: string) => void;
  onCreateBot?: (command: BotCreateInput) => Promise<Bot>;
  onCreateRoutine?: (command: RoutineCreateInput) => Promise<unknown>;
  onCreateBrowser?: (startUrl: string) => Promise<void>;
  onBrowserAction?: (action: BrowserAction) => Promise<void>;
  onCloseBrowser?: (sessionId: string) => Promise<void>;
  onRefreshBrowser?: () => Promise<void>;
  browserPending?: boolean;
  browserError?: string;
}

export function App({ state, sendMessage, watchTask, decideApproval, onRetry, selectedBotId, onSelectBot, onCreateBot, onCreateRoutine, onCreateBrowser, onBrowserAction, onCloseBrowser, onRefreshBrowser, browserPending, browserError }: AppProps) {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [activeSection, setActiveSection] = useState("chat");
  const [createOpen, setCreateOpen] = useState(false);
  const bots = state.kind === "ready" ? state.bots : [];
  const selectedBot = bots.find((bot) => bot.id === selectedBotId) ?? bots[0];

  useEffect(() => {
    const keyboardHandler = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.key.toLowerCase() === "i") {
        event.preventDefault();
        setInspectorOpen((current) => !current);
      }
    };
    window.addEventListener("keydown", keyboardHandler);
    return () => window.removeEventListener("keydown", keyboardHandler);
  }, []);

  return (
    <FluentProvider
      theme={theme === "light" ? lightTheme : darkTheme}
      data-theme={theme}
      data-testid="app-provider"
      className="app-provider"
    >
      <AppShell
        sidebar={<Sidebar bots={bots} activeSection={activeSection} onSectionChange={setActiveSection} selectedBotId={selectedBot?.id} onSelectBot={onSelectBot} onCreateBot={() => setCreateOpen(true)} />}
        inspector={inspectorOpen ? <Inspector bot={selectedBot} onCollapse={() => setInspectorOpen(false)} /> : undefined}
      >
        <main className="workspace">
          <header className="workspace-header">
            <div>
              <span className="eyebrow">DESKTOP CONTROL PLANE</span>
              <h1>{activeSection === "chat" ? selectedBot?.name ?? "Super Bot 工作台" : "Super Bot 工作台"}</h1>
            </div>
            <div className="header-actions">
              {!inspectorOpen && (
                <Tooltip content="任务检查器 (Ctrl+I)" relationship="label">
                  <Button icon={<SidebarSimple />} aria-label="展开任务检查器" onClick={() => setInspectorOpen(true)} />
                </Tooltip>
              )}
              <Tooltip content="切换主题" relationship="label">
                <Button
                  icon={theme === "light" ? <Moon /> : <Sun />}
                  aria-label={theme === "light" ? "切换为深色主题" : "切换为浅色主题"}
                  onClick={() => setTheme((current) => current === "light" ? "dark" : "light")}
                />
              </Tooltip>
            </div>
          </header>

          <section
            className="conversation"
            aria-label="对话工作区"
            hidden={state.kind === "ready" && bots.length > 0 && activeSection === "chat"}
          >
            {state.kind === "loading" && (
              <div className="center-state"><Spinner size="large" /><h2>正在连接 Super Bot 服务…</h2><p>正在加载 Bot、模型与任务状态。</p></div>
            )}
            {state.kind === "error" && (
              <div className="center-state"><MessageBar intent="error" role="alert"><MessageBarBody>{state.message}</MessageBarBody></MessageBar><h2>控制面暂时不可用</h2><p>请检查本机 API 或 Docker Desktop 服务。</p><Button appearance="primary" onClick={onRetry}>重新连接</Button></div>
            )}
            {state.kind === "ready" && bots.length === 0 && (
              <div className="center-state empty-state"><span className="empty-glyph">SB</span><h2>创建你的第一个 Bot</h2><p>为它选择模型、工作区、工具边界和每日硬预算。</p><Button appearance="primary" onClick={() => setCreateOpen(true)}>创建 Bot</Button></div>
            )}
            {state.kind === "ready" && bots.length > 0 && activeSection !== "chat" && (
              <Suspense fallback={<Spinner label="正在加载功能模块" />}>
                {renderSection(activeSection, state, selectedBot, decideApproval, onCreateRoutine, {
                  onCreate: onCreateBrowser,
                  onAction: onBrowserAction,
                  onClose: onCloseBrowser,
                  onRefresh: onRefreshBrowser,
                  pending: browserPending,
                  error: browserError,
                })}
              </Suspense>
            )}
          </section>
          {state.kind === "ready" && selectedBot && activeSection === "chat" && (
            <Conversation
              key={selectedBot.id}
              bot={selectedBot}
              sendMessage={sendMessage ?? (() => Promise.reject(new Error("控制面尚未连接")))}
              watchTask={watchTask}
            />
          )}
        </main>
      </AppShell>
      {createOpen && onCreateBot && (
        <BotCreatePanel
          models={state.kind === "ready" ? state.models ?? [] : []}
          onClose={() => setCreateOpen(false)}
          onSubmit={async (command) => {
            const created = await onCreateBot(command);
            onSelectBot?.(created.id);
            setCreateOpen(false);
          }}
        />
      )}
    </FluentProvider>
  );
}

function renderSection(
  activeSection: string,
  state: Extract<AppState, { kind: "ready" }>,
  selectedBot: Bot | undefined,
  decideApproval?: (id: string, decision: "approved" | "denied") => void,
  onCreateRoutine?: (command: RoutineCreateInput) => Promise<unknown>,
  browser?: {
    onCreate?: (startUrl: string) => Promise<void>;
    onAction?: (action: BrowserAction) => Promise<void>;
    onClose?: (sessionId: string) => Promise<void>;
    onRefresh?: () => Promise<void>;
    pending?: boolean;
    error?: string;
  },
) {
  if (activeSection === "approvals") return <ApprovalCenter approvals={state.approvals ?? []} onDecision={decideApproval ?? (() => undefined)} />;
  if (activeSection === "models") return <ModelCenter models={state.models ?? []} />;
  if (activeSection === "routines") return <RoutineCenter routines={state.routines ?? []} botId={selectedBot?.id} onCreate={onCreateRoutine} />;
  if (activeSection === "audit") return <AuditView />;
  if (activeSection === "workers") return <WorkerView workers={state.workers ?? []} />;
  if (activeSection === "browser") return (
    <BrowserView
      botId={selectedBot?.id}
      sessions={state.browserSessions ?? []}
      snapshot={state.browserSnapshot}
      pending={browser?.pending}
      error={browser?.error}
      onCreate={browser?.onCreate ?? (() => Promise.reject(new Error("浏览器服务尚未连接")))}
      onAction={browser?.onAction ?? (() => Promise.reject(new Error("浏览器服务尚未连接")))}
      onClose={browser?.onClose ?? (() => Promise.reject(new Error("浏览器服务尚未连接")))}
      onRefresh={browser?.onRefresh ?? (() => Promise.reject(new Error("浏览器服务尚未连接")))}
    />
  );
  return <section className="feature-center"><header><span className="eyebrow">VERSIONED CAPABILITIES</span><h2>技能</h2><p>从 SKILL.md 加载经过哈希版本化的工作流程和工具边界。</p></header><div className="feature-empty">尚未安装技能</div></section>;
}
