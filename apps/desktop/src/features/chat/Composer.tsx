import { useState, type FormEvent } from "react";
import { Button } from "@fluentui/react-button";
import { Textarea } from "@fluentui/react-textarea";
import { PaperPlaneRight } from "@phosphor-icons/react/dist/csr/PaperPlaneRight";

interface ComposerProps {
  onSend: (content: string, idempotencyKey: string) => Promise<void>;
  disabled?: boolean;
}

export function Composer({ onSend, disabled }: ComposerProps) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const prompt = content.trim();
    if (!prompt || submitting) return;
    setSubmitting(true);
    setError(undefined);
    try {
      const idempotencyKey = `desktop:${crypto.randomUUID()}`;
      await onSend(prompt, idempotencyKey);
      setContent("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发送失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <Textarea
        aria-label="给 Bot 发送任务"
        placeholder="描述目标，或输入 / 使用技能…"
        resize="vertical"
        value={content}
        disabled={disabled}
        onChange={(_, data) => setContent(data.value)}
      />
      <div className="composer-footer">
        <span>Enter 发送 · Shift+Enter 换行</span>
        <Button appearance="primary" icon={<PaperPlaneRight weight="fill" />} type="submit" disabled={disabled || submitting || !content.trim()}>
          {submitting ? "发送中" : "发送"}
        </Button>
      </div>
    </form>
  );
}
