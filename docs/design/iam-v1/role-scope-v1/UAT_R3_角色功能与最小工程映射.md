# UAT-R3｜角色功能与最小工程映射

2026-10-19。状态：**PENDING_OWNER / DESIGN_ONLY**。本轮只改5199合成HTML，不建立下表模型，不迁移Policy，不授予部门/公司考勤或其他App功能。旧设计固定提交`4d4ed6223e53d84d9efbca287d8e0e25c1ce3e8a`保留；本说明取代其“只读目录、无角色编辑”的后续设计范围。

## 人事的三处操作

员工管理：选择员工→考勤角色→普通员工/部门考勤员/考勤管理员→确认负责部门→保存演示。跟随部门默认与单独指定分开；未开通是结果，不是第四种岗位角色。主部门只作建议，考勤员须主动确认负责部门，多个部门不含下级。

角色与权限：选择App和角色→勾选功能→保存演示草稿→预览增加/取消功能和全部使用者→确认发布到演示。只存草稿、取消发布和错误均不改变员工；成功后所有引用者同步，逐人的部门范围与禁用保留。原型有范围不足、版本冲突、保存失败、角色停用和引用失效的可点击拒绝状态；它们是明确标注的模拟检查，不是后端命令。

部门管理：普通默认只允许普通员工或不默认开通；部门考勤员和管理员逐人指定。初始一车间有2名跟随者、1名独立考勤员；预览人数可核对。默认变化不改独立角色和明确禁止。员工更多里的临时禁用保留角色；解除仍受其他禁止及无有效角色等条件限制。

## 当前考勤功能逐项核对

以下路径均相对本仓库`apps/hb_attendance_app/hb_attendance_app/hbos_attendance/`，原生HRMS对象另标。以本轮A源码固定提交为核对依据，不借用未合入的其他考勤分支。HTML的10个勾选项是功能分组，不能直接当作已通过的API权限标识。

| 产品功能 | 已存在的页面 / API或原生对象 | 当前原生权限与数据范围事实 | 角色接入差距 |
| --- | --- | --- | --- |
| 本人打卡、每日考勤结果 | Portal `/hbos/attendance/me`；`portal/personal.get_my_attendance` | 当前Session唯一Employee；SQL先限制employee；Site本地日期；只读；原生列表另外拒绝 | 已有`attendance.read/SELF`，本轮不把它转换为新角色 |
| 负责部门实时/历史面板 | `page/hbos_department_board/department_board_data.get_data`、`live_sync` | 旧入口HR User/HR Manager/System Manager；传入部门参数不等于获授权；含固定+8时钟及同步动作 | 必须将只读面板和同步分开；接入明确公司/部门谓词；考勤员不自动获得同步 |
| 员工考勤明细、公司汇总/异常看板 | `page/hbos_attendance_dashboard/dashboard_data.get_data`；原生Employee Checkin/Attendance；`report/打卡流水`、`report/考勤结果` | 旧HR角色、报表/原生文档权限；部分SQL/get_all依赖入口保护；当前IAM管理者不可据此读业务 | 部门/公司具名授权、列表/单条/count均前置范围；管理员仍需公司边界 |
| 班次/规则查看、编辑、新建、停用、删除 | `page/hbos_shift_management/shift_management_data`：`get_shift_overview/update_shift_rule/create_shift_rule/set_rule_status/delete_shift_rule/get_rules_board/get_conflicts`；HBOS Shift Rule | READ_ROLES含HR User；WRITE_ROLES为HR Manager/System Manager；规则版本和生效约束存在 | 拆分查看、维护、停用/删除等操作，不授泛HR Manager替代公司隔离 |
| 员工班次绑定 | 同文件`get_department_employees/bind_employee_shifts/get_employee_bound_shifts`；`page/hbos_employee_management/employee_management_data.bind_shift/bulk_bind_shift` | 旧HR读写角色；Employee/班次规则原生验证 | 逐员工、部门/公司范围及批量覆盖检查；不借此获得全平台员工管理 |
| 排班导入、排班记录 | `shift_management_data.import_schedule_file`；HBOS Employee Schedule、Shift Type/Shift Assignment（HRMS） | 文件存在/读取权限、格式校验和HR写权限；导入是写入，不能等同报表查看 | 上传、预览、确认提交、下载/后台执行均需公司/员工范围；保留原生校验 |
| 打卡/月报导入 | `page/hbos_attendance_import`；`page/hbos_monthly_upload/upload.process_excel`；HBOS Attendance Import Log | 页面存在；旧月报处理受HR写保护；独立导入页面存在不证明所有候选接口均已接通 | 各导入入口逐项登记与鉴权，原型只展示功能分组；未核实的接口不开放 |
| 考勤更正/补充、请假/加班/调休记录 | 原生Attendance/Attendance Request（HRMS）；HBOS Leave Record、HBOS Overtime Record、HBOS Rest Leave Record | 原生DocPerm、提交/取消/更正流程；当前分支没有统一“考勤更正”公司范围命令 | 保留业务验证/原因/审批/审计；界面不得假定已有通用更正API |
| 规则计算、结果重算、轮班生成 | `api.regenerate_attendance`；`rotation_schedule.generate_rotation_schedule` | 重算受HR写权限、日期边界约束；生成有原生排班记录写入；不是纯查看 | 独立高影响命令与确认；执行时重验范围、版本及任务主体 |
| 月报、对账报表与AI预览 | `report/月度考勤汇总.execute/ai_review_preview`；`report/hbos_月度汇总暂存（对账）` | 原生Report门禁及当前IAM旁路守卫；AI有单独开关/数据边界 | 报表、AI外发须分开能力；考勤管理员不自动获得AI外发或其他App资料 |
| 月报/异常导出 | `report/月度考勤汇总/export.export_xlsx/export_exceptions` | 旧HR导出角色；生成文件与下载路径仍需同一范围；现IAM `attendance.export`未开放 | 导出、文件归属、直接下载、Prepared Report与后台执行共同限制 |
| 班次人员表导出 | `roster_export.export_shift_roster` | EXPORT_ROLES为HR User/HR Manager/System Manager，生成File | 与考勤数据导出分项核准，按授权员工/公司过滤，不按中文角色名称放行 |
| 采集/同步与异常回写 | `api.sync_delicloud_checkin/sync_from_bitable/sync_overtime_from_bitable/sync_attendance_exceptions_to_bitable` | HR写保护及外部同步开关；本隔离Site关闭外部同步 | 属运维/集成能力；“全部考勤功能”需明确列项审核，角色勾选不启动外部集成 |

结论：管理员设计保留完整考勤能力目标，包含维护、排班、导入、重算、更正、报表与导出；当前新角色只停在设计。`portal/permissions.py`仍将纳管用户的旧HR原生路径拒绝，旧合法Legacy HR正向路径保留。不能只加一个可编辑目录再把管理员实现为只读，也不能把旧HR宽角色映射当作已完成公司隔离。

## 最小结构与命令变更表（候选，未实施）

| 对象 | 最少字段或职责 | 命令与发布合同 | 原生配合/迁移边界 |
| --- | --- | --- | --- |
| 业务应用角色定义 | `app_id, role_key, title, boundary_kind, enabled, published_revision, draft_features[]`；功能项为受控`operation_id + scope_binding`，SELF项仍绑定本人 | `save_role_draft(expected_version)`只保存草稿；新建/复制/删除可后续；停用有使用者时先预览其影响 | 名称只作标签；不能用三个中文名决定授权；不新增身份库 |
| 不可变角色发布版本 | `role, revision, features[], native_role_mapping, created_by, published_at`；记录已校验的操作与范围上限 | `preview_role_publish`列全部成员/范围/增减功能；`publish_role(expected_revision, context_revision, request_id)`锁定角色和成员集，重验操作者覆盖全部使用者；失败原子回滚 | 映射Frappe Role/Profile/DocPerm必要能力；不得用System Manager/HR Manager代替对象隔离；未接入操作拒绝发布 |
| 员工/部门角色关联 | `app_id, subject_type(User/Department), subject_name, employee(可核唯一关联), role, published_revision, source_kind, source_ref, enabled`；子项`responsibility_type/ref/include_descendants=0`；高级期限后续 | `preview_assignment/save_assignment`显示原/新角色及范围；部门默认仅普通角色；独立指定不随默认变化；调岗预览独立职责保留/撤销/复核，不自动换负责部门 | User/Employee/Company/Department/External Identity与密码继续唯一；未来LIMS允许多条独立角色×范围；考勤首屏单选不成为全平台唯一约束 |
| 现有Policy/Rule及审计 | 显式deny、期限、资格、临时应用禁用原样保留；必要投影带`role_assignment/revision/source`并只允许受控命令维护 | 新角色定义/关联为授权来源；若复用Policy执行投影，须由同一命令事务生成、不能直接编辑成另一真相；撤权、恢复、角色发布都有来源审计 | 不把旧deny迁成“无默认”；分阶段核对旧allow来源，缺映射不猜；本轮没有迁移 |
| 能力摘要/业务执行 | 主体/应用摘要加入有关角色发布版本、关联及来源摘要；逐角色逐操作求值，不能把动作和范围集合交叉相乘 | 相关撤权下一请求生效；无关角色变动不清本人考勤；发布期间旧预览/旧成员集409；无权403 | 文档/API/页面/报表/导出/附件/后台任务同一执行链；不自动获得IAM管理、跨公司、QA签署或知识原件下载 |

本轮未新增字段、DocType、角色/Profile或业务API。正式承接仍为Vue3+Ant Design Vue；HTML是受CSP限制的内存演示，不连接5198。Owner确认固定设计和本表后，另开正式实施任务。

## Owner本次只需看

打开5199依次看员工管理、角色与权限、部门管理；试给员工选角色，再试改一个角色功能并核对影响。确认界面表达及上表工程范围即可。已通过的14日/18日、切回和退出换人无需再跑。
