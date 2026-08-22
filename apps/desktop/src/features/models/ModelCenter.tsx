import { Badge } from "@fluentui/react-badge";

import type { CatalogModel } from "../../api/queries";

export function ModelCenter({ models }: { models: CatalogModel[] }) {
  return <section className="feature-center"><header><span className="eyebrow">EXPLICIT ROUTING</span><h2>模型中心</h2><p>模型选择透明可见；只有显式配置的回退链才会生效。</p></header><div className="model-grid">{models.map((model) => <article key={model.id}><div className="section-title"><strong>{model.display_name}</strong><Badge appearance="tint">{model.provider}</Badge></div><code>{model.id}</code><p>{model.capability.context_window.toLocaleString()} tokens · {model.capability.tool_calling ? "工具调用" : "仅文本"} · {model.capability.thinking ? "思考" : "快速"}</p></article>)}</div></section>;
}
