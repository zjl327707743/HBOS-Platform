import { spawn, execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile, unlink, open } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import net from 'node:net'
import http from 'node:http'
const root=fileURLToPath(new URL('..',import.meta.url))
const vite=fileURLToPath(new URL('../node_modules/vite/bin/vite.js',import.meta.url))
const folder=root+'.runtime/',record=folder+'server.json',port=5197
const action=process.argv[2]||'status'
async function saved(){try{return JSON.parse(await readFile(record,'utf8'))}catch{return null}}
function owned(info){if(!info||info.root!==root||info.port!==port)return false;try{const command=execFileSync('/bin/ps',['-p',String(info.pid),'-o','command='],{encoding:'utf8'});return command.includes(vite)&&command.includes('--port 5197')}catch{return false}}
const probe=()=>new Promise(resolve=>{const req=http.get(`http://127.0.0.1:${port}/`,res=>{res.resume();resolve(res.statusCode===200)});req.setTimeout(600,()=>{req.destroy();resolve(false)});req.on('error',()=>resolve(false))})
const info=await saved()
if(action==='stop'){
 if(!info){console.log('本原型没有已登记的后台服务。前台 npm run dev 使用 Ctrl+C 停止。');process.exit(0)}
 if(!owned(info)){console.log('登记 PID 已失效或来源不符；未停止任何进程。');process.exit(0)}
 process.kill(info.pid,'SIGTERM');await unlink(record);console.log(`已停止本原型服务 PID ${info.pid}，未操作其他服务。`)
}else if(action==='start'){
 if(owned(info)&&await probe()){console.log(`本原型已运行：http://iam-prototype.localhost:${port}/ (PID ${info.pid})`);process.exit(0)}
 await new Promise((resolve,reject)=>{const server=net.createServer();server.once('error',()=>reject(new Error(`127.0.0.1:${port} 已被占用，未停止或覆盖现有服务。`)));server.listen(port,'127.0.0.1',()=>server.close(resolve))})
 await mkdir(folder,{recursive:true});const log=await open(folder+'server.log','a')
 const child=spawn(process.execPath,[vite,'--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:root,detached:true,stdio:['ignore',log.fd,log.fd]});child.unref();await writeFile(record,JSON.stringify({pid:child.pid,port,root},null,2));await log.close()
 let healthy=false;for(let i=0;i<20;i++){if(await probe()){healthy=true;break}await new Promise(r=>setTimeout(r,200))}
 if(!healthy)throw new Error('本原型尚未就绪，请检查原型目录 .runtime/server.log。')
 console.log(`本原型已启动：http://iam-prototype.localhost:${port}/ (PID ${child.pid})，仅监听 127.0.0.1`)
}else if(action==='status'){console.log(owned(info)&&await probe()?`RUNNING PID ${info.pid} / 127.0.0.1:${port}`:'NOT_RUNNING（未登记或未就绪）')}
else throw new Error('仅支持 start / stop / status')
