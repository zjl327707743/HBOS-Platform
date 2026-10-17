# HBOS 生产看板取数服务

生产看板的数据出口。**飞书凭据只在服务端** —— 这是它存在的唯一理由。

见 `docs/frontend/P4_生产看板_取数架构方案对比.md`（架构方案 B）与
`docs/frontend/P4_生产看板_视觉方案与页面结构.md`（口径）。口径由 Owner 逐条确认。

## 它做什么

```
读  飞书 7 张 产量明细数据-*  +  月度生产计划明细  +  月度目标产能  +  AI工艺分析结果
算  按确认过的口径聚合（见 app/contract.py 顶部的口径清单）
给  前端 4 个接口
```

**它不写飞书** —— 写的是 AI 分析服务（另一条链路，定时脚本）。

## 运行

```bash
cp .env.example .env      # 填 HBOS_FEISHU_APP_ID / HBOS_FEISHU_APP_SECRET
uv venv --python 3.12
uv pip install -r requirements.txt
uv run --env-file .env uvicorn app.main:app --host 127.0.0.1 --port 8101
```

前端侧配 `VITE_PRODUCTION_SERVICE_ORIGIN=http://127.0.0.1:8101`
（见 `frontend/hbos-portal-web/.env.example`），看板即从「未接入」切到正常态。

## 接口

| 接口 | 说明 |
|---|---|
| `GET /health` | 健康检查；返回 `feishuConfigured` 但不回显凭据 |
| `GET /production/monthly` | 当月看板行（完成/目标/完成率/收率/目标收率/昨日入库） |
| `GET /production/yesterday` | 昨日入库量（按收料日期） |
| `GET /production/ai-analysis` | AI 工艺分析结论；表空时返回空数组 |

## 两条纪律

**① 取不到就 503，不返回 0。**

凭据没配、飞书超时、表读不到 —— 一律 503 并返回错误说明。
前端据此显示「未接入」态。**绝不返回 0 或空行**：
看板上的 0% 会被读成「本月没产量」，那是比「没数据」更坏的答案。

**② 没有值就留 None，不填 0。**

`收率 = None`（未入库）与 `收率 = 0`（收率为零）在业务上完全不同 ——
`app/sources.py` 的 `_number()` 和 `contract.weighted_target_yield()` 都遵守这条。

## 结构

```
app/config.py      环境变量（凭据只在这里）
app/feishu.py      飞书 OpenAPI 客户端（取 token + 分页拉记录）
app/sources.py     飞书记录 → 内部结构（类型归一化）
app/contract.py    口径实现（**纯函数，不依赖 FastAPI/飞书，可离线测**）
app/main.py        FastAPI 接口 + 5 分钟进程内缓存
tests/             口径单测 + 服务冒烟测（都不联网）
```

## 测试

```bash
uv run --with pytest pytest tests/ -q
```

口径改动必须同步改 `tests/test_contract.py` —— 那里锁着 Owner 确认过的每条口径
（收料日期落月、加权目标收率、F13 三成员合并、四车间不录、无值留空）。

## 一个已避开的历史坑

飞书 datetime 字段返回的是**当地时间午夜**的毫秒时间戳。用 `utcfromtimestamp`
解析会得到**前一天**（如 `2025-10-01` → `2025-09-30`）——对「按日期落月」的看板
意味着跨月批次落错月。`contract.parse_month_day()` 固定按 **UTC+8** 解释，并有测试锁住。

## 网络与安全

开发：绑 `127.0.0.1`，不开外网。凭据在 `.env`（已 gitignore）。

## 部署到服务器

**本机开发不配开机自启** —— 本机只是开发环境，正式运行在服务器上（Owner 2026-10-02 定）。
所以本服务**没有 launchd plist**，用 uvicorn 手动起即可。

部署时要改的**三处**（都是环境变量，不改代码）：

| 变量 | 开发默认 | 部署时应为 |
|---|---|---|
| `HBOS_PRODUCTION_HOST` | `127.0.0.1` | 看服务器拓扑定；若前面有 nginx 反代，仍绑 `127.0.0.1` 最安全 |
| `HBOS_PRODUCTION_CORS_ORIGINS` | 本机 Vite 端口 | **看板的实际域名**（例 `https://hbos.example.com`）。不改的话浏览器会因 CORS 拦掉请求 |
| `HBOS_FEISHU_APP_ID` / `_SECRET` | 本地 `.env` | 服务器的密钥管理（环境变量 / 密钥服务），**不写进镜像** |

前端侧对应改 `VITE_PRODUCTION_SERVICE_ORIGIN` 为服务器上的服务地址。

**未做（部署阶段再说）**：Docker 化、反向代理、进程守护（systemd / supervisor）、
健康检查接入。这些依赖服务器拓扑，现在定没有意义。
