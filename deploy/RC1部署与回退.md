# Knowledge RC1 候选部署与回退

唯一受控源为本目录 `build_candidate.py`、`release_candidate.py`、`candidate/preflight.py`。
隔离任务的 `work/build_candidate_uat5.py` 与 `work/deploy/candidate/{apply,rollback,preflight}` 是生成入口，不能另存一套实现。

1. 三棵源码提交干净后，以 `build_candidate.py --task-root <隔离任务>` 构建；全部输入生成不可变 release ID，镜像与静态件均独立 staging。
2. `release_candidate.py --task-root <隔离任务> --evidence-root <私有证据> prepare` 验证实际旧镜像、可读镜像归档和静态/配置，记录真实 CURRENT 与 PREVIOUS，再生成 PROPOSED 和明确配置差异。
3. 使用同一命令的 `apply --check`、`rollback --check` 检查资源；`apply` 通过完整七份 Compose 的 preflight 后切换 BFF/service，就绪后重新挂载前端。回读两容器与 HTTP 的实际静态文件哈希。
4. 故障时执行同一命令的 `rollback`。它使用 PREVIOUS 固定镜像与静态目录及完整七文件配置重建，重新核对实际文件；不回滚业务数据库、撤回、权限或 Token。

初次候选切换最多一次，后续仅允许一次有证据的代码修复；安全回退不受次数限制。使用 Main Agent 文件锁。`CURRENT` 仅在镜像、容器静态及 HTTP 校验同时通过后更新。
原件、企业正文、凭据、资料路径表、独立服务完整 Git 历史和运行数据不进入公共 HBOS 仓库。服务本轮通过 Owner 私有 Git bundle、源码 manifest、依赖锁和离线测试/重建入口交付。
