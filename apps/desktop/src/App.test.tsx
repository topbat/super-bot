import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Bot } from "@superbot/contracts";

import { App } from "./App";

const bot: Bot = {
  id: "bot-1",
  name: "研究助手",
  role: "Research agent",
  description: "检索与核验一手资料",
  model_id: "qwen3.7-plus",
  execution_mode: "sandbox",
  max_steps: 24,
  daily_budget_usd: 2,
  fallback_model_ids: [],
  archived: false,
  created_at: "2026-08-23T00:00:00Z",
  updated_at: "2026-08-23T00:00:00Z",
};

describe("desktop shell", () => {
  it("renders accessible three-column product landmarks", () => {
    render(<App state={{ kind: "ready", bots: [bot] }} />);

    expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "任务检查器" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "研究助手" })).toBeInTheDocument();
  });

  it("collapses and restores the inspector", async () => {
    const user = userEvent.setup();
    render(<App state={{ kind: "ready", bots: [bot] }} />);

    await user.click(screen.getByRole("button", { name: "收起任务检查器" }));
    expect(screen.queryByRole("complementary", { name: "任务检查器" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "展开任务检查器" }));
    expect(screen.getByRole("complementary", { name: "任务检查器" })).toBeInTheDocument();
  });

  it("supports keyboard inspector toggle and theme state", () => {
    render(<App state={{ kind: "ready", bots: [bot] }} />);

    fireEvent.keyDown(window, { key: "i", ctrlKey: true });
    expect(screen.queryByRole("complementary", { name: "任务检查器" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "切换为深色主题" }));
    expect(screen.getByTestId("app-provider")).toHaveAttribute("data-theme", "dark");
  });

  it("renders loading, empty, and API error states", () => {
    const { rerender } = render(<App state={{ kind: "loading" }} />);
    expect(screen.getByText("正在连接 Super Bot 服务…")).toBeInTheDocument();

    rerender(<App state={{ kind: "ready", bots: [] }} />);
    expect(screen.getByText("创建你的第一个 Bot")).toBeInTheDocument();

    rerender(<App state={{ kind: "error", message: "API offline" }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("API offline");
  });
});
