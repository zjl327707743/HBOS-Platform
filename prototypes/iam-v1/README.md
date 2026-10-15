# HBOS IAM V1 · R4 A 身份与考勤交互补充

状态：`IAM_R4_IDENTITY_CONTRACT_AND_DELTA_REVIEW_READY`。B/C：`NOT_RUN / PENDING_OWNER`。

沿用 R3 已认可的登录视觉，只补 Employee 中心、企业首次开户/复用和考勤对象范围三处交互。Vue 3 + Ant Design Vue；全部人员、业务记录、标识与临时口令都是合成演示。没有 OAuth、认证 API、数据库或 Frappe 代理。正式产品代码没有改变。

## 本机预览

在本目录运行：

```sh
npm ci
npm start
npm run status
npm stop
```

地址 `http://iam-prototype.localhost:5197/`，备用 `http://127.0.0.1:5197/`，只监听回环地址。5196 的已有服务保留。启停脚本只管理本目录登记且来源匹配的 PID，冲突时拒绝，不停止其他服务。`.runtime/` 不提交。

## R4 评审路径

1. 切换演示管理员：Employee 列表包含未开户人员，服务账号和待关联账号另列。打开详情 → 身份与业务关联，查看稳定 Employee/User 键、前导零工号和来源标识；管理员查看他人安全页没有本人改密/换绑操作。
2. 退出：左侧企业场景演示首次关联已有员工开户、预建账号归属验证与复用、身份冲突、待员工关联、非本企业拒绝。独立临时口令仅一次展示于内存，重复 OAuth 不重置或再显示；全部为本地合成流程。
3. 企业账号待员工关联时没有伪造 Employee，也不能读取考勤。明确关联已有 Employee 后再次同一企业身份登录仍复用原账号。
4. 应用权限 → 考勤实例：本人读取/指定部门/导出独立判定；注入他人 employee 参数返回拒绝与 total=0。快捷场景能观察 self∩部门、限定 deny 与 APP 全禁；本人历史按 Employee 键保持，部门历史需事件时部门证据。
5. 部门预设、个人例外、调岗、停用、会话、保存失败/版本冲突与合成扩展沿用原路径。高风险不靠部门自动授予。
6. 底部重置合成演示只重置 `hbos.iam-v1.r4.synthetic.v4`；R3 的 `hbos.iam-v1.r3.synthetic.v3` 记录保留。

`attendance.read` 沿用现有产品能力名；`attendance.export` 和真实部门报表是未接入候选，合成结果不证明可授予正式能力。管理员配置目标员工与当前本人会话主体分开。

## 验证与正式接入边界

```sh
npm test
npm run build
```

测试仅证明本地演示生命周期与权限契约，不证明真实服务器隔离、密码/MFA/会话安全或 HRMS 副作用。Ant Design 全量原型构建保留体积提示。

唯一开工单为 `docs/design/iam-v1/R4_A_唯一开工单.md`；身份来源证据、Portal 候选逐 hunk 补丁、验证与截图在同目录。R3 Draft PR #50 保留，R4 另立设计分支和 Draft PR。禁止把原型整包合入产品。Owner 明确批准候选完整 SHA、固定产品基线、确切文件/模型和隔离环境后才能进入 B/C；合并/正式部署归原项目合并线。
