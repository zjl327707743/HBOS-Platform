# HBOS 入库拍照识别服务

入库时对产品标签拍照，自动识别**产品名称 / 物料代码 / 批号 / 生产日期 / 有效期至**，
识别结果经**人工校对**后写入台账。

完整方案见 [`docs/milestones/M3_R6_入库拍照识别服务方案.md`](../../docs/milestones/M3_R6_入库拍照识别服务方案.md)。

## 两条硬边界（Owner 已定）

1. **照片不出内网。** 本服务**不开任何外网访问**，不调用任何云端 API。
2. **人工校对是强制的。** 识别结果**不直接入账**，必须经操作人确认。

## 架构位置

遵项目规范 `docs/team/05_开源代码二次开发与升级规范.md` 的**优先级 5：外部服务**——
独立服务、HTTP 交互、**不修改 Frappe 核心源码、不直连数据库**。

```
┌──────────────────────┐   HTTP (JSON)   ┌──────────────────────────┐
│  hb_inventory_app     │ ───────────────→ │  本服务（FastAPI）         │
│  (Frappe 容器)         │ ←─────────────── │  原生跑在宿主机上           │
└──────────────────────┘   结构化 JSON     └──────────────────────────┘
```

**为什么原生跑在宿主机、不塞进 Frappe 容器**：承载机是 Apple M4，MLX 能吃满
Metal；而容器是 Linux arm64，**拿不到 Metal**，模型只能跑 CPU。另，ML 依赖重，
塞进 backend 会拖慢 Frappe。

### 容器访问宿主机（已实测通过）

需两件事：

1. 本服务监听 `0.0.0.0`（或宿主机在 Docker 网络中的地址），而非仅 `127.0.0.1`；
2. Frappe 侧请求 `http://host.docker.internal:8100`。

M3-R6 已实测：容器内 `GET http://host.docker.internal:8100/health` 返回 200。

### 网络与安全

> ⚠ **监听 `0.0.0.0` 意味着同局域网内其他机器也能访问 8100 端口。**
>
> - 仅作本地验证时，风险窗口小（用完即停）；
> - **正式部署时应缩小暴露面**：改为只绑 Docker 网关地址，或在宿主机防火墙
>   限制 8100 仅允许本机 / Docker 网段访问。

服务本身**不主动发起任何外网请求**——照片不出内网这条边界由它保证。

## 快速开始

```bash
cd services/hbos_ocr

# 1) 建虚拟环境并安装 Web 骨架（**不含 ML 依赖**，几十秒即可）
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# 2) 冒烟测试（stub 后端，不读图像，验证整条链路）
python tests/test_validate.py            # 约束校验层单测
python scripts/smoke_test.py             # 端到端链路（进程内，不启服务器）

# 3) 真正启动服务
HBOS_OCR_BACKEND=stub uvicorn app.main:app --host 127.0.0.1 --port 8100
```

## 识别后端（可插拔）

服务不绑定某个模型。`POST /api/v1/recognize` 的后端可用 `backend` 参数切换：

| 后端 | 依赖 | 状态 | 用途 |
| --- | --- | --- | --- |
| `stub` | 无 | ✅ 可用 | **链路冒烟测试**——不读图像，返回值由 hints/默认值构造 |
| `c1_local_vlm` | `pip install mlx-vlm` | 需安装 | 本地量化视觉语言模型（MLX / Metal） |
| `c2_ocr` | `pip install paddleocr paddlepaddle` | 需安装 | 本地 OCR + 结构化规则 |

**未安装的重型依赖不会让服务崩掉**——该后端在 `/health` 里标记为不可用，其余照常。

### 为什么要有 stub

M3-R6 方案第九节确认：**真实标签样本只能去仓库实地获取**。因此把工作分成两段：

| 工作 | 需要真实样本 |
| --- | --- |
| 服务骨架、校验层、Frappe 侧上传与校对界面、链路冒烟 | **不需要** |
| 测准确率、定 C1/C2 选型 | **必须** |

`stub` 后端让前半段**现在就能完整跑通**，不必等样本。

## 约束校验层（`app/validate.py`）

这是准确率的放大器。无论走 C1 还是 C2，识别结果都过这一层。

**核心**：物料代码是 **8 位、全数字**（Owner 确认）。OCR 最常见的错误是把数字
认成形近字母，因此可以**无条件把字母映射回形近数字**——

```
1300O215  →  13000215      l3000215  →  13000215
130002l5  →  13000215      13OOO215  →  13000215
```

**不需要知道"合法代码有哪些"**，纯字符映射即可纠错，不依赖任何主数据。

另含：批号三类结构提示、日期多格式解析、有效期早于生产日期的异常检测。

> 设计原则：**模型负责"读"，规则负责"筛"，人负责"定"。**
> 批号只提示不阻断——仓库不负责批号管理，批号由车间给出（M3-R0 确认）。

## 接口

### `GET /health`

返回各后端可用性，供 Frappe 侧判断"能不能用、能用哪个"。

### `POST /api/v1/recognize`

multipart 上传，字段：`image`（图片）、`backend`、`source_type`（自产/外购）、`request_id`（幂等键）。

响应（示例）：

```json
{
  "ok": true,
  "request_id": "…",
  "backend": "stub",
  "fields": {
    "product_name": "…", "item_code": "…", "batch_no": "…",
    "manufacturing_date": "…", "expiry_date": "…"
  },
  "raw_fields": { "…": "后端原始产出，便于追溯 AI 读到了什么" },
  "confidence": { "…": 0.99 },
  "hints": { "item_code": ["已按形近字符纠正：13OOO215 → 13000215"] },
  "needs_review": true,
  "elapsed_ms": 12
}
```

`hints` 按字段给出提示，供 Frappe 侧**高亮需要人工复核的字段**。

**本接口不写入任何业务数据**——落库由 Frappe 侧在人工确认后执行。

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `HBOS_OCR_BACKEND` | `stub` | 默认后端 |
| `HBOS_OCR_HOST` | `127.0.0.1` | 监听地址 |
| `HBOS_OCR_PORT` | `8100` | 端口 |
| `HBOS_OCR_TIMEOUT` | `60` | 单张识别超时（秒） |
| `HBOS_OCR_MAX_IMAGE_BYTES` | `5242880` | 图片大小上限 |
| `HBOS_OCR_C1_MODEL` | `mlx-community/Qwen2.5-VL-3B-Instruct-4bit` | C1 模型 |
| `HBOS_OCR_LOG_LEVEL` | `INFO` | 日志级别 |

## 数据与安全

| 项目 | 做法 |
| --- | --- |
| 照片出网 | **否**。服务不开外网访问 |
| 照片落盘 | **否**。识别后即释放。对上游库只接受文件路径的限制，用临时文件并**用完立即删除**（已在主文档记录该让步） |
| 服务日志 | **不记照片内容、不记批号与产品名**；只记 `request_id` / 后端 / 耗时 / 成败 / 错误类型 |
| 照片归档 | 由 **Frappe 侧**存到 `Attach`，随批次或单据走 |
| 幂等 | 进程内短期缓存（默认 10 分钟）。**非持久**，重启即失效——防重复点击足够，不做严格去重 |

## 目录结构

```
services/hbos_ocr/
├── app/
│   ├── main.py              FastAPI 应用（路由、幂等、日志）
│   ├── contract.py          数据契约（字段命名与业务对齐）
│   ├── config.py            环境变量配置
│   ├── validate.py          约束校验层 ← 准确率放大器
│   └── backends/
│       ├── __init__.py      后端注册表（缺依赖不崩）
│       ├── base.py          后端抽象契约
│       ├── stub.py          冒烟测试后端（无 ML 依赖）
│       ├── c1_local_vlm.py  C1：本地量化大模型（MLX）
│       └── c2_ocr.py        C2：本地 OCR + 规则
├── scripts/smoke_test.py    端到端链路测试（进程内，不启服务器）
├── tests/test_validate.py   约束校验层单测
├── requirements.txt         Web 骨架依赖（不含 ML）
└── pyproject.toml           含 c1 / c2 可选依赖分组
```

## 待办

- [x] Frappe 侧：拍照上传入口 + 人工校对界面（M3-R6 第二批）
- [x] 真实跨进程端到端验证（M3-R6 第三批，含容器 → 宿主机连通性）
- [ ] 仓库取样（清单见方案 7.8），用于测准确率、定 C1 / C2 选型
- [ ] 装 C1 / C2 的重型依赖并实测
- [ ] 准确率验收（标准见方案第七节）
- [ ] 正式部署时缩小服务暴露面（见「网络与安全」）
