# ADR-0001: Use Frappe/ERPNext as Platform Base

**Date**: 2026-07-05
**Status**: accepted
**Deciders**: 用户、ChatGPT、Claude、Codex

## Context

新乡海滨智能运营管理平台需要覆盖企业运营、业务流程、主数据、权限、报表和后续扩展。完全自研平台会增加基础能力建设成本，也会推迟业务验证。Frappe/ERPNext 已提供成熟的低代码模型、表单、权限、工作流、报表和 ERP 基础能力。

## Decision

采用 Frappe/ERPNext 作为开源平台底座，并在其上通过 Frappe 多 App 模块化架构建设海滨自定义能力。外部 AI/视频/算法能力以独立服务方式扩展，不直接混入平台核心。

## Alternatives Considered

### 完全自研平台

- **Pros**: 自由度最高，技术边界完全自主
- **Cons**: 基础能力建设周期长，维护成本高
- **Why not**: M0 阶段目标是建立可复用平台底座，不应先投入大量通用平台建设

### 只使用独立微服务

- **Pros**: 服务边界清晰，适合算法和高并发场景
- **Cons**: 缺少 ERP、权限、表单、工作流等现成业务底座
- **Why not**: 企业运营管理需要大量通用业务能力，单纯微服务会重复造轮子

## Consequences

### Positive

- 更快获得 ERP、权限、表单、工作流、报表等基础能力
- 自定义业务可以通过 Frappe App 模块化扩展
- 外部 AI/视频/算法服务可以保持独立演进

### Negative

- 需要遵守 Frappe/ERPNext 的框架约束
- 团队需要学习 Frappe 的 DocType、权限和 App 机制

### Risks

- 过度修改核心源码会增加升级风险；缓解方式是禁止修改 Frappe/ERPNext/Frappe HR 核心源码，优先使用自定义 App 扩展。
