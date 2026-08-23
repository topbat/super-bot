import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { BrowserSessionRecord, BrowserSnapshot } from "../../api/queries";
import { BrowserView } from "./BrowserView";

const session: BrowserSessionRecord = {
  id: "session-1",
  bot_id: "bot-1",
  status: "active",
  current_url: "https://example.com/form",
  title: "Example form",
  allowed_domains: ["example.com"],
  viewport_width: 1280,
  viewport_height: 720,
  created_at: "2026-08-23T00:00:00Z",
  updated_at: "2026-08-23T00:00:00Z",
};

const snapshot: BrowserSnapshot = {
  session_id: session.id,
  url: session.current_url,
  title: session.title,
  viewport_width: 1280,
  viewport_height: 720,
  screenshot_base64: "iVBORw0KGgo=",
  elements: [],
};

describe("BrowserView", () => {
  it("starts a remote browser from a public URL", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(
      <BrowserView
        botId="bot-1"
        sessions={[]}
        onCreate={onCreate}
        onAction={vi.fn()}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("起始网址"), "https://example.com/form");
    await user.click(screen.getByRole("button", { name: "启动远程浏览器" }));

    expect(onCreate).toHaveBeenCalledWith("https://example.com/form");
  });

  it("navigates and sends keyboard actions without exposing raw browser transport", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn().mockResolvedValue(undefined);
    render(
      <BrowserView
        botId="bot-1"
        sessions={[session]}
        snapshot={snapshot}
        onCreate={vi.fn()}
        onAction={onAction}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );

    await user.clear(screen.getByLabelText("地址"));
    await user.type(screen.getByLabelText("地址"), "https://example.com/next");
    await user.click(screen.getByRole("button", { name: "转到" }));
    await user.type(screen.getByLabelText("键盘输入"), "hello");
    await user.click(screen.getByRole("button", { name: "输入文本" }));
    await user.click(screen.getByRole("button", { name: "发送 Enter" }));

    expect(onAction).toHaveBeenNthCalledWith(1, {
      kind: "navigate",
      url: "https://example.com/next",
    });
    expect(onAction).toHaveBeenNthCalledWith(2, { kind: "type", text: "hello" });
    expect(onAction).toHaveBeenNthCalledWith(3, { kind: "press", key: "Enter" });
  });

  it("maps screenshot clicks to the remote viewport and can close", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn().mockResolvedValue(undefined);
    render(
      <BrowserView
        botId="bot-1"
        sessions={[session]}
        snapshot={snapshot}
        onCreate={vi.fn()}
        onAction={onAction}
        onClose={onClose}
        onRefresh={vi.fn()}
      />,
    );
    const canvas = screen.getByRole("button", { name: "远程浏览器画面" });
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 640,
      bottom: 360,
      width: 640,
      height: 360,
      toJSON: () => ({}),
    });

    fireEvent.click(canvas, { clientX: 320, clientY: 180 });
    await user.click(screen.getByRole("button", { name: "关闭会话" }));

    expect(onAction).toHaveBeenCalledWith({ kind: "click", x: 640, y: 360 });
    expect(onClose).toHaveBeenCalledWith("session-1");
  });
});
