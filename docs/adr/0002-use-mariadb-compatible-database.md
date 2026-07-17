# ADR-0002: Use MariaDB/MySQL Compatible Database Route

**Date**: 2026-07-05
**Status**: accepted
**Deciders**: 用户、ChatGPT、Claude、Codex

## Context

Frappe/ERPNext 生态长期以 MariaDB/MySQL 兼容数据库作为主要部署路线。项目需要优先保证平台底座兼容性、部署可预期性和后续升级稳定性，而不是在 M0 阶段引入不必要的数据库差异。

## Decision

采用 MariaDB/MySQL 兼容体系作为主要数据库路线。后续具体版本、部署方式和参数配置在 M0-R2 或后续环境规划中再确认。

## Alternatives Considered

### PostgreSQL

- **Pros**: 功能强，生态成熟，适合复杂查询
- **Cons**: 与 Frappe/ERPNext 常规部署路线不完全一致
- **Why not**: 当前优先级是降低底座兼容风险，而不是引入数据库路线差异

### 自研或小众数据库

- **Pros**: 可能满足特定性能或国产化诉求
- **Cons**: 生态兼容性和运维经验不足
- **Why not**: 不适合作为 M0 平台底座默认数据库路线

## Consequences

### Positive

- 与 Frappe/ERPNext 主流实践保持一致
- 降低环境部署和框架兼容风险
- 便于后续使用社区经验排查问题

### Negative

- 需要接受 MariaDB/MySQL 在部分高级 SQL 能力上的限制
- 数据分析类需求可能需要外部服务或数仓补充

### Risks

- 数据库版本选择不当可能影响 Frappe/ERPNext 兼容性；缓解方式是在 M0-R2 明确版本矩阵和验证步骤。
