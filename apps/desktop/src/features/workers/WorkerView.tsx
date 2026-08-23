export function WorkerView({ workers }: { workers: Record<string, unknown>[] }) {
  return <section className="feature-center"><header><span className="eyebrow">EXECUTION FABRIC</span><h2>Worker</h2><p>本机、Docker 沙箱和远程 Worker 的心跳与能力。</p></header>{workers.length === 0 ? <div className="feature-empty">尚无 Worker 心跳</div> : <pre>{JSON.stringify(workers, null, 2)}</pre>}</section>;
}
