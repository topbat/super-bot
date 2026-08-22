import { Badge } from "@fluentui/react-badge";
import { ProgressBar } from "@fluentui/react-progress";

import type { Task } from "@superbot/contracts";

export function TaskTimeline({ task }: { task: Task }) {
  const progress = task.max_steps ? task.current_step / task.max_steps : 0;
  return (
    <section className="task-timeline" aria-label="任务执行状态">
      <div className="section-title"><span>任务已进入队列</span><Badge appearance="tint">{task.status}</Badge></div>
      <code>{task.id}</code>
      <ProgressBar value={progress} />
      <small>{task.current_step} / {task.max_steps} 步</small>
    </section>
  );
}
