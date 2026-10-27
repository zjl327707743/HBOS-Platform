# R6 独立安全修复：Portal_R6_具名HR原生关联兼容修复

状态：G4_IMPLEMENTING / NOT_MERGED，2026-10-27。

Owner本轮明确授权独立兼容修复与18191合成验证，提案补丁e2fe046269f5f5cd983b908191b84e27ea315da21d5a566178bc91c63708d115。仅非生产候选工程实施及既有18191隔离Site；不含合并、标签、发布或真实站点变更。

既有受控开户/关联中仅为Website User准备精确Employee和Company原生限制，保留原生钩子和角色/类型/启用状态核验，并拒绝范围增长或原限制丢失。不改schema、DocPerm、原生角色或公司/对象授权范围。

验证：Python3.11/3.12各253项Portal合同PASS；5项新增测试覆盖精确两项限制及受控顺序、System User旧路径、范围增删拒绝、重复关联/停用拒绝及原生钩子失败透传。18191真实HR开户、关联、首次改密仍待验证。真实并发及权限UAT须记录新组合SHA；不能把旧3b组合的39视口等证据改写成新代码已验收。新HEAD CI和独立审查仍须完成。

生产及18090/8080不变；当前运行使用不可变快照，product工作位没有服务挂载。回退到实际产品22源码；未安装新schema，无数据库回退要求。安全修复可单独撤销，但不得以恢复旧缺陷版本当作已通过验收。

已检查CLAUDE.md/AGENTS.md（规则无状态，不改）；已同步README、AI_CONTEXT、READING_GUIDE、PROJECT_STATUS、CURRENT_MILESTONE和M1_START_GATE。TEAM_PULL_READY=PENDING；未生产上线。
