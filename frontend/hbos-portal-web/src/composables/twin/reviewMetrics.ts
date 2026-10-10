/** Local, bounded review observations. No credentials, node IDs or telemetry. */
export const twinLifecycle = {
  renderersCreated:0, renderersDisposed:0, modelsDisposed:0,
  demosCreated:0, demosDisposed:0, schedulersCreated:0, schedulersStopped:0,
}
export function sampleSummary(samples:number[]) {
  const sorted=samples.slice().sort((a,b)=>a-b)
  const at=(p:number)=>sorted.length ? sorted[Math.min(sorted.length-1,Math.ceil(sorted.length*p)-1)]! : null
  return {count:sorted.length,p50_ms:at(.5),p95_ms:at(.95),max_ms:sorted[sorted.length-1]??null}
}
export function boundedSample(samples:number[],value:number) {
  if(!Number.isFinite(value)||value<0)return
  if(samples.length>=1200)samples.shift()
  samples.push(value)
}
