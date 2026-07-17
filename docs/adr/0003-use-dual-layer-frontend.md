# ADR-0003: Use Dual-Layer Frontend

**Date**: 2026-07-05
**Status**: accepted
**Deciders**: 用户、ChatGPT、Claude、Codex

## Context

平台需要同时支持后台业务配置、数据维护、流程处理和面向管理层的运营驾驶舱。Frappe Desk 适合后台管理、表单、权限和流程操作，但大屏、图表、实时态势和体验定制更适合独立 Vue/React 前端。

## Decision

采用 Frappe Desk + Vue/React 双层前端。Frappe Desk 承担后台业务管理和配置入口，Vue/React 驾驶舱承担运营可视化、ECharts 图表和面向管理层的交互体验。

## Alternatives Considered

### 只使用 Frappe Desk

- **Pros**: 实现简单，与平台底座一致
- **Cons**: 驾驶舱视觉和交互定制能力有限
- **Why not**: 无法充分满足运营大屏和管理驾驶舱体验需求

### 只使用 Vue/React 前端

- **Pros**: 前端体验可完全定制
- **Cons**: 会绕开 Frappe Desk 的后台管理、权限和表单优势
- **Why not**: 会增加后台管理重复建设成本

## Consequences

### Positive

- 后台管理复用 Frappe Desk
- 驾驶舱可独立优化视觉和交互
- 前后端边界更清晰，便于按场景演进

### Negative

- 需要维护两类前端入口
- 需要设计统一认证、权限和数据接口边界

### Risks

- 双层前端可能造成体验割裂；缓解方式是在后续里程碑中统一导航、权限策略和 API 契约。

## References

- 前端实施流程规范：`docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`（独立前端必须原型先行 → Owner 审查 → 复刻实现 → 功能接入）
