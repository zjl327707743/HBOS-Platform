# R6-A2.2 固定设计依据

Owner 在2026-10-27正式实施指令中明确指定R6-A2.2 / HBOS Design System v1.3；此目录保存该依据，不能由历史设计文档中的“待确认”“仅原型”状态反向替代当前实施授权。原型评审通过也不等于正式产品功能、权限或发布验收通过。

规范v1.1为基础，v1.2/v1.3为增补，三份合读。R6A2_2_ROOT_CAUSE_AND_REVIEW记录宽屏、矮窗、个人空间的设计选择。ENGINEERING_MAPPING和engineering/operation-scope-map.json保存原能力映射，正式实施以现有后端注册表、服务端拒绝和接口为准。当前正式实现及测试记录见[本轮主记录](../../milestones/Portal_R6B_正式管理体验与稳定集成.md)。

六份文件逐字来自本机唯一设计源，SHA256见SOURCE_BASELINE_SHA256.json；源目录之外没有新增设计。文档中的旧SHA、旧预览URL、局部截图路径和未打包的历史参考链接按原设计时点解读，不作为当前运行或交付入口。本目录不含原型源码、mock adapter、账号数据、口令、node_modules、dist或新依赖，未复制到正式API或编译包中。

产品中的对应组件为PageHeading、StatusTag、PanelFrame、ResourceState、EmployeeDrawer、RoleSettings、ChangeReview、OwnAccountVerification，以及共享PointerAtmosphere和R6样式。宽屏最大1440、面板高度与700px自然流、个人空间最大1160、手机单列和抽屉以规范为准；不得把CSS视口或DPR模拟当作原生200%。

本轮设计追溯文档补齐不改变75383cd验收候选的任何Vue/TS/CSS行为。源码来源、浏览器验收SHA、实际产品SHA分别登记，最终合并和同源构建仍须各自门禁。TEAM_PULL_READY=PENDING，未生产上线。
