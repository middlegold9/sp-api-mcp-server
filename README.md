# sp-api-mcp-server

> **Amazon SP-API 的 MCP Server（Model Context Protocol）** —— 跨境电商 AI 工作流的「高速公路」地基。
> 把订单 / 目录 / 价格 / FBA 库存 / 报表 / Feed / 广告 等亚马逊能力，统一封装成 **20 个标准化 MCP 工具**，让上层 Agent（广告复盘、客服助手、经营日报、Listing 推送）只调工具名、不碰 API 细节。

> 状态：**已落地 + 15/15 单测通过**（Python）。可用于 stdio / SSE 两种传输，被另两个项目（`seller-central-reply-assistant`、`amazon-ads-review-agent`）直接依赖。

---

## 1. 这个工具解决什么问题

跨境卖家 / 运营每天在 5 个场景里反复调用亚马逊数据（SKU 上新、内容转化、广告复盘、客服、经营日报）。如果每个上层 Agent 都各自对接 SP-API，会出现：

- **鉴权复杂**：LWA（Login with Amazon）+ AWS SigV4 签名 + RDT 受限数据令牌，新手极易踩坑。
- **两套 OAuth**：广告 API 与 SP-API 是独立授权体系，需分别封装。
- **限流治理**：429 / quota 需统一退避、缓存、重试，否则一跑就封。
- **PII 治理**：买家姓名 / 邮箱 / 地址受 RDT 与数据驻留约束，需集中处理。

本服务把「对接亚马逊」一次性做成**平台能力（MCP Server）**，上层只需 `call_tool("spapi_orders_list", {...})`，鉴权、签名、限流、RDT、缓存全部透明。一个能力喂饱五个场景。

---

## 2. 核心能力

| 能力 | 说明 |
|---|---|
| **统一鉴权** | LWA access/refresh token 持久化 + 自动刷新；广告 API 独立 OAuth（含 profileId 路由）。 |
| **RDT 自动换取** | 返回买家 PII 的接口（买家信息、收货地址）自动判断并惰性申请受限数据令牌。 |
| **SigV4 签名** | 所有 SP-API 请求加 AWS 签名头（`x-amz-date`、`x-amz-content-sha256`、SigV4 `Authorization`）。 |
| **限流退避** | 429 / `Retry-After` 指数退避；内置短缓存减少重复调用。 |
| **审批网关** | 写操作（Feed 提交、广告调价）默认**禁用**，需 `APPROVE_WRITES`/`ADS_APPROVE_WRITES` 显式开启，返回 `blocked` 而非真的执行。 |
| **统一出参** | 所有工具返回 `{ok, data, request_id, rate_remaining, cached, raw?}`，上层解析零成本。 |
| **双传输** | `stdio`（本地 Agent 子进程）与 `sse`（远程 HTTP 服务）两种接入方式。 |

---

## 3. 工具清单（共 20 个）

> 命名约定：`spapi_<domain>_<action>`、`ads_<product>_<action>`。⚡ = 写操作（受审批网关保护），🔒 = 需 RDT（自动换）。

**订单 Orders（5）**
| 工具 | 说明 |
|---|---|
| `spapi_orders_list` | 按时间 / 状态 / 市场列出订单（低频缓存） |
| `spapi_orders_get` | 单订单详情 |
| `spapi_orders_items` | 订单商品行 |
| `spapi_orders_buyer_info` 🔒 | 买家姓名 / 邮箱（自动换 RDT） |
| `spapi_orders_address` 🔒 | 收货地址（自动换 RDT） |

**报表 Reports（3）**
| `spapi_reports_create` | 创建报表（订单 / 库存 / 商品等） |
| `spapi_reports_get` | 轮询报表状态 |
| `spapi_reports_document` | 下载报表（自动解压 / 解密） |

**FBA 库存（1）**
| `spapi_fba_inventory` | 可售 / 在途 / 预留库存、可售天数（日报核心） |

**价格 Pricing（2）**
| `spapi_pricing_get` | 自家 ASIN 价格 |
| `spapi_pricing_competitive` | Buy Box / 竞品价 |

**目录 Catalog（2）**
| `spapi_catalog_item` | 按 ASIN 查属性（可选 Client Credentials，无卖家上下文） |
| `spapi_catalog_search` | 按关键词查（竞品 / 选品调研） |

**Feed（3，写 ⚡）**
| `spapi_feeds_create` ⚡ | 提交 JSON_LISTINGS_FEED / PATCH（Listing 推送） |
| `spapi_feeds_get` | 轮询 Feed 处理状态 |
| `spapi_feeds_document` | 取结果（错误明细） |

**广告 Advertising（4，独立 OAuth）**
| `ads_profiles_list` | 列出账号 / 市场 profileId |
| `ads_campaigns_list` | 广告活动列表 |
| `ads_performance_report` | 按天 / 周的表现报表（异步 → 轮询 → gzip 下载） |
| `ads_searchterms_report` | 搜索词报表（否定词挖掘数据源） |

> 写执行工具 `ads_campaign_update` / `ads_negative_keyword_create` 已在 `AdsClient` 内实现并带 `@require_approval` 网关，由 `amazon-ads-review-agent` 经 MCP 客户端调用（受 `ADS_APPROVE_WRITES` 控制，默认关闭）。如需作为独立 MCP 工具暴露，在 `server.py` 中 `@_reg` 注册即可。

---

## 4. 快速开始

### 4.1 安装
```bash
cd sp-api-mcp-server
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
# 或仅装运行依赖：pip install "mcp" "httpx" "pydantic" "pydantic-settings" "botocore"
```

### 4.2 配置 `.env`
复制 `.env.example` 为 `.env` 并填写：
```ini
# SP-API (LWA)
LWA_CLIENT_ID=your_lwa_client_id
LWA_CLIENT_SECRET=your_lwa_client_secret
LWA_REFRESH_TOKEN=your_seller_refresh_token
# AWS SigV4 凭证
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_ROLE_ARN=            # 可选，跨账号角色
# 区域：NA / EU / FE
SP_API_REGION=NA
# 广告 API
ADS_CLIENT_ID=...
ADS_CLIENT_SECRET=...
ADS_REFRESH_TOKEN=...
ADS_REGION=NA
# 审批开关（默认 false，写操作被拦截）
APPROVE_WRITES=false
ADS_APPROVE_WRITES=false
```

### 4.3 运行
```bash
# 本地 Agent 子进程（默认）
python -m sp_api_mcp --transport stdio

# 远程 HTTP 服务（SSE）
python -m sp_api_mcp --transport sse --host 0.0.0.0 --port 8000
```

---

## 5. 工具调用示例

### 5.1 通过 MCP 客户端调用（伪代码 / JSON-RPC）
```jsonc
// 列出近 7 天 US 订单
{
  "tool": "spapi_orders_list",
  "arguments": {
    "marketplace_ids": ["ATVPDKIKJ38US"],
    "created_after": "2026-06-28T00:00:00Z"
  }
}
```
```jsonc
// 拉取某广告 profile 昨日表现报表
{
  "tool": "ads_performance_report",
  "arguments": {
    "profile_id": "1234567890",
    "record_type": "campaigns",
    "report_date": "2026-07-04"
  }
}
```

### 5.2 返回结构（统一信封）
```json
{
  "ok": true,
  "data": { "orders": [ /* ... */ ], "next_token": null },
  "request_id": "req_8f2a...",
  "rate_remaining": 0.81,
  "cached": false
}
```

### 5.3 写操作被网关拦截的返回
```json
{
  "ok": false,
  "data": {
    "blocked": true,
    "reason": "approval required: set APPROVE_WRITES=true to enable write tools",
    "tool": "spapi_feeds_create"
  }
}
```

### 5.4 调试工具
用 [MCP Inspector](https://modelcontextprotocol.io) 连接 `stdio` 端点，可可视化列出全部 20 个工具的 JSON Schema 并试调用。

---

## 6. 上层五个场景如何消费本服务

- **广告复盘** → `ads_*` 报表工具 + 诊断建议（业务在 Agent 侧）。
- **经营日报** → `spapi_orders_list` / `spapi_fba_inventory` / `spapi_reports_get` 定时聚合。
- **客服** → `spapi_orders_get` / `spapi_orders_buyer_info`(RDT) / `spapi_orders_address`(RDT) 丰富买家上下文。
- **SKU 上新 / Listing 推送** → `spapi_feeds_create`（JSON_LISTINGS_FEED）。
- **内容转化** → `spapi_catalog_item` / `spapi_catalog_search` 拉竞品 / 自家 ASIN 属性做素材。

---

## 7. 安全与合规

- **最小权限 Scope**：仅申请用到的 SP-API role；写操作单独授权。
- **PII 治理**：RDT 仅在必要时换；出参信封默认带 `request_id` 便于审计。
- **审批网关**：所有写操作（Feed / 广告调价 / 否定词）默认 `blocked`，杜绝误烧钱 / 误推送。
- **数据驻留**：报表 / 缓存默认本地；外传需显式开启。
- **限流尊重**：429 / `Retry-After` 退避；Ads quota 头监控。

---

## 8. 测试

```bash
source .venv/bin/activate
PYTHONPATH=src python -m pytest -q
# 15 passed —— 覆盖：模型、LWA 令牌刷新、RDT 换取、SigV4、限流重试、订单、审批网关、广告工具
```

---

## 9. 与另两个项目的关系

- **seller-central-reply-assistant**：后端生成回复前调用 `spapi_orders_get` / `spapi_orders_buyer_info`(RDT) 丰富订单与物流上下文。
- **amazon-ads-review-agent**：直接依赖 `ads_*` 工具拉报表；写执行通过审批网关（受 `ADS_APPROVE_WRITES` 控制）。

---

## 10. 参考资料

- SP-API 连接：https://developer-docs.amazon/sp-api/docs/connecting-to-the-selling-partner-api
- 受限数据令牌（RDT）：https://developer-docs.amazon/sp-api/docs/tokens-api-v2021-03-01
- 广告 API：https://advertising.amazon.com/API/docs/en-us/reference
- MCP 协议：https://modelcontextprotocol.io
- 配套项目：`seller-central-reply-assistant`、`amazon-ads-review-agent`
