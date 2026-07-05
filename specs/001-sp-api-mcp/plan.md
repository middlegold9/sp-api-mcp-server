# Plan: Amazon SP-API MCP Server

> 技术实现计划（Spec-Kit plan + Superpowers writing-plans 风格）。

## 技术栈
- Python 3.11+；`mcp`（FastMCP）；`httpx`；`boto3`（SigV4 签名）；`pydantic`；`python-dotenv`。
- 传输：stdio（默认）/ SSE（可选，uvicorn）。
- 测试：pytest + `respx` 模拟 SP-API / Ads API HTTP。
- 容器：Docker + docker-compose（可选 Redis 缓存）。

## 目录结构
```
sp-api-mcp-server/
├── pyproject.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── src/sp_api_mcp/
│   ├── __init__.py
│   ├── server.py            # FastMCP 入口，注册工具
│   ├── config.py            # 环境变量 / 配置
│   ├── models.py            # SellerCredential / 出参信封 / 实体
│   ├── auth/
│   │   ├── lwa.py           # LWA token store + 刷新 + RDT 换取
│   │   └── ads.py           # 广告 API OAuth + profile 路由
│   ├── client/
│   │   └── sp_api_client.py # SigV4 签名 + 限流退避 + 缓存
│   ├── gateway/
│   │   └── approve.py       # 写工具审批网关
│   └── tools/
│       ├── orders.py        # + RDT
│       ├── catalog.py
│       ├── pricing.py
│       ├── inventory.py
│       ├── reports.py
│       ├── feeds.py
│       └── advertising.py
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_rdt.py
    ├── test_client_retry.py
    └── test_tools_orders.py
```

## 数据模型（data-model.md 摘要）
- `SellerCredential`: seller_id, marketplace_ids, lwa_refresh_token(enc), ads_refresh_token(enc), region.
- `ToolCall`: tool, args, ts, latency, status, cached.
- `ReportJob`: report_type, status, document_url, expires.
- 出参信封：`Envelope{ok:bool, data:Any, request_id:str, rate_remaining:int|None, cached:bool}`。

## 契约（contracts）
- 工具命名：`spapi_<domain>_<action>` / `ads_<product>_<action>`。
- 写工具审批协议：未授权时返回 `{ok:false, blocked:true, reason:"approval required"}`。
- RDT 声明：`dataElements ∈ {buyerInfo, shippingAddress}`。

## 研究（research.md 摘要）
- **LWA**：authorization code grant → `refresh_token`（长期）/ `access_token`（~1h）；请求头 `Authorization: Bearer <LWA>` + AWS SigV4。
- **RDT**：`POST api.amazon.com/tokens/2021-03-01/restrictedDataToken`，body 含 `{operation, path, method, dataElements}`；用 RDT 作 Bearer 再带 SigV4。
- **SigV4**：需开发者 AWS 凭证（`AWS_ACCESS_KEY_ID`/`SECRET`，可选 `AWS_ROLE_ARN`）。
- **Ads API**：独立 OAuth（`advertising-api.amazon.com`）；先 `GET /v2/profiles` 拿 `profileId`，请求头带 `Amazon-Advertising-API-Scope`；报表异步创建 → 轮询 `status` → 下载 gzip `location`。
- **限流**：SP-API 每操作限流；Ads 返回 `x-amzn-RateLimit-Limit` / `x-amzn-RequestId`。

## 关键风险与缓解
- 开发者账号审批周期长 → MVP 用 sandbox + 已授权测试账号。
- RDT `dataElements` 过宽被拒 → 精确声明。
- 报表异步 + gzip → 健壮轮询 + 去重 + 解压。

## 快速开始（quickstart.md 摘要）
1. `cp .env.example .env`，填 `LWA_CLIENT_ID/SECRET`、`AWS_ACCESS_KEY_ID/SECRET`、`SP_API_REGION`。
2. `pip install -e .`（或 `docker compose up`）。
3. `python -m sp_api_mcp --transport stdio`。
4. MCP Inspector 连接 `stdio`，列出工具。

## 实现顺序（依赖）
1. 骨架 + 配置 + 出参信封（US6 基础）
2. Auth：`lwa.py`（token store+刷新）→ `ads.py`
3. Client：`sp_api_client.py`（SigV4 + 退避）
4. Tools：orders(+RDT) → reports → inventory → pricing → catalog → feeds → advertising
5. 审批网关封装写工具（FR6）
6. 测试 + Inspector 验证（FR1/FR3/FR5/FR6）
