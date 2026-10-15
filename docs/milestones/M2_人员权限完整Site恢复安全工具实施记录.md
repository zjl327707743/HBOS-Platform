# M2：人员权限完整 Site 恢复安全工具实施记录

## 人员与权限：完整Site恢复执行组件离线验证 — 2026-10-10

当前进度 **S02_FULL_SITE_RESTORE_COMPONENTS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[本轮主记录](M2_人员权限完整Site恢复执行组件实施记录.md)、[验收摘要](evidence/人员权限_完整Site恢复执行组件验收摘要_20261010.json)。**222/222离线PASS**，20文件Python3.10 AST通过；安全私有落地、有限stdio / 固定loopback转发组件和内存生命周期规划已实现。真实ROOT / clone恢复 / 解密 / 网络 / 本人登录NOT_RUN，listener / 可信持久登记 / 全阶段执行清理未实现，生产服务HARD_BLOCKED。

本轮20次Docker只读源码 / UID核验，两段五角色metadata MATCH，零原SQL / 服务控制 / 真实资源创建。源码PID1为Frappe1000:1000、DB999:999、Redis999:1000；新卷初始化未核。登录hash升级 / Hook / 通知 / 重置 / 2FA副作用未闭合，有限写入NOT_READY。下一步先补这些运行门禁及执行器，不提前请求创建运行许可。5178保持既有真实只读，管理GET NOT_READY / POST关闭 / Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING与所有旧门禁保留。状态 / 本轮主记录 / M2 Gate / 相关规范 / 公共入口同步，CLAUDE / AGENTS仅规则检查。无新分支、提交、推送或部署。以下前序记录只表示当时状态，以本段为准。


2026-10-10；状态 **S02_FULL_SITE_RESTORE_GUARDS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。本段交付离线校验层和不可执行的命令 / 挂载提案，完整恢复仍 **NOT_RUN**。运行执行器、监听 / stdio 转发与完整失败清理尚 **NOT_IMPLEMENTED**，不得据本段测试启动恢复站或放行管理功能。

沿用 Owner 指定的 `m2-r11@27d3558`，承接[完整 Site 恢复准备](M2_人员权限完整Site恢复准备记录.md)和[执行包](../plans/人员权限_完整Site恢复执行包.md)。本轮已读默认五文档、Skill 路由和上述当前资料；`superpowers` 在本环境不可用，按项目规则人工实施，三名代理分工并交叉复核。未创建新分支。

## 1. 本段交付

| 代码 | 实际作用 | 证据限度 |
| --- | --- | --- |
| `scripts/release/full_site_restore/inputs.py` | 五制品及 before / host manifest 的 SHA、bytes、FD 身份、权限、gzip CRC、安全 tar 成员及有限 JSON 校验 | 只读验证；不解密、不解析全表 SQL、不复制 / 提取 / 落地 |
| `ownership.py` | 固定 namespace-precheck 的镜像、ID、label、命令、网络、挂载、capabilities及原资源排除；重新核验后生成精确清理 argv；PID / 启动时间校验 | 只处理可信调用方提供的元数据；不运行 inspect / stop / rm / kill，不证明本轮创建或实际隔离 |
| `relay.py` | 最小 method / path / 参数 / Host / Origin 白名单、Cookie / Location / 分帧 / 体积与错误正文过滤，固定 exec argv 提案 | 没有 listener、HTTP / stdio 传输或子进程；超时 / 并发是待实施约束 |
| `plan.py`、`prepare_full_site_restore.py` | 默认输出固定提案；显式 manifest 仅按不可覆盖的已验收 SHA 读取校验；非法参数 / 文件错误固定码，不输出私有路径 | 无执行参数。服务 argv 有未验证 UID / 新 DB ID 占位，全部 `executable=false` |

入口与代码的英文名称沿用 Python 模块和既有 release CLI 命名惯例；新增主记录、矩阵与证据文件采用中文 / 中英混合名。[固定命令与挂载矩阵](evidence/人员权限_完整Site恢复命令挂载矩阵_20261010.json)列出 5 容器、0 个新 Docker 网络、9 卷、1 个宿主 relay。该矩阵是审查模板，不是批准或可执行启动命令。

## 2. 具体校验边界

输入叶目录须 0700 / 当前 euid，普通输入 0600 / 单硬链接；逐祖先与文件使用 no-follow FD 锚定，全部已准入文件保持打开至整批完成，再检查身份；晚期修改前面已验文件也拒绝。host manifest 恰好五个绝对同父路径，不能使用原容器 manifest；before 与五制品固定 hash 分离校验。归档只允许原布局的单一 `./`，uid / gid 1000，有限 mode、mtime PAX及成员 / 字节上限；拒绝路径穿越、链接、特殊文件、稀疏、重复规范路径、覆盖关系、未知 PAX和不完整 trailer。只公开索引成员 hash，不公开名称、配置 / key、SQL、认证内容或人员资料。校验通过不授予后续读取变化文件的落地能力，执行器必须重新绑定相同输入。

容器记录目前只接受非 root `1000:1000` 的固定 `/bin/sleep 2700` namespace-precheck 形状，拒绝任何服务启动命令；实际镜像内该命令 / UID 兼容性未验证。只允许本次精确新卷及ROOT内有限只读snapshot / runtime映射，要求非空可信原基线，拒绝旧资源、匿名卷、网络 / socket / 端口与host旁路；healthcheck禁用、daemon日志仅none、重启策略仅no / 0，避免内核无网络之外的daemon副作用。metadata 策略不能验证宿主 realpath 或内核路由，也不能替代创建登记与资源碰撞门禁。清理计划先验证全部新鲜 metadata再返回 exact ID，DB锚点最后；PID复用或 label / 挂载 / 配置变化均拒绝。它不是可运行的全阶段清理器。

最小 relay 只允许 GET 的 ping、身份、`/login`、`/desk` 页面轮廓，以及显式不可变静态路径（默认空）；唯一 POST 为精确同源的原生密码登录，只接收 usr / pwd。未开放通用 API / RPC、query、管理 GET、写业务、OAuth、密码恢复 / 修改、CONNECT或 WebSocket。拒绝编码歧义、重复 / 冲突 header / 参数、method override、Site / forwarded注入、跨源、压缩与未知协议。多条 Set-Cookie分别校验、host-only / 根 Path、sid HttpOnly，禁止 Domain扩张和原站 / 外站跳转；4xx / 5xx细节正文替换固定 JSON，CSP仅克隆入口。严格 CSP / 静态空清单尚不能提供完整原生页面或业务。

SID格式或新 ID格式不证明克隆会话 / 资源所有权。固定 exec 的 `1000:1000` 也是未执行提案，运输层须使用已验证资源和新鲜 inspect；旧 SQL Sessions仍须仅在新 DB先核导入指纹再作废，真实旧 SID拒绝 / 登录有限副作用与会话绑定尚未实现。

## 3. 验证与实际范围

**94/94离线PASS**（输入35、所有权29、relay20、计划10），Python3.12.14 -B，11份源码 / 测试的Python3.10 AST通过；结果与最终hash见[验收摘要](evidence/人员权限_完整Site恢复安全工具验收摘要_20261010.json)。默认CLI实际退出0、stderr0，明确NOT_IMPLEMENTED / runtime_ready=false。合成测试后，用同次已验收备份进行实际只读校验PASS：五制品 / before SHA和完整gzip、public0 / private9 / auth2及全部有限归档规则通过；SQL解压29683935bytes。没有提取或落地，该校验不证明恢复、解密或App运行。对抗输入均为合成数据；没有Docker调用、原SQL连接、网络访问、Frappe初始化、真实凭据登录、资源创建或删除。已有应用 / 前端 / schema / 配置 / Compose不在本轮改动范围，原服务未停启或刷新。本轮不重复前序应用 / 前端测试，也不把历史隔离SQL PASS计入本段测试。首次input测试全局PAX错误码分类不一致已修正并全回归；首次relay使用系统Python3.9因slots不兼容而未进入测试，改用指定3.12后通过。收尾复核补整批FD保留与2项晚期mutation回归，以及healthcheck / daemon日志 / restart拒绝与3项对抗回归；最终均已重跑，不以加固前89项采样代替。独立审查限离线层，实际运行门禁不计PASS。收尾确认本轮26文件（11源码 / 测试、15文档 / 脱敏证据），其余既有文件SHA保持，已知3项私有配置值扫描命中0、276相对链接及空白检查通过；最终独立文档 / hash复核无阻断。

## 4. 接续与门禁

下一段先完成实际源 UID / entrypoint / 有限登录副作用复核，以及恢复执行器、私有文件安全落地、固定转发运输、创建登记、截止时间与全阶段清理的代码和离线审查。当前不询问创建运行许可；只有动作完整、具体可审查后，才核对 Owner 对快照、精确资源、克隆限定写入及运行 / 清理的许可。技术门禁仍需真实执行，不由许可或合成测试代替。

完整快照 / 依赖链接闭包、真实网络隔离、全量 SQL 指纹、文件落地、真实适用密文解密、旧 SID拒绝及 Owner 原账号 / 业务验收仍 **NOT_RUN / NOT_READY**。原站管理 GET **NOT_READY**、POST关闭、真实 Grant **NOT_RUN**；5178 保持既有真实只读，本轮没有浏览器在线复验。八管理表、根锁、政策 / pins / 真人批准及 MG12/MG19/MG20/MG21/MG22/MG23、Q1/Q2、Date、固定 P1、前序 WS 未核实项与 Owner门禁保留；**S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，P4-F6-5 REVIEWING**。

状态台账、M2 Gate、执行包、准备主记录、相关规范与公共入口已同步；CLAUDE / AGENTS仅规则，收尾检查无需改变。无新分支、提交、推送或部署。
