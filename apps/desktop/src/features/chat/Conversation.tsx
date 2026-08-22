import { useEffect, useState } from "react";

import type { Bot, Task, TaskStatus } from "@superbot/contracts";

import type { ServerEvent } from "../../api/client";

import { Composer } from "./Composer";
import { TaskTimeline } from "../tasks/TaskTimeline";

interface ConversationProps {
  bot: Bot;
  sendMessage: (content: string, idempotencyKey: string) => Promise<Task>;
  watchTask?: (taskId: string, onEvent: (event: ServerEvent<Record<string, unknown>>) => void) => () => void;
}

const EVENT_STATUS: Record<string, TaskStatus> = {
  started: "running",
  approval_requested: "waiting_approval",
  completed: "succeeded",
  failed: "failed",
  cancelled: "cancelled",
};

export function Conversation({ bot, sendMessage, watchTask }: ConversationProps) {
  const [task, setTask] = useState<Task>();
  useEffect(() => {
    if (!task || !watchTask) return;
    return watchTask(task.id, (event) => {
      setTask((current) => {
        if (!current) return current;
        const eventStep = typeof event.data.step === "number" ? event.data.step : undefined;
        return {
          ...current,
          status: EVENT_STATUS[event.event] ?? current.status,
          current_step: eventStep ?? (event.event === "tool_completed" ? current.current_step + 1 : current.current_step),
        };
      });
    });
  }, [task?.id, watchTask]);
  return (
    <>
      <section className="conversation" aria-label="对话工作区">
        {!task ? (
          <div className="welcome-panel">
            <span className="eyebrow">READY FOR WORK</span>
            <h2>把目标交给 {bot.name}</h2>
            <p>{bot.description}</p>
            <div className="suggestion-grid">
              <button><strong>深度调研</strong><span>搜索、核验并整理一手资料</span></button>
              <button><strong>持续监控</strong><span>设定例行任务并按时运行</span></button>
              <button><strong>文件交付</strong><span>在隔离工作区生成可审计结果</span></button>
            </div>
          </div>
        ) : <TaskTimeline task={task} />}
      </section>
      <Composer onSend={async (content, key) => setTask(await sendMessage(content, key))} />
    </>
  );
}
