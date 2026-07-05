# Tasks: Amazon SP-API MCP Server

> Spec-Kit tasks（按用户故事组织；TDD：先测试后实现；`[P]` 可并行；含精确路径 + 验证）。

## T1 — 项目骨架与出参信封（US6 基础）
- [ ] `pyproject.toml`：声明 `mcp`、`httpx`、`boto3`、`pydantic`、`python-dotenv`、`pytest`、`respx`。
- [ ] `src/sp_api_mcp/__init__.py`：版本号。
- [ ] `src/sp_api_mcp/models.py`：定义 `Envelope`、`SellerCredential`、`ToolCall`、`ReportJob`（pydantic）。
- [ ] `src/sp_api_mcp/config.py`：用 pydantic-settings 读 `.env`（`LWA_*`、`AWS_*`、`REGION`、`CACHE_TTL`）。
- [ ] `tests/test_models.py`：断言 `Envelope` 序列化字段正确。 **← 先写测试 (TDD)**
- **验证**：`pytest tests/test_models.py` 绿。

## T2 — LWA 鉴权（US2 前置）`[P]`
- [ ] `tests/test_auth.py`：mock `api.amazon.com/auth/o2/token`，断言 refresh→access 刷新逻辑与持久化。 **← TDD**
- [ ] `src/sp_api_mcp/auth/lwa.py`：`LWATokenStore`（refresh/access 持久化、自动刷新、线程安全）。
- **验证**：测试绿；本地起服务能从 `.env` 加载。

## T3 — RDT 受限数据令牌（US2）`[P]`
- [ ] `tests/test_rdt.py`：mock `tokens/2021-03-01/restrictedDataToken`，断言对 PII 接口换 RDT 且用 RDT 作 Bearer。 **← TDD**
- [ ] `src/sp_api_mcp/auth/lwa.py` 增加 `mint_rdt(operation, path, method, data_elements)`。
- **验证**：测试绿；断言 RDT 短命、按请求换。

## T4 — SP-API 客户端（依赖 T2/T3）
- [ ] `tests/test_client_retry.py`：用 respx 模拟 429 + `Retry-After`，断言指数退避后成功。 **← TDD**
- [ ] `src/sp_api_mcp/client/sp_api_client.py`：`sign_request`（boto3 SigV4）、`call`（Bearer+RDT 选择、退避、缓存、出参包装 `Envelope`）。
- **验证**：测试绿；`rate_remaining` 被记录。

## T5 — 订单工具（US1/US2）
- [ ] `tests/test_tools_orders.py`：断言 `spapi_orders_list` / `spapi_orders_buyer_info`（自动 RDT）返回 `Envelope`。 **← TDD**
- [ ] `src/sp_api_mcp/tools/orders.py`：`spapi_orders_list`、`spapi_orders_get`、`spapi_orders_items`、`spapi_orders_buyer_info`(RDT)、`spapi_orders_address`(RDT)。
- **验证**：sandbox 下单 `spapi_orders_list` 返回。

## T6 — 报表 / 库存 / 价格 / 目录工具（US3）`[P]`
- [ ] `src/sp_api_mcp/tools/reports.py`：`spapi_reports_create/get/document`（自动解压）。
- [ ] `src/sp_api_mcp/tools/inventory.py`：`spapi_fba_inventory`。
- [ ] `src/sp_api_mcp/tools/pricing.py`：`spapi_pricing_get/competitive`。
- [ ] `src/sp_api_mcp/tools/catalog.py`：`spapi_catalog_item/search`。
- [ ] 各加对应 `tests/test_tools_*.py`（mock HTTP）。 **← TDD**
- **验证**：各测试绿。

## T7 — Feed 写工具 + 审批网关（US4/FR6）
- [ ] `src/sp_api_mcp/gateway/approve.py`：`require_approval()` 装饰器；未开启返回 `{ok:false, blocked:true, reason}`。
- [ ] `src/sp_api_mcp/tools/feeds.py`：`spapi_feeds_create/get/document`，写路径过网关。
- [ ] `tests/test_gateway.py`：断言未授权写被 `blocked`。 **← TDD**
- **验证**：测试绿；配置 `APPROVE_WRITES=false` 时写被拦。

## T8 — 广告工具（US5/FR4/FR6）
- [ ] `src/sp_api_mcp/auth/ads.py`：广告 OAuth + `profiles_list`（profileId 路由）。
- [ ] `src/sp_api_mcp/tools/advertising.py`：`ads_profiles_list`、`ads_campaigns_list`、`ads_searchterms_report`、`ads_performance_report`；写工具 `ads_campaign_update`/`ads_negativekeyword_create` 过网关。
- [ ] `tests/test_tools_advertising.py`：mock 报表异步轮询 + 下载。 **← TDD**
- **验证**：测试绿；报表 gzip 下载成功。

## T9 — Server 注册与传输（US6）
- [ ] `src/sp_api_mcp/server.py`：FastMCP 注册 T1–T8 全部工具；`--transport stdio|sse`。
- [ ] `.env.example`：列出全部变量。
- [ ] `Dockerfile` + `docker-compose.yml`。
- **验证**：`python -m sp_api_mcp` 启动；MCP Inspector 列出全部工具且 schema 合法。

## 并行与检查点
- T2/T3 可并行；T6 内四项可并行；T5/T6/T7/T8 依赖 T4。
- **人工检查点**（superpowers executing-plans）：T4 完成后暂停，确认客户端签名/退避正确再继续 T5+。
- 每任务遵循 RED→GREEN→REFACTOR；提交前 `pytest` 全绿（verification-before-completion）。
