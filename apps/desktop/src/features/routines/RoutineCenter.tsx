import { useState } from "react";
import { Button } from "@fluentui/react-button";

import type { RoutineCreateInput, RoutineRecord } from "../../api/queries";

interface RoutineCenterProps {
  routines: RoutineRecord[];
  botId?: string;
  onCreate?: (command: RoutineCreateInput) => Promise<unknown>;
}

export function RoutineCenter({ routines, botId, onCreate }: RoutineCenterProps) {
  const [creating, setCreating] = useState(false);
  const visible = botId ? routines.filter((routine) => routine.bot_id === botId) : routines;
  return (
    <section className="feature-center">
      <header className="feature-header"><div><span className="eyebrow">SCHEDULED AUTONOMY</span><h2>例行任务</h2><p>按 IANA 时区运行，单次触发拥有稳定幂等键。</p></div><Button appearance="primary" onClick={() => setCreating((value) => !value)} disabled={!botId || !onCreate}>创建例程</Button></header>
      {creating && botId && onCreate && (
        <form className="routine-form" onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          await onCreate({
            bot_id: botId,
            name: String(data.get("name")),
            cron: String(data.get("cron")),
            timezone: String(data.get("timezone")),
            prompt: String(data.get("prompt")),
            enabled: true,
          });
          setCreating(false);
        }}>
          <label>例程名称<input name="name" required /></label>
          <label>Cron<input name="cron" required placeholder="0 9 * * 1-5" /></label>
          <label>时区<input name="timezone" required defaultValue="Asia/Shanghai" /></label>
          <label className="routine-prompt">任务说明<textarea name="prompt" required rows={3} /></label>
          <Button type="submit" appearance="primary">保存例程</Button>
        </form>
      )}
      {visible.length === 0 ? <div className="feature-empty">尚未创建例行任务</div> : <div className="routine-list">{visible.map((routine) => <article key={routine.id}><div><strong>{routine.name}</strong><code>{routine.cron} · {routine.timezone}</code></div><span>{routine.enabled ? "已启用" : "已暂停"}</span><small>下次运行 {new Date(routine.next_run_at).toLocaleString()}</small></article>)}</div>}
    </section>
  );
}
