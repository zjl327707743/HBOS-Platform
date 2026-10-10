# M2：人员权限完整 Site 恢复执行组件实施记录

## 人员与权限：恢复卷、持久登记与清理离线验证 — 2026-10-10

当前进度 **S02_RESTORE_VOLUME_JOURNAL_CLEANUP_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[本轮主记录](M2_人员权限恢复卷与持久登记清理实施记录.md)、[验收摘要](evidence/人员权限_恢复卷与持久登记清理验收摘要_20261010.json)、[分阶段矩阵](evidence/人员权限_恢复分阶段资源矩阵_20261010.json)。**342/342离线PASS**，26文件Python3.10 AST通过。卷根权限tar / NoCopy守卫、固定持久日志及清理适配边界已实现，真实执行仍硬关闭。修正提案为两批同名五容器（累计最多10次创建、同时最多5个）、九卷、0新网络、1relay；阶段换代 / 可信采集尚未实现。

本轮实际3次Docker只读源码核验，五角色metadata前后MATCH，原SQL连接 / App import / 服务控制 / 资源创建均0。登录Hook的通知、客户供应商、MFA和动态写链仍未闭合；空卷daemon / 嵌套挂载、全量快照 / SQL / 文件 / key、listener / exec退出 / absence及Owner登录仍NOT_RUN或NOT_READY。下一步先接可信执行捕获与阶段登记，不提前申请不完整动作的运行许可。5178既有真实只读，管理GET NOT_READY / POST关闭 / Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING及全部旧门禁保留。状态 / M2 Gate / 当前主记录 / 执行包 / 公共入口同步，CLAUDE / AGENTS仅规则检查无需改动；无新分支、commit、push或部署。以下为前序历史，以本段及主记录为准。

**本文件下方222项及对应hash为前序交付证据，当前组件以新主记录为准，未覆盖旧摘要或矩阵。**

2026-10-10；状态 **S02_FULL_SITE_RESTORE_COMPONENTS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。本轮完成私有落地、有限 stdio / HTTP 转发组件和内存生命周期规划层，**222/222 离线 PASS**。完整 Site 恢复、容器卷落地、密文解密、真实网络和 Owner 登录均 **NOT_RUN**；生产执行 / 服务入口 **HARD_BLOCKED / NOT_READY**。

沿用 Owner 指定 m2-r11@27d3558，承接[前序安全层](M2_人员权限完整Site恢复安全工具实施记录.md)及[执行包](../plans/人员权限_完整Site恢复执行包.md)。本轮已读 CLAUDE.md、AGENTS.md、AI_CONTEXT、PROJECT_STATUS、CURRENT_MILESTONE、当前恢复资料和 Skill 路由；superpowers 不可用，按项目规则人工实施并交叉复核。未创建分支或 worktree。英文源码名遵循 Python 包 / release CLI 约定；新增交付文档均为中文 / 中英混合名称。

## 1. 交付与验证边界

| 组件 | 本轮实现 | 仍未证明 |
| --- | --- | --- |
| landing.py | 整批只读准入后同 SHA 冻结；仅全新固定 ROOT；保存五制品及 before，按原 Site 布局提取 public/private/auth；no-follow FD、独占创建、每个输出 SHA / bytes 最终和后续复验 | 仅合成文件实际落地。host 目录0700 / 文件0600 / 当前 euid；归档 UID1000与mode保留在原tar，容器内恢复 NOT_RUN |
| landing 清理 | 全树登记身份 / 内容校验，先原子无覆盖移至0700私有槽，再核 inode / 内容后删除；替换或碰撞拒绝并保留对象 | Darwin RENAME_EXCL 已实跑合成 fixture、Linux分支 NOT_RUN。依赖可信同 euid 独占，不能抵御任意同UID进程持续破坏私有槽；不是整个恢复环境清理证明 |
| wire.py / forward.py | 有限单帧协议 / EOF，32头 / 16KiB头 / 请求16KiB / 响应8MiB；固定IPv4 127.0.0.1:8080，连接2秒 / 读取5秒 / 总10秒，禁止DNS / proxy / redirect；真实HTTPResponse raw grammar与Content-Length后EOF核验 | 未访问真实socket或克隆HTTP；未知头、压缩与chunked拒绝。实际nginx / Frappe输出兼容仍待核 |
| transport.py | 单个完整HTTP/1.1请求编解码、独立Set-Cookie、connection close；固定Docker argv的有界stdio子组件，选择器读写、stdout / stderr配额、绝对期限及宿主child终止 / 回收 | 仅本地合成Python子进程；公开facade先硬闭门禁，不调用Docker。无宿主listener、真实exec ID / PID / 退出采集，宿主CLI回收不证明容器exec退出 |
| lifecycle.py | 固定5容器 / 0新网络 / 9卷 / 1relay范围、显式许可记录 / 非空原基线、创建意图及回执、首动作45分钟 / 清理10分钟不续期、父子任务、精确新鲜metadata清理argv与失败残留 | 仅内存纯规划；不执行回调 / create / rm / kill，无可信捕获 / 持久化 / 跨进程恢复。REAL形状proof也不能开启服务；清理decision永不executable |
| plan / ownership / relay | 增补只读runtime包与wrapper模板、固定启用标志提案；source PID1 UID观察独立于服务准入；user_lang和空user_image兼容有限政策，JSON home_page / redirect_to同Location精确限定 | wrapper / package未实际落地。所有服务命令不准入、UID / 新DB ID仍占位；原生页仅轮廓，空static清单 / CSP不运行Desk script，OTP不在白名单 |

固定范围与挂载见[本轮矩阵](evidence/人员权限_完整Site恢复执行组件矩阵_20261010.json)，全部 executable=false；前序94项和旧矩阵保留为历史证据，不覆盖。

## 2. 原站只读源码核验

本轮实际执行 **20 次 Docker 只读调用**：两段分别 inspect 五角色前后元数据、stdlib AST读取源码及 id / passwd / PID1身份 / binary位置；两段五角色过滤metadata均MATCH。没有原SQL连接、Frappe / App import、服务控制、镜像 / 容器 / 卷 / 网络创建或原配置写入。报告私有0600，公开摘要仅hash / 固定观察，未输出Env、配置 / key、SID、密码、SQL或人员行。第一次只读调用的自动审批传输中断，动作未执行；相同只读范围重试完成，无遗留审批阻断。

实际 PID1：backend / frontend 1000:1000，MariaDB 999:999，Redis 999:1000。它们不是全部1000:1000，原entrypoint与直接二进制也不等价；新空卷初始owner / 数据目录初始化和cap-drop/read-only运行仍未实现 / 验证。db/frontend观测sleep为/usr/bin/sleep，precheck /bin/sleep别名兼容未核。不得由这些观察把服务模板改为可执行。

登录源码发现：check_password可能因needs_update写克隆 __Auth；Session.start写Sessions / redis及User最后登录信息并运行通知；Frappe登录 / 会话Hook涉及Note、Activity Log和管理员通知，ERPNext会话Hook可能创建Customer / Supplier；hbos_portal还有accounts / security / native_read_boundary链，动态doc_events未展开。重置密码 / 2FA分支和通知后续链亦未闭合。**登录有限写入集合 NOT_READY**，不能只许可Sessions / Login Log / 三列User就启用真实登录。后续须按实际Owner用户与备份状态证明分支不触发或提出精确克隆写入范围；当前不开放通用RPC或业务写入。

## 3. 最终验证与审查

固定Python3.12.14 -B：**222/222 PASS**，input35 / ownership29 / relay23 / plan13 / landing36 / wire36 / lifecycle33 / transport17。20份源码 / 测试Python3.10 AST及空白检查PASS；默认CLI退出0 / stderr0，只打印不可执行提案，真实固定ROOT不存在。测试包括合成归档落地、真实stdlib HTTPResponse raw输入、本地Python pipe子进程；没有Docker转发、真实SQL / socket / 页面 / 登录，也未重复前序应用或前端测试。

交叉复核修复：输出同inode内容漏验、检查后删除的替换竞争、非法原始header使stdlib吞掉后续头、Content-Length后尾字节漏验；另修Connection-close socket生命周期。宿主组件追加巨大时限数值 / 伪造headers固定错误码及解码完成后绝对deadline再验。所有问题以合成回归复现并在最终版本复验；Cookie与JSON跳转政策也有有限回归。最终hash及审查限度见[验收摘要](evidence/人员权限_完整Site恢复执行组件验收摘要_20261010.json)。

OwnedLanding.cleanup必须独立记录，Registry的RECORDED_CLEAN仅覆盖其登记容器 / 卷 / 任务；不能称全部恢复对象已清理。未知创建结果、无法锚定对象、替换、未确认exec退出均阻止清理计划，不按prefix猜删。深层隐式目录可能在128项上限前部分落地后拒绝，拒绝不是事前零写入保证。私有槽最后移除也依赖同UID独占。

## 4. 接续顺序与保留门禁

下一段先闭合服务 / 卷初始化与真实创建回执 / 持久登记，再完成固定新DB SQL导入指纹、容器文件 / UID / mode落地、快照依赖闭包和实际适用密文验证；实现listener及exec ID / PID / fresh退出 / 全阶段失败清理联动；对实际登录Hook / 通知 / hash升级 / 2FA和完整请求清单逐条确认。当前动作尚未完整具体，不提前请求资源创建运行许可。只有可复核执行器与限定克隆写入范围完成后，才核对新的精确Owner运行许可；过去停写窗口确认不能替代。

5178保持既有真实只读，本轮未停启 / 刷新 / 改配置或改应用 / 前端 / schema / Compose；未作本轮浏览器在线复验。管理GET NOT_READY、POST关闭、Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING。八管理表 / 根锁 / pins / 政策 / 真人批准，以及MG12/19/20/21/22/23、Q1/Q2、Date、固定P1 / 完整恢复 / Owner及前序WS未核项全部保留。

状态台账、M2 Gate、本轮主记录、执行包、相关规范和公共入口已同步；CLAUDE / AGENTS仅规则，检查无需改动。无分支、commit、push或部署。改动前1330个普通文件SHA基线核对：本轮30文件（9新增 / 5修改源码测试，3新增 / 13修改文档），其余既有文件SHA不变、无删除；306个相对链接与空白检查PASS，3项既有私有配置值扫描命中0。独立最终复核确认222计数、20份源码 / 测试hash、矩阵 / wrapper及私有源码报告hash吻合，无新增缺陷；证据限度不因复核而扩大。
