import { useEffect, useState } from "react";
import type { MouseEvent } from "react";
import { Button } from "@fluentui/react-button";
import { Spinner } from "@fluentui/react-spinner";
import { ArrowClockwise } from "@phosphor-icons/react/dist/csr/ArrowClockwise";
import { ArrowLeft } from "@phosphor-icons/react/dist/csr/ArrowLeft";
import { ArrowRight } from "@phosphor-icons/react/dist/csr/ArrowRight";
import { GlobeHemisphereWest } from "@phosphor-icons/react/dist/csr/GlobeHemisphereWest";
import { PaperPlaneTilt } from "@phosphor-icons/react/dist/csr/PaperPlaneTilt";
import { Power } from "@phosphor-icons/react/dist/csr/Power";

import type {
  BrowserAction,
  BrowserSessionRecord,
  BrowserSnapshot,
} from "../../api/queries";

interface BrowserViewProps {
  botId?: string;
  sessions: BrowserSessionRecord[];
  snapshot?: BrowserSnapshot;
  pending?: boolean;
  error?: string;
  onCreate: (startUrl: string) => Promise<void>;
  onAction: (action: BrowserAction) => Promise<void>;
  onClose: (sessionId: string) => Promise<void>;
  onRefresh: () => Promise<void>;
}

export function BrowserView({
  botId,
  sessions,
  snapshot,
  pending = false,
  error,
  onCreate,
  onAction,
  onClose,
  onRefresh,
}: BrowserViewProps) {
  const activeSession = sessions.find((session) => session.status === "active") ?? sessions[0];
  const [startUrl, setStartUrl] = useState("");
  const [address, setAddress] = useState(snapshot?.url ?? activeSession?.current_url ?? "");
  const [keyboardText, setKeyboardText] = useState("");

  useEffect(() => {
    setAddress(snapshot?.url ?? activeSession?.current_url ?? "");
  }, [activeSession?.current_url, snapshot?.url]);

  if (!botId) {
    return (
      <section className="feature-center browser-center">
        <header><span className="eyebrow">REMOTE PLAYWRIGHT</span><h2>交互浏览器</h2></header>
        <div className="feature-empty">请先选择一个 Bot</div>
      </section>
    );
  }

  if (!activeSession) {
    return (
      <section className="feature-center browser-center">
        <header>
          <span className="eyebrow">REMOTE PLAYWRIGHT</span>
          <h2>交互浏览器</h2>
          <p>在隔离容器中打开网页；所有导航和操作都经过策略检查与审计。</p>
        </header>
        <form
          className="browser-launch"
          onSubmit={(event) => {
            event.preventDefault();
            if (startUrl.trim()) void onCreate(startUrl.trim());
          }}
        >
          <GlobeHemisphereWest aria-hidden="true" />
          <label>
            <span>起始网址</span>
            <input
              aria-label="起始网址"
              type="url"
              required
              placeholder="https://example.com"
              value={startUrl}
              onChange={(event) => setStartUrl(event.target.value)}
            />
          </label>
          <Button appearance="primary" type="submit" disabled={pending}>
            启动远程浏览器
          </Button>
        </form>
        {error && <p className="inline-error" role="alert">{error}</p>}
      </section>
    );
  }

  const clickViewport = (event: MouseEvent<HTMLButtonElement>) => {
    if (!snapshot) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (bounds.width === 0 || bounds.height === 0) return;
    const x = Math.round(((event.clientX - bounds.left) / bounds.width) * snapshot.viewport_width);
    const y = Math.round(((event.clientY - bounds.top) / bounds.height) * snapshot.viewport_height);
    void onAction({ kind: "click", x, y });
  };

  return (
    <section className="browser-workspace" aria-label="远程浏览器控制台">
      <header className="browser-toolbar">
        <div className="browser-nav-actions">
          <Button aria-label="后退" icon={<ArrowLeft />} onClick={() => void onAction({ kind: "back" })} />
          <Button aria-label="前进" icon={<ArrowRight />} onClick={() => void onAction({ kind: "forward" })} />
          <Button aria-label="刷新" icon={<ArrowClockwise />} onClick={() => void onAction({ kind: "reload" })} />
        </div>
        <form
          className="browser-address"
          onSubmit={(event) => {
            event.preventDefault();
            if (address.trim()) void onAction({ kind: "navigate", url: address.trim() });
          }}
        >
          <input aria-label="地址" value={address} onChange={(event) => setAddress(event.target.value)} />
          <Button type="submit">转到</Button>
        </form>
        <Button
          aria-label="关闭会话"
          icon={<Power />}
          onClick={() => void onClose(activeSession.id)}
        />
      </header>

      <div className="browser-meta">
        <span className="browser-live-dot" />
        <strong>{snapshot?.title || activeSession.title || "Untitled"}</strong>
        <code>{activeSession.id.slice(0, 8)}</code>
        <span>{snapshot?.viewport_width ?? activeSession.viewport_width} × {snapshot?.viewport_height ?? activeSession.viewport_height}</span>
      </div>

      <div className="browser-stage">
        {pending && <div className="browser-loading"><Spinner label="远程浏览器正在执行" /></div>}
        {snapshot ? (
          <button className="browser-canvas" aria-label="远程浏览器画面" onClick={clickViewport}>
            <img
              src={`data:image/png;base64,${snapshot.screenshot_base64}`}
              alt={`远程页面：${snapshot.title}`}
              draggable={false}
            />
          </button>
        ) : (
          <div className="feature-empty"><Button onClick={() => void onRefresh()}>载入远程画面</Button></div>
        )}
      </div>

      <footer className="browser-input-bar">
        <label>
          <span>键盘输入</span>
          <input
            aria-label="键盘输入"
            value={keyboardText}
            placeholder="先点击远程输入框，再在这里输入"
            onChange={(event) => setKeyboardText(event.target.value)}
          />
        </label>
        <Button
          aria-label="输入文本"
          icon={<PaperPlaneTilt />}
          disabled={!keyboardText}
          onClick={() => {
            if (!keyboardText) return;
            void onAction({ kind: "type", text: keyboardText });
            setKeyboardText("");
          }}
        >
          输入
        </Button>
        <Button aria-label="发送 Enter" onClick={() => void onAction({ kind: "press", key: "Enter" })}>Enter</Button>
        <Button onClick={() => void onAction({ kind: "scroll", delta_y: 560 })}>向下滚动</Button>
      </footer>
      {error && <p className="inline-error browser-error" role="alert">{error}</p>}
    </section>
  );
}
