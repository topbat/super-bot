import { useState } from "react";
import { Button } from "@fluentui/react-button";

import type { BotCreateInput, CatalogModel } from "../../api/queries";

interface BotCreatePanelProps {
  models: CatalogModel[];
  onClose: () => void;
  onSubmit: (command: BotCreateInput) => Promise<void>;
}

export function BotCreatePanel({ models, onClose, onSubmit }: BotCreatePanelProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  const defaultModel = models[0]?.id ?? "qwen3.7-plus";

  return (
    <div className="dialog-backdrop">
      <form
        className="bot-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-bot-title"
        onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          setSaving(true);
          setError(undefined);
          try {
            await onSubmit({
              name: String(data.get("name")),
              role: String(data.get("role")),
              description: String(data.get("description")),
              model_id: String(data.get("model_id")),
              execution_mode: "sandbox",
              max_steps: Number(data.get("max_steps")),
              daily_budget_usd: Number(data.get("daily_budget_usd")),
              fallback_model_ids: [],
            });
          } catch (reason) {
            setError(reason instanceof Error ? reason.message : "创建 Bot 失败");
          } finally {
            setSaving(false);
          }
        }}
      >
        <header><span className="eyebrow">NEW TEAMMATE</span><h2 id="create-bot-title">创建 Bot</h2><p>定义长期职责、明确模型和硬预算。</p></header>
        <label>名称<input name="name" required maxLength={80} autoFocus /></label>
        <label>职责<input name="role" required maxLength={120} /></label>
        <label>说明<textarea name="description" required maxLength={4000} rows={4} /></label>
        <div className="dialog-grid">
          <label>模型<select name="model_id" defaultValue={defaultModel}>{models.length > 0 ? models.map((model) => <option value={model.id} key={model.id}>{model.display_name}</option>) : <option value={defaultModel}>Qwen 3.7 Plus</option>}</select></label>
          <label>最大步数<input name="max_steps" type="number" min={1} max={200} defaultValue={24} required /></label>
          <label>每日预算 USD<input name="daily_budget_usd" type="number" min={0} step="0.01" defaultValue={2} required /></label>
        </div>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <footer><Button type="button" appearance="secondary" onClick={onClose} disabled={saving}>取消</Button><Button type="submit" appearance="primary" disabled={saving}>{saving ? "保存中…" : "保存 Bot"}</Button></footer>
      </form>
    </div>
  );
}
