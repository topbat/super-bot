import { Badge, Button, Divider, ProgressBar } from "@fluentui/react-components";
import { CheckCircle, Clock, SidebarSimple } from "@phosphor-icons/react";

import type { Bot } from "@superbot/contracts";

interface InspectorProps {
  bot: Bot | undefined;
  onCollapse: () => void;
}

export function Inspector({ bot, onCollapse }: InspectorProps) {
  return (
    <aside className="inspector" aria-label="任务检查器">
      <header className="panel-header">
        <div>
          <span className="eyebrow">RUN INSPECTOR</span>
          <h2>运行状态</h2>
        </div>
        <Button
          appearance="subtle"
          icon={<SidebarSimple />}
          aria-label="收起任务检查器"
          onClick={onCollapse}
        />
      </header>
      <Divider />

      <section className="inspector-section">
        <div className="section-title"><span>当前 Bot</span><Badge appearance="tint" color="success">就绪</Badge></div>
        <div className="identity-row">
          <div className="identity-glyph">{bot?.name.slice(0, 1) ?? "S"}</div>
          <div><strong>{bot?.name ?? "未选择"}</strong><p>{bot?.model_id ?? "未配置模型"}</p></div>
        </div>
      </section>

      <section className="inspector-section metrics-grid" aria-label="任务指标">
        <div><span>执行模式</span><strong>{bot?.execution_mode ?? "—"}</strong></div>
        <div><span>最大步数</span><strong>{bot?.max_steps ?? "—"}</strong></div>
        <div><span>今日预算</span><strong>{bot?.daily_budget_usd ? `$${bot.daily_budget_usd}` : "不限"}</strong></div>
        <div><span>待审批</span><strong>0</strong></div>
      </section>

      <section className="inspector-section">
        <div className="section-title"><span>最近活动</span><Button appearance="transparent" size="small">查看全部</Button></div>
        <ol className="activity-list">
          <li><CheckCircle weight="fill" /><span><strong>控制面已连接</strong><small>刚刚</small></span></li>
          <li><Clock /><span><strong>等待新任务</strong><small>运行记录会显示在这里</small></span></li>
        </ol>
      </section>

      <section className="inspector-section budget-block">
        <div className="section-title"><span>预算使用</span><span>0%</span></div>
        <ProgressBar value={0} thickness="medium" />
        <p>硬预算会在模型调用前检查，超限立即停止。</p>
      </section>
    </aside>
  );
}
