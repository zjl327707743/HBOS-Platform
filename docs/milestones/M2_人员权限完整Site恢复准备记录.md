# M2：人员权限完整 Site 恢复准备记录

## 人员与权限：完整Site恢复执行组件离线验证 — 2026-10-10

当前进度 **S02_FULL_SITE_RESTORE_COMPONENTS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[本轮主记录](M2_人员权限完整Site恢复执行组件实施记录.md)、[验收摘要](evidence/人员权限_完整Site恢复执行组件验收摘要_20261010.json)。**222/222离线PASS**，20文件Python3.10 AST通过；安全私有落地、有限stdio / 固定loopback转发组件和内存生命周期规划已实现。真实ROOT / clone恢复 / 解密 / 网络 / 本人登录NOT_RUN，listener / 可信持久登记 / 全阶段执行清理未实现，生产服务HARD_BLOCKED。

本轮20次Docker只读源码 / UID核验，两段五角色metadata MATCH，零原SQL / 服务控制 / 真实资源创建。源码PID1为Frappe1000:1000、DB999:999、Redis999:1000；新卷初始化未核。登录hash升级 / Hook / 通知 / 重置 / 2FA副作用未闭合，有限写入NOT_READY。下一步先补这些运行门禁及执行器，不提前请求创建运行许可。5178保持既有真实只读，管理GET NOT_READY / POST关闭 / Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING与所有旧门禁保留。状态 / 本轮主记录 / M2 Gate / 相关规范 / 公共入口同步，CLAUDE / AGENTS仅规则检查。无新分支、提交、推送或部署。以下前序记录只表示当时状态，以本段为准。


当前接续：[安全工具实施](M2_人员权限完整Site恢复安全工具实施记录.md)已完成，**S02_FULL_SITE_RESTORE_GUARDS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。94项离线及真实既有备份只读验证通过；运行执行器、完整转发与清理未实现，完整恢复NOT_RUN。下一步以新主记录为准，以下保留前序准备段的原结果。

前序准备段（2026-10-10）状态 **S02_FULL_SITE_RESTORE_PREPARATION_REVIEWED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。完整恢复执行包与原站运行组件只读盘点已完成；**运行闭包尚未复制，隔离实施 NOT_READY，完整恢复仍 NOT_RUN**。本段不是完整 Site 恢复 PASS，不放行管理读取、保存或岗位授权。

沿用 Owner 指定的 `m2-r11@27d3558`，未创建或切换分支。承接[原站备份与隔离 SQL 验收](M2_人员权限原站备份与隔离SQL验收记录.md)，本段实际结果见[脱敏准备摘要](evidence/人员权限_完整Site恢复准备摘要_20261010.json)，具体拟执行范围见[完整 Site 恢复执行包](../plans/人员权限_完整Site恢复执行包.md)。私有报告、配置、SQL、认证内容、SID及人员明细不进入本记录或 Git。

## 1. 本段实际范围

已读默认五份协作文档、Skill 路由、当前 M2 门禁、前轮备份记录及直接相关恢复 / Preview 脚本。`superpowers` 不可用，人工执行并由两名代理独立复核。只执行已知精确 ID 的 Docker 过滤 inspect / image 元数据 / diff、原 bench Python `-B` 下的标准库文件 / AST / 分发元数据读取、禁 optional-lock 的 Git commit 读取，以及宿主私有备份 hash / gzip 检查。

**原站 SQL 连接0、Docker 新资源0、服务控制0**；未初始化 Frappe、导入业务 App、复制运行快照、解密、启动恢复站或登录。原站 `frontend` / 原数据库目标沿用前轮；数据库指纹本段没有重新 SELECT，只确认原 Site 配置 hash与已验收备份一致。两段实际只读盘点前后，12个原容器的完整过滤元数据（挂载规范排序）均一致；这是公开元数据保全，不能补证明 WebSocket 内部自动重启或前轮连续冻结事件。

核查辅助程序曾两次在 Docker 调用前停止：私有元数据顶层结构误识别、并行代理新增执行包被基线拒绝。修正结构、仅允许该精确授权文档新增，既有仓库文件 hash保持后，实际盘点成功；不把准备程序错误写成恢复环境失败。辅助程序仅保存于本机私有临时文件，最终 hash在脱敏摘要中；没有安装到原站。

## 2. 实际原版本与组件

| App | 原站源码版本字面量 | 过滤源码树普通文件数 |
| --- | --- | ---: |
| Frappe | 16.26.3 | 3406 |
| ERPNext | 16.26.2 | 5184 |
| HRMS | 16.14.0 | 1833 |
| hb_attendance_app | 0.0.1 | 169 |
| hb_inventory_app | 0.0.1 | 71 |
| hb_lims_app | 0.0.1 | 256 |
| hbos_portal | 0.1.0 | 225 |
| hb_knowledge_app | 0.1.0 | 26 |
| hb_twin_app | 0.1.0 | 18 |

备份 `before.json` 已安装 App 集合与本段实际 `apps.txt` 九项一致；不以本段文件读取冒充新的 installed-app SQL 检查。HRMS 实际 commit为 `6aa125b976469cb1c342afa3ef07d381c88677e0`；Frappe / ERPNext Git commit读取 **UNAVAILABLE**，使用原镜像 digest及实际源码树完整 hash，不猜 commit。commit不是干净源码证明。

原 Python **3.14.2**、Node **v24.12.0**、cryptography **46.0.7**，分发元数据149项。Python env过滤树 **17622普通文件 / 384120721 bytes / 4个链接**，树 SHA为 `6aa2422a4ab12b167aec8824c22e4aab0e0770b4bf45545009ea891a34084021`。原 backend 的 Docker diff中 env有2061项：1745项属于 bytecode / cache路径，316项为其余文件或目录；不能由这些数量推断316个依赖包变更，也不能只用基础镜像代替现有 env快照。

原镜像仍为前轮 Frappe/ERPNext、MariaDB exact digest；Redis本地实际 digest为 `redis@sha256:ec5e187c913d422cdf60f4216a5fdfb95246792c6de6fe21ff5bed75cbfc8c23`。三者均 Linux / arm64，本段未 pull、build或 commit镜像。九 App包括镜像内 Frappe / ERPNext代码，完整 env、字体及构建资产均须另行私有快照，执行包已列明。

已读取 Frappe dist86文件、ERPNext dist22文件、共享 assets70文件 / 6链接、fonts2文件，以及 frontend LIMS dist91文件。`sites/assets/hbos-lims` 不存在，不凭猜测把它作为恢复映射；LIMS实际挂载位于 App public/hbos-lims。各树 hash与字节数见摘要。backend与frontend使用不同树记录结构，不能直接比较两算法的hash。

过滤树排除 `.git`、`node_modules`、`__pycache__`、pyc / pyo；没有盘点全部 Node依赖内容。逐普通文件读取前后 stat一致，不等于全树原子快照。**复制前 / 后、快照及恢复端的同算法 SHA、合法链接映射、权限 / UID和原版本导入仍待执行**，运行闭包只能记 INVENTORIED_NOT_CAPTURED。

## 3. 备份、密钥与文件落地

宿主同次五备份的完整 SHA / bytes与前轮逐项匹配，仍0600 / 当前 euid / 单硬链接；before / 原 manifest另记 hash。database gzip完整读取通过，解压 SQL **29683935 bytes**。归档未变，public0 / private9 / auth2普通文件；只读复核实际前缀允许单一 `./`，Linux原 uid/gid1000:1000。没有文件落地或复制 UID保全验证，不直接 `extractall`。

实际原 `frappe/utils/password.py` SHA为 `083942571bcfa0ae9642b182146f8384eaa73a0b687061fd3a26af60332c2b1b`，确认使用 Fernet；缺失key时 `get_encryption_key()` 会写配置。未来只向短生命周期进程显式交付备份 key与真实密文，不调用该自动生成路径、不输出明文或异常内容。密钥存在仍不等于解密成功。

`__Auth` dump INSERT跨行，不能按行或逗号拆分；原完整六行 SHA保留为独立校验。原始密码hash（encrypted=0）不解密；必须核对全部doctype / 行及独立指纹后验证实际encrypted=1。本段完整记录解析与实际解密均 **NOT_RUN**，密文用例适用性 **NOT_VERIFIED**；只有后续完整解析证明没有适用密文，才记 **NOT_APPLICABLE**。不能生成 canary充当原密文恢复 PASS。

## 4. 执行提案与实际缺口

唯一拟标签 `hbos-owned-site-restore-20261010-a7d3`：5容器、0个新Docker网络、9新卷、1个受限宿主HTTP转发进程及唯一私有临时根，均 **PROPOSED / NOT_CREATED**；复用原镜像内已有bench及已安装App快照，禁止初始化 / 安装 / migrate / 下载。原卷、原 App目录、原DB/Redis及Docker socket均不接入。无worker / scheduler / websocket或外部集成。

拟入口 `http://hbos-restore.localhost:18092`，仅宿主受限进程监听 `127.0.0.1`，五个Docker容器均不发布端口。实际解析127.0.0.1和::1、18092无listener、拟目录不存在、名称无碰撞；这些采样不是入口或浏览器连通 PASS。不同主机名用于 Cookie隔离；同次SQL还包含 `tabSessions` CREATE / INSERT，**空Redis不作废SQL旧会话**。先核对原始导入指纹，再仅在克隆DB作废恢复的Sessions并实测旧SID拒绝。会话失效是明确的克隆写入提案，原账号密码 / 角色 / __Auth及原会话不动。

准备时的单一internal bridge提案不能实现peer端口白名单，已弃用。修订提案为新DB `network=none`，其余四个容器仅共享本次新DB精确ID的网络空间，五个可信克隆组件在该loopback互连；不宣称它们之间有端口ACL。宿主转发只经固定新backend精确ID的受控exec访问该空间的frontend，不提供任意URL、CONNECT或WebSocket转发。[Docker none说明](https://docs.docker.com/engine/network/drivers/none/)及[container共享网络说明](https://docs.docker.com/engine/network/)支持这些基础机制；本方案成立是设计推论，**不是本机隔离PASS**。

转发代码、真实请求白名单、固定命令 / UID / capabilities / 挂载矩阵及克隆密码登录的完整原生有限副作用尚待交付，实施仍 **NOT_READY**。新资源获精确许可后，首先以无恢复数据、无App启动、无公开入口状态核验新namespace仅lo、无原环境连接和对外路由，再做固定目标的拒绝探测；不把timeout单独计作隔离PASS。失败即清理，不加载私有恢复数据、不扩大到NET_ADMIN / 特权或改原防火墙。网络实测与完整环境仍 NOT_RUN。

宿主可用空间采样 **277103665152 bytes**，容器文件系统可用 **450202763264 bytes**；执行包采用各至少20GiB的初步预检阈值。容器文件系统可用空间不是宿主物理容量或新卷配额保证；恢复解压 / 重复副本 / DB索引及redo / 日志峰值尚未证明，执行前须再次预算和实测。恢复30分钟 + Owner验收15分钟、清理另最多10分钟是提案预算，当前未计时或创建资源。

Owner登录仅限原账号密码向克隆站创建新原生会话，会写克隆Session / 登录日志，不能称整段只读。Owner本人 / 业务验收不由代理伪造会话代替。**具体资源创建、私有快照落地、克隆配置和会话差异、运行入口及清理须获对应精确许可**；前轮原站10分钟备份窗口不能扩张。本段完成可审查提案，不执行新环境。

## 5. 状态与接续

下一段先交付和离线审查安全恢复工具、快照 / 命令挂载矩阵与转发请求白名单，使创建运行动作可以具体复核；该准备不创建资源。之后才核对Owner对精确资源、克隆有限写入及运行 / 清理的许可，按门禁捕获运行闭包、验证隔离、完整落地与原版本运行，最后由Owner本人登录。技术门禁失败时停止对应阶段，保留真实结果；不以许可替代技术通过，也不把原站WebSocket未验证项包装为克隆验收已解决。

原站管理 GET **NOT_READY**、事实 POST关闭、真实Grant **NOT_RUN**；八管理表缺失沿用前轮只读预检，本段未重查 / 建表、写根锁、人员、政策、pins或启管理工厂。**S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，P4-F6-5 REVIEWING**，Q1/Q2、Date、MG12/MG19/MG20/MG21/MG22/MG23、固定P1 / 完整恢复 / Owner等门禁保留。

本段相对开始时基线仅15份文档 / 脱敏证据变更，已有应用 / 前端 / schema / 配置 / Compose文件hash保持；没有重复运行前序应用测试或浏览器业务验收。收尾检查 PASS：资源提案5容器 / 0网络 / 9卷 / 1宿主转发一致、备份SHA一致、相对链接有效、已知私有值未命中、空白检查及辅助程序3.10 AST通过；独立文档复核剩余WARN / FAIL均0。这些检查不证明隔离或完整恢复通过。

状态台账、M2 Gate、本主记录、执行包、相关准备规范与公共入口已按本段事实同步；CLAUDE / AGENTS仅规则检查，无需修改。无新分支、提交、推送或部署。
