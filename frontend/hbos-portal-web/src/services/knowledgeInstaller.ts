/** Local-only installer. Tokens are file configuration, never model instructions. */
export const knowledgeUsageRules='涉及新乡海滨公司制度、SOP、生产、质量、安全或人事问题时，先调用 HBOS 的 list_knowledge_spaces、search_knowledge，再用 get_evidence 核对来源。列出真实标题和版本状态；资料不足时说明没有可核验的企业依据，不编造内部事实。不调用 get_source、原件下载或全文枚举。只有用户明确要求 HBOS 生成回答时才调用 ask_knowledge，默认 gpt-6-luna。客户端自己的模型由用户自己的设置控制。禁止将 MCP 凭据或配置文件提交给 LLM。'
export function localInstaller(client:'OpenClaw'|'Hermes',endpoint:string,token:string,connection:string,_legacyChallenge?:string):string {
  if (!/^hbos_mcp_[0-9a-f]{32}\.[A-Za-z0-9_-]{43}$/.test(token) || !/^[0-9a-f]{32}$/.test(connection)) throw new Error('连接安装凭据不完整，请重新创建本人连接。')
  const u=new URL(endpoint)
  if (u.pathname!=='/mcp' || u.search || u.hash || u.username || u.password || !['http:','https:'].includes(u.protocol) || (u.protocol!=='https:'&&!['knowledge-r2.localhost','127.0.0.1','localhost'].includes(u.hostname))) throw new Error('安装地址不受支持。')
  const payload=JSON.stringify({client,endpoint,token,connection,rules:knowledgeUsageRules})
  return `#!/usr/bin/env python3
# HBOS controlled local import. No network/model request and no credential printing.
import argparse,json,os,pathlib,re,shutil,tempfile
PAYLOAD=json.loads(${JSON.stringify(payload)})
def private_write(path,text):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.hbos-',dir=path.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as out:out.write(text);out.flush();os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
p=argparse.ArgumentParser(description='Import HBOS config and credential-free rules without any model call.')
p.add_argument('--directory',help='Isolated client directory, useful for verification; no existing profile is changed.')
p.add_argument('--yes',action='store_true',help='Explicitly approve the displayed local configuration changes.')
a=p.parse_args()
os.chmod(__file__,0o600)
os.umask(0o077)
client=PAYLOAD['client']
root=pathlib.Path(a.directory).expanduser().resolve() if a.directory else pathlib.Path.home()/('.openclaw' if client=='OpenClaw' else '.hermes')
path=root/('openclaw.json' if client=='OpenClaw' else 'config.yaml')
if path.is_symlink():raise SystemExit('Refusing a symlink configuration.')
cfg={}
if path.exists():
    if client=='OpenClaw':cfg=json.loads(path.read_text())
    else:
        try:import yaml
        except ImportError:
            installed=pathlib.Path.home()/'.hermes/hermes-agent/venv/bin/python'
            if installed.is_file() and installed.resolve()!=pathlib.Path(__import__('sys').executable).resolve():
                os.execv(str(installed),[str(installed),__file__,*__import__('sys').argv[1:]])
            raise SystemExit('Run with the installed Hermes Python environment (PyYAML required). No file changed.')
        cfg=yaml.safe_load(path.read_text()) or {}
    if not isinstance(cfg,dict):raise SystemExit('Configuration is not an object. No file changed.')
headers={'Authorization':'Bearer '+PAYLOAD['token']}
server={'url':PAYLOAD['endpoint'],'headers':headers}
entry='hbos-knowledge'
if client=='OpenClaw':
    server['transport']='streamable-http'
    servers=cfg.setdefault('mcp',{}).setdefault('servers',{})
    configured=cfg.get('agents',{}).get('defaults',{}).get('workspace')
    workspace=pathlib.Path(configured).expanduser() if configured and not a.directory else root/'workspace'
    if a.directory:cfg.setdefault('agents',{}).setdefault('defaults',{})['workspace']=str(workspace)
else:
    server['timeout']=90;servers=cfg.setdefault('mcp_servers',{})
    workspace=root
prior=servers.get(entry)
if prior and (not isinstance(prior,dict) or prior.get('url')!=PAYLOAD['endpoint']):
    raise SystemExit('The hbos-knowledge entry belongs to another endpoint. No existing entry was changed.')
servers[entry]=server
rules=workspace/'AGENTS.md'
if rules.is_symlink():raise SystemExit('Refusing a symlink rules file. No file changed.')
existing=rules.read_text() if rules.exists() else ''
print('Install HBOS in '+str(path)+' and credential-free rules in '+str(rules)+'. Existing files will be backed up.')
if not a.yes and input('Continue? [y/N] ').strip().lower() not in ('y','yes'):
    raise SystemExit('Cancelled. No configuration was changed; remove the private installer if no longer needed.')
block='<!-- HBOS_KNOWLEDGE_RULES_START -->\\n'+PAYLOAD['rules']+'\\n<!-- HBOS_KNOWLEDGE_RULES_END -->'
pattern=r'<!-- HBOS_KNOWLEDGE_RULES_START -->.*?<!-- HBOS_KNOWLEDGE_RULES_END -->'
updated=re.sub(pattern,lambda m:block,existing,flags=re.S) if re.search(pattern,existing,re.S) else existing.rstrip()+'\\n\\n'+block+'\\n'
if path.exists():
    backup=path.with_name(path.name+'.hbos-'+PAYLOAD['connection'][:8]+'.backup')
    if backup.exists():raise SystemExit('Backup already exists; refusing to overwrite it.')
    private_write(backup,path.read_text())
if rules.exists():
    backup_rules=rules.with_name('AGENTS.md.hbos-'+PAYLOAD['connection'][:8]+'.backup')
    if backup_rules.exists():raise SystemExit('Rules backup already exists; refusing to overwrite it.')
    private_write(backup_rules,existing)
private_write(rules,updated)
private_write(path,json.dumps(cfg,ensure_ascii=False,indent=2)+'\\n')
# The downloaded file contains the credential. Remove it after a successful import.
pathlib.Path(__file__).unlink()
print('HBOS installed. Restart your assistant and ask a normal company knowledge question. No model request was made during installation.')
`
}
