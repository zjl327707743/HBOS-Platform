# 人员权限：完整 Site 恢复执行包

## 人员与权限：恢复卷、持久登记与清理离线验证 — 2026-10-10

当前进度 **S02_RESTORE_VOLUME_JOURNAL_CLEANUP_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[本轮主记录](../milestones/M2_人员权限恢复卷与持久登记清理实施记录.md)、[验收摘要](../milestones/evidence/人员权限_恢复卷与持久登记清理验收摘要_20261010.json)、[分阶段矩阵](../milestones/evidence/人员权限_恢复分阶段资源矩阵_20261010.json)。**342/342离线PASS**，26文件Python3.10 AST通过。卷根权限tar / NoCopy守卫、固定持久日志及清理适配边界已实现，真实执行仍硬关闭。修正提案为两批同名五容器（累计最多10次创建、同时最多5个）、九卷、0新网络、1relay；阶段换代 / 可信采集尚未实现。

本轮实际3次Docker只读源码核验，五角色metadata前后MATCH，原SQL连接 / App import / 服务控制 / 资源创建均0。登录Hook的通知、客户供应商、MFA和动态写链仍未闭合；空卷daemon / 嵌套挂载、全量快照 / SQL / 文件 / key、listener / exec退出 / absence及Owner登录仍NOT_RUN或NOT_READY。下一步先接可信执行捕获与阶段登记，不提前申请不完整动作的运行许可。5178既有真实只读，管理GET NOT_READY / POST关闭 / Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING及全部旧门禁保留。状态 / M2 Gate / 当前主记录 / 执行包 / 公共入口同步，CLAUDE / AGENTS仅规则检查无需改动；无新分支、commit、push或部署。以下为前序历史，以本段及主记录为准。

## 前序人员与权限：完整Site恢复执行组件离线验证 — 2026-10-10

当前进度 **S02_FULL_SITE_RESTORE_COMPONENTS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[本轮主记录](../milestones/M2_人员权限完整Site恢复执行组件实施记录.md)、[验收摘要](../milestones/evidence/人员权限_完整Site恢复执行组件验收摘要_20261010.json)。**222/222离线PASS**，20文件Python3.10 AST通过；安全私有落地、有限stdio / 固定loopback转发组件和内存生命周期规划已实现。真实ROOT / clone恢复 / 解密 / 网络 / 本人登录NOT_RUN，listener / 可信持久登记 / 全阶段执行清理未实现，生产服务HARD_BLOCKED。

本轮20次Docker只读源码 / UID核验，两段五角色metadata MATCH，零原SQL / 服务控制 / 真实资源创建。源码PID1为Frappe1000:1000、DB999:999、Redis999:1000；新卷初始化未核。登录hash升级 / Hook / 通知 / 重置 / 2FA副作用未闭合，有限写入NOT_READY。下一步先补这些运行门禁及执行器，不提前请求创建运行许可。5178保持既有真实只读，管理GET NOT_READY / POST关闭 / Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING与所有旧门禁保留。状态 / 本轮主记录 / M2 Gate / 相关规范 / 公共入口同步，CLAUDE / AGENTS仅规则检查。无新分支、提交、推送或部署。以下前序记录只表示当时状态，以本段为准。


2026-10-10；状态 **EXECUTION_PACKAGE_GUARDS_IMPLEMENTED / REVIEWING / FULL_SITE_RESTORE_NOT_RUN**。[离线安全校验层](../milestones/M2_人员权限完整Site恢复安全工具实施记录.md)与[94项测试 / 真实备份校验证据](../milestones/evidence/人员权限_完整Site恢复安全工具验收摘要_20261010.json)已交付；[命令 / 挂载矩阵](../milestones/evidence/人员权限_完整Site恢复命令挂载矩阵_20261010.json)为不可执行模板，实际UID / entrypoint、完整恢复执行器、listener / stdio传输、创建登记与全阶段清理仍未完成。最小HTTP政策已实现不等于运输实现，**NETWORK_ENFORCEMENT_NOT_READY / RELAY_NOT_IMPLEMENTED**。本文件不是创建或启动恢复环境的授权；完整Site文件落地、密钥解密、原App启动、Owner本人登录及业务恢复仍NOT_RUN，未创建容器、卷或转发进程。

沿用 Owner 指定的 `m2-r11@27d3558`。承接[原站备份与隔离 SQL 验收记录](../milestones/M2_人员权限原站备份与隔离SQL验收记录.md)及[M2 门禁](../milestones/M2_START_GATE.md)。同次备份 SQL / 归档验证 PASS 不代替完整 Site 恢复，原站管理 GET 仍 NOT_READY、POST 关闭、真实岗位 Grant NOT_RUN；5178 继续既有真实只读。

## 当前执行提案（本轮修订，尚未许可或执行）

上方222 / 94项及对应阶段描述为历史；下方资源、分阶段流程与门禁已按本轮组件交付修订，以新验收摘要与分阶段矩阵为准。

## 1. 待 Owner 明确许可的提案

仅为本次恢复验收创建、运行和清理下列精确资源，统一所有权标识为 **`hbos-owned-site-restore-20261010-a7d3`**。所有资源目前均为 **PROPOSED / NOT_CREATED**。原 Site `frontend` 仅作为备份来源；克隆 Site 仍叫 `frontend`，但位于本次独立 sites 存储、连接本次新数据库实例，不连接原数据库或原 Redis。

授权须覆盖：下列五个精确容器名的两批创建（预检 / 卷初始化五个，移除后服务五个；累计最多10次、同时最多5个）、九个新卷、唯一具名宿主 HTTP relay 进程及其受控 exec 子进程、全量私有快照与恢复文件落地、新实例 SQL 导入、仅克隆配置的允许差异、离线密钥验证、受限 loopback 入口、Owner 原账号密码登录产生的限定克隆写入、运行时间以及精确清理。自定义 Docker 网络数量为 **0**。此前最多十分钟的具名原站备份窗口已经结束，不能扩张为本次资源创建、运行许可，也不允许再次停启或冻结原服务。

已交付输入 / 元数据 / 最小HTTP政策、私有落地、stdio组件、内存生命周期、卷根权限tar、固定持久日志及清理适配边界，并通过离线回归；真实既有备份校验是前序证据。本轮卷 / 日志 / 清理组件只在合成环境验证，没有真实daemon捕获或操作。下一步补可信创建与退出捕获、两阶段换代、SQL指纹 / 文件 / 密钥执行器和登录有限副作用，使动作完整可审查；当前不创建资源或提前请求许可。完成工具和实际范围审查后，再取得Owner对全量快照、资源创建、克隆启动与登录验收的精确许可；许可不代替技术门禁。

该路径复用核实过的原镜像内**已经存在的** `/home/frappe/frappe-bench`，恢复已经安装 App 的源文件与资产快照；不执行 `bench init`、`bench new-site`、`bench new-app`、`install-app` 或 `migrate`。这与 `AGENTS.md` 禁止的“创建 Frappe bench”“创建任何 Frappe App”初始化行为不同，但新克隆 Site、数据库和运行资源仍须本次精确许可，不从“下一步”推导为已获创建授权。

## 2. 唯一资源清单与原资源排除

私有工具根目录固定为 `/private/tmp/hbos-owned-site-restore-20261010-a7d3`，0700；敏感普通文件0600。记录实际 owner、设备 / inode、无链接及单硬链接验证，拒绝目录已存在、祖先路径异常或目标碰撞。源五制品、before / manifest 与历史私有 staging 只读保留，不作为该目录的清理对象。

| 类别 | 拟创建的精确名称 | 用途 |
| --- | --- | --- |
| 容器 | `hbos-owned-site-restore-20261010-a7d3-db` | 新 MariaDB，唯一 SQL 导入目的地；`network=none`，作为本次网络空间锚点 |
| 容器 | `hbos-owned-site-restore-20261010-a7d3-redis-cache` | 新空 cache Redis；共享本次新 DB 精确 ID 的网络空间 |
| 容器 | `hbos-owned-site-restore-20261010-a7d3-redis-queue` | 新空 queue Redis；共享同一新网络空间，无任务消费者 |
| 容器 | `hbos-owned-site-restore-20261010-a7d3-backend` | 原镜像内 bench / 原生 WSGI；共享同一新网络空间 |
| 容器 | `hbos-owned-site-restore-20261010-a7d3-frontend` | 克隆静态资产与内部 HTTP 入口；共享同一新网络空间 |
| 宿主进程 | `hbos-owned-site-restore-20261010-a7d3-http-relay` | 唯一宿主 HTTP relay；仅监听 `127.0.0.1:18092`，记录精确 PID、启动时间、可执行文件及脚本 hash |
| 受控子进程 | 上述 relay 的具名请求任务及 exec 子进程 | 仅对本次新 backend 精确 ID 执行固定 Python 转发脚本；逐项登记任务 / 子进程身份、目的 ID、起止时间与退出结果，不增加容器 |

不创建自定义 Docker 网络（**networks=0**），不使用原网络。五个精确名称分两批使用，累计最多10个不同ID、同时最多5个；每批均不发布端口。宿主入口由唯一 relay 进程提供。宿主 relay 的部署脚本拟位于本次工具根目录的 `http_relay.py`；源码和 hash 须先审查，当前进程 / PID / 子进程及部署文件均 **NOT_CREATED**。名称只是所有权标识，清理还必须核对精确 PID、启动时间和可执行文件，不能按进程名批量结束任务。

九个拟用新命名卷如下，均须带本次精确所有权标识，不能复用同名旧资源或产生未登记匿名卷：

| 精确卷名 | 克隆挂载用途 |
| --- | --- |
| `hbos-owned-site-restore-20261010-a7d3-db-data` | 新数据库 `/var/lib/mysql` |
| `hbos-owned-site-restore-20261010-a7d3-redis-cache-data` | 新 cache Redis `/data` |
| `hbos-owned-site-restore-20261010-a7d3-redis-queue-data` | 新 queue Redis `/data` |
| `hbos-owned-site-restore-20261010-a7d3-sites` | bench `sites`，仅克隆文件 |
| `hbos-owned-site-restore-20261010-a7d3-logs` | 克隆日志，不进入公开证据 |
| `hbos-owned-site-restore-20261010-a7d3-assets-data` | bench `assets` 与 `sites/assets` 同一新卷 |
| `hbos-owned-site-restore-20261010-a7d3-frappe-dist` | 恢复的 Frappe 构建资产 |
| `hbos-owned-site-restore-20261010-a7d3-erpnext-dist` | 恢复的 ERPNext 构建资产 |
| `hbos-owned-site-restore-20261010-a7d3-hbos-lims-dist` | 恢复的 LIMS 构建资产 |

九个源 App（包括原镜像中的 Frappe / ERPNext 代码）、字体和完整 bench `env` 依赖快照，只从本次私有工具根目录的具名子目录只读挂载到对应 bench 路径。依赖环境必须来自实际原站完整私有快照，不能新安装或仅以基础镜像代替。必要的镜像声明 VOLUME 必须由以上精确新卷覆盖；若实际镜像需要额外卷或不能按此清单启动，停止并修改提案，不临时增加资源。

执行前保存原容器、网络、卷、挂载、端口与公开进程状态的完整基线，明确排除 `hbos-m0-r3a` 原站、`hbos-portal-preview` 及其他既有环境的全部资源。任何原卷、原 App 目录、原 sites、原 DB 或 Redis 端点都不得成为克隆挂载或写入目标，**即使只读挂载也不接入原数据卷**。不挂 Docker socket、原服务 UNIX socket 或其他宿主服务通道，不使用 host 网络、NET_ADMIN 或特权模式，不执行全局 prune、Compose down、按名称前缀批量删除或原服务 stop / pause。宿主 relay 使用 Docker CLI 仅作为执行本次固定转发程序的受控传输；不得提供 Docker API、任意容器 / 命令 / URL 选择或通用 exec 入口，不对任何原容器执行转发命令。

本次不创建或启动 websocket、worker、scheduler、configurator、create-site、前端构建或外部集成服务。运行资源只限上述五个名称的两批容器（累计10 / 同时5）、九卷、唯一宿主 relay 及其受控子进程，不调用原 Preview / workspace / release 启动和清理脚本。

## 2.1 两阶段创建与卷初始化提案

容器命令和挂载固定在创建时，不能用start将预检sleep切换为业务服务。本版先创建五个同名预检容器：DB / 两Redis / backend使用`volume-initialize`，UID1000:1000、固定`/bin/sleep 2700`、read-only rootfs、cap-drop ALL，无私有bind；DB和Redis各挂一个NoCopy+RW新卷，backend只挂六个NoCopy+RW新卷（sites、logs、sites/assets、三dist），不重复挂assets别名。frontend仍为`namespace-precheck`，全部必要卷显式登记，内容只读，日志卷可写。实际镜像VOLUME完整覆盖、所有镜像sleep别名及启动兼容仍须核验。

卷初始化仅提议对已登记且停止的本次容器，用固定`docker cp -a - <新ID>:<固定现存父目录>`传入一个无payload的目录header，设置固定卷根UID / GID / mode。MariaDB为999:999 / 0700，Redis为999:1000 / 0700，Frappe卷为1000:1000（logs0700、其他0755）。不加入root exec、CHOWN capability或辅助容器。[Docker cp官方说明](https://docs.docker.com/reference/cli/docker/container/cp/)支持stdin tar与`-a`保留源UID/GID；实际daemon对NoCopy、read-only rootfs、已挂载目录的兼容、目标父路径及初始化后无额外文件均NOT_RUN。空卷tar codec和caller observation只能生成不可执行计划，旧observation可重复使用，不证明执行前fresh空卷。 sites与sites/assets的嵌套挂载可能生成mountpoint目录，使严格root-only空卷检查拒绝；这项采集 / 次序兼容保持NESTED_MOUNT_EMPTY_VOLUME_CAPTURE_NOT_VERIFIED，不能放宽碰撞检查后声称已通过。

无私有输入的namespace负例验收及卷检查通过后，按frontend / backend / 两Redis / DB最后的顺序移除首批容器，保留九卷；新建服务批的五个同名容器，新DB ID成为新的namespace锚点，其他四个不能复用旧DB ID。服务批重新核验netns / 内部正例 / 外部负例后才可继续。两批累计最多10次创建、同时最多5个，失败不自动创建第三批或追加卷 / 网络；未知删除或换代结果终止。当前Registry没有换代实现，service命令也不准入，此流程是修订提案，不是已取得的资源运行许可。

## 3. 执行前必须重新核验

本轮只读核查已取得以下实际源信息；完整项以脱敏证据为准。它们证明采样时的源清单，不证明已复制快照、启动恢复站或通过实际网络隔离：

| 源组件 | 本轮核实的镜像 / 版本 |
| --- | --- |
| backend / frontend 原镜像 | `frappe/erpnext@sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583` |
| MariaDB 原镜像 | `mariadb@sha256:efb4959ef2c835cd735dbc388eb9ad6aab0c78dd64febcd51bc17481111890c4` |
| 两个 Redis 原镜像 | `redis@sha256:ec5e187c913d422cdf60f4216a5fdfb95246792c6de6fe21ff5bed75cbfc8c23` |
| 实际 Frappe / ERPNext | `16.26.3` / `16.26.2` |
| 实际 HRMS | `16.14.0`，commit `6aa125b976469cb1c342afa3ef07d381c88677e0`；不替换成仓库兼容 lock |
| 实际 Python / Node / cryptography | `3.14.2` / `v24.12.0` / `46.0.7` |

九个源 App 为 `frappe`、`erpnext`、`hrms`、`hb_attendance_app`、`hb_inventory_app`、`hb_lims_app`、`hbos_portal`、`hb_knowledge_app`、`hb_twin_app`。这九个源码树以及 assets、dist、fonts 的 hash 已取得；**全量私有快照复制及恢复端 hash 比较尚 NOT_RUN**。恢复必须包括 Frappe / ERPNext 的实际代码，而不只是七个宿主 App。

实际 bench `env` 清单包括 **17,622个普通文件 / 384,120,721 bytes / 4个链接**，149项 distribution 元数据，清单 SHA256 为 `6aa2422a4ab12b167aec8824c22e4aab0e0770b4bf45545009ea891a34084021`。原容器 Docker diff 的 env 相关项为2061项，其中1745项 cache、316项其他变化；不能以原镜像单独声称依赖闭包完整。须复制完整私有 env，核对四个链接及所需解释器 / 库的实际目标，依赖只读挂载，不运行 pip 安装。源码和依赖镜像内路径保持兼容；不兼容时停止，不能新建 bench 或安装依赖修复。

源12个容器在本轮两段只读读取的前后元数据完全一致，原状态保全仅覆盖这些采样及核查字段。目标唯一目录和资源名本轮未发现碰撞，18092未发现 listener；执行前仍须重新确认。

以下全部以本轮脱敏证据及执行前的新核查为准，不把仓库 lock、历史元数据或源 hash 冒充恢复结果：

- 同次已验收备份的五制品、before / manifest、完整 hash / bytes、权限与安全归档成员；复制到私有恢复输入后再次核对。
- 原镜像精确 digest、九 App 实际源码、已安装 App 列表、脏工作区内容、完整 env、依赖和构建资产闭包。所有输入必须全量私有复制后再使用；源复制前 hash / 清单、复制后源稳定性 hash、快照 hash及恢复端 hash相符才通过。不能以本轮未执行复制的清单代替文件落地，镜像也不自动包含容器可写层变化。缺失项保持 NOT_READY，不执行 git clone、pip / npm 下载或升级补齐。
- `apps.txt`、必要 common 配置、所有源码与资产路径及符号链接目标的可还原性。合法资产链接必须仅解析到克隆快照，不能保留指向原挂载路径的有效访问。
- 备份 SQL、解压文件、九 App / 完整 env / 资产快照、数据库实际恢复占用和日志的容量初算；宿主 staging 文件系统及 Docker 存储各要求至少 **20 GiB** 可用空间作为预检阈值。该阈值与当前初算不是峰值已证：解压、重复副本、数据库索引 / redo / 临时空间、卷、日志仍须逐项预算并在执行前复核。历史或本轮空闲采样值不能代替峰值验证。
- 五个容器、九个卷、唯一目录及具名 relay / 登记文件全部不存在；宿主 `127.0.0.1:18092` 无 listener，拟用主机名解析符合约定。创建后还须确认新网络空间内的五个服务端口无碰撞；不创建自定义网络。源运行闭包在复制前后稳定。碰撞或不一致时终止，不换随机资源名、不改端口、不删除已有资源后重试。
- 每个容器的精确 image digest、entrypoint / command、运行 UID / GID、capabilities、九卷及快照的完整挂载目的地与只读 / 可写模式、必要 clone 配置 key 差异必须形成审查通过的矩阵。Docker 默认行为、镜像 VOLUME 或已有 source 路径不能代替显式矩阵；额外卷、网络、宿主通道或权限需求出现时停止并重审。
- 宿主 relay、固定容器内转发脚本、请求与参数白名单、协议边界、超时 / 体积 / 并发上限、错误与子进程清理均须离线审查通过。只固定 Docker 命令而未审查 HTTP 分派规则，或只列设计目标而未交付代码，仍记 NOT_READY。

原镜像只使用已核实的本地版本，不 pull、build 或 commit 新镜像。若镜像与已收齐快照仍不足以还原依赖，记录缺口，停止运行阶段。

## 4. 文件、SQL 与克隆配置差异

先在无公开入口阶段安全落地备份，逐项核对普通文件 hash、权限、路径和实际内容保全；拒绝绝对路径、`..`、设备 / FIFO、未批准链接及覆盖工具根以外路径。auth 归档恢复到克隆 Site 的 `private`，public/private files 按实际归档布局恢复，不凭文件名猜测布局。

全部 SQL 仅导入本次新 DB。确认目的容器精确 ID、实例身份和无原挂载之后才导入；原数据库名称即使被沿用，实例与地址也必须独立，不能只用名称证明隔离。先核对账号 / 密码验证记录 / 角色 / User Permission / 业务关联及约定全表指纹，再启动应用。

原配置完整备份与克隆派生配置分别私有保存，记录差异，不把 secret、原 db 名 / 密码、key、Cookie、SID、人员明细、完整日志或配置内容写入公开文档 / Git。仅允许下列克隆差异：

| 配置项目 | 允许的克隆变化 |
| --- | --- |
| DB / Redis | 仅指向新共享网络空间的固定 loopback：DB `127.0.0.1:3306`、cache `127.0.0.1:6379`、queue `127.0.0.1:6380`；新数据库连接凭据以0600文件交付；不改原生 User 密码验证记录 |
| 克隆会话 | 同次 SQL 含 `tabSessions` 数据；完成原始导入指纹核对后，仅在新 DB 清除全部恢复的 `tabSessions` 行，新 Redis 保持空；原站会话不受影响 |
| 入口 / Origin / Host | 宿主 relay 固定本次 loopback 主机名与端口；必要的原生 Site header 仍选择克隆 `frontend`；请求 / 响应边界按已审规则校验，禁止回跳原站 |
| 集成 / 调度 | 禁用外部 OAuth、通知、飞书 / AI / OCR等集成及调度；保留恢复输入原文，运行层禁用且核验实际生效 |
| Nginx / WebSocket | frontend 仅监听新空间 `127.0.0.1:8080`，upstream 仅为新 backend `127.0.0.1:8000` 和克隆资产；不依赖 websocket；`/socket.io` 固定失败响应且无原服务 upstream |
| 运行文件 | 必要 logs / cache / PID 路径均在克隆存储；禁用 Python bytecode 写入源码快照 |

加密 key 原样保留，不能为启动成功生成替代 key。管理配置 / 工厂保持关闭，不创建管理表 / 根锁 / 人员 / 政策 / pins，不执行权限或岗位 Grant。其他差异先中止并重新说明，不临时扩大许可。

新 Redis 从空状态开始，不复制原 queue / cache / SID，也不启动任务消费者。**仅清空 Redis 不会作废 SQL 中恢复的会话**；入口开放前，必须在精确新 DB 以事先核对的表范围清除恢复的 `tabSessions`，记录克隆删除前 / 后计数及旧 SID 无法恢复认证的真实检查。账号 / 密码 / 角色原始导入指纹先验，再单独记录这项有意的克隆会话差异；不删除 `__Auth` 或 User、角色、业务数据，不调用原站 logout 或 Redis。其他临时证明状态尚未审定，不能猜表批量清理；本次仅允许原生密码登录，恢复、改密、外部认证、集成及通用写入入口保持关闭，临时状态边界未通过时不公开入口。原 Redis 恢复仍单独 **NOT_RUN**；不把空 Redis 运行写成旧任务或会话已恢复。

## 5. 网络拒绝门禁与 Owner 登录

### 5.1 独立 loopback 与固定转发路径

新 DB 容器以 `--network none` 创建并作为本次网络空间锚点；创建后登记其精确新 ID，其余四个容器使用 `--network container:<该精确新 DB ID>`，不能按用户参数或名称查找替代目标。五个**受信恢复组件共享同一克隆网络空间**，服务仅使用下列 loopback 端口：

| 服务 | 克隆空间内的固定监听地址 |
| --- | --- |
| DB | `127.0.0.1:3306` |
| cache Redis | `127.0.0.1:6379` |
| queue Redis | `127.0.0.1:6380` |
| backend WSGI | `127.0.0.1:8000` |
| frontend HTTP | `127.0.0.1:8080` |

这五个组件之间可互访其 loopback，**撤回 frontend / backend 之间的 peer 端口隔离承诺**。该设计不提供组件间网络访问控制或任意服务器代码沙箱；如果验收仍要求逐组件端口白名单，应保持 NOT_READY 并另审方案，不能临时增加 NET_ADMIN、特权、宿主防火墙修改或其他资源补齐。

Docker 官方说明 `none` 只创建 loopback，默认不配置 IPv6 loopback；`container:<id>` 可共享另一容器的网络栈且不支持 publish / hostname / dns 等相关选项。这里将两个机制组合为克隆网络空间，是**依据文档的设计推论，不是本机已创建或验证的隔离证据**。[Docker none 驱动](https://docs.docker.com/engine/network/drivers/none/)、[Docker 网络说明](https://docs.docker.com/engine/network/)

唯一宿主 relay 拟监听 **`127.0.0.1:18092`**，浏览器入口为 **`http://hbos-restore.localhost:18092`**；所有 Docker 容器均无 publish，不增加 IPv6 / 0.0.0.0 监听。relay 校验请求后，仅以固定 argv 数组调用 `docker exec -i <本次新 backend 精确 ID>`，执行经过审查的既有 bench Python 和固定转发脚本；容器内脚本唯一 HTTP 目的地是 `127.0.0.1:8080`。这样请求仍经过本次新 frontend，再由其访问新 backend，不直接分派 Frappe 方法，也不接受客户端指定的目标地址、端口、容器或命令。

请求体 / 响应及必要 Cookie 仅经受限 stdin / stdout 管道传输，不放入命令行、环境变量、聊天或日志；不使用 shell、TTY、privileged exec 或任意命令拼接。Docker exec 依赖目标容器 PID 1 仍运行，因此 backend 退出、ID / 标签变化、协议错误或超时都必须立即失败关闭入口，不能自动选择替代容器。有限stdio与固定loopback转发组件已离线实现；listener、真实exec ID / PID / 退出捕获未实现，未对实际容器执行。[Docker exec 说明](https://docs.docker.com/reference/cli/docker/container/exec/)

### 5.2 relay 请求与会话门禁

relay 状态为 **COMPONENTS_ONLY_LISTENER_NOT_IMPLEMENTED / NOT_READY**。政策层23项离线测试覆盖零参数ping / 身份、login / desk轮廓、默认空的显式静态清单和唯一同源usr / pwd登录POST；16KiB请求 / 8MiB响应、32头 / 16KiB总头上限，拒绝额外query / 通用API / 跨源 / Domain / 外跳 / 协议歧义并固定脱敏错误响应。wire / forward / transport组件已实施连接2秒 / 读5秒 / 总10秒和有界stdio计时；公开facade硬关闭，未实现listener / 并发入口及真实exec退出采集，不把组件定时器称为全阶段清理保证。完整Portal资料与业务路径尚未验证；继续按下列规则补齐源契约与完整白名单，不先开通通用代理：

- 精确 HTTP method、规范化 path、RPC / `cmd` 与参数 key / 值范围；包括 query、表单或 JSON 中的命令、v1 / v2 / legacy 别名及冲突输入。不能以 GET、`/api/` 前缀或方法名后缀判断只读；未知方法、编码歧义、重复 / 冲突命令、额外参数与方法覆盖一律拒绝。仅明确列出的原生密码登录允许写入，其他 POST / 写 RPC、密码恢复 / 修改、OAuth、集成、任意文档操作与管理入口不通行。
- 只接受该入口的精确 Host；Origin 存在时须精确匹配，登录请求须通过已审同源规则及原生认证 / CSRF 契约核查。拒绝 absolute URL、CONNECT、WebSocket / Upgrade、任意转发目标与客户端注入的 upstream / Site / forwarded headers；固定必要的克隆 Site header。
- 正确处理重复响应头和多条 `Set-Cookie`，保留原生登录所需 Cookie 语义；核查 Cookie Domain / Path 与 Host，禁止覆盖原站或扩大到共享域。Location 仅可为已审克隆路径或该精确克隆 origin；外部 / 原站跳转须失败关闭，不能跟随。实际页面资源、脚本和连接也须留在克隆入口，不将容器无出站误当作浏览器无外部请求证明。
- 明确报文长度与分帧规则、请求体 / 响应体 / header 大小、连接 / exec / 总请求超时、并发和队列上限；拒绝异常 Content-Length / Transfer-Encoding、超限及不完整报文，去除 hop-by-hop headers。具体数值须写入已审工具配置，缺失时不能启动；不可无界读取、缓冲、排队或留下 exec 任务。
- 每项请求仅使用登记的新 backend 精确 ID，记录不含敏感内容的任务身份及退出结果；不得记录密码、SID、Cookie、请求 / 响应体、人员信息或完整异常。原生 Session / 日志、有限读取产生的原生缓存等写入应以实核源码列清，不能由 relay 白名单泛准所有 clone 写入。

仅换端口不能隔离 Cookie。Owner 原站 5178 与恢复站必须使用不同主机名。本轮实际解析 `hbos-restore.localhost` 得到 **`127.0.0.1` 与 `::1`**，均属 loopback；仅允许 IPv4 relay 监听。双栈解析不能证明浏览器实际选择 / 回退到 IPv4 或入口可用，**实际 IPv4 HTTP、浏览器连接及隔离验收仍 NOT_RUN**；不为可用性自动增加 IPv6绑定。再次核对解析、IPv4连接、Cookie Domain / Path、Host、Origin、登录后 Location 和资源请求均留在克隆入口。

不同主机名不能代替克隆数据库的旧会话作废，必须完成上一节的会话门禁。源 SID 仅允许从私有恢复输入在内存中取得并作为拒绝负例，测试请求仅发向精确克隆入口；不用于 Owner 登录，不向原站发送请求，不保存或公开会话内容。Owner 登录不得使用原站 Cookie / SID 或伪造本人会话。

### 5.3 实际拒绝验收与本人登录

**NETWORK_ENFORCEMENT_NOT_READY**。取得精确运行许可后，先在所列新资源的无私有恢复输入、无 App 启动、无宿主 relay listener 阶段，以已审固定命令核查新网络空间；不是本轮创建空容器实测。至少核验：

- DB 的 NetworkMode 为 none，其他四个精确新 ID 共享其空间；新容器 netns 相同、与原环境不同，空间内仅 loopback、无外部 / IPv6 默认路由、额外网络或 Docker 端口发布。核对 caps / mounts / proxy 配置，排除宿主与原服务 UNIX socket 等旁路。
- 无认证、无业务载荷地对既有原容器地址、host gateway / `host.docker.internal`、原站 8080 / 5178、公网 IP 及外部 DNS 执行限定连接拒绝探测；检查接口与路由并记录错误分类，不能仅凭某个目标 timeout 或未启动就声称隔离。
- 隔离前检通过后才落地私有输入；服务启动后，新 loopback 的五个固定服务按所需路径连通，原服务 / 宿主 / 外部仍拒绝。缺少实际内部正例或外部负例，都不能记网络 PASS。
- 宿主 relay 开放前完成原始导入指纹、clone `tabSessions` 作废、固定转发脚本 / 请求白名单与原生密码登录副作用范围核验；随后实际检查 ingress 允许、未知 / 写入命令拒绝、Host / Origin / Cookie / redirect / 资源边界和旧 SID 拒绝。任一失败撤回入口并停止，不临时增加网络、权限或修改原 Docker 防火墙。

通过隔离及技术检查后，由 Owner 本人以原账号密码登录，执行事先列明的账号资料与只读业务页验收。不重置原账号、不自动关联飞书、不代填密码、不跳往外部 OAuth。登录本身会写**克隆** DB / Redis 的 Session、User登录信息、认证日志与缓存等；本轮只读源码还确认Portal安全版本会进入Session，管理员通知 / ERPNext客户供应商创建 / User通知后置save / MFA有条件分支。实际克隆用户、配置、通知和凭据事实仍NOT_RUN，**有限写入NOT_READY**。须在运行前逐表 / 字段列入待许可差异及登录后指纹核对，不能泛准其他 User 或业务写入；未限定清楚时本人登录保持 NOT_RUN。原站保持不写。密钥解密检查不输出明文，仅记录成功 / 失败和必要脱敏指标。

本轮核实既有 `__Auth` 六行完整指纹、原生密码处理源文件及 cryptography 版本，但**备份凭据记录的完整解析尚 NOT_RUN，已有密文用例适用性为 NOT_VERIFIED**；不能从六行 hash 或库可用性推导不存在适用密文。恢复端文件落地 / key保全、实际解密运行仍 **NOT_RUN**。后续用已审解析机制完整核查备份中的各 doctype / field、encrypted 标记与全行指纹；`encrypted=0` 的密码 hash 不可称为可解密密文。只有完整解析确认不存在 `encrypted=1` 记录时，该用例才可记 NOT_APPLICABLE；若存在，须以原备份 key 验证已有密文，至少一条解密成功且适用记录无失败才可按实际范围记 PASS，失败即停止。不输出明文，不以新生成 canary 的解密推导原密文恢复 PASS；账号密码登录 PASS 也不能替代 key 保全或加密凭据恢复检查。

## 6. 运行预算、终止与清理

提案预算：恢复与技术核查最多30分钟，Owner 本人验收窗口最多15分钟；从首个新容器 / 卷、工具自有恢复目录落地或宿主 relay 运行动作中最早一项起计，满45分钟即停止新工作、撤回入口并开始清理，不由 relay 或容器重启重新计时。清理另有最多10分钟的有限等待预算，不把预算写成基础设施失败时必然完成的硬承诺。relay 的单请求 / exec 超时、并发、体积上限另外由已审配置限定，不得超过本次剩余窗口。Owner 未在窗口内完成时，本人登录 / 业务验收记 NOT_RUN，关闭资源，不无限保留克隆站。

以下任一情况立即停止：目标碰撞、容量不足、源闭包变化、备份 / 文件 / 账号指纹不符、依赖不完整、密钥失败、应用需迁移 / 安装才能启动、原资源被挂载或访问、网络拒绝门禁失败、relay ID / 白名单 / 协议检查失效、exec 任务无法收回、入口 / Cookie / redirect / 浏览器资源回到原站或外部、登录或读取出现未列明写入、出现原服务状态变化或超过预算。保留失败记录，不自动换目标、下载依赖、修改原站、关闭安全验证或重试扩大动作。

每项动作前持久写入意图，成功fsync并复验后才可由未来可信执行器行动；动作后捕获并持久写入名称、精确 ID、所有权标签、镜像、挂载、网络空间、端口与时间。固定日志组件已经实现，但尚未接入真实创建 / 清理执行器，首个ROOT创建的预动作证据及跨进程期限也未闭合；内存或手填回执不能替代。宿主 relay 记录 PID、启动时间、可执行文件 / 脚本 hash 及全部受控子进程 / exec 任务身份。清理首先关闭 relay listener、停止接收与排队，按登记身份有限等待并结束本次宿主 relay、Docker CLI 子进程及容器内转发 exec 任务；确认端口关闭和任务退出。再停止并删除 frontend、backend、两个 Redis，最后停止并删除 DB 网络空间锚点；不要在共享者仍运行时先移除 DB。仅删除当前阶段登记、清单内精确 ID 对应的本次容器及九个卷（两批累计上限10），**无自定义网络清理动作**；每项删除前再次核对标签、ID和无原挂载，不按前缀或进程名批量清理。删除临时凭据、SQL工作副本、PID / 登记文件和工具自有恢复目录，只保留获准的脱敏报告；源备份与历史私有 staging 保持不动。

清理失败时记录残留精确资源和拒绝原因，保持入口关闭，不执行全局清理或强行删除不明资源。核对本次资源无残留、原资源元数据和公开状态与基线一致；原数据库不是恢复目的地、原站配置 / 账号 / 权限未改。完整源数据“不变”的结论只覆盖实际核查的范围。

## 7. 结果与许可门禁

执行结果分别记录：文件落地 / hash、SQL 与账号业务指纹、依赖 / App 启动、key保全与现有密文用例适用性 / 解密、网络拒绝、本人登录 / 只读业务、资源清理和原资源保全。任一未运行项保留 NOT_RUN；没有已有密文的用例记 NOT_APPLICABLE，不记解密 PASS；不能以其他子项 PASS 替代。

**当前卷 / 持久日志 / 清理边界及前序组件已离线验证；完整恢复运行未获本次授权，两批容器（累计10 / 同时5）/ 九卷 / 唯一宿主 relay 及其受控子进程全部未创建，自定义网络为0。** namespace-precheck / volume-initialize守卫仅准入固定sleep/非root/readonlyrootfs，禁healthcheck、daemon日志none、restart=no；后者只允许受约束NoCopy+RW新卷，无bind或assets双挂载。不准入服务命令；阶段换代、可信创建 / 退出 / absence采集和完整执行清理仍HARD_BLOCKED。下一步完成这些接线及SQL / 文件 / key / 登录副作用门禁，保持 NETWORK_ENFORCEMENT_NOT_READY / LISTENER_NOT_IMPLEMENTED；不直接请求 Owner 批准未具体化的实施。完成这些工作后，再取得 Owner 对本文件的唯一资源、完整私有快照、克隆配置差异、loopback 本人登录窗口、运行预算和清理范围的精确许可，才可进入执行前复核和创建。源闭包、碰撞 / 容量 / 版本及实际隔离门禁依序核查；具体许可不能替代缺失技术门禁，历史备份窗口不能作为本次授权。

本执行包不放行正式管理 GET / POST、真实岗位 Grant、原站迁移或公司服务器部署。S01-B / S02 PARTIAL、C / S03—S06 NOT_STARTED、P4-F6-5 REVIEWING，以及 Q1 / Q2、Date、固定 P1、完整恢复 / Owner 与管理门禁继续保留。实际状态、hash、版本与未完成项以本轮脱敏证据及根代理同步的状态台账为准。
