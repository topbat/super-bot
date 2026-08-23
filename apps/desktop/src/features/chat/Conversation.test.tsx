import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Bot, Task } from "@superbot/contracts";

import { Conversation } from "./Conversation";

const bot = {
  id: "bot-1",
  name: "研究助手",
  description: "可靠研究",
  model_id: "qwen3.7-plus",
} as Bot;

describe("Conversation", () => {
  it("submits an idempotent task and renders its durable status", async () => {
    const created = {
      id: "task-1",
      status: "queued",
      current_step: 0,
      max_steps: 24,
    } as Task;
    const send = vi.fn().mockResolvedValue(created);
    const user = userEvent.setup();
    render(<Conversation bot={bot} sendMessage={send} />);

    await user.type(screen.getByRole("textbox", { name: "给 Bot 发送任务" }), "核验 Qwen 文档");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(send).toHaveBeenCalledWith("核验 Qwen 文档", expect.stringMatching(/^desktop:/));
    expect(await screen.findByText("任务已进入队列")).toBeInTheDocument();
    expect(screen.getByText("task-1")).toBeInTheDocument();
  });

  it("keeps the user's prompt when submission fails", async () => {
    const send = vi.fn().mockRejectedValue(new Error("service offline"));
    const user = userEvent.setup();
    render(<Conversation bot={bot} sendMessage={send} />);
    const input = screen.getByRole("textbox", { name: "给 Bot 发送任务" });

    await user.type(input, "不要丢失这段内容");
    await user.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("service offline");
    expect(input).toHaveValue("不要丢失这段内容");
  });
});
