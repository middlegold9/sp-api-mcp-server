# sp-api-mcp-server

> Amazon SP-API MCP Server —— 跨境电商 AI 工作流的「高速公路」地基。
> 把订单 / 目录 / 价格 / FBA 库存 / 报表 / Feed / 广告 等亚马逊能力封装为标准化 MCP 工具，供上层 Agent（广告复盘、经营日报、Listing 推送、客服助手）直接调用。

> 阶段：**功能设计（Design）**。本仓库当前为端到端功能梳理文档，代码骨架待落地。

---

## 0. 背景与动机

**FDE 视角（碎石路 → 高速公路）**：参考 FDE 岗位认知文档 9.4——海外 FDE 把现场解法回流成平台能力，越做越轻、出现利润拐点；国内多数驻场成果留在单个客户、人撤即失效。本服务就是要做那个「回流的平台能力」。

跨境卖家每天在五个场景（SKU 上新、内容转化、广告复盘、客服、经营日报）里重复调用亚马逊数据。如果每个上层 Agent 都各自对接 SP-API，会出现：重复写鉴权、重复处理 RDT/PII、重复踩限流、无法复用。**本服务把「对接亚马逊」一次性做成平台能力（MCP Server）**，上层只调工具名，不碰 API 细节——一个能力喂饱五个场景。

### 解决的具体问题
- **鉴权复杂**：LWA + AWS SigV4 + RDT 受限数据令牌，新手极易踩坑。
- **两套 OAuth**：广告 API 与 SP-API 是独立授权体系，需统一封装。
- **限流治理**：429 / quota 需统一退避、缓存、重试。
- **PII 治理**：买家信息、地址受 RDT 与数据驻留约束，需集中处理。

---

## 1. 目标与范围

**Goals**
- 提供一组**稳定的 MCP 工具**，覆盖卖家日常最高频的读 / 写操作。
- 统一鉴权：LWA access/refresh token 管理 + RDT 自动换取 + 广告 API token 管理。
- 统一限流 / 重试 / 缓存 / 日志，对上层透明。
- 暴露 `Tool Schema`（JSON Schema）供任何 MCP Client（Claude Desktop、Cursor、自研 Agent）发现与调用。
- 本地优先 / 数据不出域可选（沿用「数据隐私优先」原则）。

**Non-goals（v1）**
- 不实现具体业务策略（如「何时调价」），那是上层 Agent 的事。
- 不实现 UI；仅提供 MCP 协议接口（stdio / SSE）。
- 不做多租户 SaaS 账号体系（v1 单机 / 单凭证）。

---

## 2. 用户角色

| 角色 | 如何使用本服务 |
|---|---|
| 上层 Agent 开发者 | 在 Agent 里 `call_tool("spapi_orders_list", {...})` |
| 广告复盘 Agent | 调用 `ads_*` 报表工具拉数据 |
| 经营日报 Agent | 调用 orders / inventory / reports 聚合 |
| 客服助手后端 | 调用 orders / buyer_info 丰富上下文 |
| FDE / 运维 | 本地起服务，用 MCP Inspector 调试工具 |

---

## 3. 端到端链路总览

```
[Agent / 插件后端]
      │  MCP (stdio / SSE + JSON-RPC)
      ▼
[sp-api-mcp-server]
      ├─ Auth Layer     (LWA token store, RDT mint, Ads token store)
      ├─ SP-API Client  (AWS SigV4 签名, 限流退避, 缓存)
      ├─ Ads Client     (独立 OAuth, profileId 路由, gzip 报表下载)
      └─ Cache / Log / Metrics
      │  HTTPS (SigV4 + LWA / RDT)
      ▼
[Amazon SP-API]  +  [Amazon Advertising API]
```

**上层五个场景如何消费本服务**
- **广告复盘** → `ads_*` 报表工具 + 诊断建议（业务在 Agent 侧）。
- **经营日报** → `orders_list` / `fba_inventory` / `reports_get` 定时聚合。
- **客服** → `orders_get` / `order_buyer_info(RDT)` / `order_address(RDT)` 丰富买家上下文。
- **SKU 上新 / Listing 推送** → `feeds_create`（JSON_LISTINGS_FEED）推送草稿到卖家后台。
- **内容转化** → `catalog_item` 拉竞品 / 自家 ASIN 属性做素材。

---

## 4. 鉴权链路（核心难点）

### 4.1 SP-API（LWA Authorization Code Grant）
1. 卖家在 Appstore / 授权页同意 → 回调拿到 `authorization_code`。
2. 用 `client_id + client_secret + authorization_code` 向 `https://api.amazon.com/auth/o2/token` 换 `refresh_token`（长期）+ `access_token`（短期，约 1h）。
3. 后续调用：用 `refresh_token` 换 `access_token`。**本服务维护 refresh/access token 持久化与自动刷新。**
4. 请求 SP-API 时：
   - `Authorization: Bearer <LWA access_token>`
   - 加 AWS SigV4 签名头（`x-amz-date`、`x-amz-content-sha256`、AWS 签名 `Authorization`）——需要开发者 AWS 凭证（`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`，及可选 `AWS_ROLE_ARN`）。
5. 沙箱：`https://sandbox.sellingpartnerapi-na.amazon.com`（默认开 sandbox 便于联调）。

### 4.2 受限数据令牌 RDT（PII）
- 任何返回买家 PII 的接口（订单买家信息、收货地址）**不能直接用 LWA token**，必须先向 `https://api.amazon.com/tokens/2021-03-01/restrictedDataToken` 申请 RDT，传入 `{operation, path, method, dataElements:[buyerInfo|shippingAddress]}`。
- 用 RDT 作为 `Authorization: Bearer <RDT>` 再带 SigV4 调用。
- RDT 短命（约数分钟），按请求换；**服务自动判断接口是否需要 RDT 并惰性换取。**

### 4.3 广告 API（独立 OAuth）
- 授权域 `advertising-api.amazon.com`（欧洲 `...eu` / 远东 `...fe`）。
- 授权拿到 `access_token`（约 1h）+ `refresh_token`；调用头 `Authorization: bearer <token>` + `Amazon-Advertising-API-ClientId`。
- 需先 `GET /v2/profiles` 拿到 `profileId`（按市场 / 账号），后续接口带 `Amazon-Advertising-API-Scope: <profileId>`。
- 报表：`POST /<product>/<version>/report` 创建 → 轮询 `status` → `GET` 拿 `location`（gzip URL）下载。

### 4.4 凭证存储
- 本地：加密文件 / 环境变量；多卖家用 `seller_id` 索引。
- 不落明文的 secret；提供 `.env.example`。

---

## 5. 功能模块与工具清单

> 命名约定：`spapi_<domain>_<action>`、`ads_<product>_<action>`。每个工具暴露 JSON Schema（入参 / 出参）。

### 5.1 订单 Orders（restricted 部分需 RDT）
| 工具 | 对应 SP-API | 说明 | 限流注意 |
|---|---|---|---|
| `spapi_orders_list` | getOrders | 按时间 / 状态 / 市场列出订单 | 低频，缓存 |
| `spapi_orders_get` | getOrder | 单订单详情 | — |
| `spapi_orders_items` | getOrderItems | 订单商品行 | — |
| `spapi_orders_buyer_info` | getOrderBuyerInfo | **RDT** 买家姓名 / 邮箱 | 自动换 RDT |
| `spapi_orders_address` | getOrderAddress | **RDT** 收货地址 | 自动换 RDT |

### 5.2 目录 Catalog
| 工具 | 对应 SP-API | 说明 |
|---|---|---|
| `spapi_catalog_item` | catalog/2022-04-01/items | 按 ASIN / 关键词查属性（可用 Client Credentials，无卖家上下文） |
| `spapi_catalog_search` | 同上 keywords | 竞品 / 选品调研 |

### 5.3 价格 Pricing
| 工具 | 对应 SP-API | 说明 |
|---|---|---|
| `spapi_pricing_get` | product/pricing/v0/price | 自家 ASIN 价格 |
| `spapi_pricing_competitive` | product/pricing/v0/competitivePrice | Buy Box / 竞品价 |

### 5.4 FBA 库存 Inventory
| 工具 | 对应 SP-API | 说明 |
|---|---|---|
| `spapi_fba_inventory` | fulfillment/inventory/v0 getInventorySummaries | 可售 / 在途 / 预留库存、可售天数（日报核心） |
| `spapi_fba_inbound` | fulfillment/inbound/v0 | 发货计划状态（可选） |

### 5.5 报表 Reports
| 工具 | 对应 SP-API | 说明 |
|---|---|---|
| `spapi_reports_create` | reports/2021-06-30 createReport | 创建报表（GET_MERCHANT_LISTINGS_ALL_DATA、GET_FLAT_FILE_ORDERS 等） |
| `spapi_reports_get` | getReport | 轮询状态 |
| `spapi_reports_document` | getReportDocument | 下载（自动解压 / 解密） |

### 5.6 Feed（写：Listing 推送）
| 工具 | 对应 SP-API | 说明 |
|---|---|---|
| `spapi_feeds_create` | feeds/2021-06-30 createFeed | 提交 JSON_LISTINGS_FEED / PATCH |
| `spapi_feeds_get` | getFeed | 轮询处理状态 |
| `spapi_feeds_document` | getFeedDocument | 取结果（错误明细） |

### 5.7 广告 Advertising（独立 OAuth）
| 工具 | 对应 Ads API | 说明 |
|---|---|---|
| `ads_profiles_list` | /v2/profiles | 列出账号 / 市场 profileId |
| `ads_campaigns_list` | /v2/sp/campaigns | 广告活动 |
| `ads_adgroups_list` | /v2/sp/adGroups | 广告组 |
| `ads_keywords_list` | /v2/sp/keywords | 关键词 |
| `ads_targets_list` | /v2/sp/targets | 商品 / 品类投放 |
| `ads_searchterms_report` | /v2/sp/searchterms/report | 搜索词报表（否定词挖掘） |
| `ads_performance_report` | /v2/sp/**/report | 按时间维度表现 |
| `ads_campaign_update` | 写接口 | **需人工审批开关**（见 §8） |
| `ads_keyword_update` | 写接口 | 需人工审批开关 |
| `ads_negativekeyword_create` | 写接口 | 需人工审批开关 |

---

## 6. 数据模型（核心实体）
- `SellerCredential`：`seller_id`, `marketplace_ids`, `lwa_refresh_token(enc)`, `ads_refresh_token(enc)`, `region`。
- `ToolCall`：`tool`, `args`, `ts`, `latency`, `status`, `cached`。
- `ReportJob`：`report_type`, `status`, `document_url`, `expires`。
- 出参统一包装：`{ok, data, request_id, rate_remaining, cached, raw?}`。

---

## 7. 配置与部署
- 环境变量 `.env`：`LWA_CLIENT_ID`, `LWA_CLIENT_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ROLE_ARN`(可选), `SP_API_REGION`, `ADS_REGION`, `TOKEN_STORE_PATH`, `CACHE_TTL`, `LOG_LEVEL`。
- 启动：`python -m sp_api_mcp --transport stdio`（默认）；可选 `--transport sse --port 8000`。
- Docker：`Dockerfile` + `docker-compose`（含 Redis 缓存可选）。
- 依赖：`mcp`(Python SDK), `boto3`(SigV4), `httpx`, `pydantic`。

---

## 8. 安全与合规
- **最小权限 Scope**：仅申请用到的 SP-API role（如具体 `orders:read` 等）；写操作单独授权。
- **PII 治理**：RDT 仅在必要时换；出参默认脱敏（邮箱 / 电话掩码可配置）。
- **数据驻留**：报表 / 缓存默认本地；上传外传需显式开启（沿用「数据隐私优先」）。
- **审计**：所有写操作（feed / ads 更新）记日志 + 人工审批。
- **限流尊重**：429 / Retry-After 退避；Ads quota 头监控。

---

## 9. 可验证（Verification）
- **Tool Schema 测试**：用 MCP Inspector 列出全部工具，断言 schema 合法、必填入参校验生效。
- **连通性测试**：sandbox 下 `spapi_orders_list` 能返回（或正式环境受限数据集）。
- **RDT 路径测试**：mock 订单买家信息接口，断言自动换 RDT 且用 RDT 调用。
- **限流测试**：人为触发 429，断言退避并成功重试。
- **Eval 集**：`tests/fixtures` 放样例响应，断言归一化出参稳定。

---

## 10. 可复盘（Observability & Feedback）
- 结构化日志（JSON）：每工具调用 `latency / status / rate_remaining`。
- Metrics：调用量、错误率、缓存命中率、RDT 使用次数。
- 上层 Agent 可回传「该工具结果是否有用」标注 → 改进缓存策略与 schema。
- 版本化工具（语义版本），breaking change 走 `spapi_*_v2`。

---

## 11. 与另两个项目的接口契约
- **seller-central-reply-assistant**：后端在生成回复前调用 `spapi_orders_get` / `spapi_orders_buyer_info(RDT)` 丰富上下文。约定出参含 `order_status, ship_status, buyer_name, market`。
- **amazon-ads-review-agent**：直接依赖 `ads_*` 工具拉报表；写操作（`ads_campaign_update` 等）通过「审批网关」执行（见 §5.7 注）。

---

## 12. 路线图
- **M1**：Auth + Orders + Reports 读链路（sandbox 跑通）。
- **M2**：FBA 库存 + Pricing + Catalog + Feeds 写。
- **M3**：Advertising 全工具 + RDT 治理 + 缓存。
- **M4**：SSE 传输 + 多卖家 + 审计面板。

---

## 13. 风险与开放问题
- SP-API 审批周期长（开发者账号 + Appstore 上架）；MVP 可先用 sandbox / 已授权测试账号。
- 广告 API 报表为异步 + gzip，需健壮轮询。
- RDT 的 `dataElements` 声明需精确，过宽会被拒。
- 各市场 endpoint 不同（NA / EU / FE），需 region 路由表。

---

## 14. 参考资料
- SP-API 连接：https://developer-docs.amazon/sp-api/docs/connecting-to-the-selling-partner-api
- 受限数据令牌：https://developer-docs.amazon/sp-api/docs/tokens-api-v2021-03-01
- 授权码授权：https://developer-docs.amazon/sp-api/docs/authorization-api-v1
- 报表 API：https://developer-docs.amazon/sp-api/docs/reports-api-v2021-06-30
- Feed API：https://developer-docs.amazon/sp-api/docs/feeds-api-v2021-06-30
- 广告 API：https://advertising.amazon.com/API/docs/en-us/reference
- MCP 协议：https://modelcontextprotocol.io
- 配套项目：middlegold9/seller-central-reply-assistant、middlegold9/amazon-ads-review-agent
