# M2：人员权限原站备份与隔离 SQL 验收记录

2026-10-10 后续接续：[完整 Site 恢复准备](M2_人员权限完整Site恢复准备记录.md)现为 **S02_FULL_SITE_RESTORE_PREPARATION_REVIEWED / PARTIAL / REVIEWING / 5178_REAL_READONLY**，本段运行闭包只读盘点和具体提案已形成；完整恢复仍NOT_RUN。下方保留上段备份 / 隔离SQL的实际验收状态与失败历史，不代表新窗口已获许可或新环境已创建。

2026-10-10；状态 **S02_ORIGINAL_BACKUP_SQL_RESTORE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。Owner 已允许现在进入不超过10分钟的原站服务窗口；同次私有备份、宿主转存和隔离 SQL 验收已实际完成。**完整 Site 恢复、密钥解密、Owner 本人登录及业务恢复仍 NOT_RUN**，原站管理读取仍 NOT_READY。

沿用 Owner 指定的 `m2-r11`，没有创建或切换分支。本记录承接[原站只读预检](M2_人员权限原站只读预检记录.md)，实际脱敏汇总见[备份与隔离 SQL 验收摘要](evidence/人员权限_原站备份与隔离SQL验收摘要_20261010.json)。私有日志、SQL、配置、认证内容、账号及人员明细不进入本记录或 Git。

## 1. 目标、授权与执行范围

固定既有 Site `frontend`、bench `/home/frappe/frappe-bench`、数据库 SHA256 `98d2b2166d96e1969c24b420238b40e82a7572a59105b5e31d4f6f215b6aa4cb`。原 backend / DB / Redis 保持原容器；备份通过现有 bench 执行，没有安装 App、创建 bench / Site、迁移管理结构或改变原账号目标。**source_db_destination=false**：原数据库从未作为 SQL 恢复目的地。

本次允许的影响包括原 frontend、scheduler、两个 queue 的停止及原态恢复，以及原 WebSocket 精确 ID 的 Docker pause / finally unpause。该授权用于本次具名窗口，不代表后续任意停服许可。Owner 窗口已执行，不再使用 WINDOW_UNCONFIRMED 描述本轮。

仓库工具原样交付和执行，源码锁定如下：

| 工具 / 镜像 | 精确依据 |
| --- | --- |
| prepare_existing_backup.py | `5803439792af5e98f706664d1d812ea635686245a7acd2d9007a20ea7d4f2bf3` |
| verify_backup_restore.py | `6ad6151c6dc626a7c3eb5623f4c24a21f9dc267c40cc89b2bbf9f2aca51718b0` |
| MariaDB 原版本镜像 | `mariadb@sha256:efb4959ef2c835cd735dbc388eb9ad6aab0c78dd64febcd51bc17481111890c4` |

宿主 Docker CLI 使用已核实的 `/Applications/Docker.app/Contents/Resources/bin/docker`。恢复执行在原服务恢复后进行，不延长备份窗口；工具恢复阶段预算20分钟，finally 清理另有有限等待，不把它写成20分钟硬总时限。

## 2. 窗口实际结果与失败记录

| 执行段 | 实际结果 | 保留的限度 |
| --- | --- | --- |
| 第一次窗口 | 备份 NOT_STARTED；原报告 backup=UNVERIFIED / source_service_recovery=FAIL，窗口210.799857秒 | WebSocket 未完成退出；恢复段有错误。报告内12个原容器最终公开状态均匹配，不覆盖原 FAIL |
| 第二次窗口 | 备份 NOT_STARTED；原报告 backup=UNVERIFIED / source_service_recovery=FAIL，窗口211.467277秒 | 同样未进入备份；12个原容器最终公开状态匹配，不把原恢复段错误抹去 |
| 另拟 probe / attempt3 | NOT_RUN | 未执行，不计入验收或制造成功记录 |
| 第四次窗口 | backup=PASS / source_service_recovery=PASS，窗口 **8.400962125秒**，WITHIN_600_SECONDS | 已知生产入口 / 消费进程静止有执行器证据，仍受下述全局及连续性限制 |

成功窗口 UTC：`2026-10-10T06:52:29.546382+00:00` 至 `2026-10-10T06:52:37.947961+00:00`。备份捕获 UTC：`06:52:32.741914` 至 `06:52:36.606874`，在该窗口内完成。

已纠正进程信号位掩码解释：WebSocket 未注册 INT / TERM 处理器，不能把早先 stop 请求等同已退出。成功窗口使用原 ID 的 Docker pause，finally 对同一原 ID unpause；没有新增强杀或重建。**WebSocket 自动重启内部语义 NOT_VERIFIED**，前两次 stop 请求对内部自动重启状态的影响没有得到证明。

窗口前及停止消费者前，正确 RQ 连接实际发现两个有效 idle worker，均无 current job，采样 queued_count=0 / started_count=0。两个 queue 实际 warm exit，**exit_code均0**；恢复后实际两个注册 worker为 idle、无 current job、订阅存在。旧“只见一个记录、两 worker 未验证”的准备描述不再适用于本次结果；空 queue / started key 列表仅描述该采样，不能推导永久无任务。

原站来源账户无法读取全局在途事务，仍 **UNKNOWN / UNAVAILABLE**。Docker 事件缓存上限256，后查 WebSocket 事件返回空，不能证明整个区间连续冻结、没有迟到 stop 事件，或内部自动重启状态已恢复。**连续冻结与 late stop 事件完整性 UNKNOWN**；本轮不宣称全球一致快照、全库零写或完整服务生命周期恢复。

## 3. 同次私有备份与源保全

同次 audit 叶目录0700 / uid1000，五个组件及固定 before / manifest 均按私有权限保存；源文件0600、非链接、单硬链接及完整 SHA / bytes 核验通过。唯一同次 stem 与五组件严格匹配，manifest 恰包含 database / site_config / public_files / private_files / auth_files。完整 gzip CRC **PASS**。

| 组件 | bytes | 完整 SHA256 |
| --- | ---: | --- |
| database | 2645386 | `c2f3c190095224ae075867582cedb5bd831a7fd7c9c7481d8f3df27ecccceac9` |
| site_config | 1259 | `533a2b31faf6265df003d6fa2fc1bc42fa9fa70778a4fa5c5d08c8c8ec37b89a` |
| public_files | 10240 | `ec494d1950ae0bfe001150421a8218b5e9a3fb99cdf2e7b34e54769db87e00ed` |
| private_files | 174080 | `cc581cc045fd49b226d536816e5631a43f84b02ef3a74f0751e81c2c7675f3f5` |
| auth_files | 293 | `56043bd376e2366ec8dff632feea3184f798558dac2a2772404928ab3d3aab20` |

原生备份 retention 清理影响到旧文件后，执行器从本轮预先保存的私有副本恢复了全部 **4个旧普通文件**，完整 SHA 保全 PASS；**2个既有目录**已归还，目录保全 PASS。不能把这次恢复保全写成原生 backup 从未改动旧制品。三个 tar 的普通文件成员数分别为 public0 / private9 / auth2；源文件内容匹配 PASS。auth 仅包括原有两份飞书私有文件；knowledge gateway token 原本缺失仍缺失，不新增、不推断集成状态。

八个原生表的完整行指纹、计数在备份前后一致，`native_full_rows_unchanged=true`：

| 表 | 前后 rows | 完整行指纹 |
| --- | ---: | --- |
| User | 18 | 相同 |
| Employee | 0 | 相同 |
| Company | 1 | 相同 |
| Department | 14 | 相同 |
| Designation | 31 | 相同 |
| Has Role | 963 | 相同 |
| User Permission | 0 | 相同 |
| __Auth | 6 | 相同 |

common 配置前后 SHA均为 `caa296533e604fb712977e422092b8e77463ff72ac8c85e69b4c12b197b409bf`，site配置前后 SHA均为 `533a2b31faf6265df003d6fa2fc1bc42fa9fa70778a4fa5c5d08c8c8ec37b89a`。这些具体表和配置的保全证据不能外推成全部数据库未写入。

## 4. 宿主转存、隔离 SQL 验收与清理

源五制品和固定 before / manifest 转存至全新宿主0700工具自有 staging；文件0600 / 当前 euid / 单硬链接 / 双端完整 SHA及bytes全部匹配。容器 manifest 路径映射到实际宿主路径，映射及原文保持私有。源 audit 与两次工具自有 staging 均保留；没有删除旧备份、源配置或原容器。最终 staging 另存恢复前原容器过滤元数据，方便核验。

每次恢复均创建独立工具自有 MariaDB：实际运行期间核验 **network=none、published_ports=0、original_volume_bindings=0**，只读挂载工具自有临时凭据，数据库卷为本次新建卷。镜像 EXPOSE 的空绑定不算宿主发布端口。全部 SQL import / 查询 / stop绑定该次新容器精确 ID，原 sites / DB卷没有作为挂载或恢复目的地。

| 恢复段 | SQL / 指纹 / 归档 | 外层结果及原因 |
| --- | --- | --- |
| 首次隔离恢复 | 全部 PASS；新容器 / 卷 / 凭据 / import进程清理 PASS | 外层 FAIL：Docker 返回 Mounts 数组顺序改变，直接列表比较误报 original_container_metadata_preserved=false；原报告保留 |
| 修复后再次隔离恢复 | 全部 PASS；原容器完整过滤元数据及全部清理 PASS | **最终外层 PASS**；对完整挂载记录作确定排序，保留所有字段，不放松元数据比较 |

根代理独立三次读取原12容器：9项只有 Mounts 数组顺序变化，3项原数组亦稳定；完整挂载项规范排序后语义一致，12项公开状态匹配。最终恢复报告 `original_container_metadata_preserved=true`，自有容器 / 卷 / 凭据目录均移除，SQL import进程已关闭。

完整 SQL 恢复所得 **User18 / User认证6 / User角色103**；账号、密码验证记录、User角色、User Permission、存在时外部身份和业务关联指纹 PASS，三个 tar完整安全可读 PASS。这里103仅统计 parenttype=User的角色行；源表 Has Role 全表963行口径不同，不是保全缺失。site_config包含 encryption_key 的存在检查通过，未输出其内容，**尚未验证实际解密**。

恢复后匿名实际可用性：8080 Frappe ping、5178 Portal ping和人员页均HTTP200，ping为pong。原两个RQ worker恢复注册且idle；这是匿名连通及当次进程观察，**Owner 本人登录 / 业务验收 NOT_RUN**，不伪造会话代验。

## 5. 保留门禁与接续

完整 Site 的公私 / auth 文件落地、密钥实际解密、原版本Frappe及所有挂载App运行、Owner本人原账号登录和业务恢复均 **NOT_RUN**。SQL / tar PASS 不放行完整恢复、原站管理 GET、事实 POST或岗位 Grant。

前序原站预检已指出八管理表缺失，本次没有以备份结果代替结构预检；没有创建管理 schema / 根锁 / 人员来源 / 政策 / pins或安装管理工厂。5178保持已确认页面与既有真实只读路径。下一段先形成精确完整 Site 恢复目标、文件 / 密钥 / 版本运行及销毁范围，再按相应门禁执行；具名真实管理主体和批准、结构准备及查询启用仍须各自核验。

**S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，真实 Grant NOT_RUN，P4-F6-5 REVIEWING**。Q1/Q2、Date、MG12/MG19/MG20/MG21/MG22/MG23、可信内部SQL非沙箱、固定P1 / 完整恢复 / Owner门禁保留。14原生 / 428离线等为前序证据，本段无应用代码改动，未重跑应用测试、未做真人浏览器复验。

本轮已同步本主记录、[窗口执行包](../plans/人员权限_原站备份停写窗口执行包.md)、[备份准备范围](../plans/人员权限_原站只读预检与备份恢复准备范围.md)、正式启用清单和配置规范顶部；PROJECT_STATUS / CURRENT_MILESTONE / M2 Gate / 公共入口及脱敏证据已按实际结果更新。CLAUDE / AGENTS规则检查无需修改。未创建分支、提交、推送或部署。
