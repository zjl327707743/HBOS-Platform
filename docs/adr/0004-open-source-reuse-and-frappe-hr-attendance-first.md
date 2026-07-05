# ADR-0004: Open Source Reuse and Frappe HR Attendance First

**Date**: 2026-07-05
**Status**: accepted
**Deciders**: 用户、ChatGPT、Claude、Codex

## Context

项目计划复用 Frappe/ERPNext/Frappe HR 等开源能力，同时后续 M1 可能优先涉及考勤能力。开源复用可以降低建设成本，但直接复制大段源码或修改核心源码会带来许可证、升级和维护风险。

## Decision

采用开源复用优先原则。M1 考勤优先做 Frappe HR / HRMS 能力映射，先确认已有能力、扩展点和差距；未经确认不得复制大段开源源码；禁止修改 Frappe/ERPNext/Frappe HR 核心源码。

## Alternatives Considered

### 直接复制开源考勤源码后改造

- **Pros**: 短期看似启动快
- **Cons**: 容易引入许可证、升级和维护风险
- **Why not**: 未经确认不得复制大段开源源码，必须先做能力映射和扩展方案

### 完全自研考勤模块

- **Pros**: 业务定制空间大
- **Cons**: 会重复建设 Frappe HR / HRMS 已有能力
- **Why not**: M1 应优先评估和复用成熟开源能力

## Consequences

### Positive

- 降低重复建设成本
- 降低核心源码修改导致的升级风险
- 为 M1 考勤边界提供清晰评估路径

### Negative

- 前期需要投入能力映射和差距分析
- 部分海滨特有规则可能需要自定义 App 扩展

### Risks

- 误用开源源码可能造成许可证或维护问题；缓解方式是保留来源审查、限制复制范围，并通过自定义 App 扩展实现差异能力。
