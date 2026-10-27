# R6 独立安全修复：Portal_R6_请求前鉴权读取并发修复

状态：G4_IMPLEMENTING / NOT_MERGED，2026-10-27。

Owner本轮明确授权独立安全修复与18191合成验证，提案补丁567d2f8fb2180db60edb72d1fb7acf798011dde0d251b165355ba9fa12bb6b7b。仅非生产候选工程实施及既有18191隔离Site；不含合并、标签、发布或真实站点变更。

请求前只读guard复用current_read，最多4次、回滚后全量重鉴权；拒绝及非读取错误不重试，业务命令不重放。不改schema、DocPerm、原生角色或公司/对象授权范围。

验证：Python3.11/3.12 各581考勤测试PASS；Python3.12的248 Portal合同PASS（没有把单测当真实权限验收）。真实并发及权限UAT须记录新组合SHA；不能把旧3b组合的39视口等证据改写成新代码已验收。新HEAD CI和独立审查仍须完成。

生产及18090/8080不变；当前运行使用不可变快照，product工作位没有服务挂载。回退到实际产品22源码；未安装新schema，无数据库回退要求。安全修复可单独撤销，但不得以恢复旧缺陷版本当作已通过验收。

已检查CLAUDE.md/AGENTS.md（规则无状态，不改）；已同步README、AI_CONTEXT、READING_GUIDE、PROJECT_STATUS、CURRENT_MILESTONE和M1_START_GATE。TEAM_PULL_READY=PENDING；未生产上线。
