export function RoutineCenter({ routines }: { routines: Record<string, unknown>[] }) {
  return <section className="feature-center"><header><span className="eyebrow">SCHEDULED AUTONOMY</span><h2>例行任务</h2><p>按 IANA 时区运行，单次触发拥有稳定幂等键。</p></header>{routines.length === 0 ? <div className="feature-empty">尚未创建例行任务</div> : <pre>{JSON.stringify(routines, null, 2)}</pre>}</section>;
}
