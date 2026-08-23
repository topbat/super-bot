import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";

import type { Approval } from "@superbot/contracts";

export function ApprovalCenter({ approvals, onDecision }: { approvals: Approval[]; onDecision: (id: string, decision: "approved" | "denied") => void }) {
  return <section className="feature-center"><header><span className="eyebrow">HUMAN IN THE LOOP</span><h2>审批中心</h2><p>高风险动作只有在你确认后才会恢复执行。</p></header>{approvals.length === 0 ? <div className="feature-empty">当前没有待审批动作</div> : approvals.map((approval) => <article className="approval-row" key={approval.id}><div><Badge color="warning">{approval.risk}</Badge><h3>{approval.summary}</h3><code>{approval.tool_name}</code></div><div><Button onClick={() => onDecision(approval.id, "denied")}>拒绝</Button><Button appearance="primary" onClick={() => onDecision(approval.id, "approved")}>允许一次</Button></div></article>)}</section>;
}
