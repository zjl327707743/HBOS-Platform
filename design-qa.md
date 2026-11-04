# R6-A2.2 正式页面设计复核

source visual truth path: /Users/hb/Projects/HBOS/design/r6-experience-v2（Owner 固定的 R6-A2.2 / Design System v1.3；原型只读）
implementation: /Users/hb/Projects/HBOS/workspaces/product，feat/hbos-r6b-experience-v1，整改起点2261a2d。
implementation screenshot path: PENDING_NEW_CANDIDATE_BROWSER_CAPTURE
viewport: 最终构建须按任务书T10同尺寸、同状态复核；当前不填写未执行尺寸。
source/implementation pixel dimensions and density: PENDING；不使用历史DPR模拟代替原生200%。
state: G3/G4 reopened after Owner rejected full fidelity.

## 阻断与整改范围

- [P1] 员工应用角色仍由旧应用清单与嵌套设置承接，原型的直接角色来源、角色卡、范围、变化核对主流程未完整落地。工作包A实施。
- [P1] 部门默认角色、跟随者与单独安排的解释和变化核对不连贯。工作包A实施，人数必须来自服务端预览。
- [P1] 个人中心密码/飞书/恢复动作仍展开旧表单或直接跳页，缺少原型弹窗与步骤。工作包B实施，保留真实proof/MFA/渠道。
- [P1] 角色编辑、保存草稿、影响核对、发布的下一步不清楚，干净草稿只显示禁用预览入口。工作包C实施。

以上初始问题来源于Owner实际反馈与代码映射，不冒充本轮截图比较结论。浏览器工具返回 Local browser use is disabled in Work settings，新构建的可见状态尚未抓取。

## 必需检查面

- 字体与排版：PENDING同状态截图。
- 间距与布局节奏：PENDING；含固定抽屉身份/底部操作、宽屏及短窗。
- 色彩与token：沿用既有主题，PENDING最终可见比较。
- 图片与资产：保留既有品牌/头像/图标资源；PENDING最终可见比较。
- 产品文案与内容：按原型任务语言补齐，真实数据状态不捏造；PENDING完整逐状态核对。

## 比较历史

1. Owner否决旧753的整体还原，G3/G4重新打开。完整视图与聚焦区域的新对照均待浏览器工具恢复后取得。
2. 正式代码已补齐流程并通过44文件409离线测试、类型与改动lint；这些不计作视觉比较迭代。仍缺新构建与原型同尺寸、同状态的完整/聚焦截图，未作视觉通过声明。

full-view comparison evidence: PENDING
focused region comparison evidence: PENDING，员工角色/部门默认/安全弹窗/发布弹窗均需要聚焦比较。
primary interactions tested: 旧753历史证据另列；本轮新候选PENDING。
console errors checked: NOT_RUN_ON_NEW_CANDIDATE。

final result: blocked
