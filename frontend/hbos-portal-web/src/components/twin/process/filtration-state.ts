// Adapted from frozen WUJUN release; provenance hashes are in the private compatibility record.
// All lengths, quantities and timing below are schematic visual assumptions.
export const demoConfig = Object.freeze({duration:40,residualLiquid:.12,particles:240,seed:102,liquidHeight:2.1,cakeHeight:.34,particleRadius:.035});
export type DemoConfig=typeof demoConfig;
export type DataSourceMode='demo'|'history'|'live_readonly';
export type TelemetryField={value:number|string|boolean|null;unit:string|null;timestamp:string|null;source:'none'|'history'|'live_readonly';quality:'missing'|'good'|'stale'|'bad'};
export type StateInput={dataSourceMode:DataSourceMode;demoTime:number|null;telemetry:Record<string,TelemetryField>;batchId:string|null};
export const reviewedTags:string[]=[];
export function missingTelemetry():Record<string,TelemetryField>{return Object.fromEntries([...reviewedTags,'command','setpoint','feedback','valvePosition','agitatorSpeed','cakeThickness'].map(k=>[k,{value:null,unit:null,timestamp:null,source:'none',quality:'missing'}]));}
const clamp=(v:number)=>Math.max(0,Math.min(1,v));
const rand=(i:number,seed:number)=>{let n=(i+seed)*2654435761>>>0;n^=n>>>16;n=Math.imul(n,2246822507);n^=n>>>13;return (n>>>0)/4294967296;};
export function evaluateFiltrationDemo(t:number,config=demoConfig){
 const time=Math.max(0,Math.min(config.duration,Number.isFinite(t)?t:0));const p=time/config.duration;
 const collected=(1-config.residualLiquid)*p,remaining=1-collected;
 // Weighted solid bookkeeping equals the sum of the same per-particle capture fractions.
 const particles=Array.from({length:config.particles},(_,i)=>{
  const u=rand(i*4,config.seed),a=rand(i*4+1,config.seed)*Math.PI*2,r=Math.sqrt(rand(i*4+2,config.seed))*.9;
  const captured=clamp((p-u*.7)/.3),floor=.09+config.particleRadius+config.cakeHeight*.75*rand(i*4+3,config.seed)*p;
  const suspendedY=.16+config.liquidHeight*remaining*(.15+.8*u);
  return {id:`demo_solid_${i}`,x:r*Math.cos(a),y:Math.max(floor,suspendedY*(1-captured)+floor*captured),z:r*Math.sin(a),captured};
 });
 const retained=particles.reduce((n,q)=>n+q.captured,0)/config.particles;
 return {time,progress:p,liquid:{remaining,collected,residual:config.residualLiquid,free:remaining-config.residualLiquid,total:1},solid:{suspended:1-retained,retained,total:1},particles,wetSolid:true,phase:'schematic_filtration' as const};
}
export type DemoState=ReturnType<typeof evaluateFiltrationDemo>;
export function adaptState(input:StateInput){if(input.dataSourceMode!=='demo')throw new Error('Only demo implemented; history/live_readonly require authorized records and mapping');return {dataSourceMode:input.dataSourceMode,demoState:evaluateFiltrationDemo(input.demoTime??0),telemetry:missingTelemetry(),batchId:null};}
