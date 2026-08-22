import { useEffect, useState } from "react";
import {
  Button,
  FluentProvider,
  MessageBar,
  MessageBarBody,
  Spinner,
  Textarea,
  Tooltip,
} from "@fluentui/react-components";
import { Moon, PaperPlaneRight, SidebarSimple, Sun } from "@phosphor-icons/react";

import type { Bot } from "@superbot/contracts";

import { AppShell } from "./components/AppShell";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { darkTheme, lightTheme } from "./theme";

export type AppState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; bots: Bot[] };

interface AppProps {
  state: AppState;
}

export function App({ state }: AppProps) {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const bots = state.kind === "ready" ? state.bots : [];

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
        sidebar={<Sidebar bots={bots} />}
        inspector={inspectorOpen ? <Inspector bot={bots[0]} onCollapse={() => setInspectorOpen(false)} /> : undefined}
      >
        <main className="workspace">
          <header className="workspace-header">
            <div>
              <span className="eyebrow">DESKTOP CONTROL PLANE</span>
              <h1>{bots[0]?.name ?? "Super Bot 工作台"}</h1>
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

          <section className="conversation" aria-label="对话工作区">
            {state.kind === "loading" && (
              <div className="center-state"><Spinner size="large" /><h2>正在连接 Super Bot 服务…</h2><p>正在加载 Bot、模型与任务状态。</p></div>
            )}
            {state.kind === "error" && (
              <div className="center-state"><MessageBar intent="error" role="alert"><MessageBarBody>{state.message}</MessageBarBody></MessageBar><h2>控制面暂时不可用</h2><p>请检查本机 API 或 Docker Desktop 服务。</p><Button appearance="primary">重新连接</Button></div>
            )}
            {state.kind === "ready" && bots.length === 0 && (
              <div className="center-state empty-state"><span className="empty-glyph">SB</span><h2>创建你的第一个 Bot</h2><p>为它选择模型、工作区、工具边界和每日硬预算。</p><Button appearance="primary">创建 Bot</Button></div>
            )}
            {state.kind === "ready" && bots.length > 0 && (
              <div className="welcome-panel">
                <span className="eyebrow">READY FOR WORK</span>
                <h2>把目标交给 {bots[0].name}</h2>
                <p>{bots[0].description}</p>
                <div className="suggestion-grid">
                  <button><strong>深度调研</strong><span>搜索、核验并整理一手资料</span></button>
                  <button><strong>持续监控</strong><span>设定例行任务并按时运行</span></button>
                  <button><strong>文件交付</strong><span>在隔离工作区生成可审计结果</span></button>
                </div>
              </div>
            )}
          </section>

          <form className="composer" onSubmit={(event) => event.preventDefault()}>
            <Textarea aria-label="给 Bot 发送任务" placeholder="描述目标，或输入 / 使用技能…" resize="vertical" />
            <div className="composer-footer">
              <span>Enter 发送 · Shift+Enter 换行</span>
              <Button appearance="primary" icon={<PaperPlaneRight weight="fill" />} type="submit">发送</Button>
            </div>
          </form>
        </main>
      </AppShell>
    </FluentProvider>
  );
}
